# -*- coding: utf-8 -*-
"""
E2E 测试：关键词表混合检索（3.2）
验证:
    1. 关键词表创建
    2. 分词功能（jieba 或回退）
    3. 单分段索引构建
    4. 数据集批量索引构建
    5. 关键词检索
    6. 混合检索
    7. API 端点
"""
import json
import sys
import os
import time
import urllib.request
import urllib.parse

# 确保 backend 目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Windows 编码修复
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = 'http://127.0.0.1:5000'
PASS = 0
FAIL = 0

# /api/knowledge/* 受 @login_required 保护，需携带 Bearer Token
import e2e_auth_helper  # noqa: E402
AUTH_HEADER = e2e_auth_helper.get_auth_header(verbose=True)


def api(method, path, body=None):
    """调用 API"""
    url = BASE_URL + path
    data = json.dumps(body).encode('utf-8') if body else None
    headers = {'Content-Type': 'application/json', **AUTH_HEADER}
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
        print(f'  ✓ {name}')
    else:
        FAIL += 1
        print(f'  ✗ {name} {detail}')


def setup_test_dataset():
    """创建测试知识库和分段"""
    # 创建知识库
    resp = api('POST', '/api/knowledge/datasets', {'name': '关键词测试库', 'description': '测试'})
    if resp.get('code') != 200:
        return None, None
    dataset_id = resp['data']['id']

    # 创建文档（通过上传）
    # 直接插入分段
    from config import get_db
    db = get_db()
    try:
        cur = db.cursor()
        # 获取租户
        cur.execute('SELECT id FROM dify_tenants LIMIT 1')
        tenant_row = cur.fetchone()
        tenant_id = tenant_row['id'] if tenant_row else 'test-tenant'

        # 创建文档
        import uuid
        doc_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO dify_documents (id, tenant_id, dataset_id, position, data_source_type, data_source_info,
                                       batch, name, created_from, created_by, indexing_status, word_count)
            VALUES (%s, %s, %s, 0, 'upload_file', %s, %s, %s, 'api', NULL, 'completed', 100)
        """, (doc_id, tenant_id, dataset_id, '{}', 'test', '测试文档'))

        # 创建分段（含中文内容）
        segments = [
            '人工智能（Artificial Intelligence）是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。',
            '机器学习是人工智能的核心研究领域之一。机器学习是一门多领域交叉学科，涉及概率论、统计学、逼近论、凸分析、算法复杂度理论等多门学科。',
            '深度学习是机器学习的一种，而机器学习是人工智能的一个子集。深度学习通过模拟人脑的神经网络结构来实现对数据的学习和理解。',
            '自然语言处理（NLP）是人工智能和语言学领域的分支学科。它研究能实现人与计算机之间用自然语言进行有效通信的各种理论和方法。',
            '知识图谱是一种结构化的语义知识库，用于以符号形式描述物理世界中的概念及其相互关系。它是搜索引擎、问答系统、推荐系统的重要基础。',
        ]
        seg_ids = []
        for idx, content in enumerate(segments):
            seg_id = str(uuid.uuid4())
            wc = len(content.replace('\n', '').replace(' ', ''))
            tokens = max(1, int(len(content) / 3))
            cur.execute("""
                INSERT INTO dify_document_segments (id, tenant_id, dataset_id, document_id, position, content,
                                                   word_count, tokens, hit_count, status, created_by,
                                                   segment_type, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, 'completed', NULL, 'general', '')
            """, (seg_id, tenant_id, dataset_id, doc_id, idx, content, wc, tokens))
            seg_ids.append(seg_id)

        db.commit()
        return dataset_id, seg_ids
    finally:
        db.close()


print('\n=== 3.2 关键词表混合检索 E2E 测试 ===\n')

# 准备测试数据
print('[准备测试数据]')
dataset_id, seg_ids = setup_test_dataset()
test('创建测试知识库和分段', dataset_id is not None and len(seg_ids) == 5)

if not dataset_id:
    print('\n无法创建测试数据，跳过后续测试')
else:
    # 测试 1: 关键词表创建
    print('\n[1. 关键词表]')
    from engine.keyword_engine import ensure_keyword_table, JIEBA_AVAILABLE
    ensure_keyword_table()
    test('ensure_keyword_table 执行成功', True)
    test(f'jieba 可用: {JIEBA_AVAILABLE}', True)

    # 测试 2: 分词功能
    print('\n[2. 分词功能]')
    from engine.keyword_engine import _tokenize, _extract_keywords
    tokens = _tokenize('人工智能和机器学习是当今科技领域的热门话题')
    test('中文分词返回结果', len(tokens) > 0, f'tokens={tokens}')
    test('分词包含关键词', '人工智能' in tokens or '机器' in tokens, f'tokens={tokens}')

    keywords = _extract_keywords('深度学习是机器学习的一种，而机器学习是人工智能的一个子集。')
    test('关键词提取返回结果', len(keywords) > 0, f'keywords={keywords}')

    # 测试 3: 单分段索引
    print('\n[3. 单分段索引构建]')
    from engine.keyword_engine import build_keyword_index_for_segment
    count = build_keyword_index_for_segment(dataset_id, seg_ids[0], '人工智能是计算机科学的一个分支')
    test('单分段索引构建成功', count > 0, f'count={count}')

    # 测试 4: 数据集批量索引
    print('\n[4. 数据集批量索引构建]')
    from engine.keyword_engine import build_keyword_index_for_dataset, get_keyword_stats
    n = build_keyword_index_for_dataset(dataset_id)
    test('批量索引构建成功', n > 0, f'indexed={n}')

    stats = get_keyword_stats(dataset_id)
    test('关键词统计返回结果', stats['keyword_count'] > 0, f'stats={stats}')
    test('索引分段数正确', stats['indexed_segments'] == 5, f'stats={stats}')

    # 测试 5: 关键词检索
    print('\n[5. 关键词检索]')
    from engine.keyword_engine import keyword_search
    results = keyword_search(dataset_id, '人工智能', top_k=3)
    test('关键词检索返回结果', len(results) > 0, f'results={len(results)}')
    if results:
        test('检索结果包含 segment_id', 'segment_id' in results[0])
        test('检索结果包含 score', 'score' in results[0] and results[0]['score'] > 0)
        test('检索结果包含 matched_keywords', 'matched_keywords' in results[0])

    results_ml = keyword_search(dataset_id, '机器学习', top_k=3)
    test('机器学习关键词检索返回结果', len(results_ml) > 0)

    # 测试 6: 混合检索
    print('\n[6. 混合检索]')
    from engine.keyword_engine import hybrid_search
    # 模拟向量结果
    mock_vec_results = [
        {'id': seg_ids[0], 'content': '人工智能内容', 'score': 0.95, 'dataset_id': dataset_id, 'document_id': ''},
        {'id': seg_ids[1], 'content': '机器学习内容', 'score': 0.85, 'dataset_id': dataset_id, 'document_id': ''},
    ]
    merged = hybrid_search(dataset_id, '人工智能', mock_vec_results, top_k=5, vector_weight=0.7)
    test('混合检索返回结果', len(merged) > 0, f'merged={len(merged)}')
    if merged:
        test('混合结果包含 hybrid_score', 'hybrid_score' in merged[0])
        test('混合结果包含 vector_score', 'vector_score' in merged[0])
        test('混合结果包含 keyword_score', 'keyword_score' in merged[0])

    # 测试 7: API 端点
    print('\n[7. API 端点]')
    resp = api('GET', f'/api/knowledge/datasets/{dataset_id}/keyword-index')
    test('GET keyword-index 统计', resp.get('code') == 200, f'resp={resp}')
    if resp.get('code') == 200:
        test('统计包含 keyword_count', resp['data'].get('keyword_count', 0) > 0)

    resp = api('POST', f'/api/knowledge/datasets/{dataset_id}/keyword-search', {
        'query': '深度学习',
        'top_k': 3,
    })
    test('POST keyword-search', resp.get('code') == 200, f'resp={resp}')
    if resp.get('code') == 200:
        test('关键词检索结果非空', len(resp['data'].get('results', [])) > 0)

    resp = api('POST', f'/api/knowledge/datasets/{dataset_id}/hybrid-search', {
        'query': '自然语言处理',
        'top_k': 3,
        'vector_weight': 0.7,
    })
    test('POST hybrid-search', resp.get('code') == 200, f'resp={resp}')

    # 测试 8: 知识库详情包含关键词统计
    print('\n[8. 知识库详情]')
    resp = api('GET', f'/api/knowledge/datasets/{dataset_id}')
    test('知识库详情返回关键词统计', resp.get('code') == 200 and resp['data'].get('keyword_count', 0) > 0)

    # 测试 9: 分段删除时级联删除关键词索引
    print('\n[9. 级联删除]')
    # 先记录当前关键词数
    stats_before = get_keyword_stats(dataset_id)
    # 删除一个分段
    resp = api('DELETE', f'/api/knowledge/segments/{seg_ids[4]}')
    test('删除分段成功', resp.get('code') == 200)
    stats_after = get_keyword_stats(dataset_id)
    test('删除后关键词索引减少', stats_after['indexed_segments'] < stats_before['indexed_segments'])

    # 清理：删除测试知识库
    print('\n[清理测试数据]')
    resp = api('DELETE', f'/api/knowledge/datasets/{dataset_id}')
    test('删除测试知识库', resp.get('code') == 200)

print(f'\n=== 测试结果: {PASS} 通过, {FAIL} 失败 ===\n')
sys.exit(0 if FAIL == 0 else 1)
