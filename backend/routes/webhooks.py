# -*- coding: utf-8 -*-
"""Webhook 路由 —— 工作流 Webhook 触发器管理"""
import json
import uuid
import secrets
import string
from flask import Blueprint, request, jsonify
from datetime import datetime

from models.tables import WEBHOOKS_TABLE_SQL, WEBHOOK_LOGS_TABLE_SQL
from config import get_db
from utils.auth import login_required

bp = Blueprint('webhooks', __name__)

# ============================================================
# 初始化表
# ============================================================

def init_tables():
    """初始化 Webhook 相关表"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(WEBHOOKS_TABLE_SQL)
        cur.execute(WEBHOOK_LOGS_TABLE_SQL)
        db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()

init_tables()

# ============================================================
# 辅助函数
# ============================================================

def _generate_webhook_key():
    """生成唯一 Webhook 密钥"""
    return 'wh-' + ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(24))

def _row_to_webhook(row):
    """数据库行转 Webhook 字典"""
    return {
        'id': row['id'],
        'app_id': row['app_id'],
        'name': row['name'],
        'description': row['description'] or '',
        'webhook_key': row['webhook_key'],
        'trigger_url': row['trigger_url'],
        'input_schema': json.loads(row['input_schema'] or '{}'),
        'is_active': bool(row['is_active']),
        'call_count': row['call_count'] or 0,
        'last_called_at': str(row['last_called_at']) if row['last_called_at'] else '',
        'last_status': row['last_status'] or '',
        'created_at': str(row['created_at']),
        'updated_at': str(row['updated_at']),
    }

def _get_webhook_by_id(webhook_id):
    """根据 ID 获取 Webhook"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT * FROM webhooks WHERE id = %s', (webhook_id,))
        return cur.fetchone()
    finally:
        db.close()

