# -*- coding: utf-8 -*-
"""任务 1.4 Service API 端到端验证（用后即焚，验证后可删除）"""
import json
import urllib.request
import urllib.error

KEY = 'app-6xAwfBF7GNYjqgHTTJjUrFbq'
BASE = 'http://localhost:5000'


def call(method, path, body=None, key=KEY):
    req = urllib.request.Request(BASE + path, method=method)
    if key:
        req.add_header('Authorization', 'Bearer ' + key)
    data = None
    if body is not None:
        data = json.dumps(body).encode('utf-8')
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, data) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))


# 1. 无 key 应 401
s, r = call('GET', '/v1/info', key=None)
assert s == 401, r
print('1 no-key 401: OK')

# 2. GET /v1/info
s, r = call('GET', '/v1/info')
assert s == 200 and 'name' in r['data'], r
print('2 info:', s, json.dumps(r['data'], ensure_ascii=False)[:150])

# 3. GET /v1/parameters
s, r = call('GET', '/v1/parameters')
d = r['data']
need = {'opening_statement', 'suggested_questions', 'suggested_questions_after_answer',
        'speech_to_text', 'text_to_speech', 'retriever_resource', 'annotation_reply',
        'user_input_form', 'file_upload', 'system_parameters'}
assert s == 200 and need.issubset(d.keys()), (s, d.keys())
print('3 parameters:', s, 'all Dify fields present; opening=', repr(d['opening_statement']))

# 4. POST chat-messages -> 落库
s, r = call('POST', '/v1/chat-messages',
            {'query': 'service-api 端到端测试', 'user': 'e2e-tester', 'response_mode': 'blocking'})
assert s == 200 and r['data']['conversation_id'], r
conv_id = r['data']['conversation_id']
print('4 chat:', s, 'conv=', conv_id[:8], 'msg=', (r['data']['message_id'] or '')[:8])

# 5. GET /v1/conversations?user=
s, r = call('GET', '/v1/conversations?user=e2e-tester')
assert s == 200 and conv_id in [c['id'] for c in r['data']['data']], r
print('5 conversations:', s, 'count=', len(r['data']['data']))

# 6. GET /v1/messages?conversation_id=
s, r = call('GET', '/v1/messages?conversation_id=%s&user=e2e-tester' % conv_id)
msgs = r['data']['data']
assert s == 200 and len(msgs) == 2, (s, len(msgs))
asst = [m for m in msgs if m['answer']]
user = [m for m in msgs if m['message']]
assert asst and user, msgs
assert user[0]['message'] == 'service-api 端到端测试'
print('6 messages:', s, 'user_msg + assistant_msg both present, feedback=', [m['feedback'] for m in msgs])
asst_id = asst[0]['id']

# 7. POST feedback like
s, r = call('POST', '/v1/messages/%s/feedbacks' % asst_id, {'rating': 'like', 'user': 'e2e-tester'})
assert s == 200 and r['data']['result'] == 'success', r
print('7 feedback like: OK')

# 8. messages 里 feedback 应显示 like
s, r = call('GET', '/v1/messages?conversation_id=%s' % conv_id)
fb = {m['id']: m['feedback'] for m in r['data']['data']}
assert fb[asst_id] == {'rating': 'like'}, fb
print('8 feedback echoed: OK')

# 9. rename conversation
s, r = call('POST', '/v1/conversations/%s/name' % conv_id,
            {'name': 'E2E测试会话', 'user': 'e2e-tester'})
assert s == 200 and r['data']['name'] == 'E2E测试会话', r
print('9 rename: OK ->', r['data']['name'])

# 10. delete conversation
s, r = call('DELETE', '/v1/conversations/%s?user=e2e-tester' % conv_id)
assert s == 200 and r['data']['result'] == 'success', r
print('10 delete: OK')

# 11. 删除后 conversations 应为空
s, r = call('GET', '/v1/conversations?user=e2e-tester')
assert s == 200 and conv_id not in [c['id'] for c in r['data']['data']], r
print('11 after delete: OK (hidden)')

# 12. messages 对软删会话应 404（本仓库约定：HTTP 200 + 信封 code）
s, r = call('GET', '/v1/messages?conversation_id=%s' % conv_id)
assert s == 200 and r.get('code') == 404, (s, r)
print('12 deleted conv messages 404: OK')

# 13. user 参数校验
s, r = call('GET', '/v1/conversations')
assert s == 200 and r.get('code') == 400, (s, r)
print('13 conversations without user 400: OK')

# 14. 无效 key 应 401
s, r = call('GET', '/v1/info', key='app-invalid-key')
assert s == 401, (s, r)
print('14 invalid key 401: OK')

print()
print('ALL 14 CHECKS PASSED')
