# -*- coding: utf-8 -*-
"""
Human Input 节点单元测试
测试 Human Input 节点的核心逻辑：暂停/恢复机制
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from engine.workflow_runner import (
    _node_human_input,
    _execute_workflow_graph,
    run_workflow,
)


def test_human_input_basic():
    """测试 Human Input 节点基本功能"""
    data = {
        'type': 'human-input',
        'message': '请输入您的姓名：',
        'form_fields': [
            {'name': 'name', 'label': '姓名', 'type': 'text', 'required': True}
        ],
        'output': 'user_input',
        '_node_id': 'human1',
    }
    context = {}

    result = _node_human_input(data, context, None)

    assert result.get('_human_input_wait') is True
    assert result.get('_human_input_output_var') == 'user_input'
    config = result.get('_human_input_config', {})
    assert config.get('message') == '请输入您的姓名：'
    assert len(config.get('fields', [])) == 1
    print('[PASS] test_human_input_basic')


def test_human_input_variable_replacement():
    """测试 Human Input 变量替换"""
    data = {
        'type': 'human-input',
        'message': '您好 {{name}}，请确认以下信息：',
        'form_fields': [],
        'output': 'confirmation',
        '_node_id': 'human1',
    }
    context = {'name': '张三'}

    result = _node_human_input(data, context, None)

    config = result.get('_human_input_config', {})
    assert '张三' in config.get('message', '')
    print('[PASS] test_human_input_variable_replacement')


def test_human_input_default_output():
    """测试 Human Input 默认输出变量名"""
    data = {
        'type': 'human-input',
        'message': '请确认',
        'form_fields': [],
        '_node_id': 'human1',
    }
    context = {}

    result = _node_human_input(data, context, None)

    assert result.get('_human_input_output_var') == 'human_input'
    print('[PASS] test_human_input_default_output')


def test_human_input_multiple_fields():
    """测试 Human Input 多字段表单"""
    data = {
        'type': 'human-input',
        'message': '请填写以下信息：',
        'form_fields': [
            {'name': 'name', 'label': '姓名', 'type': 'text', 'required': True},
            {'name': 'email', 'label': '邮箱', 'type': 'text', 'required': True},
            {'name': 'age', 'label': '年龄', 'type': 'number', 'required': False},
            {'name': 'gender', 'label': '性别', 'type': 'select', 'required': False},
        ],
        'output': 'form_data',
        '_node_id': 'human1',
    }
    context = {}

    result = _node_human_input(data, context, None)

    config = result.get('_human_input_config', {})
    assert len(config.get('fields', [])) == 4
    assert result.get('_human_input_output_var') == 'form_data'
    print('[PASS] test_human_input_multiple_fields')


def test_workflow_with_human_input():
    """测试包含 Human Input 节点的完整工作流"""
    graph = {
        'nodes': [
            {'id': 'start', 'data': {'type': 'start', 'title': '开始'}},
            {'id': 'human', 'data': {
                'type': 'human-input', 'title': '人工确认',
                'message': '请确认是否继续？',
                'form_fields': [
                    {'name': 'confirm', 'label': '确认', 'type': 'select', 'required': True}
                ],
                'output': 'user_confirm',
                '_node_id': 'human',
            }},
            {'id': 'code', 'data': {'type': 'code', 'title': '处理结果', 'code': 'result = \"用户选择: \" + args.get(\"confirm\", \"\")'}},
            {'id': 'end', 'data': {'type': 'end', 'title': '结束'}},
        ],
        'edges': [
            {'source': 'start', 'target': 'human'},
            {'source': 'human', 'target': 'code'},
            {'source': 'code', 'target': 'end'},
        ]
    }

    inputs = {}
    result = _execute_workflow_graph(graph, inputs, None, 'test-app', 'test-run')

    # 验证返回了暂停状态
    assert result.get('__human_input_pause__') is True
    assert result.get('__human_input_node_id__') == 'human'
    assert '__context__' in result
    assert '__exec_order__' in result
    print('[PASS] test_workflow_with_human_input')


def test_workflow_pause_position():
    """测试 Human Input 在流程中间暂停"""
    graph = {
        'nodes': [
            {'id': 'start', 'data': {'type': 'start', 'title': '开始'}},
            {'id': 'code1', 'data': {'type': 'code', 'title': '步骤1', 'code': 'result = True'}},
            {'id': 'human', 'data': {
                'type': 'human-input', 'title': '人工输入',
                'message': '请输入：',
                'form_fields': [{'name': 'input', 'label': '输入', 'type': 'text'}],
                'output': 'user_data',
                '_node_id': 'human',
            }},
            {'id': 'code2', 'data': {'type': 'code', 'title': '步骤2', 'code': 'result = False'}},
            {'id': 'end', 'data': {'type': 'end', 'title': '结束'}},
        ],
        'edges': [
            {'source': 'start', 'target': 'code1'},
            {'source': 'code1', 'target': 'human'},
            {'source': 'human', 'target': 'code2'},
            {'source': 'code2', 'target': 'end'},
        ]
    }

    inputs = {}
    result = _execute_workflow_graph(graph, inputs, None, 'test-app', 'test-run')

    # 验证在 Human Input 处暂停
    assert result.get('__human_input_pause__') is True
    # 验证前面的节点已执行（code1 设置了 result = True）
    context = result.get('__context__', {})
    assert context.get('result') is True
    # 验证当前节点索引（应该是 human 节点的索引 = 2）
    assert result.get('__current_node_idx__', 0) == 2
    print('[PASS] test_workflow_pause_position')


def run_all_tests():
    """运行所有测试"""
    print('=' * 60)
    print('Human Input 节点单元测试')
    print('=' * 60)

    test_human_input_basic()
    test_human_input_variable_replacement()
    test_human_input_default_output()
    test_human_input_multiple_fields()
    test_workflow_with_human_input()
    test_workflow_pause_position()

    print('=' * 60)
    print('所有测试通过！')
    print('=' * 60)


if __name__ == '__main__':
    run_all_tests()
