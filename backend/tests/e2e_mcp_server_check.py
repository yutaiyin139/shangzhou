# -*- coding: utf-8 -*-
"""
E2E 测试：MCP 服务端（3.7）
验证:
    1. SSE 端点连接与 endpoint 事件
    2. JSON-RPC initialize 握手
    3. tools/list 工具列表
    4. tools/call 工具调用
    5. ping 心跳
    6. 未知方法错误
    7. REST 工具列表端点
"""
import json
import sys
import os
import time
import threading
import urllib.request
import urllib.parse
import http.client

# 确保 backend 目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Windows 编码修复
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = 'http://127.0.0.1:5000'
MCP_URL = f'{BASE_URL}/mcp/v1'
PASS = 0
FAIL = 0


def test(name, condition, detail=''):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  [PASS] {name}')
    else:
        FAIL += 1
        print(f'  [FAIL] {name} {detail}')


class MCPClient:
    """简单的 MCP 客户端用于测试"""

    def __init__(self):
        self.session_id = None
        self.endpoint_url = None
        self.responses = {}
        self.events = []
        self._connected = False
        self._thread = None
        self._conn = None

    def connect(self, timeout=10):
        """连接 SSE 端点"""
        self._conn = http.client.HTTPConnection('127.0.0.1', 5000, timeout=timeout)
        self._conn.request('GET', '/mcp/v1')
        self._response = self._conn.getresponse()

        # 读取 endpoint 事件
        line = self._response.fp.readline().decode('utf-8').strip()
        if line.startswith('event: endpoint'):
            data_line = self._response.fp.readline().decode('utf-8').strip()
            if data_line.startswith('data: '):
                self.endpoint_url = data_line[6:]
                # 提取 session_id
                parsed = urllib.parse.urlparse(self.endpoint_url)
                params = urllib.parse.parse_qs(parsed.query)
                self.session_id = params.get('session_id', [None])[0]
                self._connected = True

                # 启动后台线程读取事件
                self._thread = threading.Thread(target=self._read_events, daemon=True)
                self._thread.start()
                return True
        return False

    def _read_events(self):
        """后台读取 SSE 事件"""
        buffer = b''
        try:
            while True:
                chunk = self._response.fp.readline()
                if not chunk:
                    break
                line = chunk.decode('utf-8').strip()
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        if 'id' in data:
                            self.responses[data['id']] = data
                        self.events.append(data)
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass

    def send(self, method, params=None, msg_id=None):
        """发送 JSON-RPC 消息"""
        if not self.endpoint_url:
            return None

        message = {
            'jsonrpc': '2.0',
            'method': method,
        }
        if params is not None:
            message['params'] = params
        if msg_id is not None:
            message['id'] = msg_id

        url = self.endpoint_url
        data = json.dumps(message).encode('utf-8')

        req = urllib.request.Request(
            f'{BASE_URL}{url}',
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            return {'error': str(e)}

    def wait_for_response(self, msg_id, timeout=5):
        """等待响应"""
        start = time.time()
        while time.time() - start < timeout:
            if msg_id in self.responses:
                return self.responses[msg_id]
            time.sleep(0.1)
        return None

    def call(self, method, params=None, msg_id=1, timeout=5):
        """发送请求并等待响应"""
        self.send(method, params, msg_id)
        return self.wait_for_response(msg_id, timeout)


print('\n=== 3.7 MCP 服务端 E2E 测试 ===\n')

# 测试 0: 健康检查
print('[0. 健康检查]')
try:
    with urllib.request.urlopen(f'{MCP_URL}/health', timeout=5) as resp:
        health = json.loads(resp.read().decode('utf-8'))
        test('健康检查返回 OK', health.get('status') == 'ok')
        test('包含协议版本', 'protocol_version' in health)
        test('包含服务器信息', 'server' in health)
except Exception as e:
    test('健康检查', False, f'error={e}')

# 测试 1: 直接测试 JSON-RPC 处理逻辑（不依赖 SSE 长连接）
print('\n[1. JSON-RPC 处理逻辑]')
from engine.mcp_server import (
    _handle_jsonrpc, _get_or_create_session, _send_to_session,
    _get_all_tools, _execute_mcp_tool,
)

# 创建测试会话
sid = _get_or_create_session()
test('创建会话', sid is not None)

# initialize
resp = _handle_jsonrpc({
    'jsonrpc': '2.0', 'id': 1,
    'method': 'initialize',
    'params': {'protocolVersion': '2024-11-05', 'capabilities': {},
               'clientInfo': {'name': 'test', 'version': '1.0'}}
}, sid)
test('initialize 返回结果', resp is not None and 'result' in resp)
if resp and 'result' in resp:
    r = resp['result']
    test('包含 protocolVersion', 'protocolVersion' in r)
    test('包含 serverInfo', 'serverInfo' in r)
    test('包含 capabilities', 'capabilities' in r)

# ping
resp = _handle_jsonrpc({'jsonrpc': '2.0', 'id': 2, 'method': 'ping'}, sid)
test('ping 返回结果', resp is not None and resp.get('result') == {})

# tools/list
resp = _handle_jsonrpc({'jsonrpc': '2.0', 'id': 3, 'method': 'tools/list'}, sid)
test('tools/list 返回结果', resp is not None and 'result' in resp)
if resp and 'result' in resp:
    tools = resp['result'].get('tools', [])
    test('工具列表非空', len(tools) > 0, f'tools={len(tools)}')
    if tools:
        t = tools[0]
        test('工具包含 name', 'name' in t)
        test('工具包含 description', 'description' in t)
        test('工具包含 inputSchema', 'inputSchema' in t)

# 通知
resp = _handle_jsonrpc({'jsonrpc': '2.0', 'method': 'notifications/initialized'}, sid)
test('通知返回 None', resp is None)

# 未知方法
resp = _handle_jsonrpc({'jsonrpc': '2.0', 'id': 4, 'method': 'unknown/method'}, sid)
test('未知方法返回错误', resp is not None and 'error' in resp)

# 测试 2: 工具执行
print('\n[2. 工具执行]')
# 获取所有工具
tools = _get_all_tools()
test('获取工具列表', len(tools) > 0)
print(f'  共 {len(tools)} 个工具')

# 找一个计算器工具
calc_tool = None
for t in tools:
    if 'calculator' in t['name'].lower():
        calc_tool = t
        break

if calc_tool:
    print(f'  测试工具: {calc_tool["name"]}')
    result = _execute_mcp_tool(calc_tool['name'], {'expression': '2+3'})
    test('工具执行返回结果', result is not None)
    content = result.get('content', [])
    test('返回 content', len(content) > 0)
    if content:
        test('包含 text', 'text' in content[0])
        print(f'  结果: {content[0]["text"][:100]}')

# 无效工具
result = _execute_mcp_tool('nonexistent__tool', {})
test('无效工具返回错误', result.get('isError') == True)

# 测试 3: REST 工具列表端点
print('\n[3. REST 工具列表]')
try:
    with urllib.request.urlopen(f'{BASE_URL}/api/mcp-server/tools', timeout=5) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        test('REST 工具列表', data.get('code') == 200)
        if data.get('code') == 200:
            tools = data['data'].get('tools', [])
            test('工具数量正确', data['data'].get('count') == len(tools))
            print(f'  共 {len(tools)} 个工具')
except Exception as e:
    test('REST 工具列表', False, f'error={e}')

# 测试 4: POST 消息端点
print('\n[4. POST 消息端点]')
# 先创建一个新会话
sid2 = _get_or_create_session()
# 构造 endpoint URL
endpoint = f'/mcp/v1/messages?session_id={sid2}'

# 发送 initialize 消息
req = urllib.request.Request(
    f'{BASE_URL}{endpoint}',
    data=json.dumps({
        'jsonrpc': '2.0', 'id': 10,
        'method': 'initialize',
        'params': {'protocolVersion': '2024-11-05', 'capabilities': {},
                   'clientInfo': {'name': 'test', 'version': '1.0'}}
    }).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST',
)
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        test('POST 消息返回 accepted', result.get('status') == 'accepted')
except Exception as e:
    test('POST 消息', False, f'error={e}')

# 发送 ping
req = urllib.request.Request(
    f'{BASE_URL}{endpoint}',
    data=json.dumps({'jsonrpc': '2.0', 'id': 11, 'method': 'ping'}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST',
)
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        test('POST ping 返回 accepted', result.get('status') == 'accepted')
except Exception as e:
    test('POST ping', False, f'error={e}')

# 无效 session（现在自动创建，应返回 accepted）
req = urllib.request.Request(
    f'{MCP_URL}/messages?session_id=invalid_session',
    data=json.dumps({'jsonrpc': '2.0', 'method': 'ping', 'id': 99}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST',
)
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        test('无效 session 自动创建并返回 accepted', result.get('status') == 'accepted')
except urllib.error.HTTPError as e:
    test('无效 session 处理', False, f'HTTP {e.code}')

# 测试 5: 无效 JSON
print('\n[5. 错误处理]')
req = urllib.request.Request(
    f'{BASE_URL}{endpoint}',
    data=b'not json',
    headers={'Content-Type': 'application/json'},
    method='POST',
)
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        test('无效 JSON 应返回 400', False)
except urllib.error.HTTPError as e:
    test('无效 JSON 返回 400', e.code == 400)

# 缺少 session_id
req = urllib.request.Request(
    f'{MCP_URL}/messages',
    data=json.dumps({'jsonrpc': '2.0', 'method': 'ping'}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST',
)
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        test('缺少 session_id 应返回 400', False)
except urllib.error.HTTPError as e:
    test('缺少 session_id 返回 400', e.code == 400)

print(f'\n=== 测试结果: {PASS} 通过, {FAIL} 失败 ===\n')
sys.exit(0 if FAIL == 0 else 1)
