# -*- coding: utf-8 -*-
"""
知识索引节点引擎 —— 工作流 knowledge-index 节点的实际执行

把上游节点输出的文本写入指定知识库（数据集）：
    1. 创建文档行（dify_documents，data_source_type='workflow_index'）
    2. 复用 routes/knowledge.py 的分段器切分文本
    3. 写入分段（dify_document_segments，embedding_status='pending'）
    4. 投递 Celery 异步 Embedding 任务

节点数据结构（node.data）:
    dataset_id:        目标知识库 ID（必填）
    content_variable:  上游文本变量名（默认 'content'，先取该变量，取不到则取 'text'/'answer'）
    document_name:     生成的文档名（支持 {{变量}}，默认 节点标题 + 时间戳）
    max_length:        分段最大长度（默认 1024）
    overlap:           分段重叠（默认 50）
    delimiter:         分段分隔符（默认 \n）

输出变量:
    document_id / segment_count / word_count / knowledge_index_status
"""

import uuid
from datetime import datetime

from config import get_db


class KnowledgeIndexError(Exception):
    """知识索引失败"""


def _extract_text(data, context):
    """从上下文提取要索引的文本"""
    var = data.get('content_variable') or 'content'
    value = context.get(var)
    if value is None and var != 'content':
        value = context.get('content')
    if value is None:
        for fallback in ('text', 'answer', 'result'):
            if context.get(fallback) is not None:
                value = context[fallback]
                break
    if value is None:
        raise KnowledgeIndexError(
            f'上下文中未找到文本变量「{var}」（已尝试 content/text/answer/result）'
        )
    if isinstance(value, str):
        text = value
    elif isinstance(value, (list, tuple)):
        parts = []
        for it in value:
            if isinstance(it, dict):
                parts.append(it.get('content') or it.get('text') or str(it))
            else:
                parts.append(str(it))
        text = '\n'.join(parts)
    elif isinstance(value, dict):
        text = value.get('content') or value.get('text') or str(value)
    else:
        text = str(value)
    text = text.strip()
    if not text:
        raise KnowledgeIndexError('待索引文本为空')
    return text


def run_knowledge_index(data, context):
    """
    执行 knowledge-index 节点，返回输出变量字典（失败时 status='error'，不抛出）
    """
    import time
    start = time.time()

    dataset_id = (data.get('dataset_id') or '').strip()
    if not dataset_id:
        return _error('未配置目标知识库（dataset_id）', start)

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('SELECT id, tenant_id, name FROM dify_datasets WHERE id = %s', (dataset_id,))
        ds = cur.fetchone()
        if not ds:
            return _error(f'知识库 {dataset_id} 不存在', start)
        tenant_id = ds['tenant_id']
    finally:
        db.close()

    try:
        text = _extract_text(data, context)
    except KnowledgeIndexError as e:
        return _error(str(e), start)

    # 文档名（变量替换）
    name = data.get('document_name') or ''
    for k, v in context.items():
        if isinstance(v, str):
            name = name.replace('{{' + k + '}}', v)
    if not name.strip():
        name = f"{data.get('title', '工作流索引')} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    # 分段（复用知识库通用分段器）
    from routes.knowledge import _segment_text
    delimiter = data.get('delimiter') or '\n'
    max_length = int(data.get('max_length') or 1024)
    overlap = int(data.get('overlap') or 50)
    segments = _segment_text(text, delimiter=delimiter, max_length=max_length, overlap=overlap)
    if not segments:
        return _error('分段结果为空', start)

    doc_id = str(uuid.uuid4())
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    word_count = len(text)

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('''
            INSERT INTO dify_documents
            (id, tenant_id, dataset_id, position, data_source_type, data_source_info,
             name, created_from, created_by, indexing_status, enabled, word_count, created_at)
            VALUES (%s, %s, %s, 0, 'workflow_index', %s, %s, 'workflow', NULL, 'indexing', 1, %s, %s)
        ''', (doc_id, tenant_id, dataset_id,
              '{"source": "knowledge-index node"}', name[:255], word_count, now))

        for idx, seg_text in enumerate(segments):
            cur.execute('''
                INSERT INTO dify_document_segments
                (id, tenant_id, dataset_id, document_id, position, content, word_count,
                 enabled, status, embedding_status, segment_type, created_by, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 1, 'completed', 'pending', 'general', NULL, %s)
            ''', (str(uuid.uuid4()), tenant_id, dataset_id, doc_id, idx,
                  seg_text, len(seg_text), now))
        db.commit()
    except Exception as e:
        db.rollback()
        return _error(f'写入知识库失败: {str(e)[:200]}', start)
    finally:
        db.close()

    # 异步 Embedding
    embedding_queued = False
    try:
        from tasks.embedding_tasks import generate_embeddings_async
        generate_embeddings_async.delay(dataset_id=dataset_id, batch_size=20)
        embedding_queued = True
    except Exception:
        try:
            from engine.embedding_service import generate_missing_embeddings
            generate_missing_embeddings(dataset_id, 20)
        except Exception:
            pass

    return {
        'document_id': doc_id,
        'document_name': name[:255],
        'dataset_id': dataset_id,
        'segment_count': len(segments),
        'word_count': word_count,
        'knowledge_index_status': 'success',
        'embedding_queued': embedding_queued,
        'knowledge_index_elapsed_ms': int((time.time() - start) * 1000),
    }


def _error(message, start):
    import time
    return {
        'document_id': '',
        'segment_count': 0,
        'knowledge_index_status': 'error',
        'knowledge_index_error': message,
        'knowledge_index_elapsed_ms': int((time.time() - start) * 1000),
    }
