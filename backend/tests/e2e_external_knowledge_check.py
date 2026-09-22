# -*- coding: utf-8 -*-
"""
E2E 测试：外部知识 API（3.3）
验证:
    1. 表创建
    2. 外部 API CRUD
    3. 绑定管理
    4. 检索代理（mock 外部 API）
    5. 错误处理
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


def api(method, path, body=None):
    """调用 API"""
    url = BASE_URL + path
    data = json.dumps(body).encode('utf-8') if body else None
    headers = {'Content-Type': 'application/json'}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode('utf-8'))
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


# Mock 外部检索 API
class MockHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        data = json.loads(body.decode('utf-8'))

        query = data.get('query', '')

        # 模拟返回结果
        results = [
            {
                'content': f'外部知识结果1：关于「{query}」的信息',
                'score': 0.95,
                'title': '外部文档A',
                'metadata': {'source': 'mock'},
            },
            {
                'content': f'外部知识结果2：{query} 的详细说明',
                'score': 0.85,
                'title': '外部文档B',
                'metadata': {'source': 'mock'},
            },
        ]

        response = json.dumps({'results': results}).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        pass  # 静音日志


def start_mock_server(port=18080):
    """启动 mock 外部 API 服务器"""
    server = http.server.HTTPServer(('127.0.0.1', port), MockHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


print('\n=== 3.3 外部知识 API E2E 测试 ===\n')

# 启动 mock 服务器
mock_server = start_mock_server()
time.sleep(0.5)
print('[Mock 外部 API 已启动在端口 18080]\n')

# 准备测试数据
print('[准备测试数据]')
from config import get_db
import uuid

db = get_db()
try:
    cur = db.cursor()
    # 创建测试知识库
    cur.execute("""
        INSERT INTO dify_datasets (id, tenant_id, name, description, created_by, updated_by)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (str(uuid.uuid4()), 'test-tenant', '外部知识测试库', '', None, None))
    db.commit()
    dataset_id = cur.lastrowid
    # 获取实际 ID（自增的）
    cur.execute("SELECT id FROM dify_datasets WHERE name = '外部知识测试库' ORDER BY created_at DESC LIMIT 1")
    ds_row = cur.fetchone()
    dataset_id = ds_row['id']
finally:
    db.close()

test('创建测试知识库', dataset_id is not None)

# 测试 1: 表创建
print('\n[1. 表创建]')
from engine.external_knowledge import ensure_external_knowledge_tables
ensure_external_knowledge_tables()
test('ensure_external_knowledge_tables 执行成功', True)

# 验证表存在
db = get_db()
try:
    cur = db.cursor()
    cur.execute("SHOW TABLES LIKE 'external_knowledge_apis'")
    table1 = cur.fetchone()
    cur.execute("SHOW TABLES LIKE 'external_knowledge_bindings'")
    table2 = cur.fetchone()
finally:
    db.close()
test('external_knowledge_apis 表存在', table1 is not None)
test('external_knowledge_bindings 表存在', table2 is not None)

# 测试 2: 外部 API CRUD
print('\n[2. 外部 API CRUD]')
from engine.external_knowledge import (
    create_external_api, get_external_api, update_external_api,
    delete_external_api, list_external_apis
)

api_id = create_external_api('测试API', 'http://127.0.0.1:18080/retrieve', '测试描述', 'test-key', 30)
test('创建外部 API', api_id is not None and api_id.get('id') is not None)

if api_id:
    api_id = api_id['id']

    api_detail = get_external_api(api_id)
    test('获取外部 API', api_detail is not None and api_detail['name'] == '测试API')
    test('API endpoint 正确', api_detail['endpoint_url'] == 'http://127.0.0.1:18080/retrieve')

    ok = update_external_api(api_id, name='更新后API', description='更新描述')
    test('更新外部 API', ok)

    updated = get_external_api(api_id)
    test('更新后名称正确', updated['name'] == '更新后API')

    apis = list_external_apis()
    test('列表包含新 API', any(a['id'] == api_id for a in apis))

