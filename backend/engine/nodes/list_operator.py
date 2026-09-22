# -*- coding: utf-8 -*-
"""
列表操作节点执行模块

负责对列表数据进行操作，支持：
- 条件过滤（contains, not_contains, equals, not_equals, starts_with, ends_with, regex）
- 字段排序（升序/降序）
- 字段提取
- 数量限制
"""

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


def _node_list_operator(data, context, model_cfg=None):
    """
    List Operator 节点 —— 对列表数据进行操作。

    节点数据结构:
    - variable: 输入列表变量选择器 ["node_id", "variable"]
    - var_type: 变量类型（array[string], array[file], array[number]）
    - filter_by: 过滤条件 {enabled, key, value, operator}
    - sort_by: 排序条件 {enabled, key, value(asc/desc)}
    - limit: 限制数量
    - extract_by: 提取条件 {enabled, key, value}

    返回:
    - output: 处理后的列表
    """
    variable_selector = data.get('variable', [])
    var_type = data.get('var_type', 'array[string]')
    filter_by = data.get('filter_by', {})
    sort_by = data.get('sort_by', {})
    limit = data.get('limit', 0)
    extract_by = data.get('extract_by', {})

    # 获取输入列表
    items = _resolve_selector(context, variable_selector) if variable_selector else None
    if not items:
        return {'output': []}

    if not isinstance(items, list):
        items = [items]

    # 过滤
    if filter_by.get('enabled'):
        items = _apply_filter(items, filter_by, var_type)

    # 排序
    if sort_by.get('enabled'):
        items = _apply_sort(items, sort_by)

    # 提取
    if extract_by.get('enabled'):
        items = _apply_extract(items, extract_by)

    # 限制数量
    if limit and limit > 0:
        items = items[:limit]

    return {'output': items}


def _apply_filter(items, filter_by, var_type):
    """应用过滤条件"""
    key = filter_by.get('key', '')
    value = filter_by.get('value', '')
    operator = filter_by.get('operator', 'contains')

    result = []
    for item in items:
        # 获取要比较的字段值
        if isinstance(item, dict):
            field_value = str(item.get(key, ''))
        elif hasattr(item, key):
            field_value = str(getattr(item, key, ''))
        else:
            field_value = str(item)

        # 根据操作符比较
        match = False
        if operator == 'contains':
            match = value.lower() in field_value.lower()
        elif operator == 'not_contains':
            match = value.lower() not in field_value.lower()
        elif operator == 'equals':
            match = field_value.lower() == value.lower()
        elif operator == 'not_equals':
            match = field_value.lower() != value.lower()
        elif operator == 'starts_with':
            match = field_value.lower().startswith(value.lower())
        elif operator == 'ends_with':
            match = field_value.lower().endswith(value.lower())
        elif operator == 'regex':
            match = bool(re.search(value, field_value))

        if match:
            result.append(item)

    return result


def _apply_sort(items, sort_by):
    """应用排序条件"""
    key = sort_by.get('key', '')
    order = sort_by.get('value', 'asc')

    def sort_key(item):
        if isinstance(item, dict):
            return item.get(key, '')
        elif hasattr(item, key):
            return getattr(item, key, '')
        return str(item)

    try:
        sorted_items = sorted(items, key=sort_key, reverse=(order == 'desc'))
    except TypeError:
        sorted_items = items

    return sorted_items


def _apply_extract(items, extract_by):
    """应用提取条件"""
    key = extract_by.get('key', '')

    result = []
    for item in items:
        if isinstance(item, dict):
            if key in item:
                result.append(item[key])
        elif hasattr(item, key):
            result.append(getattr(item, key, ''))

    return result
