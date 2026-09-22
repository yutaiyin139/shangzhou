# -*- coding: utf-8 -*-
"""
子工作流节点（Sub-Graph）实现

调用另一个工作流作为子流程执行，实现工作流复用和模块化。
通过 sub_app_id 或 sub_workflow_id 加载子工作流定义，经输入/输出变量映射
将当前上下文数据传入子工作流并回收结果。
"""

import json
from collections import deque
from config import get_db


def _node_sub_graph(data, context, model_cfg):
    """
    子工作流节点（Sub-Graph）

    调用另一个工作流作为子流程执行，实现工作流复用和模块化。

    节点数据结构:
    - sub_app_id: 子工作流的应用 ID
    - sub_workflow_id: 子工作流 ID（可选，优先使用 sub_app_id）
    - input_mapping: 输入变量映射 [{ "variable": "var_name", "value_selector": ["node", "output"] }]
    - output_mapping: 输出变量映射，两种形状:
        {"子工作流变量": "当前上下文变量名"}  或
        [{"variable": "当前变量名", "value_selector": ["子工作流变量"]}]

    注意: 子工作流代码节点遵循沙箱约定——输出通过顶层赋值到 outputs
    同名变量（如 ``sub_out = 'SUB_OK'``）暴露给上下文，而非通过 return。
    """
    sub_app_id = data.get('sub_app_id', '')
    sub_workflow_id = data.get('sub_workflow_id', '')

    if not sub_app_id and not sub_workflow_id:
        raise Exception('子工作流节点未配置 sub_app_id 或 sub_workflow_id')

    # 加载子工作流
    db = get_db()
    try:
        cur = db.cursor()
        if sub_workflow_id:
            cur.execute('SELECT * FROM dify_workflows WHERE id = %s LIMIT 1', (sub_workflow_id,))
        else:
            cur.execute('SELECT * FROM dify_workflows WHERE app_id = %s ORDER BY created_at DESC LIMIT 1', (sub_app_id,))
        wf_row = cur.fetchone()

        if not wf_row:
            raise Exception(f'子工作流不存在: app_id={sub_app_id}, workflow_id={sub_workflow_id}')

        # 加载子工作流的应用信息（获取模型配置）
        cur.execute('SELECT * FROM dify_app_model_configs WHERE app_id = %s LIMIT 1', (wf_row['app_id'],))
        sub_model_cfg = cur.fetchone()

        graph = json.loads(wf_row['graph'] or '{}')
        sub_app_id = wf_row['app_id']
    finally:
        db.close()

    # 解析输入映射
    input_mapping = data.get('input_mapping', [])
    sub_inputs = {}
    for mapping in input_mapping:
        var_name = mapping.get('variable', '')
        value_selector = mapping.get('value_selector', [])
        if not value_selector and var_name:
            value_selector = [var_name]
        value = _resolve_selector(context, value_selector)
        if value is not None:
            sub_inputs[var_name] = value

    # 执行子工作流图
    sub_context = dict(sub_inputs)
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])

    # 构建邻接表
    adj = {}
    in_degree = {}
    node_map = {}
    for n in nodes:
        nid = n['id']
        node_map[nid] = n
        adj[nid] = []
        in_degree[nid] = 0
    for e in edges:
        src = e.get('source', '')
        tgt = e.get('target', '')
        if src in adj and tgt in in_degree:
            adj[src].append(tgt)
            in_degree[tgt] = in_degree.get(tgt, 0) + 1

    # 拓扑排序
    queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
    exec_order = []
    while queue:
        nid = queue.popleft()
        exec_order.append(nid)
        for tgt in adj[nid]:
            in_degree[tgt] -= 1
            if in_degree[tgt] == 0:
                queue.append(tgt)

    # 执行子工作流节点
    from ..workflow_runner import _execute_node_with_retry  # lazy import to avoid circular dependency
    for nid in exec_order:
        node = node_map[nid]
        node_data = node.get('data', {})
        node_type = node_data.get('type', '')

        # 跳过 start/end 节点
        if node_type in ('start', 'end'):
            continue

        try:
            outputs = _execute_node_with_retry(node_type, node_data, sub_context, sub_model_cfg)
            if isinstance(outputs, dict):
                sub_context.update(outputs)
        except Exception as e:
            raise Exception(f'子工作流节点 {nid}（类型: {node_type}）执行失败: {str(e)}')

    # 解析输出映射
    # 兼容两种 output_mapping 形状:
    #   {"sub_out": "main_result"}  (key=子工作流变量, value=当前上下文变量名)
    #   [{"variable": "main_result", "value_selector": ["sub_out"]}]  (标准选择器)
    output_mapping = data.get('output_mapping', {})
    result = {}
    if output_mapping:
        # 字典形
        if isinstance(output_mapping, dict):
            for key, output_var in output_mapping.items():
                if key in sub_context and not key.startswith('_'):
                    result[output_var] = sub_context[key]
        # 列表形
        elif isinstance(output_mapping, list):
            for m in output_mapping:
                var_name = m.get('variable', '')
                sel = m.get('value_selector', [])
                if not sel and var_name:
                    sel = [var_name]
                value = _resolve_selector(sub_context, sel)
                if value is not None:
                    result[var_name] = value
    else:
        # 默认返回所有子工作流输出
        result = {k: v for k, v in sub_context.items()
                  if not k.startswith('_') and not k.startswith('__')}

    return result


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
