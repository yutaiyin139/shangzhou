# -*- coding: utf-8 -*-
"""
WebSocket 推送模块 —— 基于 Flask-SocketIO 的实时通信

功能:
    1. 工作流执行进度实时推送
    2. Embedding 生成进度实时推送
    3. 系统通知推送
    4. 在线用户状态管理

使用方式:
    1. 在 app.py 中初始化:
       from utils.ws import init_socketio
       socketio = init_socketio(app)

    2. 在任务中推送:
       from utils.ws import emit_workflow_progress
       emit_workflow_progress(run_id, {'event': 'node_complete', ...})

    3. 前端连接:
       const socket = io();
       socket.on('workflow_progress', (data) => { ... });
"""

import os
import sys
import json
import threading

# 确保 backend 目录在 sys.path 中
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# ============================================================
# SocketIO 实例（延迟初始化）
# ============================================================

_socketio = None
_redis_listener_thread = None


def init_socketio(app=None):
    """
    初始化 SocketIO

    参数:
        app: Flask 应用实例（可选，延迟初始化时可不传）

    返回:
        SocketIO 实例
    """
    global _socketio

    if _socketio is not None:
        return _socketio

    try:
        from flask_socketio import SocketIO, emit, join_room, leave_room
        from flask import request

        _socketio = SocketIO(
            app,
            cors_allowed_origins='*',
            async_mode='threading',  # 使用线程模式（与 Flask 开发服务器兼容）
            logger=False,
            engineio_logger=False,
            ping_timeout=60,
            ping_interval=25,
        )

        # 注册事件处理器
        _register_socketio_events(_socketio)

        # 启动 Redis 订阅监听器
        _start_redis_listener()

        return _socketio

    except ImportError:
        # Flask-SocketIO 未安装，返回 None
        return None


def get_socketio():
    """获取 SocketIO 实例"""
    return _socketio


# ============================================================
# SocketIO 事件注册
# ============================================================

def _register_socketio_events(socketio):
    """注册 SocketIO 事件处理器"""

    @socketio.on('connect')
    def handle_connect():
        """客户端连接"""
        from flask import request
        # 可以在这里进行身份验证
        return {'status': 'connected', 'sid': request.sid}

    @socketio.on('disconnect')
    def handle_disconnect():
        """客户端断开连接"""
        pass

    @socketio.on('subscribe_workflow')
    def handle_subscribe_workflow(data):
        """
        订阅工作流进度

        参数: {run_id: str}
        """
        from flask_socketio import join_room, emit
        from flask import request

        run_id = data.get('run_id', '')
        if run_id:
            room = f'wf:{run_id}'
            join_room(room)
            emit('subscribed', {'run_id': run_id, 'room': room})

            # 推送当前最新状态
            try:
                from utils.redis_cache import get_redis
                r = get_redis()
                status = r.get(f'wf:status:{run_id}')
                if status:
                    emit('workflow_progress', json.loads(status))
            except Exception:
                pass

    @socketio.on('unsubscribe_workflow')
    def handle_unsubscribe_workflow(data):
        """
        取消订阅工作流进度

        参数: {run_id: str}
        """
        from flask_socketio import leave_room, emit

        run_id = data.get('run_id', '')
        if run_id:
            room = f'wf:{run_id}'
            leave_room(room)
            emit('unsubscribed', {'run_id': run_id})

    @socketio.on('subscribe_embedding')
    def handle_subscribe_embedding(data):
        """
        订阅 Embedding 进度

        参数: {dataset_id: str}
        """
        from flask_socketio import join_room, emit

        dataset_id = data.get('dataset_id', '')
        if dataset_id:
            room = f'emb:{dataset_id}'
            join_room(room)
            emit('subscribed', {'dataset_id': dataset_id, 'room': room})

    @socketio.on('unsubscribe_embedding')
    def handle_unsubscribe_embedding(data):
        """
        取消订阅 Embedding 进度

        参数: {dataset_id: str}
        """
        from flask_socketio import leave_room, emit

        dataset_id = data.get('dataset_id', '')
        if dataset_id:
            room = f'emb:{dataset_id}'
            leave_room(room)
            emit('unsubscribed', {'dataset_id': dataset_id})


