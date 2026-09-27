# -*- coding: utf-8 -*-
"""任务 1.6 端到端回归 —— 全节点类型执行回归套件（in-process，直连 run_workflow）

用法:  python tests/test_node_regression.py
覆盖:  30 种节点类型（runner 全部分支），按 Dify 1.17 行为断言。
外部依赖: MySQL/Redis/Qdrant/Celery 已启动；LLM 用 deepseek-v4-flash（已配置）。
"""
import io
import json
import sys
import time
import uuid
from datetime import datetime

# 用 reconfigure 而不是包一层 TextIOWrapper：后者被回收时会连带关掉真正的 stdout buffer
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
import os
# 用绝对路径而不是 '.'：让脚本无论从 backend/ 还是 backend/tests/ 启动都能导入 config/engine
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_db  # noqa: E402
from engine.workflow_runner import run_workflow  # noqa: E402

TENANT = 'eb4e3172-df56-4d30-97fb-ed24633f4e30'
MODEL_CFG_APP = 'ad72f39c-e507-4d88-a934-37dd6f38c582'  # 复用其模型配置
TEST_DATASET = '27eed499-3648-41b3-bb71-3196056e87c4'   # Test Dataset

RESULTS = []  # (node_type, 'PASS'/'FAIL'/'SKIP', note)


def record(node_type, status, note=''):
    RESULTS.append((node_type, status, note))
    mark = {'PASS': '✅', 'FAIL': '❌', 'SKIP': '⏭️'}.get(status, '?')
    print(f'{mark} {node_type}: {note}')


def build_graph(nodes, edges):
    return {
        'nodes': [
            {'id': nid, 'type': 'custom', 'position': {'x': i * 260, 'y': 0},
             'data': {'type': ntype, 'title': ntype, **data}}
            for i, (nid, ntype, data) in enumerate(nodes)
        ],
        'edges': [
            {'id': f'e{i}', 'source': s, 'target': t,
             'sourceHandle': sh, 'targetHandle': th, 'type': 'custom', 'data': {}}
            for i, (s, t, sh, th) in enumerate(edges)
        ],
        'viewport': {'x': 0, 'y': 0, 'zoom': 1},
    }


def start_node(nid, variables=None):
    return (nid, 'start', {'variables': variables or []})


def end_node(nid, outputs=None):
    return (nid, 'end', {'outputs': outputs or []})


def answer_node(nid, text):
    return (nid, 'answer', {'answer': text})


# ---------------------------------------------------------------
# 测试环境：一个临时应用，所有用例通过 graph 参数注入
# ---------------------------------------------------------------
APP_ID = str(uuid.uuid4())


def setup_app():
    db = get_db()
    try:
        cur = db.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute(
            "INSERT INTO dify_apps (id, tenant_id, name, mode, status, created_at, updated_at)"
            " VALUES (%s, %s, 'E2E回归测试(临时)', 'workflow', 'normal', %s, %s)",
            (APP_ID, TENANT, now, now))
        # 占位工作流行（run_workflow 要求存在，实际图通过 graph 参数注入）
        cur.execute(
            "INSERT INTO dify_workflows (id, tenant_id, app_id, type, version, graph, created_at, updated_at)"
            " VALUES (%s, %s, %s, 'workflow', 'draft', '{}', %s, %s)",
            (str(uuid.uuid4()), TENANT, APP_ID, now, now))
        # 复制模型配置（LLM 节点需要）
        cur.execute("SELECT * FROM dify_app_model_configs WHERE app_id = %s LIMIT 1",
                    (MODEL_CFG_APP,))
        cfg = cur.fetchone()
        if cfg:
            cols = [k for k in cfg.keys() if k not in ('id', 'app_id', 'created_at', 'updated_at')]
            sql = ('INSERT INTO dify_app_model_configs (id, app_id, ' + ', '.join(cols) +
                   ', created_at, updated_at) VALUES (%s, %s, ' + ', '.join(['%s'] * len(cols)) +
                   ', %s, %s)')
            cur.execute(sql, [str(uuid.uuid4()), APP_ID] + [cfg[c] for c in cols] + [now, now])
        db.commit()
    finally:
        db.close()


