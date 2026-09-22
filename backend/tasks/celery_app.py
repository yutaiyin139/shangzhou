# -*- coding: utf-8 -*-
"""
Celery 应用实例 —— 使用 Redis 作为消息代理和结果后端

使用方式:
    1. 启动 Worker: celery -A tasks.celery_app worker --loglevel=info
    2. 启动 Beat (定时任务): celery -A tasks.celery_app beat --loglevel=info
    3. 调用任务: from tasks.workflow_tasks import run_workflow_async
       task = run_workflow_async.delay(app_id, inputs, user)

配置说明:
    - broker_url: Redis 消息代理地址
    - result_backend: Redis 结果存储地址
    - task_serializer: 任务序列化格式（JSON）
    - task_track_started: 跟踪任务开始状态
    - task_time_limit: 任务硬超时（秒）
    - task_soft_time_limit: 任务软超时（秒）
    - worker_prefetch_multiplier: 每次预取任务数（1 = 公平调度）
"""

import os
import sys

# 确保 backend 目录在 sys.path 中
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from celery import Celery
from celery.schedules import crontab

# ============================================================
# Redis 配置
# ============================================================

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_DB_BROKER = int(os.environ.get('REDIS_DB_BROKER', 0))
REDIS_DB_BACKEND = int(os.environ.get('REDIS_DB_BACKEND', 1))
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', None)

# 构造 Redis URL
if REDIS_PASSWORD:
    _redis_url = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}'
else:
    _redis_url = f'redis://{REDIS_HOST}:{REDIS_PORT}'

BROKER_URL = f'{_redis_url}/{REDIS_DB_BROKER}'
RESULT_BACKEND = f'{_redis_url}/{REDIS_DB_BACKEND}'

# ============================================================
# Celery 应用
# ============================================================

celery_app = Celery(
    'shangzhou_tasks',
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=[
        'tasks.workflow_tasks',
        'tasks.embedding_tasks',
        'tasks.scheduled',
    ],
)

# ============================================================
# Celery 配置
# ============================================================

celery_app.conf.update(
    # 序列化
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],

    # 时区
    timezone='Asia/Shanghai',
    enable_utc=True,

    # 任务跟踪
    task_track_started=True,
    task_acks_late=True,  # 任务完成后确认（防止 worker 崩溃丢失任务）
    worker_prefetch_multiplier=1,  # 公平调度，每次只预取 1 个任务

    # 超时设置
    task_time_limit=1800,  # 硬超时 30 分钟
    task_soft_time_limit=1500,  # 软超时 25 分钟

    # 结果过期时间
    result_expires=86400,  # 结果保留 24 小时

    # 重试设置
    task_default_retry_delay=60,  # 默认 60 秒后重试
    task_max_retries=3,  # 最大重试 3 次

    # Worker 设置
    worker_max_tasks_per_child=100,  # 每个 worker 子进程处理 100 个任务后重启（防内存泄漏）
    worker_concurrency=4,  # worker 并发数

    # 路由设置（可选：将不同任务路由到不同队列）
    task_routes={
        'tasks.workflow_tasks.*': {'queue': 'workflow'},
        'tasks.embedding_tasks.*': {'queue': 'embedding'},
        'tasks.scheduled.*': {'queue': 'scheduled'},
    },

    # 定时任务调度（Celery Beat）
    beat_schedule={
        'generate-pending-embeddings': {
            'task': 'tasks.scheduled.generate_pending_embeddings',
            'schedule': crontab(minute='*/5'),  # 每 5 分钟执行一次
        },
        'cleanup-expired-results': {
            'task': 'tasks.scheduled.cleanup_expired_results',
            'schedule': crontab(hour=3, minute=0),  # 每天凌晨 3 点执行
        },
        'cleanup-stale-workflow-runs': {
            'task': 'tasks.scheduled.cleanup_stale_workflow_runs',
            'schedule': crontab(hour=4, minute=0),  # 每天凌晨 4 点执行
        },
        'dispatch-due-schedule-plans': {
            'task': 'tasks.scheduled.dispatch_due_schedule_plans',
            'schedule': crontab(minute='*'),  # 每分钟检查到期的定时触发计划
        },
    },
)

# Windows 下 prefork/billiard spawn 会出现 fast_trace_task
# 「not enough values to unpack (expected 3, got 0)」，导致所有入队任务直接失败，
# 因此该平台强制使用 solo 池；Linux/macOS 保持 prefork 多进程。
celery_app.conf.update(
    **({'worker_pool': 'solo', 'worker_concurrency': 1} if os.name == 'nt' else {}),
)


# ============================================================
# 启动时的信号处理
# ============================================================

@celery_app.task(bind=True)
def debug_task(self):
    """调试任务 —— 用于验证 Celery 是否正常工作"""
    print(f'Request: {self.request!r}')
    return {'status': 'ok', 'task_id': self.request.id}


if __name__ == '__main__':
    # 直接运行此文件可启动 worker
    celery_app.start()
