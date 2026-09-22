# -*- coding: utf-8 -*-
"""
MCP 服务端 —— 将熵舟工具暴露为 MCP Server（3.7）

协议: MCP (Model Context Protocol) over SSE
端点:
    GET  /mcp/v1              — SSE 连接（服务器 → 客户端事件流）
    POST /mcp/v1/messages     — 客户端 → 服务器消息（JSON-RPC 2.0）

支持的方法:
    initialize       — 握手，返回服务器能力
    tools/list       — 列出所有可用工具
    tools/call       — 调用工具
    ping             — 心跳
    resources/list   — 列出资源（空实现）
    prompts/list     — 列出提示模板（空实现）

SSE 事件流:
    连接建立后发送 endpoint 事件，告知客户端 POST 地址
    之后通过 event: message 发送 JSON-RPC 响应
"""
import json
import uuid
import time
import queue
import threading
from typing import Dict, Optional, List

from flask import Response, request, jsonify, stream_with_context

from config import get_db

# 协议版本
PROTOCOL_VERSION = '2024-11-05'
SERVER_NAME = 'shangzhou-mcp-server'
SERVER_VERSION = '1.0.0'

# SSE 会话管理 {session_id: {'queue': Queue, 'created_at': float, 'closed': bool}}
_mcp_sessions: Dict[str, dict] = {}
_mcp_lock = threading.Lock()

SESSION_TIMEOUT = 3600  # 1 小时


def _cleanup_sessions():
    """清理过期会话"""
    now = time.time()
    with _mcp_lock:
        expired = [sid for sid, s in _mcp_sessions.items()
                   if now - s['created_at'] > SESSION_TIMEOUT or s.get('closed')]
        for sid in expired:
            _mcp_sessions.pop(sid, None)


def _get_or_create_session(session_id: str = None) -> str:
    """获取或创建 SSE 会话"""
    _cleanup_sessions()
    with _mcp_lock:
        if session_id and session_id in _mcp_sessions:
            return session_id
        sid = session_id or str(uuid.uuid4())
        _mcp_sessions[sid] = {
            'queue': queue.Queue(),
            'created_at': time.time(),
            'closed': False,
        }
        return sid


def _send_to_session(session_id: str, data: dict):
    """向会话发送消息"""
    with _mcp_lock:
        session = _mcp_sessions.get(session_id)
    if session and not session.get('closed'):
        session['queue'].put(data)


def _close_session(session_id: str):
    """关闭会话"""
    with _mcp_lock:
        if session_id in _mcp_sessions:
            _mcp_sessions[session_id]['closed'] = True


# ============================================================
# 工具发现与转换
# ============================================================

