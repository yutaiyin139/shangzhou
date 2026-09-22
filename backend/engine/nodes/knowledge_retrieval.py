# -*- coding: utf-8 -*-
"""
知识检索节点执行模块

负责执行知识库检索节点（knowledge-retrieval），支持：
- 向量搜索（vector_search / hybrid_search）
- 关键词搜索（jieba 分词索引 + LIKE 回退）
- 元数据过滤（metadata_filters）
- 外部知识 API 检索结果合并
- 结构化引用追踪（retriever_resources）
"""

import logging

from config import get_db


def _resolve_selector(context, selector):
    """解析变量选择器，从上下文中获取值"""
    if not selector or not isinstance(selector, list):
        return ''
    # selector 格式: ["node_id", "variable_name"]
    if len(selector) >= 2:
        node_id = selector[0]
        var_name = selector[1]
        node_output = context.get(node_id, {})
        if isinstance(node_output, dict):
            return node_output.get(var_name, '')
    return ''


def _node_knowledge_retrieval(data, context, model_cfg=None):
    """知识检索节点（支持向量搜索和混合搜索，支持元数据过滤）"""
    dataset_ids = data.get('dataset_ids', [])
    # 支持 query_variable_selector 或直接使用 query
    query_selector = data.get('query_variable_selector', [])
    if query_selector:
        query = _resolve_selector(context, query_selector) if query_selector else ''
    else:
        query = context.get('query', '')

    if not dataset_ids or not query:
        return {'result': '', 'context': '', 'sources': []}

    # 获取检索配置
    top_k = data.get('top_k', 5)
    min_score = data.get('min_score', 0.0)
    search_type = data.get('search_type', 'auto')  # auto, vector, keyword, hybrid
    metadata_filters = data.get('metadata_filters', [])  # [{name, value, operator}]

    results = []

    # 尝试向量搜索
    if search_type in ('auto', 'vector', 'hybrid'):
        try:
            from engine.embedding_service import vector_search, hybrid_search
            if search_type == 'hybrid':
                results = hybrid_search(query, dataset_ids, top_k=top_k, min_score=min_score)
            else:
                results = vector_search(query, dataset_ids, top_k=top_k, min_score=min_score)
        except Exception:
            results = []

    # 向量搜索没有结果，回退到关键词搜索
    if not results and search_type in ('auto', 'keyword'):
        results = _keyword_search(query, dataset_ids, top_k)

    # 补充 document_name（用于引用追踪展示）
    if results:
        try:
            seg_ids = [r['id'] for r in results if not r.get('is_external')]
            if seg_ids:
                db = get_db()
                cur = db.cursor()
                fmt = ','.join(['%s'] * len(seg_ids))
                cur.execute(
                    f'SELECT s.id AS seg_id, s.dataset_id, s.document_id, d.name AS doc_name'
                    f' FROM dify_document_segments s'
                    f' LEFT JOIN dify_documents d ON s.document_id = d.id'
                    f' WHERE s.id IN ({fmt})', seg_ids)
                info_map = {r['seg_id']: r for r in cur.fetchall()}
                db.close()
                for r in results:
                    info = info_map.get(r['id'], {})
                    r['dataset_id'] = info.get('dataset_id', r.get('dataset_id', ''))
                    r['document_id'] = info.get('document_id', r.get('document_id', ''))
                    r['document_name'] = info.get('doc_name', '')
        except Exception:
            pass

    # 外部知识 API 检索（3.3: 外部 API 结果并入召回）
    external_results = []
    try:
        from engine.external_knowledge import retrieve_external_knowledge
        ext_results, ext_errors = retrieve_external_knowledge(dataset_ids, query, top_k=top_k)
        external_results = ext_results
        if ext_errors:
            logging.getLogger(__name__).warning(f'[外部知识API] 检索警告: {ext_errors}')
    except Exception:
        pass

    # 合并本地和外部结果
    if external_results:
        results = results + external_results
        # 按分数排序
        results.sort(key=lambda x: -x.get('score', 0))

    if not results:
        return {'result': '', 'context': '', 'sources': []}

    # 元数据过滤（2.3: 下推到 SQL 过滤）
    if metadata_filters:
        try:
            from engine.metadata_engine import filter_segments_by_metadata
            for ds_id in dataset_ids:
                seg_ids = [r['id'] for r in results]
                filtered = filter_segments_by_metadata(ds_id, seg_ids, metadata_filters)
                results = [r for r in results if r['id'] in set(filtered)]
        except Exception:
            pass  # 过滤失败不阻塞检索

    if not results:
        return {'result': '', 'context': '', 'sources': []}

    # 更新命中计数
    db = get_db()
    try:
        cur = db.cursor()
        for r in results:
            cur.execute('''
                UPDATE dify_document_segments
                SET hit_count = hit_count + 1
                WHERE id = %s
            ''', (r['id'],))
        db.commit()
    finally:
        db.close()

    # 构建结果（含结构化引用）
    content_parts = []
    sources = []
    retriever_resources = []  # 3.1: 结构化引用追踪
    for idx, r in enumerate(results):
        content_parts.append(r.get('content', ''))
        sources.append({
            'id': r['id'],
            'score': r.get('score', 0),
            'content': r.get('content', '')[:200],  # 摘要
        })
        retriever_resources.append({
            'segment_id': r['id'],
            'dataset_id': r.get('dataset_id', ''),
            'document_id': r.get('document_id', ''),
            'document_name': r.get('document_name', ''),
            'content': r.get('content', '')[:500],
            'score': r.get('score', 0),
            'position': idx,
        })

    result = '\n\n'.join(content_parts)
    return {
        'result': result,
        'context': result,
        'sources': sources,
        'retriever_resources': retriever_resources,
        'result_count': len(results),
    }


