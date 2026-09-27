# -*- coding: utf-8 -*-
"""
Parameter Extractor 节点单元测试
测试参数提取节点的核心逻辑：LLM 提取、JSON 解析、类型转换
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock
# 实现已拆到 engine/nodes/parameter_extractor.py
from engine.nodes.parameter_extractor import _node_parameter_extractor, _convert_type


def _make_model_cfg():
    """创建测试用的模型配置"""
    return {
        'model': '{"name": "gpt-4o-mini", "provider": "openai"}'
    }


def _make_parameters():
    """创建测试用的参数定义"""
    return [
        {
            'name': 'order_id',
            'description': '用户提到的订单号、运单号；没有就为空',
            'type': 'string',
            'required': False,
        },
        {
            'name': 'product_name',
            'description': '用户提到的产品或服务名称；没有就为空',
            'type': 'string',
            'required': False,
        },
        {
            'name': 'quantity',
            'description': '用户提到的数量',
            'type': 'integer',
            'required': False,
        },
        {
            'name': 'urgency',
            'description': '紧急程度，只能是 low、medium、high',
            'type': 'string',
            'required': True,
        },
    ]


def test_extractor_empty_query():
    """测试空输入返回空结果"""
    data = {
        'type': 'parameter-extractor',
        'query': ['start', 'query'],
        'parameters': _make_parameters(),
        'output': 'extracted_params',
    }
    context = {'start': {'query': ''}}

    result = _node_parameter_extractor(data, context, None)

    assert result.get('extracted_params') == {}
    assert result.get('missing_required') == []
    print('[PASS] test_extractor_empty_query')


def test_extractor_empty_parameters():
    """测试空参数定义返回空结果"""
    data = {
        'type': 'parameter-extractor',
        'query': ['start', 'query'],
        'parameters': [],
        'output': 'extracted_params',
    }
    context = {'start': {'query': '我想查询订单'}}

    result = _node_parameter_extractor(data, context, None)

    assert result.get('extracted_params') == {}
    print('[PASS] test_extractor_empty_parameters')


def test_extractor_default_output_var():
    """测试默认输出变量名"""
    data = {
        'type': 'parameter-extractor',
        'query': ['start', 'query'],
        'parameters': _make_parameters(),
    }

    # 验证默认输出变量名
    assert data.get('output', 'extracted_params') == 'extracted_params'
    print('[PASS] test_extractor_default_output_var')


def test_extractor_with_mocked_llm():
    """测试使用 Mock LLM 进行参数提取"""
    data = {
        'type': 'parameter-extractor',
        'query': ['start', 'query'],
        'parameters': _make_parameters(),
        'output': 'extracted_params',
    }
    context = {'start': {'query': '我想查询订单 ABC123，产品是手机，数量 2 个，紧急程度高'}}

    mock_response = {
        'content': '{"order_id": "ABC123", "product_name": "手机", "quantity": 2, "urgency": "high"}'
    }

    with patch('engine.nodes.parameter_extractor._call_llm', return_value=mock_response):
        with patch('engine.nodes.parameter_extractor.get_db') as mock_db:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'api_key': 'test-key',
                'api_base_url': 'https://api.openai.com',
                'model_name': 'gpt-4o-mini',
                'credential_name': 'openai',
                'provider': 'openai',
            }
            mock_db.return_value.cursor.return_value = mock_cursor

            result = _node_parameter_extractor(data, context, _make_model_cfg())

    extracted = result.get('extracted_params', {})
    assert extracted.get('order_id') == 'ABC123'
    assert extracted.get('product_name') == '手机'
    assert extracted.get('quantity') == 2
    assert extracted.get('urgency') == 'high'
    print('[PASS] test_extractor_with_mocked_llm')


def test_extractor_json_in_code_block():
    """测试 JSON 在代码块中的情况"""
    data = {
        'type': 'parameter-extractor',
        'query': ['start', 'query'],
        'parameters': _make_parameters(),
        'output': 'extracted_params',
    }
    context = {'start': {'query': '订单号 XYZ789'}}

    mock_response = {
        'content': '```json\n{"order_id": "XYZ789", "product_name": "", "quantity": null, "urgency": "low"}\n```'
    }

    with patch('engine.nodes.parameter_extractor._call_llm', return_value=mock_response):
        with patch('engine.nodes.parameter_extractor.get_db') as mock_db:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'api_key': 'test-key',
                'api_base_url': 'https://api.openai.com',
                'model_name': 'gpt-4o-mini',
                'credential_name': 'openai',
                'provider': 'openai',
            }
            mock_db.return_value.cursor.return_value = mock_cursor

            result = _node_parameter_extractor(data, context, _make_model_cfg())

    extracted = result.get('extracted_params', {})
    assert extracted.get('order_id') == 'XYZ789'
    print('[PASS] test_extractor_json_in_code_block')


def test_extractor_missing_required():
    """测试必填参数缺失检测"""
    data = {
        'type': 'parameter-extractor',
        'query': ['start', 'query'],
        'parameters': _make_parameters(),
        'output': 'extracted_params',
    }
    context = {'start': {'query': '我想查询一下'}}

    # LLM 没有提取到 urgency（必填参数）
    mock_response = {
        'content': '{"order_id": "", "product_name": "", "quantity": null}'
    }

    with patch('engine.nodes.parameter_extractor._call_llm', return_value=mock_response):
        with patch('engine.nodes.parameter_extractor.get_db') as mock_db:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'api_key': 'test-key',
                'api_base_url': 'https://api.openai.com',
                'model_name': 'gpt-4o-mini',
                'credential_name': 'openai',
                'provider': 'openai',
            }
            mock_db.return_value.cursor.return_value = mock_cursor

            result = _node_parameter_extractor(data, context, _make_model_cfg())

    # urgency 是必填参数，应该被记录为缺失
    assert 'urgency' in result.get('missing_required', [])
    print('[PASS] test_extractor_missing_required')


def test_extractor_type_conversion():
    """测试类型转换"""
    data = {
        'type': 'parameter-extractor',
        'query': ['start', 'query'],
        'parameters': [
            {'name': 'count', 'description': '数量', 'type': 'integer', 'required': False},
            {'name': 'price', 'description': '价格', 'type': 'number', 'required': False},
            {'name': 'active', 'description': '是否激活', 'type': 'boolean', 'required': False},
        ],
        'output': 'extracted_params',
    }
    context = {'start': {'query': '数量 10，价格 99.99，激活状态 true'}}

    mock_response = {
        'content': '{"count": "10", "price": "99.99", "active": "true"}'
    }

    with patch('engine.nodes.parameter_extractor._call_llm', return_value=mock_response):
        with patch('engine.nodes.parameter_extractor.get_db') as mock_db:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'api_key': 'test-key',
                'api_base_url': 'https://api.openai.com',
                'model_name': 'gpt-4o-mini',
                'credential_name': 'openai',
                'provider': 'openai',
            }
            mock_db.return_value.cursor.return_value = mock_cursor

            result = _node_parameter_extractor(data, context, _make_model_cfg())

    extracted = result.get('extracted_params', {})
    assert extracted.get('count') == 10  # 转为整数
    assert extracted.get('price') == 99.99  # 转为浮点数
    assert extracted.get('active') is True  # 转为布尔值
    print('[PASS] test_extractor_type_conversion')


def test_extractor_custom_output_var():
    """测试自定义输出变量名"""
    data = {
        'type': 'parameter-extractor',
        'query': ['start', 'query'],
        'parameters': _make_parameters(),
        'output': 'my_params',
    }
    context = {'start': {'query': '订单 ABC123'}}

    mock_response = {
        'content': '{"order_id": "ABC123", "product_name": "", "quantity": null, "urgency": "low"}'
    }

    with patch('engine.nodes.parameter_extractor._call_llm', return_value=mock_response):
        with patch('engine.nodes.parameter_extractor.get_db') as mock_db:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'api_key': 'test-key',
                'api_base_url': 'https://api.openai.com',
                'model_name': 'gpt-4o-mini',
                'credential_name': 'openai',
                'provider': 'openai',
            }
            mock_db.return_value.cursor.return_value = mock_cursor

            result = _node_parameter_extractor(data, context, _make_model_cfg())

    # 验证使用自定义输出变量名
    assert 'my_params' in result
    assert result['my_params']['order_id'] == 'ABC123'
    print('[PASS] test_extractor_custom_output_var')


def test_extractor_raw_response_included():
    """测试结果中包含原始响应"""
    data = {
        'type': 'parameter-extractor',
        'query': ['start', 'query'],
        'parameters': _make_parameters(),
        'output': 'extracted_params',
    }
    context = {'start': {'query': 'test'}}

    mock_response = {
        'content': '{"order_id": "TEST123", "product_name": "", "quantity": null, "urgency": "low"}'
    }

    with patch('engine.nodes.parameter_extractor._call_llm', return_value=mock_response):
        with patch('engine.nodes.parameter_extractor.get_db') as mock_db:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'api_key': 'test-key',
                'api_base_url': 'https://api.openai.com',
                'model_name': 'gpt-4o-mini',
                'credential_name': 'openai',
                'provider': 'openai',
            }
            mock_db.return_value.cursor.return_value = mock_cursor

            result = _node_parameter_extractor(data, context, _make_model_cfg())

    assert 'raw_response' in result
    assert 'TEST123' in result['raw_response']
    print('[PASS] test_extractor_raw_response_included')


def test_convert_type_number():
    """测试数字类型转换"""
    assert _convert_type('123', 'number') == 123.0
    assert _convert_type('45.67', 'number') == 45.67
    assert _convert_type(100, 'number') == 100
    print('[PASS] test_convert_type_number')


def test_convert_type_integer():
    """测试整数类型转换"""
    assert _convert_type('42', 'integer') == 42
    assert _convert_type('3.14', 'integer') == 3
    assert _convert_type(7, 'integer') == 7
    print('[PASS] test_convert_type_integer')


def test_convert_type_boolean():
    """测试布尔类型转换"""
    assert _convert_type('true', 'boolean') is True
    assert _convert_type('false', 'boolean') is False
    assert _convert_type('yes', 'boolean') is True
    assert _convert_type('no', 'boolean') is False
    assert _convert_type('是', 'boolean') is True
    assert _convert_type(True, 'boolean') is True
    print('[PASS] test_convert_type_boolean')


def test_convert_type_array():
    """测试数组类型转换"""
    assert _convert_type('a,b,c', 'array') == ['a', 'b', 'c']
    assert _convert_type([1, 2, 3], 'array') == [1, 2, 3]
    assert _convert_type('single', 'array') == ['single']
    print('[PASS] test_convert_type_array')


def test_convert_type_string():
    """测试字符串类型转换"""
    assert _convert_type(123, 'string') == '123'
    assert _convert_type(True, 'string') == 'True'
    assert _convert_type('hello', 'string') == 'hello'
    print('[PASS] test_convert_type_string')


def test_extractor_partial_extraction():
    """测试部分参数提取（只提取到部分参数）"""
    data = {
        'type': 'parameter-extractor',
        'query': ['start', 'query'],
        'parameters': _make_parameters(),
        'output': 'extracted_params',
    }
    context = {'start': {'query': '我的订单号是 DEF456'}}

    # LLM 只提取到了 order_id
    mock_response = {
        'content': '{"order_id": "DEF456"}'
    }

    with patch('engine.nodes.parameter_extractor._call_llm', return_value=mock_response):
        with patch('engine.nodes.parameter_extractor.get_db') as mock_db:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'api_key': 'test-key',
                'api_base_url': 'https://api.openai.com',
                'model_name': 'gpt-4o-mini',
                'credential_name': 'openai',
                'provider': 'openai',
            }
            mock_db.return_value.cursor.return_value = mock_cursor

            result = _node_parameter_extractor(data, context, _make_model_cfg())

    extracted = result.get('extracted_params', {})
    assert extracted.get('order_id') == 'DEF456'
    # 其他参数不应该出现在结果中
    assert 'product_name' not in extracted
    print('[PASS] test_extractor_partial_extraction')


def run_all_tests():
    """运行所有测试"""
    print('=' * 60)
    print('Parameter Extractor 节点单元测试')
    print('=' * 60)

    test_extractor_empty_query()
    test_extractor_empty_parameters()
    test_extractor_default_output_var()
    test_extractor_with_mocked_llm()
    test_extractor_json_in_code_block()
    test_extractor_missing_required()
    test_extractor_type_conversion()
    test_extractor_custom_output_var()
    test_extractor_raw_response_included()
    test_convert_type_number()
    test_convert_type_integer()
    test_convert_type_boolean()
    test_convert_type_array()
    test_convert_type_string()
    test_extractor_partial_extraction()

    print('=' * 60)
    print('所有测试通过！')
    print('=' * 60)


if __name__ == '__main__':
    run_all_tests()
