# -*- coding: utf-8 -*-
"""
Rerank 重排序模块。

对检索结果进行语义重排序，提升检索精度。

优先级：
1. 若配置了本地 BGE-Reranker 模型 → 使用本地模型（sentence-transformers）
2. 若配置了支持 rerank 的 API（如 Jina/cohere）→ 调用 API
3. 否则 → 使用 embedding 余弦相似度重排序（利用已有 embedding_service）
4. 最终回退 → 保持原始排序
"""


def rerank_segments(query, segments, top_k=None, model_cfg=None):
    """
    对检索结果进行语义重排序。

    参数:
    - query: 查询文本
    - segments: 分段列表 [{content, ...}]
    - top_k: 返回前 K 个结果
    - model_cfg: 模型配置

    返回: 重排序后的分段列表
    """
    if not segments:
        return segments

    # 尝试本地 rerank 模型
    local_score = _rerank_local(query, segments)
    if local_score is not None:
        return _sort_by_score(segments, local_score, top_k)

    # 尝试 API rerank
    api_score = _rerank_api(query, segments, model_cfg)
    if api_score is not None:
        return _sort_by_score(segments, api_score, top_k)

    # 使用 embedding 余弦相似度（已有基础设施）
    embedding_score = _rerank_embedding(query, segments)
    if embedding_score is not None:
        return _sort_by_score(segments, embedding_score, top_k)

    # 最终回退：保持原始排序
    return segments[:top_k] if top_k else segments


def _rerank_local(query, segments):
    """
    使用本地 rerank 模型（如 BGE-Reranker）计算相关性分数。

    需要安装: pip install sentence-transformers
    """
    try:
        from sentence_transformers import CrossEncoder
    except ImportError:
        return None

    try:
        # 使用轻量级 rerank 模型
        model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        pairs = [(query, seg.get('content', '')) for seg in segments]
        scores = model.predict(pairs)
        return scores.tolist() if hasattr(scores, 'tolist') else list(scores)
    except Exception:
        return None


def _rerank_api(query, segments, model_cfg=None):
    """
    使用支持 rerank 的 API（如 Jina/cohere）计算相关性分数。
    """
    import os
    import json

    # 检查是否有 rerank API 配置
    api_key = os.environ.get('RERANK_API_KEY', '')
    api_url = os.environ.get('RERANK_API_URL', 'https://api.jina.ai/v1/rerank')
    model_name = os.environ.get('RERANK_MODEL', 'jina-reranker-v1-base-en')

    if not api_key:
        return None

    try:
        import urllib.request

        documents = [seg.get('content', '') for seg in segments]
        payload = json.dumps({
            'model': model_name,
            'query': query,
            'documents': documents,
            'top_n': len(segments),
        }).encode('utf-8')

        req = urllib.request.Request(api_url, data=payload, headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
        })

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        # 提取分数
        results = data.get('results', [])
        if results:
            # 构建原始索引到分数的映射
            scores = [0.0] * len(segments)
            for r in results:
                idx = r.get('index', 0)
                score = r.get('relevance_score', 0.0)
                if 0 <= idx < len(scores):
                    scores[idx] = score
            return scores

    except Exception:
        pass

    return None


def _rerank_embedding(query, segments):
    """
    使用已有 embedding_service 计算余弦相似度。

    利用现有的 embedding 基础设施，无需新增依赖。
    """
    try:
        from engine.embedding_service import get_embedding, cosine_similarity
    except ImportError:
        return None

    try:
        query_vec = get_embedding(query)
        if query_vec is None:
            return None

        scores = []
        for seg in segments:
            content = seg.get('content', '')
            if not content:
                scores.append(0.0)
                continue
            seg_vec = get_embedding(content)
            if seg_vec is not None:
                scores.append(cosine_similarity(query_vec, seg_vec))
            else:
                scores.append(0.0)
        return scores
    except Exception:
        return None


def _sort_by_score(segments, scores, top_k=None):
    """
    根据分数对分段排序。

    参数:
    - segments: 分段列表
    - scores: 分数列表
    - top_k: 返回前 K 个结果

    返回: 排序后的分段列表
    """
    if len(segments) != len(scores):
        return segments[:top_k] if top_k else segments

    # 合并分数到分段
    scored_segments = []
    for i, seg in enumerate(segments):
        seg_copy = dict(seg) if isinstance(seg, dict) else {'content': str(seg)}
        seg_copy['rerank_score'] = scores[i]
        scored_segments.append(seg_copy)

    # 按分数降序排序
    scored_segments.sort(key=lambda x: x['rerank_score'], reverse=True)

    # 取 top_k
    if top_k and top_k > 0:
        return scored_segments[:top_k]
    return scored_segments