def _keyword_search(query, dataset_ids, top_k=5):
    """
    关键词搜索（优先使用 jieba 分词索引，回退到 LIKE 模糊匹配）。

    参数:
        query: 查询文本
        dataset_ids: 数据集 ID 列表
        top_k: 返回结果数

    返回:
        结果列表 [{id, content, score, dataset_id, document_id}]
    """
    # 优先使用 keyword_engine（jieba 分词索引）
    try:
        from engine.keyword_engine import keyword_search as _kw_search
        merged = {}
        for ds_id in dataset_ids:
            kw_results = _kw_search(ds_id, query, top_k=top_k)
            for r in kw_results:
                seg_id = r['segment_id']
                if seg_id not in merged or r['score'] > merged[seg_id]['score']:
                    merged[seg_id] = {
                        'id': seg_id,
                        'score': r['score'],
                        'dataset_id': ds_id,
                        'document_id': '',
                        'content': '',
                    }
        if merged:
            # 补充 content 和 document_id
            seg_ids = list(merged.keys())
            db = get_db()
            try:
                cur = db.cursor()
                fmt = ','.join(['%s'] * len(seg_ids))
                cur.execute(
                    f'SELECT id, content, dataset_id, document_id'
                    f' FROM dify_document_segments'
                    f' WHERE id IN ({fmt})', seg_ids)
                info_map = {r['id']: r for r in cur.fetchall()}
                for seg_id, info in merged.items():
                    if seg_id in info_map:
                        info['content'] = info_map[seg_id]['content']
                        info['dataset_id'] = info_map[seg_id]['dataset_id']
                        info['document_id'] = info_map[seg_id]['document_id']
            finally:
                db.close()
            results = sorted(merged.values(), key=lambda x: -x['score'])[:top_k]
            # 过滤掉空 content
            results = [r for r in results if r['content']]
            if results:
                return results
    except Exception:
        pass  # keyword_engine 不可用时回退到 LIKE

    # 回退：LIKE 模糊匹配
    db = get_db()
    try:
        cur = db.cursor()
        placeholders = ','.join(['%s'] * len(dataset_ids))

        # 构建 LIKE 条件
        keywords = [w for w in query.split() if len(w) > 1]
        if not keywords:
            keywords = [query]

        like_conditions = []
        like_params = []
        for kw in keywords:
            like_conditions.append('content LIKE %s')
            like_params.append(f'%{kw}%')

        sql = f'''
            SELECT id, dataset_id, document_id, content,
                   ({' + '.join(['(LENGTH(content) - LENGTH(REPLACE(LOWER(content), LOWER(%s), \'\'))) / LENGTH(%s)' for _ in keywords])})
                   AS relevance
            FROM dify_document_segments
            WHERE dataset_id IN ({placeholders})
              AND enabled = 1
              AND status = 'completed'
              AND ({' OR '.join(like_conditions)})
            ORDER BY relevance DESC, hit_count DESC
            LIMIT {top_k}
        '''

        # 构建参数列表
        params = []
        for kw in keywords:
            params.extend([kw, kw])
        params.extend(dataset_ids)
        params.extend(like_params)

        cur.execute(sql, params)
        rows = cur.fetchall()
    except Exception:
        # 如果复杂查询失败，使用简单查询
        try:
            cur.execute(f'''
                SELECT id, dataset_id, document_id, content, 1 AS relevance
                FROM dify_document_segments
                WHERE dataset_id IN ({placeholders})
                  AND enabled = 1
                  AND status = 'completed'
                ORDER BY hit_count DESC
                LIMIT {top_k}
            ''', dataset_ids)
            rows = cur.fetchall()
        except Exception:
            rows = []
    finally:
        db.close()

    results = []
    for row in rows:
        results.append({
            'id': row['id'],
            'content': row['content'],
            'score': 0.5,  # 关键词搜索默认分数
            'dataset_id': row.get('dataset_id', ''),
            'document_id': row.get('document_id', ''),
        })
    return results