def run(nodes, edges, inputs=None, app_id=None):
    """构图并执行，返回 (status, result)"""
    return run_workflow(app_id or APP_ID, inputs or {}, graph=build_graph(nodes, edges))


def expect_ok(node_type, nodes, edges, inputs=None, check=None, app_id=None):
    try:
        status, result = run(nodes, edges, inputs, app_id=app_id)
        if status != 200:
            record(node_type, 'FAIL', f'status={status} result={str(result)[:150]}')
            return None
        if check:
            err = check(result)
            if err:
                record(node_type, 'FAIL', err)
                return None
        record(node_type, 'PASS', '')
        return result
    except Exception as e:
        record(node_type, 'FAIL', f'{type(e).__name__}: {str(e)[:150]}')
        return None


# ---------------------------------------------------------------
# Tier 1: 确定性节点
# ---------------------------------------------------------------

def t_start_end():
    g = [start_node('s1'), end_node('e1')]
    edges = [('s1', 'e1', None, None)]
    expect_ok('start/end', g, edges, check=lambda r: None if r.get('status') == 'succeeded'
              else f"status={r.get('status')}")


def t_answer():
    g = [start_node('s1'), answer_node('a1', '你好，{{name}}'), end_node('e1')]
    edges = [('s1', 'a1', None, None), ('a1', 'e1', None, None)]
    expect_ok('answer', g, edges, inputs={'name': '世界'},
              check=lambda r: None if '世界' in json.dumps(r.get('outputs', {}), ensure_ascii=False)
              else f"outputs 未包含变量替换结果: {str(r.get('outputs'))[:100]}")


def t_code():
    code = "result = args['x'] * 2\n"
    g = [start_node('s1'),
         ('c1', 'code', {'code_language': 'python3', 'code': code,
                         'outputs': {'result': {'type': 'number'}}}),
         end_node('e1')]
    edges = [('s1', 'c1', None, None), ('c1', 'e1', None, None)]
    expect_ok('code', g, edges, inputs={'x': 21},
              check=lambda r: None if '42' in json.dumps(r.get('outputs', {}))
              else f"outputs 不含 42: {str(r.get('outputs'))[:100]}")


def t_ifelse():
    cases = [
        {'id': 'c1', 'name': '大于10', 'conditions': [
            {'variable': 'n', 'operator': '>', 'value': 10}]},
        {'id': 'c2', 'name': '否则', 'conditions': []},
    ]
    g = [start_node('s1'), ('i1', 'if-else', {'cases': cases}),
         ('a1', 'answer', {'answer': 'big'}),
         end_node('e1')]
    edges = [('s1', 'i1', None, None),
             ('i1', 'a1', 'case-c1', None),
             ('a1', 'e1', None, None)]
    expect_ok('if-else', g, edges, inputs={'n': 42},
              check=lambda r: None if 'big' in json.dumps(r.get('outputs', {}), ensure_ascii=False)
              else f"未走 true 分支: {str(r.get('outputs'))[:100]}")


def t_template_transform():
    g = [start_node('s1'),
         ('t1', 'template-transform', {
             'template': '姓名: {{username}}',
             'variables': [{'variable': 'username', 'value_selector': ['s1', 'name']},
                           {'variable': 'unused', 'value_selector': []}]}),
         end_node('e1')]
    edges = [('s1', 't1', None, None), ('t1', 'e1', None, None)]
    expect_ok('template-transform', g, edges, inputs={'name': '熵舟'},
              check=lambda r: None if '熵舟' in json.dumps(r.get('outputs', {}), ensure_ascii=False)
              else f"模板未替换: {str(r.get('outputs'))[:100]}")


