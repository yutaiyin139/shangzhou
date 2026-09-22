# -*- coding: utf-8 -*-
"""
Agent 记忆向量化引擎 —— 把 Agent 长期记忆写入 Qdrant 并按 query 语义召回

职责:
    1. 记忆写入时同步生成 embedding，双写 MySQL + Qdrant（每个 agent 独立集合）
    2. 对话前按 query 检索 top-k 相关记忆，注入 system prompt
    3. 记忆删除/失效时同步清理 Qdrant 侧点

设计要点:
    - 集合命名: agent_memory:{agent_id}，按 agent 隔离，避免跨 agent 泄漏
    - embedding 模型复用 engine.embedding_service（OpenAI 兼容 / 自动选 embedding 模型）
    - 写入失败不阻塞主流程：MySQL 落库优先，embedding 失败标记 status='failed'，
      由后台任务重试（与 knowledge-index 的 generate_embeddings_async 同模式）
"""
import json
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Optional

from config import get_db

logger = logging.getLogger(__name__)

# 向量点 ID 派生命名空间：memory_id -> 稳定 point id（保证重复向量化为幂等更新）
_POINT_NAMESPACE = uuid.UUID('6f1d3c2e-8a54-4a7f-9c1b-2d5e7a90c3f1')


def _point_id(memory_id) -> str:
    """由 memory_id 派生稳定的向量 point ID（UUID 字符串，兼容 Qdrant 与 MySQL 后端）"""
    return str(uuid.uuid5(_POINT_NAMESPACE, f'memory:{memory_id}'))


# ============================================================
# 集合命名
# ============================================================

def _collection_name(agent_id) -> str:
    """每个 agent 一个 Qdrant 集合，隔离记忆。
    Qdrant 集合名不能含 ':'，用 '__' 代替。"""
    return f'agent_memory__{agent_id}'


def _ensure_vector_dim(collection: str, dim: int) -> bool:
    """维度漂移时要求重建集合（例如本地 384 维向量升级到通义 1024 维）。

    返回: True 表示集合可继续使用（维度一致或新建），False 表示应先删除旧集合。
    """
    # 1) Qdrant 后端：以服务端实际声明的维度为准
    try:
        from utils.vector_store import get_vector_store
        store = get_vector_store()
        if getattr(store, 'backend', '') == 'qdrant':
            declared = store.get_declared_dim(collection)
            if declared is not None and int(declared) != int(dim):
                logger.info('[agent_memory] 集合 %s 维度 %s -> %s，待重建',
                            collection, declared, dim)
                return False
            return True
    except Exception:
        logger.exception('[agent_memory] 集合维度检查异常 collection=%s', collection)

    # 2) MySQL 回退后端：向量存于 dify_document_segments，维度不一致的旧行检索时会被自然跳过，
    #    仅需保证 vector_collections 元数据记录为最新维度
    db = get_db()
    try:
        cur = db.cursor()
        try:
            cur.execute('SELECT vector_size FROM vector_collections WHERE name = %s', (collection,))
            row = cur.fetchone()
        except Exception:
            row = None  # 表尚不存在
        if row and row.get('vector_size') and int(row['vector_size']) != int(dim):
            cur.execute('UPDATE vector_collections SET vector_size = %s WHERE name = %s',
                        (dim, collection))
            db.commit()
            logger.info('[agent_memory] 集合 %s 维度记录 %s -> %s',
                        collection, row['vector_size'], dim)
    except Exception:
        db.rollback()
    finally:
        db.close()
    return True


def ensure_memories_schema():
    """
    确保 memories 表包含向量化字段（兼容旧表自动升级）。
    在注册路由时调用一次。
    """
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('SHOW COLUMNS FROM memories')
        cols = {r['Field'] for r in cur.fetchall()}
        needed = {
            'embedding': 'JSON',
            'embedding_model': "VARCHAR(100) DEFAULT ''",
            'embedding_status': "VARCHAR(20) DEFAULT 'pending'",
        }
        for col, typ in needed.items():
            if col not in cols:
                cur.execute(f'ALTER TABLE memories ADD COLUMN {col} {typ}')
        # 索引
        cur.execute("SHOW INDEX FROM memories WHERE Key_name = 'idx_agent_id'")
        if not cur.fetchone():
            cur.execute('ALTER TABLE memories ADD INDEX idx_agent_id (agent_id)')
        cur.execute("SHOW INDEX FROM memories WHERE Key_name = 'idx_embedding_status'")
        if not cur.fetchone():
            cur.execute('ALTER TABLE memories ADD INDEX idx_embedding_status (embedding_status)')
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


# ============================================================
# 写入
# ============================================================

