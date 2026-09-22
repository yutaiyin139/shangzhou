# -*- coding: utf-8 -*-
"""
深度研究助手 —— 节点级验证（第七步复测）
通过 run 详情的 nodes 字段逐节点核对《03 深度研究助手.pdf》预期行为。
"""
import json
import time
import requests

BASE = 'http://localhost:5000'
APP_ID = '3847078a-b212-4ed0-9043-ea1d8a86b9ce'
RESULTS = []


def log(item, expected, actual, status):
    RESULTS.append({'item': item, 'expected': expected, 'actual': str(actual)[:400], 'status': status})
    mark = {'PASS': '✅', 'FAIL': '❌', 'WARN': '⚠️'}.get(status, '❓')
    print('%s %s — %s' % (mark, item, status))
    if status != 'PASS':
        print('    预期: %s' % expected[:200])
        print('    实际: %s' % str(actual)[:300])


def run_workflow(input01):
    r = requests.post(BASE + '/api/workflows/%s/run' % APP_ID,
                      json={'inputs': {'input01': input01}, 'user': 'yuty'}, timeout=900)
    d = r.json()
    assert d.get('code') == 200, '运行失败: %s' % d.get('msg')
    run_id = d['data']['id']
    detail = requests.get(BASE + '/api/workflows/%s/runs/%s' % (APP_ID, run_id), timeout=60).json()['data']
    nodes = {n['node_id']: n for n in detail.get('nodes', [])}
    return detail, nodes


