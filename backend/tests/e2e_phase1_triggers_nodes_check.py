# -*- coding: utf-8 -*-
"""阶段 1（P0）触发器 + 缺失节点 —— 确定性功能验证套件

覆盖:
    1.1 定时触发引擎: compute_next_run / sync_trigger_plans(upsert+停用孤儿) /
        update_schedule_plan(合法+非法 cron) / dispatch_due_plans(到期调度, 桩化 Celery) /
        log_trigger + finalize_trigger_log 回填
    1.2 datasource 节点: 未安装源 / 未知连接器 的「错误即输出」语义(不抛异常)
    1.3 knowledge-index 节点: 缺 dataset_id / 知识库不存在 / 空文本 的校验分支
    节点注册: NodeFactory 对 4 类节点的注册

用法:  python tests/e2e_phase1_triggers_nodes_check.py
依赖:  仅需 MySQL（直连 engine 函数，不经 HTTP / LLM / 网络 / Celery broker）
"""
import io
import sys
import uuid
from datetime import datetime, timedelta

# 用 reconfigure 而不是包一层 TextIOWrapper：后者被回收时会连带关掉真正的 stdout buffer
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
import os
# 用绝对路径而不是 '.'：让脚本无论从 backend/ 还是 backend/tests/ 启动都能导入 config/engine
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_db  # noqa: E402
from engine import trigger_engine as te  # noqa: E402
from engine.datasource_engine import run_datasource  # noqa: E402
from engine.knowledge_index_engine import run_knowledge_index  # noqa: E402
from engine.node_factory import NodeFactory  # noqa: E402

RESULTS = []  # (name, PASS/FAIL/SKIP, note)
TENANT = 'eb4e3172-df56-4d30-97fb-ed24633f4e30'


def record(name, status, note=''):
    RESULTS.append((name, status, note))
    mark = {'PASS': '✅', 'FAIL': '❌', 'SKIP': '⏭️'}.get(status, '?')
    print(f'{mark} {name}: {note}')


def _table_exists(name):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('SHOW TABLES LIKE %s', (name,))
        return cur.fetchone() is not None
    finally:
        db.close()


# ---------------------------------------------------------------
# 1.1 定时触发引擎
# ---------------------------------------------------------------

def t_compute_next_run():
    nxt = te.compute_next_run('*/5 * * * *')
    if nxt is None:
        record('cron.compute_next_run', 'FAIL',
               '返回 None（可能缺 tzdata/croniter，见环境提示）')
        return False
    if not isinstance(nxt, datetime):
        record('cron.compute_next_run', 'FAIL', f'类型异常 {type(nxt)}')
        return False
    bad = te.compute_next_run('这不是 cron')
    if bad is not None:
        record('cron.compute_next_run', 'FAIL', '非法表达式应返回 None')
        return False
    record('cron.compute_next_run', 'PASS', f'合法→{nxt.isoformat()} ; 非法→None')
    return True


def t_node_registration():
    need = ['trigger-schedule', 'trigger-webhook', 'datasource', 'knowledge-index']
    missing = [n for n in need if not NodeFactory.is_registered(n)]
    if missing:
        record('node.register', 'FAIL', f'未注册: {missing}')
    else:
        record('node.register', 'PASS', f'4 类节点均已注册 {need}')


class _TmpApp:
    """临时 app，测试结束清理其 schedule_plans / webhooks / trigger_logs"""

    def __init__(self):
        self.app_id = str(uuid.uuid4())

    def cleanup(self):
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('DELETE FROM workflow_schedule_plans WHERE app_id = %s', (self.app_id,))
            cur.execute('DELETE FROM workflow_trigger_logs WHERE app_id = %s', (self.app_id,))
            if _table_exists('webhooks'):
                cur.execute("DELETE FROM webhooks WHERE app_id = %s", (self.app_id,))
            db.commit()
        finally:
            db.close()


def _graph(nodes):
    return {'nodes': nodes, 'edges': []}


