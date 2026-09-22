# -*- coding: utf-8 -*-
"""工具插件与自动更新设置路由"""

import json
import uuid
from datetime import datetime

from flask import jsonify, request
from config import get_db
from utils.helpers import now
from models.tables import (
    TOOL_INSTALLS_TABLE_SQL, TOOL_SETTINGS_TABLE_SQL,
    TOOL_CALL_LOGS_TABLE_SQL, WORKFLOW_TOOLS_TABLE_SQL,
    TOOL_BUILTIN_PROVIDERS_TABLE_SQL, TOOL_API_PROVIDERS_TABLE_SQL,
    TOOL_WORKFLOW_PROVIDERS_TABLE_SQL, TOOL_MCP_PROVIDERS_TABLE_SQL
)
from models.builtin_tools import BUILTIN_TOOLS, TOOL_AUTO_UPDATE_DEFAULT


def _ensure_tool_installs_table():
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(TOOL_INSTALLS_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def _installed_tool_ids():
    """已安装的内置工具 id 集合"""
    _ensure_tool_installs_table()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT tool_id FROM tool_installs')
        return {row['tool_id'] for row in cur.fetchall()}
    finally:
        db.close()


def _ensure_tool_settings_table():
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(TOOL_SETTINGS_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def _ensure_tool_call_logs_table():
    """确保工具调用日志表存在"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(TOOL_CALL_LOGS_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def _ensure_workflow_tools_table():
    """确保工作流工具表存在"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(WORKFLOW_TOOLS_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def _ensure_tool_builtin_providers_table():
    """确保内置工具提供者表存在，并同步 builtin_tools.py 中的定义"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(TOOL_BUILTIN_PROVIDERS_TABLE_SQL)
        # 同步 builtin_tools.py 中的定义到数据库
        from models.builtin_tools import BUILTIN_TOOLS
        for t in BUILTIN_TOOLS:
            actions_json = json.dumps(t.get('tools', []), ensure_ascii=False)
            cur.execute(r'''INSERT IGNORE INTO tool_builtin_providers
                           (id, provider_name, provider_label, description, icon, icon_background,
                            category, actions_json, is_authenticated, status)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                        (t['id'], t['id'], t.get('name', t['id']),
                         t.get('description', ''), t.get('icon', '🔧'),
                         t.get('icon_background', '#E8F3FF'),
                         t.get('category', 'utility'), actions_json,
                         1 if t.get('need_auth') else 0, 'active'))
        db.commit()
    finally:
        db.close()


def _ensure_tool_api_providers_table():
    """确保 API 工具提供者表存在"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(TOOL_API_PROVIDERS_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def _ensure_tool_workflow_providers_table():
    """确保工作流工具提供者表存在"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(TOOL_WORKFLOW_PROVIDERS_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def _ensure_tool_mcp_providers_table():
    """确保 MCP 工具提供者表存在，并同步 mcp_servers 中的工具"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(TOOL_MCP_PROVIDERS_TABLE_SQL)
        # 尝试同步 MCP 服务器工具（如果 mcp_servers 表存在且有数据）
        try:
            cur.execute(r'SELECT id, name FROM mcp_servers WHERE enabled = 1')
            servers = cur.fetchall()
            for srv in servers:
                # 这里仅创建占位记录，实际工具列表通过 MCP 协议动态获取
                cur.execute(r'''INSERT IGNORE INTO tool_mcp_providers
                               (id, tenant_id, server_id, server_name, tool_name, tool_label, status)
                               VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                            (str(__import__('uuid').uuid4()), 'system', srv['id'],
                             srv['name'], '_placeholder_', '待同步', 'inactive'))
        except Exception:
            pass  # mcp_servers 表可能不存在，静默跳过
        db.commit()
    finally:
        db.close()


def log_tool_call(workflow_run_id, node_id, node_type, provider_id, tool_name,
                  parameters, result, status, error_message='', elapsed_ms=0):
    """
    记录工具调用日志。

    Args:
        workflow_run_id: 工作流运行 ID
        node_id: 节点 ID
        node_type: 节点类型 (tool/mcp/workflow 等)
        provider_id: 工具提供者 ID
        tool_name: 工具名称
        parameters: 调用参数 (dict)
        result: 调用结果
        status: success 或 error
        error_message: 错误信息
        elapsed_ms: 耗时毫秒

    Returns:
        log_id 或 None
    """
    _ensure_tool_call_logs_table()
    db = get_db()
    try:
        cur = db.cursor()
        log_id = str(uuid.uuid4())
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute(r'''INSERT INTO tool_call_logs
                       (id, workflow_run_id, node_id, node_type, provider_id, tool_name,
                        parameters, result, status, error_message, elapsed_ms, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                    (log_id, workflow_run_id, node_id, node_type, provider_id, tool_name,
                     json.dumps(parameters, ensure_ascii=False) if parameters else '',
                     str(result)[:2000] if result else '',
                     status, error_message[:500] if error_message else '',
                     elapsed_ms, ts))
        db.commit()
        return log_id
    except Exception:
        pass
    finally:
        db.close()


def register_tool_routes(app):
    """注册工具插件相关路由"""

    @app.route('/api/tools/builtin', methods=['GET'])
    def get_builtin_tools():
        """内置工具提供者列表（含 actions 与安装状态）"""
        installed = _installed_tool_ids()
        data = []
        for t in BUILTIN_TOOLS:
            item = dict(t)
            item['installed'] = t['id'] in installed
            data.append(item)
        return jsonify(code=200, data=data)

    @app.route('/api/tools/builtin/<tid>/tools', methods=['GET'])
    def get_builtin_tool_tools(tid):
        """单个内置工具的 action 列表（详情抽屉用）"""
        for t in BUILTIN_TOOLS:
            if t['id'] == tid:
                return jsonify(code=200, data=t['tools'])
        return jsonify(code=404, msg='工具不存在')

    @app.route('/api/tools/builtin/<tid>/install', methods=['POST'])
    def install_builtin_tool(tid):
        """安装内置工具"""
        if not any(t['id'] == tid for t in BUILTIN_TOOLS):
            return jsonify(code=404, msg='工具不存在')
        _ensure_tool_installs_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'INSERT IGNORE INTO tool_installs (tool_id, installed_at) VALUES (%s, %s)', (tid, now()))
            db.commit()
            return jsonify(code=200, msg='已安装')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    @app.route('/api/tools/builtin/<tid>/install', methods=['DELETE'])
    def uninstall_builtin_tool(tid):
        """卸载内置工具"""
        _ensure_tool_installs_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'DELETE FROM tool_installs WHERE tool_id = %s', (tid,))
            db.commit()
            return jsonify(code=200, msg='已卸载')
        finally:
            db.close()

    @app.route('/api/tools/auto-update', methods=['GET'])
    def get_tool_auto_update():
        """读取自动更新设置"""
        _ensure_tool_settings_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT mode, update_time, scope FROM tool_settings WHERE id = 1')
            row = cur.fetchone()
            if not row:
                return jsonify(code=200, data=dict(TOOL_AUTO_UPDATE_DEFAULT))
            return jsonify(code=200, data=row)
        finally:
            db.close()

    @app.route('/api/tools/auto-update', methods=['PUT'])
    def update_tool_auto_update():
        """保存自动更新设置"""
        d = request.get_json()
        mode = d.get('mode', 'patch')
        update_time = d.get('update_time', '19:45')
        scope = d.get('scope', 'all')
        if mode not in ('disabled', 'patch', 'latest'):
            return jsonify(code=400, msg='非法的更新模式')
        if scope not in ('all', 'exclude', 'only'):
            return jsonify(code=400, msg='非法的更新范围')
        _ensure_tool_settings_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''INSERT INTO tool_settings (id, mode, update_time, scope, updated_at)
                            VALUES (1, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE mode=%s, update_time=%s, scope=%s, updated_at=%s''',
                        (mode, update_time, scope, now(), mode, update_time, scope, now()))
            db.commit()
            return jsonify(code=200, msg='保存成功', data={'mode': mode, 'update_time': update_time, 'scope': scope})
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    # ============================================================
    # 工具调用日志 API
    # ============================================================

    @app.route('/api/tools/logs', methods=['GET'])
    def list_tool_logs():
        """查询工具调用日志（支持分页和过滤）"""
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        provider_id = request.args.get('provider_id', '')
        status = request.args.get('status', '')
        workflow_run_id = request.args.get('workflow_run_id', '')

        where = []
        params = []
        if provider_id:
            where.append(r'provider_id = %s')
            params.append(provider_id)
        if status:
            where.append(r'status = %s')
            params.append(status)
        if workflow_run_id:
            where.append(r'workflow_run_id = %s')
            params.append(workflow_run_id)

        where_sql = 'WHERE ' + ' AND '.join(where) if where else ''
        offset = (page - 1) * page_size

        _ensure_tool_call_logs_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT COUNT(*) as total FROM tool_call_logs ' + where_sql, params)
            total = cur.fetchone()['total']
            cur.execute(r'''SELECT * FROM tool_call_logs ''' + where_sql +
                        r' ORDER BY created_at DESC LIMIT %s OFFSET %s',
                        params + [page_size, offset])
            items = []
            for r in cur.fetchall():
                items.append({
                    'id': r['id'],
                    'workflow_run_id': r['workflow_run_id'],
                    'node_id': r['node_id'],
                    'node_type': r['node_type'],
                    'provider_id': r['provider_id'],
                    'tool_name': r['tool_name'],
                    'parameters': json.loads(r['parameters'] or '{}'),
                    'result': r['result'] or '',
                    'status': r['status'],
                    'error_message': r['error_message'] or '',
                    'elapsed_ms': r['elapsed_ms'],
                    'created_at': str(r['created_at']),
                })
            return jsonify(code=200, data={'items': items, 'total': total, 'page': page, 'page_size': page_size})
        finally:
            db.close()

    @app.route('/api/tools/logs/<log_id>', methods=['GET'])
    def get_tool_log_detail(log_id):
        """获取单条工具调用日志详情"""
        _ensure_tool_call_logs_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM tool_call_logs WHERE id = %s', (log_id,))
            r = cur.fetchone()
            if not r:
                return jsonify(code=404, msg='日志不存在')
            return jsonify(code=200, data={
                'id': r['id'],
                'workflow_run_id': r['workflow_run_id'],
                'node_id': r['node_id'],
                'node_type': r['node_type'],
                'provider_id': r['provider_id'],
                'tool_name': r['tool_name'],
                'parameters': json.loads(r['parameters'] or '{}'),
                'result': r['result'] or '',
                'status': r['status'],
                'error_message': r['error_message'] or '',
                'elapsed_ms': r['elapsed_ms'],
                'created_at': str(r['created_at']),
            })
        finally:
            db.close()

    @app.route('/api/tools/logs', methods=['DELETE'])
    def clear_tool_logs():
        """清空工具调用日志"""
        _ensure_tool_call_logs_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'DELETE FROM tool_call_logs')
            db.commit()
            return jsonify(code=200, msg='日志已清空')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    # ============================================================
    # 工作流作为工具 API
    # ============================================================

    @app.route('/api/tools/workflow', methods=['GET'])
    def list_workflow_tools():
        """列出所有工作流工具"""
        _ensure_workflow_tools_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM workflow_tools WHERE status = "active" ORDER BY created_at DESC')
            items = []
            for r in cur.fetchall():
                items.append({
                    'id': r['id'],
                    'app_id': r['app_id'],
                    'name': r['name'],
                    'description': r['description'],
                    'input_schema': json.loads(r['input_schema'] or '{}'),
                    'call_count': r['call_count'],
                    'created_at': str(r['created_at']),
                })
            return jsonify(code=200, data=items)
        finally:
            db.close()

    @app.route('/api/tools/workflow/<app_id>/publish', methods=['POST'])
    def publish_workflow_as_tool(app_id):
        """将工作流发布为工具"""
        # 加载应用信息
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('SELECT * FROM dify_apps WHERE id = %s LIMIT 1', (app_id,))
            app_info = cur.fetchone()
        finally:
            db.close()

        if not app_info:
            return jsonify(code=404, msg='应用不存在')

        # 加载工作流
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('SELECT * FROM dify_workflows WHERE app_id = %s LIMIT 1', (app_id,))
            wf = cur.fetchone()
        finally:
            db.close()

        if not wf:
            return jsonify(code=404, msg='工作流不存在')

        body = request.get_json() or {}
        name = (body.get('name') or app_info['name']).strip()
        description = (body.get('description') or app_info['description'] or '').strip()

        # 从 Start 节点提取输入参数
        graph = json.loads(wf['graph'] or '{}')
        input_schema = _extract_workflow_inputs(graph, app_info.get('mode', 'workflow'))

        # 生成 API token
        import secrets
        import string
        api_token = 'wt-' + ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(24))

        tool_id = str(uuid.uuid4())
        _ensure_workflow_tools_table()
        _ensure_tool_workflow_providers_table()
        db = get_db()
        try:
            cur = db.cursor()
            # 写入 workflow_tools 表
            cur.execute(r'''INSERT INTO workflow_tools
                           (id, app_id, name, description, input_schema, api_token)
                           VALUES (%s, %s, %s, %s, %s, %s)''',
                        (tool_id, app_id, name, description,
                         json.dumps(input_schema, ensure_ascii=False), api_token))
            # 同步写入 tool_workflow_providers 表
            provider_id = str(uuid.uuid4())
            cur.execute(r'''INSERT INTO tool_workflow_providers
                           (id, tenant_id, app_id, workflow_id, workflow_tool_id,
                            name, description, input_schema, status, created_by)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'active', %s)''',
                        (provider_id, 'system', app_id, wf['id'], tool_id,
                         name, description,
                         json.dumps(input_schema, ensure_ascii=False),
                         body.get('created_by', '')))
            db.commit()
            return jsonify(code=200, msg='已发布为工具', data={'id': tool_id, 'provider_id': provider_id, 'name': name, 'api_token': api_token})
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    @app.route('/api/tools/workflow/<tool_id>', methods=['DELETE'])
    def unpublish_workflow_tool(tool_id):
        """取消发布工作流工具"""
        _ensure_workflow_tools_table()
        _ensure_tool_workflow_providers_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'UPDATE workflow_tools SET status = "inactive" WHERE id = %s', (tool_id,))
            # 同步更新 tool_workflow_providers 状态
            cur.execute(r'UPDATE tool_workflow_providers SET status = "inactive" WHERE workflow_tool_id = %s', (tool_id,))
            db.commit()
            return jsonify(code=200, msg='已取消发布')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    @app.route('/api/tools/workflow/<tool_id>/invoke', methods=['POST'])
    def invoke_workflow_tool(tool_id):
        """调用工作流工具"""
        from engine.workflow_runner import run_workflow

        _ensure_workflow_tools_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM workflow_tools WHERE id = %s AND status = "active"', (tool_id,))
            tool = cur.fetchone()
        finally:
            db.close()

        if not tool:
            return jsonify(code=404, msg='工具不存在或已停用')

        body = request.get_json() or {}
        inputs = body.get('inputs') or {}

        # 执行工作流
        status, result = run_workflow(tool['app_id'], inputs)
        if status not in (200, 201):
            return jsonify(code=status, msg='执行失败', data=result)

        # 更新调用计数和统计
        _ensure_tool_workflow_providers_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'UPDATE workflow_tools SET call_count = call_count + 1 WHERE id = %s', (tool_id,))
            # 同步更新 tool_workflow_providers 统计
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute(r'''UPDATE tool_workflow_providers
                           SET call_count = call_count + 1,
                               last_called_at = %s,
                               avg_latency_ms = CASE
                                   WHEN avg_latency_ms = 0 THEN %s
                                   ELSE (avg_latency_ms * call_count + %s) / (call_count + 1)
                               END
                           WHERE workflow_tool_id = %s''',
                        (now_str, result.get('elapsed_ms', 0), result.get('elapsed_ms', 0), tool_id))
            db.commit()
        finally:
            db.close()

        return jsonify(code=200, data={'output': result.get('outputs', {}), 'status': 'success'})

    # ============================================================
    # 工具提供者管理 API（P0: 多提供者统一管理）
    # ============================================================

    @app.route('/api/tools/providers', methods=['GET'])
    def list_all_tool_providers():
        """列出所有工具提供者（按类型分组）"""
        _ensure_tool_builtin_providers_table()
        _ensure_tool_api_providers_table()
        _ensure_tool_workflow_providers_table()
        _ensure_tool_mcp_providers_table()

        tenant_id = request.args.get('tenant_id', 'system')
        result = {'builtin': [], 'api': [], 'workflow': [], 'mcp': []}

        db = get_db()
        try:
            cur = db.cursor()
            # 内置工具提供者
            cur.execute(r'''SELECT id, provider_name, provider_label, description, icon, icon_background,
                                  category, actions_json, is_authenticated, status, installed_at
                           FROM tool_builtin_providers WHERE status = 'active'
                           ORDER BY category, provider_label''')
            for r in cur.fetchall():
                result['builtin'].append({
                    'id': r['id'], 'provider_name': r['provider_name'],
                    'provider_label': r['provider_label'], 'description': r['description'],
                    'icon': r['icon'], 'icon_background': r['icon_background'],
                    'category': r['category'],
                    'actions': json.loads(r['actions_json'] or '[]'),
                    'is_authenticated': bool(r['is_authenticated']),
                    'status': r['status'], 'installed_at': str(r['installed_at'] or ''),
                })

            # API 工具提供者
            cur.execute(r'''SELECT id, name, description, icon, icon_background, server_url,
                                  auth_type, status, last_tested_at, created_at
                           FROM tool_api_providers WHERE tenant_id = %s AND status = 'active'
                           ORDER BY created_at DESC''', (tenant_id,))
            for r in cur.fetchall():
                result['api'].append({
                    'id': r['id'], 'name': r['name'], 'description': r['description'],
                    'icon': r['icon'], 'icon_background': r['icon_background'],
                    'server_url': r['server_url'], 'auth_type': r['auth_type'],
                    'status': r['status'], 'last_tested_at': str(r['last_tested_at'] or ''),
                    'created_at': str(r['created_at'] or ''),
                })

            # 工作流工具提供者
            cur.execute(r'''SELECT id, name, description, icon, icon_background, app_id,
                                  call_count, avg_latency_ms, status, last_called_at
                           FROM tool_workflow_providers WHERE tenant_id = %s AND status = 'active'
                           ORDER BY created_at DESC''', (tenant_id,))
            for r in cur.fetchall():
                result['workflow'].append({
                    'id': r['id'], 'name': r['name'], 'description': r['description'],
                    'icon': r['icon'], 'icon_background': r['icon_background'],
                    'app_id': r['app_id'], 'call_count': r['call_count'],
                    'avg_latency_ms': r['avg_latency_ms'], 'status': r['status'],
                    'last_called_at': str(r['last_called_at'] or ''),
                })

            # MCP 工具提供者
            cur.execute(r'''SELECT id, server_id, server_name, tool_name, tool_label,
                                  description, is_enabled, call_count, status
                           FROM tool_mcp_providers WHERE tenant_id = %s
                           ORDER BY server_name, tool_name''', (tenant_id,))
            for r in cur.fetchall():
                result['mcp'].append({
                    'id': r['id'], 'server_id': r['server_id'],
                    'server_name': r['server_name'], 'tool_name': r['tool_name'],
                    'tool_label': r['tool_label'], 'description': r['description'],
                    'is_enabled': bool(r['is_enabled']), 'call_count': r['call_count'],
                    'status': r['status'],
                })

            return jsonify(code=200, data=result)
        finally:
            db.close()

    @app.route('/api/tools/providers/builtin', methods=['GET'])
    def list_builtin_providers():
        """列出内置工具提供者"""
        _ensure_tool_builtin_providers_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''SELECT id, provider_name, provider_label, description, icon, icon_background,
                                  category, actions_json, is_authenticated, status
                           FROM tool_builtin_providers WHERE status = 'active'
                           ORDER BY category, provider_label''')
            items = []
            for r in cur.fetchall():
                items.append({
                    'id': r['id'], 'provider_name': r['provider_name'],
                    'provider_label': r['provider_label'], 'description': r['description'],
                    'icon': r['icon'], 'icon_background': r['icon_background'],
                    'category': r['category'],
                    'actions': json.loads(r['actions_json'] or '[]'),
                    'is_authenticated': bool(r['is_authenticated']),
                    'status': r['status'],
                })
            return jsonify(code=200, data=items)
        finally:
            db.close()

    @app.route('/api/tools/providers/api', methods=['GET'])
    def list_api_providers():
        """列出 API 工具提供者"""
        _ensure_tool_api_providers_table()
        tenant_id = request.args.get('tenant_id', 'system')
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''SELECT id, name, description, icon, icon_background, server_url,
                                  auth_type, status, last_tested_at, last_error, created_at
                           FROM tool_api_providers WHERE tenant_id = %s
                           ORDER BY created_at DESC''', (tenant_id,))
            items = []
            for r in cur.fetchall():
                items.append({
                    'id': r['id'], 'name': r['name'], 'description': r['description'],
                    'icon': r['icon'], 'icon_background': r['icon_background'],
                    'server_url': r['server_url'], 'auth_type': r['auth_type'],
                    'status': r['status'], 'last_tested_at': str(r['last_tested_at'] or ''),
                    'last_error': r['last_error'] or '',
                    'created_at': str(r['created_at'] or ''),
                })
            return jsonify(code=200, data=items)
        finally:
            db.close()

    @app.route('/api/tools/providers/api', methods=['POST'])
    def create_api_provider():
        """创建 API 工具提供者（OpenAPI 导入）"""
        _ensure_tool_api_providers_table()
        body = request.get_json()
        if not body:
            return jsonify(code=400, msg='请求体不能为空')

        name = (body.get('name') or '').strip()
        server_url = (body.get('server_url') or '').strip()
        if not name or not server_url:
            return jsonify(code=400, msg='名称和服务器 URL 必填')

        provider_id = str(uuid.uuid4())
        tenant_id = body.get('tenant_id', 'system')
        openapi_schema = body.get('openapi_schema', '')
        actions = body.get('actions', [])

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''INSERT INTO tool_api_providers
                           (id, tenant_id, name, description, icon, icon_background,
                            server_url, openapi_schema, actions_json, auth_type, headers_json,
                            timeout_ms, is_public, status, created_by)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                        (provider_id, tenant_id, name,
                         body.get('description', ''),
                         body.get('icon', '🔌'),
                         body.get('icon_background', '#FFF3E0'),
                         server_url,
                         json.dumps(openapi_schema, ensure_ascii=False) if isinstance(openapi_schema, dict) else openapi_schema,
                         json.dumps(actions, ensure_ascii=False),
                         body.get('auth_type', 'none'),
                         json.dumps(body.get('headers', {}), ensure_ascii=False),
                         body.get('timeout_ms', 30000),
                         1 if body.get('is_public') else 0,
                         'active',
                         body.get('created_by', '')))
            db.commit()
            return jsonify(code=200, msg='创建成功', data={'id': provider_id, 'name': name})
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='创建失败: ' + str(e))
        finally:
            db.close()

    @app.route('/api/tools/providers/api/<provider_id>', methods=['PUT'])
    def update_api_provider(provider_id):
        """更新 API 工具提供者"""
        _ensure_tool_api_providers_table()
        body = request.get_json()
        if not body:
            return jsonify(code=400, msg='请求体不能为空')

        db = get_db()
        try:
            cur = db.cursor()
            # 构建动态更新 SQL
            fields = []
            params = []
            for field in ['name', 'description', 'icon', 'icon_background', 'server_url',
                          'auth_type', 'timeout_ms', 'status']:
                if field in body:
                    fields.append(f'{field} = %s')
                    params.append(body[field])
            if 'actions' in body:
                fields.append('actions_json = %s')
                params.append(json.dumps(body['actions'], ensure_ascii=False))
            if 'headers' in body:
                fields.append('headers_json = %s')
                params.append(json.dumps(body['headers'], ensure_ascii=False))
            if 'is_public' in body:
                fields.append('is_public = %s')
                params.append(1 if body['is_public'] else 0)

            if not fields:
                return jsonify(code=400, msg='无更新字段')

            params.append(provider_id)
            cur.execute(f'''UPDATE tool_api_providers SET {', '.join(fields)}
                           WHERE id = %s''', params)
            db.commit()
            return jsonify(code=200, msg='更新成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='更新失败: ' + str(e))
        finally:
            db.close()

    @app.route('/api/tools/providers/api/<provider_id>', methods=['DELETE'])
    def delete_api_provider(provider_id):
        """删除 API 工具提供者"""
        _ensure_tool_api_providers_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'DELETE FROM tool_api_providers WHERE id = %s', (provider_id,))
            db.commit()
            return jsonify(code=200, msg='删除成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='删除失败: ' + str(e))
        finally:
            db.close()

    @app.route('/api/tools/providers/api/<provider_id>/test', methods=['POST'])
    def test_api_provider(provider_id):
        """测试 API 工具提供者连通性"""
        _ensure_tool_api_providers_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM tool_api_providers WHERE id = %s', (provider_id,))
            provider = cur.fetchone()
        finally:
            db.close()

        if not provider:
            return jsonify(code=404, msg='提供者不存在')

        # 测试连通性
        import socket
        from urllib.parse import urlparse
        parsed = urlparse(provider['server_url'])
        host = parsed.hostname or 'localhost'
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            is_reachable = (result == 0)
        except Exception:
            is_reachable = False

        # 更新测试状态
        db = get_db()
        try:
            cur = db.cursor()
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if is_reachable:
                cur.execute(r'''UPDATE tool_api_providers
                               SET last_tested_at = %s, last_error = '', status = 'active'
                               WHERE id = %s''', (now_str, provider_id))
            else:
                cur.execute(r'''UPDATE tool_api_providers
                               SET last_tested_at = %s, last_error = '连接失败', status = 'error'
                               WHERE id = %s''', (now_str, provider_id))
            db.commit()
        finally:
            db.close()

        if is_reachable:
            return jsonify(code=200, msg='连接成功', data={'reachable': True})
        return jsonify(code=200, msg='连接失败', data={'reachable': False})

    @app.route('/api/tools/providers/workflow', methods=['GET'])
    def list_workflow_providers():
        """列出工作流工具提供者"""
        _ensure_tool_workflow_providers_table()
        tenant_id = request.args.get('tenant_id', 'system')
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''SELECT id, name, description, icon, icon_background, app_id,
                                  workflow_tool_id, call_count, avg_latency_ms, status, last_called_at
                           FROM tool_workflow_providers WHERE tenant_id = %s
                           ORDER BY created_at DESC''', (tenant_id,))
            items = []
            for r in cur.fetchall():
                items.append({
                    'id': r['id'], 'name': r['name'], 'description': r['description'],
                    'icon': r['icon'], 'icon_background': r['icon_background'],
                    'app_id': r['app_id'], 'workflow_tool_id': r['workflow_tool_id'],
                    'call_count': r['call_count'], 'avg_latency_ms': r['avg_latency_ms'],
                    'status': r['status'], 'last_called_at': str(r['last_called_at'] or ''),
                })
            return jsonify(code=200, data=items)
        finally:
            db.close()

    @app.route('/api/tools/providers/mcp', methods=['GET'])
    def list_mcp_providers():
        """列出 MCP 工具提供者"""
        _ensure_tool_mcp_providers_table()
        tenant_id = request.args.get('tenant_id', 'system')
        server_id = request.args.get('server_id', '')

        db = get_db()
        try:
            cur = db.cursor()
            if server_id:
                cur.execute(r'''SELECT id, server_id, server_name, tool_name, tool_label,
                                      description, input_schema, is_enabled, call_count, status
                               FROM tool_mcp_providers
                               WHERE tenant_id = %s AND server_id = %s
                               ORDER BY tool_name''', (tenant_id, server_id))
            else:
                cur.execute(r'''SELECT id, server_id, server_name, tool_name, tool_label,
                                      description, input_schema, is_enabled, call_count, status
                               FROM tool_mcp_providers
                               WHERE tenant_id = %s
                               ORDER BY server_name, tool_name''', (tenant_id,))
            items = []
            for r in cur.fetchall():
                items.append({
                    'id': r['id'], 'server_id': r['server_id'],
                    'server_name': r['server_name'], 'tool_name': r['tool_name'],
                    'tool_label': r['tool_label'], 'description': r['description'],
                    'input_schema': json.loads(r['input_schema'] or '{}'),
                    'is_enabled': bool(r['is_enabled']), 'call_count': r['call_count'],
                    'status': r['status'],
                })
            return jsonify(code=200, data=items)
        finally:
            db.close()

    @app.route('/api/tools/providers/mcp/<provider_id>/enable', methods=['PUT'])
    def enable_mcp_provider(provider_id):
        """启用/禁用 MCP 工具提供者"""
        _ensure_tool_mcp_providers_table()
        body = request.get_json() or {}
        is_enabled = body.get('is_enabled', True)

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''UPDATE tool_mcp_providers
                           SET is_enabled = %s, status = %s
                           WHERE id = %s''',
                        (1 if is_enabled else 0,
                         'active' if is_enabled else 'inactive',
                         provider_id))
            db.commit()
            return jsonify(code=200, msg='更新成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='更新失败: ' + str(e))
        finally:
            db.close()

    @app.route('/api/tools/providers/sync/mcp', methods=['POST'])
    def sync_mcp_tools():
        """同步 MCP 服务器工具列表到 tool_mcp_providers 表"""
        _ensure_tool_mcp_providers_table()
        body = request.get_json() or {}
        server_id = body.get('server_id', '')
        tools = body.get('tools', [])

        if not server_id:
            return jsonify(code=400, msg='server_id 必填')

        db = get_db()
        try:
            cur = db.cursor()
            # 获取服务器信息
            cur.execute(r'SELECT id, name FROM mcp_servers WHERE id = %s', (server_id,))
            srv = cur.fetchone()
            if not srv:
                return jsonify(code=404, msg='MCP 服务器不存在')

            # 删除旧的占位记录
            cur.execute(r"DELETE FROM tool_mcp_providers WHERE server_id = %s AND tool_name = '_placeholder_'", (server_id,))

            # 插入新工具
            for tool in tools:
                tool_name = tool.get('name', '')
                if not tool_name:
                    continue
                cur.execute(r'''INSERT INTO tool_mcp_providers
                               (id, tenant_id, server_id, server_name, tool_name, tool_label,
                                description, input_schema, output_schema, annotations_json, status)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active')
                               ON DUPLICATE KEY UPDATE
                                tool_label = VALUES(tool_label),
                                description = VALUES(description),
                                input_schema = VALUES(input_schema),
                                output_schema = VALUES(output_schema),
                                annotations_json = VALUES(annotations_json),
                                status = 'active'
                            ''',
                            (str(uuid.uuid4()), 'system', server_id, srv['name'],
                             tool_name, tool.get('label', tool_name),
                             tool.get('description', ''),
                             json.dumps(tool.get('inputSchema', {}), ensure_ascii=False),
                             json.dumps(tool.get('outputSchema', {}), ensure_ascii=False) if tool.get('outputSchema') else None,
                             json.dumps(tool.get('annotations', {}), ensure_ascii=False) if tool.get('annotations') else None))
            db.commit()
            return jsonify(code=200, msg=f'同步成功，共 {len(tools)} 个工具')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='同步失败: ' + str(e))
        finally:
            db.close()

    # ============================================================
    # 工具标签 API（3.5）
    # ============================================================

    @app.route('/api/tools/labels', methods=['GET'])
    def list_tool_labels():
        """列出所有标签（含使用次数）"""
        try:
            from engine.tool_label_engine import list_all_labels
            labels = list_all_labels()
            return jsonify(code=200, data=labels)
        except Exception as e:
            return jsonify(code=500, msg='获取标签失败: ' + str(e))

    @app.route('/api/tools/labels/bind', methods=['POST'])
    def bind_tool_label():
        """为工具添加标签"""
        from engine.tool_label_engine import add_label
        body = request.json or {}
        tool_type = (body.get('tool_type') or '').strip()
        tool_id = (body.get('tool_id') or '').strip()
        label = (body.get('label') or '').strip()
        if not tool_type or not tool_id or not label:
            return jsonify(code=400, msg='tool_type, tool_id, label 均为必填')
        result = add_label(tool_type, tool_id, label)
        if not result:
            return jsonify(code=500, msg='添加标签失败')
        return jsonify(code=200, data=result)

    @app.route('/api/tools/labels/unbind', methods=['POST'])
    def unbind_tool_label():
        """移除工具标签"""
        from engine.tool_label_engine import remove_label
        body = request.json or {}
        tool_type = (body.get('tool_type') or '').strip()
        tool_id = (body.get('tool_id') or '').strip()
        label = (body.get('label') or '').strip()
        if not tool_type or not tool_id or not label:
            return jsonify(code=400, msg='tool_type, tool_id, label 均为必填')
        ok = remove_label(tool_type, tool_id, label)
        if not ok:
            return jsonify(code=404, msg='标签不存在')
        return jsonify(code=200, msg='移除成功')

    @app.route('/api/tools/labels/batch', methods=['POST'])
    def batch_set_tool_labels():
        """批量设置工具标签（覆盖式）"""
        from engine.tool_label_engine import batch_set_labels
        body = request.json or {}
        tool_type = (body.get('tool_type') or '').strip()
        tool_id = (body.get('tool_id') or '').strip()
        labels = body.get('labels') or []
        if not tool_type or not tool_id:
            return jsonify(code=400, msg='tool_type 和 tool_id 必填')
        if not isinstance(labels, list):
            return jsonify(code=400, msg='labels 必须是数组')
        n = batch_set_labels(tool_type, tool_id, labels)
        return jsonify(code=200, data={'updated': n})

    @app.route('/api/tools/<tool_type>/<tool_id>/labels', methods=['GET'])
    def get_tool_labels_api(tool_type, tool_id):
        """获取工具的标签列表"""
        from engine.tool_label_engine import get_tool_labels
        labels = get_tool_labels(tool_type, tool_id)
        return jsonify(code=200, data=labels)

    @app.route('/api/tools/filter', methods=['GET'])
    def filter_tools_api():
        """
        综合筛选工具。

        查询参数:
            tool_type: builtin/api/workflow
            label: 标签名
            keyword: 关键字
        """
        try:
            from engine.tool_label_engine import filter_tools
            tool_type = request.args.get('tool_type', '').strip() or None
            label = request.args.get('label', '').strip() or None
            keyword = request.args.get('keyword', '').strip() or None
            results = filter_tools(tool_type=tool_type, label=label, keyword=keyword)
            return jsonify(code=200, data=results)
        except Exception as e:
            return jsonify(code=500, msg='筛选失败: ' + str(e))

    @app.route('/api/tools/<tool_type>/<tool_id>/version', methods=['PUT'])
    def set_tool_version_api(tool_type, tool_id):
        """设置工具版本号"""
        from engine.tool_label_engine import set_tool_version
        body = request.json or {}
        version = (body.get('version') or '').strip()
        if not version:
            return jsonify(code=400, msg='version 不能为空')
        ok = set_tool_version(tool_type, tool_id, version)
        if not ok:
            return jsonify(code=404, msg='工具不存在或不支持的类型')
        return jsonify(code=200, msg='版本已更新')

    # ============================================================
    # 工具 OAuth API（3.4）
    # ============================================================

    @app.route('/api/tools/oauth/system-clients', methods=['POST'])
    def create_system_oauth_client():
        """创建系统级 OAuth 客户端"""
        from engine.tool_oauth import create_system_client
        body = request.json or {}
        provider_name = (body.get('provider_name') or '').strip()
        client_id = (body.get('client_id') or '').strip()
        client_secret = (body.get('client_secret') or '').strip()
        auth_url = (body.get('auth_url') or '').strip()
        token_url = (body.get('token_url') or '').strip()
        if not provider_name or not client_id or not client_secret:
            return jsonify(code=400, msg='provider_name, client_id, client_secret 必填')
        if not auth_url or not token_url:
            return jsonify(code=400, msg='auth_url 和 token_url 必填')
        client_id_db = create_system_client(
            provider_name, client_id, client_secret, auth_url, token_url,
            redirect_uri=(body.get('redirect_uri') or '').strip(),
            scopes=(body.get('scopes') or '').strip(),
            extra_params=body.get('extra_params'),
        )
        if not client_id_db:
            return jsonify(code=500, msg='创建失败')
        return jsonify(code=200, data={'id': client_id_db})

    @app.route('/api/tools/oauth/tenant-clients', methods=['POST'])
    def create_tenant_oauth_client():
        """创建租户级 OAuth 客户端"""
        from engine.tool_oauth import create_tenant_client
        body = request.json or {}
        tenant_id = (body.get('tenant_id') or 'default').strip()
        provider_name = (body.get('provider_name') or '').strip()
        client_id = (body.get('client_id') or '').strip()
        client_secret = (body.get('client_secret') or '').strip()
        auth_url = (body.get('auth_url') or '').strip()
        token_url = (body.get('token_url') or '').strip()
        if not provider_name or not client_id or not client_secret:
            return jsonify(code=400, msg='provider_name, client_id, client_secret 必填')
        if not auth_url or not token_url:
            return jsonify(code=400, msg='auth_url 和 token_url 必填')
        client_id_db = create_tenant_client(
            tenant_id, provider_name, client_id, client_secret, auth_url, token_url,
            redirect_uri=(body.get('redirect_uri') or '').strip(),
            scopes=(body.get('scopes') or '').strip(),
            extra_params=body.get('extra_params'),
        )
        if not client_id_db:
            return jsonify(code=500, msg='创建失败')
        return jsonify(code=200, data={'id': client_id_db})

    @app.route('/api/tools/oauth/authorize', methods=['POST'])
    def oauth_authorize():
        """
        获取 OAuth 授权 URL。

        请求体: {provider_name, tenant_id}
        响应: {code: 200, data: {auth_url, state}}
        """
        from engine.tool_oauth import generate_auth_url
        body = request.json or {}
        provider_name = (body.get('provider_name') or '').strip()
        tenant_id = (body.get('tenant_id') or '').strip() or None
        if not provider_name:
            return jsonify(code=400, msg='provider_name 必填')
        auth_url, state_or_err = generate_auth_url(tenant_id, provider_name)
        if not auth_url:
            return jsonify(code=400, msg=state_or_err)
        return jsonify(code=200, data={'auth_url': auth_url, 'state': state_or_err})

    @app.route('/api/tools/oauth/callback', methods=['GET'])
    def oauth_callback():
        """
        OAuth 回调端点。

        查询参数: code, state, error
        """
        from engine.tool_oauth import handle_oauth_callback
        code = request.args.get('code', '').strip() or None
        state = request.args.get('state', '').strip() or None
        error = request.args.get('error', '').strip() or None

        if not state:
            return jsonify(code=400, msg='缺少 state 参数')

        success, message = handle_oauth_callback(state, code, error)
        if success:
            # 返回简单的 HTML 页面
            return f'''
            <!DOCTYPE html><html><head><meta charset="utf-8"><title>授权成功</title></head>
            <body style="font-family:sans-serif;text-align:center;padding:50px;">
                <h1 style="color:#4CAF50;">✅ 授权成功</h1>
                <p>{message}</p>
                <p>您可以关闭此页面。</p>
            </body></html>
            '''
        else:
            return f'''
            <!DOCTYPE html><html><head><meta charset="utf-8"><title>授权失败</title></head>
            <body style="font-family:sans-serif;text-align:center;padding:50px;">
                <h1 style="color:#F44336;">❌ 授权失败</h1>
                <p>{message}</p>
                <p>请重试或联系管理员。</p>
            </body></html>
            ''', 400

    @app.route('/api/tools/oauth/token-status', methods=['GET'])
    def oauth_token_status():
        """获取 token 状态"""
        from engine.tool_oauth import get_token_status
        provider_name = request.args.get('provider_name', '').strip()
        tenant_id = request.args.get('tenant_id', 'default').strip()
        if not provider_name:
            return jsonify(code=400, msg='provider_name 必填')
        status = get_token_status(tenant_id, provider_name)
        if not status:
            return jsonify(code=200, data={'authorized': False})
        return jsonify(code=200, data={'authorized': True, **status})

    @app.route('/api/tools/oauth/revoke', methods=['POST'])
    def oauth_revoke():
        """撤销 OAuth 授权"""
        from engine.tool_oauth import revoke_token
        body = request.json or {}
        provider_name = (body.get('provider_name') or '').strip()
        tenant_id = (body.get('tenant_id') or 'default').strip()
        if not provider_name:
            return jsonify(code=400, msg='provider_name 必填')
        ok = revoke_token(tenant_id, provider_name)
        if not ok:
            return jsonify(code=404, msg='未找到授权记录')
        return jsonify(code=200, msg='已撤销')


def _extract_workflow_inputs(graph, mode='workflow'):
    """从工作流图的 Start 节点提取输入参数 Schema"""
    input_schema = {'type': 'object', 'properties': {}, 'required': []}
    nodes = graph.get('nodes', [])

    for node in nodes:
        data = node.get('data', {})
        node_type = data.get('type', '')
        if node_type == 'start':
            variables = data.get('variables', [])
            for v in variables:
                var_name = v.get('variable', '')
                if var_name:
                    input_schema['properties'][var_name] = {
                        'type': v.get('type', 'string'),
                        'description': v.get('label', var_name),
                    }
                    if v.get('required'):
                        input_schema['required'].append(var_name)
            break

    return input_schema
