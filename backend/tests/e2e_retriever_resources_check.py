# -*- coding: utf-8 -*-
"""
E2E 测试：3.1 知识库引用追踪（retriever_resources）—— 确定性，无网络/模型依赖
验证:
    1. dataset_retriever_resources 表确保存在
    2. save_retriever_resources 落库 + 去重（同 message 二次保存不堆积）
    3. get_retriever_resources 按 position 升序回读，字段完整
    4. 空 message_id / 空列表 安全返回 0
    5. _build_retriever_resources 转换：score 归一化(/10 封顶 1.0)、content 截断 500、
       document_name 取 dataset_name、position 递增
    6. delete_retriever_resources 级联清理
"""
import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from config import get_db
from engine.retrieval_resources import (
    ensure_retriever_resources_table,
    save_retriever_resources,
    get_retriever_resources,
    delete_retriever_resources,
)
from routes.chat import _build_retriever_resources

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


print('\n=== 3.1 引用追踪 E2E 测试 ===\n')

MSG_ID = 'rr-e2e-' + str(uuid.uuid4())[:8]

# 1. 表确保存在
print('[1. 表确保]')
ensure_retriever_resources_table()
db = get_db()
try:
    cur = db.cursor()
    cur.execute("SHOW TABLES LIKE 'dataset_retriever_resources'")
    test('dataset_retriever_resources 表存在', cur.fetchone() is not None)
finally:
    db.close()

# 2. 保存 + 去重
print('\n[2. 保存与去重]')
resources = [
    {'segment_id': 'seg-1', 'dataset_id': 'ds-1', 'document_id': 'doc-1',
     'document_name': '产品手册', 'content': '段落一内容', 'score': 0.92, 'position': 0},
    {'segment_id': 'seg-2', 'dataset_id': 'ds-1', 'document_id': 'doc-2',
     'document_name': 'FAQ', 'content': '段落二内容', 'score': 0.61, 'position': 1},
    {'segment_id': 'seg-3', 'dataset_id': 'ds-2', 'document_id': 'doc-3',
     'document_name': '更新日志', 'content': '段落三内容', 'score': 0.35, 'position': 2},
]
n = save_retriever_resources(MSG_ID, resources)
test('保存 3 条引用', n == 3, f'n={n}')
# 二次保存同 message 不堆积（先删后插）
n2 = save_retriever_resources(MSG_ID, resources)
rows = get_retriever_resources(MSG_ID)
test('二次保存幂等不堆积', len(rows) == 3, f'count={len(rows)}')

# 3. 回读顺序与字段
print('\n[3. 回读顺序与字段]')
test('按 position 升序', [r['position'] for r in rows] == [0, 1, 2],
     f'positions={[r["position"] for r in rows]}')
first = rows[0]
test('字段完整回读',
     first['segment_id'] == 'seg-1' and first['document_name'] == '产品手册'
     and abs(first['score'] - 0.92) < 1e-6 and first['dataset_id'] == 'ds-1',
     f'first={first}')

# 4. 边界安全
print('\n[4. 边界安全]')
test('空 message_id 返回 0', save_retriever_resources('', resources) == 0)
test('空列表返回 0', save_retriever_resources(MSG_ID + '-empty', []) == 0)
test('无效 message 查询返回空', get_retriever_resources('not-exist-xx') == [])

# 5. _build_retriever_resources 转换
print('\n[5. 检索结果转换]')
long_content = 'X' * 800
scored = [
    (9.5, {'id': 's1', 'dataset_id': 'd1', 'document_id': 'c1',
           'dataset_name': '手册A', 'content': long_content}),
    (12.0, {'id': 's2', 'dataset_id': 'd1', 'document_id': 'c2',
            'dataset_name': '手册B', 'content': '短内容'}),
]
built = _build_retriever_resources(scored)
test('转换条数一致', len(built) == 2, f'len={len(built)}')
test('score 归一化 /10', abs(built[0]['score'] - 0.95) < 1e-6, f"score={built[0]['score']}")
test('score 封顶 1.0', built[1]['score'] == 1.0, f"score={built[1]['score']}")
test('content 截断 500', len(built[0]['content']) == 500, f"len={len(built[0]['content'])}")
test('document_name 取 dataset_name', built[0]['document_name'] == '手册A')
test('position 递增', built[0]['position'] == 0 and built[1]['position'] == 1)
test('segment_id 映射自 id', built[0]['segment_id'] == 's1')

# 6. 级联清理
print('\n[6. 级联清理]')
deleted = delete_retriever_resources(MSG_ID)
test('删除已有引用', deleted == 3, f'deleted={deleted}')
test('删除后查询为空', get_retriever_resources(MSG_ID) == [])
test('删除无记录返回 0', delete_retriever_resources('not-exist-xx') == 0)

# 最终清理（防止测试数据残留）
db = get_db()
try:
    cur = db.cursor()
    cur.execute('DELETE FROM dataset_retriever_resources WHERE message_id = %s', (MSG_ID,))
    cur.execute('DELETE FROM dataset_retriever_resources WHERE message_id = %s', (MSG_ID + '-empty',))
    db.commit()
finally:
    db.close()

print(f'\n=== 测试结果: {PASS} 通过, {FAIL} 失败 ===\n')
sys.exit(0 if FAIL == 0 else 1)