def _get_webhook_by_key(webhook_key):
    """根据密钥获取 Webhook"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT * FROM webhooks WHERE webhook_key = %s AND is_active = 1', (webhook_key,))
        return cur.fetchone()
    finally:
        db.close()

# ============================================================
# Webhook CRUD
# ============================================================

@bp.route('/api/webhooks', methods=['GET'])
@login_required
def list_webhooks():
    """列出所有 Webhook"""
    app_id = request.args.get('app_id', '')
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)

    where = []
    params = []
    if app_id:
        where.append(r'app_id = %s')
        params.append(app_id)

    where_sql = 'WHERE ' + ' AND '.join(where) if where else ''
    offset = (page - 1) * page_size

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT COUNT(*) as total FROM webhooks ' + where_sql, params)
        total = cur.fetchone()['total']

        cur.execute(
            r'SELECT * FROM webhooks ' + where_sql +
            r' ORDER BY created_at DESC LIMIT %s OFFSET %s',
            params + [page_size, offset]
        )
        items = [_row_to_webhook(r) for r in cur.fetchall()]
        return jsonify(code=200, data={
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
        })
    finally:
        db.close()


@bp.route('/api/webhooks/<webhook_id>', methods=['GET'])
@login_required
def get_webhook(webhook_id):
    """获取单个 Webhook 详情"""
    row = _get_webhook_by_id(webhook_id)
    if not row:
        return jsonify(code=404, msg='Webhook 不存在')
    return jsonify(code=200, data=_row_to_webhook(row))


@bp.route('/api/webhooks', methods=['POST'])
@login_required
def create_webhook():
    """创建新 Webhook"""
    body = request.get_json() or {}
    app_id = (body.get('app_id') or '').strip()
    name = (body.get('name') or '').strip()

    if not app_id:
        return jsonify(code=400, msg='应用 ID 不能为空')
    if not name:
        return jsonify(code=400, msg='Webhook 名称不能为空')

    webhook_id = str(uuid.uuid4())
    webhook_key = _generate_webhook_key()
    trigger_url = request.host_url.rstrip('/') + f'/api/webhooks/trigger/{webhook_key}'
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''INSERT INTO webhooks
                       (id, app_id, name, description, webhook_key, trigger_url,
                        input_schema, is_active, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, 1, %s, %s)''',
                    (
                        webhook_id, app_id, name,
                        body.get('description', ''),
                        webhook_key, trigger_url,
                        json.dumps(body.get('input_schema', {}), ensure_ascii=False),
                        now, now,
                    ))
        db.commit()
        return jsonify(code=200, msg='创建成功', data={
            'id': webhook_id,
            'name': name,
            'webhook_key': webhook_key,
            'trigger_url': trigger_url,
        })
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=str(e))
    finally:
        db.close()


@bp.route('/api/webhooks/<webhook_id>', methods=['PUT'])
@login_required
def update_webhook(webhook_id):
    """更新 Webhook"""
    row = _get_webhook_by_id(webhook_id)
    if not row:
        return jsonify(code=404, msg='Webhook 不存在')

    body = request.get_json() or {}
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''UPDATE webhooks SET
                       name = %s, description = %s, input_schema = %s,
                       is_active = %s, updated_at = %s
                       WHERE id = %s''',
                    (
                        body.get('name', row['name']),
                        body.get('description', row['description'] or ''),
                        json.dumps(body.get('input_schema', json.loads(row['input_schema'] or '{}')), ensure_ascii=False),
                        1 if body.get('is_active', bool(row['is_active'])) else 0,
                        now,
                        webhook_id,
                    ))
        db.commit()
        return jsonify(code=200, msg='更新成功')
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=str(e))
    finally:
        db.close()


@bp.route('/api/webhooks/<webhook_id>', methods=['DELETE'])
@login_required
def delete_webhook(webhook_id):
    """删除 Webhook"""
    row = _get_webhook_by_id(webhook_id)
    if not row:
        return jsonify(code=404, msg='Webhook 不存在')

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'DELETE FROM webhooks WHERE id = %s', (webhook_id,))
        db.commit()
        return jsonify(code=200, msg='删除成功')
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=str(e))
    finally:
        db.close()


@bp.route('/api/webhooks/<webhook_id>/regenerate-key', methods=['POST'])
@login_required
def regenerate_key(webhook_id):
    """重新生成 Webhook 密钥"""
    row = _get_webhook_by_id(webhook_id)
    if not row:
        return jsonify(code=404, msg='Webhook 不存在')

    new_key = _generate_webhook_key()
    trigger_url = request.host_url.rstrip('/') + f'/api/webhooks/trigger/{new_key}'
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'UPDATE webhooks SET webhook_key = %s, trigger_url = %s, updated_at = %s WHERE id = %s',
                    (new_key, trigger_url, now, webhook_id))
        db.commit()
        return jsonify(code=200, msg='密钥已更新', data={'webhook_key': new_key, 'trigger_url': trigger_url})
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=str(e))
    finally:
        db.close()


# ============================================================
# Webhook 触发端点（公开访问）
# ============================================================

@bp.route('/api/webhooks/trigger/<webhook_key>', methods=['POST'])
def trigger_webhook(webhook_key):
    """触发 Webhook 执行工作流"""
    import time
    start_time = time.time()

    row = _get_webhook_by_key(webhook_key)
    if not row:
        return jsonify(code=404, msg='Webhook 不存在或已停用')

    body = request.get_json() or {}
    request_headers = dict(request.headers)

    # 记录调用日志
    log_id = str(uuid.uuid4())
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    elapsed_ms = int((time.time() - start_time) * 1000)

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''INSERT INTO webhook_logs
                       (id, webhook_id, trigger_key, request_body, request_headers,
                        status, response_code, error_message, elapsed_ms, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                    (
                        log_id, row['id'], webhook_key,
                        json.dumps(body, ensure_ascii=False),
                        json.dumps(request_headers, ensure_ascii=False),
                        'success', 200, '', elapsed_ms, now,
                    ))
        # 更新调用计数
        cur.execute(r'''UPDATE webhooks SET
                       call_count = call_count + 1,
                       last_called_at = %s,
                       last_status = "success"
                       WHERE id = %s''', (now, row['id']))
        db.commit()
    except Exception:
        pass
    finally:
        db.close()

    # 触发工作流执行
    try:
        from engine.workflow_runner import run_workflow
        status, result = run_workflow(row['app_id'], body)
        elapsed_ms = int((time.time() - start_time) * 1000)

        # 更新日志
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''UPDATE webhook_logs SET
                           status = %s, response_code = %s,
                           error_message = %s, elapsed_ms = %s
                           WHERE id = %s''',
                        (
                            'success' if status in (200, 201) else 'error',
                            status,
                            '' if status in (200, 201) else str(result)[:500],
                            elapsed_ms,
                            log_id,
                        ))
            db.commit()
        except Exception:
            pass
        finally:
            db.close()

        if status in (200, 201):
            return jsonify(code=200, msg='执行成功', data=result)
        return jsonify(code=status, msg='执行失败', data=result)
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''UPDATE webhook_logs SET
                           status = "error", error_message = %s, elapsed_ms = %s
                           WHERE id = %s''',
                        (str(e)[:500], elapsed_ms, log_id))
            db.commit()
        except Exception:
            pass
        finally:
            db.close()
        return jsonify(code=500, msg=f'执行错误: {str(e)}')


# ============================================================
# Webhook 调用日志
# ============================================================

@bp.route('/api/webhooks/<webhook_id>/logs', methods=['GET'])
@login_required
def list_webhook_logs(webhook_id):
    """获取 Webhook 调用日志"""
    row = _get_webhook_by_id(webhook_id)
    if not row:
        return jsonify(code=404, msg='Webhook 不存在')

    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    offset = (page - 1) * page_size

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT COUNT(*) as total FROM webhook_logs WHERE webhook_id = %s', (webhook_id,))
        total = cur.fetchone()['total']

        cur.execute(
            r'SELECT * FROM webhook_logs WHERE webhook_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s',
            (webhook_id, page_size, offset)
        )
        items = []
        for r in cur.fetchall():
            items.append({
                'id': r['id'],
                'webhook_id': r['webhook_id'],
                'status': r['status'],
                'response_code': r['response_code'],
                'error_message': r['error_message'] or '',
                'elapsed_ms': r['elapsed_ms'] or 0,
                'created_at': str(r['created_at']),
            })
        return jsonify(code=200, data={
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
        })
    finally:
        db.close()


# ============================================================
# 注册路由
# ============================================================

def register_webhook_routes(app):
    """注册 Webhook 路由"""
    app.register_blueprint(bp)
