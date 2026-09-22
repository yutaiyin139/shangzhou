# -*- coding: utf-8 -*-
"""
E2E 测试：Human Input 邮件投递（3.6）
验证:
    1. 表创建（system_settings + human_input_form_deliveries）
    2. SMTP 配置 CRUD
    3. 投递记录创建和查询
    4. 邮件 HTML 构建
    5. Human Input 节点 email 字段透传
    6. 提交时标记投递状态
"""
import json
import sys
import os
import time
import urllib.request

# 确保 backend 目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Windows 编码修复
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = 'http://127.0.0.1:5000'
PASS = 0
FAIL = 0

# 不内置明文口令（错口令会触发登录失败锁定）；由 helper 取真实登录或签发 token
import e2e_auth_helper
AUTH_HEADER = e2e_auth_helper.get_auth_header(verbose=True)


def api(method, path, body=None):
    """调用 API"""
    url = BASE_URL + path
    data = json.dumps(body).encode('utf-8') if body else None
    headers = {'Content-Type': 'application/json'}
    headers.update(AUTH_HEADER)
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


print('\n=== 3.6 Human Input 邮件投递 E2E 测试 ===\n')

# 测试 1: 表创建
print('[1. 表创建]')
from engine.human_input_delivery import ensure_tables
from config import get_db
ensure_tables()
test('ensure_tables 执行成功', True)

db = get_db()
try:
    cur = db.cursor()
    cur.execute("SHOW TABLES LIKE 'system_settings'")
    t1 = cur.fetchone()
    cur.execute("SHOW TABLES LIKE 'human_input_form_deliveries'")
    t2 = cur.fetchone()
finally:
    db.close()
test('system_settings 表存在', t1 is not None)
test('human_input_form_deliveries 表存在', t2 is not None)

# 测试 2: SMTP 配置 CRUD
print('\n[2. SMTP 配置 CRUD]')
from engine.human_input_delivery import (
    get_smtp_config, set_smtp_config, test_smtp_connection
)

# 初始应为 None
cfg = get_smtp_config()
test('初始无 SMTP 配置', cfg is None)

# 设置配置
ok = set_smtp_config({
    'host': 'smtp.example.com',
    'port': 587,
    'username': 'test@example.com',
    'password': 'testpass123',
    'use_tls': True,
    'from_email': 'test@example.com',
    'from_name': '测试发件人',
})
test('设置 SMTP 配置', ok)

cfg = get_smtp_config()
test('获取 SMTP 配置', cfg is not None)
test('host 正确', cfg['host'] == 'smtp.example.com')
test('port 正确', cfg['port'] == 587)
test('username 正确', cfg['username'] == 'test@example.com')
test('password 正确', cfg['password'] == 'testpass123')

# 测试 3: 投递记录
print('\n[3. 投递记录]')
from engine.human_input_delivery import (
    create_delivery, update_delivery_status, get_deliveries,
    mark_delivery_submitted, build_form_url, build_email_html
)

delivery_id = create_delivery(
    run_id='test-run-001',
    app_id='test-app-001',
    node_id='human_node_1',
    email='user@example.com',
    subject='【测试】需要您的输入',
    form_url='/human-input-form?app_id=test-app-001&run_id=test-run-001',
)
test('创建投递记录', delivery_id is not None)

deliveries = get_deliveries(run_id='test-run-001')
test('查询投递记录', len(deliveries) > 0)
if deliveries:
    d = deliveries[0]
    test('投递记录字段完整', d['email'] == 'user@example.com' and d['status'] == 'pending')
    test('包含 run_id', d['run_id'] == 'test-run-001')
    test('包含 app_id', d['app_id'] == 'test-app-001')

# 更新状态
update_delivery_status(delivery_id, 'sent')
deliveries = get_deliveries(run_id='test-run-001')
test('更新为已发送', deliveries[0]['status'] == 'sent')
test('delivered_at 不为空', deliveries[0]['delivered_at'] is not None)

