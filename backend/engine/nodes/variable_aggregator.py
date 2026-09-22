# -*- coding: utf-8 -*-
"""
Variable Aggregator 变量聚合节点执行模块

负责将多个变量聚合为一个输出，支持：
- 聚合为对象（object）：{var_name: value, ...}
- 聚合为数组（array）：[value1, value2, ...]
- 聚合为字符串（string）：使用分隔符拼接
- 支持值选择器（value_selector）从上下文中取值
- 支持默认值（default）兜底
"""


def _node_variable_aggregator(data, context, model_cfg):
    """
    Variable Aggregator 节点 —— 聚合多个变量为一个输出。

    用于合并来自多个分支（如 if-else、并行分支）的变量。

    节点数据结构:
    - variables: 要聚合的变量列表 [{variable: "var_name", value_selector: ["node", "output"]}]
    - output_type: 输出类型（object/array/string）
    - output: 输出变量名（默认 'aggregated_output'）
    """
    variables = data.get('variables', [])
    output_type = data.get('output_type', 'object')
    output_var = data.get('output', 'aggregated_output')

    if not variables:
        return {output_var: {}}

    if output_type == 'object':
        # 聚合为对象 {var_name: value}
        result = {}
        for v in variables:
            var_name = v.get('variable', '')
            value_selector = v.get('value_selector', [])
            if not value_selector and var_name:
                value_selector = [var_name]

            # 从上下文中获取值
            value = _resolve_selector(context, value_selector)
            if value is None:
                value = v.get('default', '')
            result[var_name] = value
        return {output_var: result, 'aggregated': result}

    elif output_type == 'array':
        # 聚合为数组 [value1, value2, ...]
        result = []
        for v in variables:
            value_selector = v.get('value_selector', [])
            var_name = v.get('variable', '')
            if not value_selector and var_name:
                value_selector = [var_name]

            value = _resolve_selector(context, value_selector)
            if value is None:
                value = v.get('default', '')
            result.append(value)
        return {output_var: result, 'aggregated': result}

    elif output_type == 'string':
        # 字符串拼接
        parts = []
        separator = data.get('separator', ', ')
        for v in variables:
            value_selector = v.get('value_selector', [])
            var_name = v.get('variable', '')
            if not value_selector and var_name:
                value_selector = [var_name]

            value = _resolve_selector(context, value_selector)
            if value is None:
                value = v.get('default', '')
            parts.append(str(value))
        result = separator.join(parts)
        return {output_var: result, 'aggregated': result}

    else:
        return {output_var: {}}


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
