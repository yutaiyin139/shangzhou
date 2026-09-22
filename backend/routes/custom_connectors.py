# -*- coding: utf-8 -*-
"""自定义连接器路由"""

from flask import jsonify, request
from config import get_db
from models.tables import CUSTOM_CONNECTORS_TABLE_SQL

CC_TYPES = ('http', 'mcp', 'database', 'other')
CC_AUTHS = ('none', 'api_key', 'bearer')


def _ensure_cc_table():
    db = get_db()
    try:
        db.cursor().execute(CUSTOM_CONNECTORS_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def _cc_conn():
    _ensure_cc_table()
    return get_db()


def _cc_public(r):
    """自定义连接器 → 前端结构（auth_value 明文不回传）"""
    return {'id': r['id'], 'name': r['name'], 'type': r['ctype'], 'endpoint': r['endpoint'] or '',
            'auth_type': r['auth_type'], 'auth_configured': bool(r['auth_value']),
            'description': r['description'] or '',
            'created_at': str(r['created_at']), 'updated_at': str(r['updated_at'])}


def _cc_payload(body, require_auth_value=True, keep_value=None):
    """校验并整理自定义连接器表单"""
    name = (body.get('name') or '').strip()
    if not name:
        return None, '请填写连接器名称'
    ctype = body.get('type') or 'http'
    if ctype not in CC_TYPES:
        ctype = 'http'
    auth_type = body.get('auth_type') or 'none'
    if auth_type not in CC_AUTHS:
        auth_type = 'none'
    auth_value = (body.get('auth_value') or '').strip()
    if auth_type != 'none':
        if not auth_value:
            if require_auth_value:
                return None, '请填写认证凭据'
            auth_value = keep_value or ''
    return {'name': name, 'ctype': ctype, 'endpoint': (body.get('endpoint') or '').strip(),
            'auth_type': auth_type, 'auth_value': auth_value,
            'description': (body.get('description') or '').strip()}, None


def register_custom_connector_routes(app):
    """注册自定义连接器相关路由"""

    @app.route('/api/connectors/custom', methods=['GET'])
    def list_custom_connectors():
        """自定义连接器列表"""
        db = _cc_conn()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM custom_connectors ORDER BY id DESC')
            return jsonify(code=200, data=[_cc_public(r) for r in cur.fetchall()])
        finally:
            db.close()

    @app.route('/api/connectors/custom', methods=['POST'])
    def create_custom_connector():
        """新建自定义连接器"""
        body = request.get_json(silent=True) or {}
        payload, err = _cc_payload(body)
        if err:
            return jsonify(code=400, msg=err)
        db = _cc_conn()
        try:
            cur = db.cursor()
            cur.execute(r'INSERT INTO custom_connectors (name, ctype, endpoint, auth_type, auth_value, description) '
                        r'VALUES (%s, %s, %s, %s, %s, %s)',
                        (payload['name'], payload['ctype'], payload['endpoint'],
                         payload['auth_type'], payload['auth_value'], payload['description']))
            db.commit()
            return jsonify(code=200, msg='已创建', data={'id': cur.lastrowid})
        finally:
            db.close()

    @app.route('/api/connectors/custom/<int:cid>', methods=['PUT'])
    def update_custom_connector(cid):
        """编辑自定义连接器（凭据留空时保留原值）"""
        body = request.get_json(silent=True) or {}
        db = _cc_conn()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT auth_value FROM custom_connectors WHERE id = %s', (cid,))
            row = cur.fetchone()
            if not row:
                return jsonify(code=404, msg='连接器不存在')
            payload, err = _cc_payload(body, require_auth_value=False, keep_value=row['auth_value'])
            if err:
                return jsonify(code=400, msg=err)
            cur.execute(r'UPDATE custom_connectors SET name=%s, ctype=%s, endpoint=%s, auth_type=%s, auth_value=%s, description=%s WHERE id=%s',
                        (payload['name'], payload['ctype'], payload['endpoint'],
                         payload['auth_type'], payload['auth_value'], payload['description'], cid))
            db.commit()
            return jsonify(code=200, msg='已保存')
        finally:
            db.close()

    @app.route('/api/connectors/custom/<int:cid>', methods=['DELETE'])
    def delete_custom_connector(cid):
        """删除自定义连接器"""
        db = _cc_conn()
        try:
            cur = db.cursor()
            cur.execute(r'DELETE FROM custom_connectors WHERE id = %s', (cid,))
            db.commit()
            return jsonify(code=200, msg='已删除')
        finally:
            db.close()
