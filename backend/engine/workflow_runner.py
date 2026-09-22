# -*- coding: utf-8 -*-
"""
本地工作流执行引擎（graphon 架构）—— 替代 Dify Service API 的 /workflows/run 和 /chat-messages 功能。
支持节点类型：start, llm, answer, end, code, if-else, knowledge-retrieval, http-request, tool, mcp, iteration, agent

架构:
- 节点执行委托给 NodeFactory（graphon 模式，节点定义在 nodes/ 目录）
- 本文件保留：图遍历调度、流式执行、工作流入口
- 公共工具函数已提取至 engine/workflow_utils.py
"""

import json
import time
import uuid
import threading
import urllib.request
import urllib.error
import ssl
import socket
from datetime import datetime
from collections import deque
from config import get_db

# 导入节点工厂（自动注册所有节点）
from engine.node_factory import NodeFactory

# 导入图调度器（Dify 式动态就绪调度 + 可达性剪枝）
from engine.graph_scheduler import build_scheduler

# 导入提取的公共工具函数
from engine.workflow_utils import (
    http_request,
    register_workflow_task,
    cancel_workflow_task,
    is_workflow_task_cancelled,
    unregister_workflow_task,
    get_active_workflow_tasks,
    find_model_config,
    get_model_config,
    extract_thought_chains,
    safe_serialize_outputs,
)

# 注意: record_node_start/end 保留在本文件（使用 dify_workflow_node_executions 表）
# workflow_utils 中的版本使用 workflow_node_executions 表（不同 schema）

from utils.llm import decrypt_api_key, build_openai_url

# 注意: HTTP 客户端、任务管理、模型配置查找等公共函数
# 已提取至 engine/workflow_utils.py，通过上方导入使用。
# 本文件保留工作流特有的图遍历调度和流式执行逻辑。


