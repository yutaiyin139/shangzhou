# -*- coding: utf-8 -*-
"""
Agent 节点单元测试
测试 Agent 节点的核心逻辑：响应解析、工具执行、ReAct 循环
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from unittest.mock import patch, MagicMock
from engine.workflow_runner import (
    _node_agent,
    _parse_agent_response,
    _execute_agent_tool,
    _build_tool_descriptions,
    _call_llm,
    _tool_code,
    _tool_calculator,
)


def test_parse_agent_response_final_answer():
    """测试解析 Final Answer 响应"""
    response = 'Final Answer: 地球是太阳系的第三颗行星。'
    result = _parse_agent_response(response)
    assert result['type'] == 'final_answer'
    assert '地球' in result['content']
    print('[PASS] test_parse_agent_response_final_answer')


def test_parse_agent_response_action():
    """测试解析 Action 响应"""
    response = 'Action: search\nAction Input: {"query": "天气预报"}'
    result = _parse_agent_response(response)
    assert result['type'] == 'action'
    assert result['action'] == 'search'
    assert result['action_input'] == {'query': '天气预报'}
    print('[PASS] test_parse_agent_response_action')


def test_parse_agent_response_action_string_input():
    """测试解析 Action 响应（字符串输入）"""
    response = 'Action: echo\nAction Input: hello world'
    result = _parse_agent_response(response)
    assert result['type'] == 'action'
    assert result['action'] == 'echo'
    assert result['action_input'] == 'hello world'
    print('[PASS] test_parse_agent_response_action_string_input')


def test_parse_agent_response_json_format():
    """测试解析 JSON 格式响应"""
    response = '{"action": "search", "action_input": {"query": "test"}}'
    result = _parse_agent_response(response)
    assert result['type'] == 'action'
    assert result['action'] == 'search'
    print('[PASS] test_parse_agent_response_json_format')


def test_parse_agent_response_json_final_answer():
    """测试解析 JSON 格式最终答案"""
    response = '{"final_answer": "这是最终答案"}'
    result = _parse_agent_response(response)
    assert result['type'] == 'final_answer'
    assert result['content'] == '这是最终答案'
    print('[PASS] test_parse_agent_response_json_final_answer')


def test_parse_agent_response_unknown():
    """测试解析未知格式响应"""
    response = '这是一个普通的回答'
    result = _parse_agent_response(response)
    assert result['type'] == 'unknown'
    assert result['content'] == '这是一个普通的回答'
    print('[PASS] test_parse_agent_response_unknown')


def test_parse_agent_response_empty():
    """测试解析空响应"""
    result = _parse_agent_response('')
    assert result['type'] == 'unknown'
    assert result['content'] == ''
    print('[PASS] test_parse_agent_response_empty')


def test_build_tool_descriptions():
    """测试构建工具描述"""
    tools = [
        {'name': 'search', 'description': '搜索信息', 'type': 'http', 'parameters': {'url': 'http://api.search.com'}},
        {'name': 'calc', 'description': '计算器', 'type': 'calculator', 'parameters': {}},
    ]
    desc = _build_tool_descriptions(tools)
    assert 'search' in desc
    assert '搜索信息' in desc
    assert 'calc' in desc
    assert '计算器' in desc
    print('[PASS] test_build_tool_descriptions')


def test_build_tool_descriptions_empty():
    """测试空工具列表"""
    desc = _build_tool_descriptions([])
    assert desc == ''
    print('[PASS] test_build_tool_descriptions_empty')


def test_tool_calculator_basic():
    """测试计算器工具"""
    tool_def = {}
    result = _tool_calculator(tool_def, '2 + 3 * 4', {})
    assert result == '14'
    print('[PASS] test_tool_calculator_basic')


def test_tool_calculator_complex():
    """测试复杂计算"""
    tool_def = {}
    result = _tool_calculator(tool_def, '(10 + 5) * 2', {})
    assert result == '30'
    print('[PASS] test_tool_calculator_complex')


def test_tool_calculator_power():
    """测试幂运算"""
    tool_def = {}
    result = _tool_calculator(tool_def, '2 ** 10', {})
    assert result == '1024'
    print('[PASS] test_tool_calculator_power')


def test_tool_calculator_invalid_chars():
    """测试非法字符"""
    tool_def = {}
    result = _tool_calculator(tool_def, '__import__("os")', {})
    assert '错误' in result
    print('[PASS] test_tool_calculator_invalid_chars')


def test_tool_calculator_empty():
    """测试空输入"""
    tool_def = {}
    result = _tool_calculator(tool_def, '', {})
    assert '错误' in result
    print('[PASS] test_tool_calculator_empty')


def test_tool_code_basic():
    """测试代码执行工具"""
    tool_def = {'code': 'result = args["x"] + args["y"]'}
    result = _tool_code(tool_def, {'x': 10, 'y': 20}, {})
    assert result == '30'
    print('[PASS] test_tool_code_basic')


def test_tool_code_string():
    """测试字符串处理代码"""
    tool_def = {'code': 'result = args["text"].upper()'}
    result = _tool_code(tool_def, {'text': 'hello'}, {})
    assert result == 'HELLO'
    print('[PASS] test_tool_code_string')


def test_tool_code_list():
    """测试列表处理代码"""
    tool_def = {'code': 'result = sum(args["numbers"])'}
    result = _tool_code(tool_def, {'numbers': [1, 2, 3, 4, 5]}, {})
    assert result == '15'
    print('[PASS] test_tool_code_list')


def test_tool_code_no_code():
    """测试未配置代码"""
    tool_def = {}
    result = _tool_code(tool_def, {}, {})
    assert '错误' in result
    print('[PASS] test_tool_code_no_code')


def test_execute_agent_tool_not_found():
    """测试工具未找到"""
    result = _execute_agent_tool('nonexistent', {}, [], {})
    assert '未找到工具' in result
    print('[PASS] test_execute_agent_tool_not_found')


def test_execute_agent_tool_unsupported_type():
    """测试不支持的工具类型"""
    tools = [{'name': 'mytool', 'type': 'unsupported'}]
    result = _execute_agent_tool('mytool', {}, tools, {})
    assert '不支持的工具类型' in result
    print('[PASS] test_execute_agent_tool_unsupported_type')


@patch('engine.workflow_runner._call_llm')
def test_node_agent_direct_answer(mock_llm):
    """测试 Agent 节点直接回答（无需工具）"""
    mock_llm.return_value = {
        'content': 'Final Answer: 你好！我是AI助手。',
        'total_tokens': 50
    }

    data = {
        'type': 'agent',
        'model': {'provider': 'deepseek', 'name': 'deepseek-v4-pro'},
        'prompt': '你是一个友好的助手',
        'user_prompt': '你好',
        'tools': [],
        'max_iterations': 3,
        'output': 'result'
    }
    context = {}

    result = _node_agent(data, context, None)

    assert result['result'] == '你好！我是AI助手。'
    assert result['total_tokens'] == 50
    assert result['iterations_used'] == 1
    print('[PASS] test_node_agent_direct_answer')


@patch('engine.workflow_runner._call_llm')
def test_node_agent_with_tool_call(mock_llm):
    """测试 Agent 节点调用工具"""
    # 第一次调用返回 Action，第二次返回 Final Answer
    mock_llm.side_effect = [
        {'content': 'Action: calculator\nAction Input: 2 + 2', 'total_tokens': 30},
        {'content': 'Final Answer: 计算结果是 4', 'total_tokens': 40}
    ]

    data = {
        'type': 'agent',
        'model': {'provider': 'deepseek', 'name': 'deepseek-v4-pro'},
        'prompt': '你是一个助手',
        'user_prompt': '请计算 2 + 2',
        'tools': [{'name': 'calculator', 'description': '计算器', 'type': 'calculator'}],
        'max_iterations': 5,
        'output': 'result'
    }
    context = {}

    result = _node_agent(data, context, None)

    assert '计算结果是 4' in result['result']
    assert result['iterations_used'] == 2
    assert len(result['tool_calls']) == 1
    assert result['tool_calls'][0]['tool'] == 'calculator'
    print('[PASS] test_node_agent_with_tool_call')


@patch('engine.workflow_runner._call_llm')
def test_node_agent_max_iterations(mock_llm):
    """测试 Agent 节点达到最大迭代次数"""
    # 每次都返回 Action，直到达到最大迭代次数
    mock_llm.return_value = {
        'content': 'Action: calculator\nAction Input: 1 + 1',
        'total_tokens': 20
    }

    data = {
        'type': 'agent',
        'model': {'provider': 'deepseek', 'name': 'deepseek-v4-pro'},
        'prompt': '你是一个助手',
        'user_prompt': '请计算',
        'tools': [{'name': 'calculator', 'description': '计算器', 'type': 'calculator'}],
        'max_iterations': 3,
        'output': 'result'
    }
    context = {}

    result = _node_agent(data, context, None)

    assert '达到最大迭代次数' in result['result']
    assert result['iterations_used'] == 3
    print('[PASS] test_node_agent_max_iterations')


@patch('engine.workflow_runner._call_llm')
def test_node_agent_variable_replacement(mock_llm):
    """测试 Agent 节点变量替换"""
    mock_llm.return_value = {
        'content': 'Final Answer: 你好，张三！',
        'total_tokens': 30
    }

    data = {
        'type': 'agent',
        'model': {'provider': 'deepseek', 'name': 'deepseek-v4-pro'},
        'prompt': '你是一个助手',
        'user_prompt': '你好，{{name}}',
        'tools': [],
        'max_iterations': 3,
        'output': 'result'
    }
    context = {'name': '张三'}

    result = _node_agent(data, context, None)

    assert result['result'] == '你好，张三！'
    print('[PASS] test_node_agent_variable_replacement')


@patch('engine.workflow_runner._call_llm')
def test_node_agent_json_response(mock_llm):
    """测试 Agent 节点 JSON 格式响应"""
    mock_llm.side_effect = [
        {'content': '{"action": "calculator", "action_input": "6 * 7"}', 'total_tokens': 25},
        {'content': '{"final_answer": "42"}', 'total_tokens': 35}
    ]

    data = {
        'type': 'agent',
        'model': {'provider': 'deepseek', 'name': 'deepseek-v4-pro'},
        'prompt': '你是一个助手',
        'user_prompt': '请计算 6 * 7',
        'tools': [{'name': 'calculator', 'description': '计算器', 'type': 'calculator'}],
        'max_iterations': 5,
        'output': 'result'
    }
    context = {}

    result = _node_agent(data, context, None)

    assert result['result'] == '42'
    print('[PASS] test_node_agent_json_response')


def run_all_tests():
    """运行所有测试"""
    print('=' * 60)
    print('Agent 节点单元测试')
    print('=' * 60)

    # 响应解析测试
    test_parse_agent_response_final_answer()
    test_parse_agent_response_action()
    test_parse_agent_response_action_string_input()
    test_parse_agent_response_json_format()
    test_parse_agent_response_json_final_answer()
    test_parse_agent_response_unknown()
    test_parse_agent_response_empty()

    # 工具描述测试
    test_build_tool_descriptions()
    test_build_tool_descriptions_empty()

    # 计算器工具测试
    test_tool_calculator_basic()
    test_tool_calculator_complex()
    test_tool_calculator_power()
    test_tool_calculator_invalid_chars()
    test_tool_calculator_empty()

    # 代码工具测试
    test_tool_code_basic()
    test_tool_code_string()
    test_tool_code_list()
    test_tool_code_no_code()

    # 工具执行测试
    test_execute_agent_tool_not_found()
    test_execute_agent_tool_unsupported_type()

    # Agent 节点集成测试（使用 mock）
    test_node_agent_direct_answer()
    test_node_agent_with_tool_call()
    test_node_agent_max_iterations()
    test_node_agent_variable_replacement()
    test_node_agent_json_response()

    print('=' * 60)
    print('所有测试通过！')
    print('=' * 60)


if __name__ == '__main__':
    run_all_tests()
