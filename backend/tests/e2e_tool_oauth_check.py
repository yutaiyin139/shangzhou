# -*- coding: utf-8 -*-
"""
E2E 测试：工具 OAuth（3.4）
验证:
    1. 表创建（system_clients / tenant_clients / tokens）
    2. OAuth 客户端 CRUD
    3. 授权 URL 生成
    4. OAuth 回调处理（mock OAuth 服务器）
    5. Token 存储和刷新
    6. API 端点
"""
import json
import sys
import os
import time
import urllib.request
import urllib.parse
import threading
import http.server

# 确保 backend 目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Windows 编码修复
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = 'http://127.0.0.1:5000'
PASS = 0
FAIL = 0

# 后端已启用全局鉴权闸门（REQUIRE_LOGIN_FOR_API=strict）：控制台式接口必须带 token，
# 只有 /api/tools/oauth/callback 这类第三方回跳接口在豁免名单里
import e2e_auth_helper

AUTH = e2e_auth_helper.get_auth_header()


def api(method, path, body=None):
    url = BASE_URL + path
    data = json.dumps(body).encode('utf-8') if body else None
    headers = {'Content-Type': 'application/json'}
    headers.update(AUTH)
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        try:
            return json.loads(body)
        except Exception:
            return {'code': e.code, 'body': body[:500]}
    except Exception as e:
        return {'error': str(e)}


def test(name, condition, detail=''):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  [PASS] {name}')
    else:
        FAIL += 1
        print(f'  [FAIL] {name} {detail}')


