# -*- coding: utf-8 -*-
"""
MCP 节点执行模块

负责调用 MCP（Model Context Protocol）服务器的工具，支持：
- HTTP/SSE 类型 MCP 服务器（JSON-RPC 2.0 over HTTP）
- stdio 类型 MCP 服务器（子进程通信）
- 变量引用解析与工具调用日志记录
- SSRF 防护安全检查
"""

import json


def _node_mcp(data, context, model_cfg=None):
    """
    MCP 节点 —— 调用 MCP 服务器的工具。

    节点数据结构:
    - mcp_server_id: MCP 服务器 ID
    - mcp_tool_name: 要调用的工具名称
    - mcp_parameters: 参数配置 {param_name: {value: ..., type: ...}}
    - output: 输出变量名（默认 'mcp_output'）

    返回: context + {output: 工具结果, mcp_output: 工具结果}
    """
    import time
    start_time = time.time()

    mcp_server_id = data.get('mcp_server_id', '')
    mcp_tool_name = data.get('mcp_tool_name', '')
    mcp_parameters = data.get('mcp_parameters', {})
    output_var = data.get('output', 'mcp_output')

    if not mcp_server_id or not mcp_tool_name:
        return {output_var: '', 'mcp_output': '', 'mcp_error': '未配置 MCP 工具'}

    # 解析变量引用
    from nodes.tool import _resolve_tool_parameters
    resolved_params = _resolve_tool_parameters(mcp_parameters, context)

    # 调用 MCP 工具
    try:
        result = _invoke_mcp_tool(mcp_server_id, mcp_tool_name, resolved_params)
        elapsed_ms = int((time.time() - start_time) * 1000)

        # 记录工具调用日志
        try:
            from routes.tools import log_tool_call
            log_tool_call(
                workflow_run_id=context.get('__workflow_run_id__', ''),
                node_id=data.get('_node_id', ''),
                node_type='mcp',
                provider_id=mcp_server_id,
                tool_name=mcp_tool_name,
                parameters=resolved_params,
                result=result,
                status='success',
                elapsed_ms=elapsed_ms
            )
        except Exception:
            pass

        return {
            output_var: str(result),
            'mcp_output': result,
            'mcp_status': 'success',
            'mcp_server_id': mcp_server_id,
            'mcp_tool_name': mcp_tool_name,
            'mcp_elapsed_ms': elapsed_ms,
        }
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)

        # 记录错误日志
        try:
            from routes.tools import log_tool_call
            log_tool_call(
                workflow_run_id=context.get('__workflow_run_id__', ''),
                node_id=data.get('_node_id', ''),
                node_type='mcp',
                provider_id=mcp_server_id,
                tool_name=mcp_tool_name,
                parameters=resolved_params,
                result='',
                status='error',
                error_message=str(e),
                elapsed_ms=elapsed_ms
            )
        except Exception:
            pass

        return {
            output_var: f'MCP 工具调用错误: {str(e)}',
            'mcp_output': '',
            'mcp_status': 'error',
            'mcp_error': str(e),
            'mcp_elapsed_ms': elapsed_ms,
        }


def _invoke_mcp_tool(mcp_server_id, tool_name, params):
    """
    调用 MCP 服务器的工具。

    支持 http/sse/stdio 三种 MCP 服务器类型。
    使用 JSON-RPC 2.0 协议调用 tools/call 方法。
    """
    # 获取 MCP 服务器配置
    from config import get_db
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT * FROM mcp_servers WHERE id = %s AND enabled = 1', (mcp_server_id,))
        server = cur.fetchone()
    finally:
        db.close()

    if not server:
        raise Exception(f'MCP 服务器不存在或已停用 (ID: {mcp_server_id})')

    mtype = server['mtype']
    url = server['url'] or ''
    command = server['command'] or ''

    # 解析 headers 和 env
    headers = json.loads(server['headers'] or '[]') if isinstance(server['headers'], str) else (server['headers'] or [])
    env = json.loads(server['env'] or '[]') if isinstance(server['env'], str) else (server['env'] or [])

    if mtype in ('http', 'sse'):
        # HTTP/SSE 类型：通过 HTTP 调用 MCP 工具
        return _invoke_mcp_http(url, tool_name, params, headers)
    elif mtype == 'stdio':
        # stdio 类型：通过子进程调用
        return _invoke_mcp_stdio(command, tool_name, params, env)
    else:
        raise Exception(f'不支持的 MCP 服务器类型: {mtype}')


def _invoke_mcp_http(url, tool_name, params, headers):
    """通过 HTTP 调用 MCP 工具（JSON-RPC 2.0，含 SSRF 防护）"""
    import urllib.request
    import urllib.error

    # 安全加固：SSRF 防护检查
    from utils.ssrf import is_safe_url
    if not is_safe_url(url):
        raise Exception('URL 被安全策略禁止（SSRF 防护）')

    payload = json.dumps({
        'jsonrpc': '2.0',
        'method': 'tools/call',
        'params': {'name': tool_name, 'arguments': params},
        'id': 1
    }).encode('utf-8')

    req_headers = {'Content-Type': 'application/json'}
    for h in headers:
        if isinstance(h, dict) and h.get('k'):
            req_headers[h['k']] = h.get('v', '')

    req = urllib.request.Request(url, data=payload, headers=req_headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        raise Exception(f'MCP HTTP 错误 {e.code}: {e.read().decode("utf-8", errors="replace")[:500]}')

    if 'error' in result:
        raise Exception(f'MCP 错误: {result["error"]}')
    return result.get('result', {}).get('content', str(result.get('result', '')))


def _invoke_mcp_stdio(command, tool_name, params, env):
    """通过 stdio 调用 MCP 工具（子进程）"""
    import subprocess
    import os

    # 构造 MCP JSON-RPC 请求
    request = json.dumps({
        'jsonrpc': '2.0',
        'method': 'tools/call',
        'params': {'name': tool_name, 'arguments': params},
        'id': 1
    })

    # 安全加固：不继承完整环境变量，仅传递必要变量+自定义变量
    run_env = {k: v for k, v in os.environ.items()
               if k in ('PATH', 'HOME', 'USERPROFILE', 'SYSTEMROOT', 'LANG', 'LC_ALL')}
    for e in env:
        if isinstance(e, dict) and e.get('k'):
            run_env[e['k']] = e.get('v', '')

    # 启动子进程
    cmd = command.split()
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=run_env
    )

    try:
        stdout, stderr = proc.communicate(input=request.encode('utf-8'), timeout=60)
        if proc.returncode != 0:
            raise Exception(f'MCP 进程错误: {stderr.decode("utf-8", errors="replace")[:500]}')
        result = json.loads(stdout.decode('utf-8'))
        if 'error' in result:
            raise Exception(f'MCP 错误: {result["error"]}')
        return result.get('result', {}).get('content', str(result.get('result', '')))
    finally:
        if proc.poll() is None:
            proc.kill()