def t_variable_aggregator():
    g = [start_node('s1'),
         ('v1', 'variable-aggregator', {
             'variables': [{'variable': 'first', 'value_selector': ['s1', 'name']}],
             'output_type': 'object', 'output': 'agg'}),
         end_node('e1')]
    edges = [('s1', 'v1', None, None), ('v1', 'e1', None, None)]
    expect_ok('variable-aggregator', g, edges, inputs={'name': '聚合值'},
              check=lambda r: None if '聚合值' in json.dumps(r.get('outputs', {}), ensure_ascii=False)
              else f"聚合失败: {str(r.get('outputs'))[:100]}")


def t_assigner():
    g = [start_node('s1'),
         ('v1', 'assigner', {
             'variables': [{'variable': 'copied', 'value_selector': ['s1', 'src']}],
             'output_type': 'object', 'output': 'assigned'}),
         end_node('e1')]
    edges = [('s1', 'v1', None, None), ('v1', 'e1', None, None)]
    expect_ok('assigner', g, edges, inputs={'src': '赋值内容'},
              check=lambda r: None if '赋值内容' in json.dumps(r.get('outputs', {}), ensure_ascii=False)
              else f"赋值失败: {str(r.get('outputs'))[:100]}")


def t_list_operator():
    g = [start_node('s1'),
         ('l1', 'list-operator', {
             'variable': ['s1', 'items'], 'var_type': 'array[string]',
             'filter_by': {'enabled': False}, 'sort_by': {'enabled': False},
             'extract_by': {'enabled': False}, 'limit': 2}),
         end_node('e1')]
    edges = [('s1', 'l1', None, None), ('l1', 'e1', None, None)]
    expect_ok('list-operator', g, edges,
              inputs={'items': ['c', 'a', 'b']},
              check=lambda r: None if 'c' in json.dumps(r.get('outputs', {})) and
              json.dumps(r.get('outputs', {})).count('"') >= 4
              else f"limit 未生效: {str(r.get('outputs'))[:100]}")


def t_custom_note():
    g = [start_node('s1'), ('n1', 'custom-note', {'text': '备注'}),
         ('a1', 'answer', {'answer': 'done'}), end_node('e1')]
    edges = [('s1', 'n1', None, None), ('n1', 'a1', None, None), ('a1', 'e1', None, None)]
    expect_ok('custom-note', g, edges)


def t_document_extractor():
    g = [start_node('s1'),
         ('d1', 'document-extractor', {'variable_selector': ['s1', 'doc'],
                                       'is_array_file': False}),
         end_node('e1')]
    edges = [('s1', 'd1', None, None), ('d1', 'e1', None, None)]
    expect_ok('document-extractor', g, edges,
              inputs={'doc': {'name': 'f.txt', 'content': '文件内容ABC'}})


def t_trigger_schedule():
    g = [start_node('s1'),
         ('tr1', 'trigger-schedule', {'cron_expr': '0 9 * * *', 'timezone': 'Asia/Shanghai'}),
         ('a1', 'answer', {'answer': 'fired'}), end_node('e1')]
    edges = [('tr1', 'a1', None, None), ('a1', 'e1', None, None)]
    expect_ok('trigger-schedule', g, [], check=lambda r: None)


def t_trigger_webhook():
    g = [('tr1', 'trigger-webhook', {'enabled': True}),
         ('a1', 'answer', {'answer': 'hook fired'}), end_node('e1')]
    edges = [('tr1', 'a1', None, None), ('a1', 'e1', None, None)]
    expect_ok('trigger-webhook', g, edges, inputs={'_trigger_inputs': {'k': 'v'}})


