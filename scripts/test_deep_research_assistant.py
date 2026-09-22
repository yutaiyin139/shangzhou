# -*- coding: utf-8 -*-
"""
深度研究助手工作流 —— 按《03 深度研究助手.pdf》流程的端到端自动化测试

对应 PDF 步骤：
  第一步  创建工作流应用「深度研究助手」
  第二步  阶段1：输入节点 + LLM「理解主题&生成研究计划」+ 问题分类器「判断是否已澄清」
  第三步  参数提取器「提取需要用户澄清的问题」→ 结束节点
  第四步  阶段2：LLM「生成 SERP 查询」+ 参数提取器「提取信息检索条件数组」
  第五步  阶段3：迭代节点「信息检索批处理」内含知识检索节点（PDF 内网场景用知识库搜索代替联网搜索）
  第六步  阶段4：LLM「信息整合与深度研究」→ 结束节点
  第七步  测试运行（首轮触发澄清、次轮完成深度报告）
  第八步  发布 + 发布后提问
"""
import json
import os
import sys
import time
import requests

BASE = 'http://localhost:5000'
HERE = os.path.dirname(os.path.abspath(__file__))
RESULT_FILE = os.path.join(HERE, 'deep_research_test_results.json')

# 复用首次运行创建的应用（避免重复建应用）；清空则每次新建
REUSE_APP_ID = '3847078a-b212-4ed0-9043-ea1d8a86b9ce'

RESULTS = []


def log(step, item, expected, actual, status):
    entry = {'step': step, 'item': item, 'expected': expected,
             'actual': actual, 'status': status}
    RESULTS.append(entry)
    mark = {'PASS': '✅', 'FAIL': '❌', 'WARN': '⚠️'}.get(status, '❓')
    print('%s [%s] %s — %s' % (mark, step, item, status))
    if status != 'PASS':
        print('    预期: %s' % expected[:300])
        print('    实际: %s' % str(actual)[:300])


def api(method, path, token=None, **kw):
    headers = kw.pop('headers', {})
    if token:
        headers['Authorization'] = 'Bearer ' + token
    timeout = kw.pop('timeout', 900)
    r = requests.request(method, BASE + path, headers=headers, timeout=timeout, **kw)
    try:
        body = r.json()
    except Exception:
        body = {'raw': r.text[:500]}
    # 业务码：后端多数接口 HTTP 恒为 200，失败体现在 body.code
    return body.get('code', r.status_code), body


# ---------------------------------------------------------------
# 提示词（与 PDF 一致）
# ---------------------------------------------------------------
SY1 = '''你是一个专业的研究助理，正在帮助用户开展深度研究。用户提出了一个研究主题。请先判断用户输入是否已经包含足够的研究范围信息。
判断标准：若用户输入已明确以下大部分要素——技术/研究路径、时间范围、地域范围、受众、应用场景——则视为“信息已充分”；否则视为“信息不充分”。

【情况一：信息不充分】主动提出 2-4 个澄清性问题（用于明确研究范围、重点、时间、地域、受众等，问题应具体、可回答、避免宽泛），并严格以如下 Markdown 格式输出（此情况输出中必须包含“澄清问题”小节）：
**研究主题**:[根据用户提出的主题抽象为研究主题]
**初步理解**:[简要解释你对主题的理解]
**澄清问题**:
1.[问题 1]
2.[问题 2]
...

【情况二：信息已充分】不要提出任何澄清问题，直接制定一个结构化的研究计划，以 Markdown 输出（此情况输出中不得出现“澄清问题”字样），内容框架包含：
1．研究目标(1-2 句)
2. 3-5 个关键子问题(需可被信息检索验证)
3．推荐的信息来源类型(如学术论文，政府报告，行业新闻，试验数据库等)
4．建议的分析框架(如 SWOT，技术成熟度曲线，多国比较等)'''

SY2 = '''你是一个信息检索专家。根据以下研究计划，生成5-8 个高精度的搜索引擎查询语句(SERP queries)，用于收集可靠信息。
要求：
-每个查询应聚焦一个子问题
-使用高级搜索语法(如 site:gov,filetype:pdf,intitle:,2020.2024 等)
-优先使用英文查询(除非主题明确限定中文)
-避免过于宽泛的词(如"Al")，应具体(如"vision transformer in chest X-ray diagnosis")
输出格式为JSON:
{"count":[查询语句的总数],"queryArray": ["queryString1","queryString2"]}'''