# 标记提交
mark_delivery_submitted('test-run-001')
deliveries = get_deliveries(run_id='test-run-001')
test('标记为已提交', deliveries[0]['status'] == 'submitted')
test('submitted_at 不为空', deliveries[0]['submitted_at'] is not None)

# 测试 4: 表单 URL 和邮件 HTML
print('\n[4. 表单 URL 和邮件 HTML]')
url = build_form_url('app123', 'run456')
test('表单 URL 包含参数', 'app_id=app123' in url and 'run_id=run456' in url)

html = build_email_html('测试应用', '请填写信息', url, [
    {'name': 'feedback', 'label': '反馈意见', 'required': True},
    {'name': 'score', 'label': '评分', 'required': False},
])
test('邮件 HTML 包含应用名', '测试应用' in html)
test('邮件 HTML 包含提示信息', '请填写信息' in html)
test('邮件 HTML 包含表单链接', url in html)
test('邮件 HTML 包含字段标签', '反馈意见' in html and '评分' in html)
test('邮件 HTML 包含必填标记', '必填' in html)

# 测试 5: API 端点
print('\n[5. API 端点]')

# SMTP 配置端点
resp = api('GET', '/api/system/smtp')
test('GET /api/system/smtp', resp.get('code') == 200, f'resp={resp}')
if resp.get('code') == 200 and resp.get('data'):
    test('密码被隐藏', resp['data'].get('password') == '******')

resp = api('POST', '/api/system/smtp', {
    'host': 'smtp.test.com',
    'port': 465,
    'username': 'api@test.com',
    'password': 'apipass',
    'use_tls': False,
})
test('POST /api/system/smtp', resp.get('code') == 200, f'resp={resp}')

resp = api('GET', '/api/system/smtp')
test('更新后获取配置', resp.get('code') == 200 and resp['data']['host'] == 'smtp.test.com')

# 测试连接（会失败因为没有真实服务器，但应该返回错误信息而非崩溃）
resp = api('POST', '/api/system/smtp/test')
test('POST /api/system/smtp/test 返回结果', resp.get('code') in [200, 400], f'resp={resp}')

# 投递记录端点
resp = api('GET', '/api/human-input/deliveries?run_id=test-run-001')
test('GET /api/human-input/deliveries', resp.get('code') == 200, f'resp={resp}')
if resp.get('code') == 200:
    test('返回投递记录', len(resp['data']) > 0)

# 测试 6: Human Input 节点 email 透传
print('\n[6. Human Input 节点 email 透传]')
from engine.nodes.human_input import _node_human_input

result = _node_human_input({
    'message': '请填写反馈',
    'form_fields': [{'name': 'feedback', 'label': '反馈', 'type': 'text', 'required': True}],
    'email': 'notify@example.com',
    '_node_id': 'human_1',
}, {}, None)

test('返回暂停标记', result.get('_human_input_wait') == True)
test('email 在配置中', result['_human_input_config'].get('email') == 'notify@example.com')
test('message 正确', result['_human_input_config']['message'] == '请填写反馈')
test('fields 正确', len(result['_human_input_config']['fields']) == 1)

# 无 email 时不包含 email 字段
result2 = _node_human_input({
    'message': '普通输入',
    'form_fields': [],
}, {}, None)
test('无 email 时不包含字段', 'email' not in result2['_human_input_config'])

# 清理
print('\n[清理测试数据]')
db = get_db()
try:
    cur = db.cursor()
    cur.execute("DELETE FROM human_input_form_deliveries WHERE run_id = 'test-run-001'")
    cur.execute("DELETE FROM system_settings WHERE `key` = 'smtp_config'")
    db.commit()
    test('清理测试数据', True)
finally:
    db.close()

print(f'\n=== 测试结果: {PASS} 通过, {FAIL} 失败 ===\n')
sys.exit(0 if FAIL == 0 else 1)