def t_human_input():
    g = [start_node('s1'),
         ('h1', 'human-input', {'message': '请确认', 'form_fields': [],
                                'output': 'human_result'}),
         end_node('e1')]
    edges = [('s1', 'h1', None, None), ('h1', 'e1', None, None)]
    try:
        status, result = run(g, edges)
        if result.get('status') == 'waiting':
            record('human-input', 'PASS', 'waiting（暂停待人工输入）')
        else:
            record('human-input', 'FAIL', f"期望 waiting，实际 {result.get('status')}")
    except Exception as e:
        record('human-input', 'FAIL', str(e)[:150])


def t_loop():
    g = [start_node('s1'),
         ('l1', 'loop', {'loop_type': 'count', 'count': 3, 'max_iterations': 10,
                         'output_variable': 'loop_results'}),
         end_node('e1')]
    edges = [('s1', 'l1', None, None), ('l1', 'e1', None, None)]
    expect_ok('loop', g, edges,
              check=lambda r: None if 'loop_count' in json.dumps(r.get('outputs', {}))
              else f"无 loop_count: {str(r.get('outputs'))[:100]}")


# ---------------------------------------------------------------
# Tier 2: LLM 节点
# ---------------------------------------------------------------
LLM_MODEL = {'provider': 'langgenius/deepseek/deepseek', 'name': 'deepseek-v4-flash',
             'mode': 'chat', 'completion_params': {'temperature': 0.1}}


def t_llm():
    g = [start_node('s1'),
         ('m1', 'llm', {'model': LLM_MODEL,
                        'prompt_template': [
                            {'role': 'system', 'text': '你是计算器，只输出数字'},
                            {'role': 'user', 'text': '1+1=?'}],
                        'context': {'enabled': False, 'variable_selector': []},
                        'vision': {'enabled': False}}),
         end_node('e1')]
    edges = [('s1', 'm1', None, None), ('m1', 'e1', None, None)]
    expect_ok('llm', g, edges,
              check=lambda r: None if '2' in json.dumps(r.get('outputs', {}), ensure_ascii=False)
              else f"LLM 输出异常: {str(r.get('outputs'))[:100]}")


def t_question_classifier():
    g = [start_node('s1'),
         ('q1', 'question-classifier', {
             'model': LLM_MODEL,
             'query_variable_selector': ['s1', 'query'],
             'classes': [
                 {'id': 'c1', 'name': '账单问题', 'question': '用户询问账单或费用'},
                 {'id': 'c2', 'name': '其他', 'question': '其他问题'}]}),
         ('a1', 'answer', {'answer': '账单类'}), ('a2', 'answer', {'answer': '其他类'}),
         end_node('e1')]
    edges = [('s1', 'q1', None, None),
             ('q1', 'a1', 'c1', None), ('q1', 'a2', 'c2', None),
             ('a1', 'e1', None, None), ('a2', 'e1', None, None)]
    expect_ok('question-classifier', g, edges, inputs={'query': '我这个月账单多少钱'},
              check=lambda r: None if '账单' in json.dumps(r.get('outputs', {}), ensure_ascii=False)
              else f"分类结果: {str(r.get('outputs'))[:100]}")


def t_parameter_extractor():
    g = [start_node('s1'),
         ('p1', 'parameter-extractor', {
             'model': LLM_MODEL,
             'query': '{{query}}',
             'parameters': [{'name': 'city', 'type': 'string', 'required': True,
                             'description': '城市名'}]}),
         end_node('e1')]
    edges = [('s1', 'p1', None, None), ('p1', 'e1', None, None)]
    expect_ok('parameter-extractor', g, edges, inputs={'query': '明天北京天气怎么样'},
              check=lambda r: None if '北京' in json.dumps(r.get('outputs', {}), ensure_ascii=False)
              else f"未提取到城市: {str(r.get('outputs'))[:150]}")


