# -*- coding: utf-8 -*-
"""MCP 服务器管理路由"""

import json
import uuid
import urllib.request
import urllib.error
from flask import jsonify, request
from config import get_db
from models.tables import MCP_TABLE_SQL, APP_MCP_SERVERS_TABLE_SQL


def _ensure_mcp_table():
    db = get_db()
    try:
        db.cursor().execute(MCP_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def _mcp_conn():
    _ensure_mcp_table()
    return get_db()


def _parse_kv(rows):
    """键值数组 → 仅保留有效行的 JSON 字符串"""
    if not isinstance(rows, list):
        return '[]'
    out = []
    for it in rows:
        if not isinstance(it, dict):
            continue
        k = (it.get('k') or '').strip()
        v = (it.get('v') or '').strip()
        if k:
            out.append({'k': k, 'v': v})
    return json.dumps(out, ensure_ascii=False)


def _mcp_to_dict(r):
    """记录行 → 前端友好结构"""
    def parse_j(s):
        if not s:
            return []
        try:
            v = json.loads(s)
            return v if isinstance(v, list) else []
        except Exception:
            return []
    return {'id': r['id'], 'name': r['name'], 'type': r['mtype'], 'url': r['url'] or '',
            'command': r['command'] or '', 'headers': parse_j(r['headers']), 'env': parse_j(r['env']),
            'remark': r['remark'] or '', 'enabled': bool(r['enabled']),
            'created_at': str(r['created_at']), 'updated_at': str(r['updated_at'])}


def _mcp_payload(body):
    """校验并整理添加/编辑表单"""
    name = (body.get('name') or '').strip()
    if not name:
        return None, '请填写名称'
    mtype = body.get('type') or 'http'
    if mtype not in ('http', 'sse', 'stdio'):
        mtype = 'http'
    url = (body.get('url') or '').strip()
    command = (body.get('command') or '').strip()
    if mtype != 'stdio' and not url:
        return None, '请填写服务端点 URL'
    if mtype == 'stdio' and not command:
        return None, '请填写启动命令（如 npx -y xxx）'
    return (name, mtype, url, command,
            _parse_kv(body.get('headers')), _parse_kv(body.get('env')),
            (body.get('remark') or '').strip()), None


def register_mcp_routes(app):
    """注册 MCP 服务器相关路由"""
    _register_app_mcp_routes(app)

    @app.route('/api/mcps', methods=['GET'])
    def list_mcps():
        """MCP 服务器列表"""
        db = _mcp_conn()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM mcp_servers ORDER BY id DESC')
            return jsonify(code=200, data=[_mcp_to_dict(r) for r in cur.fetchall()])
        finally:
            db.close()

    @app.route('/api/mcps', methods=['POST'])
    def create_mcp():
        """添加 MCP 服务器"""
        body = request.get_json(silent=True) or {}
        payload, err = _mcp_payload(body)
        if err:
            return jsonify(code=400, msg=err)
        db = _mcp_conn()
        try:
            cur = db.cursor()
            cur.execute(r'INSERT INTO mcp_servers (name, mtype, url, command, headers, env, remark) VALUES (%s, %s, %s, %s, %s, %s, %s)', payload)
            db.commit()
            return jsonify(code=200, msg='已添加', data={'id': cur.lastrowid})
        finally:
            db.close()

    @app.route('/api/mcps/<int:mid>', methods=['PUT'])
    def update_mcp(mid):
        """编辑 MCP 服务器"""
        body = request.get_json(silent=True) or {}
        payload, err = _mcp_payload(body)
        if err:
            return jsonify(code=400, msg=err)
        db = _mcp_conn()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT id FROM mcp_servers WHERE id = %s', (mid,))
            if not cur.fetchone():
                return jsonify(code=404, msg='服务器不存在')
            cur.execute(r'UPDATE mcp_servers SET name=%s, mtype=%s, url=%s, command=%s, headers=%s, env=%s, remark=%s WHERE id=%s',
                        payload + (mid,))
            db.commit()
            return jsonify(code=200, msg='已保存')
        finally:
            db.close()

    @app.route('/api/mcps/<int:mid>', methods=['DELETE'])
    def delete_mcp(mid):
        """删除 MCP 服务器"""
        db = _mcp_conn()
        try:
            cur = db.cursor()
            cur.execute(r'DELETE FROM mcp_servers WHERE id = %s', (mid,))
            db.commit()
            return jsonify(code=200, msg='已删除')
        finally:
            db.close()

    @app.route('/api/mcps/<int:mid>/toggle', methods=['POST'])
    def toggle_mcp(mid):
        """启用 / 停用 MCP 服务器"""
        db = _mcp_conn()
        try:
            cur = db.cursor()
            cur.execute(r'UPDATE mcp_servers SET enabled = 1 - enabled WHERE id = %s', (mid,))
            db.commit()
            if not cur.rowcount:
                return jsonify(code=404, msg='服务器不存在')
            cur.execute(r'SELECT enabled FROM mcp_servers WHERE id = %s', (mid,))
            return jsonify(code=200, msg='已启用' if cur.fetchone()['enabled'] else '已停用')
        finally:
            db.close()

    @app.route('/api/mcps/<int:mid>/tools', methods=['GET'])
    def get_mcp_tools(mid):
        """获取 MCP 服务器的工具列表"""
        db = _mcp_conn()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM mcp_servers WHERE id = %s AND enabled = 1', (mid,))
            server = cur.fetchone()
        finally:
            db.close()

        if not server:
            return jsonify(code=404, msg='服务器不存在或已停用')

        mtype = server['mtype']
        url = server['url'] or ''
        command = server['command'] or ''
        headers = json.loads(server['headers'] or '[]') if isinstance(server['headers'], str) else (server['headers'] or [])
        env = json.loads(server['env'] or '[]') if isinstance(server['env'], str) else (server['env'] or [])

        try:
            if mtype in ('http', 'sse'):
                tools = _list_mcp_tools_http(url, headers)
            elif mtype == 'stdio':
                tools = _list_mcp_tools_stdio(command, env)
            else:
                return jsonify(code=400, msg=f'不支持的 MCP 服务器类型: {mtype}')
            return jsonify(code=200, data=tools)
        except Exception as e:
            return jsonify(code=500, msg=f'获取工具列表失败: {str(e)}')

    @app.route('/api/mcps/parse', methods=['POST'])
    def parse_mcp_config():
        """智能识别：粘贴 mcpServers JSON 自动解析为表单配置"""
        body = request.get_json(silent=True) or {}
        text = (body.get('text') or '').strip()
        if not text:
            return jsonify(code=400, msg='请粘贴 MCP 配置内容')
        try:
            obj = json.loads(text)
        except Exception:
            return jsonify(code=400, msg='不是合法的 JSON，请粘贴 mcpServers 结构')
        servers = obj.get('mcpServers') if isinstance(obj, dict) and 'mcpServers' in obj else obj
        if not isinstance(servers, dict):
            return jsonify(code=400, msg='未找到 mcpServers 对象')
        out = []
        for name, cfg in servers.items():
            if not isinstance(cfg, dict):
                continue
            mtype = 'stdio'
            if cfg.get('type') in ('http', 'sse'):
                mtype = cfg['type']
            elif cfg.get('url'):
                mtype = 'sse' if 'sse' in str(cfg.get('url')) else 'http'
            env = cfg.get('env') or {}
            env_rows = [{'k': str(k), 'v': str(v)} for k, v in env.items()] if isinstance(env, dict) else []
            out.append({'name': str(name), 'type': mtype, 'url': str(cfg.get('url') or '') if mtype != 'stdio' else '',
                        'command': ' '.join(cfg['command']) if isinstance(cfg.get('command'), list) else str(cfg.get('command') or ''),
                        'env': env_rows, 'headers': [], 'remark': ''})
        if not out:
            return jsonify(code=400, msg='未解析到任何 MCP 服务器')
        return jsonify(code=200, data=out)


def _list_mcp_tools_http(url, headers):
    """通过 HTTP 获取 MCP 工具列表"""
    payload = json.dumps({
        'jsonrpc': '2.0',
        'method': 'tools/list',
        'params': {},
        'id': 1
    }).encode('utf-8')

    req_headers = {'Content-Type': 'application/json'}
    for h in headers:
        if isinstance(h, dict) and h.get('k'):
            req_headers[h['k']] = h.get('v', '')

    req = urllib.request.Request(url, data=payload, headers=req_headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        raise Exception(f'HTTP 错误 {e.code}: {e.read().decode("utf-8", errors="replace")[:500]}')

    if 'error' in result:
        raise Exception(f'MCP 错误: {result["error"]}')

    tools = result.get('result', {}).get('tools', [])
    return [_normalize_mcp_tool(t) for t in tools]


def _list_mcp_tools_stdio(command, env):
    """通过 stdio 获取 MCP 工具列表"""
    import subprocess
    import os

    request_data = json.dumps({
        'jsonrpc': '2.0',
        'method': 'tools/list',
        'params': {},
        'id': 1
    })

    run_env = os.environ.copy()
    for e in env:
        if isinstance(e, dict) and e.get('k'):
            run_env[e['k']] = e.get('v', '')

    cmd = command.split()
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=run_env
    )

    try:
        stdout, stderr = proc.communicate(input=request_data.encode('utf-8'), timeout=30)
        if proc.returncode != 0:
            raise Exception(f'进程错误: {stderr.decode("utf-8", errors="replace")[:500]}')
        result = json.loads(stdout.decode('utf-8'))
        if 'error' in result:
            raise Exception(f'MCP 错误: {result["error"]}')
        tools = result.get('result', {}).get('tools', [])
        return [_normalize_mcp_tool(t) for t in tools]
    finally:
        if proc.poll() is None:
            proc.kill()


def _normalize_mcp_tool(tool):
    """标准化 MCP 工具定义"""
    params = tool.get('inputSchema', {}).get('properties', {})
    required = tool.get('inputSchema', {}).get('required', [])
    parameters = []
    for name, schema in params.items():
        parameters.append({
            'name': name,
            'label': name,
            'type': schema.get('type', 'string'),
            'required': name in required,
            'description': schema.get('description', ''),
        })
    return {
        'name': tool.get('name', ''),
        'label': tool.get('name', ''),
        'description': tool.get('description', ''),
        'parameters': parameters,
    }


def _ensure_app_mcp_servers_table():
    """确保应用-MCP 关联表存在"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(APP_MCP_SERVERS_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def _register_app_mcp_routes(app):
    """注册应用-MCP 关联路由（在 register_mcp_routes 中调用）"""

    @app.route('/api/apps/<app_id>/mcps', methods=['GET'])
    def list_app_mcp_servers(app_id):
        """列出应用关联的 MCP 服务器"""
        _ensure_app_mcp_servers_table()
        tenant_id = request.args.get('tenant_id', 'system')
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''SELECT * FROM app_mcp_servers
                           WHERE tenant_id = %s AND app_id = %s
                           ORDER BY priority DESC, created_at ASC''',
                        (tenant_id, app_id))
            items = []
            for r in cur.fetchall():
                items.append({
                    'id': r['id'], 'tenant_id': r['tenant_id'],
                    'app_id': r['app_id'], 'server_id': r['server_id'],
                    'server_name': r['server_name'],
                    'is_enabled': bool(r['is_enabled']),
                    'tool_whitelist': json.loads(r['tool_whitelist_json'] or '[]'),
                    'tool_blacklist': json.loads(r['tool_blacklist_json'] or '[]'),
                    'priority': r['priority'], 'status': r['status'],
                    'last_connected_at': str(r['last_connected_at'] or ''),
                    'last_error': r['last_error'] or '',
                    'created_at': str(r['created_at'] or ''),
                })
            return jsonify(code=200, data=items)
        finally:
            db.close()

    @app.route('/api/apps/<app_id>/mcps', methods=['POST'])
    def bind_mcp_to_app(app_id):
        """绑定 MCP 服务器到应用"""
        _ensure_app_mcp_servers_table()
        body = request.get_json()
        if not body:
            return jsonify(code=400, msg='请求体不能为空')

        server_id = body.get('server_id', '')
        if not server_id:
            return jsonify(code=400, msg='server_id 必填')

        # 获取服务器信息
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT id, name FROM mcp_servers WHERE id = %s', (server_id,))
            srv = cur.fetchone()
        finally:
            db.close()

        if not srv:
            return jsonify(code=404, msg='MCP 服务器不存在')

        bind_id = str(uuid.uuid4())
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''INSERT INTO app_mcp_servers
                           (id, tenant_id, app_id, server_id, server_name,
                            is_enabled, tool_whitelist_json, tool_blacklist_json,
                            priority, status)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE
                            server_name = VALUES(server_name),
                            is_enabled = VALUES(is_enabled),
                            tool_whitelist_json = VALUES(tool_whitelist_json),
                            tool_blacklist_json = VALUES(tool_blacklist_json),
                            priority = VALUES(priority),
                            status = 'active' ''',
                        (bind_id,
                         body.get('tenant_id', 'system'),
                         app_id,
                         server_id,
                         srv['name'],
                         1 if body.get('is_enabled', True) else 0,
                         json.dumps(body.get('tool_whitelist', []), ensure_ascii=False),
                         json.dumps(body.get('tool_blacklist', []), ensure_ascii=False),
                         body.get('priority', 0),
                         'active'))
            db.commit()
            return jsonify(code=200, msg='绑定成功', data={'id': bind_id})
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='绑定失败: ' + str(e))
        finally:
            db.close()

    @app.route('/api/apps/<app_id>/mcps/<bind_id>', methods=['PUT'])
    def update_app_mcp_binding(app_id, bind_id):
        """更新应用-MCP 绑定"""
        _ensure_app_mcp_servers_table()
        body = request.get_json()
        if not body:
            return jsonify(code=400, msg='请求体不能为空')

        db = get_db()
        try:
            cur = db.cursor()
            fields = []
            params = []
            if 'is_enabled' in body:
                fields.append('is_enabled = %s')
                params.append(1 if body['is_enabled'] else 0)
            if 'priority' in body:
                fields.append('priority = %s')
                params.append(body['priority'])
            if 'tool_whitelist' in body:
                fields.append('tool_whitelist_json = %s')
                params.append(json.dumps(body['tool_whitelist'], ensure_ascii=False))
            if 'tool_blacklist' in body:
                fields.append('tool_blacklist_json = %s')
                params.append(json.dumps(body['tool_blacklist'], ensure_ascii=False))
            if 'status' in body:
                fields.append('status = %s')
                params.append(body['status'])
            if 'custom_config' in body:
                fields.append('custom_config = %s')
                params.append(json.dumps(body['custom_config'], ensure_ascii=False))

            if not fields:
                return jsonify(code=400, msg='无更新字段')
            params.append(bind_id)
            cur.execute(f'''UPDATE app_mcp_servers SET {', '.join(fields)}
                           WHERE id = %s''', params)
            db.commit()
            return jsonify(code=200, msg='更新成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='更新失败: ' + str(e))
        finally:
            db.close()

    @app.route('/api/apps/<app_id>/mcps/<bind_id>', methods=['DELETE'])
    def unbind_mcp_from_app(app_id, bind_id):
        """解绑 MCP 服务器"""
        _ensure_app_mcp_servers_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'DELETE FROM app_mcp_servers WHERE id = %s AND app_id = %s',
                        (bind_id, app_id))
            db.commit()
            return jsonify(code=200, msg='解绑成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='解绑失败: ' + str(e))
        finally:
            db.close()

    @app.route('/api/apps/<app_id>/mcps/tools', methods=['GET'])
    def get_app_mcp_tools(app_id):
        """获取应用可用的所有 MCP 工具（合并所有绑定的服务器）"""
        _ensure_app_mcp_servers_table()
        tenant_id = request.args.get('tenant_id', 'system')
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''SELECT * FROM app_mcp_servers
                           WHERE tenant_id = %s AND app_id = %s AND is_enabled = 1
                           ORDER BY priority DESC''',
                        (tenant_id, app_id))
            bindings = cur.fetchall()
        finally:
            db.close()

        all_tools = []
        for bind in bindings:
            try:
                db = get_db()
                try:
                    cur = db.cursor()
                    cur.execute(r'SELECT * FROM mcp_servers WHERE id = %s', (bind['server_id'],))
                    srv = cur.fetchone()
                finally:
                    db.close()

                if not srv:
                    continue

                whitelist = json.loads(bind['tool_whitelist_json'] or '[]')
                blacklist = json.loads(bind['tool_blacklist_json'] or '[]')

                if srv['mtype'] in ('http', 'sse'):
                    tools = _list_mcp_tools_http(srv['url'] or '', json.loads(srv['headers'] or '[]'))
                elif srv['mtype'] == 'stdio':
                    tools = _list_mcp_tools_stdio(srv['command'] or '', json.loads(srv['env'] or '[]'))
                else:
                    continue

                for t in tools:
                    tool_name = t.get('name', '')
                    if whitelist and tool_name not in whitelist:
                        continue
                    if blacklist and tool_name in blacklist:
                        continue
                    t['server_id'] = bind['server_id']
                    t['server_name'] = bind['server_name']
                    all_tools.append(t)
            except Exception as e:
                # 单个服务器失败不影响其他服务器
                all_tools.append({
                    'server_id': bind['server_id'],
                    'server_name': bind['server_name'],
                    'error': str(e),
                })

        return jsonify(code=200, data=all_tools)