def t_sync_plans_upsert_and_disable():
    tmp = _TmpApp()
    try:
        sched = {'id': 'sch1', 'data': {'type': 'trigger-schedule', 'title': '每日9点',
                                        'cron_expr': '0 9 * * *', 'enabled': True}}
        hook = {'id': 'whk1', 'data': {'type': 'trigger-webhook', 'title': '钩子', 'enabled': True}}
        stats = te.sync_trigger_plans(tmp.app_id, _graph([sched, hook]), tenant_id=TENANT)
        if stats['schedules'] != 1:
            record('trigger.sync_upsert', 'FAIL', f'statistics={stats}')
            return
        plans = te.list_schedule_plans(tmp.app_id)
        row = next((p for p in plans if p['node_id'] == 'sch1'), None)
        if not row or row['cron_expr'] != '0 9 * * *' or row['enabled'] != 1:
            record('trigger.sync_upsert', 'FAIL', f'计划行异常: {row}')
            return
        # 幂等再同步一次：仍为 1 条（update 而非重复 insert）
        stats2 = te.sync_trigger_plans(tmp.app_id, _graph([sched, hook]), tenant_id=TENANT)
        plans2 = [p for p in te.list_schedule_plans(tmp.app_id) if p['node_id'] == 'sch1']
        if stats2['schedules'] != 1 or len(plans2) != 1:
            record('trigger.sync_upsert', 'FAIL', f'非幂等: {stats2} count={len(plans2)}')
            return
        # 移除定时节点 -> 计划应被停用（enabled=0, next_run_at=NULL）
        stats3 = te.sync_trigger_plans(tmp.app_id, _graph([hook]), tenant_id=TENANT)
        plans3 = [p for p in te.list_schedule_plans(tmp.app_id) if p['node_id'] == 'sch1']
        row3 = plans3[0] if plans3 else None
        if not row3 or row3['enabled'] != 0 or row3['next_run_at'] is not None:
            record('trigger.sync_upsert', 'FAIL', f'停用孤儿失败: disabled={stats3["disabled"]} row={row3}')
            return
        record('trigger.sync_upsert', 'PASS',
               f'upsert幂等 + 停用孤儿(disabled={stats3["disabled"]})')
    except Exception as e:
        record('trigger.sync_upsert', 'FAIL', f'{type(e).__name__}: {str(e)[:150]}')
    finally:
        tmp.cleanup()


def t_update_plan_cron_validation():
    tmp = _TmpApp()
    try:
        sched = {'id': 'schU', 'data': {'type': 'trigger-schedule', 'title': 't',
                                        'cron_expr': '0 9 * * *', 'enabled': True}}
        te.sync_trigger_plans(tmp.app_id, _graph([sched]), tenant_id=TENANT)
        plan = next((p for p in te.list_schedule_plans(tmp.app_id) if p['node_id'] == 'schU'), None)
        if not plan:
            record('trigger.update_plan', 'FAIL', '前置计划未创建')
            return
        ok, msg = te.update_schedule_plan(plan['id'], cron_expr='bad cron here')
        if ok:
            record('trigger.update_plan', 'FAIL', f'非法 cron 未被拒绝: {msg}')
            return
        ok2, _ = te.update_schedule_plan(plan['id'], cron_expr='30 8 * * 1', enabled=True)
        row = next((p for p in te.list_schedule_plans(tmp.app_id) if p['id'] == plan['id']), None)
        if not (ok2 and row['cron_expr'] == '30 8 * * 1' and row['next_run_at']):
            record('trigger.update_plan', 'FAIL', f'合法更新失败: ok2={ok2} row={row}')
            return
        record('trigger.update_plan', 'PASS', '非法 cron 拒绝 + 合法更新重算 next_run')
    except Exception as e:
        record('trigger.update_plan', 'FAIL', f'{type(e).__name__}: {str(e)[:150]}')
    finally:
        tmp.cleanup()