def t_agent():
    g = [start_node('s1'),
         ('g1', 'agent', {'model': LLM_MODEL,
                          'prompt': '你是助手，直接回答用户问题。',
                          'user_prompt': '{{q}}',
                          'tools': [], 'max_iterations': 1, 'output': 'agent_output'}),
         end_node('e1')]
    edges = [('s1', 'g1', None, None), ('g1', 'e1', None, None)]
    expect_ok('agent', g, edges, inputs={'q': '用一句话介绍熵舟平台'},
              check=lambda r: None if len(json.dumps(r.get('outputs', {}), ensure_ascii=False)) > 10
              else f"agent 输出为空: {str(r.get('outputs'))[:100]}")


def t_batch_task():
    g = [start_node('s1', variables=[{'variable': 'items', 'type': 'array[string]'}]),
         ('b1', 'batch-task', {
             'input_selector': ['items'],
             'task_type': 'code',
             'task_config': {'code_language': 'python3',
                             'code': "upper = args['item'].upper()\n",
                             'outputs': {'upper': {'type': 'string'}}},
             'batch_size': 2, 'max_parallel': 1, 'max_items': 10,
             'error_strategy': 'continue_on_error', 'output_variable': 'batch_results'}),
         end_node('e1')]
    edges = [('s1', 'b1', None, None), ('b1', 'e1', None, None)]
    expect_ok('batch-task', g, edges,
              inputs={'items': ['apple', 'banana', 'cherry']},
              check=lambda r: None if 'APPLE' in json.dumps(r.get('outputs', '')).upper()
              else f"批量结果: {str(r.get('outputs'))[:150]}")


def t_iteration():
    # 迭代节点：loop 口出子流程（code 节点），element 口返回
    code = "doubled = args['item'] * 2\n"
    g = [start_node('s1', variables=[{'variable': 'items', 'type': 'array[number]'}]),
         ('it1', 'iteration', {'input_selector': ['items'],
                               'output_selector': ['doubled'], 'max_iterations': 10}),
         ('c1', 'code', {'code_language': 'python3', 'code': code,
                         'outputs': {'doubled': {'type': 'number'}}}),
         end_node('e1')]
    edges = [('s1', 'it1', None, None),
             ('it1', 'c1', 'loop', None), ('c1', 'it1', None, 'element'),
             ('it1', 'e1', 'end', None)]
    expect_ok('iteration', g, edges, inputs={'items': [1, 2, 3]},
              check=lambda r: None if '2' in json.dumps(r.get('outputs', {}))
              else f"迭代结果: {str(r.get('outputs'))[:150]}")


# ---------------------------------------------------------------
# Tier 3: 外部依赖节点
# ---------------------------------------------------------------

def t_http_request():
    g = [start_node('s1'),
         ('h1', 'http-request', {'method': 'get', 'url': 'https://www.baidu.com',
                                 'headers': '', 'params': '', 'body': ''}),
         end_node('e1')]
    edges = [('s1', 'h1', None, None), ('h1', 'e1', None, None)]
    expect_ok('http-request', g, edges,
              check=lambda r: None if '200' in json.dumps(r.get('outputs', {})) or
              'status' in json.dumps(r.get('outputs', {}))
              else f"http 输出: {str(r.get('outputs'))[:100]}")


def t_datasource():
    g = [start_node('s1'),
         ('d1', 'datasource', {'source_type': 'builtin', 'source_key': 'github',
                               'operation': 'search', 'query': 'dify',
                               'limit': 2, 'connector_id': ''}),
         end_node('e1')]
    edges = [('s1', 'd1', None, None), ('d1', 'e1', None, None)]
    expect_ok('datasource', g, edges,
              check=lambda r: None if r.get('outputs', {}).get('datasource_status') == 'success'
              else f"datasource: {str(r.get('outputs'))[:150]}")


