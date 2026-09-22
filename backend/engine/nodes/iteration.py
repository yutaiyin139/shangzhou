# -*- coding: utf-8 -*-
"""
迭代节点（Iterator）实现

对输入列表中的每个元素执行子流程，收集所有结果后返回。
支持顺序执行模式，预留并行执行接口。
"""

import json
from collections import deque


def _node_iteration(data, context, model_cfg):
    """
    迭代节点（Iterator）
    对输入列表中的每个元素执行子流程，收集所有结果后返回。

    节点数据结构:
    - input_selector: 输入列表的变量路径，如 ["start", "items"]
    - output_selector: 输出变量配置
    - iteration_mode: "sequential"（顺序）或 "parallel"（并行，预留）
    - max_iterations: 最大迭代次数（安全限制）

    图结构约定:
    - 迭代节点的 "loop" 输出口连接子流程的起始节点
    - 子流程的末尾节点连接回迭代节点的 "element" 入口（通过 edge 的 sourceHandle）
    - 迭代节点的 "end" 输出口连接迭代结束后的下一个节点
    """
    # 获取输入列表
    input_selector = data.get('input_selector', [])
    if not input_selector:
        return {'output': [], 'iteration_results': []}

    # 从上下文中获取列表值
    input_list = _resolve_selector(context, input_selector)
    if not isinstance(input_list, list):
        # 尝试解析 JSON 字符串
        try:
            if isinstance(input_list, str):
                input_list = json.loads(input_list)
        except Exception:
            pass
    if not isinstance(input_list, list):
        raise Exception('迭代节点的输入必须是列表，当前值: ' + str(input_list)[:100])

    # 安全限制：最大迭代次数
    max_iterations = data.get('max_iterations', 100)
    if len(input_list) > max_iterations:
        raise Exception(f'迭代次数超过限制 {max_iterations}，当前 {len(input_list)} 次')

    # 获取子流程节点（通过图结构识别）
    # 注意：子流程节点信息需要通过 context 传递，或者在图遍历时处理
    # 这里我们使用一种简化的方式：通过 iteration_id 来识别子流程节点

    # 获取迭代节点的 id（从 context 中获取，由调用者设置）
    iteration_node_id = data.get('_node_id', '')

    # 从上下文中获取子流程节点列表（由 _execute_workflow_graph 预处理）
    child_nodes = data.get('_child_nodes', [])
    child_edges = data.get('_child_edges', [])

    # 执行迭代
    all_results = []
    for idx, item in enumerate(input_list):
        # 为每个元素创建子上下文
        sub_context = dict(context)
        sub_context['_iteration'] = {
            'index': idx,
            'item': item,
            'total': len(input_list)
        }
        # 将当前元素作为输入变量
        if isinstance(item, dict):
            sub_context.update(item)
        else:
            sub_context['item'] = item
            sub_context['_item'] = item

        # 执行子流程
        if child_nodes:
            sub_result = _execute_sub_graph(
                child_nodes, child_edges, sub_context, model_cfg, iteration_node_id, idx
            )
            all_results.append(sub_result)
        else:
            # 没有子流程节点，直接返回元素本身
            all_results.append(item)

    # 聚合输出
    output_selector = data.get('output_selector', [])
    aggregated = _aggregate_results(all_results, output_selector)

    return {
        'output': aggregated,
        'iteration_results': all_results,
        'iteration_count': len(all_results)
    }


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


def _execute_sub_graph(nodes, edges, context, model_cfg, parent_node_id, iteration_index):
    """
    执行子流程（迭代体）
    """
    from ..workflow_runner import _execute_node_with_retry  # lazy import to avoid circular dependency
    # 构建子图的邻接表
    adj = {}
    in_degree = {}
    node_map = {}
    for n in nodes:
        nid = n['id']
        node_map[nid] = n
        adj[nid] = []
        in_degree[nid] = 0

    for e in edges:
        src = e.get('source')
        tgt = e.get('target')
        if src in adj and tgt in in_degree:
            adj[src].append(tgt)
            in_degree[tgt] = in_degree.get(tgt, 0) + 1

    # 拓扑排序
    queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
    exec_order = []
    while queue:
        nid = queue.popleft()
        exec_order.append(nid)
        for tgt in adj.get(nid, []):
            in_degree[tgt] -= 1
            if in_degree[tgt] == 0:
                queue.append(tgt)

    # 执行节点
    sub_context = dict(context)
    for nid in exec_order:
        node = node_map[nid]
        node_data = node.get('data', {})
        node_type = node_data.get('type', '')

        try:
            outputs = _execute_node_with_retry(node_type, node_data, sub_context, model_cfg)
            if isinstance(outputs, dict):
                sub_context.update(outputs)
        except Exception as e:
            raise Exception(f'迭代第 {iteration_index + 1} 次，节点 {nid} 执行失败: {str(e)}')

    return sub_context


def _aggregate_results(results, output_selector):
    """聚合迭代结果"""
    if not output_selector:
        # 默认返回所有结果的列表
        return results

    # 根据 output_selector 提取指定字段
    aggregated = []
    for r in results:
        if isinstance(r, dict) and output_selector:
            item = {}
            for sel in output_selector:
                key = sel if isinstance(sel, str) else sel.get('variable', '')
                if key and key in r:
                    item[key] = r[key]
            aggregated.append(item)
        else:
            aggregated.append(r)

    return aggregated
