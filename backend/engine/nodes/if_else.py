# -*- coding: utf-8 -*-
"""
If-Else 条件分支节点执行模块

负责执行条件分支节点，支持：
- 多分支条件评估（AND 逻辑）
- 点号分隔的变量路径选择器（兼容 node 命名空间与裸变量名）
- 多种比较操作符（数值、字符串、正则）
- 兜底分支（最后一个分支）

分支句柄契约：输出的 `__branch__` 必须等于命中 case 的 id，
调度器（engine/graph_scheduler.py）据此匹配边的 sourceHandle；
前端 WfNode.vue 为每个 case 渲染 <Handle :id="case.id">，三者保持一致。
"""


def _branch_result(context, branch_id):
    """返回带分支决策的输出（仅返回决策相关变量，不返回整个上下文）。"""
    return {'__branch__': branch_id, '__if_else_branch__': branch_id}


def _node_ifelse(data, context, model_cfg=None):
    """
    条件分支节点 —— 评估条件并返回对应分支标识。

    节点数据结构:
    - cases: 分支列表 [{id, name, conditions: [{variable, operator, value}]}]

    每个分支的 conditions 之间是 AND 逻辑。
    分支按顺序评估，返回第一个满足条件的分支 id。
    如果都不满足，返回最后一个分支（兜底）。

    返回: {'__branch__': 命中的分支 id, '__if_else_branch__': 同上（历史兼容）}
    """
    cases = data.get('cases', [])
    if not cases:
        return {}

    for i, case in enumerate(cases):
        branch_id = str(case.get('id', i))
        conditions = case.get('conditions', [])
        if not conditions:
            # 没有条件的分支（如"否则"）作为兜底，只在最后生效
            if i == len(cases) - 1:
                return _branch_result(context, branch_id)
            continue
        if _evaluate_conditions(conditions, context):
            return _branch_result(context, branch_id)

    # 默认走最后一个分支（兜底）
    return _branch_result(context, str(cases[-1].get('id', 'default')))


def _evaluate_conditions(conditions, context):
    """
    评估条件列表（AND 逻辑）。
    所有条件都满足时返回 True。
    """
    if not conditions:
        return True
    return all(_evaluate_single_condition(c, context) for c in conditions)


def _evaluate_single_condition(condition, context):
    """
    评估单个条件。

    条件结构:
    - variable: 变量路径，支持点号分隔（如 "start.query" 或 "llm.output"）
    - operator: 操作符（equals, not_equals, contains, not_contains, starts_with, ends_with,
                       greater_than, less_than, greater_equal, less_equal, is_empty, is_not_empty, regex）
    - value: 比较值
    """
    variable = condition.get('variable', '')
    operator = condition.get('operator', 'equals')
    value = condition.get('value', '')

    # 从上下文获取变量值（点号路径 → 命名空间解析；否则读扁平别名）
    if isinstance(variable, list):
        actual_value = _resolve_selector(context, variable)
    elif '.' in str(variable):
        actual_value = _resolve_selector(context, str(variable).split('.'))
    else:
        actual_value = context.get(variable)

    if actual_value is None:
        actual_value = ''

    # 类型转换和比较
    return _compare_values(actual_value, operator, value)


def _compare_values(actual, operator, expected):
    """
    比较值。支持多种操作符。

    参数:
    - actual: 实际值（来自上下文）
    - operator: 操作符
    - expected: 期望值（来自条件配置）
    """
    # 数值比较操作符（兼容符号与英文两种写法，前端/旧数据可能混用）
    numeric_operators = {'greater_than', 'less_than', 'greater_equal', 'less_equal',
                         '>', '<', '>=', '<='}
    alias = {'>': 'greater_than', '<': 'less_than',
             '>=': 'greater_equal', '<=': 'less_equal'}
    if operator in alias:
        operator = alias[operator]

    if operator in numeric_operators:
        try:
            actual_num = float(actual) if not isinstance(actual, (int, float)) else actual
            expected_num = float(expected)
            operators = {
                'greater_than': lambda a, e: a > e,
                'less_than': lambda a, e: a < e,
                'greater_equal': lambda a, e: a >= e,
                'less_equal': lambda a, e: a <= e,
            }
            return operators.get(operator, lambda a, e: False)(actual_num, expected_num)
        except (ValueError, TypeError):
            return False

    # 字符串比较操作符
    actual_str = str(actual)
    expected_str = str(expected)

    import re
    operators = {
        'equals': lambda a, e: a == e,
        'not_equals': lambda a, e: a != e,
        'contains': lambda a, e: e in a,
        'not_contains': lambda a, e: e not in a,
        'starts_with': lambda a, e: a.startswith(e),
        'ends_with': lambda a, e: a.endswith(e),
        'is_empty': lambda a, e: not a or a.strip() == '',
        'is_not_empty': lambda a, e: bool(a and a.strip()),
        'regex': lambda a, e: bool(re.search(e, a)),
    }

    return operators.get(operator, lambda a, e: False)(actual_str, expected_str)


def _resolve_selector(context, selector):
    """
    根据选择器路径从上下文中获取变量值。

    支持三种写法：
    - ['node_id', 'var'] / 'node_id.var'：node 命名空间路径
    - 'var'：裸变量名（扁平别名，向后兼容）
    - 首段不是上下文键时，退回全局查找
    """
    if not selector:
        return None
    if isinstance(selector, str):
        selector = [part for part in selector.split('.') if part != '']

    value = context
    for key in selector:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None
        if value is None:
            return None
    return value
