# -*- coding: utf-8 -*-
"""分支路由回归测试（无需 MySQL/模型）—— 验证 §8.0 重构后的动态就绪调度。

覆盖 docs/工作流功能对比与优化建议.md 第六章的 5 节点缺陷图：
    start → if-else(x==1 ? Yes : No) → {answer(Yes), answer(No)} → end
断言（条件为真 x='1'）：
  1. 未命中的 No 分支节点（n_no）不产生 node_execution（可达性剪枝生效）；
  2. 命中分支 answer(Yes) 被执行、answer 输出为 'yes'（不被 No 分支覆盖）；
  3. 三种 sourceHandle 命名（前端 yes/no、case id true/false、Dify case- 前缀）行为一致。

用法:  python tests/test_branch_routing.py
"""
import io
import sys

# 用 reconfigure 而不是包一层 TextIOWrapper：后者被回收时会连带关掉真正的 stdout buffer，
# 在 pytest 下会让捕获层直接崩成 ValueError: I/O operation on closed file
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
import os
# 用绝对路径而不是 '.'：让脚本无论从 backend/ 还是 backend/tests/ 启动都能导入 config/engine
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import engine.workflow_runner as R  # noqa: E402

EXECED = []


def _stub_start(run, app, ex, nid, nt, title):
    EXECED.append(nid)


def _stub_end(ex, status, outputs, error=None):
    return None


R._record_node_start = _stub_start
R._record_node_end = _stub_end


def node(nid, ntype, **data):
    return {'id': nid, 'type': 'custom', 'position': {'x': 0, 'y': 0},
            'data': {'type': ntype, 'title': ntype, **data}}


def edge(src, tgt, handle=None):
    return {'id': f'{src}->{tgt}:{handle}', 'source': src, 'target': tgt,
            'sourceHandle': handle, 'type': 'custom', 'data': {}}


def build_graph(yes_handle, no_handle):
    return {
        'nodes': [
            node('n_start', 'start'),
            node('n_if', 'if-else', cases=[
                {'id': 'true', 'name': 'Yes',
                 'conditions': [{'variable': 'x', 'operator': 'equals', 'value': '1'}]},
                {'id': 'false', 'name': 'No', 'conditions': []},
            ]),
            node('n_yes', 'answer', answer='yes'),
            node('n_no', 'answer', answer='no'),
            node('n_end', 'end', outputs=[]),
        ],
        'edges': [
            edge('n_start', 'n_if'),
            edge('n_if', 'n_yes', yes_handle),
            edge('n_if', 'n_no', no_handle),
            edge('n_yes', 'n_end'),
            edge('n_no', 'n_end'),
        ],
        'viewport': {'x': 0, 'y': 0, 'zoom': 1},
    }


CASES = [
    ('前端默认 yes/no', 'yes', 'no'),
    ('case id true/false', 'true', 'false'),
    ('Dify case- 前缀', 'case-true', 'case-false'),
]

EXPECTED_EXECUTED = {'n_start', 'n_if', 'n_yes', 'n_end'}


def build_graph_with_human():
    # start → human-input → if-else(x==1 ? Yes : No) → {answer(Yes), answer(No)} → end
    return {
        'nodes': [
            node('n_start', 'start'),
            node('n_h', 'human-input', output='approver', message='ok?'),
            node('n_if', 'if-else', cases=[
                {'id': 'true', 'name': 'Yes',
                 'conditions': [{'variable': 'x', 'operator': 'equals', 'value': '1'}]},
                {'id': 'false', 'name': 'No', 'conditions': []},
            ]),
            node('n_yes', 'answer', answer='yes'),
            node('n_no', 'answer', answer='no'),
            node('n_end', 'end', outputs=[]),
        ],
        'edges': [
            edge('n_start', 'n_h'),
            edge('n_h', 'n_if'),
            edge('n_if', 'n_yes', 'yes'),
            edge('n_if', 'n_no', 'no'),
            edge('n_yes', 'n_end'),
            edge('n_no', 'n_end'),
        ],
        'viewport': {'x': 0, 'y': 0, 'zoom': 1},
    }


def run_resume_case():
    """验证 Human Input 暂停后经调度器恢复：人工节点不被重跑、下游分支仍正确剪枝。"""
    failures = []
    graph = build_graph_with_human()

    EXECED.clear()
    payload = R._execute_workflow_graph(graph, {'x': '1'}, None, 'app-test', 'run-test')
    pause_ok = (isinstance(payload, dict) and payload.get('__human_input_pause__')
                and set(EXECED) == {'n_start', 'n_h'}
                and payload.get('__human_input_node_id__') == 'n_h')
    print(f'{"\u2705" if pause_ok else "\u274c"} 暂停: executed={sorted(EXECED)} '
          f'node_id={payload.get("__human_input_node_id__") if isinstance(payload, dict) else None!r}')
    if not pause_ok:
        failures.append('pause')

    # 模拟 submit_human_input 的恢复流程（与 routes/workflows.py 一致）
    ctx = dict(payload['__context__'])
    from engine.workflow_runner import apply_node_outputs
    apply_node_outputs(ctx, 'n_h', {'approver': 'alice'}, extra=True)
    resume_executed = list(dict.fromkeys(payload['__executed_nodes__'] + ['n_h']))

    EXECED.clear()
    result = R._execute_workflow_graph(
        graph, {}, None, 'app-test', 'run-test',
        resume={'executed': resume_executed, 'branches': payload['__branch_map__'], 'context': ctx})
    resumed = set(EXECED)
    answer = result.get('answer') if isinstance(result, dict) else None
    approver = result.get('approver') if isinstance(result, dict) else None
    ok = (resumed == {'n_if', 'n_yes', 'n_end'} and answer == 'yes'
          and approver == 'alice' and 'n_h' not in resumed and 'n_no' not in resumed
          and 'n_start' not in resumed)
    print(f'{"\u2705" if ok else "\u274c"} 恢复: resumed={sorted(resumed)} '
          f'answer={answer!r} approver={approver!r}')
    if not ok:
        failures.append('resume')
    return failures


def run_case():
    failures = []
    for label, yes_h, no_h in CASES:
        EXECED.clear()
        ctx = R._execute_workflow_graph(build_graph(yes_h, no_h), {'x': '1'}, None,
                                        'app-test', 'run-test')
        executed = set(EXECED)
        answer = ctx.get('answer')
        ok = (executed == EXPECTED_EXECUTED) and answer == 'yes' and 'n_no' not in executed
        print(f'{"✅" if ok else "❌"} {label}: executed={sorted(executed)} answer={answer!r}')
        if not ok:
            failures.append((label, sorted(executed), answer))
    return failures


if __name__ == '__main__':
    fails = run_case()
    resume_fails = run_resume_case()
    print()
    if fails or resume_fails:
        print('分支路由回归失败:')
        for label, executed, answer in fails:
            print(f'  ❌ {label}: executed={executed} answer={answer!r}')
        for name in resume_fails:
            print(f'  ❌ resume 阶段失败: {name}')
        sys.exit(1)
    print('ALL PASSED —— 分支剪枝 + 命中分支文本 + Human Input 暂停/恢复')
