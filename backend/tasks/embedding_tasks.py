# -*- coding: utf-8 -*-
"""
Embedding 异步生成任务 —— 通过 Celery 异步生成文档向量

使用方式:
    from tasks.embedding_tasks import generate_embeddings_async

    # 异步生成指定数据集的 Embedding
    task = generate_embeddings_async.delay(dataset_id='xxx', batch_size=20)

    # 批量生成所有待处理的 Embedding
    task = generate_all_pending_embeddings.delay()

    # 查询任务状态
    result = generate_embeddings_async.AsyncResult(task.id)
"""

import os
import sys
import json
import time
from datetime import datetime

# 确保 backend 目录在 sys.path 中
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from tasks.celery_app import celery_app
from config import get_db


# ============================================================
# Embedding 异步生成任务
# ============================================================

@celery_app.task(bind=True, name='tasks.embedding_tasks.generate_embeddings_async',
                 queue='embedding', max_retries=3, default_retry_delay=60)
def generate_embeddings_async(self, dataset_id=None, batch_size=20):
    """
    异步生成文档 Embedding

    参数:
        dataset_id: 数据集 ID（可选，为 None 则处理所有）
        batch_size: 每批处理数量

    返回:
        dict: {processed, total, dataset_id, elapsed_time}
    """
    from engine.embedding_service import generate_missing_embeddings

    start_time = time.time()
    total_processed = 0
    batch_count = 0
    max_batches = 100  # 安全限制：最多处理 100 批

    self.update_state(
        state='STARTED',
        meta={
            'dataset_id': dataset_id,
            'status': 'starting',
            'message': '正在生成 Embedding...',
            'processed': 0,
        }
    )

    while batch_count < max_batches:
        batch_count += 1

        try:
            processed = generate_missing_embeddings(dataset_id, batch_size)
            total_processed += processed
        except Exception as e:
            # 重试逻辑
            if self.request.retries < self.max_retries:
                self.update_state(
                    state='RETRY',
                    meta={
                        'dataset_id': dataset_id,
                        'status': 'retrying',
                        'message': f'生成失败，正在重试 ({self.request.retries + 1}/{self.max_retries})...',
                        'processed': total_processed,
                    }
                )
                raise self.retry(exc=e)
            break

        # 更新进度
        self.update_state(
            state='RUNNING',
            meta={
                'dataset_id': dataset_id,
                'status': 'running',
                'message': f'已处理 {total_processed} 个分段...',
                'processed': total_processed,
                'batch': batch_count,
            }
        )

        # 如果本批没有处理任何数据，说明已全部完成
        if processed == 0:
            break

        # 短暂休眠，避免 API 限流
        time.sleep(0.5)

    elapsed = time.time() - start_time

    result = {
        'status': 'succeeded',
        'dataset_id': dataset_id,
        'processed': total_processed,
        'batches': batch_count,
        'elapsed_time': elapsed,
    }

    # 发布完成事件
    _publish_embedding_progress(dataset_id, {
        'event': 'embedding_complete',
        'dataset_id': dataset_id,
        'processed': total_processed,
        'elapsed_time': elapsed,
    })

    return result


@celery_app.task(bind=True, name='tasks.embedding_tasks.generate_all_pending_embeddings',
                 queue='embedding', max_retries=2, default_retry_delay=120)
def generate_all_pending_embeddings(self):
    """
    生成所有待处理的 Embedding（遍历所有数据集）

    返回:
        dict: {datasets_processed, total_processed, details: [{dataset_id, processed}]}
    """
    start_time = time.time()

    self.update_state(
        state='STARTED',
        meta={
            'status': 'starting',
            'message': '正在扫描待处理的数据集...',
        }
    )

    # 获取所有有待处理分段的数据集
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('''
            SELECT DISTINCT dataset_id, COUNT(*) as pending_count
            FROM dify_document_segments
            WHERE enabled = 1
              AND status = 'completed'
              AND (embedding IS NULL OR embedding_status = 'pending')
            GROUP BY dataset_id
            ORDER BY pending_count DESC
        ''')
        datasets = cur.fetchall()
    finally:
        db.close()

    if not datasets:
        return {
            'status': 'succeeded',
            'datasets_processed': 0,
            'total_processed': 0,
            'message': '没有待处理的分段',
            'elapsed_time': time.time() - start_time,
        }

    total_processed = 0
    details = []

    for i, ds in enumerate(datasets):
        dataset_id = ds['dataset_id']
        pending_count = ds['pending_count']

        self.update_state(
            state='RUNNING',
            meta={
                'status': 'running',
                'message': f'正在处理数据集 {dataset_id}（{pending_count} 个分段）...',
                'current_dataset': dataset_id,
                'dataset_index': i + 1,
                'total_datasets': len(datasets),
                'total_processed': total_processed,
            }
        )

        try:
            # 调用单数据集任务
            from engine.embedding_service import generate_missing_embeddings
            batch_count = 0
            ds_processed = 0
            max_batches = 100

            while batch_count < max_batches:
                batch_count += 1
                processed = generate_missing_embeddings(dataset_id, 20)
                ds_processed += processed
                if processed == 0:
                    break
                time.sleep(0.3)

            total_processed += ds_processed
            details.append({
                'dataset_id': dataset_id,
                'processed': ds_processed,
                'pending': pending_count,
            })

        except Exception as e:
            details.append({
                'dataset_id': dataset_id,
                'processed': 0,
                'error': str(e)[:200],
            })

    elapsed = time.time() - start_time

    return {
        'status': 'succeeded',
        'datasets_processed': len(datasets),
        'total_processed': total_processed,
        'details': details,
        'elapsed_time': elapsed,
    }


