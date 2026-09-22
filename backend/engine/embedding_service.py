# -*- coding: utf-8 -*-
"""
Embedding 服务模块 —— 向量嵌入与相似度搜索

功能：
1. 调用 Embedding API 生成文本向量
2. 存储和检索向量
3. 余弦相似度计算
4. 向量相似度搜索
"""
import json
import math
import urllib.request
import urllib.error
from config import get_db
from utils.llm import decrypt_api_key, build_openai_url

# 本地 embedding 维度（与常见轻量模型一致，便于后续替换为真实模型时平滑迁移）
EMBEDDING_DIM = 384


def ensure_model_configs_schema():
    """
    确保 model_configs 表包含 model_type 列（兼容旧表自动升级）。
    model_type 取值: 'llm' | 'embedding' | 'rerank' | 'tts' | 'stt' | ''
    """
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('SHOW COLUMNS FROM model_configs')
        cols = {r['Field'] for r in cur.fetchall()}
        if 'model_type' not in cols:
            cur.execute("ALTER TABLE model_configs ADD COLUMN model_type VARCHAR(20) DEFAULT ''")
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def get_embedding_config():
    """
    获取可用的 Embedding 模型配置
    优先查找专门配置为 embedding 类型的模型，否则使用默认模型
    """
    # 确保 schema 已升级（model_type 列可能不存在）
    ensure_model_configs_schema()
    db = get_db()
    try:
        cur = db.cursor()
        # 优先查找 embedding 类型的模型配置
        cur.execute('''
            SELECT * FROM model_configs
            WHERE status = 1 AND model_type = 'embedding'
            ORDER BY updated_at DESC LIMIT 1
        ''')
        cfg = cur.fetchone()
        if not cfg:
            # 如果没有专门的 embedding 模型，使用默认模型
            cur.execute('''
                SELECT * FROM model_configs
                WHERE status = 1
                ORDER BY updated_at DESC LIMIT 1
            ''')
            cfg = cur.fetchone()
        return cfg
    finally:
        db.close()


def get_embedding(text, model_name=None, api_key=None, base_url=None):
    """
    调用 Embedding API 生成文本向量。

    策略:
        1. 优先调用配置的远端 Embedding API（OpenAI 兼容 /v1/embeddings）
        2. 若远端不可用（未配置 / 404 / 网络错误），自动降级到本地 embedding
           （基于字符 n-gram 的确定性哈希向量，离线可用，用于开发/演示）

    参数:
        text: 要嵌入的文本
        model_name: 模型名称（可选，默认使用配置中的模型）
        api_key: API Key（可选）
        base_url: API Base URL（可选）

    返回:
        list: 向量（浮点数列表）
    """
    if not text or not text.strip():
        return []

    # 尝试远端 API
    remote = _try_remote_embedding(text, model_name=model_name, api_key=api_key, base_url=base_url)
    if remote is not None:
        return remote

    # 降级到本地 embedding
    return _local_embedding(text)


def _try_remote_embedding(text, model_name=None, api_key=None, base_url=None):
    """尝试远端 Embedding API，失败返回 None"""
    try:
        # 获取配置
        cfg = None
        if not api_key or not base_url:
            cfg = get_embedding_config()
            if not cfg:
                return None
            api_key = decrypt_api_key(cfg['api_key'])
            base_url = (cfg['api_base_url'] or '').rstrip('/')
            if not model_name:
                model_name = cfg['model_name'] or cfg['credential_name'] or cfg['provider']

        if not model_name:
            model_name = 'text-embedding-3-small'

        payload = json.dumps({
            'model': model_name,
            'input': text[:8000],
        }).encode('utf-8')

        req = urllib.request.Request(
            build_openai_url(base_url, 'embeddings'),
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + api_key
            },
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode('utf-8'))

        if 'data' in result and result['data']:
            return result['data'][0].get('embedding', [])
        return None
    except Exception:
        return None


def _local_embedding(text, dim=EMBEDDING_DIM):
    """
    本地 Embedding（字符 n-gram 哈希向量）。

    离线可用、确定性输出，用于开发/演示环境。
    远端 Embedding API 不可用时自动降级。
    生产环境建议配置专用 embedding 模型（如 OpenAI text-embedding-3-small、
    BGE、M3E 等）以获得更好的语义表征。
    """
    import hashlib
    vec = [0.0] * dim
    # 多粒度字符 n-gram（适配中英文混合）
    for n in (1, 2, 3):
        for i in range(len(text) - n + 1):
            gram = text[i:i + n]
            h = hashlib.md5(gram.encode('utf-8')).hexdigest()
            # 用哈希的前 8 位决定维度索引，后 4 位决定符号
            idx = int(h[:8], 16) % dim
            sign = 1.0 if int(h[8:12], 16) % 2 == 0 else -1.0
            vec[idx] += sign
    # L2 归一化
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