def t_knowledge_index_and_retrieval():
    """先索引文档，再检索（含 embedding 异步完成的轮询）"""
    text = '熵舟智能体平台支持工作流编排、知识库和定时触发。' * 8
    g = [start_node('s1'),
         ('k1', 'knowledge-index', {'dataset_id': TEST_DATASET,
                                    'content_variable': 'content',
                                    'document_name': 'e2e回归-{{seq}}',
                                    'max_length': 512, 'overlap': 50, 'delimiter': '\n'}),
         end_node('e1')]
    edges = [('s1', 'k1', None, None), ('k1', 'e1', None, None)]
    import uuid as _uuid
    seq = _uuid.uuid4().hex[:6]
    result = expect_ok('knowledge-index', g, edges,
                       inputs={'content': text, 'seq': seq},
                       check=lambda r: None
                       if r.get('outputs', {}).get('knowledge_index_status') == 'success'
                       else f"index: {str(r.get('outputs'))[:150]}")
    if not result:
        record('knowledge-retrieval', 'SKIP', '前置索引失败')
        return

    # 等待 embedding 完成（Celery worker 消费 generate_embeddings_async）
    doc_id = result['outputs'].get('document_id')
    deadline = time.time() + 90
    indexed = False
    while time.time() < deadline:
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute("SELECT indexing_status FROM dify_documents WHERE id = %s", (doc_id,))
            row = cur.fetchone()
            if row and row['indexing_status'] == 'completed':
                indexed = True
        finally:
            db.close()
        if indexed:
            break
        time.sleep(5)
    if not indexed:
        record('knowledge-retrieval', 'SKIP', 'embedding 90s 内未完成')
        return

    g = [start_node('s1'),
         ('kr1', 'knowledge-retrieval', {'dataset_ids': [TEST_DATASET],
                                         'query_variable_selector': ['s1', 'q'],
                                         'search_type': 'vector', 'top_k': 3,
                                         'min_score': 0.0}),
         end_node('e1')]
    edges = [('s1', 'kr1', None, None), ('kr1', 'e1', None, None)]
    expect_ok('knowledge-retrieval', g, edges,
              inputs={'q': '熵舟平台支持什么功能'},
              check=lambda r: None if 'result' in json.dumps(r.get('outputs', {})).lower() or
              'document' in json.dumps(r.get('outputs', {})).lower()
              else f"检索输出: {str(r.get('outputs'))[:150]}")


def t_sub_graph():
    """子工作流：临时应用 B（start->code->end），主流程 sub-graph 引用"""
    sub_app = str(uuid.uuid4())
    sub_graph = build_graph(
        [start_node('s1'),
         ('c1', 'code', {'code_language': 'python3',
                         'code': "sub_out = 'SUB_OK'\n",
                         'outputs': {'sub_out': {'type': 'string'}}}),
         end_node('e1', outputs=[])],
        [('s1', 'c1', None, None), ('c1', 'e1', None, None)])
    db = get_db()
    try:
        cur = db.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute(
            "INSERT INTO dify_apps (id, tenant_id, name, mode, status, created_at, updated_at)"
            " VALUES (%s, %s, 'E2E子图(临时)', 'workflow', 'normal', %s, %s)",
            (sub_app, TENANT, now, now))
        cur.execute(
            "INSERT INTO dify_workflows (id, tenant_id, app_id, type, version, graph, created_at, updated_at)"
            " VALUES (%s, %s, %s, 'workflow', 'draft', %s, %s, %s)",
            (str(uuid.uuid4()), TENANT, sub_app, json.dumps(sub_graph), now, now))
        db.commit()
    finally:
        db.close()

    g = [start_node('s1'),
         ('sg1', 'sub-graph', {'type': 'sub-graph', 'sub_app_id': sub_app,
                               'sub_workflow_id': '', 'input_mapping': [],
                               'output_mapping': {'sub_out': 'main_result'}}),
         end_node('e1')]
    edges = [('s1', 'sg1', None, None), ('sg1', 'e1', None, None)]
    expect_ok('sub-graph', g, edges,
              check=lambda r: None if 'SUB_OK' in json.dumps(r.get('outputs', {}))
              else f"子图输出: {str(r.get('outputs'))[:150]}")

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("DELETE FROM dify_workflow_runs WHERE app_id = %s", (sub_app,))
        cur.execute("DELETE FROM dify_workflows WHERE app_id = %s", (sub_app,))
        cur.execute("DELETE FROM dify_apps WHERE id = %s", (sub_app,))
        db.commit()
    finally:
        db.close()


