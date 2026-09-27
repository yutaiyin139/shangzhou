# -*- coding: utf-8 -*-
"""
Variable Aggregator 节点单元测试
测试变量聚合节点的核心逻辑：多变量合并、多种输出格式
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 实现已拆到 engine/nodes/variable_aggregator.py
from engine.nodes.variable_aggregator import _node_variable_aggregator


def test_aggregator_object_output():
    """测试对象模式输出"""
    data = {
        'type': 'variable-aggregator',
        'output_type': 'object',
        'output': 'result',
        'variables': [
            {'variable': 'name', 'value_selector': ['user', 'name']},
            {'variable': 'age', 'value_selector': ['user', 'age']},
        ],
    }
    context = {
        'user': {'name': '张三', 'age': 25},
    }

    result = _node_variable_aggregator(data, context, None)

    assert result.get('result') == {'name': '张三', 'age': 25}
    assert result.get('aggregated') == {'name': '张三', 'age': 25}
    print('[PASS] test_aggregator_object_output')


def test_aggregator_array_output():
    """测试数组模式输出"""
    data = {
        'type': 'variable-aggregator',
        'output_type': 'array',
        'output': 'items',
        'variables': [
            {'variable': 'a', 'value_selector': ['val1']},
            {'variable': 'b', 'value_selector': ['val2']},
        ],
    }
    context = {'val1': 'hello', 'val2': 'world'}

    result = _node_variable_aggregator(data, context, None)

    assert result.get('items') == ['hello', 'world']
    assert result.get('aggregated') == ['hello', 'world']
    print('[PASS] test_aggregator_array_output')


def test_aggregator_string_output():
    """测试字符串拼接模式"""
    data = {
        'type': 'variable-aggregator',
        'output_type': 'string',
        'output': 'text',
        'separator': ', ',
        'variables': [
            {'variable': 'first', 'value_selector': ['a']},
            {'variable': 'second', 'value_selector': ['b']},
            {'variable': 'third', 'value_selector': ['c']},
        ],
    }
    context = {'a': '苹果', 'b': '香蕉', 'c': '橙子'}

    result = _node_variable_aggregator(data, context, None)

    assert result.get('text') == '苹果, 香蕉, 橙子'
    print('[PASS] test_aggregator_string_output')


def test_aggregator_empty_variables():
    """测试空变量列表"""
    data = {
        'type': 'variable-aggregator',
        'output_type': 'object',
        'output': 'result',
        'variables': [],
    }
    context = {}

    result = _node_variable_aggregator(data, context, None)

    assert result.get('result') == {}
    print('[PASS] test_aggregator_empty_variables')


def test_aggregator_default_output_var():
    """测试默认输出变量名"""
    data = {
        'type': 'variable-aggregator',
        'output_type': 'object',
        'variables': [
            {'variable': 'x', 'value_selector': ['val']},
        ],
    }
    context = {'val': 123}

    result = _node_variable_aggregator(data, context, None)

    assert 'aggregated_output' in result
    assert result['aggregated_output'] == {'x': 123}
    print('[PASS] test_aggregator_default_output_var')


def test_aggregator_missing_variable_uses_default():
    """测试变量不存在时使用默认值"""
    data = {
        'type': 'variable-aggregator',
        'output_type': 'object',
        'output': 'result',
        'variables': [
            {'variable': 'exists', 'value_selector': ['a']},
            {'variable': 'missing', 'value_selector': ['nonexistent'], 'default': '默认值'},
        ],
    }
    context = {'a': '存在'}

    result = _node_variable_aggregator(data, context, None)

    assert result.get('result') == {'exists': '存在', 'missing': '默认值'}
    print('[PASS] test_aggregator_missing_variable_uses_default')


def test_aggregator_nested_selector():
    """测试嵌套选择器"""
    data = {
        'type': 'variable-aggregator',
        'output_type': 'object',
        'output': 'result',
        'variables': [
            {'variable': 'city', 'value_selector': ['location', 'city']},
            {'variable': 'country', 'value_selector': ['location', 'country']},
        ],
    }
    context = {'location': {'city': '杭州', 'country': '中国'}}

    result = _node_variable_aggregator(data, context, None)

    assert result.get('result') == {'city': '杭州', 'country': '中国'}
    print('[PASS] test_aggregator_nested_selector')


def test_aggregator_string_with_newline_separator():
    """测试换行分隔符"""
    data = {
        'type': 'variable-aggregator',
        'output_type': 'string',
        'output': 'text',
        'separator': '\n',
        'variables': [
            {'variable': 'line1', 'value_selector': ['a']},
            {'variable': 'line2', 'value_selector': ['b']},
        ],
    }
    context = {'a': '第一行', 'b': '第二行'}

    result = _node_variable_aggregator(data, context, None)

    assert result.get('text') == '第一行\n第二行'
    print('[PASS] test_aggregator_string_with_newline_separator')


def test_aggregator_mixed_types_in_array():
    """测试数组模式混合类型"""
    data = {
        'type': 'variable-aggregator',
        'output_type': 'array',
        'output': 'mixed',
        'variables': [
            {'variable': 'str_val', 'value_selector': ['s']},
            {'variable': 'num_val', 'value_selector': ['n']},
            {'variable': 'bool_val', 'value_selector': ['b']},
            {'variable': 'list_val', 'value_selector': ['l']},
        ],
    }
    context = {'s': '文本', 'n': 42, 'b': True, 'l': [1, 2, 3]}

    result = _node_variable_aggregator(data, context, None)

    assert result.get('mixed') == ['文本', 42, True, [1, 2, 3]]
    print('[PASS] test_aggregator_mixed_types_in_array')


def test_aggregator_unknown_output_type():
    """测试未知输出类型返回空对象"""
    data = {
        'type': 'variable-aggregator',
        'output_type': 'unknown_type',
        'output': 'result',
        'variables': [
            {'variable': 'x', 'value_selector': ['a']},
        ],
    }
    context = {'a': 'test'}

    result = _node_variable_aggregator(data, context, None)

    assert result.get('result') == {}
    print('[PASS] test_aggregator_unknown_output_type')


def test_aggregator_variable_name_as_selector():
    """测试变量名作为选择器（无显式选择器时）"""
    data = {
        'type': 'variable-aggregator',
        'output_type': 'object',
        'output': 'result',
        'variables': [
            {'variable': 'name'},  # 没有 value_selector
            {'variable': 'age'},
        ],
    }
    context = {'name': '李四', 'age': 30}

    result = _node_variable_aggregator(data, context, None)

    assert result.get('result') == {'name': '李四', 'age': 30}
    print('[PASS] test_aggregator_variable_name_as_selector')


def test_aggregator_string_numeric_values():
    """测试字符串模式数值自动转字符串"""
    data = {
        'type': 'variable-aggregator',
        'output_type': 'string',
        'output': 'text',
        'separator': '-',
        'variables': [
            {'variable': 'a', 'value_selector': ['x']},
            {'variable': 'b', 'value_selector': ['y']},
        ],
    }
    context = {'x': 100, 'y': 200}

    result = _node_variable_aggregator(data, context, None)

    assert result.get('text') == '100-200'
    print('[PASS] test_aggregator_string_numeric_values')


def run_all_tests():
    """运行所有测试"""
    print('=' * 60)
    print('Variable Aggregator 节点单元测试')
    print('=' * 60)

    test_aggregator_object_output()
    test_aggregator_array_output()
    test_aggregator_string_output()
    test_aggregator_empty_variables()
    test_aggregator_default_output_var()
    test_aggregator_missing_variable_uses_default()
    test_aggregator_nested_selector()
    test_aggregator_string_with_newline_separator()
    test_aggregator_mixed_types_in_array()
    test_aggregator_unknown_output_type()
    test_aggregator_variable_name_as_selector()
    test_aggregator_string_numeric_values()

    print('=' * 60)
    print('所有测试通过！')
    print('=' * 60)


if __name__ == '__main__':
    run_all_tests()
