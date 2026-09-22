# -*- coding: utf-8 -*-
"""
异步任务管理路由 —— 查询和管理 Celery 异步任务

API 列表:
    GET  /api/tasks/<task_id>              —— 查询任务状态
    POST /api/tasks/<task_id>/cancel       —— 取消任务
    GET  /api/tasks/active                 —— 获取活跃任务列表
    GET  /api/tasks/scheduled/logs         —— 获取定时任务执行日志
    GET  /api/tasks/health                 —— 系统健康检查
"""

from flask import jsonify, request


def register_task_routes(app):
    """注册异步任务管理路由"""

    @app.route('/api/tasks/<task_id>', methods=['GET'])
    def get_task_status(task_id):
        """
        查询异步任务状态

        支持查询任意 Celery 任务的状态（工作流、Embedding、定时任务）

        响应:
            进行中: {code: 200, data: {task_id, state: 'RUNNING', status: 'running', meta: {...}}}
            成功:   {code: 200, data: {task_id, state: 'SUCCESS', status: 'succeeded', result: {...}}}
            失败:   {code: 200, data: {task_id, state: 'FAILURE', status: 'failed', error: '...'}}
            待执行: {code: 200, data: {task_id, state: 'PENDING', status: 'pending', meta: {}}}
        """
        from tasks.celery_app import celery_app
        result = celery_app.AsyncResult(task_id)

        response = {
            'task_id': task_id,
            'state': result.state,
        }

        if result.state == 'PENDING':
            response['status'] = 'pending'
            response['message'] = '任务等待执行中'
        elif result.state == 'STARTED':
            response['status'] = 'started'
            response['meta'] = result.info if isinstance(result.info, dict) else {}
        elif result.state == 'RUNNING':
            response['status'] = 'running'
            response['meta'] = result.info if isinstance(result.info, dict) else {}
        elif result.state == 'SUCCESS':
            response['status'] = 'succeeded'
            response['result'] = result.result
        elif result.state == 'FAILURE':
            response['status'] = 'failed'
            response['error'] = str(result.info)[:500] if result.info else '未知错误'
        elif result.state == 'RETRY':
            response['status'] = 'retrying'
            response['meta'] = result.info if isinstance(result.info, dict) else {}
        elif result.state == 'REVOKED':
            response['status'] = 'cancelled'
            response['message'] = '任务已取消'
        else:
            response['status'] = result.state.lower()
            response['meta'] = str(result.info)[:500] if result.info else {}

        return jsonify(code=200, data=response)

    @app.route('/api/tasks/<task_id>/cancel', methods=['POST'])
    def cancel_task(task_id):
        """
        取消异步任务

        响应: {code: 200, msg: '已发送取消信号'} 或 {code: 400, msg: '任务已完成或不存在'}
        """
        from tasks.celery_app import celery_app
        from celery.task.control import revoke

        result = celery_app.AsyncResult(task_id)

        if result.ready():
            return jsonify(code=400, msg='任务已完成或不存在，无法取消')

        try:
            revoke(task_id, terminate=True)
            return jsonify(code=200, msg='已发送取消信号')
        except Exception as e:
            return jsonify(code=500, msg='取消失败: %s' % str(e))

    @app.route('/api/tasks/active', methods=['GET'])
    def get_active_tasks():
        """
        获取当前活跃的任务列表

        响应: {code: 200, data: {active_count, tasks: [{id, name, args, kwargs, time_start, worker}]}}
        """
        from tasks.celery_app import celery_app

        try:
            inspector = celery_app.control.inspect()
            active = inspector.active() or {}

            tasks = []
            for worker_name, worker_tasks in active.items():
                for task in worker_tasks:
                    tasks.append({
                        'id': task.get('id', ''),
                        'name': task.get('name', ''),
                        'args': str(task.get('args', []))[:200],
                        'kwargs': str(task.get('kwargs', {}))[:200],
                        'worker': worker_name,
                        'time_start': task.get('time_start', ''),
                    })

            return jsonify(code=200, data={
                'active_count': len(tasks),
                'tasks': tasks,
            })
        except Exception as e:
            return jsonify(code=200, data={
                'active_count': 0,
                'tasks': [],
                'message': f'无法获取活跃任务: {str(e)}',
            })

    @app.route('/api/tasks/scheduled/logs', methods=['GET'])
    def get_scheduled_logs():
        """
        获取定时任务执行日志

        参数:
            count: 返回的日志数量（默认 20）

        响应: {code: 200, data: [{task, timestamp, data}]}
        """
        count = int(request.args.get('count', 20))

        from tasks.scheduled import get_scheduled_task_logs
        logs = get_scheduled_task_logs(count)

        return jsonify(code=200, data=logs)

    @app.route('/api/tasks/health', methods=['GET'])
    def tasks_health_check():
        """
        异步任务系统健康检查

        检查项:
            1. Redis 连接
            2. Celery Worker 状态
            3. Celery Beat 状态

        响应: {code: 200, data: {redis, celery_worker, celery_beat, timestamp}}
        """
        from datetime import datetime
        result = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'redis': False,
            'celery_worker': False,
            'celbeat': False,
        }

        # 检查 Redis
        try:
            from utils.redis_cache import redis_available
            result['redis'] = redis_available()
        except Exception as e:
            result['redis_error'] = str(e)[:100]

        # 检查 Celery Worker
        try:
            from tasks.celery_app import celery_app
            inspector = celery_app.control.inspect()
            stats = inspector.stats()
            if stats:
                result['celery_worker'] = True
                result['workers'] = list(stats.keys())
        except Exception as e:
            result['celery_worker_error'] = str(e)[:100]

        return jsonify(code=200, data=result)
