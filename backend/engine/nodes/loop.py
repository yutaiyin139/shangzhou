# -*- coding: utf-8 -*-
"""
循环节点（Loop）实现

基于条件或次数的循环执行，支持:
- 按次数循环（count）
- 按条件循环（condition）
- 无限循环（直到 break）

通过子图方式执行循环体，返回每次迭代的结果列表与循环计数。
"""

def _node_loop(data, context, model_cfg):
    """
    循环节点（Loop）

    基于条件或次数的循环执行，支持:
    - 按次数循环（count）
    - 按条件循环（condition）
    - 无限循环（直到 break）

    节点数据结构:
    - loop_type: "count"（次数）| "condition"（条件）| "infinite"（无限）
    - max_iterations: 最大迭代次数（安全限制，默认 100）
    - count: 循环次数（loop_type=count 时）
    - condition: 循环继续条件（loop_type=condition 时）
      - variable: 条件变量选择器
      - operator: 比较操作符
      - value: 比较值
    - output_variable: 循环输出变量名

    返回:
        循环结果 {output_variable: [result1, result2, ...], loop_count: N}
    """
    loop_type = data.get('loop_type', 'count')
    max_iterations = data.get('max_iterations', 100)
    output_variable = data.get('output_variable', 'loop_results')

    all_results = []
    loop_count = 0

    if loop_type == 'count':
        # 按次数循环
        count = data.get('count', 0)
        if not isinstance(count, int) or count < 0:
            raise Exception(f'循环次数必须是非负整数，当前值: {count}')

        if count > max_iterations:
            raise Exception(f'循环次数超过限制 {max_iterations}，当前 {count} 次')

        for idx in range(count):
            # 更新循环上下文
            context['_loop'] = {
                'index': idx,
                'count': count,
                'is_first': idx == 0,
                'is_last': idx == count - 1,
            }
            # 执行循环体（这里返回当前迭代的结果）
            result = _execute_loop_body(data, context, model_cfg, idx)
            all_results.append(result)
            loop_count = idx + 1

    elif loop_type == 'condition':
        # 按条件循环
        # _resolve_selector and _compare_values are defined locally in this module
        condition = data.get('condition', {})
        var_selector = condition.get('variable', [])
        operator = condition.get('operator', 'equals')
        expected_value = condition.get('value', '')

        for idx in range(max_iterations):
            # 更新循环上下文
            context['_loop'] = {
                'index': idx,
                'count': max_iterations,
                'is_first': idx == 0,
                'is_last': False,
            }

            # 检查循环条件
            actual_value = _resolve_selector(context, var_selector) if var_selector else None
            if not _compare_values(str(actual_value), operator, str(expected_value)):
                # 条件不满足，退出循环
                loop_count = idx
                break

            # 执行循环体
            result = _execute_loop_body(data, context, model_cfg, idx)
            all_results.append(result)
            loop_count = idx + 1
        else:
            # 达到最大迭代次数
            raise Exception(f'循环达到最大迭代次数限制 {max_iterations}')

    elif loop_type == 'infinite':
        # 无限循环（需要内部 break）
        for idx in range(max_iterations):
            context['_loop'] = {
                'index': idx,
                'count': max_iterations,
                'is_first': idx == 0,
                'is_last': False,
            }

            result = _execute_loop_body(data, context, model_cfg, idx)
            all_results.append(result)

            # 检查是否 break
            if isinstance(result, dict) and result.get('_loop_break'):
                loop_count = idx + 1
                break

            loop_count = idx + 1
        else:
            raise Exception(f'无限循环达到最大迭代次数限制 {max_iterations}')

    else:
        raise Exception(f'不支持的循环类型: {loop_type}')

    # 清理循环上下文
    context.pop('_loop', None)

    return {
        output_variable: all_results,
        'loop_count': loop_count,
        'loop_results': all_results,
    }


def _execute_loop_body(data, context, model_cfg, iteration_index):
    """
    执行循环体

    循环体通过子图方式执行，类似于迭代节点的子流程。
    这里简化为返回当前上下文中的变量值。

    在实际实现中，循环体可以通过子图节点连接来定义。
    """
    # 获取循环体输出配置
    output_selector = data.get('output_selector', [])
    if output_selector:
        result = {}
        for sel in output_selector:
            key = sel if isinstance(sel, str) else sel.get('variable', '')
            if key and key in context:
                result[key] = context[key]
        return result

    # 默认返回整个上下文（去除内部变量）
    return {k: v for k, v in context.items() if not k.startswith('_') and not k.startswith('__')}


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


def _compare_values(actual, operator, expected):
    """比较两个值，用于条件循环"""
    if operator == 'equals':
        return actual == expected
    elif operator == 'not_equals':
        return actual != expected
    elif operator == 'contains':
        return expected in actual
    elif operator == 'not_contains':
        return expected not in actual
    elif operator == 'empty':
        return actual == '' or actual == 'None' or actual is None
    elif operator == 'not_empty':
        return actual != '' and actual != 'None' and actual is not None
    elif operator == 'gt':
        try:
            return float(actual) > float(expected)
        except Exception:
            return False
    elif operator == 'gte':
        try:
            return float(actual) >= float(expected)
        except Exception:
            return False
    elif operator == 'lt':
        try:
            return float(actual) < float(expected)
        except Exception:
            return False
    elif operator == 'lte':
        try:
            return float(actual) <= float(expected)
        except Exception:
            return False
    return False
