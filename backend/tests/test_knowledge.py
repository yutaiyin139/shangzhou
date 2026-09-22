# -*- coding: utf-8 -*-
"""
知识库模块单元测试
测试分段引擎、文档结构提取、父子分段、Q&A分段、Rerank 等功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock
from routes.knowledge import (
    _segment_text,
    _extract_document_structure,
    _get_segment_structure,
    _segment_parent_child,
    _extract_json_list,
    _calc_keyword_score,
)
from utils.rerank import rerank_segments, _sort_by_score


def test_chinese_segmentation():
    """测试中文分段"""
    text = "这是一段测试文本。" * 100
    segments = _segment_text(text, max_length=256)
    assert len(segments) > 1, f"Expected multiple segments, got {len(segments)}"
    # 允许 overlap
    assert all(len(s) <= 256 + 50 for s in segments), "Segment exceeds max_length + overlap"
    print('[PASS] test_chinese_segmentation')


def test_chinese_segmentation_short_text():
    """测试短文本不分段"""
    text = "短文本"
    segments = _segment_text(text, max_length=256)
    assert len(segments) == 1
    assert segments[0] == text
    print('[PASS] test_chinese_segmentation_short_text')


def test_chinese_segmentation_empty():
    """测试空文本返回空列表"""
    assert _segment_text('', max_length=256) == []
    assert _segment_text('   ', max_length=256) == []
    assert _segment_text(None or '', max_length=256) == []
    print('[PASS] test_chinese_segmentation_empty')


def test_western_segmentation():
    """测试英文分段"""
    text = "This is a test sentence. " * 50
    segments = _segment_text(text, max_length=256)
    assert len(segments) > 1
    print('[PASS] test_western_segmentation')


def test_segmentation_with_overlap():
    """测试重叠分段"""
    text = "第一段内容。第二段内容。第三段内容。" * 20
    segments_no_overlap = _segment_text(text, max_length=100, overlap=0)
    segments_with_overlap = _segment_text(text, max_length=100, overlap=20)
    # 有重叠的分段应该比无重叠的多或相等
    assert len(segments_with_overlap) >= len(segments_no_overlap)
    print('[PASS] test_segmentation_with_overlap')


def test_segmentation_clean_rules():
    """测试清洗规则"""
    text = "文本   https://example.com   内容"
    clean_rules = {'remove_urls': True, 'remove_extra_spaces': True}
    segments = _segment_text(text, max_length=256, clean_rules=clean_rules)
    assert len(segments) >= 1
    # URL 应该被移除
    assert 'https://example.com' not in segments[0]
    print('[PASS] test_segmentation_clean_rules')


def test_parent_child_segmentation():
    """测试父子分段"""
    text = "第一章\n" + "这是第一章的内容。" * 50 + "\n\n第二章\n" + "这是第二章的内容。" * 50
    segments = _segment_parent_child(text, child_max=100, parent_max=300, overlap=20)

    children = [s for s in segments if s.get('segment_type') == 'child']
    parents = [s for s in segments if s.get('segment_type') == 'parent']

    assert len(parents) > 0, "Should have parent segments"
    assert len(children) >= len(parents), "Should have at least one child per parent"

    # 验证子段落有 parent_id 指向父段落
    for child in children:
        assert child.get('parent_id') is not None
        # 验证 parent_id 指向一个存在的父段落
        parent_ids = [p['id'] for p in parents]
        assert child['parent_id'] in parent_ids
    print('[PASS] test_parent_child_segmentation')


def test_parent_child_short_text():
    """测试短文本父子分段"""
    text = "短文本内容"
    segments = _segment_parent_child(text, child_max=100, parent_max=300)
    assert len(segments) >= 1
    # 短文本应该只有一个父段落和一个子段落
    parents = [s for s in segments if s.get('segment_type') == 'parent']
    children = [s for s in segments if s.get('segment_type') == 'child']
    assert len(parents) == 1
    assert len(children) == 1
    print('[PASS] test_parent_child_short_text')


def test_document_structure_extraction():
    """测试文档结构提取"""
    text = "# 标题一\n内容一\n## 子标题\n内容二\n### 子子标题\n内容三\n# 标题二\n内容四"
    structure = _extract_document_structure(text)

    assert len(structure) == 4, f"Expected 4 headers, got {len(structure)}"
    assert structure[0]['level'] == 1
    assert structure[0]['title'] == '标题一'
    assert structure[1]['level'] == 2
    assert structure[1]['title'] == '子标题'
    assert structure[1]['path'] == '标题一 > 子标题'
    assert structure[2]['level'] == 3
    assert structure[2]['path'] == '标题一 > 子标题 > 子子标题'
    print('[PASS] test_document_structure_extraction')


def test_document_structure_empty():
    """测试无标题文档"""
    text = "这是一段没有标题的纯文本内容。"
    structure = _extract_document_structure(text)
    assert len(structure) == 0
    print('[PASS] test_document_structure_empty')


def test_get_segment_structure():
    """测试分段结构路径获取"""
    text = "# 第一章\n第一章内容\n## 1.1 节\n节内容"
    structure = _extract_document_structure(text)

    # 找到 "节内容" 的位置
    seg_start = text.find('节内容')
    seg_end = seg_start + len('节内容')
    path = _get_segment_structure(text, seg_start, seg_end, structure)

    assert path == '第一章 > 1.1 节', f"Expected '第一章 > 1.1 节', got '{path}'"
    print('[PASS] test_get_segment_structure')


def test_extract_json_list():
    """测试 JSON 列表提取"""
    # 直接 JSON
    result = _extract_json_list('[{"question": "Q1", "answer": "A1"}]')
    assert len(result) == 1
    assert result[0]['question'] == 'Q1'

    # 带额外文本
    result = _extract_json_list('以下是问答对：\n[{"question": "Q1", "answer": "A1"}]\n结束')
    assert len(result) == 1

    # 无效 JSON
    result = _extract_json_list('不是 JSON')
    assert result == []
    print('[PASS] test_extract_json_list')


def test_calc_keyword_score():
    """测试关键词匹配分数"""
    # 完全匹配
    score = _calc_keyword_score('测试', '这是一段测试文本')
    assert score == 1.0, f"Expected 1.0, got {score}"

    # 部分匹配
    score = _calc_keyword_score('测试功能', '这是一段测试文本')
    assert 0 < score < 1.0

    # 不匹配
    score = _calc_keyword_score('不存在', '这是一段测试文本')
    assert score == 0.0

    # 空输入
    assert _calc_keyword_score('', '内容') == 0.0
    assert _calc_keyword_score('查询', '') == 0.0
    print('[PASS] test_calc_keyword_score')


def test_calc_keyword_score_english():
    """测试英文关键词匹配"""
    score = _calc_keyword_score('test function', 'This is a test function')
    assert score > 0
    print('[PASS] test_calc_keyword_score_english')


def test_rerank_fallback():
    """测试 Rerank 无模型时回退到原始排序"""
    segments = [
        {'content': '结果A'},
        {'content': '结果B'},
        {'content': '结果C'},
    ]
    result = rerank_segments('查询', segments)
    assert len(result) == 3
    # 无模型时应该保持原始顺序
    assert result[0]['content'] == '结果A'
    print('[PASS] test_rerank_fallback')


def test_rerank_fallback_with_top_k():
    """测试 Rerank top_k 截断"""
    segments = [
        {'content': '结果A'},
        {'content': '结果B'},
        {'content': '结果C'},
    ]
    result = rerank_segments('查询', segments, top_k=2)
    assert len(result) == 2
    print('[PASS] test_rerank_fallback_with_top_k')


def test_rerank_empty_segments():
    """测试 Rerank 空分段"""
    result = rerank_segments('查询', [])
    assert result == []
    print('[PASS] test_rerank_empty_segments')


def test_sort_by_score():
    """测试按分数排序"""
    segments = [
        {'content': '低分'},
        {'content': '高分'},
        {'content': '中分'},
    ]
    scores = [0.3, 0.9, 0.6]
    result = _sort_by_score(segments, scores)

    assert result[0]['content'] == '高分'
    assert result[1]['content'] == '中分'
    assert result[2]['content'] == '低分'
    assert 'rerank_score' in result[0]
    print('[PASS] test_sort_by_score')


def test_sort_by_score_with_top_k():
    """测试按分数排序并截断"""
    segments = [{'content': f'结果{i}'} for i in range(5)]
    scores = [0.1, 0.5, 0.9, 0.3, 0.7]
    result = _sort_by_score(segments, scores, top_k=3)

    assert len(result) == 3
    assert result[0]['content'] == '结果2'  # 分数 0.9
    assert result[1]['content'] == '结果4'  # 分数 0.7
    assert result[2]['content'] == '结果1'  # 分数 0.5
    print('[PASS] test_sort_by_score_with_top_k')


def test_sort_by_score_mismatched_length():
    """测试分数和分段数量不匹配"""
    segments = [{'content': 'A'}, {'content': 'B'}]
    scores = [0.5]  # 数量不匹配
    result = _sort_by_score(segments, scores)
    # 不匹配时返回原始分段
    assert len(result) == 2
    print('[PASS] test_sort_by_score_mismatched_length')


def test_rerank_with_mock_embedding():
    """测试使用 Mock Embedding 进行 Rerank"""
    with patch('utils.rerank._rerank_local', return_value=None):
        with patch('utils.rerank._rerank_api', return_value=None):
            with patch('utils.rerank._rerank_embedding', return_value=[0.9, 0.3, 0.6]):
                segments = [
                    {'content': '结果A'},
                    {'content': '结果B'},
                    {'content': '结果C'},
                ]
                result = rerank_segments('查询', segments)

                assert len(result) == 3
                # 应该按 embedding 分数排序：A(0.9) > C(0.6) > B(0.3)
                assert result[0]['content'] == '结果A'
                assert result[1]['content'] == '结果C'
                assert result[2]['content'] == '结果B'
    print('[PASS] test_rerank_with_mock_embedding')


def test_segment_metadata():
    """测试分段元数据格式"""
    text = "# 标题\n内容"
    segments = _segment_parent_child(text, child_max=50, parent_max=100)

    for seg in segments:
        assert 'id' in seg
        assert 'content' in seg
        assert 'segment_type' in seg
        assert 'metadata' in seg
        assert seg['segment_type'] in ('parent', 'child')
    print('[PASS] test_segment_metadata')


def test_segment_type_values():
    """测试分段类型值"""
    text = "这是一段测试文本。" * 20
    segments = _segment_parent_child(text, child_max=50, parent_max=200)

    for seg in segments:
        assert seg['segment_type'] in ('parent', 'child')
    print('[PASS] test_segment_type_values')


def run_all_tests():
    """运行所有测试"""
    print('=' * 60)
    print('知识库模块单元测试')
    print('=' * 60)

    test_chinese_segmentation()
    test_chinese_segmentation_short_text()
    test_chinese_segmentation_empty()
    test_western_segmentation()
    test_segmentation_with_overlap()
    test_segmentation_clean_rules()
    test_parent_child_segmentation()
    test_parent_child_short_text()
    test_document_structure_extraction()
    test_document_structure_empty()
    test_get_segment_structure()
    test_extract_json_list()
    test_calc_keyword_score()
    test_calc_keyword_score_english()
    test_rerank_fallback()
    test_rerank_fallback_with_top_k()
    test_rerank_empty_segments()
    test_sort_by_score()
    test_sort_by_score_with_top_k()
    test_sort_by_score_mismatched_length()
    test_rerank_with_mock_embedding()
    test_segment_metadata()
    test_segment_type_values()

    print('=' * 60)
    print('所有测试通过！')
    print('=' * 60)


if __name__ == '__main__':
    run_all_tests()
