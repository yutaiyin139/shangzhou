# -*- coding: utf-8 -*-
"""
模板转换节点执行模块

负责使用模板转换数据，支持：
- {{variable}} 语法的变量替换
- {{#node.variable#}} 语法的直接变量引用
- 列表/字典的 JSON 格式化输出
"""

import json
import re


def _resolve_selector(context, selector):
    """根据选择器路径从上下文中获取变量值"""
    if not selector:
        return None
    if isinstance(selector, str):
        selector = [selector]

    value = context
    for key in selector:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None
        if value is None:
            return None
    return value


def _node_template_transform(data, context, model_cfg=None):
    """
    Template Transform 节点 —— 使用模板转换数据。

    节点数据结构:
    - template: 模板字符串，支持 {{variable}} 语法
    - variables: 变量列表 [{variable, value_selector, value_type}]

    返回:
    - output: 转换后的文本
    """
    template = data.get('template', '')
    variables = data.get('variables', [])

    if not template:
        return {'output': ''}

    result = template

    # 先处理 variables 中定义的变量
    for var in variables:
        var_name = var.get('variable', '')
        value_selector = var.get('value_selector', [])
        if not var_name:
            continue

        value = _resolve_selector(context, value_selector) if value_selector else ''
        if value is None:
            value = ''

        # 处理列表/字典的格式化
        if isinstance(value, (list, dict)):
            value = json.dumps(value, ensure_ascii=False, indent=2)

        result = result.replace('{{' + var_name + '}}', str(value))

    # 再处理模板中剩余的直接变量引用 {{#node.variable#}}
    pattern = r'\{\{#(.+?)#\}\}'
    for match in re.finditer(pattern, result):
        selector_str = match.group(1)
        parts = selector_str.split('.')
        value = _resolve_selector(context, parts)
        if value is not None:
            result = result.replace(match.group(0), str(value))

    return {'output': result}
