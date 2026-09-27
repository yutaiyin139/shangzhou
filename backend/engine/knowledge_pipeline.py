# -*- coding: utf-8 -*-
"""
知识 Pipeline 引擎（P2 #13）

功能:
    - 自定义文档 ETL 流程（获取 → 解析 → 清洗 → 分段 → 向量化 → 索引）
    - 支持多阶段 Pipeline 配置（JSON stages）
    - 支持定时调度（cron）
    - 异步执行 + 执行日志

Pipeline 阶段类型:
    - fetch: 获取文档（file/upload, url/scrape, api/fetch, text/direct）
    - parse: 解析内容（pdf, docx, html, markdown, text）
    - clean: 清洗文本（去空白, 去重, 格式标准化）
    - segment: 分段（通用, 父子, Q&A, 表格）
    - transform: 转换（摘要, 翻译, 关键词提取）
    - embed: 向量化（调用 Embedding API）
    - index: 写入知识库（创建分段 + 向量）
"""

import json
import re
import uuid
import time
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from config import get_db
from models.tables import (
    PIPELINES_TABLE_SQL,
    PIPELINE_EXECUTION_LOGS_TABLE_SQL,
    PIPELINE_DOCUMENTS_TABLE_SQL,
)
from utils.helpers import now


# ============================================================
# Pipeline CRUD
# ============================================================