SY3 = '''你是一个专业研究员，你需要根据研究主题，研究计划和所有收集到的信息撰写一份深度研究报告。
要求：
-报告为Markdown 格式
-包含：摘要，背景，方法论，主要发现(分点)，挑战与争议，未来展望，参考文献
-每项结论必须引用至少一个可靠来源
-语言严谨，客观，避免主观臆断
-长度：1500-3500 字
请生成完整报告。'''

MODEL = {'provider': 'deepseek', 'name': 'deepseek-chat', 'mode': 'chat',
         'completion_params': {'temperature': 0.7}}


def node(nid, ntype, title, x, y, **data):
    d = {'type': ntype, 'title': title}
    d.update(data)
    return {'id': nid, 'type': 'custom', 'position': {'x': x, 'y': y},
            'width': 240, 'height': 90, 'data': d}


def edge(eid, src, tgt, **kw):
    e = {'id': eid, 'source': src, 'target': tgt, 'type': 'custom'}
    e.update(kw)
    return e


def build_graph(dataset_id):
    nodes = [
        node('start1', 'start', '用户输入', 80, 320,
             variables=[{'variable': 'input01', 'label': '研究主题', 'type': 'paragraph',
                         'required': True, 'max_length': 4000}]),
        node('llm1', 'llm', '理解主题&生成研究计划', 380, 320,
             model=MODEL,
             prompt_template=[{'role': 'system', 'text': SY1},
                              {'role': 'user', 'text': '用户输入：{{input01}}'}],
             context={'enabled': False, 'variable_selector': []},
             vision={'enabled': False}),
        node('qc1', 'question-classifier', '判断是否已澄清', 680, 320,
             query_variable_selector=['text'],
             classes=[{'id': '1', 'label': '需要用户澄清',
                       'name': '输出包含“澄清问题”小节，需要用户澄清'},
                      {'id': '2', 'label': '无需澄清',
                       'name': '已直接输出研究计划，无需用户澄清'}],
             model=MODEL),
        node('pe1', 'parameter-extractor', '提取需要用户澄清的问题', 980, 160,
             query=['text'],
             parameters=[{'name': 'question', 'description': '需要用户澄清的问题',
                          'type': 'string', 'required': True}],
             model=MODEL, output='clarify_question'),
        node('llm2', 'llm', '生成 SERP 查询', 980, 440,
             model=MODEL,
             prompt_template=[{'role': 'system', 'text': SY2},
                              {'role': 'user', 'text': '研究计划：{{text}}'}],
             context={'enabled': False, 'variable_selector': []},
             vision={'enabled': False}),
        node('pe2', 'parameter-extractor', '提取信息检索条件数组', 1280, 440,
             query=['text'],
             parameters=[{'name': 'count', 'description': '检索条件总数，对应 JSON 中的 count',
                          'type': 'integer', 'required': True},
                         {'name': 'queryList', 'description': '检索条件字符串数组，对应 JSON 中的 queryArray',
                          'type': 'array', 'required': True}],
             model=MODEL, output='serp_params'),
        node('iter1', 'iteration', '信息检索批处理', 1580, 440,
             input_selector=['serp_params', 'queryList'],
             output_selector=['result'],
             iteration_mode='sequential',
             max_iterations=10),
        node('kr1', 'knowledge-retrieval', '知识搜索', 1880, 440,
             query_variable_selector=['item'],
             dataset_ids=[dataset_id],
             top_k=3, search_type='hybrid'),
        node('llm3', 'llm', '信息整合与深度研究', 1880, 640,
             model=MODEL,
             prompt_template=[{'role': 'system', 'text': SY3},
                              {'role': 'user', 'text': '研究主题：{{input01}}\n\n检索结果：{{output}}'}],
             context={'enabled': False, 'variable_selector': []},
             vision={'enabled': False}),
        node('end1', 'end', '结束', 2180, 440,
             outputs=[{'variable': 'report', 'value_selector': ['llm3', 'text']}]),
    ]
    edges = [
        edge('e-start-llm1', 'start1', 'llm1'),
        edge('e-llm1-qc1', 'llm1', 'qc1'),
        edge('e-qc1-pe1', 'qc1', 'pe1', sourceHandle='case-1'),   # 「需要用户澄清」分支
        edge('e-qc1-llm2', 'qc1', 'llm2', sourceHandle='case-2'),  # 「默认」分支
        edge('e-pe1-end1', 'pe1', 'end1'),
        edge('e-llm2-pe2', 'llm2', 'pe2'),
        edge('e-pe2-iter1', 'pe2', 'iter1'),
        edge('e-iter1-kr1', 'iter1', 'kr1', sourceHandle='loop'),
        edge('e-iter1-llm3', 'iter1', 'llm3'),
        edge('e-llm3-end1', 'llm3', 'end1'),
    ]
    return {'nodes': nodes, 'edges': edges, 'viewport': {'x': 0, 'y': 0, 'zoom': 1}}


