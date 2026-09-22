# -*- coding: utf-8 -*-
"""任务 2.3 知识库元数据系统 端到端验证（用后即焚）"""
import json
import urllib.request
import urllib.error
import uuid

BASE = 'http://localhost:5000'

# /api/knowledge/* 受 @login_required 保护，需携带 Bearer Token
import e2e_auth_helper  # noqa: E402
AUTH_HEADER = e2e_auth_helper.get_auth_header(verbose=True)


def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method)
    data = None
    headers = dict(AUTH_HEADER)
    if body is not None:
        data = json.dumps(body).encode()
        headers['Content-Type'] = 'application/json'
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, data) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


assert AUTH_HEADER, '无法取得认证令牌，后续受保护接口不可用'

# 使用已有数据集（优先使用有分段的）
s, r = call('GET', '/api/knowledge/datasets')
assert s == 200 and r['data'], f'No datasets found (HTTP {s}: {str(r)[:200]})'
# 找有文档的数据集
DS = None
for d in r['data']:
    if d['doc_count'] > 0:
        DS = d['id']
        break
if not DS:
    DS = r['data'][0]['id']
print(f'Using dataset: {DS}')

# 1. 创建元数据字段：部门
s, r = call('POST', f'/api/knowledge/datasets/{DS}/metadata-fields',
            {'name': '部门', 'type': 'string', 'description': '所属部门'})
assert s == 200 and r['data'].get('id'), r
dept_field = r['data']
print(f'1 created field: {dept_field["name"]} ({dept_field["id"][:8]})')

# 2. 创建元数据字段：年份
s, r = call('POST', f'/api/knowledge/datasets/{DS}/metadata-fields',
            {'name': '年份', 'type': 'number', 'description': '文档年份'})
assert s == 200 and r['data'].get('id'), r
year_field = r['data']
print(f'2 created field: {year_field["name"]} ({year_field["id"][:8]})')

# 3. 列出字段
s, r = call('GET', f'/api/knowledge/datasets/{DS}/metadata-fields')
assert s == 200 and len(r['data']) >= 2, r
print(f'3 list fields: {len(r["data"])} fields')

# 4. 获取数据集的 segments（通过文档）
s, r = call('GET', f'/api/knowledge/datasets/{DS}')
doc_id = None
if r.get('data') and r['data'].get('documents'):
    doc_id = r['data']['documents'][0]['id']
segments = []
if doc_id:
    s, r = call('GET', f'/api/knowledge/datasets/{DS}/documents/{doc_id}/segments')
    if s == 200 and r.get('data'):
        d = r['data']
        if isinstance(d, dict):
            segments = d.get('items', d.get('segments', []))
        elif isinstance(d, list):
            segments = d
print(f'4 found {len(segments)} segments')

if not segments:
    print('4 SKIP: dataset has no segments, testing field CRUD only')
    call('DELETE', f'/api/knowledge/datasets/{DS}/metadata-fields/{dept_field["id"]}')
    call('DELETE', f'/api/knowledge/datasets/{DS}/metadata-fields/{year_field["id"]}')
    print()
    print('FIELD CRUD TESTS PASSED (segment binding skipped - no segments)')
    exit(0)

# 5. 绑定第一条 segment 的部门=法务
seg1 = segments[0]
s, r = call('POST', f'/api/knowledge/datasets/{DS}/metadata-bindings',
            {'metadata_id': dept_field['id'], 'segment_id': seg1['id'], 'value': '法务'})
assert s == 200 and r['data'].get('id'), r
print(f'5 bound seg1 部门=法务')

# 6. 绑定第一条 segment 的年份=2024
s, r = call('POST', f'/api/knowledge/datasets/{DS}/metadata-bindings',
            {'metadata_id': year_field['id'], 'segment_id': seg1['id'], 'value': '2024'})
assert s == 200 and r['data'].get('id'), r
print(f'6 bound seg1 年份=2024')

