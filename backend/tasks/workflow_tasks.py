# -*- coding: utf-8 -*-
"""
工作流异步执行任务 —— 通过 Celery 异步执行工作流

使用方式:
    from tasks.workflow_tasks import run_workflow_async

    # 异步执行工作流
    task = run_workflow_async.delay(app_id, inputs, user)
    print(f"任务 ID: {task.id}")

    # 查询任务状态
    result = run_workflow_async.AsyncResult(task.id)

    # 取消任务
    task.revoke(terminate=True)
"""

import os
import sys
import json
import time
import uuid
from datetime import datetime

# 确保 backend 目录在 sys.path 中
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from tasks.celery_app import celery_app
from config import get_db


# ============================================================
# 工作流异步执行任务
# ============================================================

@celery_app.task(bind=True, name='tasks.workflow_tasks.run_workflow_async',
                 queue='workflow', max_retries=2, default_retry_delay=30)
def run_workflow_async(self, app_id, inputs, user='szagent-user'):
    """
    异步执行工作流

    参数:
        app_id: 应用 ID
        inputs: 输入参数字典
        user: 用户标识

    返回:
        dict: {id, status, outputs, elapsed_time, total_tokens, total_steps}

    状态更新:
        - 通过 self.update_state() 更新任务状态
        - 通过 Redis 发布进度事件（供 WebSocket 推送）
    """
    from engine.workflow_runner import (
        run_workflow, _execute_workflow_graph, _execute_chat_graph,
        _identify_iteration_subgraphs
    )

    run_id = str(uuid.uuid4())
    start_time = time.time()

    # 更新任务状态为「开始」
    self.update_state(
        state='STARTED',
        meta={
            'run_id': run_id,
            'app_id': app_id,
            'status': 'starting',
            'message': '正在加载工作流...',
            'progress': 0,
        }
    )

    # 加载工作流
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('SELECT * FROM dify_workflows WHERE app_id = %s LIMIT 1', (app_id,))
        wf_row = cur.fetchone()
        if not wf_row:
            return {'id': run_id, 'status': 'failed', 'message': '工作流不存在'}

        cur.execute('SELECT * FROM dify_apps WHERE id = %s LIMIT 1', (app_id,))
        app_row = cur.fetchone()
        if not app_row:
            return {'id': run_id, 'status': 'failed', 'message': '应用不存在'}

        cur.execute('SELECT * FROM dify_app_model_configs WHERE app_id = %s LIMIT 1', (app_id,))
        model_cfg_row = cur.fetchone()

        graph = json.loads(wf_row['graph'] or '{}')
        mode = app_row['mode']
    finally:
        db.close()

    # 创建运行记录
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('''
            INSERT INTO dify_workflow_runs
            (id, app_id, tenant_id, workflow_id, status, inputs, created_by, created_at)
            VALUES (%s, %s, %s, %s, 'running', %s, %s, %s)
        ''', (run_id, app_id, wf_row['tenant_id'], wf_row['id'],
              json.dumps(inputs, ensure_ascii=False), user, ts))
        db.commit()
    finally:
        db.close()

    # 计算总节点数（用于进度追踪）
    total_nodes = len(graph.get('nodes', []))
    completed_nodes = 0

    # 更新任务状态为「运行中」
    self.update_state(
        state='RUNNING',
        meta={
            'run_id': run_id,
            'app_id': app_id,
            'status': 'running',
            'message': '正在执行工作流...',
            'progress': 0,
            'total_nodes': total_nodes,
            'completed_nodes': 0,
        }
    )

    # 发布进度事件到 Redis
    _publish_progress(run_id, {
        'event': 'workflow_start',
        'run_id': run_id,
        'app_id': app_id,
        'total_nodes': total_nodes,
    })

    try:
        # 执行工作流图
        if mode in ('workflow', 'completion'):
            result = _execute_workflow_graph(graph, inputs, model_cfg_row, app_id, run_id)
        else:
            result = _execute_chat_graph(graph, inputs, model_cfg_row, app_id, run_id)

        elapsed = time.time() - start_time
        completed_nodes = total_nodes

        # 检查是否需要暂停等待 Human Input
        if isinstance(result, dict) and result.get('__human_input_pause__'):
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute('''
                    UPDATE dify_workflow_runs
                    SET status='waiting', outputs=%s, elapsed_time=%s
                    WHERE id=%s
                ''', (json.dumps(result, ensure_ascii=False), elapsed, run_id))
                db.commit()
            finally:
                db.close()

            _publish_progress(run_id, {
                'event': 'workflow_waiting',
                'run_id': run_id,
                'status': 'waiting',
                'message': '等待用户输入',
            })

            _finalize_trigger_log(self.request.id, run_id, 'waiting',
                                  elapsed_ms=int(elapsed * 1000))

            return {
                'id': run_id,
                'status': 'waiting',
                'message': '等待用户输入',
                'human_input': {
                    'config': result.get('__human_input_config__', {}),
                    'node_id': result.get('__human_input_node_id__', ''),
                    'output_var': result.get('__human_input_output_var__', 'human_input'),
                },
                'elapsed_time': elapsed,
            }

        # 更新运行记录为成功
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('''
                UPDATE dify_workflow_runs
                SET status='succeeded', outputs=%s, elapsed_time=%s, finished_at=%s
                WHERE id=%s
            ''', (json.dumps(result, ensure_ascii=False), elapsed,
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S'), run_id))
            db.commit()
        finally:
            db.close()

        # 发布完成事件
        _publish_progress(run_id, {
            'event': 'workflow_complete',
            'run_id': run_id,
            'status': 'succeeded',
            'elapsed_time': elapsed,
        })

        _finalize_trigger_log(self.request.id, run_id, 'succeeded',
                              elapsed_ms=int(elapsed * 1000))

        return {
            'id': run_id,
            'status': 'succeeded',
            'outputs': result,
            'elapsed_time': elapsed,
            'total_tokens': result.get('total_tokens', 0) if isinstance(result, dict) else 0,
            'total_steps': completed_nodes,
        }

    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = str(e)[:500]

        # 更新运行记录为失败
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('''
                UPDATE dify_workflow_runs
                SET status='failed', error=%s, elapsed_time=%s, finished_at=%s
                WHERE id=%s
            ''', (error_msg, elapsed,
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S'), run_id))
            db.commit()
        finally:
            db.close()

        # 发布错误事件
        _publish_progress(run_id, {
            'event': 'workflow_error',
            'run_id': run_id,
            'status': 'failed',
            'error': error_msg,
        })

        # 重试逻辑
        if self.request.retries < self.max_retries:
            self.update_state(
                state='RETRY',
                meta={
                    'run_id': run_id,
                    'status': 'retrying',
                    'message': f'执行失败，正在重试 ({self.request.retries + 1}/{self.max_retries})...',
                    'error': error_msg,
                }
            )
            raise self.retry(exc=e)

        return {
            'id': run_id,
            'status': 'failed',
            'message': error_msg,
            'elapsed_time': elapsed,
        }


def _finalize_trigger_log(task_id, run_id, status, error_message=None, elapsed_ms=0):
    """触发器来源的任务结束时回填 workflow_trigger_logs"""
    if not task_id:
        return
    try:
        from engine.trigger_engine import finalize_trigger_log
        finalize_trigger_log(task_id, run_id=run_id, status=status,
                             error_message=error_message, elapsed_ms=elapsed_ms)
    except Exception:
        pass


@celery_app.task(bind=True, name='tasks.workflow_tasks.run_workflow_stream_async',
                 queue='workflow', max_retries=2, default_retry_delay=30)
def run_workflow_stream_async(self, app_id, inputs, user='szagent-user'):
    """
    异步流式执行工作流 —— 通过 Redis 发布 SSE 事件

    与 run_workflow_async 的区别:
    - 逐节点发布进度事件
    - 支持实时查看执行进度
    - 事件通过 Redis Pub/Sub 推送（前端可通过 WebSocket 订阅）

    参数:
        app_id: 应用 ID
        inputs: 输入参数字典
        user: 用户标识

    返回:
        dict: {id, status, outputs, elapsed_time, total_tokens, total_steps, events}
    """
    from engine.workflow_runner import run_workflow_stream

    run_id = str(uuid.uuid4())
    start_time = time.time()
    events = []

    self.update_state(
        state='STARTED',
        meta={
            'run_id': run_id,
            'app_id': app_id,
            'status': 'starting',
            'message': '正在启动流式执行...',
            'progress': 0,
        }
    )

    _publish_progress(run_id, {
        'event': 'workflow_start',
        'run_id': run_id,
        'app_id': app_id,
    })

    try:
        # 使用流式执行引擎
        for evt in run_workflow_stream(app_id, inputs, user):
            event_name = evt.get('event', 'message')
            event_data = evt.get('data', {})

            # 记录事件
            events.append(evt)

            # 发布到 Redis
            _publish_progress(run_id, {
                'event': event_name,
                'run_id': run_id,
                'data': event_data,
            })

            # 更新任务状态
            if event_name == 'node_start':
                self.update_state(
                    state='RUNNING',
                    meta={
                        'run_id': run_id,
                        'status': 'running',
                        'message': f"正在执行节点: {event_data.get('title', '')}",
                        'current_node': event_data.get('node_id', ''),
                    }
                )
            elif event_name == 'workflow_complete':
                elapsed = time.time() - start_time
                _publish_progress(run_id, {
                    'event': 'workflow_complete',
                    'run_id': run_id,
                    'status': 'succeeded',
                    'elapsed_time': elapsed,
                })
                return {
                    'id': run_id,
                    'status': 'succeeded',
                    'outputs': event_data.get('outputs', {}),
                    'elapsed_time': elapsed,
                    'total_tokens': event_data.get('total_tokens', 0),
                    'total_steps': event_data.get('total_steps', 0),
                }
            elif event_name == 'workflow_stopped':
                elapsed = time.time() - start_time
                return {
                    'id': run_id,
                    'status': 'stopped',
                    'message': '工作流已停止',
                    'elapsed_time': elapsed,
                }
            elif event_name == 'error':
                elapsed = time.time() - start_time
                error_msg = event_data.get('message', str(event_data))
                if self.request.retries < self.max_retries:
                    raise self.retry(exc=Exception(error_msg))
                return {
                    'id': run_id,
                    'status': 'failed',
                    'message': error_msg,
                    'elapsed_time': elapsed,
                }

        # 如果循环正常结束但没有 complete 事件
        elapsed = time.time() - start_time
        return {
            'id': run_id,
            'status': 'succeeded',
            'outputs': {},
            'elapsed_time': elapsed,
            'total_tokens': 0,
            'total_steps': 0,
        }

    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = str(e)[:500]

        _publish_progress(run_id, {
            'event': 'workflow_error',
            'run_id': run_id,
            'status': 'failed',
            'error': error_msg,
        })

        if self.request.retries < self.max_retries:
            self.update_state(
                state='RETRY',
                meta={
                    'run_id': run_id,
                    'status': 'retrying',
                    'message': f'执行失败，正在重试 ({self.request.retries + 1}/{self.max_retries})...',
                }
            )
            raise self.retry(exc=e)

        return {
            'id': run_id,
            'status': 'failed',
            'message': error_msg,
            'elapsed_time': elapsed,
        }


# ============================================================
# 辅助函数
# ============================================================

def _publish_progress(run_id, data):
    """
    发布进度事件到 Redis Pub/Sub

    前端可通过 WebSocket 订阅 channel: wf:progress:{run_id}
    获取实时执行进度
    """
    try:
        from utils.redis_cache import get_redis
        r = get_redis()
        channel = f'wf:progress:{run_id}'
        r.publish(channel, json.dumps(data, ensure_ascii=False))
        # 同时保存最新状态（带过期时间）
        r.setex(f'wf:status:{run_id}', 3600, json.dumps(data, ensure_ascii=False))
    except Exception:
        pass


def get_workflow_task_status(task_id):
    """
    查询工作流任务状态

    参数:
        task_id: Celery 任务 ID

    返回:
        dict: {task_id, state, status, result, meta}
    """
    result = run_workflow_async.AsyncResult(task_id)
    return {
        'task_id': task_id,
        'state': result.state,
        'status': result.info.get('status', '') if isinstance(result.info, dict) else str(result.info),
        'result': result.result if result.ready() else None,
        'meta': result.info if isinstance(result.info, dict) else {},
    }


def revoke_workflow_task(task_id, terminate=True):
    """
    取消工作流任务

    参数:
        task_id: Celery 任务 ID
        terminate: 是否强制终止正在执行的任务

    返回:
        bool: 是否成功发送取消信号
    """
    from celery.task.control import revoke
    revoke(task_id, terminate=terminate)
    return True
