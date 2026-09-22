# -*- coding: utf-8 -*-
"""触发器订阅管理 API —— 订阅 schedule/webhook/plugin 触发结果并外发通知

订阅方式：
    email   触发完成后发送邮件通知（subscriber_target 为邮箱地址）
    webhook 触发完成后回调 URL（POST 运行结果 JSON，走 SSRF 安全校验）
    api     仅记录，供外部轮询（subscriber_target 为自定义标识）

端点：
    GET    /api/workflows/<app_id>/trigger-subscriptions     列表
    POST   /api/workflows/<app_id>/trigger-subscriptions     新建
    PUT    /api/trigger-subscriptions/<sub_id>               更新（启停/目标）
    DELETE /api/trigger-subscriptions/<sub_id>               删除
    GET    /api/trigger-subscriptions/<sub_id>/logs          该订阅关联的触发日志
"""
import re
import uuid
from datetime import datetime

from flask import jsonify, request

from config import get_db
from models.tables import TRIGGER_SUBSCRIPTIONS_TABLE_SQL

TRIGGER_TYPES = ('schedule', 'webhook', 'plugin')
SUBSCRIBER_TYPES = ('email', 'webhook', 'api')
EMAIL_RE = re.compile(r'^[\w.+-]+@[\w-]+(\.[\w-]+)+$')


def _ensure_table():
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(TRIGGER_SUBSCRIPTIONS_TABLE_SQL)
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


def _is_uuid(s):
    return bool(re.match(r'^[0-9a-fA-F-]{36}$', s or ''))


def _validate_target(subscriber_type, target):
    """校验 subscriber_target 合法性，返回错误消息或 None"""
    if not target or not str(target).strip():
        return 'subscriber_target 不能为空'
    target = str(target).strip()
    if subscriber_type == 'email':
        if not EMAIL_RE.match(target):
            return '邮箱地址格式不正确'
    elif subscriber_type == 'webhook':
        if not target.startswith(('http://', 'https://')):
            return '回调地址必须是 http(s) URL'
        from utils.ssrf import is_safe_url
        try:
            if not is_safe_url(target):
                return '回调地址未通过 SSRF 安全校验（内网/环回地址不允许）'
        except Exception:
            return '回调地址校验失败'
    elif subscriber_type == 'api':
        if len(target) > 200:
            return 'API 标识长度不能超过 200'
    return None


def _resolve_trigger(db, app_id, trigger_type, target_id):
    """校验目标触发器存在，返回 (node_id, node_title) 或 None"""
    cur = db.cursor()
    if trigger_type == 'schedule':
        cur.execute(
            'SELECT node_id, node_title FROM workflow_schedule_plans WHERE id = %s AND app_id = %s',
            (target_id, app_id))
    elif trigger_type == 'webhook':
        cur.execute(
            'SELECT NULL AS node_id, name AS node_title FROM webhooks WHERE id = %s AND app_id = %s',
            (target_id, app_id))
    else:  # plugin：应用下存在工作流定义即可
        cur.execute(
            "SELECT id AS node_id, '' AS node_title FROM dify_workflows WHERE app_id = %s LIMIT 1",
            (app_id,))
        row = cur.fetchone()
        return (None, None) if row else None
    row = cur.fetchone()
    if not row:
        return None
    return (row.get('node_id'), row.get('node_title') or '')