# ============================================================
# 推送函数
# ============================================================

def emit_workflow_progress(run_id, data):
    """
    推送工作流执行进度

    参数:
        run_id: 工作流运行 ID
        data: 进度数据字典
    """
    if _socketio is None:
        return

    try:
        room = f'wf:{run_id}'
        _socketio.emit('workflow_progress', data, room=room, namespace='/')
    except Exception:
        pass


def emit_embedding_progress(dataset_id, data):
    """
    推送 Embedding 生成进度

    参数:
        dataset_id: 数据集 ID
        data: 进度数据字典
    """
    if _socketio is None:
        return

    try:
        room = f'emb:{dataset_id}'
        _socketio.emit('embedding_progress', data, room=room, namespace='/')
    except Exception:
        pass


def emit_system_notification(data):
    """
    推送系统通知（广播）

    参数:
        data: 通知数据字典 {type, title, message, level}
    """
    if _socketio is None:
        return

    try:
        _socketio.emit('system_notification', data, broadcast=True, namespace='/')
    except Exception:
        pass


def emit_task_status(task_id, status, result=None):
    """
    推送任务状态更新

    参数:
        task_id: Celery 任务 ID
        status: 任务状态
        result: 任务结果（可选）
    """
    if _socketio is None:
        return

    try:
        room = f'task:{task_id}'
        data = {
            'task_id': task_id,
            'status': status,
            'result': result,
        }
        _socketio.emit('task_status', data, room=room, namespace='/')
    except Exception:
        pass


# ============================================================
# Redis 订阅监听器 —— 将 Redis Pub/Sub 消息转发到 WebSocket
# ============================================================

def _start_redis_listener():
    """启动 Redis 订阅监听器（在后台线程中运行）"""
    global _redis_listener_thread

    if _redis_listener_thread is not None and _redis_listener_thread.is_alive():
        return

    _redis_listener_thread = threading.Thread(
        target=_redis_listener_loop,
        daemon=True,
        name='ws-redis-listener',
    )
    _redis_listener_thread.start()


def _redis_listener_loop():
    """
    Redis 订阅监听循环

    订阅以下频道:
        - wf:progress:* (工作流进度)
        - emb:progress:* (Embedding 进度)
    """
    try:
        from utils.redis_cache import get_redis
        r = get_redis()
        pubsub = r.pubsub()

        # 订阅模式
        pubsub.psubscribe('wf:progress:*')
        pubsub.psubscribe('emb:progress:*')

        for message in pubsub.listen():
            if message['type'] not in ('pmessage', 'message'):
                continue

            try:
                channel = message.get('channel', '')
                if isinstance(channel, bytes):
                    channel = channel.decode('utf-8')

                data = json.loads(message.get('data', '{}'))

                # 根据频道类型分发
                if channel.startswith('wf:progress:'):
                    run_id = channel.split(':')[-1]
                    emit_workflow_progress(run_id, data)
                elif channel.startswith('emb:progress:'):
                    dataset_id = channel.split(':')[-1]
                    emit_embedding_progress(dataset_id, data)

            except Exception:
                continue

    except Exception:
        pass


# ============================================================
# 在线用户管理
# ============================================================

_online_users = {}
_users_lock = threading.Lock()


def add_online_user(sid, user_info=None):
    """
    添加在线用户

    参数:
        sid: SocketIO 会话 ID
        user_info: 用户信息字典
    """
    with _users_lock:
        _online_users[sid] = {
            'sid': sid,
            'info': user_info or {},
            'connected_at': __import__('time').time(),
        }


def remove_online_user(sid):
    """
    移除在线用户

    参数:
        sid: SocketIO 会话 ID
    """
    with _users_lock:
        _online_users.pop(sid, None)


def get_online_users():
    """获取在线用户列表"""
    with _users_lock:
        return list(_online_users.values())


def get_online_user_count():
    """获取在线用户数量"""
    with _users_lock:
        return len(_online_users)