@celery_app.task(bind=True, name='tasks.embedding_tasks.generate_single_embedding',
                 queue='embedding', max_retries=3, default_retry_delay=30)
def generate_single_embedding(self, segment_id):
    """
    为单个分段生成 Embedding

    参数:
        segment_id: 分段 ID

    返回:
        dict: {segment_id, status, elapsed_time}
    """
    from engine.embedding_service import get_embedding, store_embedding, get_embedding_config

    start_time = time.time()

    # 获取分段内容
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('''
            SELECT id, content, dataset_id FROM dify_document_segments
            WHERE id = %s AND enabled = 1
        ''', (segment_id,))
        row = cur.fetchone()
    finally:
        db.close()

    if not row:
        return {'segment_id': segment_id, 'status': 'failed', 'message': '分段不存在'}

    content = row['content']
    if not content:
        return {'segment_id': segment_id, 'status': 'skipped', 'message': '分段内容为空'}

    # 获取 Embedding 配置
    cfg = get_embedding_config()
    if not cfg:
        return {'segment_id': segment_id, 'status': 'failed', 'message': '未配置 Embedding 模型'}

    model_name = cfg['model_name'] or cfg['credential_name'] or cfg['provider']
    api_key = cfg['api_key']
    base_url = (cfg['api_base_url'] or '').rstrip('/')

    try:
        # 生成向量
        embedding = get_embedding(content, model_name, api_key, base_url)

        # 存储向量
        store_embedding(
            segment_id=segment_id,
            embedding=embedding,
            model_name=model_name,
            dataset_id=row['dataset_id'],
            content=content,
        )

        elapsed = time.time() - start_time

        # 更新状态为完成
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('''
                UPDATE dify_document_segments
                SET embedding_status = 'completed'
                WHERE id = %s
            ''', (segment_id,))
            db.commit()
        finally:
            db.close()

        return {
            'segment_id': segment_id,
            'status': 'succeeded',
            'elapsed_time': elapsed,
        }

    except Exception as e:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        # 更新状态为失败
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('''
                UPDATE dify_document_segments
                SET embedding_status = 'failed'
                WHERE id = %s
            ''', (segment_id,))
            db.commit()
        finally:
            db.close()

        return {
            'segment_id': segment_id,
            'status': 'failed',
            'message': str(e)[:200],
        }


# ============================================================
# 辅助函数
# ============================================================

def _publish_embedding_progress(dataset_id, data):
    """发布 Embedding 进度事件到 Redis"""
    try:
        from utils.redis_cache import get_redis
        r = get_redis()
        channel = f'emb:progress:{dataset_id or "all"}'
        r.publish(channel, json.dumps(data, ensure_ascii=False))
        r.setex(f'emb:status:{dataset_id or "all"}', 3600, json.dumps(data, ensure_ascii=False))
    except Exception:
        pass


def get_embedding_task_status(task_id):
    """查询 Embedding 任务状态"""
    result = generate_embeddings_async.AsyncResult(task_id)
    return {
        'task_id': task_id,
        'state': result.state,
        'status': result.info.get('status', '') if isinstance(result.info, dict) else str(result.info),
        'result': result.result if result.ready() else None,
        'meta': result.info if isinstance(result.info, dict) else {},
    }


# ============================================================
# Agent 记忆向量化任务
# ============================================================