def _ensure_tables():
    """确保 Pipeline 相关表已创建"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(PIPELINES_TABLE_SQL)
        cur.execute(PIPELINE_EXECUTION_LOGS_TABLE_SQL)
        cur.execute(PIPELINE_DOCUMENTS_TABLE_SQL)
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


def create_pipeline(name, description, stages, dataset_id=None, schedule=None, created_by=None):
    """
    创建 Pipeline

    参数:
        name: Pipeline 名称
        description: 描述
        stages: 阶段列表 [{type, config, order}]
        dataset_id: 关联知识库 ID
        schedule: cron 表达式
        created_by: 创建者 ID

    返回: pipeline_id
    """
    _ensure_tables()
    pipeline_id = str(uuid.uuid4())
    ts = now()

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''INSERT INTO knowledge_pipelines
            (id, name, description, dataset_id, status, stages, schedule, created_by, created_at, updated_at)
            VALUES (%s, %s, %s, %s, 'draft', %s, %s, %s, %s, %s)''',
            (pipeline_id, name, description, dataset_id,
             json.dumps(stages, ensure_ascii=False) if isinstance(stages, list) else stages,
             schedule, created_by, ts, ts))
        db.commit()
    finally:
        db.close()
    return pipeline_id


def update_pipeline(pipeline_id, **kwargs):
    """更新 Pipeline"""
    _ensure_tables()
    allowed = {'name', 'description', 'dataset_id', 'status', 'stages', 'schedule'}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return False

    if 'stages' in updates and isinstance(updates['stages'], list):
        updates['stages'] = json.dumps(updates['stages'], ensure_ascii=False)

    set_clause = ', '.join(f'{k} = %s' for k in updates)
    values = list(updates.values()) + [pipeline_id]

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(f'UPDATE knowledge_pipelines SET {set_clause}, updated_at = NOW() WHERE id = %s', values)
        db.commit()
        return cur.rowcount > 0
    finally:
        db.close()


def delete_pipeline(pipeline_id):
    """删除 Pipeline"""
    _ensure_tables()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'DELETE FROM pipeline_documents WHERE pipeline_id = %s', (pipeline_id,))
        cur.execute(r'DELETE FROM pipeline_execution_logs WHERE pipeline_id = %s', (pipeline_id,))
        cur.execute(r'DELETE FROM knowledge_pipelines WHERE id = %s', (pipeline_id,))
        db.commit()
    finally:
        db.close()


def get_pipeline(pipeline_id):
    """获取 Pipeline 详情"""
    _ensure_tables()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT * FROM knowledge_pipelines WHERE id = %s', (pipeline_id,))
        row = cur.fetchone()
        if row:
            row = _parse_pipeline(row)
        return row
    finally:
        db.close()


def list_pipelines(dataset_id=None, status=None, page=1, limit=20):
    """列出 Pipeline"""
    _ensure_tables()
    db = get_db()
    try:
        cur = db.cursor()
        sql = r'SELECT * FROM knowledge_pipelines WHERE 1=1'
        params = []
        if dataset_id:
            sql += r' AND dataset_id = %s'
            params.append(dataset_id)
        if status:
            sql += r' AND status = %s'
            params.append(status)
        sql += r' ORDER BY created_at DESC LIMIT %s OFFSET %s'
        params.extend([limit, (page - 1) * limit])
        cur.execute(sql, params)
        rows = cur.fetchall()
        return [_parse_pipeline(r) for r in rows]
    finally:
        db.close()


def _parse_pipeline(row):
    """解析 Pipeline 行数据"""
    try:
        if isinstance(row.get('stages'), str):
            row['stages'] = json.loads(row['stages'])
    except Exception:
        row['stages'] = []
    for field in ('created_at', 'updated_at', 'last_run_at'):
        if row.get(field) and hasattr(row[field], 'strftime'):
            row[field] = row[field].strftime('%Y-%m-%d %H:%M:%S')
    return row


# ============================================================
# Pipeline 执行引擎
# ============================================================

def run_pipeline(pipeline_id, trigger_type='manual', executor=None):
    """
    执行 Pipeline

    参数:
        pipeline_id: Pipeline ID
        trigger_type: 触发类型 (manual/scheduled/webhook)
        executor: 线程池（可选）

    返回: execution_id
    """
    _ensure_tables()
    execution_id = str(uuid.uuid4())
    pipeline = get_pipeline(pipeline_id)

    if not pipeline:
        raise ValueError(f'Pipeline {pipeline_id} 不存在')

    stages = pipeline.get('stages', [])
    if not stages:
        raise ValueError('Pipeline 没有配置阶段')

    # 创建执行日志
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''INSERT INTO pipeline_execution_logs
            (id, pipeline_id, trigger_type, status, started_at, created_at)
            VALUES (%s, %s, %s, 'running', NOW(), NOW())''',
            (execution_id, pipeline_id, trigger_type))
        # 更新 Pipeline 状态
        cur.execute(r'UPDATE knowledge_pipelines SET status = %s, last_run_at = NOW() WHERE id = %s',
                    ('running', pipeline_id))
        db.commit()
    finally:
        db.close()

    # 异步执行
    if executor:
        executor.submit(_execute_pipeline, execution_id, pipeline, stages)
    else:
        _execute_pipeline(execution_id, pipeline, stages)

    return execution_id


def _execute_pipeline(execution_id, pipeline, stages):
    """执行 Pipeline 各阶段"""
    pipeline_id = pipeline['id']
    dataset_id = pipeline.get('dataset_id')
    stages_result = []
    total_processed = 0
    total_succeeded = 0
    total_failed = 0

    try:
        context = {'documents': [], 'segments': [], 'pipeline_id': pipeline_id}

        for stage in stages:
            stage_type = stage.get('type', '')
            stage_config = stage.get('config', {})
            stage_start = time.time()

            try:
                result = _execute_stage(stage_type, stage_config, context, dataset_id)
                stage_duration = round(time.time() - stage_start, 2)
                stages_result.append({
                    'stage': stage_type,
                    'status': 'success',
                    'duration': stage_duration,
                    'output': result,
                })
                # 更新当前阶段
                _update_execution(execution_id, current_stage=stage_type,
                                  stages_result=stages_result)
            except Exception as e:
                stage_duration = round(time.time() - stage_start, 2)
                stages_result.append({
                    'stage': stage_type,
                    'status': 'failed',
                    'duration': stage_duration,
                    'error': str(e),
                })
                raise  # 中止后续阶段

        # 统计
        total_processed = len(context.get('documents', []))
        total_succeeded = len([d for d in context.get('documents', []) if d.get('status') == 'success'])
        total_failed = total_processed - total_succeeded

        # 更新执行日志为成功
        _update_execution(execution_id, status='success', current_stage=None,
                          stages_result=stages_result, docs_processed=total_processed,
                          docs_succeeded=total_succeeded, docs_failed=total_failed,
                          completed_at=datetime.now())

        # 更新 Pipeline 状态
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''UPDATE knowledge_pipelines
                SET status = 'draft', total_docs = total_docs + %s
                WHERE id = %s''', (total_succeeded, pipeline_id))
            db.commit()
        finally:
            db.close()

    except Exception as e:
        _update_execution(execution_id, status='failed', current_stage=None,
                          stages_result=stages_result, error_message=str(e),
                          docs_processed=total_processed, docs_succeeded=total_succeeded,
                          docs_failed=total_failed, completed_at=datetime.now())
        # 更新 Pipeline 状态为暂停
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r"UPDATE knowledge_pipelines SET status = 'paused' WHERE id = %s", (pipeline_id,))
            db.commit()
        finally:
            db.close()


def _execute_stage(stage_type, config, context, dataset_id=None):
    """
    执行单个阶段

    返回: 阶段输出信息
    """
    if stage_type == 'fetch':
        return _stage_fetch(config, context)
    elif stage_type == 'parse':
        return _stage_parse(config, context)
    elif stage_type == 'clean':
        return _stage_clean(config, context)
    elif stage_type == 'segment':
        return _stage_segment(config, context)
    elif stage_type == 'transform':
        return _stage_transform(config, context)
    elif stage_type == 'embed':
        return _stage_embed(config, context, dataset_id)
    elif stage_type == 'index':
        return _stage_index(config, context, dataset_id)
    else:
        raise ValueError(f'未知的阶段类型: {stage_type}')


def _stage_fetch(config, context):
    """获取文档阶段"""
    source_type = config.get('source_type', 'text')
    documents = []

    if source_type == 'text':
        # 直接输入文本
        texts = config.get('texts', [])
        for text in texts:
            doc_id = str(uuid.uuid4())
            documents.append({
                'id': doc_id,
                'source_type': 'text',
                'raw_content': text,
                'status': 'pending',
            })
    elif source_type == 'file':
        # 从文件获取
        file_paths = config.get('file_paths', [])
        for path in file_paths:
            doc_id = str(uuid.uuid4())
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                documents.append({
                    'id': doc_id,
                    'source_type': 'file',
                    'source_path': path,
                    'raw_content': content,
                    'status': 'pending',
                })
            except Exception as e:
                documents.append({
                    'id': doc_id,
                    'source_type': 'file',
                    'source_path': path,
                    'status': 'failed',
                    'error': str(e),
                })
    elif source_type == 'url':
        # 从 URL 抓取
        urls = config.get('urls', [])
        for url in urls:
            doc_id = str(uuid.uuid4())
            try:
                import urllib.request
                req = urllib.request.Request(url, headers={'User-Agent': 'Shangzhou-Pipeline/1.0'})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    content = resp.read().decode('utf-8', errors='replace')
                documents.append({
                    'id': doc_id,
                    'source_type': 'url',
                    'source_path': url,
                    'raw_content': content,
                    'status': 'pending',
                })
            except Exception as e:
                documents.append({
                    'id': doc_id,
                    'source_type': 'url',
                    'source_path': url,
                    'status': 'failed',
                    'error': str(e),
                })

    context['documents'] = documents
    return {'documents_fetched': len([d for d in documents if d.get('status') == 'pending'])}


def _stage_parse(config, context):
    """解析文档阶段"""
    parsed_count = 0
    for doc in context.get('documents', []):
        if doc.get('status') != 'pending':
            continue
        raw = doc.get('raw_content', '')
        if not raw:
            doc['status'] = 'failed'
            doc['error'] = '无内容'
            continue

        # HTML 标签去除
        if config.get('strip_html', True):
            raw = re.sub(r'<[^>]+>', ' ', raw)
        # 去除多余空白
        if config.get('strip_whitespace', True):
            raw = re.sub(r'\s+', ' ', raw).strip()

        doc['processed_content'] = raw
        doc['status'] = 'success'
        parsed_count += 1

    return {'documents_parsed': parsed_count}


def _stage_clean(config, context):
    """清洗文本阶段"""
    cleaned_count = 0
    for doc in context.get('documents', []):
        content = doc.get('processed_content') or doc.get('raw_content', '')
        if not content:
            continue

        # 去除特殊字符
        if config.get('remove_special_chars', False):
            content = re.sub(r'[^\w\s一-鿿.,;:!?\-]', '', content)

        # 标准化空白
        if config.get('normalize_whitespace', True):
            content = re.sub(r'\s+', ' ', content).strip()

        # 去除重复行
        if config.get('remove_duplicates', False):
            lines = content.split('\n')
            seen = set()
            unique_lines = []
            for line in lines:
                line_hash = hashlib.md5(line.strip().encode()).hexdigest()
                if line_hash not in seen:
                    seen.add(line_hash)
                    unique_lines.append(line)
            content = '\n'.join(unique_lines)

        doc['processed_content'] = content
        cleaned_count += 1

    return {'documents_cleaned': cleaned_count}


def _stage_segment(config, context):
    """分段阶段"""
    segment_mode = config.get('mode', 'general')
    max_tokens = int(config.get('max_tokens', 500))
    overlap = int(config.get('overlap', 50))
    all_segments = []

    for doc in context.get('documents', []):
        content = doc.get('processed_content') or doc.get('raw_content', '')
        if not content:
            continue

        if segment_mode == 'general':
            segments = _segment_general(content, max_tokens, overlap)
        elif segment_mode == 'paragraph':
            segments = _segment_by_paragraph(content, max_tokens)
        else:
            segments = _segment_general(content, max_tokens, overlap)

        doc['segments'] = segments
        all_segments.extend(segments)

    context['segments'] = all_segments
    return {'total_segments': len(all_segments), 'documents_segmented': len(context.get('documents', []))}


def _segment_general(content, max_tokens, overlap):
    """通用分段（按字数切分）"""
    chunks = []
    # 按句子分割
    sentences = re.split(r'(?<=[。！？.!?])\s*', content)
    current_chunk = ''
    current_size = 0

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        sent_size = len(sent)
        if current_size + sent_size > max_tokens and current_chunk:
            chunks.append(current_chunk.strip())
            # 保留重叠
            if overlap > 0 and len(current_chunk) > overlap:
                current_chunk = current_chunk[-overlap:] + sent
                current_size = len(current_chunk)
            else:
                current_chunk = sent
                current_size = sent_size
        else:
            current_chunk += sent
            current_size += sent_size

    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    return chunks


def _segment_by_paragraph(content, max_tokens):
    """按段落分段"""
    paragraphs = content.split('\n\n')
    chunks = []
    current = ''
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) > max_tokens and current:
            chunks.append(current.strip())
            current = para
        else:
            current += '\n\n' + para if current else para
    if current.strip():
        chunks.append(current.strip())
    return chunks


def _stage_transform(config, context):
    """转换阶段（摘要、关键词提取）"""
    transform_type = config.get('transform_type', 'none')
    transformed = 0

    if transform_type == 'keywords':
        # 关键词提取（jieba）
        try:
            import jieba.analyse
            for doc in context.get('documents', []):
                content = doc.get('processed_content') or doc.get('raw_content', '')
                if content:
                    keywords = jieba.analyse.extract_tags(content, topK=10)
                    doc['keywords'] = keywords
                    transformed += 1
        except ImportError:
            pass  # jieba 不可用则跳过

    return {'documents_transformed': transformed, 'transform_type': transform_type}


def _stage_embed(config, context, dataset_id=None):
    """向量化阶段"""
    segments = context.get('segments', [])
    if not segments:
        return {'embedded': 0}

    embedded_count = 0
    try:
        from engine.embedding_service import get_embeddings_batch
        # 批量获取 embedding
        batch_size = 10
        for i in range(0, len(segments), batch_size):
            batch = segments[i:i + batch_size]
            # 分段可能是字符串也可能是 dict，向量化入参只能是文本；
            # 嵌入服务对外的批量入口叫 get_embeddings_batch（旧的 get_embeddings 并不存在）
            texts = [(s.get('content', '') if isinstance(s, dict) else s) for s in batch]
            embeddings = get_embeddings_batch(texts)
            for j, emb in enumerate(embeddings):
                if i + j < len(segments):
                    if isinstance(segments[i + j], str):
                        segments[i + j] = {'content': segments[i + j], 'embedding': emb}
                    else:
                        segments[i + j]['embedding'] = emb
                    embedded_count += 1
    except Exception as e:
        raise Exception(f'向量化失败: {e}')

    context['segments'] = segments
    return {'embedded': embedded_count}


def _stage_index(config, context, dataset_id=None):
    """索引阶段（写入知识库）"""
    if not dataset_id:
        return {'indexed': 0, 'reason': '未关联知识库'}

    segments = context.get('segments', [])
    if not segments:
        return {'indexed': 0}

    db = get_db()
    try:
        cur = db.cursor()
        # 获取 tenant_id
        cur.execute(r'SELECT tenant_id FROM dify_datasets WHERE id = %s', (dataset_id,))
        ds_row = cur.fetchone()
        tenant_id = ds_row['tenant_id'] if ds_row else str(uuid.uuid4())

        indexed = 0
        for seg in segments:
            content = seg if isinstance(seg, str) else seg.get('content', '')
            embedding = seg.get('embedding') if isinstance(seg, dict) else None
            if not content:
                continue

            segment_id = str(uuid.uuid4())
            word_count = len(content.replace('\n', '').replace(' ', ''))
            tokens = max(1, int(len(content) / 3))
            cur.execute(r'''INSERT INTO dify_document_segments
                (id, tenant_id, dataset_id, document_id, position, content,
                 word_count, tokens, hit_count, status, created_by,
                 parent_id, segment_type, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, 'completed', %s, %s, %s, %s)''',
                (segment_id, tenant_id, dataset_id, str(uuid.uuid4()), indexed, content,
                 word_count, tokens, 'pipeline', None, 'general',
                 json.dumps({'embedding': embedding}, ensure_ascii=False) if embedding else ''))
            indexed += 1

        # 更新知识库文档计数
        cur.execute(r'''UPDATE dify_datasets
            SET document_count = COALESCE(document_count, 0) + %s
            WHERE id = %s''', (indexed, dataset_id))
        db.commit()
        return {'indexed': indexed}
    except Exception as e:
        db.rollback()
        raise Exception(f'索引失败: {e}')
    finally:
        db.close()


def _update_execution(execution_id, **kwargs):
    """更新执行日志"""
    allowed = {'status', 'current_stage', 'stages_result', 'docs_processed',
               'docs_succeeded', 'docs_failed', 'error_message', 'completed_at'}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return

    if 'stages_result' in updates and isinstance(updates['stages_result'], list):
        updates['stages_result'] = json.dumps(updates['stages_result'], ensure_ascii=False)

    set_clause = ', '.join(f'{k} = %s' for k in updates)
    values = list(updates.values()) + [execution_id]

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(f'UPDATE pipeline_execution_logs SET {set_clause} WHERE id = %s', values)
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


def get_execution_log(execution_id):
    """获取执行日志"""
    _ensure_tables()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT * FROM pipeline_execution_logs WHERE id = %s', (execution_id,))
        row = cur.fetchone()
        if row:
            try:
                if isinstance(row.get('stages_result'), str):
                    row['stages_result'] = json.loads(row['stages_result'])
            except Exception:
                row['stages_result'] = []
            for field in ('started_at', 'completed_at', 'created_at'):
                if row.get(field) and hasattr(row[field], 'strftime'):
                    row[field] = row[field].strftime('%Y-%m-%d %H:%M:%S')
        return row
    finally:
        db.close()


def list_execution_logs(pipeline_id, page=1, limit=20):
    """列出执行日志"""
    _ensure_tables()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''SELECT * FROM pipeline_execution_logs
            WHERE pipeline_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s''',
            (pipeline_id, limit, (page - 1) * limit))
        rows = cur.fetchall()
        result = []
        for row in rows:
            try:
                if isinstance(row.get('stages_result'), str):
                    row['stages_result'] = json.loads(row['stages_result'])
            except Exception:
                row['stages_result'] = []
            for field in ('started_at', 'completed_at', 'created_at'):
                if row.get(field) and hasattr(row[field], 'strftime'):
                    row[field] = row[field].strftime('%Y-%m-%d %H:%M:%S')
            result.append(row)
        return result
    finally:
        db.close()