def add_memory(agent_id, content: str, account_id: str = '') -> Optional[Dict]:
    """
    写入一条 Agent 记忆。
    同步落库 MySQL，异步（Celery）生成 embedding 并写入 Qdrant。
    返回记忆行（dict）；失败返回 None。
    """
    if not (content or '').strip():
        return None
    content = content.strip()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            'INSERT INTO memories (agent_id, content, embedding_status, created_at, updated_at)'
            ' VALUES (%s, %s, %s, %s, %s)',
            (agent_id, content, 'pending', now, now))
        db.commit()
        memory_id = cur.lastrowid
    except Exception:
        db.rollback()
        return None
    finally:
        db.close()

    # 异步向量化（失败不阻塞返回）
    _queue_embedding(memory_id, agent_id, content)

    return {
        'id': memory_id,
        'agent_id': agent_id,
        'content': content,
        'embedding_status': 'pending',
        'created_at': now,
    }


def add_memories_bulk(agent_id, contents: List[str], account_id: str = '') -> int:
    """批量写入记忆，返回成功写入条数"""
    n = 0
    for c in contents:
        if c and c.strip() and add_memory(agent_id, c.strip(), account_id):
            n += 1
    return n


def _queue_embedding(memory_id, agent_id, content):
    """投递 Celery 异步 embedding 任务"""
    try:
        from tasks.embedding_tasks import embed_agent_memory
        embed_agent_memory.delay(memory_id=memory_id, agent_id=agent_id, content=content)
    except Exception:
        # Celery 不可用时，退化为同步生成
        _embed_sync(memory_id, agent_id, content)


def _embed_sync(memory_id, agent_id, content):
    """同步生成 embedding（降级路径）"""
    try:
        from engine.embedding_service import get_embedding
        vector = get_embedding(content)
        if vector:
            _persist_embedding(memory_id, agent_id, vector, content)
        else:
            _mark_failed(memory_id, 'embedding 返回空向量')
    except Exception as exc:
        logger.exception('[agent_memory] 同步向量化失败 memory_id=%s', memory_id)
        _mark_failed(memory_id, f'同步向量化异常: {exc}')


def embed_memory(memory_id, agent_id, content):
    """
    Celery 任务入口：生成 embedding 并写入 Qdrant + 更新 MySQL。
    （tasks.embedding_tasks.embed_agent_memory 调用本函数）
    """
    try:
        from engine.embedding_service import get_embedding
        vector = get_embedding(content)
        if not vector:
            _mark_failed(memory_id, 'embedding 返回空向量')
            return False
        _persist_embedding(memory_id, agent_id, vector, content)
        return True
    except Exception as exc:
        logger.exception('[agent_memory] 向量化失败 memory_id=%s agent_id=%s', memory_id, agent_id)
        _mark_failed(memory_id, f'向量化异常: {exc}')
        return False


def _persist_embedding(memory_id, agent_id, vector, content):
    """双写：MySQL 存向量 + 向量库存点（point ID 稳定，重复向量化为幂等更新）"""
    model = _current_embedding_model()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            'UPDATE memories SET embedding = %s, embedding_model = %s, embedding_status = %s, updated_at = %s'
            ' WHERE id = %s',
            (json.dumps(vector), model, 'completed',
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'), memory_id))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

    # 写向量库（point ID 必须为 UUID 格式，不能是整数）
    try:
        from utils.vector_store import get_vector_store
        store = get_vector_store()
        collection = _collection_name(agent_id)
        # 维度变化（如 384 本地向量 -> 1024 通义向量）时先重建集合，避免 upsert 静默失败
        if not _ensure_vector_dim(collection, len(vector)):
            store.delete_collection(collection)
        store.create_collection(collection, vector_size=len(vector))
        store.upsert(
            collection=collection,
            vectors=[vector],
            payloads=[{
                'memory_id': memory_id,
                'agent_id': str(agent_id),
                'content': content[:500],
                'model': model,
            }],
            ids=[_point_id(memory_id)],
        )
    except Exception:
        logger.exception('[agent_memory] 向量库写入失败 memory_id=%s（MySQL 状态已提交）', memory_id)


def _mark_failed(memory_id, error: str = ''):
    if error:
        logger.warning('[agent_memory] memory_id=%s 向量化失败: %s', memory_id, error[:300])
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            "UPDATE memories SET embedding_status = 'failed', updated_at = %s WHERE id = %s",
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), memory_id))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _current_embedding_model() -> str:
    try:
        from engine.embedding_service import get_embedding_config
        cfg = get_embedding_config()
        if cfg:
            return cfg.get('model_name') or cfg.get('credential_name') or cfg.get('provider') or ''
    except Exception:
        pass
    return ''


# ============================================================
# 检索
# ============================================================

