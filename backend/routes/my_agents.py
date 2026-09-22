# -*- coding: utf-8 -*-
"""我的智能体 / 工作流整合路由（MySQL 版，脱离 Dify）"""

import re
from flask import jsonify, request
from config import get_db
from utils.helpers import now, _safe_uid
from models.tables import DIFY_APPS_TABLE_SQL, DIFY_ACCOUNTS_TABLE_SQL


def _ensure_my_agent_tables():
    """确保我的智能体相关表已创建"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(DIFY_APPS_TABLE_SQL)
        cur.execute(DIFY_ACCOUNTS_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def register_my_agents_routes(app):
    """注册我的智能体与工作流相关路由"""

    @app.route('/api/my-agents', methods=['GET'])
    def my_agents():
        """整合当前登录用户创建的单智能体/多智能体/工作流应用"""
        _ensure_my_agent_tables()
        uid = _safe_uid(request.args.get('uid'))
        from routes.agents import _ensure_agents_table
        _ensure_agents_table()
        items = []
        # 单/多智能体：agents 表按 owner 过滤
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r"SELECT id, name, type, status, updated_at FROM agents WHERE type IN ('single','multi') AND owner = %s ORDER BY updated_at DESC", (uid,))
            for r in cur.fetchall():
                items.append({
                    'id': r['id'], 'name': r['name'], 'type': r['type'], 'status': r['status'],
                    'updated_at': r['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if r['updated_at'] else ''
                })
        finally:
            db.close()
        # 工作流应用：dify_apps 按创建账号过滤
        try:
            db = get_db()
            try:
                cur = db.cursor()
                # 使用 dify_accounts 表（users 表已合并）
                cur.execute(r"SELECT id FROM dify_accounts WHERE id = %s AND status = 'active'", (uid,))
                accs = cur.fetchall()
            finally:
                db.close()
                if accs:
                    db = get_db()
                    try:
                        cur = db.cursor()
                        cur.execute(r'''SELECT id, name, mode, icon, description, updated_at
                                           FROM dify_apps WHERE status = 'normal' AND enable_api = true AND created_by = %s
                                           ORDER BY updated_at DESC''', (accs[0]['id'],))
                        rows = cur.fetchall()
                    finally:
                        db.close()
                    for a in rows:
                        items.append({
                            'id': str(a['id']), 'name': a['name'], 'type': 'workflow',
                            'status': 'published', 'mode': a['mode'],
                            'icon': a['icon'] or '🤖', 'desc': a['description'] or '',
                            'updated_at': a['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if a['updated_at'] else ''
                        })
        except Exception:
            pass  # 不可用时静默跳过工作流部分
        items.sort(key=lambda x: x.get('updated_at') or '', reverse=True)
        return jsonify(code=200, data=items)

    @app.route('/api/workflows-app/<wid>', methods=['DELETE'])
    def delete_workflow_app_mine(wid):
        """软删除工作流应用"""
        _ensure_my_agent_tables()
        if not re.fullmatch(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', wid):
            return jsonify(code=400, msg='非法的工作流 ID')
        try:
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(r"UPDATE dify_apps SET status = 'archived' WHERE id = %s AND status = 'normal'", (wid,))
                db.commit()
                affected = cur.rowcount
            finally:
                db.close()
        except Exception as e:
            return jsonify(code=500, msg='删除失败: %s' % e)
        if not affected:
            return jsonify(code=404, msg='工作流不存在或已删除')
        return jsonify(code=200, msg='删除成功')

    @app.route('/api/workflows-app', methods=['GET'])
    def list_workflow_apps():
        """从 MySQL 列出工作流应用"""
        _ensure_my_agent_tables()
        try:
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(r'''SELECT id, name, mode, icon, icon_type, description, updated_at
                                   FROM dify_apps WHERE status = 'normal' AND enable_api = true
                                   ORDER BY updated_at DESC''')
                apps = cur.fetchall()
            finally:
                db.close()
            return jsonify(code=200, data=[{
                'id': str(a['id']),
                'name': a['name'],
                'mode': a['mode'],
                'icon': a['icon'] or '🤖',
                'icon_type': a['icon_type'] or '',
                'desc': a['description'] or '',
                'updated_at': a['updated_at'].strftime('%Y/%m/%d %H:%M') if a['updated_at'] else ''
            } for a in apps])
        except Exception as e:
            return jsonify(code=500, msg='获取应用列表失败: %s' % e)
