# -*- coding: utf-8 -*-
"""任务 1.5 触发器订阅管理 API 端到端验证（用后即焚）"""
import json
import urllib.request
import urllib.error

BASE = 'http://localhost:5000'
APP = 'ad72f39c-e507-4d88-a934-37dd6f38c582'


def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method)
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, data) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


P = f'/api/workflows/{APP}/trigger-subscriptions'

s, r = call('GET', P)
assert s == 200 and r['data'] == [], r
print('1 empty list OK')

s, r = call('POST', P, {'trigger_type': 'foo', 'target_id': 'x', 'subscriber_type': 'api', 'subscriber_target': 't1'})
assert r['code'] == 400, r
print('2 bad trigger_type 400 OK')

s, r = call('POST', P, {'trigger_type': 'plugin', 'target_id': APP, 'subscriber_type': 'sms', 'subscriber_target': 't1'})
assert r['code'] == 400, r
print('3 bad subscriber_type 400 OK')

s, r = call('POST', P, {'trigger_type': 'plugin', 'target_id': APP, 'subscriber_type': 'email', 'subscriber_target': 'not-an-email'})
assert r['code'] == 400, r
print('4 bad email 400 OK')

s, r = call('POST', P, {'trigger_type': 'plugin', 'target_id': APP, 'subscriber_type': 'webhook', 'subscriber_target': 'http://192.168.1.10/cb'})
assert r['code'] == 400, r
print('5 SSRF blocked OK')

s, r = call('POST', P, {'trigger_type': 'webhook', 'target_id': '00000000-0000-0000-0000-000000000000', 'subscriber_type': 'api', 'subscriber_target': 't1'})
assert r['code'] == 404, r
print('6 missing target 404 OK')

s, r = call('POST', P, {'trigger_type': 'plugin', 'target_id': APP, 'subscriber_type': 'api', 'subscriber_target': 'e2e-sub-001'})
assert s == 200 and r['data'].get('id'), r
sub_id = r['data']['id']
print('7 create OK')

s, r = call('POST', P, {'trigger_type': 'plugin', 'target_id': APP, 'subscriber_type': 'api', 'subscriber_target': 'e2e-sub-001'})
assert s == 200 and r['data'].get('duplicated'), r
print('8 idempotent OK')

s, r = call('POST', P, {'trigger_type': 'plugin', 'target_id': APP, 'subscriber_type': 'email', 'subscriber_target': 'ops@example.com'})
assert s == 200, r
print('9 email sub OK')

s, r = call('GET', P)
assert len(r['data']) == 2, r
print('10 list=2 OK')

s, r = call('PUT', f'/api/trigger-subscriptions/{sub_id}', {'enabled': False})
assert r['code'] == 200, r
s, r = call('GET', P)
row = [x for x in r['data'] if x['id'] == sub_id][0]
assert row['enabled'] == 0, row
print('11 disable OK')

s, r = call('PUT', f'/api/trigger-subscriptions/{sub_id}', {'subscriber_target': 'e2e-sub-002'})
assert r['code'] == 200, r
print('12 update target OK')

s, r = call('PUT', f'/api/trigger-subscriptions/{sub_id}', {'subscriber_target': ''})
assert r['code'] == 400, r
print('13 empty target 400 OK')

s, r = call('GET', f'/api/trigger-subscriptions/{sub_id}/logs')
assert s == 200 and 'items' in r['data'], r
print('14 logs OK total=', r['data']['total'])

s, r = call('GET', P)
for x in r['data']:
    s2, r2 = call('DELETE', f"/api/trigger-subscriptions/{x['id']}")
    assert r2['code'] == 200, r2
s, r = call('GET', P)
assert r['data'] == [], r
print('15 delete all OK')

s, r = call('DELETE', f'/api/trigger-subscriptions/{sub_id}')
assert r['code'] == 404, r
print('16 delete missing 404 OK')

print()
print('ALL 16 CHECKS PASSED')
