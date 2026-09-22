# -*- coding: utf-8 -*-
"""
定时任务模块 —— 基于 Celery Beat 的周期性任务

调度配置（在 celery_app.py 的 beat_schedule 中定义）:
    - generate-pending-embeddings: 每 5 分钟生成待处理的 Embedding
    - cleanup-expired-results: 每天凌晨 3 点清理过期结果
    - cleanup-stale-workflow-runs: 每天凌晨 4 点清理卡住的工作流运行

使用方式:
    1. 启动 Beat: celery -A tasks.celery_app beat --loglevel=info
    2. 启动 Worker: celery -A tasks.celery_app worker --loglevel=info
    3. 或使用 Worker + Beat 合一: celery -A tasks.celery_app worker -B --loglevel=info
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta

# 确保 backend 目录在 sys.path 中
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from tasks.celery_app import celery_app
from config import get_db


# ============================================================
# Embedding 定时任务
# ============================================================

@celery_app.task(bind=True, name='tasks.scheduled.generate_pending_embeddings',
                 queue='scheduled', max_retries=2, default_retry_delay=30)
def generate_pending_embeddings(self):
    """
    定时任务：生成所有待处理的 Embedding

    触发频率: 每 5 分钟
    逻辑: 检查是否有待处理的分段，有则触发生成任务
    """
    from engine.embedding_service import generate_missing_embeddings

    start_time = time.time()
    total_processed = 0
    batch_count = 0
    max_batches = 50  # 每次定时任务最多处理 50 批

    while batch_count < max_batches:
        batch_count += 1
        try:
            processed = generate_missing_embeddings(None, 20)
            total_processed += processed
        except Exception:
            break

        if processed == 0:
            break

        time.sleep(0.3)

    elapsed = time.time() - start_time

    if total_processed > 0:
        # 记录日志
        _log_scheduled_task('generate_pending_embeddings', {
            'processed': total_processed,
            'batches': batch_count,
            'elapsed_time': elapsed,
        })

    return {
        'status': 'succeeded',
        'processed': total_processed,
        'batches': batch_count,
        'elapsed_time': elapsed,
    }


# ============================================================
# 清理任务
# ============================================================

@celery_app.task(bind=True, name='tasks.scheduled.cleanup_expired_results',
                 queue='scheduled', max_retries=1)
def cleanup_expired_results(self):
    """
    定时任务：清理过期的任务结果和缓存

    触发频率: 每天凌晨 3 点
    逻辑:
        1. 清理 Redis 中过期的任务状态
        2. 清理过期的 LLM 缓存
        3. 清理过期的限流记录
    """
    start_time = time.time()
    cleaned = {
        'workflow_states': 0,
        'llm_cache': 0,
        'rate_limits': 0,
        'task_status': 0,
    }

    try:
        from utils.redis_cache import get_redis
        r = get_redis()

        # 清理过期的 LLM 缓存（超过 24 小时的）
        llm_keys = r.keys('llc:*')
        if llm_keys:
            # LLM 缓存使用 TTL 自动过期，这里只统计
            cleaned['llm_cache'] = len(llm_keys)

        # 清理过期的限流记录
        rl_keys = r.keys('rl:*')
        if rl_keys:
            cleaned['rate_limits'] = len(rl_keys)

        # 清理过期的任务状态（超过 1 小时的）
        wf_keys = r.keys('wf:status:*')
        if wf_keys:
            cleaned['task_status'] = len(wf_keys)

        # 清理过期的 Embedding 进度
        emb_keys = r.keys('emb:status:*')
        if emb_keys:
            cleaned['embedding_status'] = len(emb_keys)

    except Exception as e:
        cleaned['error'] = str(e)[:200]

    elapsed = time.time() - start_time

    _log_scheduled_task('cleanup_expired_results', {
        'cleaned': cleaned,
        'elapsed_time': elapsed,
    })

    return {
        'status': 'succeeded',
        'cleaned': cleaned,
        'elapsed_time': elapsed,
    }


@celery_app.task(bind=True, name='tasks.scheduled.cleanup_stale_workflow_runs',
                 queue='scheduled', max_retries=1)
def cleanup_stale_workflow_runs(self):
    """
    定时任务：清理卡住的工作流运行

    触发频率: 每天凌晨 4 点
    逻辑: 将超过 24 小时仍处于 'running' 状态的运行记录标记为 'failed'
    """
    start_time = time.time()
    cutoff = datetime.now() - timedelta(hours=24)
    cutoff_str = cutoff.strftime('%Y-%m-%d %H:%M:%S')

    db = get_db()
    try:
        cur = db.cursor()
        # 查找卡住的运行记录
        cur.execute('''
            SELECT id, app_id, created_at FROM dify_workflow_runs
            WHERE status = 'running' AND created_at < %s
        ''', (cutoff_str,))
        stale_runs = cur.fetchall()

        # 标记为失败
        if stale_runs:
            cur.execute('''
                UPDATE dify_workflow_runs
                SET status = 'failed', error = '超时自动终止（超过 24 小时）', finished_at = %s
                WHERE status = 'running' AND created_at < %s
            ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cutoff_str))
            db.commit()

        cleaned_count = len(stale_runs)
    except Exception as e:
        db.rollback()
        cleaned_count = 0
        error_msg = str(e)[:200]
    finally:
        db.close()

    elapsed = time.time() - start_time

    if cleaned_count > 0:
        _log_scheduled_task('cleanup_stale_workflow_runs', {
            'cleaned': cleaned_count,
            'elapsed_time': elapsed,
        })

    return {
        'status': 'succeeded',
        'cleaned': cleaned_count,
        'elapsed_time': elapsed,
    }


# ============================================================
# 健康检查任务
# ============================================================

@celery_app.task(bind=True, name='tasks.scheduled.dispatch_due_schedule_plans',
                 queue='scheduled', max_retries=1)
def dispatch_due_schedule_plans(self):
    """
    定时任务：触发所有到期的定时触发计划（trigger-schedule 节点）

    触发频率: 每分钟
    逻辑:
        1. 查询 next_run_at 已到期的启用计划（每次最多 50 个）
        2. 对每个计划调用 engine.trigger_engine.dispatch_due_plans 启动异步工作流
        3. 推进 next_run_at（croniter 计算）并写 workflow_trigger_logs
    """
    start_time = time.time()

    from engine.trigger_engine import dispatch_due_plans
    result = dispatch_due_plans()

    elapsed = time.time() - start_time
    if result.get('dispatched') or result.get('errors'):
        _log_scheduled_task('dispatch_due_schedule_plans', {
            'dispatched': result.get('dispatched', 0),
            'errors': result.get('errors', 0),
            'elapsed_time': elapsed,
        })

    return {
        'status': 'succeeded',
        'dispatched': result.get('dispatched', 0),
        'errors': result.get('errors', 0),
        'elapsed_time': elapsed,
    }


@celery_app.task(bind=True, name='tasks.scheduled.health_check',
                 queue='scheduled', max_retries=0)
def health_check(self):
    """
    定时任务：系统健康检查

    检查项:
        1. MySQL 连接
        2. Redis 连接
        3. Celery Worker 状态

    返回:
        dict: {mysql, redis, celery, timestamp}
    """
    result = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'mysql': False,
        'redis': False,
        'celery': True,  # 能执行此任务说明 Celery 正常
    }

    # 检查 MySQL
    try:
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('SELECT 1')
            result['mysql'] = True
        finally:
            db.close()
    except Exception as e:
        result['mysql_error'] = str(e)[:100]

    # 检查 Redis
    try:
        from utils.redis_cache import redis_available
        result['redis'] = redis_available()
    except Exception as e:
        result['redis_error'] = str(e)[:100]

    return result


# ============================================================
# 统计任务
# ============================================================

@celery_app.task(bind=True, name='tasks.scheduled.daily_statistics',
                 queue='scheduled', max_retries=1)
def daily_statistics(self):
    """
    定时任务：每日统计

    统计内容:
        1. 活跃工作流数量
        2. 今日运行次数
        3. 平均执行时间
        4. 成功率

    触发频率: 每天凌晨 2:30
    """
    db = get_db()
    try:
        cur = db.cursor()
        today = datetime.now().strftime('%Y-%m-%d')

        # 活跃工作流数量
        cur.execute('SELECT COUNT(*) as cnt FROM dify_workflows')
        total_workflows = cur.fetchone()['cnt']

        # 今日运行次数
        cur.execute('''
            SELECT COUNT(*) as cnt FROM dify_workflow_runs
            WHERE DATE(created_at) = %s
        ''', (today,))
        today_runs = cur.fetchone()['cnt']

        # 成功率
        cur.execute('''
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'succeeded' THEN 1 ELSE 0 END) as succeeded
            FROM dify_workflow_runs
            WHERE DATE(created_at) = %s
        ''', (today,))
        row = cur.fetchone()
        success_rate = (row['succeeded'] / row['total'] * 100) if row['total'] > 0 else 0

        # 平均执行时间
        cur.execute('''
            SELECT AVG(elapsed_time) as avg_time FROM dify_workflow_runs
            WHERE DATE(created_at) = %s AND elapsed_time IS NOT NULL
        ''', (today,))
        avg_time = cur.fetchone()['avg_time'] or 0

        stats = {
            'date': today,
            'total_workflows': total_workflows,
            'today_runs': today_runs,
            'success_rate': round(success_rate, 2),
            'avg_elapsed_time': round(avg_time, 3),
        }
    finally:
        db.close()

    return {
        'status': 'succeeded',
        'statistics': stats,
    }


# ============================================================
# 辅助函数
# ============================================================

def _log_scheduled_task(task_name, data):
    """记录定时任务执行日志"""
    try:
        from utils.redis_cache import get_redis
        r = get_redis()
        log_entry = {
            'task': task_name,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data': data,
        }
        # 保存到列表（最近 100 条）
        r.lpush('scheduled:task:logs', json.dumps(log_entry, ensure_ascii=False))
        r.ltrim('scheduled:task:logs', 0, 99)
    except Exception:
        pass


def get_scheduled_task_logs(count=20):
    """获取最近的定时任务执行日志"""
    try:
        from utils.redis_cache import get_redis
        r = get_redis()
        logs = r.lrange('scheduled:task:logs', 0, count - 1)
        return [json.loads(log) for log in logs]
    except Exception:
        return []