def _get_all_tools() -> List[Dict]:
    """获取所有可用工具（MCP 格式）"""
    tools = []

    # 内置工具
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            SELECT id, provider_name, provider_label, description, actions_json, icon
            FROM tool_builtin_providers WHERE status = 'active'
        """)
        for row in cur.fetchall():
            try:
                actions = json.loads(row['actions_json'] or '[]')
            except Exception:
                actions = []
            for action in actions:
                tool_name = f"{row['provider_name']}__{action.get('name', '')}"
                tools.append({
                    'name': tool_name,
                    'title': action.get('label', action.get('name', '')),
                    'description': f"[{row['provider_label']}] {action.get('description', row['description'] or '')}",
                    'inputSchema': _convert_params_to_schema(action.get('params', [])),
                    'annotations': {
                        'icon': row.get('icon', '🔧'),
                        'provider': row['provider_name'],
                        'action': action.get('name', ''),
                        'source': 'builtin',
                    },
                })
    finally:
        db.close()

    # API 工具
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            SELECT id, name, description, actions_json
            FROM tool_api_providers WHERE status = 'active'
        """)
        for row in cur.fetchall():
            try:
                actions = json.loads(row['actions_json'] or '[]')
            except Exception:
                actions = []
            for action in actions:
                tool_name = f"api__{row['name']}__{action.get('name', '')}"
                tools.append({
                    'name': tool_name,
                    'title': f"[{row['name']}] {action.get('label', action.get('name', ''))}",
                    'description': action.get('description', row['description'] or ''),
                    'inputSchema': _convert_params_to_schema(action.get('params', [])),
                    'annotations': {
                        'provider': row['name'],
                        'action': action.get('name', ''),
                        'source': 'api',
                    },
                })
    finally:
        db.close()

    # 工作流工具
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            SELECT id, name, description, input_schema
            FROM tool_workflow_providers WHERE status = 'active'
        """)
        for row in cur.fetchall():
            tool_name = f"workflow__{row['name']}"
            try:
                schema = json.loads(row['input_schema']) if row['input_schema'] else {
                    'type': 'object', 'properties': {}
                }
            except Exception:
                schema = {'type': 'object', 'properties': {}}
            tools.append({
                'name': tool_name,
                'title': f"[工作流] {row['name']}",
                'description': row['description'] or '',
                'inputSchema': schema,
                'annotations': {
                    'provider': row['name'],
                    'source': 'workflow',
                },
            })
    finally:
        db.close()

    return tools


def _convert_params_to_schema(params: List[Dict]) -> Dict:
    """将工具参数列表转换为 JSON Schema"""
    properties = {}
    required = []

    if not params:
        return {'type': 'object', 'properties': {}}

    for p in params:
        name = p.get('name', '')
        if not name:
            continue
        prop = {
            'type': _map_type(p.get('type', 'string')),
            'description': p.get('label', p.get('description', '')),
        }
        if p.get('default') is not None:
            prop['default'] = p['default']
        if p.get('enum'):
            prop['enum'] = p['enum']
        properties[name] = prop
        if p.get('required'):
            required.append(name)

    schema = {'type': 'object', 'properties': properties}
    if required:
        schema['required'] = required
    return schema


def _map_type(t: str) -> str:
    """映射工具参数类型到 JSON Schema 类型"""
    mapping = {
        'str': 'string', 'string': 'string', 'text': 'string',
        'int': 'integer', 'integer': 'integer', 'number': 'number',
        'float': 'number', 'bool': 'boolean', 'boolean': 'boolean',
        'array': 'array', 'list': 'array', 'object': 'object', 'dict': 'object',
        'select': 'string', 'enum': 'string',
    }
    return mapping.get(t.lower(), 'string')


def _execute_mcp_tool(tool_name: str, arguments: Dict) -> Dict:
    """
    执行 MCP 工具调用。

    工具名格式: {source}__{provider}__{action} 或 {source}__{name}
    """
    parts = tool_name.split('__', 2)
    if len(parts) < 2:
        return {'content': [{'type': 'text', 'text': f'无效的工具名: {tool_name}'}], 'isError': True}

    source = parts[0]

    try:
        from engine.tool_runtime import invoke_tool

        if source == 'builtin':
            if len(parts) < 3:
                return {'content': [{'type': 'text', 'text': '工具名格式错误'}], 'isError': True}
            provider, action = parts[1], parts[2]
            result = invoke_tool(provider, action, arguments)
        elif source == 'api':
            if len(parts) < 3:
                return {'content': [{'type': 'text', 'text': '工具名格式错误'}], 'isError': True}
            provider, action = parts[1], parts[2]
            result = invoke_tool(provider, action, arguments)
        elif source == 'workflow':
            provider = parts[1] if len(parts) == 2 else parts[1]
            result = invoke_tool(provider, 'execute', arguments)
        else:
            return {'content': [{'type': 'text', 'text': f'未知的工具来源: {source}'}], 'isError': True}

        if isinstance(result, str):
            text = result
        else:
            text = json.dumps(result, ensure_ascii=False, default=str)

        return {
            'content': [{'type': 'text', 'text': text}],
            'isError': False,
        }
    except Exception as e:
        return {
            'content': [{'type': 'text', 'text': f'工具执行错误: {str(e)[:500]}'}],
            'isError': True,
        }


# ============================================================
# JSON-RPC 处理
# ============================================================

def _handle_jsonrpc(message: dict, session_id: str) -> Optional[dict]:
    """
    处理 JSON-RPC 消息。

    返回:
        响应 dict 或 None（通知无需响应）
    """
    method = message.get('method', '')
    msg_id = message.get('id')
    params = message.get('params', {})

    # 通知（无 id）不需要响应
    is_notification = msg_id is None

    if method == 'initialize':
        result = {
            'protocolVersion': PROTOCOL_VERSION,
            'capabilities': {
                'tools': {'listChanged': False},
                'resources': {'subscribe': False, 'listChanged': False},
                'prompts': {'listChanged': False},
            },
            'serverInfo': {
                'name': SERVER_NAME,
                'version': SERVER_VERSION,
            },
        }
        return _jsonrpc_result(msg_id, result)

    elif method == 'notifications/initialized':
        # 客户端初始化完成通知，无需响应
        return None

    elif method == 'ping':
        return _jsonrpc_result(msg_id, {})

    elif method == 'tools/list':
        tools = _get_all_tools()
        return _jsonrpc_result(msg_id, {'tools': tools})

    elif method == 'tools/call':
        tool_name = params.get('name', '')
        arguments = params.get('arguments', {})
        result = _execute_mcp_tool(tool_name, arguments)
        return _jsonrpc_result(msg_id, result)

    elif method == 'resources/list':
        return _jsonrpc_result(msg_id, {'resources': []})

    elif method == 'resources/templates/list':
        return _jsonrpc_result(msg_id, {'resourceTemplates': []})

    elif method == 'prompts/list':
        return _jsonrpc_result(msg_id, {'prompts': []})

    else:
        if is_notification:
            return None
        return _jsonrpc_error(msg_id, -32601, f'Method not found: {method}')


def _jsonrpc_result(msg_id, result) -> dict:
    """构建 JSON-RPC 成功响应"""
    return {
        'jsonrpc': '2.0',
        'id': msg_id,
        'result': result,
    }


def _jsonrpc_error(msg_id, code: int, message: str) -> dict:
    """构建 JSON-RPC 错误响应"""
    return {
        'jsonrpc': '2.0',
        'id': msg_id,
        'error': {
            'code': code,
            'message': message,
        },
    }


# ============================================================
# Flask 路由
# ============================================================

def register_mcp_server_routes(app):
    """注册 MCP 服务端路由"""

    @app.route('/mcp/v1', methods=['GET'])
    def mcp_sse_endpoint():
        """
        MCP SSE 端点 —— 建立服务器到客户端的事件流。

        连接后发送 endpoint 事件，告知客户端 POST 地址。
        """
        session_id = _get_or_create_session()

        def event_stream():
            # 发送 endpoint 事件
            endpoint_url = f'/mcp/v1/messages?session_id={session_id}'
            yield f'event: endpoint\ndata: {endpoint_url}\n\n'

            # 持续发送队列中的消息
            q = _mcp_sessions[session_id]['queue']
            try:
                while True:
                    try:
                        msg = q.get(timeout=30)
                        data = json.dumps(msg, ensure_ascii=False)
                        yield f'event: message\ndata: {data}\n\n'
                    except queue.Empty:
                        # 发送心跳注释防止连接断开
                        yield ': heartbeat\n\n'
            except GeneratorExit:
                _close_session(session_id)

        response = Response(
            stream_with_context(event_stream()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive',
            }
        )
        return response

    @app.route('/mcp/v1/messages', methods=['POST'])
    def mcp_messages_endpoint():
        """
        MCP 消息端点 —— 接收客户端 JSON-RPC 消息。

        查询参数: session_id
        """
        session_id = request.args.get('session_id', '').strip()
        if not session_id:
            return jsonify({'error': '缺少 session_id'}), 400

        with _mcp_lock:
            if session_id not in _mcp_sessions:
                # 自动创建会话（支持无 SSE 的简化客户端）
                _mcp_sessions[session_id] = {
                    'queue': queue.Queue(),
                    'created_at': time.time(),
                    'closed': False,
                }

        try:
            message = request.get_json(force=True)
        except Exception:
            return jsonify({'error': '无效的 JSON'}), 400

        if not isinstance(message, dict):
            return jsonify({'error': '消息必须是 JSON 对象'}), 400

        # 处理消息
        response = _handle_jsonrpc(message, session_id)

        # 通知无需响应
        if response is None:
            return jsonify({'status': 'ok'})

        # 通过 SSE 发送响应
        _send_to_session(session_id, response)

        return jsonify({'status': 'accepted'})

    @app.route('/mcp/v1/health', methods=['GET'])
    def mcp_health():
        """MCP 服务器健康检查"""
        _cleanup_sessions()
        with _mcp_lock:
            session_count = len(_mcp_sessions)
        return jsonify({
            'status': 'ok',
            'protocol_version': PROTOCOL_VERSION,
            'server': f'{SERVER_NAME} v{SERVER_VERSION}',
            'active_sessions': session_count,
        })

    @app.route('/api/mcp-server/tools', methods=['GET'])
    def mcp_server_tools_list():
        """获取 MCP 服务端暴露的工具列表（REST 方式）"""
        tools = _get_all_tools()
        return jsonify(code=200, data={
            'tools': tools,
            'count': len(tools),
        })
