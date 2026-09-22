# -*- coding: utf-8 -*-
"""向量库一致性修复 / 重建索引。

背景：
  1) 配置通义 embedding（1024 维）前，系统使用本地 384 维哈希向量，
     旧 Qdrant 集合维度声明与向量均已失效；
  2) generate_missing_embeddings 在「全量扫描」模式下曾把 dataset_id 传成 None，
     导致所有知识库向量被写进 knowledge_default，破坏按数据集隔离的检索。

本脚本（可重复执行，幂等）：
  A. 读取 MySQL 中已完成的分段向量，仅保留与当前 embedding 模型维度一致的行，
     重新 upsert 到 knowledge_<dataset_id> 正确集合；
  B. 清理被误用的 knowledge_default 集合；
  C. 对 embedding_status=pending/failed 的记忆，复用 memories.embedding（维度一致时）
     或重新向量化，写入 agent_memory__<agent_id>。

用法：
    python scripts/reindex_vectors.py            # 修复 + 摘要
    python scripts/reindex_vectors.py --dry-run  # 只报告不写入
"""
import os
import sys
import json
import argparse
from collections import defaultdict

_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend')
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from config import get_db
from engine.embedding_service import (
    get_embedding_config, get_embedding, _get_qdrant_collection_name,
)
from utils.vector_store import get_vector_store


def _current_dim():
    """当前 embedding 模型的真实输出维度（用一条极短文本探测）。

    注意：get_embedding_config() 返回的 api_key 为 Fernet 密文，必须解密后传入，
    否则远端 401 会静默降级为本地 384 维向量，探测结果就是错的。
    """
    from utils.llm import decrypt_api_key
    cfg = get_embedding_config()
    if not cfg:
        return None, None
    model = cfg['model_name'] or cfg['credential_name'] or cfg['provider']
    vec = get_embedding('维度探测', model, decrypt_api_key(cfg['api_key']),
                        cfg['api_base_url'])
    return (len(vec) if vec else None), model


def _load_segment_vectors(dim):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            SELECT id, dataset_id, content, embedding, embedding_status
            FROM dify_document_segments
            WHERE enabled = 1 AND status = 'completed' AND embedding IS NOT NULL
        """)
        rows = cur.fetchall()
    finally:
        db.close()

    ok, stale = [], 0
    for r in rows:
        try:
            vec = json.loads(r['embedding']) if r['embedding'] else []
        except (json.TypeError, ValueError):
            vec = []
        if vec and len(vec) == dim:
            ok.append((r['id'], r['dataset_id'], r['content'] or '', vec))
        else:
            stale += 1
    return ok, stale


def reindex_segments(dim, dry_run=False):
    vectors, stale = _load_segment_vectors(dim)
    by_dataset = defaultdict(list)
    for sid, ds_id, content, vec in vectors:
        by_dataset[ds_id or ''].append((sid, content, vec))

    print(f'[segments] 维度一致可复用={len(vectors)}，维度不符/损坏={stale}，'
          f'涉及数据集={len(by_dataset)}')

    if dry_run:
        for ds_id, items in by_dataset.items():
            print(f'  would write {len(items)} -> {_get_qdrant_collection_name(ds_id)}')
        return 0, stale

    store = get_vector_store()
    written = 0
    for ds_id, items in by_dataset.items():
        if not ds_id:
            continue  # 无归属数据集的分段不写入，避免再造 knowledge_default
        collection = _get_qdrant_collection_name(ds_id)
        store.create_collection(collection, vector_size=dim)
        for sid, content, vec in items:
            store.upsert(
                collection=collection,
                vectors=[vec],
                payloads=[{
                    'segment_id': sid,
                    'dataset_id': ds_id,
                    'content': content[:500],
                    'embedding_model': 'text-embedding-v3',
                }],
                ids=[sid],
            )
            written += 1
        print(f'  wrote {len(items)} points -> {collection}')

    # 清理历史误写的 knowledge_default（其内容均已按数据集重路由）
    if store.delete_collection('knowledge_default'):
        print('  dropped stale collection: knowledge_default')

    # 待补向量化的分段（维度不符 / 从未成功）置回 pending，交由既有异步任务处理
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            UPDATE dify_document_segments
            SET embedding_status = 'pending', embedding = NULL
            WHERE enabled = 1 AND status = 'completed'
              AND (embedding IS NULL OR JSON_LENGTH(embedding) <> %s)
        """, (dim,))
        db.commit()
        print(f'  重置为 pending 待重新向量化: {cur.rowcount} 个分段')
    except Exception as exc:
        db.rollback()
        print(f'  [warn] 重置 pending 失败（不影响主流程）: {exc}')
    finally:
        db.close()

    return written, stale


def reindex_memories(dim, dry_run=False):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            SELECT id, agent_id, content, embedding, embedding_status
            FROM memories
        """)
        rows = cur.fetchall()
    finally:
        db.close()

    from engine.agent_memory import _persist_embedding, _collection_name

    todo = []
    for r in rows:
        try:
            vec = json.loads(r['embedding']) if r['embedding'] else []
        except (json.TypeError, ValueError):
            vec = []
        if vec and len(vec) == dim:
            todo.append((r, vec))
    print(f'[memories] 总数={len(rows)}，维度一致可复用={len(todo)}')

    if dry_run:
        for r, _ in todo:
            print(f'  would write memory {r["id"]} -> {_collection_name(r["agent_id"])}')
        return len(todo)

    store = get_vector_store()
    seen = set()
    for r, vec in todo:
        collection = _collection_name(r['agent_id'])
        if collection not in seen:
            store.delete_collection(collection)      # 旧维度集合不可复用
            store.create_collection(collection, vector_size=dim)
            seen.add(collection)
        from engine.agent_memory import _point_id
        store.upsert(
            collection=collection,
            vectors=[vec],
            payloads=[{
                'memory_id': r['id'],
                'agent_id': str(r['agent_id']),
                'content': (r['content'] or '')[:500],
                'model': 'text-embedding-v3',
            }],
            ids=[_point_id(r['id'])],
        )
        if r['embedding_status'] != 'completed':
            _persist_embedding(r['id'], r['agent_id'], vec, r['content'] or '')
    print(f'  已写入 {len(todo)} 条记忆向量，覆盖集合 {len(seen)} 个: {sorted(seen)}')
    return len(todo)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    dim, model = _current_dim()
    if not dim:
        print('未检测到可用的 embedding 模型配置，终止。')
        return 1
    print(f'当前 embedding 模型 = {model}，维度 = {dim}')
    print(f'向量后端 = {get_vector_store().backend}')
    print('-' * 60)
    reindex_segments(dim, args.dry_run)
    print('-' * 60)
    reindex_memories(dim, args.dry_run)
    return 0


if __name__ == '__main__':
    sys.exit(main())
