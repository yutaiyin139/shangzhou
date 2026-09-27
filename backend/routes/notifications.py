# -*- coding: utf-8 -*-
"""通知中心路由 - 提供用户通知的查询、标记已读、清除等功能"""

import json
import uuid
from flask import jsonify, request
from config import get_db
from utils.helpers import _safe_uid

NOTIFICATIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS user_notifications (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    type VARCHAR(30) DEFAULT 'info',
    title VARCHAR(255) NOT NULL,
    message TEXT,
    link VARCHAR(500) DEFAULT '',
    is_read TINYINT(1) DEFAULT 0,
    source_type VARCHAR(50) DEFAULT '',
    source_id VARCHAR(100) DEFAULT '',
    extra_data TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    read_at DATETIME DEFAULT NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_is_read (is_read),
    INDEX idx_created_at (created_at),
    INDEX idx_user_read (user_id, is_read)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def _ensure_table():
    try:
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(NOTIFICATIONS_TABLE_SQL)
            db.commit()
        finally:
            db.close()
    except Exception:
        pass


def _get_user_id():
    """通知中心的身份：只认登录 token 里的 user_id（= dify_accounts.id）。

    两个已经拆掉的写法：
    - getattr(g, 'user_id', None)：全仓没有任何地方写过 g.user_id，这个分支永远进不了；
      真正在填 request.user 的是 utils/api_guard.py 的 before_request。
    - 拿不到就当空串回退到 ?uid= / body.uid：那等于任何人传别人的账号 id 就能读
      别人通知、把别人通知标已读/清空。
    """
    return _safe_uid(None)


def register_notification_routes(app):
    _ensure_table()

    @app.route('/api/notifications', methods=['GET'])
    def get_notifications():
        user_id = _get_user_id()
        if not user_id:
            return jsonify({'code': 401, 'msg': '未登录', 'data': None})
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        page = max(1, request.args.get('page', 1, type=int))
        page_size = min(50, request.args.get('page_size', 20, type=int))
        offset = (page - 1) * page_size
        db = get_db()
        try:
            cur = db.cursor()
            where = "WHERE user_id = %s"
            params = [user_id]
            if unread_only:
                where += " AND is_read = 0"
            cur.execute(f"SELECT COUNT(*) as cnt FROM user_notifications {where}", params)
            total = cur.fetchone()['cnt']
            cur.execute("SELECT COUNT(*) as cnt FROM user_notifications WHERE user_id = %s AND is_read = 0", [user_id])
            unread_count = cur.fetchone()['cnt']
            cur.execute(
                f"SELECT id, type, title, message, link, is_read, source_type, source_id, extra_data, created_at, read_at FROM user_notifications {where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
                params + [page_size, offset]
            )
            items = cur.fetchall()
            notifications = []
            for item in items:
                notifications.append({
                    'id': item['id'], 'type': item['type'], 'title': item['title'],
                    'message': item['message'] or '', 'link': item['link'] or '',
                    'is_read': bool(item['is_read']),
                    'source_type': item['source_type'] or '',
                    'source_id': item['source_id'] or '',
                    'extra_data': json.loads(item['extra_data']) if item['extra_data'] else {},
                    'created_at': str(item['created_at']),
                    'read_at': str(item['read_at']) if item['read_at'] else None,
                })
            return jsonify({'code': 200, 'msg': 'success', 'data': {
                'total': total, 'unread_count': unread_count,
                'page': page, 'page_size': page_size, 'items': notifications,
            }})
        finally:
            db.close()

    @app.route('/api/notifications/unread-count', methods=['GET'])
    def get_unread_count():
        user_id = _get_user_id()
        if not user_id:
            return jsonify({'code': 200, 'msg': 'success', 'data': {'unread_count': 0}})
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute("SELECT COUNT(*) as cnt FROM user_notifications WHERE user_id = %s AND is_read = 0", [user_id])
            return jsonify({'code': 200, 'msg': 'success', 'data': {'unread_count': cur.fetchone()['cnt']}})
        finally:
            db.close()

    @app.route('/api/notifications/<notif_id>/read', methods=['POST'])
    def mark_as_read(notif_id):
        user_id = _get_user_id()
        if not user_id:
            return jsonify({'code': 401, 'msg': '未登录', 'data': None})
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute("UPDATE user_notifications SET is_read = 1, read_at = NOW() WHERE id = %s AND user_id = %s", [notif_id, user_id])
            db.commit()
            return jsonify({'code': 200, 'msg': 'success', 'data': {'updated': cur.rowcount}})
        finally:
            db.close()

    @app.route('/api/notifications/read-all', methods=['POST'])
    def mark_all_read():
        user_id = _get_user_id()
        if not user_id:
            return jsonify({'code': 401, 'msg': '未登录', 'data': None})
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute("UPDATE user_notifications SET is_read = 1, read_at = NOW() WHERE user_id = %s AND is_read = 0", [user_id])
            db.commit()
            return jsonify({'code': 200, 'msg': 'success', 'data': {'updated': cur.rowcount}})
        finally:
            db.close()

    @app.route('/api/notifications/<notif_id>', methods=['DELETE'])
    def delete_notification(notif_id):
        user_id = _get_user_id()
        if not user_id:
            return jsonify({'code': 401, 'msg': '未登录', 'data': None})
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute("DELETE FROM user_notifications WHERE id = %s AND user_id = %s", [notif_id, user_id])
            db.commit()
            return jsonify({'code': 200, 'msg': 'success', 'data': {'deleted': cur.rowcount}})
        finally:
            db.close()

    @app.route('/api/notifications', methods=['POST'])
    def create_notification():
        data = request.get_json(silent=True) or {}
        # 只能给自己发：data.user_id 是调用方填的，接受它就等于任意人往任意账号
        # 的收件箱里写消息（诱导点击类钓鱼）。服务端内部发送请走 app.add_notification。
        user_id = _get_user_id()
        if not user_id:
            return jsonify({'code': 401, 'msg': '未登录', 'data': None})
        title = data.get('title', '')
        if not title:
            return jsonify({'code': 400, 'msg': '缺少 title', 'data': None})
        notif_id = str(uuid.uuid4())
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                "INSERT INTO user_notifications (id, user_id, type, title, message, link, source_type, source_id, extra_data) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                [notif_id, user_id, data.get('type', 'info'), title, data.get('message', ''), data.get('link', ''), data.get('source_type', ''), data.get('source_id', ''), json.dumps(data.get('extra_data', {})) if data.get('extra_data') else None]
            )
            db.commit()
            return jsonify({'code': 200, 'msg': 'success', 'data': {'id': notif_id}})
        finally:
            db.close()

    @app.route('/api/notifications/clear', methods=['POST'])
    def clear_notifications():
        user_id = _get_user_id()
        if not user_id:
            return jsonify({'code': 401, 'msg': '未登录', 'data': None})
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute("DELETE FROM user_notifications WHERE user_id = %s", [user_id])
            db.commit()
            return jsonify({'code': 200, 'msg': 'success', 'data': {'deleted': cur.rowcount}})
        finally:
            db.close()

    def add_notification(user_id, title, message='', notif_type='info', link='', source_type='', source_id='', extra_data=None):
        if not user_id or not title:
            return None
        notif_id = str(uuid.uuid4())
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                "INSERT INTO user_notifications (id, user_id, type, title, message, link, source_type, source_id, extra_data) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                [notif_id, user_id, notif_type, title, message, link, source_type, source_id, json.dumps(extra_data) if extra_data else None]
            )
            db.commit()
            return notif_id
        except Exception:
            return None
        finally:
            db.close()

    app.add_notification = add_notification