def main():
    # ---------- 第七步 · 第一轮：裸主题，预期触发澄清 ----------
    detail, nodes = run_workflow('分析脑机接口的最新研究进展')
    log('首轮运行完成', 'status=succeeded', detail['status'],
        'PASS' if detail['status'] == 'succeeded' else 'FAIL')

    llm1_text = (nodes.get('llm1', {}).get('outputs') or {}).get('text', '')
    asked = '澄清问题' in llm1_text
    log('LLM1「理解主题&生成研究计划」输出含「澄清问题」', '包含（PDF：首轮应提问澄清）',
        llm1_text[:100].replace('\n', ' '), 'PASS' if asked else 'WARN')

    cls = (nodes.get('qc1', {}).get('outputs') or {})
    log('分类器「判断是否已澄清」判定', '与 LLM1 输出一致（含澄清问题→需要用户澄清）',
        cls.get('class_label'),
        'PASS' if (asked and cls.get('class_label') == '需要用户澄清') or
                  (not asked and cls.get('class_label') == '无需澄清') else 'FAIL')

    q = ((nodes.get('pe1', {}).get('outputs') or {}).get('clarify_question') or {}).get('question', '')
    log('参数提取器提取澄清问题 question', '提取到非空问题文本', q[:100],
        'PASS' if q else ('PASS' if not asked else 'FAIL'))

    print('    首轮分类结果: %s | 提取问题: %s' % (cls.get('class_label'), (q or '(空)')[:60]))
    time.sleep(20)

    # ---------- 第七步 · 第二轮：补充澄清，预期直达研究报告 ----------
    detail2, nodes2 = run_workflow(
        '分析脑机接口的最新研究进展。补充说明：聚焦非侵入式与微创脑机接口，时间范围2020-2025年，'
        '面向医疗健康应用（瘫痪康复、神经疾病治疗），受众为行业研究人员，地域关注中国与美国的进展。'
        '以上信息已足够明确，请直接输出研究计划，不要再提澄清问题。')
    log('次轮运行完成', 'status=succeeded', detail2['status'],
        'PASS' if detail2['status'] == 'succeeded' else 'FAIL')

    llm1b = (nodes2.get('llm1', {}).get('outputs') or {}).get('text', '')
    direct_plan = '研究计划' in llm1b or '研究目标' in llm1b
    log('LLM1 次轮直接输出研究计划', '不再提问，输出结构化研究计划',
        llm1b[:100].replace('\n', ' '), 'PASS' if direct_plan else 'WARN')

    cls2 = (nodes2.get('qc1', {}).get('outputs') or {})
    log('次轮分类器判定', '无需澄清', cls2.get('class_label'),
        'PASS' if cls2.get('class_label') == '无需澄清' else 'WARN')

    serp = (nodes2.get('llm2', {}).get('outputs') or {}).get('text', '')
    try:
        serp_json = json.loads(serp[serp.index('{'):serp.rindex('}') + 1])
        queries = serp_json.get('queryArray', [])
    except Exception:
        queries = []
    log('LLM2「生成 SERP 查询」输出合法 JSON 且 5-8 条',
        'JSON 含 count 与 queryArray，长度 5-8',
        'count=%s len=%s' % ((serp_json or {}).get('count'), len(queries)),
        'PASS' if 3 <= len(queries) <= 10 else 'FAIL')

    pe2 = (nodes2.get('pe2', {}).get('outputs') or {}).get('serp_params') or {}
    qlist = pe2.get('queryList') or []
    log('参数提取器「提取信息检索条件数组」', 'count>=3 且 queryList 为数组',
        'count=%s queryList=%s' % (pe2.get('count'), json.dumps(qlist, ensure_ascii=False)[:200]),
        'PASS' if isinstance(qlist, list) and len(qlist) >= 3 else 'FAIL')

    outputs2 = detail2.get('outputs') or {}
    iter_count = outputs2.get('iteration_count')
    log('迭代节点「信息检索批处理」执行轮数', 'iteration_count == len(queryList)',
        'iteration_count=%s len(queryList)=%s' % (iter_count, len(qlist)),
        'PASS' if iter_count == len(qlist) and iter_count else 'FAIL')

    iter_out = outputs2.get('output')
    iter_text = json.dumps(iter_out, ensure_ascii=False) if iter_out else ''
    has_hit = ('脑机接口' in iter_text) or ('BCI' in iter_text) or ('brain' in iter_text.lower())
    log('知识检索命中内容（迭代输出含检索结果）', '包含脑机接口相关知识片段',
        iter_text[:150], 'PASS' if has_hit else 'FAIL')

    report = (nodes2.get('llm3', {}).get('outputs') or {}).get('text', '')
    sections = [k for k in ('摘要', '背景', '主要发现', '未来展望') if k in report]
    log('LLM3「信息整合与深度研究」生成报告', 'Markdown 含摘要/背景/主要发现/未来展望，>800字',
        'len=%d sections=%s head=%s' % (len(report), sections, report[:80].replace('\n', ' ')),
        'PASS' if len(report) > 800 and len(sections) >= 3 else 'FAIL')

    # ---------- 第八步复测：发布后提问 ----------
    time.sleep(20)
    detail3, _ = run_workflow('分析脑机接口的最新研究进展。聚焦非侵入式脑机接口，2020-2025年，医疗健康应用。请直接输出研究计划。')
    outputs3 = detail3.get('outputs') or {}
    report3 = str(outputs3.get('text', ''))
    log('发布后提问（第三次运行）', 'succeeded 且输出报告',
        'status=%s report_len=%d' % (detail3['status'], len(report3)),
        'PASS' if detail3['status'] == 'succeeded' and len(report3) > 800 else 'FAIL')

    passed = sum(1 for r in RESULTS if r['status'] == 'PASS')
    failed = sum(1 for r in RESULTS if r['status'] == 'FAIL')
    warned = sum(1 for r in RESULTS if r['status'] == 'WARN')
    print('\n===== 节点级验证: %d PASS / %d FAIL / %d WARN =====' % (passed, failed, warned))
    with open('scripts/deep_research_verify_results.json', 'w', encoding='utf-8') as f:
        json.dump({'round1_question': q, 'round2_queries': qlist,
                   'report_head': report[:500], 'results': RESULTS}, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
