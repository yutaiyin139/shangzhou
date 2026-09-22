# -*- coding: utf-8 -*-
"""
触发器引擎 —— trigger-schedule / trigger-webhook 节点的计划同步、调度和日志

职责:
    1. ensure_trigger_tables()      建表（workflow_schedule_plans / workflow_trigger_logs）
    2. sync_trigger_plans()         保存工作流图时，把画布中的触发节点同步为可执行计划
    3. dispatch_due_plans()         供 Celery Beat 每分钟调用，触发到期的定时计划
    4. log_trigger()                统一触发日志

设计要点（与 Dify 1.17 trigger_schedule 对齐）:
    - 触发节点是入口节点（无输入边），执行时输出 trigger_type / trigger_time 元数据
    - cron 表达式使用 croniter 解析（5 段标准 cron：分 时 日 月 周）
    - 计划同步是 upsert 语义：以 (app_id, node_id) 为唯一键，保存图时幂等刷新
"""

import uuid
from datetime import datetime

from config import get_db
from models.tables import (
    WORKFLOW_SCHEDULE_PLANS_TABLE_SQL,
    WORKFLOW_TRIGGER_LOGS_TABLE_SQL,
)

TABLES_ENSURED = False


def ensure_trigger_tables():
    """确保触发器相关表存在（幂等）"""
    global TABLES_ENSURED
    if TABLES_ENSURED:
        return
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(WORKFLOW_SCHEDULE_PLANS_TABLE_SQL)
        cur.execute(WORKFLOW_TRIGGER_LOGS_TABLE_SQL)
        db.commit()
        TABLES_ENSURED = True
    finally:
        db.close()


def compute_next_run(cron_expr, tz_name='Asia/Shanghai', base=None):
    """
    计算下次触发时间

    参数:
        cron_expr: 5 段 cron 表达式，如 '*/2 * * * *'
        tz_name:   时区名（默认 Asia/Shanghai）
        base:      基准时间（默认当前时间）

    返回:
        datetime 或 None（表达式非法）
    """
    try:
        from croniter import croniter
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(tz_name) if tz_name else None
        now = base or datetime.now(tz)
        return croniter(cron_expr, now).get_next(datetime)
    except Exception:
        return None


def _valid_cron(cron_expr):
    """校验 cron 表达式是否可解析"""
    return compute_next_run(cron_expr) is not None