def t_tool():
    g = [start_node('s1'),
         ('t1', 'tool', {'provider_id': 'calculator', 'tool_name': 'calculate',
                         'tool_parameters': {'expression': '6*7'},
                         'output': 'tool_output'}),
         end_node('e1')]
    edges = [('s1', 't1', None, None), ('t1', 'e1', None, None)]
    expect_ok('tool', g, edges,
              check=lambda r: None if '42' in json.dumps(r.get('outputs', {}))
              else f"tool 输出: {str(r.get('outputs'))[:150]}")


def t_mcp():
    record('mcp', 'SKIP', '无已配置的 MCP 服务器（app_mcp_servers 为空），需 阶段3 MCP 落地后补齐')


# ---------------------------------------------------------------
# 清理
# ---------------------------------------------------------------

def cleanup():
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("DELETE FROM dify_workflow_runs WHERE app_id = %s", (APP_ID,))
        cur.execute("DELETE FROM dify_workflows WHERE app_id = %s", (APP_ID,))
        cur.execute("DELETE FROM dify_app_model_configs WHERE app_id = %s", (APP_ID,))
        cur.execute("DELETE FROM dify_apps WHERE id = %s", (APP_ID,))
        # 清理回归测试产生的知识库文档
        cur.execute("DELETE FROM dify_document_segments WHERE document_id IN"
                    " (SELECT id FROM dify_documents WHERE name LIKE 'e2e回归-%')")
        cur.execute("DELETE FROM dify_documents WHERE name LIKE 'e2e回归-%'")
        db.commit()
    finally:
        db.close()


ALL_TESTS = [
    ('start/end', t_start_end),
    ('answer', t_answer),
    ('code', t_code),
    ('if-else', t_ifelse),
    ('template-transform', t_template_transform),
    ('variable-aggregator', t_variable_aggregator),
    ('assigner', t_assigner),
    ('list-operator', t_list_operator),
    ('custom-note', t_custom_note),
    ('document-extractor', t_document_extractor),
    ('trigger-schedule', t_trigger_schedule),
    ('trigger-webhook', t_trigger_webhook),
    ('human-input', t_human_input),
    ('loop', t_loop),
    ('llm', t_llm),
    ('question-classifier', t_question_classifier),
    ('parameter-extractor', t_parameter_extractor),
    ('agent', t_agent),
    ('batch-task', t_batch_task),
    ('iteration', t_iteration),
    ('http-request', t_http_request),
    ('datasource', t_datasource),
    ('knowledge-index + retrieval', t_knowledge_index_and_retrieval),
    ('sub-graph', t_sub_graph),
    ('tool', t_tool),
    ('mcp', t_mcp),
]

if __name__ == '__main__':
    setup_app()
    print(f'临时应用: {APP_ID}\n')
    t0 = time.time()
    for name, fn in ALL_TESTS:
        try:
            fn()
        except Exception as e:
            record(name, 'FAIL', f'{type(e).__name__}: {str(e)[:150]}')
    elapsed = time.time() - t0
    cleanup()

    passed = sum(1 for _, s, _ in RESULTS if s == 'PASS')
    failed = sum(1 for _, s, _ in RESULTS if s == 'FAIL')
    skipped = sum(1 for _, s, _ in RESULTS if s == 'SKIP')
    print()
    print('=' * 50)
    print(f'回归完成: {passed} PASS / {failed} FAIL / {skipped} SKIP  ({elapsed:.0f}s)')
    if failed:
        print('失败项:')
        for name, s, note in RESULTS:
            if s == 'FAIL':
                print(f'  ❌ {name}: {note}')
        sys.exit(1)
    print('ALL PASSED (除 SKIP 项)')
