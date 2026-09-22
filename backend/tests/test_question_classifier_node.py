# -*- coding: utf-8 -*-
"""
Question Classifier 节点单元测试
测试问题分类节点的核心逻辑：LLM 分类、结果解析
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock
from engine.workflow_runner import _node_question_classifier


def _make_model_cfg():
    """创建测试用的模型配置"""
    return {
        'model': '{"name": "gpt-4o-mini", "provider": "openai"}'
    }


def _make_classes():
    """创建测试用的分类类别"""
    return [
        {
            'id': '1',
            'label': '技术支持',
            'name': '包括系统故障、软件安装、网络连接、密码重置等技术问题'
        },
        {
            'id': '2',
            'label': '销售咨询',
            'name': '包括产品报价、购买流程、合同条款等销售相关问题'
        },
        {
            'id': '3',
            'label': '投诉建议',
            'name': '包括用户投诉、产品建议、服务反馈等'
        },
    ]


def test_classifier_empty_query():
    """测试空查询返回 None"""
    data = {
        'type': 'question-classifier',
        'query_variable_selector': ['start', 'query'],
        'classes': _make_classes(),
        'output': 'classification',
    }
    context = {'start': {'query': ''}}

    result = _node_question_classifier(data, context, None)

    assert result.get('class_id') is None
    assert result.get('class_index') == -1
    print('[PASS] test_classifier_empty_query')


def test_classifier_empty_classes():
    """测试空类别列表返回 None"""
    data = {
        'type': 'question-classifier',
        'query_variable_selector': ['start', 'query'],
        'classes': [],
        'output': 'classification',
    }
    context = {'start': {'query': '我的电脑无法开机了'}}

    result = _node_question_classifier(data, context, None)

    assert result.get('class_id') is None
    assert result.get('class_index') == -1
    print('[PASS] test_classifier_empty_classes')


def test_classifier_default_output_var():
    """测试默认输出变量名"""
    data = {
        'type': 'question-classifier',
        'query_variable_selector': ['start', 'query'],
        'classes': _make_classes(),
    }
    context = {'start': {'query': 'test'}}

    # 验证默认输出变量名
    assert data.get('output', 'classification') == 'classification'
    print('[PASS] test_classifier_default_output_var')


def test_classifier_with_mocked_llm():
    """测试使用 Mock LLM 进行分类"""
    data = {
        'type': 'question-classifier',
        'query_variable_selector': ['start', 'query'],
        'classes': _make_classes(),
        'output': 'classification',
    }
    context = {'start': {'query': '我的电脑无法开机了，屏幕不亮'}}

    # Mock _call_llm 函数
    mock_response = {
        'content': '类别ID: 1\n类别名称: 技术支持'
    }

    with patch('engine.workflow_runner._call_llm', return_value=mock_response):
        with patch('engine.workflow_runner.get_db') as mock_db:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'api_key': 'test-key',
                'api_base_url': 'https://api.openai.com',
                'model_name': 'gpt-4o-mini',
                'credential_name': 'openai',
                'provider': 'openai',
            }
            mock_db.return_value.cursor.return_value = mock_cursor

            result = _node_question_classifier(data, context, _make_model_cfg())

    assert result.get('class_id') == '1'
    assert result.get('class_label') == '技术支持'
    assert result.get('class_index') == 0
    assert result.get('classification', {}).get('class_id') == '1'
    print('[PASS] test_classifier_with_mocked_llm')


def test_classifier_sales_category():
    """测试分类到销售类别"""
    data = {
        'type': 'question-classifier',
        'query_variable_selector': ['start', 'query'],
        'classes': _make_classes(),
        'output': 'result',
    }
    context = {'start': {'query': '请问你们的产品怎么卖？有什么优惠？'}}

    mock_response = {
        'content': '类别ID: 2\n类别名称: 销售咨询'
    }

    with patch('engine.workflow_runner._call_llm', return_value=mock_response):
        with patch('engine.workflow_runner.get_db') as mock_db:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'api_key': 'test-key',
                'api_base_url': 'https://api.openai.com',
                'model_name': 'gpt-4o-mini',
                'credential_name': 'openai',
                'provider': 'openai',
            }
            mock_db.return_value.cursor.return_value = mock_cursor

            result = _node_question_classifier(data, context, _make_model_cfg())

    assert result.get('class_id') == '2'
    assert result.get('class_label') == '销售咨询'
    assert result.get('class_index') == 1
    assert result.get('result', {}).get('class_id') == '2'
    print('[PASS] test_classifier_sales_category')


def test_classifier_complaint_category():
    """测试分类到投诉类别"""
    data = {
        'type': 'question-classifier',
        'query_variable_selector': ['start', 'query'],
        'classes': _make_classes(),
        'output': 'classification',
    }
    context = {'start': {'query': '你们的服务太差了，我要投诉！'}}

    mock_response = {
        'content': '类别ID: 3\n类别名称: 投诉建议'
    }

    with patch('engine.workflow_runner._call_llm', return_value=mock_response):
        with patch('engine.workflow_runner.get_db') as mock_db:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'api_key': 'test-key',
                'api_base_url': 'https://api.openai.com',
                'model_name': 'gpt-4o-mini',
                'credential_name': 'openai',
                'provider': 'openai',
            }
            mock_db.return_value.cursor.return_value = mock_cursor

            result = _node_question_classifier(data, context, _make_model_cfg())

    assert result.get('class_id') == '3'
    assert result.get('class_label') == '投诉建议'
    assert result.get('class_index') == 2
    print('[PASS] test_classifier_complaint_category')


def test_classifier_fallback_matching():
    """测试回退匹配（响应中只包含类别标签）"""
    data = {
        'type': 'question-classifier',
        'query_variable_selector': ['start', 'query'],
        'classes': _make_classes(),
        'output': 'classification',
    }
    context = {'start': {'query': '产品报价是多少？'}}

    # LLM 返回格式不规范，只包含类别名称
    mock_response = {
        'content': '这个问题属于销售咨询类别'
    }

    with patch('engine.workflow_runner._call_llm', return_value=mock_response):
        with patch('engine.workflow_runner.get_db') as mock_db:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'api_key': 'test-key',
                'api_base_url': 'https://api.openai.com',
                'model_name': 'gpt-4o-mini',
                'credential_name': 'openai',
                'provider': 'openai',
            }
            mock_db.return_value.cursor.return_value = mock_cursor

            result = _node_question_classifier(data, context, _make_model_cfg())

    # 回退匹配应该能找到 "销售咨询"
    assert result.get('class_id') == '2'
    assert result.get('class_label') == '销售咨询'
    print('[PASS] test_classifier_fallback_matching')


def test_classifier_custom_output_var():
    """测试自定义输出变量名"""
    data = {
        'type': 'question-classifier',
        'query_variable_selector': ['start', 'query'],
        'classes': _make_classes(),
        'output': 'my_category',
    }
    context = {'start': {'query': '网络连接有问题'}}

    mock_response = {
        'content': '类别ID: 1\n类别名称: 技术支持'
    }

    with patch('engine.workflow_runner._call_llm', return_value=mock_response):
        with patch('engine.workflow_runner.get_db') as mock_db:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'api_key': 'test-key',
                'api_base_url': 'https://api.openai.com',
                'model_name': 'gpt-4o-mini',
                'credential_name': 'openai',
                'provider': 'openai',
            }
            mock_db.return_value.cursor.return_value = mock_cursor

            result = _node_question_classifier(data, context, _make_model_cfg())

    # 验证使用自定义输出变量名
    assert 'my_category' in result
    assert result['my_category']['class_id'] == '1'
    print('[PASS] test_classifier_custom_output_var')


def test_classifier_raw_response_included():
    """测试结果中包含原始响应"""
    data = {
        'type': 'question-classifier',
        'query_variable_selector': ['start', 'query'],
        'classes': _make_classes(),
        'output': 'classification',
    }
    context = {'start': {'query': 'test query'}}

    mock_response = {
        'content': '类别ID: 1\n类别名称: 技术支持\n这是原始响应内容'
    }

    with patch('engine.workflow_runner._call_llm', return_value=mock_response):
        with patch('engine.workflow_runner.get_db') as mock_db:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'api_key': 'test-key',
                'api_base_url': 'https://api.openai.com',
                'model_name': 'gpt-4o-mini',
                'credential_name': 'openai',
                'provider': 'openai',
            }
            mock_db.return_value.cursor.return_value = mock_cursor

            result = _node_question_classifier(data, context, _make_model_cfg())

    assert 'raw_response' in result
    assert '类别ID: 1' in result['raw_response']
    print('[PASS] test_classifier_raw_response_included')


def test_classifier_two_classes():
    """测试只有两个类别的分类"""
    data = {
        'type': 'question-classifier',
        'query_variable_selector': ['start', 'query'],
        'classes': [
            {'id': 'yes', 'label': '是', 'name': '用户确认、同意、肯定的回答'},
            {'id': 'no', 'label': '否', 'name': '用户拒绝、否定、不同意的回答'},
        ],
        'output': 'classification',
    }
    context = {'start': {'query': '是的，我同意'}}

    mock_response = {
        'content': '类别ID: yes\n类别名称: 是'
    }

    with patch('engine.workflow_runner._call_llm', return_value=mock_response):
        with patch('engine.workflow_runner.get_db') as mock_db:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'api_key': 'test-key',
                'api_base_url': 'https://api.openai.com',
                'model_name': 'gpt-4o-mini',
                'credential_name': 'openai',
                'provider': 'openai',
            }
            mock_db.return_value.cursor.return_value = mock_cursor

            result = _node_question_classifier(data, context, _make_model_cfg())

    assert result.get('class_id') == 'yes'
    assert result.get('class_label') == '是'
    assert result.get('class_index') == 0
    print('[PASS] test_classifier_two_classes')


def test_classifier_class_name_in_output():
    """测试输出包含类别描述"""
    data = {
        'type': 'question-classifier',
        'query_variable_selector': ['start', 'query'],
        'classes': _make_classes(),
        'output': 'classification',
    }
    context = {'start': {'query': '我要买你们的产品'}}

    mock_response = {
        'content': '类别ID: 2\n类别名称: 销售咨询'
    }

    with patch('engine.workflow_runner._call_llm', return_value=mock_response):
        with patch('engine.workflow_runner.get_db') as mock_db:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'api_key': 'test-key',
                'api_base_url': 'https://api.openai.com',
                'model_name': 'gpt-4o-mini',
                'credential_name': 'openai',
                'provider': 'openai',
            }
            mock_db.return_value.cursor.return_value = mock_cursor

            result = _node_question_classifier(data, context, _make_model_cfg())

    assert result.get('class_name') == '包括产品报价、购买流程、合同条款等销售相关问题'
    print('[PASS] test_classifier_class_name_in_output')


def run_all_tests():
    """运行所有测试"""
    print('=' * 60)
    print('Question Classifier 节点单元测试')
    print('=' * 60)

    test_classifier_empty_query()
    test_classifier_empty_classes()
    test_classifier_default_output_var()
    test_classifier_with_mocked_llm()
    test_classifier_sales_category()
    test_classifier_complaint_category()
    test_classifier_fallback_matching()
    test_classifier_custom_output_var()
    test_classifier_raw_response_included()
    test_classifier_two_classes()
    test_classifier_class_name_in_output()

    print('=' * 60)
    print('所有测试通过！')
    print('=' * 60)


if __name__ == '__main__':
    run_all_tests()
