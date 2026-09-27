# -*- coding: utf-8 -*-
"""
E2E 测试：工具标签/版本（3.5）
验证:
    1. 表创建（tool_label_bindings + version 字段迁移）
    2. 标签增删查
    3. 批量设置标签
    4. 按标签筛选工具
    5. 工具版本管理
    6. API 端点
"""
import json
import sys
import os
import uuid
import urllib.parse

# 确保 backend 目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Windows 编码修复
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = 'http://127.0.0.1:5000'
PASS = 0
FAIL = 0

# 后端已启用全局鉴权闸门（REQUIRE_LOGIN_FOR_API=strict），走 live HTTP 的脚本也必须带 token
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


print('\n=== 3.5 工具标签/版本 E2E 测试 ===\n')

# 准备测试数据：创建一个 API 工具提供者
from config import get_db

db = get_db()
try:
    cur = db.cursor()
    test_tool_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO tool_api_providers
        (id, tenant_id, name, description, server_url, status)
        VALUES (%s, 'test-tenant', '标签测试工具', '用于标签测试', 'http://test.example.com', 'active')
    """, (test_tool_id,))
    db.commit()
finally:
    db.close()

test('创建测试工具', True)

# 测试 1: 表创建
print('\n[1. 表创建]')
from engine.tool_label_engine import ensure_label_tables
ensure_label_tables()
test('ensure_label_tables 执行成功', True)

db = get_db()
try:
    cur = db.cursor()
    cur.execute("SHOW TABLES LIKE 'tool_label_bindings'")
    t = cur.fetchone()
    test('tool_label_bindings 表存在', t is not None)

    # 检查 version 字段
    cur.execute("SHOW COLUMNS FROM tool_api_providers LIKE 'version'")
    v = cur.fetchone()
    test('tool_api_providers 有 version 字段', v is not None)
finally:
    db.close()

# 测试 2: 标签增删查
print('\n[2. 标签增删查]')
from engine.tool_label_engine import add_label, remove_label, get_tool_labels

r = add_label('api', test_tool_id, '效率')
test('添加标签', r is not None)

r = add_label('api', test_tool_id, '测试')
test('添加第二个标签', r is not None)

# 重复添加（应该不报错，幂等）
r = add_label('api', test_tool_id, '效率')
test('重复添加标签幂等', r is not None)

labels = get_tool_labels('api', test_tool_id)
test('获取标签列表', len(labels) == 2, f'labels={labels}')
test('包含效率', '效率' in labels)
test('包含测试', '测试' in labels)

# 无效标签
r = add_label('api', test_tool_id, '')
test('空标签被拒绝', r is None)
r = add_label('api', test_tool_id, 'a' * 101)
test('超长标签被拒绝', r is None)
r = add_label('api', test_tool_id, '<script>')
test('特殊字符标签被拒绝', r is None)

ok = remove_label('api', test_tool_id, '测试')
test('移除标签', ok)
labels = get_tool_labels('api', test_tool_id)
test('移除后只剩一个', len(labels) == 1 and labels[0] == '效率')

# 测试 3: 批量设置标签
print('\n[3. 批量设置标签]')
from engine.tool_label_engine import batch_set_labels

n = batch_set_labels('api', test_tool_id, ['AI', '开发', '网络'])
test('批量设置标签', n == 3, f'n={n}')

labels = get_tool_labels('api', test_tool_id)
test('批量设置后标签正确', set(labels) == {'AI', '开发', '网络'}, f'labels={labels}')

# 再次批量（覆盖）
n = batch_set_labels('api', test_tool_id, ['效率'])
test('覆盖式批量设置', n == 1)
labels = get_tool_labels('api', test_tool_id)
test('覆盖后只剩一个', labels == ['效率'])

# 测试 4: 按标签筛选
print('\n[4. 按标签筛选]')
from engine.tool_label_engine import get_tools_by_label, list_all_labels, filter_tools

# 给第二个工具加标签
test_tool_id2 = str(uuid.uuid4())
db = get_db()
try:
    cur = db.cursor()
    cur.execute("""
        INSERT INTO tool_api_providers
        (id, tenant_id, name, description, server_url, status)
        VALUES (%s, 'test-tenant', '第二个工具', '另一个', 'http://test2.example.com', 'active')
    """, (test_tool_id2,))
    db.commit()
finally:
    db.close()
add_label('api', test_tool_id2, '效率')

bindings = get_tools_by_label(label='效率')
test('按标签查询', len(bindings) >= 2, f'bindings={len(bindings)}')
test('包含两个工具', any(b['tool_id'] == test_tool_id for b in bindings) and any(b['tool_id'] == test_tool_id2 for b in bindings))

all_labels = list_all_labels()
test('列出所有标签', len(all_labels) > 0)
eff_labels = [l for l in all_labels if l['label'] == '效率']
test('效率标签计数正确', len(eff_labels) > 0 and eff_labels[0]['tool_count'] >= 2)

# filter_tools
tools = filter_tools(tool_type='api', label='效率')
test('filter_tools 按类型+标签', len(tools) >= 2, f'tools={len(tools)}')
tools = filter_tools(keyword='标签测试')
test('filter_tools 按关键字', len(tools) == 1 and tools[0]['name'] == '标签测试工具')

# 测试 5: 工具版本管理
print('\n[5. 工具版本管理]')
from engine.tool_label_engine import set_tool_version, get_tool_version

ok = set_tool_version('api', test_tool_id, '2.0.0')
test('设置版本', ok)
v = get_tool_version('api', test_tool_id)
test('获取版本', v == '2.0.0')

ok = set_tool_version('nonexistent', test_tool_id, '3.0.0')
test('无效类型返回 False', not ok)

# 测试 6: API 端点
print('\n[6. API 端点]')

# 需要重启服务器才能加载新路由
import urllib.request
try:
    resp = api('GET', '/api/tools/labels')
    if resp.get('code') == 404:
        print('\n  [SKIP] API 端点测试需要重启服务器')
    else:
        test('GET /api/tools/labels', resp.get('code') == 200, f'resp={resp}')

        resp = api('POST', '/api/tools/labels/bind', {
            'tool_type': 'api', 'tool_id': test_tool_id, 'label': 'API端点测试'
        })
        test('POST /api/tools/labels/bind', resp.get('code') == 200, f'resp={resp}')

        resp = api('GET', f'/api/tools/api/{test_tool_id}/labels')
        test('GET 工具标签', resp.get('code') == 200 and 'API端点测试' in (resp.get('data') or []))

        resp = api('POST', '/api/tools/labels/batch', {
            'tool_type': 'api', 'tool_id': test_tool_id,
            'labels': ['批量1', '批量2']
        })
        test('POST /api/tools/labels/batch', resp.get('code') == 200, f'resp={resp}')

        resp = api('GET', f'/api/tools/filter?tool_type=api&label=' + urllib.parse.quote('批量1'))
        test('GET /api/tools/filter', resp.get('code') == 200, f'resp={resp}')

        resp = api('PUT', f'/api/tools/api/{test_tool_id}/version', {'version': '3.1.0'})
        test('PUT 工具版本', resp.get('code') == 200, f'resp={resp}')

        resp = api('POST', '/api/tools/labels/unbind', {
            'tool_type': 'api', 'tool_id': test_tool_id, 'label': '批量1'
        })
        test('POST /api/tools/labels/unbind', resp.get('code') == 200)
except Exception as e:
    print(f'\n  [SKIP] API 端点测试异常: {e}')

# 清理
print('\n[清理测试数据]')
db = get_db()
try:
    cur = db.cursor()
    cur.execute("DELETE FROM tool_label_bindings WHERE tool_id IN (%s, %s)", (test_tool_id, test_tool_id2))
    cur.execute("DELETE FROM tool_api_providers WHERE id IN (%s, %s)", (test_tool_id, test_tool_id2))
    db.commit()
    test('清理测试数据', True)
finally:
    db.close()

print(f'\n=== 测试结果: {PASS} 通过, {FAIL} 失败 ===\n')
sys.exit(0 if FAIL == 0 else 1)
