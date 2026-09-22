# -*- coding: utf-8 -*-
"""
Iterator 节点单元测试
测试迭代节点的核心逻辑：子图识别、迭代执行、结果聚合
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from engine.workflow_runner import (
    _execute_node,
    _node_iteration,
    _identify_iteration_subgraphs,
    _resolve_selector,
    _aggregate_results,
    _execute_sub_graph,
)


def test_resolve_selector():
    """测试变量选择器解析"""
    context = {
        'start': {'items': [1, 2, 3]},
        'data': {'name': 'test'}
    }

    # 正常路径
    assert _resolve_selector(context, ['start', 'items']) == [1, 2, 3]
    assert _resolve_selector(context, ['data', 'name']) == 'test'

    # 单级路径
    assert _resolve_selector(context, ['data']) == {'name': 'test'}

    # 不存在的路径
    assert _resolve_selector(context, ['not_exist']) is None
    assert _resolve_selector(context, ['start', 'not_exist']) is None

    # 空选择器
    assert _resolve_selector(context, []) is None
    assert _resolve_selector(context, '') is None

    print('[PASS] test_resolve_selector 通过')


def test_aggregate_results():
    """测试结果聚合"""
    # 无选择器时返回全部
    results = [{'a': 1}, {'a': 2}, {'a': 3}]
    assert _aggregate_results(results, []) == results

    # 按选择器提取
    results = [
        {'name': 'Alice', 'age': 25, 'city': 'Beijing'},
        {'name': 'Bob', 'age': 30, 'city': 'Shanghai'}
    ]
    aggregated = _aggregate_results(results, ['name', 'age'])
    assert aggregated == [{'name': 'Alice', 'age': 25}, {'name': 'Bob', 'age': 30}]

    # 选择器字段不存在
    aggregated = _aggregate_results(results, ['name', 'not_exist'])
    assert aggregated == [{'name': 'Alice'}, {'name': 'Bob'}]

    print('[PASS] test_aggregate_results 通过')


def test_identify_iteration_subgraphs():
    """测试迭代子图识别"""
    nodes = [
        {'id': 'start', 'data': {'type': 'start'}},
        {'id': 'iterator', 'data': {'type': 'iteration'}},
        {'id': 'code1', 'data': {'type': 'code'}},
        {'id': 'llm1', 'data': {'type': 'llm'}},
        {'id': 'end', 'data': {'type': 'end'}},
    ]
    edges = [
        {'source': 'start', 'target': 'iterator'},
        {'source': 'iterator', 'target': 'code1', 'sourceHandle': 'loop'},
        {'source': 'code1', 'target': 'llm1'},
        {'source': 'iterator', 'target': 'end', 'sourceHandle': 'end'},
    ]

    iteration_nodes, child_node_map = _identify_iteration_subgraphs(nodes, edges)

    # 验证识别到迭代节点
    assert 'iterator' in iteration_nodes
    assert len(iteration_nodes['iterator']['nodes']) == 2  # code1, llm1
    assert 'code1' in child_node_map
    assert 'llm1' in child_node_map

    # 验证子图边
    child_edge_sources = [e['source'] for e in iteration_nodes['iterator']['edges']]
    assert 'iterator' in child_edge_sources
    assert 'code1' in child_edge_sources

    print('[PASS] test_identify_iteration_subgraphs 通过')


def test_identify_iteration_no_loop_handle():
    """测试无明确 loop handle 时的子图识别"""
    nodes = [
        {'id': 'start', 'data': {'type': 'start'}},
        {'id': 'iterator', 'data': {'type': 'iteration'}},
        {'id': 'code1', 'data': {'type': 'code'}},
        {'id': 'end', 'data': {'type': 'end'}},
    ]
    edges = [
        {'source': 'start', 'target': 'iterator'},
        {'source': 'iterator', 'target': 'code1'},  # 无 sourceHandle
        {'source': 'iterator', 'target': 'end'},
    ]

    iteration_nodes, child_node_map = _identify_iteration_subgraphs(nodes, edges)

    # 第一个输出应被视为子图
    assert 'iterator' in iteration_nodes
    assert len(iteration_nodes['iterator']['nodes']) == 1  # code1
    assert 'code1' in child_node_map

    print('[PASS] test_identify_iteration_no_loop_handle 通过')


def test_identify_no_iteration():
    """测试无迭代节点时返回空"""
    nodes = [
        {'id': 'start', 'data': {'type': 'start'}},
        {'id': 'end', 'data': {'type': 'end'}},
    ]
    edges = [
        {'source': 'start', 'target': 'end'},
    ]

    iteration_nodes, child_node_map = _identify_iteration_subgraphs(nodes, edges)
    assert len(iteration_nodes) == 0
    assert len(child_node_map) == 0

    print('[PASS] test_identify_no_iteration 通过')


def test_iteration_node_basic():
    """测试迭代节点基本执行"""
    data = {
        'type': 'iteration',
        'input_selector': ['items'],
        'output_selector': [],
        'max_iterations': 100,
    }
    context = {
        'items': ['apple', 'banana', 'cherry']
    }

    result = _node_iteration(data, context, None)

    assert result['iteration_count'] == 3
    assert len(result['iteration_results']) == 3
    assert result['output'] == ['apple', 'banana', 'cherry']

    print('[PASS] test_iteration_node_basic 通过')


def test_iteration_node_empty_list():
    """测试空列表迭代"""
    data = {
        'type': 'iteration',
        'input_selector': ['items'],
        'output_selector': [],
    }
    context = {'items': []}

    result = _node_iteration(data, context, None)

    assert result['iteration_count'] == 0
    assert result['output'] == []

    print('[PASS] test_iteration_node_empty_list 通过')


def test_iteration_node_with_subgraph():
    """测试带子图的迭代节点"""
    data = {
        'type': 'iteration',
        'input_selector': ['numbers'],
        'output_selector': [],
        'max_iterations': 100,
        '_node_id': 'iter1',
        '_child_nodes': [
            {'id': 'code1', 'data': {'type': 'code', 'code': 'result = args["item"] * 2'}},
        ],
        '_child_edges': [],
    }
    context = {
        'numbers': [1, 2, 3, 4, 5]
    }

    result = _node_iteration(data, context, None)

    assert result['iteration_count'] == 5
    # 每个子流程执行后 result 应该是 item * 2
    assert len(result['iteration_results']) == 5

    print('[PASS] test_iteration_node_with_subgraph 通过')


def test_iteration_node_max_iterations():
    """测试最大迭代次数限制"""
    data = {
        'type': 'iteration',
        'input_selector': ['items'],
        'max_iterations': 3,
    }
    context = {'items': [1, 2, 3, 4, 5]}

    try:
        _node_iteration(data, context, None)
        assert False, '应该抛出异常'
    except Exception as e:
        assert '超过限制' in str(e)

    print('[PASS] test_iteration_node_max_iterations 通过')


def test_iteration_node_invalid_input():
    """测试无效输入"""
    data = {
        'type': 'iteration',
        'input_selector': ['items'],
    }
    context = {'items': 'not_a_list'}

    try:
        _node_iteration(data, context, None)
        assert False, '应该抛出异常'
    except Exception as e:
        assert '必须是列表' in str(e)

    print('[PASS] test_iteration_node_invalid_input 通过')


def test_iteration_node_json_string_input():
    """测试 JSON 字符串输入"""
    data = {
        'type': 'iteration',
        'input_selector': ['items'],
    }
    context = {'items': '[1, 2, 3]'}

    result = _node_iteration(data, context, None)

    assert result['iteration_count'] == 3

    print('[PASS] test_iteration_node_json_string_input 通过')


def test_execute_sub_graph():
    """测试子图执行"""
    nodes = [
        {'id': 'code1', 'data': {'type': 'code', 'code': 'result = args["item"] + 10'}},
        {'id': 'code2', 'data': {'type': 'code', 'code': 'result = args["result"] * 2'}},
    ]
    edges = [
        {'source': 'code1', 'target': 'code2'},
    ]
    context = {'item': 5}

    result = _execute_sub_graph(nodes, edges, context, None, 'iter1', 0)

    # code1: result = 5 + 10 = 15
    # code2: result = 15 * 2 = 30
    assert result['result'] == 30

    print('[PASS] test_execute_sub_graph 通过')


def test_iteration_with_dict_items():
    """测试字典列表迭代"""
    data = {
        'type': 'iteration',
        'input_selector': ['users'],
        'output_selector': ['name'],
        '_node_id': 'iter1',
        '_child_nodes': [
            {'id': 'code1', 'data': {'type': 'code', 'code': 'result = args["name"].upper()'}},
        ],
        '_child_edges': [],
    }
    context = {
        'users': [
            {'name': 'alice', 'age': 25},
            {'name': 'bob', 'age': 30},
        ]
    }

    result = _node_iteration(data, context, None)

    assert result['iteration_count'] == 2
    # output_selector 提取 name 字段
    assert result['output'] == [{'name': 'alice'}, {'name': 'bob'}]

    print('[PASS] test_iteration_with_dict_items 通过')


def run_all_tests():
    """运行所有测试"""
    print('=' * 60)
    print('Iterator 节点单元测试')
    print('=' * 60)

    test_resolve_selector()
    test_aggregate_results()
    test_identify_iteration_subgraphs()
    test_identify_iteration_no_loop_handle()
    test_identify_no_iteration()
    test_iteration_node_basic()
    test_iteration_node_empty_list()
    test_iteration_node_with_subgraph()
    test_iteration_node_max_iterations()
    test_iteration_node_invalid_input()
    test_iteration_node_json_string_input()
    test_execute_sub_graph()
    test_iteration_with_dict_items()

    print('=' * 60)
    print('所有测试通过！')
    print('=' * 60)


if __name__ == '__main__':
    run_all_tests()