def get_embeddings_batch(texts, model_name=None, api_key=None, base_url=None):
    """
    批量生成文本向量。
    单条失败自动降级到本地 embedding，保证批量不中断。
    """
    if not texts:
        return []
    # 简单可靠路径：逐条生成（每条自带远端→本地降级）
    return [get_embedding(t, model_name=model_name, api_key=api_key, base_url=base_url) for t in texts]

    # 以下为远端批量路径（暂不启用，保留供后续优化）
    clean_texts = [t[:8000] for t in texts if t and t.strip()]
    if not clean_texts:
        return []

    payload = json.dumps({
        'model': model_name,
        'input': clean_texts,
    }).encode('utf-8')

    req = urllib.request.Request(
        build_openai_url(base_url, 'embeddings'),
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + api_key
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='replace')
        raise Exception(f'Embedding API 调用失败: {e.code} {error_body}')
    except Exception as e:
        raise Exception(f'Embedding API 调用失败: {str(e)}')

    # 提取向量
    embeddings = []
    if 'data' in result:
        # 按原始顺序排序
        data_sorted = sorted(result['data'], key=lambda x: x.get('index', 0))
        embeddings = [item.get('embedding', []) for item in data_sorted]

    return embeddings


def cosine_similarity(vec1, vec2):
    """
    计算两个向量的余弦相似度

    参数:
        vec1: 向量1
        vec2: 向量2

    返回:
        float: 相似度（-1 到 1）
    """
    if not vec1 or not vec2:
        return 0.0
    if len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


def store_embedding(segment_id, embedding, model_name=None, dataset_id=None, content=None):
    """
    存储向量到数据库（MySQL + Qdrant 双写）

    参数:
        segment_id: 分段 ID
        embedding: 向量（列表）
        model_name: 使用的模型名称
        dataset_id: 数据集 ID（Qdrant 过滤用）
        content: 分段内容（Qdrant payload 用）
    """
    # 写入 MySQL（始终写入，作为持久化存储）
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('''
            UPDATE dify_document_segments
            SET embedding = %s, embedding_model = %s, embedding_status = 'completed'
            WHERE id = %s
        ''', (json.dumps(embedding), model_name, segment_id))
        db.commit()
    finally:
        db.close()

    # 写入 Qdrant（如果可用）
    try:
        from utils.vector_store import get_vector_store
        store = get_vector_store()
        if store.is_available and embedding:
            collection = _get_qdrant_collection_name(dataset_id)
            store.create_collection(collection, vector_size=len(embedding))
            store.upsert(
                collection=collection,
                vectors=[embedding],
                payloads=[{
                    'segment_id': segment_id,
                    'dataset_id': dataset_id or '',
                    'content': (content or '')[:500],  # 摘要
                    'embedding_model': model_name or '',
                }],
                ids=[segment_id]
            )
    except Exception:
        pass  # Qdrant 写入失败不影响主流程


def _get_qdrant_collection_name(dataset_id=None):
    """获取 Qdrant 集合名称"""
    if dataset_id:
        return f'knowledge_{dataset_id.replace("-", "_")}'
    return 'knowledge_default'


def get_segments_with_embeddings(dataset_ids, limit=100):
    """
    获取有向量的分段

    参数:
        dataset_ids: 数据集 ID 列表
        limit: 返回数量限制

    返回:
        list: 分段列表（包含 embedding）
    """
    if not dataset_ids:
        return []

    db = get_db()
    try:
        cur = db.cursor()
        placeholders = ','.join(['%s'] * len(dataset_ids))
        cur.execute(f'''
            SELECT id, content, embedding, embedding_model
            FROM dify_document_segments
            WHERE dataset_id IN ({placeholders})
              AND enabled = 1
              AND status = 'completed'
              AND embedding IS NOT NULL
              AND embedding_status = 'completed'
            LIMIT {limit}
        ''', dataset_ids)
        rows = cur.fetchall()
    finally:
        db.close()

    results = []
    for row in rows:
        try:
            embedding = json.loads(row['embedding']) if row['embedding'] else []
        except (json.JSONDecodeError, TypeError):
            embedding = []
        if embedding:
            results.append({
                'id': row['id'],
                'content': row['content'],
                'embedding': embedding,
                'embedding_model': row['embedding_model'],
            })
    return results