@celery_app.task(bind=True, name='tasks.embedding_tasks.embed_agent_memory',
                 queue='embedding', max_retries=3, default_retry_delay=30)
def embed_agent_memory(self, memory_id, agent_id, content):
    """
    异步为 Agent 记忆生成 embedding 并写入 Qdrant
    """
    try:
        from engine.agent_memory import embed_memory
        ok = embed_memory(memory_id, agent_id, content)
        if not ok:
            raise Exception('embed_memory 返回失败')
        return {'memory_id': memory_id, 'ok': True}
    except Exception as exc:
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            from engine.agent_memory import _mark_failed
            _mark_failed(memory_id)
            return {'memory_id': memory_id, 'ok': False, 'error': str(exc)}


def get_pending_embedding_count(dataset_id=None):
    """获取待处理的分段数量"""
    db = get_db()
    try:
        cur = db.cursor()
        if dataset_id:
            cur.execute('''
                SELECT COUNT(*) as cnt FROM dify_document_segments
                WHERE dataset_id = %s AND enabled = 1 AND status = 'completed'
                  AND (embedding IS NULL OR embedding_status = 'pending')
            ''', (dataset_id,))
        else:
            cur.execute('''
                SELECT COUNT(*) as cnt FROM dify_document_segments
                WHERE enabled = 1 AND status = 'completed'
                  AND (embedding IS NULL OR embedding_status = 'pending')
            ''')
        row = cur.fetchone()
        return row['cnt'] if row else 0
    finally:
        db.close()


# ============================================================
# 关键词索引任务（3.2: jieba 分词混合检索）
# ============================================================

@celery_app.task(bind=True, name='tasks.embedding_tasks.build_keyword_index',
                 queue='embedding', max_retries=2, default_retry_delay=30)
def build_keyword_index(self, dataset_id=None):
    """
    异步构建关键词索引。

    参数:
        dataset_id: 数据集 ID（可选，为 None 则处理所有）

    返回:
        dict: {status, indexed_segments, keyword_count, dataset_id}
    """
    from engine.keyword_engine import build_keyword_index_for_dataset, get_keyword_stats, ensure_keyword_table

    # 确保表存在
    ensure_keyword_table()

    start_time = time.time()

    if dataset_id:
        self.update_state(state='RUNNING', meta={
            'status': 'running',
            'message': f'正在为数据集 {dataset_id} 建立关键词索引...',
        })
        n = build_keyword_index_for_dataset(dataset_id)
        stats = get_keyword_stats(dataset_id)
        return {
            'status': 'succeeded',
            'dataset_id': dataset_id,
            'indexed_segments': n,
            'keyword_count': stats['keyword_count'],
            'elapsed_time': time.time() - start_time,
        }

    # 处理所有数据集
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('SELECT DISTINCT dataset_id FROM dify_document_segments WHERE enabled = 1 AND status = "completed"')
        datasets = [r['dataset_id'] for r in cur.fetchall()]
    finally:
        db.close()

    total_segments = 0
    for i, ds_id in enumerate(datasets):
        self.update_state(state='RUNNING', meta={
            'status': 'running',
            'message': f'正在处理数据集 {ds_id} ({i + 1}/{len(datasets)})...',
            'current': i + 1,
            'total': len(datasets),
        })
        n = build_keyword_index_for_dataset(ds_id)
        total_segments += n

    return {
        'status': 'succeeded',
        'datasets_processed': len(datasets),
        'indexed_segments': total_segments,
        'elapsed_time': time.time() - start_time,
    }


# ============================================================
# Agent 对话自动记忆写入任务
# ============================================================

@celery_app.task(bind=True, name='tasks.embedding_tasks.save_conversation_memory',
                 queue='embedding', max_retries=2, default_retry_delay=10)
def save_conversation_memory(self, agent_id, user_message, assistant_reply):
    """
    对话结束后自动将 Q&A 摘要写入 Agent 长期记忆。

    参数:
        agent_id: 智能体 ID
        user_message: 用户消息
        assistant_reply: 助手回复
    """
    try:
        from engine.agent_memory import add_memory
        # 构造记忆内容：用户问题 + 回答摘要（控制在合理长度）
        user_part = (user_message or '')[:150]
        reply_part = (assistant_reply or '')[:300]
        content = f"用户提问：{user_part}\n助手回答：{reply_part}"
        row = add_memory(int(agent_id), content)
        if row:
            return {'ok': True, 'memory_id': row.get('id')}
        return {'ok': False, 'message': 'add_memory 返回 None'}
    except Exception as exc:
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {'ok': False, 'error': str(exc)[:200]}