# Mock OAuth 服务器
class MockOAuthHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        params = urllib.parse.parse_qs(body)
        grant_type = params.get('grant_type', [''])[0]

        if self.path == '/oauth/token':
            if grant_type == 'authorization_code':
                code = params.get('code', [''])[0]
                if code == 'valid_code_123':
                    response = {
                        'access_token': 'mock_access_token_456',
                        'refresh_token': 'mock_refresh_token_789',
                        'expires_in': 3600,
                        'scope': 'read write',
                    }
                else:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'invalid_grant'}).encode())
                    return
            elif grant_type == 'refresh_token':
                refresh_token = params.get('refresh_token', [''])[0]
                if refresh_token == 'mock_refresh_token_789':
                    response = {
                        'access_token': 'mock_access_token_refreshed',
                        'refresh_token': 'mock_refresh_token_789',
                        'expires_in': 3600,
                        'scope': 'read write',
                    }
                else:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'invalid_grant'}).encode())
                    return
            else:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'unsupported_grant_type'}).encode())
                return

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def start_mock_oauth_server(port=18081):
    server = http.server.HTTPServer(('127.0.0.1', port), MockOAuthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


print('\n=== 3.4 工具 OAuth E2E 测试 ===\n')

# 启动 mock OAuth 服务器
mock_server = start_mock_oauth_server()
time.sleep(0.5)
print('[Mock OAuth 服务器已启动在端口 18081]\n')

# 测试 1: 表创建
print('[1. 表创建]')
from engine.tool_oauth import ensure_oauth_tables
ensure_oauth_tables()
test('ensure_oauth_tables 执行成功', True)

from config import get_db
db = get_db()
try:
    cur = db.cursor()
    for table in ('tool_oauth_system_clients', 'tool_oauth_tenant_clients', 'tool_oauth_tokens'):
        cur.execute(f"SHOW TABLES LIKE '{table}'")
        t = cur.fetchone()
        test(f'{table} 表存在', t is not None)
finally:
    db.close()

# 测试 2: OAuth 客户端 CRUD
print('\n[2. OAuth 客户端 CRUD]')
from engine.tool_oauth import (
    create_system_client, create_tenant_client,
    get_oauth_client, delete_oauth_client,
)

sys_client_id = create_system_client(
    provider_name='test_provider',
    client_id='sys_client_123',
    client_secret='sys_secret_456',
    auth_url='http://127.0.0.1:18081/oauth/authorize',
    token_url='http://127.0.0.1:18081/oauth/token',
    redirect_uri='http://localhost:5000/api/tools/oauth/callback',
    scopes='read write',
)
test('创建系统级客户端', sys_client_id is not None)

tenant_client_id = create_tenant_client(
    tenant_id='tenant_001',
    provider_name='test_provider',
    client_id='tenant_client_789',
    client_secret='tenant_secret_abc',
    auth_url='http://127.0.0.1:18081/oauth/authorize',
    token_url='http://127.0.0.1:18081/oauth/token',
    redirect_uri='http://localhost:5000/api/tools/oauth/callback',
    scopes='read',
)
test('创建租户级客户端', tenant_client_id is not None)

# 租户级优先
client = get_oauth_client('tenant_001', 'test_provider')
test('获取客户端（租户级优先）', client is not None)
if client:
    test('租户级 client_id 正确', client['client_id'] == 'tenant_client_789')
    test('level 为 tenant', client['level'] == 'tenant')

# 系统级回退
client = get_oauth_client(None, 'test_provider')
test('获取客户端（系统级）', client is not None)
if client:
    test('系统级 client_id 正确', client['client_id'] == 'sys_client_123')
    test('level 为 system', client['level'] == 'system')

# 不存在的 provider
client = get_oauth_client(None, 'nonexistent')
test('不存在的 provider 返回 None', client is None)

# 测试 3: 授权 URL 生成
print('\n[3. 授权 URL 生成]')
from engine.tool_oauth import generate_auth_url, _oauth_states

url, state = generate_auth_url('tenant_001', 'test_provider')
test('生成授权 URL', url is not None, f'url={url}')
test('生成 state', state is not None)
if url:
    test('URL 包含 client_id', 'tenant_client_789' in url)
    test('URL 包含 redirect_uri', 'redirect_uri' in url)
    test('URL 包含 state', state in url)
    test('URL 包含 scope', 'scope=read' in url)
    test('state 已存储', state in _oauth_states)

# 不存在的 provider
url2, err = generate_auth_url(None, 'nonexistent')
test('不存在的 provider 返回错误', url2 is None and err is not None)

# 测试 4: OAuth 回调
print('\n[4. OAuth 回调处理]')
from engine.tool_oauth import handle_oauth_callback, get_token_status

# 先生成一个新的 state
url, state = generate_auth_url('tenant_001', 'test_provider')

# 模拟回调（使用有效 code）
success, msg = handle_oauth_callback(state, code='valid_code_123')
test('回调处理成功', success, f'msg={msg}')
test('成功消息包含 provider', 'test_provider' in msg)

# state 应该被消费
success2, msg2 = handle_oauth_callback(state, code='valid_code_123')
test('重复 state 被拒绝', not success2)

# 无效 code
url, state = generate_auth_url('tenant_001', 'test_provider')
success3, msg3 = handle_oauth_callback(state, code='invalid_code')
test('无效 code 返回错误', not success3)

# 错误参数
url, state = generate_auth_url('tenant_001', 'test_provider')
success4, msg4 = handle_oauth_callback(state, error='access_denied')
test('用户拒绝授权', not success4 and 'access_denied' in msg4)

# 测试 5: Token 存储和状态
print('\n[5. Token 存储和状态]')
from engine.tool_oauth import get_valid_token

status = get_token_status('tenant_001', 'test_provider')
test('token 状态存在', status is not None)
if status:
    test('状态为 active', status['status'] == 'active')
    test('未过期', not status['expired'])
    test('包含 scopes', 'read' in status['scopes'])

# 获取有效 token
token, err = get_valid_token('tenant_001', 'test_provider')
test('获取有效 token', token is not None, f'err={err}')
if token:
    test('token 正确', token == 'mock_access_token_456')

# 未授权的 provider
token2, err2 = get_valid_token('tenant_001', 'unauthorized_provider')
test('未授权 provider 返回错误', token2 is None and err2 is not None)

# 测试 6: Token 撤销
print('\n[6. Token 撤销]')
from engine.tool_oauth import revoke_token

ok = revoke_token('tenant_001', 'test_provider')
test('撤销 token', ok)

status = get_token_status('tenant_001', 'test_provider')
test('撤销后状态为 revoked', status['status'] == 'revoked')

# 重新授权（为后续测试）
url, state = generate_auth_url('tenant_001', 'test_provider')
handle_oauth_callback(state, code='valid_code_123')

# 测试 7: API 端点
print('\n[7. API 端点]')

resp = api('POST', '/api/tools/oauth/system-clients', {
    'provider_name': 'api_test_provider',
    'client_id': 'api_sys_client',
    'client_secret': 'api_sys_secret',
    'auth_url': 'http://127.0.0.1:18081/oauth/authorize',
    'token_url': 'http://127.0.0.1:18081/oauth/token',
    'redirect_uri': 'http://localhost:5000/api/tools/oauth/callback',
    'scopes': 'read',
})
test('POST system-clients', resp.get('code') == 200, f'resp={resp}')

resp = api('POST', '/api/tools/oauth/tenant-clients', {
    'tenant_id': 'tenant_001',
    'provider_name': 'api_tenant_provider',
    'client_id': 'api_tenant_client',
    'client_secret': 'api_tenant_secret',
    'auth_url': 'http://127.0.0.1:18081/oauth/authorize',
    'token_url': 'http://127.0.0.1:18081/oauth/token',
    'scopes': 'read',
})
test('POST tenant-clients', resp.get('code') == 200, f'resp={resp}')

resp = api('POST', '/api/tools/oauth/authorize', {
    'provider_name': 'api_tenant_provider',
    'tenant_id': 'tenant_001',
})
test('POST authorize', resp.get('code') == 200, f'resp={resp}')
if resp.get('code') == 200:
    test('返回 auth_url', 'auth_url' in resp['data'])
    test('返回 state', 'state' in resp['data'])
    api_state = resp['data']['state']

# 测试回调端点（返回 HTML，需要特殊处理）
try:
    url = f'{BASE_URL}/api/tools/oauth/callback?code=valid_code_123&state={api_state}'
    req = urllib.request.Request(url, method='GET')
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode('utf-8')
        test('GET callback 返回成功页面', resp.status == 200 and '授权成功' in html)
except Exception as e:
    test('GET callback', False, f'error={e}')

resp = api('GET', '/api/tools/oauth/token-status?provider_name=api_tenant_provider&tenant_id=tenant_001')
test('GET token-status', resp.get('code') == 200, f'resp={resp}')
if resp.get('code') == 200:
    test('已授权', resp['data'].get('authorized') == True)

resp = api('POST', '/api/tools/oauth/revoke', {
    'provider_name': 'api_tenant_provider',
    'tenant_id': 'tenant_001',
})
test('POST revoke', resp.get('code') == 200, f'resp={resp}')

# 清理
print('\n[清理测试数据]')
from engine.tool_oauth import delete_oauth_client

ok = delete_oauth_client('test_provider')
test('删除系统级客户端', ok)
ok = delete_oauth_client('test_provider', 'tenant_001')
test('删除租户级客户端', ok)
ok = delete_oauth_client('api_test_provider')
test('删除 API 测试系统客户端', ok)
ok = delete_oauth_client('api_tenant_provider', 'tenant_001')
test('删除 API 测试租户客户端', ok)

db = get_db()
try:
    cur = db.cursor()
    cur.execute("DELETE FROM tool_oauth_tokens WHERE provider_name IN ('test_provider', 'api_tenant_provider')")
    db.commit()
    test('清理 token 数据', True)
finally:
    db.close()

mock_server.shutdown()

print(f'\n=== 测试结果: {PASS} 通过, {FAIL} 失败 ===\n')
sys.exit(0 if FAIL == 0 else 1)