def search_memories(agent_id, query: str, limit: int = 5, min_score: float = 0.0) -> List[Dict]:
    """
    按 query 语义检索 agent 的记忆。
    返回: [{id, agent_id, content, score, embedding_status}, ...] 按 score 降序
    """
    if not (query or '').strip():
        return []
    query = query.strip()

    # 生成 query 向量
    try:
        from engine.embedding_service import get_embedding
        vector = get_embedding(query)
    except Exception:
        vector = []
    if not vector:
        return []

    from utils.vector_store import get_vector_store
    store = get_vector_store()

    # Qdrant 不可用（向量存储回退到 MySQL）时，直接基于 memories.embedding 做余弦检索。
    # 回退存储的 upsert 只保留 content，会丢失 payload.memory_id，若仍走 store.search
    # 将命中无法回映射 → 检索恒为空。此处兜底保证记忆检索在两种后端下都可用。
    if store.backend != 'qdrant':
        return _search_memories_local(agent_id, vector, limit, min_score)

    # Qdrant 检索
    try:
        hits = store.search(
            collection=_collection_name(agent_id),
            query_vector=vector,
            limit=limit,
            min_score=min_score)
    except Exception:
        hits = []

    # 命中结果回查 MySQL 拿完整 content（Qdrant point ID 为 UUID，
    # 真实 memory_id 存在 payload.memory_id 里）
    memory_ids = []
    score_map = {}
    for h in hits:
        mid = h.get('payload', {}).get('memory_id')
        if mid is not None:
            try:
                mid = int(mid)
            except (TypeError, ValueError):
                continue
            memory_ids.append(mid)
            score_map[mid] = h['score']
    # Qdrant 命中但无法回映射 memory_id（如向量点由回退期写入）→ 本地余弦兜底
    if not memory_ids:
        return _search_memories_local(agent_id, vector, limit, min_score)
    rows = _fetch_memories_by_ids(memory_ids)
    content_map = {r['id']: r for r in rows}

    results = []
    for mid in memory_ids:
        row = content_map.get(mid)
        if not row:
            continue
        results.append({
            'id': row['id'],
            'agent_id': row['agent_id'],
            'content': row['content'],
            'embedding_status': row['embedding_status'],
            'score': round(score_map.get(mid, 0.0), 4),
        })
    results.sort(key=lambda x: x['score'], reverse=True)
    return results


def _search_memories_local(agent_id, query_vector, limit: int = 5, min_score: float = 0.0) -> List[Dict]:
    """MySQL 直检回退：基于 memories.embedding(JSON) 做余弦相似度排序检索。
    用于 Qdrant 后端不可用（store.backend != 'qdrant'）或命中无法回映射 memory_id 时。"""
    from engine.embedding_service import cosine_similarity
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            "SELECT id, agent_id, content, embedding_status, embedding FROM memories"
            " WHERE agent_id = %s AND embedding_status = 'completed' AND embedding IS NOT NULL",
            (agent_id,))
        rows = cur.fetchall()
    finally:
        db.close()
    scored = []
    for r in rows:
        try:
            emb = json.loads(r['embedding']) if r['embedding'] else None
        except (TypeError, ValueError):
            emb = None
        if not emb:
            continue
        score = cosine_similarity(query_vector, emb)
        if score < min_score:
            continue
        scored.append({
            'id': r['id'],
            'agent_id': r['agent_id'],
            'content': r['content'],
            'embedding_status': r['embedding_status'],
            'score': round(score, 4),
        })
    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored[:limit]


def build_memory_context(agent_id, query: str, limit: int = 5, min_score: float = 0.2) -> str:
    """
    检索记忆并拼成 system prompt 片段。
    无命中时返回空字符串，避免污染 prompt。
    """
    hits = search_memories(agent_id, query, limit=limit, min_score=min_score)
    if not hits:
        return ''
    lines = ['# 用户长期记忆（供参考）']
    for i, h in enumerate(hits, 1):
        lines.append(f'{i}. {h["content"]}')
    return '\n'.join(lines)


# ============================================================
# CRUD
# ============================================================

def list_memories(agent_id, page: int = 1, page_size: int = 20,
                  status: str = '') -> Dict:
    """分页列出 agent 的记忆"""
    where = ['agent_id = %s']
    params = [agent_id]
    if status:
        where.append('embedding_status = %s')
        params.append(status)
    where_sql = 'WHERE ' + ' AND '.join(where)
    offset = (page - 1) * page_size

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('SELECT COUNT(*) c FROM memories ' + where_sql, params)
        total = cur.fetchone()['c']
        cur.execute(
            'SELECT * FROM memories ' + where_sql +
            ' ORDER BY id DESC LIMIT %s OFFSET %s',
            params + [page_size, offset])
        items = [dict(r) for r in cur.fetchall()]
        # 不返回原始 embedding 向量（节省带宽）
        for it in items:
            it.pop('embedding', None)
        return {'items': items, 'total': total, 'page': page, 'page_size': page_size}
    finally:
        db.close()


