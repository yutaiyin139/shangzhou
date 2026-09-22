# -*- coding: utf-8 -*-
"""阶段 2.1 Agent 记忆向量化 端到端验证（用后即焚）"""
import json
import urllib.request
import urllib.error
import urllib.parse
import time

BASE = 'http://localhost:5000'
AID = 15  # 现有 agent


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


# 1. 清空该 agent 记忆（隔离测试）
s, r = call('DELETE', f'/api/agents/{AID}/memories')
print('1 cleanup:', s, 'deleted=', r.get('data', {}).get('deleted', 0))

# 2. 写入 3 条记忆
contents = [
    '张三是一名高级后端工程师，擅长 Python 和分布式系统，主导过日活千万的推荐系统重构。',
    '李四是产品经理，负责 AI 平台条线，重点关注 Agent 与 RAG 场景落地。',
    '公司每周三下午有技术分享会，地点在 3 号楼报告厅，全员可参加。',
]
ids = []
for c in contents:
    s, r = call('POST', f'/api/agents/{AID}/memories', {'content': c})
    assert s == 200 and r['data'].get('id'), r
    ids.append(r['data']['id'])
print('2 add 3 memories:', ids, 'status=', r['data']['embedding_status'])

# 3. 列表
s, r = call('GET', f'/api/agents/{AID}/memories')
assert s == 200 and r['data']['total'] == 3, r
print('3 list total=3 OK')

# 4. 等待向量化（同步路径，几秒内完成）
for _ in range(20):
    s, r = call('GET', f'/api/agents/{AID}/memories?status=completed')
    if r['data']['total'] >= 3:
        break
    time.sleep(1)
print('4 embedding completed:', r['data']['total'])

# 5. 语义检索 —— "后端工程师" 应命中张三
q = urllib.parse.quote('后端工程师')
s, r = call('GET', f'/api/agents/{AID}/memories/search?q={q}&limit=3')
print('5 search 后端工程师:', 'hits=', len(r['data']['items']))
for h in r['data']['items']:
    print('   ', h['id'], 'score=', h['score'], h['content'][:25])
# 验证张三排第一
assert len(r['data']['items']) >= 1, '无检索结果'
assert '张三' in r['data']['items'][0]['content'], f"张三应排第一: {r['data']['items'][0]['content']}"
print('   -> 张三排第一 OK')

# 6. 语义检索 —— "产品" 应命中李四
q2 = urllib.parse.quote('产品经理')
s, r = call('GET', f'/api/agents/{AID}/memories/search?q={q2}&limit=3')
assert any('李四' in h['content'] for h in r['data']['items']), [h['content'] for h in r['data']['items']]
print('6 search 产品经理 -> 命中李四 OK')

# 7. context 拼接
q3 = urllib.parse.quote('技术分享')
s, r = call('GET', f'/api/agents/{AID}/memories/context?q={q3}')
print('7 context:', r['data']['context'][:200])
assert '技术分享会' in r['data']['context'], r['data']['context']
print('   -> 包含技术分享会 OK')

# 8. 空 content 校验
s, r = call('POST', f'/api/agents/{AID}/memories', {'content': '   '})
assert s == 200 and r.get('code') == 400, r
print('8 empty rejected OK')

# 9. 更新记忆
s, r = call('PUT', f'/api/agents/{AID}/memories/{ids[0]}', {'content': '张三已离职，现为独立技术顾问。'})
assert r['code'] == 200, r
print('9 update OK')

# 10. 删除单条
s, r = call('DELETE', f'/api/agents/{AID}/memories/{ids[0]}')
assert r['code'] == 200, r
s, r = call('GET', f'/api/agents/{AID}/memories')
assert r['data']['total'] == 2, r['data']
print('10 delete one OK -> total=2')

# 11. 清空
s, r = call('DELETE', f'/api/agents/{AID}/memories')
assert r['code'] == 200, r
s, r = call('GET', f'/api/agents/{AID}/memories')
assert r['data']['total'] == 0, r['data']
print('11 clear all OK -> total=0')

print()
print('ALL 11 CHECKS PASSED')
