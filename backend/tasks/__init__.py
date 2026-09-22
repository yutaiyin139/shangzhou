# -*- coding: utf-8 -*-
"""
异步任务模块 —— 基于 Celery + Redis 的异步任务队列

模块列表:
- celery_app: Celery 应用实例
- workflow_tasks: 工作流异步执行任务
- embedding_tasks: Embedding 异步生成任务
- scheduled: 定时任务（Celery Beat）
"""

from tasks.celery_app import celery_app

__all__ = ['celery_app']