def get_memory(memory_id, agent_id=None) -> Optional[Dict]:
    db = get_db()
    try:
        cur = db.cursor()
        if agent_id is not None:
            cur.execute('SELECT * FROM memories WHERE id = %s AND agent_id = %s', (memory_id, agent_id))
        else:
            cur.execute('SELECT * FROM memories WHERE id = %s', (memory_id,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d.pop('embedding', None)
        return d
    finally:
        db.close()


def update_memory(memory_id, agent_id, content: str) -> bool:
    """更新记忆内容，重置 embedding 为 pending 并重新向量化"""
    if not (content or '').strip():
        return False
    content = content.strip()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            'UPDATE memories SET content = %s, embedding_status = %s, updated_at = %s'
            ' WHERE id = %s AND agent_id = %s',
            (content, 'pending', now, memory_id, agent_id))
        db.commit()
        if cur.rowcount == 0:
            return False
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()
    _queue_embedding(memory_id, agent_id, content)
    return True


def delete_memory(memory_id, agent_id) -> bool:
    """删除记忆（MySQL + Qdrant 同步清理）"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('DELETE FROM memories WHERE id = %s AND agent_id = %s', (memory_id, agent_id))
        db.commit()
        if cur.rowcount == 0:
            return False
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()
    # 同步清理向量库侧
    _delete_vector_points(agent_id, [memory_id])
    return True


def _delete_vector_points(agent_id, memory_ids):
    """清理记忆对应的向量点：Qdrant 按 payload 过滤删，MySQL 后端按稳定 point ID 删。"""
    memory_ids = [m for m in (memory_ids or []) if m is not None]
    if not memory_ids:
        return
    collection = _collection_name(agent_id)
    try:
        from utils.vector_store import get_vector_store
        store = get_vector_store()
    except Exception:
        logger.exception('[agent_memory] 无法加载向量存储，跳过清理 %s', collection)
        return

    if getattr(store, 'backend', '') == 'qdrant':
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            store.delete_points_by_filter(
                collection,
                Filter(should=[FieldCondition(key='memory_id', match=MatchValue(value=mid))
                               for mid in memory_ids]),
            )
        except Exception:
            logger.exception('[agent_memory] Qdrant 点清理失败 collection=%s', collection)
        return

    # MySQL 回退后端：向量点以 dify_document_segments 行存储，ID 由 memory_id 派生
    try:
        pid = [_point_id(m) for m in memory_ids]
        placeholders = ','.join(['%s'] * len(pid))
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(f'DELETE FROM dify_document_segments WHERE id IN ({placeholders})', pid)
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.exception('[agent_memory] MySQL 向量点清理失败 agent_id=%s', agent_id)


def delete_all_memories(agent_id) -> int:
    """清空 agent 的全部记忆"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('SELECT id FROM memories WHERE agent_id = %s', (agent_id,))
        memory_ids = [r['id'] for r in cur.fetchall()]
        cur.execute('DELETE FROM memories WHERE agent_id = %s', (agent_id,))
        db.commit()
        n = cur.rowcount
    except Exception:
        db.rollback()
        return 0
    finally:
        db.close()
    try:
        from utils.vector_store import get_vector_store
        store = get_vector_store()
        store.delete_collection(_collection_name(agent_id))
    except Exception:
        logger.exception('[agent_memory] 集合删除失败 agent_id=%s', agent_id)
    # MySQL 回退后端下 delete_collection 为空操作，需按稳定 point ID 清理残留向量行
    _delete_vector_points(agent_id, memory_ids)
    return n


def _fetch_memories_by_ids(ids: List[int]) -> List[Dict]:
    if not ids:
        return []
    db = get_db()
    try:
        cur = db.cursor()
        fmt = ','.join(['%s'] * len(ids))
        cur.execute(f'SELECT * FROM memories WHERE id IN ({fmt})', ids)
        return [dict(r) for r in cur.fetchall()]
    finally:
        db.close()


def retry_failed_embeddings(agent_id=None, limit: int = 50) -> int:
    """重试 embedding 失败的记忆（后台任务用）。返回重试条数"""
    db = get_db()
    try:
        cur = db.cursor()
        if agent_id is not None:
            cur.execute(
                "SELECT id, agent_id, content FROM memories"
                " WHERE agent_id = %s AND embedding_status IN ('pending','failed')"
                " ORDER BY id ASC LIMIT %s", (agent_id, limit))
        else:
            cur.execute(
                "SELECT id, agent_id, content FROM memories"
                " WHERE embedding_status IN ('pending','failed')"
                " ORDER BY id ASC LIMIT %s", (limit,))
        rows = cur.fetchall()
    finally:
        db.close()

    n = 0
    for r in rows:
        _queue_embedding(r['id'], r['agent_id'], r['content'])
        n += 1
    return n