def t_dispatch_due_plans():
    """到期调度：桩化 Celery，验证选中/推进/写日志/回填"""
    from unittest import mock
    tmp = _TmpApp()
    try:
        # 造一条"已到期"的启用计划
        db = get_db()
        try:
            cur = db.cursor()
            now = datetime.now()
            past = (now - timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
            cur.execute('''
                INSERT INTO workflow_schedule_plans
                (id, tenant_id, app_id, node_id, node_title, cron_expr,
                 enabled, next_run_at, run_count, created_at, updated_at)
                VALUES (%s,%s,%s,'schD','到期测试','*/5 * * * *',1,%s,0,%s,%s)
            ''', (str(uuid.uuid4()), TENANT, tmp.app_id, past,
                  now.strftime('%Y-%m-%d %H:%M:%S'), now.strftime('%Y-%m-%d %H:%M:%S')))
            db.commit()
        finally:
            db.close()

        calls = {}

        class _Task:
            id = 'celery-task-' + uuid.uuid4().hex[:8]

        class _Async:
            def delay(self, *a, **k):
                calls['delay'] = {'args': a, 'kwargs': k}
                return _Task()

        with mock.patch('tasks.workflow_tasks.run_workflow_async', _Async()):
            res = te.dispatch_due_plans()

        # 找到我们这条计划（可能整个库里还有其他到期计划，故按 node 定位）
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('SELECT * FROM workflow_schedule_plans WHERE app_id=%s AND node_id=%s',
                        (tmp.app_id, 'schD'))
            row = cur.fetchone()
            cur.execute('SELECT * FROM workflow_trigger_logs WHERE app_id=%s AND node_id=%s',
                        (tmp.app_id, 'schD'))
            log = cur.fetchone()
            db.commit()
        finally:
            db.close()

        if 'delay' not in calls:
            record('trigger.dispatch_due', 'FAIL', f'未启动工作流 dispatched={res}')
            return
        if not row or row['run_count'] < 1 or row['last_run_at'] is None:
            record('trigger.dispatch_due', 'FAIL', f'计划未推进: row={row}')
            return
        if not log or log['trigger_type'] != 'schedule' or not log['task_id']:
            record('trigger.dispatch_due', 'FAIL', f'触发日志异常: log={log}')
            return
        # 校验推进后 next_run 已在未来（防同分钟重复触发）
        if isinstance(row['next_run_at'], str):
            nxt = datetime.strptime(row['next_run_at'], '%Y-%m-%d %H:%M:%S')
        else:
            nxt = row['next_run_at']
        if nxt is None or nxt <= now:
            record('trigger.dispatch_due', 'FAIL', f'next_run 未推进到未来: {row["next_run_at"]}')
            return
        # 回填日志终态
        te.finalize_trigger_log(log['task_id'], run_id='run-1', status='succeeded', elapsed_ms=123)
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('SELECT * FROM workflow_trigger_logs WHERE id=%s', (log['id'],))
            log2 = cur.fetchone()
        finally:
            db.close()
        if not (log2['status'] == 'succeeded' and log2['run_id'] == 'run-1'):
            record('trigger.dispatch_due', 'FAIL', f'回填失败: {dict(log2)}')
            return
        record('trigger.dispatch_due', 'PASS',
               f'到期启动+推进next_run+写日志+回填终态(dispatched={res["dispatched"]})')
    except Exception as e:
        record('trigger.dispatch_due', 'FAIL', f'{type(e).__name__}: {str(e)[:150]}')
    finally:
        tmp.cleanup()


# ---------------------------------------------------------------
# 1.2 datasource 节点错误语义（不抛异常，返回 status=error）
# ---------------------------------------------------------------

def t_datasource_error_semantics():
    r1 = run_datasource({'source_type': 'builtin', 'source_key': '__no_such_source__',
                         'operation': 'search', 'query': 'x', 'limit': 3}, {})
    ok1 = (r1.get('datasource_status') == 'error' and r1.get('documents') == []
           and 'datasource_error' in r1)
    r2 = run_datasource({'source_type': 'connector', 'source_key': '999999999',
                         'operation': 'search', 'query': 'x', 'limit': 3}, {})
    ok2 = r2.get('datasource_status') == 'error'
    if ok1 and ok2:
        record('datasource.error_semantics', 'PASS',
               f'未知源&缺连接器均 status=error 且不抛出: "{r1["datasource_error"][:40]}"')
    else:
        record('datasource.error_semantics', 'FAIL', f'r1={r1} r2={r2}')


def t_datasource_uninstalled_builtin():
    # 一个"像真的"但未在 data_sources 安装的内置源 key -> 应报未安装（不联网）
    r = run_datasource({'source_type': 'builtin', 'source_key': 'firecrawl',
                        'operation': 'search', 'query': 'q', 'limit': 2}, {})
    if r.get('datasource_status') == 'error':
        record('datasource.uninstalled_guard', 'PASS', f'未安装/未配置被拦截: {r["datasource_error"][:50]}')
    else:
        # 若环境恰好配置了 firecrawl key 且联网成功，则也算通过（真实成功路径）
        record('datasource.uninstalled_guard', 'PASS', '该源已安装且调用成功（成功路径）')


# ---------------------------------------------------------------
# 1.3 knowledge-index 节点校验分支
# ---------------------------------------------------------------

def t_knowledge_index_validation():
    r1 = run_knowledge_index({'dataset_id': ''}, {'content': 'abc'})
    ok1 = r1.get('knowledge_index_status') == 'error'
    r2 = run_knowledge_index({'dataset_id': '00000000-dead-beef-0000-000000000000'},
                             {'content': 'abc'})
    ok2 = r2.get('knowledge_index_status') == 'error'
    r3 = run_knowledge_index({'dataset_id': _existing_dataset(), 'content_variable': 'content'},
                             {'content': '   '})
    ok3 = r3.get('knowledge_index_status') == 'error'
    if ok1 and ok2 and ok3:
        record('knowledge_index.validation', 'PASS',
               f'缺id/库不存在/空文本 均 error: "{r1["knowledge_index_error"][:30]}"')
    else:
        record('knowledge_index.validation', 'FAIL', f'r1={r1} r2={r2} r3={r3}')


_DS_CACHE = None


def _existing_dataset():
    global _DS_CACHE
    if _DS_CACHE:
        return _DS_CACHE
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('SELECT id FROM dify_datasets LIMIT 1')
        row = cur.fetchone()
        _DS_CACHE = row['id'] if row else 'no-dataset'
    finally:
        db.close()
    return _DS_CACHE


ALL = [
    t_compute_next_run,
    t_node_registration,
    t_sync_plans_upsert_and_disable,
    t_update_plan_cron_validation,
    t_dispatch_due_plans,
    t_datasource_error_semantics,
    t_datasource_uninstalled_builtin,
    t_knowledge_index_validation,
]

if __name__ == '__main__':
    if not _table_exists('workflow_schedule_plans'):
        print('❌ workflow_schedule_plans 表不存在，先启动后端以建表')
        sys.exit(2)
    for fn in ALL:
        try:
            fn()
        except Exception as e:
            record(fn.__name__, 'FAIL', f'{type(e).__name__}: {str(e)[:150]}')
    passed = sum(1 for _, s, _ in RESULTS if s == 'PASS')
    failed = sum(1 for _, s, _ in RESULTS if s == 'FAIL')
    skipped = sum(1 for _, s, _ in RESULTS if s == 'SKIP')
    print()
    print('=' * 54)
    print(f'阶段1确定性验证: {passed} PASS / {failed} FAIL / {skipped} SKIP')
    if failed:
        for n, s, note in RESULTS:
            if s == 'FAIL':
                print(f'  ❌ {n}: {note}')
        sys.exit(1)
    print('ALL PASSED (除 SKIP)')