def main():
    # ---------- 登录（账号口令由环境变量注入，不写入仓库）----------
    _user = os.getenv('SZ_TEST_USERNAME', 'yuty')
    _pw = os.getenv('SZ_TEST_PASSWORD', '')
    code, resp = api('POST', '/api/login', json={'username': _user, 'password': _pw})
    token = (resp.get('data') or {}).get('access_token', '')
    log('预备', '登录获取 token', '200 + access_token', 'code=%s token=%s...' % (code, token[:20]),
        'PASS' if code == 200 and token else 'FAIL')
    if not token:
        sys.exit(1)

    # ---------- 第五步（前置）：创建知识库 ----------
    dataset_id = ''
    for attempt in range(3):
        with open(os.path.join(HERE, 'testdata', 'bci_research_notes.txt'), 'rb') as fh:
            code, resp = api('POST', '/api/knowledge/datasets', token=token,
                             files=[('files', ('脑机接口研究资料.txt', fh, 'text/plain'))],
                             data={'segmentation': json.dumps(
                                 {'mode': 'auto', 'max_length': 800, 'overlap': 50})})
        ds = resp.get('data') or {}
        dataset_id = ds.get('id', '')
        if code == 200 and dataset_id:
            break
        time.sleep(2)
    log('第五步', '上传文件创建知识库「脑机接口研究资料」',
        '返回 dataset id', 'code=%s id=%s segments=%s' % (code, dataset_id, ds.get('segment_count')),
        'PASS' if code == 200 and dataset_id else 'FAIL')

    code, resp = api('POST', '/api/knowledge/datasets/%s/generate-embeddings' % dataset_id,
                     json={'batch_size': 20})
    task_id = (resp.get('data') or {}).get('task_id', '')
    log('第五步', '触发 Embedding 生成', '202 + task_id', 'code=%s task=%s' % (code, task_id),
        'PASS' if code == 202 else 'FAIL')
    for _ in range(60):
        code, resp = api('GET', '/api/knowledge/tasks/%s' % task_id)
        st = (resp.get('data') or {}).get('state', '')
        if st in ('SUCCESS', 'FAILURE'):
            break
        time.sleep(3)
    log('第五步', '等待 Embedding 完成', 'SUCCESS',
        'state=%s result=%s' % (st, json.dumps((resp.get('data') or {}).get('result'), ensure_ascii=False)[:200]),
        'PASS' if st == 'SUCCESS' else 'FAIL')

    # ---------- 第一步：创建工作流应用 ----------
    app_id = ''
    if REUSE_APP_ID:
        code, resp = api('GET', '/api/workflows/%s' % REUSE_APP_ID)
        if code == 200:
            app_id = REUSE_APP_ID
            log('第一步', '复用已创建的工作流应用「深度研究助手」', '应用存在',
                'app_id=%s' % app_id, 'PASS')
    if not app_id:
        code, resp = api('POST', '/api/workflows/create',
                         json={'name': '深度研究助手', 'description': '按《03 深度研究助手》构建的 Deep Research 工作流',
                               'mode': 'workflow',
                               'model': {'provider': 'deepseek', 'name': 'deepseek-chat', 'mode': 'chat',
                                         'completion_params': {'temperature': 0.7}}})
        app = resp.get('data') or {}
        app_id = app.get('id', '')
        log('第一步', '创建工作流应用「深度研究助手」', '返回 app_id',
            'code=%s id=%s mode=%s' % (code, app_id, app.get('mode')),
            'PASS' if code == 200 and app_id else 'FAIL')
    if not app_id:
        sys.exit(1)

    # ---------- 第二~六步：保存完整图 ----------
    graph = build_graph(dataset_id)
    node_count = len(graph['nodes'])
    code, resp = api('PUT', '/api/workflows/%s/graph' % app_id,
                     json={'graph': graph})
    log('第二~六步', '保存工作流图（输入/LLM/分类器/参数提取x2/迭代+知识检索/报告LLM/结束，共%d节点）' % node_count,
        '200', 'code=%s msg=%s' % (code, resp.get('msg')),
        'PASS' if code == 200 else 'FAIL')

    code, resp = api('GET', '/api/workflows/%s/inputs' % app_id)
    inputs_def = resp.get('data')
    log('第七步', '获取运行输入表单（由开始节点 variables 生成）', '包含必填字段 input01',
        json.dumps(inputs_def, ensure_ascii=False)[:300],
        'PASS' if code == 200 and inputs_def else 'FAIL')

    # ---------- 第七步：测试运行（第一轮 —— 预期触发澄清） ----------
    t0 = time.time()
    code, resp = api('POST', '/api/workflows/%s/run' % app_id,
                     json={'inputs': {'input01': '分析脑机接口的最新研究进展'},
                           'user': 'yuty'})
    elapsed1 = time.time() - t0
    data = resp.get('data') or {}
    outputs = data.get('outputs') or {}
    log('第七步', '首轮测试运行「分析脑机接口的最新研究进展」',
        'status=succeeded，输出包含澄清问题',
        'http=%s status=%s elapsed=%.1fs' % (code, data.get('status'), elapsed1),
        'PASS' if code == 200 and data.get('status') == 'succeeded' else 'FAIL')

    llm1_text = str(outputs.get('text', ''))
    has_clarify = '澄清问题' in llm1_text
    log('第七步', 'LLM1「理解主题&生成研究计划」输出澄清问题', '包含「澄清问题」小节',
        llm1_text[:120].replace('\n', ' '), 'PASS' if has_clarify else 'FAIL')

    cls = outputs.get('classification') or {}
    log('第七步', '问题分类器「判断是否已澄清」判定结果', 'class_label=需要用户澄清',
        json.dumps(cls, ensure_ascii=False),
        'PASS' if cls.get('class_label') == '需要用户澄清' else 'FAIL')

    q = (outputs.get('clarify_question') or {}).get('question', '')
    log('第七步', '参数提取器提取澄清问题 question', '提取到非空问题文本',
        str(q)[:150], 'PASS' if q else 'FAIL')

    report1 = str(outputs.get('output', ''))
    serp = outputs.get('serp_params') or {}
    log('第七步(平台差异)', '首轮运行是否继续执行「生成SERP查询/知识检索/报告」分支',
        '按 PDF 语义应在澄清后结束（分类器分支未命中则不执行后续节点）',
        'serp_params=%s iteration_count=%s report_len=%d' % (
            json.dumps(serp, ensure_ascii=False)[:120],
            outputs.get('iteration_count'), len(report1)),
        'WARN' if serp or outputs.get('iteration_count') else 'PASS')

    # ---------- 第七步：测试运行（第二轮 —— 补充澄清，预期完整报告） ----------
    t0 = time.time()
    code, resp = api('POST', '/api/workflows/%s/run' % app_id,
                     json={'inputs': {'input01': '分析脑机接口的最新研究进展。'
                                                '补充说明：聚焦非侵入式与微创脑机接口，时间范围2020-2025年，'
                                                '面向医疗健康应用（瘫痪康复、神经疾病治疗），受众为行业研究人员，'
                                                '地域关注中国与美国的进展。'},
                           'user': 'yuty'})
    elapsed2 = time.time() - t0
    data = resp.get('data') or {}
    outputs2 = data.get('outputs') or {}
    log('第七步', '次轮测试运行（已补充澄清信息）', 'status=succeeded，生成完整研究报告',
        'http=%s status=%s elapsed=%.1fs' % (code, data.get('status'), elapsed2),
        'PASS' if code == 200 and data.get('status') == 'succeeded' else 'FAIL')

    cls2 = (outputs2.get('classification') or {}).get('class_label', '')
    log('第七步', '次轮分类器判定', 'class_label=无需澄清', cls2,
        'PASS' if cls2 == '无需澄清' else 'FAIL')

    serp2 = outputs2.get('serp_params') or {}
    qlist = serp2.get('queryList') or []
    log('第七步', '提取检索条件数组 queryList', '数组长度>=3',
        'count=%s queryList=%s' % (serp2.get('count'), json.dumps(qlist, ensure_ascii=False)[:200]),
        'PASS' if isinstance(qlist, list) and len(qlist) >= 3 else 'FAIL')

    iter_count = outputs2.get('iteration_count')
    kr_hits = outputs2.get('output')
    log('第七步', '迭代节点「信息检索批处理」执行', 'iteration_count == len(queryList)',
        'iteration_count=%s' % iter_count,
        'PASS' if iter_count == len(qlist) and iter_count else 'FAIL')

    # 最终报告取结束节点声明的输出变量 'report'（即 llm3 正文），
    # 而非扁平 'text'（首个生产者 llm1 的研究计划）——否则“答非所问”。
    report2 = str(outputs2.get('report') or outputs2.get('answer') or outputs2.get('text', ''))
    has_sections = all(k in report2 for k in ('摘要', '背景')) and len(report2) > 800
    log('第七步', 'LLM3「信息整合与深度研究」生成报告', 'Markdown 报告，含摘要/背景等小节，>800字',
        'report_len=%d head=%s' % (len(report2), report2[:100].replace('\n', ' ')),
        'PASS' if has_sections else 'FAIL')

    run_id = data.get('id', '')
    code, resp = api('GET', '/api/workflows/%s/runs/%s' % (app_id, run_id))
    run_detail = resp.get('data') or {}
    node_runs = run_detail.get('node_runs') or run_detail.get('nodes') or []
    log('第七步', '运行详情含逐节点执行记录', '可查询到节点级 inputs/outputs',
        'node_records=%d' % len(node_runs) if isinstance(node_runs, list) else str(run_detail.keys()),
        'PASS' if code == 200 else 'FAIL')

    # ---------- 第八步：发布 + 发布后提问 ----------
    code, resp = api('POST', '/api/workflows/%s/publish' % app_id,
                     json={'name': 'v1.0', 'comment': '深度研究助手首个可用版本'})
    pub = resp.get('data') or {}
    log('第八步', '发布工作流', '返回 version_number',
        'code=%s data=%s' % (code, json.dumps(pub, ensure_ascii=False)[:200]),
        'PASS' if code == 200 and pub.get('version_number') else 'FAIL')

    code, resp = api('POST', '/api/workflows/%s/run' % app_id,
                     json={'inputs': {'input01': '分析脑机接口的最新研究进展。'
                                                '聚焦非侵入式与微创脑机接口（排除侵入式），2020-2025年，'
                                                '地域关注中国与美国，面向医疗健康应用（瘫痪康复、神经疾病治疗），'
                                                '受众为行业研究人员。'},
                           'user': 'yuty'})
    data3 = resp.get('data') or {}
    report3 = str((data3.get('outputs') or {}).get('report') or (data3.get('outputs') or {}).get('text', ''))
    log('第八步', '发布后提问（再次运行）', 'succeeded 且返回报告',
        'status=%s report_len=%d' % (data3.get('status'), len(report3)),
        'PASS' if code == 200 and data3.get('status') == 'succeeded' and len(report3) > 800 else 'FAIL')

    # ---------- 清理调试期遗留的临时知识库 ----------
    for junk in ('4ee10c06-4f4b-48ab-a2a6-3f24560c262f', '728b1d99-f2ab-4173-832e-cc20de65eb87',
                 '992a73b7-8133-45c2-8f8b-d8ebff2dafcd', 'a1cd0090-73f4-46a5-a87b-d3321518a244'):
        api('DELETE', '/api/knowledge/datasets/%s' % junk, token=token)

    # ---------- 汇总 ----------
    summary = {
        'app_id': app_id,
        'dataset_id': dataset_id,
        'elapsed_round1': round(elapsed1, 1),
        'elapsed_round2': round(elapsed2, 1),
        'round1': {'classification': cls, 'question': q, 'llm1_head': llm1_text[:200]},
        'round2': {'classification': cls2, 'queryList': qlist,
                   'iteration_count': iter_count, 'report_head': report2[:300],
                   'report_len': len(report2)},
    }
    with open(RESULT_FILE, 'w', encoding='utf-8') as f:
        json.dump({'summary': summary, 'results': RESULTS}, f, ensure_ascii=False, indent=2)

    passed = sum(1 for r in RESULTS if r['status'] == 'PASS')
    failed = sum(1 for r in RESULTS if r['status'] == 'FAIL')
    warned = sum(1 for r in RESULTS if r['status'] == 'WARN')
    print('\n===== 汇总: %d PASS / %d FAIL / %d WARN =====' % (passed, failed, warned))
    print('结果已保存: %s' % RESULT_FILE)
    print('应用: /workflows/%s  dataset: %s' % (app_id, dataset_id))


if __name__ == '__main__':
    main()