def run_workflow(app_id, inputs, user='szagent-user', graph=None, mode=None):
    """
    执行工作流，返回 (status_code, result_dict)
    实现 Dify Service API 的 blocking 模式执行逻辑。

    参数:
        app_id: 应用 ID
        inputs: 输入参数
        user: 用户标识
        graph: 可选，前端传入的图数据。如提供则优先使用，否则从数据库加载
        mode: 可选，应用模式。如提供则优先使用，否则从数据库加载
    """
    db = get_db()
    try:
        cur = db.cursor()
        # 加载工作流
        cur.execute('SELECT * FROM dify_workflows WHERE app_id = %s LIMIT 1', (app_id,))
        wf_row = cur.fetchone()
        if not wf_row:
            return 404, {'message': '工作流不存在'}

        # 加载应用信息
        cur.execute('SELECT * FROM dify_apps WHERE id = %s LIMIT 1', (app_id,))
        app_row = cur.fetchone()
        if not app_row:
            return 404, {'message': '应用不存在'}

        # 加载模型配置
        cur.execute('SELECT * FROM dify_app_model_configs WHERE app_id = %s LIMIT 1', (app_id,))
        model_cfg_row = cur.fetchone()

        # 优先使用前端传入的图数据，否则从数据库加载
        if graph is None:
            graph = json.loads(wf_row['graph'] or '{}')
        if mode is None:
            mode = app_row['mode']
    finally:
        db.close()

    # 创建运行记录
    run_id = str(uuid.uuid4())
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('''
            INSERT INTO dify_workflow_runs
            (id, app_id, tenant_id, workflow_id, status, inputs, created_by, created_at)
            VALUES (%s, %s, %s, %s, 'running', %s, %s, %s)
        ''', (run_id, app_id, wf_row['tenant_id'], wf_row['id'],
              json.dumps(inputs, ensure_ascii=False), user, ts))
        db.commit()
    finally:
        db.close()

    # 执行图
    start_time = time.time()
    try:
        if mode in ('workflow', 'completion'):
            result = _execute_workflow_graph(graph, inputs, model_cfg_row, app_id, run_id)
        else:
            result = _execute_chat_graph(graph, inputs, model_cfg_row, app_id, run_id)

        elapsed = time.time() - start_time

        # 检查是否需要暂停等待 Human Input
        if isinstance(result, dict) and result.get('__human_input_pause__'):
            # 保存暂停状态到数据库
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute('''
                    UPDATE dify_workflow_runs
                    SET status='waiting', outputs=%s, elapsed_time=%s
                    WHERE id=%s
                ''', (json.dumps(result, ensure_ascii=False), elapsed, run_id))
                db.commit()
            finally:
                db.close()

            # 3.6: Human Input 邮件投递（如果配置了邮箱）
            try:
                human_input_config = result.get('__human_input_config__', {})
                email_to = human_input_config.get('email', '')
                if email_to:
                    from engine.human_input_delivery import deliver_human_input_email
                    app_name = app_row.get('name', '未知应用') if app_row else '未知应用'
                    node_message = human_input_config.get('message', '请输入信息')
                    fields = human_input_config.get('fields', [])
                    node_id = result.get('__human_input_node_id__', '')
                    success, err, delivery_id = deliver_human_input_email(
                        app_id, run_id, node_id, email_to,
                        app_name, node_message, fields
                    )
                    if success:
                        result['__email_delivery_id__'] = delivery_id
                        import logging
                        logging.getLogger(__name__).info(
                            f'[HumanInput] 邮件已发送至 {email_to}, delivery_id={delivery_id}'
                        )
                    else:
                        import logging
                        logging.getLogger(__name__).warning(
                            f'[HumanInput] 邮件发送失败: {err}'
                        )
            except Exception:
                pass  # 邮件失败不阻塞工作流

            return 200, {
                'id': run_id,
                'status': 'waiting',
                'message': '等待用户输入',
                'human_input': {
                    'config': result.get('__human_input_config__', {}),
                    'node_id': result.get('__human_input_node_id__', ''),
                    'output_var': result.get('__human_input_output_var__', 'human_input'),
                },
                'elapsed_time': elapsed,
            }

        # 更新运行记录
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('''
                UPDATE dify_workflow_runs
                SET status='succeeded', outputs=%s, elapsed_time=%s, finished_at=%s
                WHERE id=%s
            ''', (json.dumps(result, ensure_ascii=False), elapsed,
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S'), run_id))
            db.commit()
        finally:
            db.close()

        return 200, {
            'id': run_id,
            'status': 'succeeded',
            'outputs': result,
            'thought_chain': extract_thought_chains(result),
            'elapsed_time': elapsed,
            'total_tokens': result.get('total_tokens', 0),
            'total_steps': 0,
        }
    except Exception as e:
        elapsed = time.time() - start_time
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('''
                UPDATE dify_workflow_runs
                SET status='failed', error=%s, elapsed_time=%s, finished_at=%s
                WHERE id=%s
            ''', (str(e)[:500], elapsed,
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S'), run_id))
            db.commit()
        finally:
            db.close()
        return 500, {'message': str(e)}


# ============================================================
# 执行上下文：node 命名空间 + 扁平别名
# ============================================================

# 保留键：不属于任何业务变量，不进入命名空间/扁平别名
_RESERVED_CONTEXT_KEYS = ('__flat_owner__',)


def apply_node_outputs(context, node_id, outputs, extra=False):
    """
    把节点输出写入执行上下文（消除同名覆盖）。

    - 命名空间：context[node_id] = {name: value}，每个节点的输出互不覆盖，
      下游可用点号路径引用（如 if-else 条件 'n_start.x' / 变量选择器 [node_id, name]）。
    - 扁平别名：仅为「首个生产者」写入，同一节点自身可更新（迭代/循环场景）；
      不同节点的同名输出不再互相覆盖，保持对旧「裸变量名」写法的向后兼容。
    - 下划线开头的键视为节点内部信号（如 _human_input_wait），不进入业务变量。

    返回：(namespaced_outputs, signals) —— signals 为以单个下划线开头的内部键。
    """
    if not isinstance(outputs, dict):
        outputs = {'output': outputs} if outputs is not None else {}

    flat_owner = context.setdefault('__flat_owner__', {})
    namespaced = {}
    signals = {}

    for key, value in outputs.items():
        if key in _RESERVED_CONTEXT_KEYS:
            continue
        if key.startswith('_'):
            signals[key] = value
            continue
        namespaced[key] = value
        owner = flat_owner.get(key)
        if extra or owner is None or owner == node_id:
            context[key] = value
            flat_owner[key] = node_id

    if namespaced:
        merged = dict(context.get(node_id) or {}) if isinstance(context.get(node_id), dict) else {}
        merged.update(namespaced)
        context[node_id] = merged

    return namespaced, signals


def _inject_node_id(node_type, nid, data):
    """为需要 node 身份的节点注入内部字段（迭代体 / 人工介入表单回写）。"""
    if node_type in ('human-input', 'iteration', 'loop'):
        data['_node_id'] = nid


def _prepare_iteration_data(nid, data, iteration_nodes):
    """为迭代节点注入子图信息。"""
    if nid in iteration_nodes:
        child_info = iteration_nodes[nid]
        data['_child_nodes'] = child_info['nodes']
        data['_child_edges'] = child_info['edges']
        data['_node_id'] = nid


def _pause_payload(context, scheduler, executed_order, pause_index, signals, node_id):
    """构造 Human Input 暂停返回值（携带可恢复的调度状态）。"""
    return {
        '__human_input_pause__': True,
        '__human_input_config__': signals.get('_human_input_config', {}),
        '__human_input_output_var__': signals.get('_human_input_output_var', 'human_input'),
        '__human_input_node_id__': signals.get('_human_input_node_id', node_id),
        '__context__': context,
        '__exec_order__': list(executed_order),
        '__current_node_idx__': pause_index,
        '__executed_nodes__': sorted(scheduler.executed),
        '__branch_map__': dict(scheduler.branches),
    }


def _execute_workflow_graph(graph, inputs, model_cfg, app_id, run_id, resume=None):
    """
    执行工作流图。

    调度方式：Dify 式动态就绪调度（engine/graph_scheduler.py）——
    节点只在所有入边来源落定且至少一条入边被激活时才执行，未命中分支的节点
    通过可达性剪枝整体失活，不会再被当作根节点重复执行。

    参数:
        resume: 可选，{'executed': [...], 'branches': {...}}，用于 Human Input 暂停后恢复执行。
    """
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])

    # 预处理：识别迭代节点及其子图（子图节点由迭代节点内部执行）
    iteration_nodes, child_node_map = _identify_iteration_subgraphs(nodes, edges)
    main_nodes = [n for n in nodes if n['id'] not in child_node_map]
    main_edges = [e for e in edges
                  if e.get('source') not in child_node_map and e.get('target') not in child_node_map]

    node_map = {n['id']: n for n in main_nodes}

    resume = resume or {}
    if resume.get('context') is not None:
        # Human Input 暂停后恢复：沿用已保存的执行上下文（含 node 命名空间与扁平别名）
        context = dict(resume['context'])
    else:
        context = dict(inputs)  # Start 节点的输入变量（扁平 + 按 start 节点命名空间可见）
        for start_id in [n['id'] for n in main_nodes
                         if (n.get('data') or {}).get('type') == 'start']:
            apply_node_outputs(context, start_id, inputs, extra=False)

    scheduler = build_scheduler(node_map, main_nodes, main_edges,
                                executed=resume.get('executed'),
                                branches=resume.get('branches'))

    executed_order = [nid for nid in scheduler.executed]  # 稳定顺序（用于历史展示）
    pause_index = -1

    while True:
        nid = scheduler.next_ready()
        if nid is None:
            break

        node = node_map[nid]
        data = node.get('data', {})
        node_type = data.get('type', '')

        _prepare_iteration_data(nid, data, iteration_nodes)
        _inject_node_id(node_type, nid, data)

        # 记录节点执行
        node_exec_id = str(uuid.uuid4())
        _record_node_start(run_id, app_id, node_exec_id, nid, node_type, data.get('title', ''))

        try:
            node_timeout = data.get('timeout', 120)
            raw_outputs = _execute_node_with_retry(node_type, data, context, model_cfg,
                                                   timeout=node_timeout)
        except Exception as e:
            _record_node_end(node_exec_id, 'failed', None, str(e))
            scheduler.on_failed(nid)
            raise

        namespaced, signals = apply_node_outputs(context, nid, raw_outputs)
        _record_node_end(node_exec_id, 'succeeded', namespaced)

        # Human Input：保存调度状态以便恢复执行
        if signals.get('_human_input_wait'):
            executed_order = _executed_order_of(scheduler)
            pause_index = len(executed_order) - 1
            return _pause_payload(context, scheduler, executed_order, pause_index,
                                  signals, nid)

        executed_order = _executed_order_of(scheduler)

        # 分支决策：命中分支的出边激活，未命中分支的下游整体剪枝
        # （从节点原始输出读 __branch__/class_id，因为它们属于下划线开头的内部信号）
        branch = scheduler.decide_branch(nid, {**signals, **namespaced})
        scheduler.on_executed(nid, branch)

    pending = scheduler.remaining()
    if pending:
        import logging
        logging.getLogger(__name__).warning(
            '图调度提前结束，仍有节点未就绪（可能存在成环或缺失入边）: %s', pending)

    return context


def _executed_order_of(scheduler):
    """按图内声明顺序返回已执行节点列表（保持稳定可复现）。"""
    return [nid for nid in scheduler.node_ids if nid in scheduler.executed]


def _identify_iteration_subgraphs(nodes, edges):
    """
    识别迭代节点及其子图
    返回:
    - iteration_nodes: {iteration_id: {'nodes': [...], 'edges': [...]}}
    - child_node_map: {child_node_id: iteration_id} 用于过滤主图
    """
    iteration_nodes = {}
    child_node_map = {}

    # 找到所有迭代节点
    iteration_ids = set()
    for n in nodes:
        data = n.get('data', {})
        if data.get('type') == 'iteration':
            iteration_ids.add(n['id'])
            iteration_nodes[n['id']] = {'nodes': [], 'edges': []}

    if not iteration_ids:
        return iteration_nodes, child_node_map

    # 构建邻接关系
    adj = {}  # source -> [(target, edge)]
    for e in edges:
        src = e.get('source')
        tgt = e.get('target')
        if src not in adj:
            adj[src] = []
        adj[src].append((tgt, e))

    # 对于每个迭代节点，找到其子图
    # 约定：迭代节点有两个输出
    # - "loop" 或 "iteration" handle: 连接到子图起始节点
    # - 默认输出: 连接到迭代后的下一个节点
    for iter_id in iteration_ids:
        # 找到从迭代节点出发的边
        loop_edges = []
        next_edges = []
        for tgt, e in adj.get(iter_id, []):
            source_handle = e.get('sourceHandle', '')
            # 如果 sourceHandle 是 loop/iteration 开头，则为子图边
            if source_handle and ('loop' in source_handle.lower() or 'iter' in source_handle.lower() or source_handle == 'element'):
                loop_edges.append((tgt, e))
            else:
                next_edges.append((tgt, e))

        # 如果没有明确的 handle 区分，默认第一个输出为子图
        if not loop_edges and adj.get(iter_id):
            # 简单策略：假设第一个输出是子图
            first_tgt, first_edge = adj[iter_id][0]
            loop_edges.append((first_tgt, first_edge))
            for tgt, e in adj[iter_id][1:]:
                next_edges.append((tgt, e))

        # BFS 找到子图的所有节点
        child_nodes = set()
        child_edges = []
        visited = set()
        queue = deque()

        for tgt, e in loop_edges:
            queue.append(tgt)
            child_edges.append(e)

        while queue:
            current = queue.popleft()
            if current in visited or current == iter_id:
                continue
            visited.add(current)
            child_nodes.add(current)

            # 继续遍历子图内的边
            for tgt, e in adj.get(current, []):
                if tgt not in visited and tgt != iter_id:
                    child_edges.append(e)
                    queue.append(tgt)

        # 收集子图节点对象
        child_node_list = [n for n in nodes if n['id'] in child_nodes]

        iteration_nodes[iter_id] = {
            'nodes': child_node_list,
            'edges': child_edges
        }

        # 记录子图节点到迭代节点的映射
        for cnid in child_nodes:
            child_node_map[cnid] = iter_id

    return iteration_nodes, child_node_map


def _execute_chat_graph(graph, inputs, model_cfg, app_id, run_id):
    """执行对话类图（chat/advanced-chat/agent-chat）"""
    # 对话类：找到 query 输入 → 执行 LLM 节点 → 返回 answer
    query = inputs.get('query', '')
    context = dict(inputs)

    nodes = graph.get('nodes', [])
    for n in nodes:
        data = n.get('data', {})
        node_type = data.get('type', '')
        if node_type == 'llm':
            result = _execute_node(node_type, data, {'query': query, **context}, model_cfg)
            return {'answer': result.get('text', result.get('output', ''))}

    return {'answer': ''}



def _execute_node(node_type, data, context, model_cfg):
    """
    执行单个节点 —— 委托给 NodeFactory（graphon 模式）

    NodeFactory 自动处理:
    - 节点类型路由（支持 kebab-case 和 snake_case 别名）
    - 未知节点类型错误
    - 特殊节点（start/end/answer/trigger/datasource/knowledge-index）
    """
    return NodeFactory.execute(node_type, data, context, model_cfg)


def _execute_node_with_timeout(node_type, data, context, model_cfg, timeout=120):
    """
    带超时控制的节点执行

    参数:
        node_type: 节点类型
        data: 节点数据
        context: 执行上下文
        model_cfg: 模型配置
        timeout: 超时时间（秒），默认 120 秒

    返回:
        节点执行结果

    异常:
        TimeoutError: 节点执行超时
    """
    import concurrent.futures

    # 使用线程池执行节点（支持超时控制）
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_execute_node, node_type, data, context, model_cfg)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            # 尝试取消任务
            future.cancel()
            raise TimeoutError(f'节点执行超时（{timeout}秒），节点类型: {node_type}，节点: {data.get("title", "")}')


def _execute_node_with_retry(node_type, data, context, model_cfg, timeout=120):
    """
    带超时和重试控制的节点执行

    支持通过节点 data 配置重试策略:
        data.retry_config = {
            'retry_enabled': True,       # 是否启用重试
            'max_retries': 3,            # 最大重试次数
            'retry_interval': 1000,      # 初始重试间隔（毫秒）
            'retry_factor': 2,           # 指数退避因子
        }

    参数:
        node_type: 节点类型
        data: 节点数据
        context: 执行上下文
        model_cfg: 模型配置
        timeout: 单次执行超时时间（秒）

    返回:
        节点执行结果

    异常:
        TimeoutError: 节点执行超时
        Exception: 重试耗尽后仍失败
    """
    import time

    # 读取重试配置
    retry_config = data.get('retry_config', {})
    retry_enabled = retry_config.get('retry_enabled', False)
    max_retries = retry_config.get('max_retries', 3) if retry_enabled else 0
    retry_interval = retry_config.get('retry_interval', 1000) / 1000.0  # 毫秒转秒
    retry_factor = retry_config.get('retry_factor', 2)

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return _execute_node_with_timeout(node_type, data, context, model_cfg, timeout)
        except TimeoutError:
            # 超时错误不重试，直接抛出
            raise
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                # 计算退避等待时间
                wait_time = retry_interval * (retry_factor ** attempt)
                import logging
                logging.warning(
                    f'节点执行失败（第 {attempt + 1}/{max_retries + 1} 次），'
                    f'{wait_time:.1f}秒后重试。节点: {data.get("title", "")}，'
                    f'类型: {node_type}，错误: {str(e)[:200]}'
                )
                time.sleep(wait_time)

    # 重试耗尽，抛出最后一次错误
    raise last_error


# ============================================================
# 节点执行记录（用于前端展示执行进度）
# ============================================================


def _record_node_start(run_id, app_id, exec_id, node_id, node_type, title):
    """记录节点执行开始"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('''
            INSERT INTO dify_workflow_node_executions
            (id, app_id, workflow_run_id, node_id, node_type, title, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'running', %s)
        ''', (exec_id, app_id, run_id, node_id, node_type, title or '',
              datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        db.commit()
    finally:
        db.close()


def _record_node_end(exec_id, status, outputs, error=None):
    """记录节点执行结束"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('''
            UPDATE dify_workflow_node_executions
            SET status=%s, outputs=%s, error=%s, finished_at=%s
            WHERE id=%s
        ''', (status,
              json.dumps(outputs or {}, ensure_ascii=False) if outputs else None,
              error[:500] if error else None,
              datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
              exec_id))
        db.commit()
    finally:
        db.close()




# ============================================================
# 流式 LLM 调用（SSE）
# ============================================================

def _call_llm_stream(messages, model_name, api_key, base_url, temperature=0.7, max_tokens=2048,
                     trace_run_id='', trace_node_id='', trace_node_type='llm'):
    """
    流式调用 OpenAI 兼容 API，返回生成器。

    每次 yield 一个字典:
    - {'content': str}: 增量内容
    - {'thinking': str}: 思维链增量（DeepSeek R1 等推理模型的 reasoning_content）
    - {'done': True}: 流式结束
    - {'error': str}: 错误信息
    - {'usage': {'total_tokens': int}}: 使用量（结束时）

    参数:
        trace_run_id: 工作流运行 ID（用于 Tracing）
        trace_node_id: 节点 ID（用于 Tracing）
        trace_node_type: 节点类型（用于 Tracing）
    """
    full_content = ''
    full_thinking = ''
    usage_info = None

    payload = json.dumps({
        'model': model_name,
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens,
        'stream': True
    }).encode('utf-8')

    api_url = build_openai_url(base_url, 'chat/completions')
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + api_key}

    try:
        resp = http_request(api_url, data=payload, headers=headers, method='POST', timeout=180)
    except Exception as e:
        yield {'error': f'模型 API 连接失败: {e}'}
        return

    for raw_line in resp:
        line = raw_line.decode('utf-8').strip()
        if not line:
            continue
        if line.startswith('data: '):
            data = line[6:]
            if data == '[DONE]':
                yield {'done': True}
                # 发送 trace（在流结束时）
                try:
                    from utils.tracing import trace_llm_call
                    with trace_llm_call(
                        model=model_name,
                        messages=messages,
                        run_id=trace_run_id,
                        node_id=trace_node_id,
                        node_type=trace_node_type,
                    ) as trace:
                        trace.set_output(full_content, usage_info)
                        if full_thinking:
                            trace.set_metadata(thinking=full_thinking[:2000])
                except Exception:
                    pass
                return
            try:
                chunk = json.loads(data)
                if 'choices' in chunk and chunk['choices']:
                    delta = chunk['choices'][0].get('delta', {})
                    # 提取正文内容
                    content = delta.get('content', '')
                    if content:
                        full_content += content
                        yield {'content': content}
                    # 提取思维链内容（DeepSeek R1 等推理模型的 reasoning_content）
                    reasoning = delta.get('reasoning_content', '')
                    if reasoning:
                        full_thinking += reasoning
                        yield {'thinking': reasoning}
                # 提取 usage 信息
                if 'usage' in chunk and chunk['usage']:
                    usage_info = chunk['usage']
                    yield {'usage': chunk['usage']}
            except json.JSONDecodeError:
                pass


# get_model_config 已提取至 workflow_utils，通过上方导入使用


# ============================================================
# 流式工作流执行引擎 (SSE)
# ============================================================

def run_workflow_stream(app_id, inputs, user='szagent-user', graph=None, mode=None):
    """
    流式执行工作流，通过 SSE 推送实时进度。

    这是一个生成器函数，每次 yield 一个 SSE 事件字典:
    - {'event': 'workflow_start', 'data': {...}}
    - {'event': 'node_start', 'data': {...}}
    - {'event': 'node_stream', 'data': {...}}  (LLM 节点流式输出)
    - {'event': 'node_complete', 'data': {...}}
    - {'event': 'workflow_complete', 'data': {...}}
    - {'event': 'workflow_stopped', 'data': {...}}  (用户主动停止)
    - {'event': 'error', 'data': {...}}

    停止运行: 调用 cancel_workflow_task(run_id) 或 API /api/workflows/<run_id>/stop

    参数:
        app_id: 应用 ID
        inputs: 输入参数
        user: 用户标识
        graph: 可选，前端传入的图数据。如提供则优先使用，否则从数据库加载
        mode: 可选，应用模式。如提供则优先使用，否则从数据库加载

    使用方式（Flask 路由）:
        @app.route('/api/workflows/<app_id>/stream', methods=['POST'])
        def workflow_stream(app_id):
            def generate():
                for evt in run_workflow_stream(app_id, inputs, user):
                    yield f"event: {evt['event']}\ndata: {json.dumps(evt['data'], ensure_ascii=False)}\n\n"
            return Response(generate(), mimetype='text/event-stream')
    """
    run_id = str(uuid.uuid4())
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 注册任务
    register_workflow_task(run_id)

    # 加载工作流
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('SELECT * FROM dify_workflows WHERE app_id = %s LIMIT 1', (app_id,))
        wf_row = cur.fetchone()
        if not wf_row:
            yield {'event': 'error', 'data': {'message': '工作流不存在'}}
            return

        cur.execute('SELECT * FROM dify_apps WHERE id = %s LIMIT 1', (app_id,))
        app_row = cur.fetchone()
        if not app_row:
            yield {'event': 'error', 'data': {'message': '应用不存在'}}
            return

        cur.execute('SELECT * FROM dify_app_model_configs WHERE app_id = %s LIMIT 1', (app_id,))
        model_cfg_row = cur.fetchone()

        # 优先使用前端传入的图数据，否则从数据库加载
        if graph is None:
            graph = json.loads(wf_row['graph'] or '{}')
        if mode is None:
            mode = app_row['mode']
    finally:
        db.close()

    # 创建运行记录
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('''
            INSERT INTO dify_workflow_runs
            (id, app_id, tenant_id, workflow_id, status, inputs, created_by, created_at)
            VALUES (%s, %s, %s, %s, 'running', %s, %s, %s)
        ''', (run_id, app_id, wf_row['tenant_id'], wf_row['id'],
              json.dumps(inputs, ensure_ascii=False), user, ts))
        db.commit()
    finally:
        db.close()

    # 推送工作流开始事件
    yield {
        'event': 'workflow_start',
        'data': {
            'run_id': run_id,
            'app_id': app_id,
            'mode': mode,
            'inputs': inputs,
            'started_at': ts,
        }
    }

    # 执行图
    start_time = time.time()
    try:
        if mode in ('workflow', 'completion'):
            # 使用流式图执行
            for evt in _execute_workflow_graph_stream(graph, inputs, model_cfg_row, app_id, run_id):
                yield evt
                # 检查是否被取消
                if is_workflow_task_cancelled(run_id):
                    break
        else:
            # 对话类图流式执行
            for evt in _execute_chat_graph_stream(graph, inputs, model_cfg_row, app_id, run_id):
                yield evt
                # 检查是否被取消
                if is_workflow_task_cancelled(run_id):
                    break

        elapsed = time.time() - start_time

        # 检查是否被取消
        if is_workflow_task_cancelled(run_id):
            # 更新运行记录为已停止
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute('''
                    UPDATE dify_workflow_runs
                    SET status='stopped', elapsed_time=%s, finished_at=%s
                    WHERE id=%s
                ''', (elapsed, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), run_id))
                db.commit()
            finally:
                db.close()

            # 推送停止事件
            yield {
                'event': 'workflow_stopped',
                'data': {
                    'run_id': run_id,
                    'status': 'stopped',
                    'message': '用户主动停止',
                    'elapsed_time': elapsed,
                    'finished_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                }
            }
        else:
            # 正常完成
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute('''
                    UPDATE dify_workflow_runs
                    SET status='succeeded', elapsed_time=%s, finished_at=%s
                    WHERE id=%s
                ''', (elapsed, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), run_id))
                db.commit()
            finally:
                db.close()

            # 推送工作流完成事件
            yield {
                'event': 'workflow_complete',
                'data': {
                    'run_id': run_id,
                    'status': 'succeeded',
                    'elapsed_time': elapsed,
                    'finished_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                }
            }
    except Exception as e:
        elapsed = time.time() - start_time
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('''
                UPDATE dify_workflow_runs
                SET status='failed', error=%s, elapsed_time=%s, finished_at=%s
                WHERE id=%s
            ''', (str(e)[:500], elapsed,
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S'), run_id))
            db.commit()
        finally:
            db.close()

        yield {
            'event': 'error',
            'data': {
                'run_id': run_id,
                'status': 'failed',
                'message': str(e),
                'elapsed_time': elapsed,
            }
        }
    finally:
        # 注销任务
        unregister_workflow_task(run_id)


def _business_outputs(context):
    """从执行上下文中剔除引擎内部键，得到可展示的业务变量。"""
    return {k: v for k, v in context.items()
            if not k.startswith('__') and isinstance(v, (str, int, float, bool, list, dict))}


def _execute_workflow_graph_stream(graph, inputs, model_cfg, app_id, run_id):
    """
    流式执行工作流图（动态就绪调度 + 可达性剪枝 + 逐节点流式输出）。

    与 _execute_workflow_graph 使用同一套调度器（engine/graph_scheduler.py），
    仅额外 yield SSE 事件。
    """
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])

    # 预处理：识别迭代节点及其子图
    iteration_nodes, child_node_map = _identify_iteration_subgraphs(nodes, edges)

    # 过滤掉子图节点
    main_nodes = [n for n in nodes if n['id'] not in child_node_map]
    main_edges = [e for e in edges if e.get('source') not in child_node_map and e.get('target') not in child_node_map]

    node_map = {n['id']: n for n in main_nodes}

    context = dict(inputs)
    for start_id in [n['id'] for n in main_nodes
                     if (n.get('data') or {}).get('type') == 'start']:
        apply_node_outputs(context, start_id, inputs, extra=False)

    scheduler = build_scheduler(node_map, main_nodes, main_edges)

    while True:
        nid = scheduler.next_ready()
        if nid is None:
            break

        node = node_map[nid]
        data = node.get('data', {})
        node_type = data.get('type', '')

        _prepare_iteration_data(nid, data, iteration_nodes)
        _inject_node_id(node_type, nid, data)

        # 推送节点开始事件
        yield {
            'event': 'node_start',
            'data': {
                'node_id': nid,
                'node_type': node_type,
                'title': data.get('title', ''),
            }
        }

        node_exec_id = str(uuid.uuid4())
        _record_node_start(run_id, app_id, node_exec_id, nid, node_type, data.get('title', ''))

        try:
            # 对 LLM / Agent 节点使用流式执行（实时推送正文/思考链），其他节点同步执行
            if node_type == 'llm':
                node_outputs = yield from _node_llm_stream(data, context, model_cfg, nid, run_id)
            elif node_type == 'agent':
                node_outputs = yield from _node_agent_stream(data, context, model_cfg, nid)
            else:
                node_outputs = _execute_node_with_retry(node_type, data, context, model_cfg)

            namespaced, signals = apply_node_outputs(context, nid, node_outputs)
            _record_node_end(node_exec_id, 'succeeded', namespaced)

            # Agent 节点：推送思考链汇总事件（供前端展示 ReAct 过程）
            if node_type == 'agent' and isinstance(namespaced, dict) and namespaced.get('thought_chain'):
                yield {
                    'event': 'agent_thought',
                    'data': {
                        'node_id': nid,
                        'title': data.get('title', ''),
                        'thought_chain': namespaced['thought_chain'],
                        'tool_calls': namespaced.get('tool_calls', []),
                        'iterations_used': namespaced.get('iterations_used', 0),
                        'total_tokens': namespaced.get('total_tokens', 0),
                    }
                }

            # 推送节点完成事件
            yield {
                'event': 'node_complete',
                'data': {
                    'node_id': nid,
                    'node_type': node_type,
                    'title': data.get('title', ''),
                    'status': 'succeeded',
                    'outputs': safe_serialize_outputs(namespaced),
                }
            }

            # Human Input：暂停并推送等待事件
            if signals.get('_human_input_wait'):
                yield {
                    'event': 'workflow_pause',
                    'data': {
                        'reason': 'human_input',
                        'config': signals.get('_human_input_config', {}),
                        'node_id': signals.get('_human_input_node_id', nid),
                        'output_var': signals.get('_human_input_output_var', 'human_input'),
                        'context': _business_outputs(context),
                    }
                }
                return

            # 路由决策：命中分支的出边激活，未命中分支的下游整体剪枝
            scheduler.on_executed(nid, scheduler.decide_branch(nid, {**signals, **namespaced}))

        except Exception as e:
            _record_node_end(node_exec_id, 'failed', None, str(e))
            scheduler.on_failed(nid)
            yield {
                'event': 'node_complete',
                'data': {
                    'node_id': nid,
                    'node_type': node_type,
                    'title': data.get('title', ''),
                    'status': 'failed',
                    'error': str(e),
                }
            }
            raise

    pending = scheduler.remaining()
    if pending:
        import logging
        logging.getLogger(__name__).warning(
            '图调度提前结束，仍有节点未就绪（可能存在成环或缺失入边）: %s', pending)

    # 推送最终上下文
    yield {
        'event': 'workflow_result',
        'data': {
            'outputs': _business_outputs(context),
            'thought_chain': extract_thought_chains(context),
        }
    }


def _node_agent_stream(data, context, model_cfg, node_id):
    """
    流式执行 Agent 节点：通过 on_thought 回调实时推送思考链事件。

    yield 事件：{'event': 'agent_thought_stream', 'data': {...}}
    返回：与非流式 agent 节点一致 outputs（部分字段为节点内部信号，以 _ 开头）
    """
    from engine.agent_strategies import execute_agent_strategy
    from engine.nodes.agent import _find_model_config

    thought_events = []

    def _on_thought(event):
        thought_events.append({
            'event': 'agent_thought_stream',
            'data': {
                'node_id': node_id,
                'title': data.get('title', ''),
                'type': event.get('type', 'unknown'),
                'content': event.get('content', ''),
                'tool_name': event.get('tool_name', ''),
                'tool_input': event.get('tool_input'),
                'tool_output': event.get('tool_output'),
                'step_type': event.get('step_type', ''),
            }
        })

    agent_cfg = data.get('config', {})
    strategy_name = data.get('strategy') or agent_cfg.get('strategy', 'react')
    model = data.get('model', {})
    provider = model.get('provider', '')
    model_name = model.get('name', '')
    if not model_name and model_cfg:
        try:
            m = json.loads(model_cfg.get('model', '{}'))
            model_name = m.get('name', '')
            provider = m.get('provider', '')
        except Exception:
            pass

    cfg = _find_model_config(provider)
    if cfg:
        api_key = decrypt_api_key(cfg['api_key'])
        base_url = (cfg['api_base_url'] or '').rstrip('/')
        final_model = model_name or cfg['model_name'] or cfg['credential_name'] or cfg['provider']
    else:
        api_key = ''
        base_url = ''
        final_model = model_name

    completion_params = model.get('completion_params', {})
    llm_config = {
        'model': final_model,
        'api_key': api_key,
        'base_url': base_url,
        'temperature': completion_params.get('temperature', 0.7),
        'max_tokens': completion_params.get('max_tokens', 2048),
        'max_iterations': agent_cfg.get('max_iterations', data.get('max_iterations', 5)),
    }

    system_prompt = data.get('prompt', '你是一个智能助手，可以使用工具来帮助用户解决问题。')
    user_prompt = data.get('user_prompt', context.get('query', ''))
    for k, v in context.items():
        if k.startswith('__'):
            continue
        if isinstance(v, (str, int, float)):
            user_prompt = user_prompt.replace('{{' + k + '}}', str(v))
            system_prompt = system_prompt.replace('{{' + k + '}}', str(v))

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt},
    ]

    strategy_result = execute_agent_strategy(
        strategy_name, messages, tools=data.get('tools', []), context=context,
        llm_config=llm_config, on_thought=_on_thought)

    # 实时推送思考事件
    for evt in thought_events:
        yield evt

    return {
        data.get('output', 'output'): strategy_result.get('output', ''),
        'agent_output': strategy_result.get('output', ''),
        'tool_calls': strategy_result.get('tool_calls', []),
        'thought_chain': strategy_result.get('thought_chain', []),
        'total_tokens': strategy_result.get('tokens', 0),
        'iterations_used': strategy_result.get('iterations', 0),
        'strategy_used': strategy_name,
    }


def _execute_chat_graph_stream(graph, inputs, model_cfg, app_id, run_id):
    """流式执行对话类图"""
    query = inputs.get('query', '')
    context = dict(inputs)

    nodes = graph.get('nodes', [])
    for n in nodes:
        data = n.get('data', {})
        node_type = data.get('type', '')
        nid = n['id']

        if node_type == 'llm':
            # 推送节点开始事件
            yield {
                'event': 'node_start',
                'data': {
                    'node_id': nid,
                    'node_type': node_type,
                    'title': data.get('title', ''),
                }
            }

            # 流式执行 LLM 节点
            node_outputs = yield from _node_llm_stream(data, context, model_cfg, nid, run_id)

            yield {
                'event': 'node_complete',
                'data': {
                    'node_id': nid,
                    'node_type': node_type,
                    'title': data.get('title', ''),
                    'status': 'succeeded',
                    'outputs': safe_serialize_outputs(node_outputs),
                }
            }

            if isinstance(node_outputs, dict):
                context.update(node_outputs)

    answer = context.get('text', context.get('output', context.get('answer', '')))
    yield {
        'event': 'workflow_result',
        'data': {'answer': answer, 'outputs': {'answer': answer}}
    }


def _node_llm_stream(data, context, model_cfg, node_id, run_id):
    """
    流式执行 LLM 节点。

    与 _node_llm 不同，此函数会 yield 流式内容事件，
    最后返回完整的输出字典（与非流式版本格式一致）。

    yield 事件:
    - {'event': 'node_stream', 'data': {'node_id': ..., 'content': ..., 'delta': ...}}
    - {'event': 'node_stream', 'data': {'node_id': ..., 'done': True, 'usage': ...}}

    返回: {'text': str, 'output': str, 'total_tokens': int}
    """
    # 解析 prompt_template
    prompt_template = data.get('prompt_template', [])
    system_text = ''
    user_text = ''
    for pt in prompt_template:
        if pt.get('role') == 'system':
            system_text = pt.get('text', '')
        elif pt.get('role') == 'user':
            user_text = pt.get('text', '')

    # 变量替换
    for k, v in context.items():
        if k.startswith('__'):
            continue  # 引擎内部键不参与替换
        if isinstance(v, (str, int, float)):
            sv = str(v)
            system_text = system_text.replace('{{' + k + '}}', sv)
            user_text = user_text.replace('{{' + k + '}}', sv)

    # 获取模型配置
    model = data.get('model', {})
    provider = model.get('provider', '')
    model_name = model.get('name', '')

    if not model_name and model_cfg:
        try:
            m = json.loads(model_cfg.get('model', '{}'))
            model_name = m.get('name', '')
            provider = m.get('provider', '')
        except Exception:
            pass

    # 从 model_configs 表查找 API 凭证（支持多种 provider 格式匹配）
    cfg = find_model_config(provider)

    if not cfg:
        raise Exception('没有可用的模型配置')

    # 安全加固：解密 API Key（如果已加密）
    api_key = decrypt_api_key(cfg['api_key'])
    base_url = (cfg['api_base_url'] or '').rstrip('/')
    final_model = model_name or cfg['model_name'] or cfg['credential_name'] or cfg['provider']
    completion_params = model.get('completion_params', {})
    temperature = completion_params.get('temperature', 0.7)

    # 构建消息
    messages = []
    if system_text:
        messages.append({'role': 'system', 'content': system_text})
    messages.append({'role': 'user', 'content': user_text or context.get('query', '')})

    # 流式调用 LLM
    full_content = ''
    total_tokens = 0

    for chunk in _call_llm_stream(messages, final_model, api_key, base_url, temperature,
                                   trace_run_id=run_id, trace_node_id=node_id, trace_node_type='llm'):
        if 'error' in chunk:
            yield {
                'event': 'node_stream',
                'data': {
                    'node_id': node_id,
                    'error': chunk['error'],
                }
            }
            raise Exception(f'LLM 调用错误: {chunk["error"]}')

        if 'content' in chunk:
            full_content += chunk['content']
            yield {
                'event': 'node_stream',
                'data': {
                    'node_id': node_id,
                    'content': full_content,
                    'delta': chunk['content'],
                }
            }

        if 'usage' in chunk:
            total_tokens = chunk['usage'].get('total_tokens', 0)

        if chunk.get('done'):
            yield {
                'event': 'node_stream',
                'data': {
                    'node_id': node_id,
                    'done': True,
                    'usage': {'total_tokens': total_tokens},
                }
            }

    return {'text': full_content, 'output': full_content, 'total_tokens': total_tokens}


def safe_serialize_outputs(outputs):
    """安全序列化节点输出，用于 SSE 推送"""
    if outputs is None:
        return {}
    if isinstance(outputs, dict):
        result = {}
        for k, v in outputs.items():
            if isinstance(v, (str, int, float, bool)):
                result[k] = v
            elif isinstance(v, (list, dict)):
                try:
                    result[k] = json.loads(json.dumps(v, ensure_ascii=False))
                except (TypeError, ValueError):
                    result[k] = str(v)
            else:
                result[k] = str(v)
        return result
    return {'output': str(outputs)}