def register_trigger_subscription_routes(app):
    """注册触发器订阅管理路由"""

    @app.route('/api/workflows/<app_id>/trigger-subscriptions', methods=['GET'])
    def list_trigger_subscriptions(app_id):
        """列出应用的触发器订阅"""
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        _ensure_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                'SELECT * FROM trigger_subscriptions WHERE app_id = %s'
                ' ORDER BY created_at DESC',
                (app_id,))
            return jsonify(code=200, data=[dict(r) for r in cur.fetchall()])
        finally:
            db.close()

    @app.route('/api/workflows/<app_id>/trigger-subscriptions', methods=['POST'])
    def create_trigger_subscription(app_id):
        """新建触发器订阅"""
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        body = request.json or {}
        trigger_type = (body.get('trigger_type') or '').strip()
        target_id = (body.get('target_id') or '').strip()
        subscriber_type = (body.get('subscriber_type') or '').strip()
        subscriber_target = (body.get('subscriber_target') or '').strip()
        enabled = 1 if body.get('enabled', True) else 0

        if trigger_type not in TRIGGER_TYPES:
            return jsonify(code=400, msg=f'trigger_type 必须是 {TRIGGER_TYPES} 之一')
        if subscriber_type not in SUBSCRIBER_TYPES:
            return jsonify(code=400, msg=f'subscriber_type 必须是 {SUBSCRIBER_TYPES} 之一')
        if not _is_uuid(target_id):
            return jsonify(code=400, msg='target_id 必须是 UUID')
        err = _validate_target(subscriber_type, subscriber_target)
        if err:
            return jsonify(code=400, msg=err)

        _ensure_table()
        db = get_db()
        try:
            cur = db.cursor()
            resolved = _resolve_trigger(db, app_id, trigger_type, target_id)
            if not resolved:
                return jsonify(code=404, msg='目标触发器不存在')
            node_id, node_title = resolved

            # 幂等：同 target + subscriber 不重复创建
            cur.execute(
                'SELECT id FROM trigger_subscriptions WHERE app_id = %s AND trigger_type = %s'
                ' AND target_id = %s AND subscriber_type = %s AND subscriber_target = %s',
                (app_id, trigger_type, target_id, subscriber_type, subscriber_target))
            exists = cur.fetchone()
            if exists:
                return jsonify(code=200, msg='订阅已存在', data=dict(
                    id=exists['id'], duplicated=True))

            sub_id = str(uuid.uuid4())
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute(
                'INSERT INTO trigger_subscriptions'
                ' (id, app_id, trigger_type, target_id, node_id, node_title,'
                '  subscriber_type, subscriber_target, enabled, created_at, updated_at)'
                ' VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (sub_id, app_id, trigger_type, target_id, node_id, node_title,
                 subscriber_type, subscriber_target, enabled, now, now))
            db.commit()
            return jsonify(code=200, data={'id': sub_id})
        finally:
            db.close()

    @app.route('/api/trigger-subscriptions/<sub_id>', methods=['PUT'])
    def update_trigger_subscription(sub_id):
        """更新订阅（启停 / 修改通知目标）"""
        body = request.json or {}
        _ensure_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('SELECT * FROM trigger_subscriptions WHERE id = %s', (sub_id,))
            sub = cur.fetchone()
            if not sub:
                return jsonify(code=404, msg='订阅不存在')

            sets, params = [], []
            if 'enabled' in body:
                sets.append('enabled = %s')
                params.append(1 if body['enabled'] else 0)
            if 'subscriber_target' in body:
                err = _validate_target(sub['subscriber_type'], body['subscriber_target'])
                if err:
                    return jsonify(code=400, msg=err)
                sets.append('subscriber_target = %s')
                params.append(str(body['subscriber_target']).strip())
            if not sets:
                return jsonify(code=400, msg='无可更新字段（enabled / subscriber_target）')

            cur.execute('UPDATE trigger_subscriptions SET ' + ', '.join(sets) + ' WHERE id = %s',
                        params + [sub_id])
            db.commit()
            return jsonify(code=200, msg='更新成功')
        finally:
            db.close()

    @app.route('/api/trigger-subscriptions/<sub_id>', methods=['DELETE'])
    def delete_trigger_subscription(sub_id):
        """删除订阅"""
        _ensure_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('DELETE FROM trigger_subscriptions WHERE id = %s', (sub_id,))
            db.commit()
            if cur.rowcount == 0:
                return jsonify(code=404, msg='订阅不存在')
            return jsonify(code=200, msg='删除成功')
        finally:
            db.close()

    @app.route('/api/trigger-subscriptions/<sub_id>/logs', methods=['GET'])
    def trigger_subscription_logs(sub_id):
        """该订阅关联的触发日志（按底层 plan/webhook 过滤）"""
        _ensure_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('SELECT * FROM trigger_subscriptions WHERE id = %s', (sub_id,))
            sub = cur.fetchone()
            if not sub:
                return jsonify(code=404, msg='订阅不存在')

            page = max(int(request.args.get('page', 1) or 1), 1)
            page_size = min(int(request.args.get('page_size', 20) or 20), 100)
            offset = (page - 1) * page_size

            if sub['trigger_type'] == 'schedule':
                cond, param = 'plan_id = %s', sub['target_id']
            elif sub['trigger_type'] == 'webhook':
                cond, param = 'webhook_id = %s', sub['target_id']
            else:
                cond, param = 'app_id = %s', sub['app_id']

            cur.execute(f'SELECT COUNT(*) AS c FROM workflow_trigger_logs WHERE {cond}', (param,))
            total = cur.fetchone()['c']
            cur.execute(
                f'SELECT * FROM workflow_trigger_logs WHERE {cond}'
                ' ORDER BY triggered_at DESC LIMIT %s OFFSET %s',
                (param, page_size, offset))
            return jsonify(code=200, data={
                'items': [dict(r) for r in cur.fetchall()],
                'total': total, 'page': page, 'page_size': page_size,
            })
        finally:
            db.close()