def sync_trigger_plans(app_id, graph, tenant_id=None, account_id=None):
    """
    把画布中的触发节点同步为执行计划（在保存工作流图后调用）

    - trigger-schedule 节点 -> workflow_schedule_plans（upsert，重算 next_run_at）
    - trigger-webhook 节点   -> webhooks 表（upsert，自动生成 webhook_key）
    - 图中已删除/停用的触发节点 -> 对应计划置为停用

    返回:
        dict: {'schedules': n, 'webhooks': n, 'disabled': n}
    """
    ensure_trigger_tables()
    nodes = (graph or {}).get('nodes', []) or []
    schedule_nodes = {}
    webhook_nodes = {}
    for n in nodes:
        data = n.get('data') or {}
        ntype = data.get('type', '')
        if ntype == 'trigger-schedule':
            schedule_nodes[n.get('id', '')] = data
        elif ntype == 'trigger-webhook':
            webhook_nodes[n.get('id', '')] = data

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    stats = {'schedules': 0, 'webhooks': 0, 'disabled': 0}

    db = get_db()
    try:
        cur = db.cursor()

        # ---- 同步定时计划 ----
        cur.execute(
            'SELECT id, node_id FROM workflow_schedule_plans WHERE app_id = %s',
            (app_id,),
        )
        existing = {row['node_id']: row['id'] for row in cur.fetchall()}

        for node_id, data in schedule_nodes.items():
            cron = (data.get('cron_expr') or '').strip() or '0 9 * * *'
            enabled = 1 if data.get('enabled', True) else 0
            title = data.get('title', '') or '定时触发'
            next_run = compute_next_run(cron) if enabled else None

            if node_id in existing:
                cur.execute('''
                    UPDATE workflow_schedule_plans
                    SET node_title = %s, cron_expr = %s, enabled = %s,
                        next_run_at = %s, updated_at = %s
                    WHERE id = %s
                ''', (title, cron, enabled, next_run, now, existing[node_id]))
            else:
                cur.execute('''
                    INSERT INTO workflow_schedule_plans
                    (id, tenant_id, app_id, node_id, node_title, cron_expr,
                     enabled, next_run_at, created_by, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (str(uuid.uuid4()), tenant_id, app_id, node_id, title, cron,
                      enabled, next_run, account_id, now, now))
            stats['schedules'] += 1

        # 图中已删除的定时节点 -> 停用
        for node_id in set(existing) - set(schedule_nodes):
            cur.execute('''
                UPDATE workflow_schedule_plans
                SET enabled = 0, next_run_at = NULL, updated_at = %s
                WHERE id = %s
            ''', (now, existing[node_id]))
            stats['disabled'] += 1

        # ---- 同步 Webhook 触发节点 ----
        cur.execute(
            'SELECT id, name FROM webhooks WHERE app_id = %s AND name LIKE %s',
            (app_id, 'wf-node:%'),
        )
        existing_hooks = {row['name']: row['id'] for row in cur.fetchall()}

        for node_id, data in webhook_nodes.items():
            hook_name = f'wf-node:{node_id}'
            enabled = 1 if data.get('enabled', True) else 0
            key = 'wh-' + uuid.uuid4().hex[:24]
            trigger_url = f'/api/webhooks/trigger/{key}'
            if hook_name in existing_hooks:
                cur.execute('''
                    UPDATE webhooks SET is_active = %s, updated_at = %s WHERE id = %s
                ''', (enabled, now, existing_hooks[hook_name]))
            else:
                cur.execute('''
                    INSERT INTO webhooks
                    (id, app_id, name, description, webhook_key, trigger_url, is_active, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (str(uuid.uuid4()), app_id, hook_name,
                      (data.get('title', '') or 'Webhook 触发') + f'（节点 {node_id}）',
                      key, trigger_url, enabled, now, now))
            stats['webhooks'] += 1

        # 图中已删除的 webhook 节点 -> 停用
        for name in set(existing_hooks) - {f'wf-node:{nid}' for nid in webhook_nodes}:
            cur.execute('UPDATE webhooks SET is_active = 0 WHERE id = %s',
                        (existing_hooks[name],))
            stats['disabled'] += 1

        db.commit()
    finally:
        db.close()

    return stats


def list_schedule_plans(app_id):
    """列出应用的定时触发计划"""
    ensure_trigger_tables()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('''
            SELECT * FROM workflow_schedule_plans
            WHERE app_id = %s ORDER BY created_at DESC
        ''', (app_id,))
        return cur.fetchall()
    finally:
        db.close()


def update_schedule_plan(plan_id, cron_expr=None, enabled=None):
    """
    更新定时计划（启停或修改 cron）

    返回:
        (ok, message)
    """
    ensure_trigger_tables()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('SELECT * FROM workflow_schedule_plans WHERE id = %s', (plan_id,))
        row = cur.fetchone()
        if not row:
            return False, '计划不存在'

        if cron_expr is not None:
            cron_expr = cron_expr.strip()
            if not _valid_cron(cron_expr):
                return False, 'Cron 表达式非法（需 5 段：分 时 日 月 周）'

        enabled_val = row['enabled'] if enabled is None else (1 if enabled else 0)
        if cron_expr is not None:
            cur.execute('UPDATE workflow_schedule_plans SET cron_expr = %s WHERE id = %s',
                        (cron_expr, plan_id))
        if enabled is not None or cron_expr is not None:
            next_run = None
            if enabled_val:
                next_run = compute_next_run(cron_expr or row['cron_expr'])
            cur.execute('''
                UPDATE workflow_schedule_plans
                SET enabled = %s, next_run_at = %s, updated_at = %s
                WHERE id = %s
            ''', (enabled_val, next_run, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), plan_id))
        db.commit()
        return True, '更新成功'
    finally:
        db.close()


def delete_schedule_plan(plan_id):
    """删除定时计划"""
    ensure_trigger_tables()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('DELETE FROM workflow_schedule_plans WHERE id = %s', (plan_id,))
        db.commit()
        return cur.rowcount > 0
    finally:
        db.close()


def dispatch_due_plans():
    """
    触发所有到期的定时计划（由 Celery Beat 每分钟调用）

    返回:
        dict: {'dispatched': n, 'errors': n}
    """
    ensure_trigger_tables()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    dispatched = 0
    errors = 0

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('''
            SELECT * FROM workflow_schedule_plans
            WHERE enabled = 1 AND next_run_at IS NOT NULL AND next_run_at <= %s
            LIMIT 50
        ''', (now,))
        due = cur.fetchall()
    finally:
        db.close()

    for plan in due:
        try:
            _dispatch_plan(plan)
            dispatched += 1
        except Exception:
            errors += 1

    return {'dispatched': dispatched, 'errors': errors}


