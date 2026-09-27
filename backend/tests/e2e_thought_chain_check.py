# -*- coding: utf-8 -*-
"""任务 2.2 Agent 思考链记录 端到端验证（用后即焚）"""
import json
import urllib.request
import urllib.error

# 后端已启用全局鉴权闸门（REQUIRE_LOGIN_FOR_API=strict），走 live HTTP 的脚本也必须带 token
import e2e_auth_helper

AUTH = e2e_auth_helper.get_auth_header()

BASE = 'http://localhost:5000'


def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method)
    for _k, _v in AUTH.items():
        req.add_header(_k, _v)
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, data) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


# 1. 验证表已创建（通过 API 查询不存在的消息思考链）
s, r = call('GET', '/api/messages/nonexistent-msg-id/thoughts')
assert s == 200 and r['data']['items'] == [], r
print('1 thoughts API accessible OK')

# 2. 直接测试保存和检索（通过 engine 模块）
import sys
sys.path.insert(0, '.')
from engine.thought_chain import save_thought_chain, get_thought_chain, delete_thought_chain

test_msg_id = 'e2e-thought-test-001'
test_chain = [
    {'position': 0, 'thought': '用户问的是天气，我需要调用天气 API', 'tool_name': '', 'tool_input': '', 'tool_output': '', 'observation': ''},
    {'position': 1, 'thought': 'Action: get_weather\nAction Input: {"city": "北京"}', 'tool_name': 'get_weather', 'tool_input': '{"city": "北京"}', 'tool_output': '北京今天晴，25°C', 'observation': '北京今天晴，25°C'},
    {'position': 2, 'thought': 'Final Answer: 北京今天晴天，气温 25°C。', 'tool_name': '', 'tool_input': '', 'tool_output': '', 'observation': ''},
]

n = save_thought_chain(test_msg_id, test_chain)
assert n == 3, f'saved {n} entries'
print('2 save 3 entries OK')

# 3. 通过 API 检索
s, r = call('GET', f'/api/messages/{test_msg_id}/thoughts')
assert s == 200 and r['data']['total'] == 3, r
items = r['data']['items']
assert items[0]['position'] == 0
assert items[1]['tool_name'] == 'get_weather'
assert '北京' in items[1]['tool_output']
print('3 API retrieve 3 entries OK')

# 4. 验证步骤内容
assert '天气' in items[0]['thought']
assert 'Final Answer' in items[2]['thought']
print('4 content verification OK')

# 5. 清理
n = delete_thought_chain(test_msg_id)
assert n == 3, f'deleted {n}'
print('5 cleanup OK')

# 6. 验证已删除
s, r = call('GET', f'/api/messages/{test_msg_id}/thoughts')
assert r['data']['total'] == 0
print('6 verify deleted OK')

print()
print('ALL 6 CHECKS PASSED')