# 测试 3: 绑定管理
print('\n[3. 绑定管理]')
from engine.external_knowledge import (
    bind_external_api, unbind_external_api, get_dataset_external_apis
)

binding = bind_external_api(dataset_id, api_id)
test('绑定外部 API', binding is not None)

apis = get_dataset_external_apis(dataset_id)
test('获取数据集绑定的 API', len(apis) > 0 and apis[0]['id'] == api_id)

# 测试 4: 检索代理
print('\n[4. 检索代理]')
from engine.external_knowledge import call_external_api, retrieve_external_knowledge

api_config = get_external_api(api_id)
results, error = call_external_api(api_config, '人工智能', top_k=3)
test('调用外部 API 成功', error is None, f'error={error}')
test('返回结果非空', len(results) > 0, f'results={len(results)}')
if results:
    test('结果包含 content', 'content' in results[0])
    test('结果包含 score', 'score' in results[0] and 0 <= results[0]['score'] <= 1)
    test('结果标记为外部', results[0].get('is_external') == True)

results2, errors2 = retrieve_external_knowledge([dataset_id], '机器学习', top_k=3)
test('retrieve_external_knowledge 成功', len(errors2) == 0, f'errors={errors2}')
test('返回结果非空', len(results2) > 0)

# 测试 5: 错误处理
print('\n[5. 错误处理]')
bad_config = {'endpoint_url': 'http://127.0.0.1:99999/nonexistent', 'timeout': 2, 'name': '坏API'}
results3, error3 = call_external_api(bad_config, 'test')
test('连接失败返回错误', error3 is not None)

# 测试 6: API 端点
print('\n[6. API 端点]')
resp = api('GET', '/api/knowledge/external-apis')
test('GET external-apis 列表', resp.get('code') == 200, f'resp={resp}')
if resp.get('code') == 200:
    test('列表包含 API', any(a['id'] == api_id for a in resp['data']))

resp = api('POST', '/api/knowledge/external-apis', {
    'name': 'API端点测试',
    'endpoint_url': 'http://127.0.0.1:18080/retrieve',
    'api_key': 'test',
    'timeout': 30,
})
test('POST external-apis 创建', resp.get('code') == 200, f'resp={resp}')
endpoint_api_id = resp.get('data', {}).get('id')

if endpoint_api_id:
    resp = api('GET', f'/api/knowledge/external-apis/{endpoint_api_id}')
    test('GET external-apis/{id}', resp.get('code') == 200)

    resp = api('PUT', f'/api/knowledge/external-apis/{endpoint_api_id}', {'name': '更新名称'})
    test('PUT external-apis/{id}', resp.get('code') == 200)

resp = api('GET', f'/api/knowledge/datasets/{dataset_id}/external-bindings')
test('GET external-bindings', resp.get('code') == 200, f'resp={resp}')

resp = api('POST', f'/api/knowledge/datasets/{dataset_id}/external-bindings', {
    'external_api_id': endpoint_api_id or api_id,
})
test('POST external-bindings', resp.get('code') == 200, f'resp={resp}')

resp = api('POST', '/api/knowledge/external-retrieve', {
    'dataset_id': dataset_id,
    'query': '测试查询',
    'top_k': 3,
})
test('POST external-retrieve', resp.get('code') == 200, f'resp={resp}')
if resp.get('code') == 200:
    test('external-retrieve 返回结果', len(resp['data'].get('results', [])) > 0)

# 清理
print('\n[清理测试数据]')
if endpoint_api_id:
    resp = api('DELETE', f'/api/knowledge/external-apis/{endpoint_api_id}')
    test('删除 API 端点', resp.get('code') == 200)

if api_id:
    ok = delete_external_api(api_id)
    test('删除外部 API', ok)

# 清理测试知识库
db = get_db()
try:
    cur = db.cursor()
    cur.execute("DELETE FROM dify_datasets WHERE name = '外部知识测试库'")
    db.commit()
    test('清理测试知识库', True)
finally:
    db.close()

# 停止 mock 服务器
mock_server.shutdown()

print(f'\n=== 测试结果: {PASS} 通过, {FAIL} 失败 ===\n')
sys.exit(0 if FAIL == 0 else 1)
