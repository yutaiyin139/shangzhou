# -*- coding: utf-8 -*-
"""我的智能体 / 工作流整合路由（MySQL 版，脱离 Dify）"""

import re
import logging
from flask import jsonify, request
from config import get_db
from utils.helpers import _safe_uid
from models.tables import DIFY_APPS_TABLE_SQL

logger = logging.getLogger('szagent.my_agents')


def _ensure_my_agent_tables():
    """确保本模块要读的应用表已创建

    不再在这里保 dify_accounts：那个 DDL 是“本模块要拿 uid 去 accounts 反查”时代
    加上的，现在只读 agents / dify_apps，而且 accounts 已由 auth、account 路由保证。
    """
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(DIFY_APPS_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def register_my_agents_routes(app):
    """注册我的智能体与工作流相关路由"""

    @app.route('/api/my-agents', methods=['GET'])
    def my_agents():
        """整合当前登录用户创建的单智能体/多智能体/工作流应用"""
        _ensure_my_agent_tables()
        uid = _safe_uid(None)
        from routes.agents import _ensure_agents_table
        _ensure_agents_table()
        items = []
        if not uid:
            return jsonify(code=200, data=items)
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
        # 工作流应用：dify_apps.created_by 存的就是 dify_accounts.id（同一个 UUID），
        # 直接比对即可。以前这里先拿 uid 去 dify_accounts 反查一次“是不是个活账号”
        # 再用查回来的 id 去 dify_apps —— 那一转是“users.id 与 account_id 不同源”时代的
        # 中转，现在两个列同源，多一次连库只是冗余。
        try:
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(r'''SELECT id, name, mode, icon, description, updated_at
                                   FROM dify_apps WHERE status = 'normal' AND enable_api = true AND created_by = %s
                                   ORDER BY updated_at DESC''', (uid,))
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
        except Exception as e:
            logger.warning('读取本人工作流应用失败（仅少了 workflow 一类，不阻断页内列表）: %s', str(e)[:200])
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
                # 开了归属校验后，列表不能再返回组织全量：否则普通用户会看到
                # “列表里看得见、点进去 403” 的割裂表现。非管理员只看自己创建的，
                # 再加无主应用（这类在归属校验里也是放行的，两边保持一致）。
                caller = getattr(request, 'user', None) or {}
                owner_sql = ''
                owner_params = []
                if (caller.get('role') or '') != 'admin' and caller.get('user_id'):
                    owner_sql = ' AND (created_by = %s OR created_by IS NULL OR created_by = %s)'
                    owner_params = [str(caller['user_id']), '']
                cur.execute(r'''SELECT id, name, mode, icon, icon_type, description, updated_at
                                   FROM dify_apps WHERE status = 'normal' AND enable_api = true''' 
                            + owner_sql + r' ORDER BY updated_at DESC', tuple(owner_params))
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