def vector_search(query, dataset_ids, top_k=5, min_score=0.0):
    """
    向量相似度搜索（优先使用 Qdrant，回退到 MySQL 内存计算）

    参数:
        query: 查询文本
        dataset_ids: 数据集 ID 列表
        top_k: 返回前 K 个结果
        min_score: 最低相似度阈值

    返回:
        list: 相似分段列表，按相似度降序
    """
    if not query or not dataset_ids:
        return []

    # 生成查询向量
    try:
        query_embedding = get_embedding(query)
    except Exception as e:
        # Embedding 失败，返回空结果
        return []

    if not query_embedding:
        return []

    # 尝试使用 Qdrant 搜索
    try:
        from utils.vector_store import get_vector_store
        store = get_vector_store()
        if store.is_available:
            collection = _get_qdrant_collection_name(dataset_ids[0] if dataset_ids else None)
            # 检查集合是否存在
            if collection in store.list_collections():
                filter_conditions = None
                if len(dataset_ids) == 1:
                    filter_conditions = {'dataset_id': dataset_ids[0]}
                elif len(dataset_ids) > 1:
                    filter_conditions = {'dataset_id': dataset_ids}

                qdrant_results = store.search(
                    collection=collection,
                    query_vector=query_embedding,
                    limit=top_k,
                    min_score=min_score,
                    filter_conditions=filter_conditions,
                )
                if qdrant_results:
                    return [
                        {
                            'id': r['payload'].get('segment_id', r['id']),
                            'content': r['payload'].get('content', ''),
                            'score': r['score'],
                        }
                        for r in qdrant_results
                    ]
    except Exception:
        pass  # Qdrant 失败，回退到 MySQL

    # 回退：MySQL 内存余弦相似度搜索
    segments = get_segments_with_embeddings(dataset_ids, limit=500)
    if not segments:
        return []

    # 确保向量维度一致
    dim = len(query_embedding)
    results = []
    for seg in segments:
        seg_embedding = seg.get('embedding', [])
        if len(seg_embedding) != dim:
            continue
        score = cosine_similarity(query_embedding, seg_embedding)
        if score >= min_score:
            results.append({
                'id': seg['id'],
                'content': seg['content'],
                'score': score,
                'dataset_id': seg.get('dataset_id', ''),
                'document_id': seg.get('document_id', ''),
            })

    # 按相似度降序排序
    results.sort(key=lambda x: x['score'], reverse=True)

    return results[:top_k]


def generate_missing_embeddings(dataset_id=None, batch_size=20):
    """
    为没有向量的分段生成 Embedding（同时写入 MySQL 和 Qdrant）

    参数:
        dataset_id: 数据集 ID（可选，为 None 则处理所有）
        batch_size: 每批处理数量

    返回:
        int: 处理的分段数量
    """
    db = get_db()
    try:
        cur = db.cursor()
        if dataset_id:
            cur.execute('''
                SELECT id, content, dataset_id FROM dify_document_segments
                WHERE dataset_id = %s
                  AND enabled = 1
                  AND status = 'completed'
                  AND (embedding IS NULL OR embedding_status = 'pending')
                LIMIT %s
            ''', (dataset_id, batch_size))
        else:
            cur.execute('''
                SELECT id, content, dataset_id FROM dify_document_segments
                WHERE enabled = 1
                  AND status = 'completed'
                  AND (embedding IS NULL OR embedding_status = 'pending')
                LIMIT %s
            ''', (batch_size,))
        rows = cur.fetchall()
    finally:
        db.close()

    if not rows:
        return 0

    # 获取模型配置
    cfg = get_embedding_config()
    if not cfg:
        return 0

    model_name = cfg['model_name'] or cfg['credential_name'] or cfg['provider']
    api_key = decrypt_api_key(cfg['api_key'])
    base_url = (cfg['api_base_url'] or '').rstrip('/')

    # 批量生成向量
    texts = [row['content'] for row in rows if row['content']]
    if not texts:
        return 0

    try:
        embeddings = get_embeddings_batch(texts, model_name, api_key, base_url)
    except Exception:
        return 0

    # 存储向量（MySQL + Qdrant）
    count = 0
    for i, row in enumerate(rows):
        if i < len(embeddings) and embeddings[i]:
            store_embedding(
                segment_id=row['id'],
                embedding=embeddings[i],
                model_name=model_name,
                # 必须用分段自身的 dataset_id：全部扫入时入参 dataset_id 为 None，
                # 若直接透传会把所有知识库向量堆进 knowledge_default，破坏按数据集隔离的检索
                dataset_id=row.get('dataset_id') or dataset_id,
                content=row['content'],
            )
            count += 1

    return count


def hybrid_search(query, dataset_ids, top_k=5, min_score=0.0, text_weight=0.3):
    """
    混合搜索：结合向量相似度和关键词匹配

    参数:
        query: 查询文本
        dataset_ids: 数据集 ID 列表
        top_k: 返回前 K 个结果
        min_score: 最低相似度阈值
        text_weight: 关键词匹配权重（0-1）

    返回:
        list: 相似分段列表
    """
    # 向量搜索结果
    vector_results = vector_search(query, dataset_ids, top_k * 2, min_score)

    if text_weight == 0 or not vector_results:
        return vector_results[:top_k]

    # 关键词匹配（简单实现：检查查询词是否出现在内容中）
    query_words = set(query.lower().split())

    for result in vector_results:
        content = (result.get('content') or '').lower()
        # 计算关键词匹配分数
        match_count = sum(1 for word in query_words if word in content)
        text_score = match_count / max(len(query_words), 1)
        # 混合分数
        result['score'] = result['score'] * (1 - text_weight) + text_score * text_weight
        result['text_score'] = text_score

    # 重新排序
    vector_results.sort(key=lambda x: x['score'], reverse=True)
    return vector_results[:top_k]