def _dispatch_plan(plan):
    """触发单个定时计划：启动异步工作流 + 刷新 next_run_at + 写日志"""
    from tasks.workflow_tasks import run_workflow_async

    now = datetime.now()
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    plan_id = plan['id']

    # 先占位推进 next_run_at，防止同一分钟重复触发
    next_run = compute_next_run(plan['cron_expr'])
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('''
            UPDATE workflow_schedule_plans
            SET last_run_at = %s, next_run_at = %s, run_count = run_count + 1,
                updated_at = %s
            WHERE id = %s
        ''', (now_str, next_run, now_str, plan_id))
        db.commit()
    finally:
        db.close()

    log_id = str(uuid.uuid4())
    log_trigger({
        'id': log_id,
        'trigger_type': 'schedule',
        'plan_id': plan_id,
        'app_id': plan['app_id'],
        'node_id': plan['node_id'],
        'status': 'triggered',
    })

    inputs = {
        'trigger_type': 'schedule',
        'trigger_time': now.isoformat(),
        'trigger_schedule_id': plan_id,
        'trigger_node_id': plan['node_id'],
    }
    task = run_workflow_async.delay(
        plan['app_id'], inputs, user='trigger:schedule'
    )

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('''
            UPDATE workflow_trigger_logs SET task_id = %s WHERE id = %s
        ''', (task.id, log_id))
        db.commit()
    finally:
        db.close()


def log_trigger(entry):
    """写入触发日志（entry 为字段字典，缺省值自动补齐）"""
    ensure_trigger_tables()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('''
            INSERT INTO workflow_trigger_logs
            (id, trigger_type, plan_id, webhook_id, app_id, node_id,
             run_id, task_id, status, error_message, elapsed_ms, triggered_at, finished_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            entry.get('id') or str(uuid.uuid4()),
            entry.get('trigger_type', ''),
            entry.get('plan_id'),
            entry.get('webhook_id'),
            entry.get('app_id', ''),
            entry.get('node_id'),
            entry.get('run_id'),
            entry.get('task_id'),
            entry.get('status', 'triggered'),
            entry.get('error_message'),
            entry.get('elapsed_ms', 0),
            entry.get('triggered_at') or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            entry.get('finished_at'),
        ))
        db.commit()
    finally:
        db.close()


def finalize_trigger_log(task_id, run_id=None, status=None, error_message=None, elapsed_ms=0):
    """
    工作流运行结束后回填触发日志（按 Celery task_id 关联）

    在 tasks/workflow_tasks.run_workflow_async 的三个终态（succeeded/failed/waiting）调用。
    """
    if not task_id:
        return
    try:
        ensure_trigger_tables()
        db = get_db()
        try:
            cur = db.cursor()
            updates = ['finished_at = %s']
            params = [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
            if run_id is not None:
                updates.append('run_id = %s')
                params.append(run_id)
            if status is not None:
                updates.append('status = %s')
                params.append(status)
            if error_message is not None:
                updates.append('error_message = %s')
                params.append(error_message)
            updates.append('elapsed_ms = %s')
            params.append(elapsed_ms)
            params.append(task_id)
            cur.execute(
                'UPDATE workflow_trigger_logs SET ' + ', '.join(updates) + ' WHERE task_id = %s',
                tuple(params),
            )
            db.commit()
        finally:
            db.close()
    except Exception:
        pass


def list_trigger_logs(app_id, trigger_type=None, page=1, page_size=20):
    """分页查询触发日志"""
    ensure_trigger_tables()
    offset = (page - 1) * page_size
    db = get_db()
    try:
        cur = db.cursor()
        if trigger_type:
            cur.execute('''
                SELECT COUNT(*) AS total FROM workflow_trigger_logs
                WHERE app_id = %s AND trigger_type = %s
            ''', (app_id, trigger_type))
        else:
            cur.execute('SELECT COUNT(*) AS total FROM workflow_trigger_logs WHERE app_id = %s',
                        (app_id,))
        total = cur.fetchone()['total']

        if trigger_type:
            cur.execute('''
                SELECT * FROM workflow_trigger_logs
                WHERE app_id = %s AND trigger_type = %s
                ORDER BY triggered_at DESC LIMIT %s OFFSET %s
            ''', (app_id, trigger_type, page_size, offset))
        else:
            cur.execute('''
                SELECT * FROM workflow_trigger_logs
                WHERE app_id = %s
                ORDER BY triggered_at DESC LIMIT %s OFFSET %s
            ''', (app_id, page_size, offset))
        rows = cur.fetchall()
        return {'total': total, 'items': rows}
    finally:
        db.close()