# 7. 如果有第二条 segment，绑定不同的部门
if len(segments) > 1:
    seg2 = segments[1]
    s, r = call('POST', f'/api/knowledge/datasets/{DS}/metadata-bindings',
                {'metadata_id': dept_field['id'], 'segment_id': seg2['id'], 'value': '技术'})
    assert s == 200, r
    print(f'7 bound seg2 部门=技术')

# 8. 获取 segment 元数据
s, r = call('GET', f'/api/knowledge/segments/{seg1["id"]}/metadata')
assert s == 200 and r['data'].get('部门') == '法务', r
assert r['data'].get('年份') == '2024', r
print(f'8 get seg1 metadata: {r["data"]}')

# 9. 批量更新 segment 元数据
s, r = call('PUT', f'/api/knowledge/datasets/{DS}/segments/{seg1["id"]}/metadata',
            {'metadata': {'部门': '法务部', '年份': '2025'}})
assert s == 200, r
s, r = call('GET', f'/api/knowledge/segments/{seg1["id"]}/metadata')
assert r['data'].get('部门') == '法务部', r
assert r['data'].get('年份') == '2025', r
print(f'9 batch update metadata OK: {r["data"]}')

# 10. 验证 dify_document_segments.metadata JSON 同步
import sys
sys.path.insert(0, '.')
from config import get_db
db = get_db()
cur = db.cursor()
cur.execute('SELECT metadata FROM dify_document_segments WHERE id = %s', (seg1['id'],))
row = cur.fetchone()
db.close()
seg_meta = json.loads(row['metadata']) if row and row['metadata'] else {}
assert seg_meta.get('部门') == '法务部', f'JSON sync failed: {seg_meta}'
print(f'10 JSON sync OK: {seg_meta}')

# 11. 召回测试（带元数据过滤）
s, r = call('POST', '/api/knowledge/recall-test', {
    'dataset_id': DS,
    'query': '测试',
    'top_k': 10,
    'metadata_filters': [{'name': '部门', 'value': '法务部', 'operator': 'eq'}]
})
assert s == 200, r
filtered_results = r['data']['results']
print(f'11 recall with filter 部门=法务部: {len(filtered_results)} results')
for res in filtered_results:
    meta = json.loads(res.get('metadata', '{}')) if res.get('metadata') else {}
    assert meta.get('部门') == '法务部', f'Filter failed: {meta}'

# 12. 召回测试（无过滤 = 返回更多）
s, r = call('POST', '/api/knowledge/recall-test', {
    'dataset_id': DS,
    'query': '测试',
    'top_k': 100,
})
assert s == 200, r
unfiltered_count = len(r['data']['results'])
print(f'12 recall without filter: {unfiltered_count} results')
assert unfiltered_count >= len(filtered_results), 'Filtered should be <= unfiltered'

# 13. 解绑
s, r = call('DELETE', f'/api/knowledge/datasets/{DS}/metadata-bindings',
            {'metadata_id': year_field['id'], 'segment_id': seg1['id']})
assert s == 200, r
s, r = call('GET', f'/api/knowledge/segments/{seg1["id"]}/metadata')
assert '年份' not in r['data'], r
print(f'13 unbind year OK')

# 14. 删除字段（级联删除绑定）
s, r = call('DELETE', f'/api/knowledge/datasets/{DS}/metadata-fields/{dept_field["id"]}')
assert s == 200, r
s, r = call('GET', f'/api/knowledge/segments/{seg1["id"]}/metadata')
assert '部门' not in r['data'], f'Cascade delete failed: {r["data"]}'
print(f'14 cascade delete OK')

# 15. 清理剩余字段
s, r = call('DELETE', f'/api/knowledge/datasets/{DS}/metadata-fields/{year_field["id"]}')
assert s == 200, r
print(f'15 cleanup OK')

print()
print('ALL 15 CHECKS PASSED')
