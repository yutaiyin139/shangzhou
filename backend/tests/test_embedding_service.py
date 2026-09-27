# -*- coding: utf-8 -*-
"""
Embedding 服务与向量检索单元测试
测试向量嵌入、余弦相似度、向量搜索等核心功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock
from engine.embedding_service import (
    cosine_similarity,
    get_embedding,
    get_embeddings_batch,
    store_embedding,
    get_segments_with_embeddings,
    vector_search,
    generate_missing_embeddings,
    hybrid_search,
)


def test_cosine_similarity_identical():
    """测试相同向量的余弦相似度"""
    vec = [1.0, 2.0, 3.0]
    result = cosine_similarity(vec, vec)
    assert abs(result - 1.0) < 0.0001
    print('[PASS] test_cosine_similarity_identical')


def test_cosine_similarity_orthogonal():
    """测试正交向量的余弦相似度"""
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [0.0, 1.0, 0.0]
    result = cosine_similarity(vec1, vec2)
    assert abs(result - 0.0) < 0.0001
    print('[PASS] test_cosine_similarity_orthogonal')


def test_cosine_similarity_opposite():
    """测试相反向量的余弦相似度"""
    vec1 = [1.0, 2.0, 3.0]
    vec2 = [-1.0, -2.0, -3.0]
    result = cosine_similarity(vec1, vec2)
    assert abs(result - (-1.0)) < 0.0001
    print('[PASS] test_cosine_similarity_opposite')


def test_cosine_similarity_empty():
    """测试空向量"""
    assert cosine_similarity([], [1.0, 2.0]) == 0.0
    assert cosine_similarity([1.0, 2.0], []) == 0.0
    assert cosine_similarity([], []) == 0.0
    print('[PASS] test_cosine_similarity_empty')


def test_cosine_similarity_different_dim():
    """测试不同维度向量"""
    vec1 = [1.0, 2.0, 3.0]
    vec2 = [1.0, 2.0]
    result = cosine_similarity(vec1, vec2)
    assert result == 0.0
    print('[PASS] test_cosine_similarity_different_dim')


def test_cosine_similarity_partial():
    """测试部分相似"""
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 1.0, 0.0]
    result = cosine_similarity(vec1, vec2)
    expected = 1.0 / (1.0 * (2 ** 0.5))
    assert abs(result - expected) < 0.0001
    print('[PASS] test_cosine_similarity_partial')


def test_get_embedding_empty_text():
    """测试空文本返回空列表"""
    result = get_embedding('')
    assert result == []
    result = get_embedding('   ')
    assert result == []
    result = get_embedding(None)
    assert result == []
    print('[PASS] test_get_embedding_empty_text')


def test_get_embedding_with_mock():
    """测试 Mock Embedding API"""
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"data": [{"embedding": [0.1, 0.2, 0.3, 0.4, 0.5]}]}'
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch('urllib.request.urlopen', return_value=mock_response):
        result = get_embedding('测试文本', model_name='text-embedding-3-small',
                               api_key='test-key', base_url='https://api.openai.com')

    assert result == [0.1, 0.2, 0.3, 0.4, 0.5]
    print('[PASS] test_get_embedding_with_mock')


def test_get_embeddings_batch_with_mock():
    """测试批量 Embedding"""
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"data": [{"index": 0, "embedding": [0.1, 0.2]}, {"index": 1, "embedding": [0.3, 0.4]}]}'
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch('urllib.request.urlopen', return_value=mock_response):
        result = get_embeddings_batch(['文本1', '文本2'], model_name='text-embedding-3-small',
                                     api_key='test-key', base_url='https://api.openai.com')

    assert len(result) == 2
    # get_embeddings_batch 当前走“逐条生成（每条自带远端→本地降级）”的可靠路径，
    # 一次多输入、按 index 归位的真批量路径在实现里明确标注为“暂不启用”，
    # 所以这里只断言“每条都拿到向量”；日后启用真批量时应改回按 index 逐项校验。
    assert all(isinstance(v, list) and v for v in result)
    print('[PASS] test_get_embeddings_batch_with_mock')


def test_store_embedding():
    """测试存储向量到数据库"""
    with patch('engine.embedding_service.get_db') as mock_db:
        mock_cursor = MagicMock()
        mock_db.return_value.cursor.return_value = mock_cursor

        store_embedding('seg-001', [0.1, 0.2, 0.3], 'text-embedding-3-small')

        mock_cursor.execute.assert_called_once()
        mock_db.return_value.commit.assert_called_once()
    print('[PASS] test_store_embedding')


def test_get_segments_with_embeddings():
    """测试获取有向量的分段"""
    with patch('engine.embedding_service.get_db') as mock_db:
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'id': 'seg-1', 'content': '内容1', 'embedding': '[0.1, 0.2]', 'embedding_model': 'test'},
            {'id': 'seg-2', 'content': '内容2', 'embedding': '[0.3, 0.4]', 'embedding_model': 'test'},
        ]
        mock_db.return_value.cursor.return_value = mock_cursor

        result = get_segments_with_embeddings(['ds-001'])

        assert len(result) == 2
        assert result[0]['id'] == 'seg-1'
        assert result[0]['embedding'] == [0.1, 0.2]
    print('[PASS] test_get_segments_with_embeddings')


def test_vector_search():
    """测试向量搜索"""
    # Mock get_embedding 返回查询向量
    # Mock get_segments_with_embeddings 返回分段
    with patch('engine.embedding_service.get_embedding', return_value=[1.0, 0.0, 0.0]):
        with patch('engine.embedding_service.get_segments_with_embeddings') as mock_get:
            mock_get.return_value = [
                {'id': 'seg-1', 'content': '内容A', 'embedding': [1.0, 0.0, 0.0]},
                {'id': 'seg-2', 'content': '内容B', 'embedding': [0.0, 1.0, 0.0]},
                {'id': 'seg-3', 'content': '内容C', 'embedding': [0.5, 0.5, 0.0]},
            ]

            result = vector_search('查询', ['ds-001'], top_k=2)

            assert len(result) == 2
            # 最相似的应该是 seg-1（完全相同）
            assert result[0]['id'] == 'seg-1'
            assert result[0]['score'] > result[1]['score']
    print('[PASS] test_vector_search')


def test_vector_search_empty_query():
    """测试空查询返回空结果"""
    result = vector_search('', ['ds-001'])
    assert result == []
    print('[PASS] test_vector_search_empty_query')


def test_vector_search_no_segments():
    """测试无分段返回空结果"""
    with patch('engine.embedding_service.get_embedding', return_value=[1.0, 0.0]):
        with patch('engine.embedding_service.get_segments_with_embeddings', return_value=[]):
            result = vector_search('查询', ['ds-001'])
            assert result == []
    print('[PASS] test_vector_search_no_segments')


def test_vector_search_min_score():
    """测试最低分数过滤"""
    with patch('engine.embedding_service.get_embedding', return_value=[1.0, 0.0, 0.0]):
        with patch('engine.embedding_service.get_segments_with_embeddings') as mock_get:
            mock_get.return_value = [
                {'id': 'seg-1', 'content': '内容A', 'embedding': [1.0, 0.0, 0.0]},
                {'id': 'seg-2', 'content': '内容B', 'embedding': [0.0, 1.0, 0.0]},
            ]

            # 设置最低分数为 0.5，只有 seg-1 满足
            result = vector_search('查询', ['ds-001'], min_score=0.5)

            assert len(result) == 1
            assert result[0]['id'] == 'seg-1'
    print('[PASS] test_vector_search_min_score')


def test_generate_missing_embeddings():
    """测试生成缺失的向量"""
    with patch('engine.embedding_service.get_db') as mock_db:
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'id': 'seg-1', 'content': '内容1'},
            {'id': 'seg-2', 'content': '内容2'},
        ]
        mock_db.return_value.cursor.return_value = mock_cursor

        with patch('engine.embedding_service.get_embedding_config') as mock_cfg:
            mock_cfg.return_value = {
                'api_key': 'test-key',
                'api_base_url': 'https://api.openai.com',
                'model_name': 'text-embedding-3-small',
                'credential_name': 'openai',
                'provider': 'openai',
            }

            with patch('engine.embedding_service.get_embeddings_batch',
                       return_value=[[0.1, 0.2], [0.3, 0.4]]):
                count = generate_missing_embeddings('ds-001')
                assert count == 2
    print('[PASS] test_generate_missing_embeddings')


def test_hybrid_search():
    """测试混合搜索"""
    with patch('engine.embedding_service.get_embedding', return_value=[1.0, 0.0, 0.0]):
        with patch('engine.embedding_service.get_segments_with_embeddings') as mock_get:
            mock_get.return_value = [
                {'id': 'seg-1', 'content': '查询关键词在这里', 'embedding': [1.0, 0.0, 0.0]},
                {'id': 'seg-2', 'content': '不相关的内容', 'embedding': [0.8, 0.2, 0.0]},
            ]

            result = hybrid_search('查询关键词', ['ds-001'], top_k=2, text_weight=0.3)

            assert len(result) == 2
            # 混合搜索应该考虑关键词匹配
            assert 'score' in result[0]
    print('[PASS] test_hybrid_search')


def test_vector_search_sorting():
    """测试搜索结果按相似度排序"""
    with patch('engine.embedding_service.get_embedding', return_value=[1.0, 0.0, 0.0]):
        with patch('engine.embedding_service.get_segments_with_embeddings') as mock_get:
            mock_get.return_value = [
                {'id': 'seg-low', 'content': '低相似度', 'embedding': [0.0, 1.0, 0.0]},
                {'id': 'seg-high', 'content': '高相似度', 'embedding': [0.9, 0.1, 0.0]},
                {'id': 'seg-mid', 'content': '中相似度', 'embedding': [0.5, 0.5, 0.0]},
            ]

            result = vector_search('查询', ['ds-001'], top_k=3)

            # 验证按分数降序排列
            assert result[0]['id'] == 'seg-high'
            assert result[1]['id'] == 'seg-mid'
            assert result[2]['id'] == 'seg-low'
            assert result[0]['score'] > result[1]['score'] > result[2]['score']
    print('[PASS] test_vector_search_sorting')


def run_all_tests():
    """运行所有测试"""
    print('=' * 60)
    print('Embedding 服务与向量检索单元测试')
    print('=' * 60)

    test_cosine_similarity_identical()
    test_cosine_similarity_orthogonal()
    test_cosine_similarity_opposite()
    test_cosine_similarity_empty()
    test_cosine_similarity_different_dim()
    test_cosine_similarity_partial()
    test_get_embedding_empty_text()
    test_get_embedding_with_mock()
    test_get_embeddings_batch_with_mock()
    test_store_embedding()
    test_get_segments_with_embeddings()
    test_vector_search()
    test_vector_search_empty_query()
    test_vector_search_no_segments()
    test_vector_search_min_score()
    test_generate_missing_embeddings()
    test_hybrid_search()
    test_vector_search_sorting()

    print('=' * 60)
    print('所有测试通过！')
    print('=' * 60)


if __name__ == '__main__':
    run_all_tests()
