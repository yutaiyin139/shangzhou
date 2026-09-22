# -*- coding: utf-8 -*-
"""公开分享路由 - 提供无需登录的对话和工作流访问"""

import json
import secrets
from datetime import datetime
from flask import jsonify, request
from config import get_db
from models.tables import (
    DIFY_APPS_TABLE_SQL,
    DIFY_WORKFLOWS_TABLE_SQL,
    DIFY_SITES_TABLE_SQL,
)
from engine.workflow_runner import run_workflow


# ============================================================
# 分享令牌存储（内存，重启后丢失，生产环境应使用数据库）
# ============================================================
_share_tokens = {
    # token: { type: 'chat'|'workflow', app_id, created_at, enabled }
}


def _ensure_share_tables():
    """确保分享相关表已创建"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(DIFY_APPS_TABLE_SQL)
        cur.execute(DIFY_WORKFLOWS_TABLE_SQL)
        cur.execute(DIFY_SITES_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def register_share_routes(app):
    """注册公开分享相关路由"""

    # ============================================================
    # 创建分享链接（需要登录，由应用页面调用）
    # ============================================================

    @app.route('/api/apps/<app_id>/share', methods=['POST'])
    def create_share_link(app_id):
        """为应用创建分享链接"""
        _ensure_share_tables()
        body = request.get_json() or {}
        share_type = body.get('type', 'chat')  # chat/workflow

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM dify_apps WHERE id = %s', (app_id,))
            app_info = cur.fetchone()
        finally:
            db.close()

        if not app_info:
            return jsonify(code=404, msg='应用不存在')

        # 生成分享令牌
        token = secrets.token_hex(16)
        _share_tokens[token] = {
            'type': share_type,
            'app_id': app_id,
            'app_name': app_info['name'],
            'description': app_info.get('description', ''),
            'created_at': datetime.now().isoformat(),
            'enabled': True
        }

        base_url = request.host_url.rstrip('/')
        share_url = f"{base_url}/#/share/{share_type}/{token}"

        return jsonify(code=200, data={
            'token': token,
            'share_url': share_url,
            'type': share_type
        })

    @app.route('/api/apps/<app_id>/share', methods=['GET'])
    def get_share_link(app_id):
        """获取应用的分享链接"""
        for token, info in _share_tokens.items():
            if info['app_id'] == app_id and info['enabled']:
                base_url = request.host_url.rstrip('/')
                return jsonify(code=200, data={
                    'token': token,
                    'share_url': f"{base_url}/#/share/{info['type']}/{token}",
                    'type': info['type'],
                    'enabled': True
                })
        return jsonify(code=404, msg='未找到分享链接')

    @app.route('/api/apps/<app_id>/share', methods=['DELETE'])
    def disable_share_link(app_id):
        """禁用应用的分享链接"""
        for token, info in _share_tokens.items():
            if info['app_id'] == app_id:
                info['enabled'] = False
                return jsonify(code=200, msg='已禁用')
        return jsonify(code=404, msg='未找到分享链接')

    # ============================================================
    # 公开访问接口（无需登录）
    # ============================================================

    @app.route('/api/share/chat/<token>/info', methods=['GET'])
    def get_shared_chat_info(token):
        """获取分享对话信息"""
        info = _share_tokens.get(token)
        if not info or not info['enabled'] or info['type'] != 'chat':
            return jsonify(code=404, msg='对话不存在或已过期')

        return jsonify(code=200, data={
            'name': info['app_name'],
            'description': info.get('description', ''),
            'type': 'chat'
        })

    @app.route('/api/share/chat/<token>/message', methods=['POST'])
    def shared_chat_message(token):
        """发送消息到分享的对话"""
        info = _share_tokens.get(token)
        if not info or not info['enabled'] or info['type'] != 'chat':
            return jsonify(code=404, msg='对话不存在或已过期')

        body = request.get_json() or {}
        message = (body.get('message') or '').strip()
        if not message:
            return jsonify(code=400, msg='请输入消息')

        # 调用工作流处理消息
        from routes.multi_agents import _multi_agent_dispatch, _load_multi_agent_config
        from routes.agents import _load_agent_config

        try:
            # 尝试作为多智能体处理
            cfg = _load_multi_agent_config(int(info['app_id']))
            if cfg:
                content, err, handled_by = _multi_agent_dispatch(int(info['app_id']), cfg, message)
                if err:
                    return jsonify(code=500, msg=err)
                return jsonify(code=200, data={'reply': content, 'handled_by': handled_by})

            # 尝试作为单智能体处理
            cfg = _load_agent_config(int(info['app_id']), 'single')
            if cfg:
                from utils.llm import _call_llm_with_config
                model_cfg = None
                db = get_db()
                try:
                    cur = db.cursor()
                    cur.execute(r'SELECT * FROM model_configs WHERE status = 1 LIMIT 1')
                    model_cfg = cur.fetchone()
                finally:
                    db.close()

                system_prompt = cfg.get('prompt', '')
                content, err = _call_llm_with_config(message, system_prompt, model_cfg)
                if err:
                    return jsonify(code=500, msg=err)
                return jsonify(code=200, data={'reply': content})

            return jsonify(code=404, msg='应用配置不存在')
        except Exception as e:
            return jsonify(code=500, msg='处理失败: ' + str(e))

    @app.route('/api/share/workflow/<token>/info', methods=['GET'])
    def get_shared_workflow_info(token):
        """获取分享工作流信息"""
        info = _share_tokens.get(token)
        if not info or not info['enabled'] or info['type'] != 'workflow':
            return jsonify(code=404, msg='工作流不存在或已过期')

        # 获取工作流的输入参数定义
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM dify_workflows WHERE app_id = %s', (info['app_id'],))
            wf = cur.fetchone()
        finally:
            db.close()

        inputs = []
        if wf and wf.get('graph'):
            try:
                graph = json.loads(wf['graph'])
                for node in graph.get('nodes', []):
                    if node.get('data', {}).get('type') == 'start':
                        variables = node.get('data', {}).get('variables', [])
                        for v in variables:
                            inputs.append({
                                'variable': v.get('variable', ''),
                                'label': v.get('label', v.get('variable', '')),
                                'type': v.get('type', 'string'),
                                'required': v.get('required', False),
                                'description': v.get('description', ''),
                                'default': v.get('default', '')
                            })
            except Exception:
                pass

        return jsonify(code=200, data={
            'app': {
                'name': info['app_name'],
                'description': info.get('description', '')
            },
            'inputs': inputs
        })

    @app.route('/api/share/workflow/<token>/run', methods=['POST'])
    def run_shared_workflow(token):
        """运行分享的工作流"""
        info = _share_tokens.get(token)
        if not info or not info['enabled'] or info['type'] != 'workflow':
            return jsonify(code=404, msg='工作流不存在或已过期')

        body = request.get_json() or {}
        inputs = body.get('inputs', {})
        start_time = datetime.now()

        try:
            status, result = run_workflow(info['app_id'], inputs)
            elapsed = (datetime.now() - start_time).total_seconds() * 1000

            if status in (200, 201):
                return jsonify(code=200, data={
                    'outputs': result.get('outputs', {}),
                    'elapsed_time': int(elapsed)
                })
            return jsonify(code=status, msg=result.get('error', '运行失败'))
        except Exception as e:
            return jsonify(code=500, msg='运行失败: ' + str(e))
