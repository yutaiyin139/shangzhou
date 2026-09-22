# -*- coding: utf-8 -*-
"""
工作流高级节点单元测试
测试 Document Extractor、Template Transform、List Operator 节点
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.workflow_runner import (
    _node_document_extractor,
    _node_template_transform,
    _node_list_operator,
    _apply_filter,
    _apply_sort,
    _apply_extract,
)


# ============================================================
# Document Extractor 测试
# ============================================================

def test_doc_extractor_empty():
    """测试空文件返回空文本"""
    data = {
        'type': 'document-extractor',
        'variable_selector': ['start', 'file'],
    }
    context = {'start': {'file': None}}

    result = _node_document_extractor(data, context)
    assert result.get('text') == ''
    print('[PASS] test_doc_extractor_empty')


def test_doc_extractor_string_input():
    """测试字符串输入直接返回"""
    data = {
        'type': 'document-extractor',
        'variable_selector': ['start', 'file'],
    }
    context = {'start': {'file': '这是直接传入的文本内容'}}

    result = _node_document_extractor(data, context)
    assert result.get('text') == '这是直接传入的文本内容'
    print('[PASS] test_doc_extractor_string_input')


def test_doc_extractor_dict_with_text():
    """测试字典中包含 text 字段"""
    data = {
        'type': 'document-extractor',
        'variable_selector': ['start', 'file'],
    }
    context = {'start': {'file': {'text': '从字典中提取的文本'}}}

    result = _node_document_extractor(data, context)
    assert result.get('text') == '从字典中提取的文本'
    print('[PASS] test_doc_extractor_dict_with_text')


def test_doc_extractor_array_files():
    """测试文件数组"""
    data = {
        'type': 'document-extractor',
        'variable_selector': ['start', 'files'],
        'is_array_file': True,
    }
    context = {'start': {'files': [
        {'text': '文件1内容'},
        {'text': '文件2内容'},
        {'text': '文件3内容'},
    ]}}

    result = _node_document_extractor(data, context)
    text = result.get('text', '')
    assert '文件1内容' in text
    assert '文件2内容' in text
    assert '文件3内容' in text
    print('[PASS] test_doc_extractor_array_files')


# ============================================================
# Template Transform 测试
# ============================================================

def test_template_basic():
    """测试基本模板转换"""
    data = {
        'type': 'template-transform',
        'template': '您好 {{name}}，您的订单号是 {{order_id}}',
        'variables': [
            {'variable': 'name', 'value_selector': ['start', 'user_name']},
            {'variable': 'order_id', 'value_selector': ['start', 'order']},
        ],
    }
    context = {'start': {'user_name': '张三', 'order': 'ABC123'}}

    result = _node_template_transform(data, context)
    assert result.get('output') == '您好 张三，您的订单号是 ABC123'
    print('[PASS] test_template_basic')


def test_template_empty():
    """测试空模板"""
    data = {
        'type': 'template-transform',
        'template': '',
        'variables': [],
    }
    context = {}

    result = _node_template_transform(data, context)
    assert result.get('output') == ''
    print('[PASS] test_template_empty')


def test_template_dify_syntax():
    """测试 Dify 风格语法 {{#node.variable#}}"""
    data = {
        'type': 'template-transform',
        'template': '查询：{{#start.query#}}，结果：{{#node1.result#}}',
        'variables': [],
    }
    context = {'start': {'query': '测试问题'}, 'node1': {'result': '测试结果'}}

    result = _node_template_transform(data, context)
    assert result.get('output') == '查询：测试问题，结果：测试结果'
    print('[PASS] test_template_dify_syntax')


def test_template_with_list():
    """测试模板中渲染列表"""
    data = {
        'type': 'template-transform',
        'template': '项目列表：{{items}}',
        'variables': [
            {'variable': 'items', 'value_selector': ['node1', 'list']},
        ],
    }
    context = {'node1': {'list': ['苹果', '香蕉', '橙子']}}

    result = _node_template_transform(data, context)
    output = result.get('output', '')
    assert '苹果' in output
    assert '香蕉' in output
    assert '橙子' in output
    print('[PASS] test_template_with_list')


def test_template_missing_variable():
    """测试缺失变量替换为空"""
    data = {
        'type': 'template-transform',
        'template': '姓名：{{name}}，年龄：{{age}}',
        'variables': [
            {'variable': 'name', 'value_selector': ['start', 'name']},
            {'variable': 'age', 'value_selector': ['start', 'age']},
        ],
    }
    context = {'start': {'name': '李四'}}  # age 不存在

    result = _node_template_transform(data, context)
    assert result.get('output') == '姓名：李四，年龄：'
    print('[PASS] test_template_missing_variable')


# ============================================================
# List Operator 测试
# ============================================================

def test_list_operator_empty():
    """测试空列表"""
    data = {
        'type': 'list-operator',
        'variable': ['start', 'items'],
    }
    context = {'start': {'items': []}}

    result = _node_list_operator(data, context)
    assert result.get('output') == []
    print('[PASS] test_list_operator_empty')


def test_list_operator_filter_contains():
    """测试过滤 - 包含"""
    data = {
        'type': 'list-operator',
        'variable': ['start', 'items'],
        'filter_by': {'enabled': True, 'key': 'name', 'value': '报告', 'operator': 'contains'},
    }
    context = {'start': {'items': [
        {'name': '年度报告.pdf', 'type': 'pdf'},
        {'name': '图片.jpg', 'type': 'image'},
        {'name': '财务报告.pdf', 'type': 'pdf'},
        {'name': '文档.docx', 'type': 'doc'},
    ]}}

    result = _node_list_operator(data, context)
    output = result.get('output', [])
    assert len(output) == 2
    assert all('报告' in item['name'] for item in output)
    print('[PASS] test_list_operator_filter_contains')


def test_list_operator_filter_equals():
    """测试过滤 - 等于"""
    data = {
        'type': 'list-operator',
        'variable': ['start', 'items'],
        'filter_by': {'enabled': True, 'key': 'type', 'value': 'pdf', 'operator': 'equals'},
    }
    context = {'start': {'items': [
        {'name': '文件1.pdf', 'type': 'pdf'},
        {'name': '文件2.jpg', 'type': 'image'},
        {'name': '文件3.pdf', 'type': 'pdf'},
    ]}}

    result = _node_list_operator(data, context)
    output = result.get('output', [])
    assert len(output) == 2
    assert all(item['type'] == 'pdf' for item in output)
    print('[PASS] test_list_operator_filter_equals')


def test_list_operator_filter_regex():
    """测试过滤 - 正则匹配"""
    data = {
        'type': 'list-operator',
        'variable': ['start', 'items'],
        'filter_by': {'enabled': True, 'key': 'name', 'value': r'\.pdf$', 'operator': 'regex'},
    }
    context = {'start': {'items': [
        {'name': '文件1.pdf'},
        {'name': '文件2.jpg'},
        {'name': '文件3.pdf'},
    ]}}

    result = _node_list_operator(data, context)
    output = result.get('output', [])
    assert len(output) == 2
    print('[PASS] test_list_operator_filter_regex')


def test_list_operator_sort_asc():
    """测试升序排序"""
    data = {
        'type': 'list-operator',
        'variable': ['start', 'items'],
        'sort_by': {'enabled': True, 'key': 'name', 'value': 'asc'},
    }
    context = {'start': {'items': [
        {'name': 'Charlie'},
        {'name': 'Alice'},
        {'name': 'Bob'},
    ]}}

    result = _node_list_operator(data, context)
    output = result.get('output', [])
    assert output[0]['name'] == 'Alice'
    assert output[1]['name'] == 'Bob'
    assert output[2]['name'] == 'Charlie'
    print('[PASS] test_list_operator_sort_asc')


def test_list_operator_sort_desc():
    """测试降序排序"""
    data = {
        'type': 'list-operator',
        'variable': ['start', 'items'],
        'sort_by': {'enabled': True, 'key': 'score', 'value': 'desc'},
    }
    context = {'start': {'items': [
        {'name': 'A', 'score': 80},
        {'name': 'B', 'score': 95},
        {'name': 'C', 'score': 70},
    ]}}

    result = _node_list_operator(data, context)
    output = result.get('output', [])
    assert output[0]['score'] == 95
    assert output[1]['score'] == 80
    assert output[2]['score'] == 70
    print('[PASS] test_list_operator_sort_desc')


def test_list_operator_extract():
    """测试字段提取"""
    data = {
        'type': 'list-operator',
        'variable': ['start', 'items'],
        'extract_by': {'enabled': True, 'key': 'name'},
    }
    context = {'start': {'items': [
        {'id': 1, 'name': 'Alice', 'age': 25},
        {'id': 2, 'name': 'Bob', 'age': 30},
        {'id': '3', 'name': 'Charlie', 'age': 35},
    ]}}

    result = _node_list_operator(data, context)
    output = result.get('output', [])
    assert output == ['Alice', 'Bob', 'Charlie']
    print('[PASS] test_list_operator_extract')


def test_list_operator_limit():
    """测试数量限制"""
    data = {
        'type': 'list-operator',
        'variable': ['start', 'items'],
        'limit': 2,
    }
    context = {'start': {'items': [1, 2, 3, 4, 5]}}

    result = _node_list_operator(data, context)
    output = result.get('output', [])
    assert len(output) == 2
    assert output == [1, 2]
    print('[PASS] test_list_operator_limit')


def test_list_operator_combined():
    """测试组合操作：过滤 + 排序 + 限制"""
    data = {
        'type': 'list-operator',
        'variable': ['start', 'items'],
        'filter_by': {'enabled': True, 'key': 'type', 'value': 'pdf', 'operator': 'equals'},
        'sort_by': {'enabled': True, 'key': 'name', 'value': 'asc'},
        'limit': 2,
    }
    context = {'start': {'items': [
        {'name': 'Z文件.pdf', 'type': 'pdf'},
        {'name': 'A图片.jpg', 'type': 'image'},
        {'name': 'M文件.pdf', 'type': 'pdf'},
        {'name': 'B文件.pdf', 'type': 'pdf'},
    ]}}

    result = _node_list_operator(data, context)
    output = result.get('output', [])
    assert len(output) == 2
    assert output[0]['name'] == 'B文件.pdf'
    assert output[1]['name'] == 'M文件.pdf'
    print('[PASS] test_list_operator_combined')


# ============================================================
# 辅助函数测试
# ============================================================

def test_apply_filter_not_contains():
    """测试不包含过滤"""
    items = [{'name': 'abc'}, {'name': 'def'}, {'name': 'ghi'}]
    filter_by = {'key': 'name', 'value': 'a', 'operator': 'not_contains'}
    result = _apply_filter(items, filter_by, 'array[object]')
    assert len(result) == 2
    print('[PASS] test_apply_filter_not_contains')


def test_apply_filter_starts_with():
    """测试开头匹配过滤"""
    items = [{'name': 'test1'}, {'name': 'test2'}, {'name': 'other'}]
    filter_by = {'key': 'name', 'value': 'test', 'operator': 'starts_with'}
    result = _apply_filter(items, filter_by, 'array[object]')
    assert len(result) == 2
    print('[PASS] test_apply_filter_starts_with')


def test_apply_filter_ends_with():
    """测试结尾匹配过滤"""
    items = [{'name': 'file.pdf'}, {'name': 'file.jpg'}, {'name': 'doc.pdf'}]
    filter_by = {'key': 'name', 'value': '.pdf', 'operator': 'ends_with'}
    result = _apply_filter(items, filter_by, 'array[object]')
    assert len(result) == 2
    print('[PASS] test_apply_filter_ends_with')


def test_apply_extract_missing_key():
    """测试提取不存在的字段"""
    items = [{'name': 'Alice'}, {'age': 25}]
    extract_by = {'key': 'name'}
    result = _apply_extract(items, extract_by)
    assert result == ['Alice']
    print('[PASS] test_apply_extract_missing_key')


def run_all_tests():
    """运行所有测试"""
    print('=' * 60)
    print('工作流高级节点单元测试')
    print('=' * 60)

    # Document Extractor
    test_doc_extractor_empty()
    test_doc_extractor_string_input()
    test_doc_extractor_dict_with_text()
    test_doc_extractor_array_files()

    # Template Transform
    test_template_basic()
    test_template_empty()
    test_template_dify_syntax()
    test_template_with_list()
    test_template_missing_variable()

    # List Operator
    test_list_operator_empty()
    test_list_operator_filter_contains()
    test_list_operator_filter_equals()
    test_list_operator_filter_regex()
    test_list_operator_sort_asc()
    test_list_operator_sort_desc()
    test_list_operator_extract()
    test_list_operator_limit()
    test_list_operator_combined()

    # 辅助函数
    test_apply_filter_not_contains()
    test_apply_filter_starts_with()
    test_apply_filter_ends_with()
    test_apply_extract_missing_key()

    print('=' * 60)
    print('所有测试通过！')
    print('=' * 60)


if __name__ == '__main__':
    run_all_tests()
