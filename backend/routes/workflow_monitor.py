# -*- coding: utf-8 -*-
"""
工作流监控 API
提供执行趋势、节点耗时、错误统计、告警配置等监控数据
"""
import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from config import get_db
from utils.auth import login_required

bp = Blueprint('workflow_monitor', __name__)

# ============================================================
# 辅助函数
# ============================================================

def _parse_range(range_str):
    """解析时间范围字符串为 timedelta"""
    now = datetime.now()
    if range_str == '1h':
        return now - timedelta(hours=1)
    elif range_str == '6h':
        return now - timedelta(hours=6)
    elif range_str == '24h':
        return now - timedelta(hours=24)
    elif range_str == '7d':
        return now - timedelta(days=7)
    elif range_str == '30d':
        return now - timedelta(days=30)
    return now - timedelta(hours=24)


def _time_bucket(start_time, range_str):
    """根据时间范围返回合适的时间桶大小"""
    if range_str in ('1h', '6h'):
        return '%Y-%m-%d %H:00'  # 按小时
    return '%Y-%m-%d'  # 按天


# ============================================================
# 概览数据
# ============================================================

@bp.route('/api/monitor/overview', methods=['GET'])
@login_required
def get_overview():
    """获取监控概览数据"""
    range_str = request.args.get('range', '24h')
    app_id = request.args.get('app_id', '')
    start_time = _parse_range(range_str)

    db = get_db()
    try:
        cur = db.cursor()

        # 构建 WHERE 条件（使用 dify_workflow_runs 表）
        where_clause = "WHERE created_at >= %s"
        params = [start_time.strftime('%Y-%m-%d %H:%M:%S')]
        if app_id:
            where_clause += " AND app_id = %s"
            params.append(app_id)

        # 总执行次数
        cur.execute(f"SELECT COUNT(*) as cnt FROM dify_workflow_runs {where_clause}", params)
        total_runs = cur.fetchone()['cnt']

        # 成功次数 (status = 'succeeded')
        cur.execute(f"SELECT COUNT(*) as cnt FROM dify_workflow_runs {where_clause} AND status = 'succeeded'",
                    params)
        success_runs = cur.fetchone()['cnt']

        # 错误次数 (status IN ('failed', 'error'))
        cur.execute(f"SELECT COUNT(*) as cnt FROM dify_workflow_runs {where_clause} AND status IN ('failed', 'error')",
                    params)
        total_errors = cur.fetchone()['cnt']

        # 平均耗时 (elapsed_time 是秒，转为毫秒)
        cur.execute(f"SELECT AVG(elapsed_time) as avg_dur FROM dify_workflow_runs {where_clause} AND elapsed_time > 0",
                    params)
        row = cur.fetchone()
        avg_duration = round((row['avg_dur'] or 0) * 1000)  # 转为 ms

        # 计算趋势（对比前一个周期）
        if range_str in ('1h', '6h'):
            delta = datetime.now() - start_time
        elif range_str == '24h':
            delta = timedelta(hours=24)
        elif range_str == '7d':
            delta = timedelta(days=7)
        else:
            delta = timedelta(days=30)
        prev_end = start_time
        prev_start = prev_end - delta

        prev_params = [prev_start.strftime('%Y-%m-%d %H:%M:%S'), prev_end.strftime('%Y-%m-%d %H:%M:%S')]
        if app_id:
            prev_params.append(app_id)

        cur.execute(
            "SELECT COUNT(*) as cnt FROM dify_workflow_runs WHERE created_at >= %s AND created_at < %s"
            + (" AND app_id = %s" if app_id else ""),
            prev_params
        )
        prev_runs = cur.fetchone()['cnt']

        run_trend = 0
        if prev_runs > 0:
            run_trend = (total_runs - prev_runs) / prev_runs

        success_rate = (success_runs / total_runs * 100) if total_runs > 0 else 0

        return jsonify(code=200, data={
            'totalRuns': total_runs,
            'successRuns': success_runs,
            'totalErrors': total_errors,
            'avgDuration': avg_duration,
            'successRate': round(success_rate, 1),
            'runTrend': round(run_trend, 3),
            'durationTrend': 0,  # 可扩展
            'successTrend': 0,   # 可扩展
            'errorTrend': 0,     # 可扩展
        })
    finally:
        db.close()


# ============================================================
# 执行趋势
# ============================================================

@bp.route('/api/monitor/trend', methods=['GET'])
@login_required
def get_trend():
    """获取执行趋势数据（按时间桶聚合）"""
    range_str = request.args.get('range', '24h')
    app_id = request.args.get('app_id', '')
    start_time = _parse_range(range_str)
    bucket_fmt = _time_bucket(start_time, range_str)

    db = get_db()
    try:
        cur = db.cursor()

        where_clause = "WHERE created_at >= %s"
        params = [start_time.strftime('%Y-%m-%d %H:%M:%S')]
        if app_id:
            where_clause += " AND app_id = %s"
            params.append(app_id)

        # 时间桶格式必须当**参数**传，不能拼进 SQL 字面量：
        # pymysql 在 execute(query, args) 里会对 query 做一次 `%` 格式化，
        # 而 _time_bucket 返回的是 '%Y-%m-%d %H:00' 这种带百分号的 MySQL 格式串，
        # 拼进去就报 ValueError: unsupported format character 'Y' at index 33，
        # 本接口一直 500（监控页的“执行趋势”永远空）。参数值里的 % 不会被二次格式化。
        cur.execute(
            r'''SELECT DATE_FORMAT(created_at, %s) as bucket,
                       COUNT(*) as cnt,
                       SUM(CASE WHEN status = 'succeeded' THEN 1 ELSE 0 END) as success,
                       SUM(CASE WHEN status IN ('failed', 'error') THEN 1 ELSE 0 END) as fail
                FROM dify_workflow_runs
                ''' + where_clause + r'''
                GROUP BY bucket
                ORDER BY bucket ASC''',
            [bucket_fmt] + params
        )

        items = []
        for r in cur.fetchall():
            items.append({
                'label': r['bucket'],
                'value': r['cnt'],
                'success': r['success'],
                'fail': r['fail'],
            })

        return jsonify(code=200, data={'items': items})
    finally:
        db.close()


# ============================================================
# 节点耗时分布
# ============================================================

@bp.route('/api/monitor/node-duration', methods=['GET'])
@login_required
def get_node_duration():
    """获取节点执行耗时分布（使用 dify_workflow_node_executions 表）"""
    range_str = request.args.get('range', '24h')
    app_id = request.args.get('app_id', '')
    start_time = _parse_range(range_str)

    db = get_db()
    try:
        cur = db.cursor()

        where_clause = "WHERE ne.created_at >= %s"
        params = [start_time.strftime('%Y-%m-%d %H:%M:%S')]
        if app_id:
            where_clause += " AND ne.app_id = %s"
            params.append(app_id)

        # 从 dify_workflow_node_executions 表获取节点耗时
        cur.execute(
            f"""SELECT ne.node_type, AVG(ne.elapsed_time) as avg_dur, COUNT(*) as cnt
                FROM dify_workflow_node_executions ne
                {where_clause}
                GROUP BY ne.node_type
                ORDER BY avg_dur DESC
                LIMIT 10""",
            params
        )

        items = []
        for r in cur.fetchall():
            items.append({
                'label': r['node_type'],
                'value': round((r['avg_dur'] or 0) * 1000),  # 转为 ms
                'count': r['cnt'],
            })

        return jsonify(code=200, data={'items': items})
    finally:
        db.close()


# ============================================================
# 高频错误
# ============================================================

@bp.route('/api/monitor/top-errors', methods=['GET'])
@login_required
def get_top_errors():
    """获取高频错误排行（使用 dify_workflow_runs 表）"""
    range_str = request.args.get('range', '24h')
    app_id = request.args.get('app_id', '')
    limit = min(int(request.args.get('limit', 10)), 50)
    start_time = _parse_range(range_str)

    db = get_db()
    try:
        cur = db.cursor()

        where_clause = "WHERE created_at >= %s AND status IN ('failed', 'error') AND error IS NOT NULL AND error != ''"
        params = [start_time.strftime('%Y-%m-%d %H:%M:%S')]
        if app_id:
            where_clause += " AND app_id = %s"
            params.append(app_id)

        cur.execute(
            f"""SELECT error, COUNT(*) as cnt
                FROM dify_workflow_runs
                {where_clause}
                GROUP BY error
                ORDER BY cnt DESC
                LIMIT %s""",
            params + [limit]
        )

        items = []
        for r in cur.fetchall():
            items.append({
                'message': (r['error'] or 'Unknown error')[:200],
                'node_type': '-',
                'count': r['cnt'],
            })

        return jsonify(code=200, data={'items': items})
    finally:
        db.close()


# ============================================================
# 最近执行记录
# ============================================================

@bp.route('/api/monitor/recent-runs', methods=['GET'])
@login_required
def get_recent_runs():
    """获取最近执行记录（使用 dify_workflow_runs 表）"""
    app_id = request.args.get('app_id', '')
    limit = min(int(request.args.get('limit', 20)), 50)

    db = get_db()
    try:
        cur = db.cursor()

        if app_id:
            cur.execute(
                r'''SELECT r.*, a.name as app_name
                    FROM dify_workflow_runs r
                    LEFT JOIN dify_apps a ON r.app_id = a.id
                    WHERE r.app_id = %s
                    ORDER BY r.created_at DESC
                    LIMIT %s''',
                (app_id, limit)
            )
        else:
            cur.execute(
                r'''SELECT r.*, a.name as app_name
                    FROM dify_workflow_runs r
                    LEFT JOIN dify_apps a ON r.app_id = a.id
                    ORDER BY r.created_at DESC
                    LIMIT %s''',
                (limit,)
            )

        items = []
        for r in cur.fetchall():
            items.append({
                'id': r['id'],
                'app_id': r['app_id'],
                'app_name': r['app_name'] or r['app_id'],
                'status': r['status'],
                'duration': round((r['elapsed_time'] or 0) * 1000),  # 转为 ms
                'error_message': r['error'] or '',
                'created_at': str(r['created_at']),
                'finished_at': str(r['finished_at']) if r['finished_at'] else '',
            })

        return jsonify(code=200, data={'items': items})
    finally:
        db.close()


# ============================================================
# 告警配置
# ============================================================

# 内存存储告警配置（生产环境应存储到数据库）
_alert_configs = {
    'err_rate': {'label': '错误率告警', 'condition': '错误率 > 5%', 'enabled': True, 'threshold': 5},
    'duration': {'label': '耗时告警', 'condition': '执行耗时 > 30s', 'enabled': True, 'threshold': 30000},
    'fail_count': {'label': '连续失败告警', 'condition': '连续失败 > 3 次', 'enabled': False, 'threshold': 3},
    'node_err': {'label': '节点错误告警', 'condition': '节点执行失败', 'enabled': True, 'threshold': 1},
}


@bp.route('/api/monitor/alerts', methods=['GET'])
@login_required
def get_alerts():
    """获取告警配置列表"""
    items = []
    for k, v in _alert_configs.items():
        items.append({'id': k, **v})
    return jsonify(code=200, data={'items': items})


@bp.route('/api/monitor/alerts/<alert_id>', methods=['POST'])
@login_required
def update_alert(alert_id):
    """更新告警配置"""
    if alert_id not in _alert_configs:
        return jsonify(code=404, msg='告警配置不存在')

    body = request.get_json() or {}
    if 'enabled' in body:
        _alert_configs[alert_id]['enabled'] = bool(body['enabled'])
    if 'threshold' in body:
        _alert_configs[alert_id]['threshold'] = body['threshold']

    return jsonify(code=200, msg='已更新', data=_alert_configs[alert_id])


# ============================================================
# 检查告警触发（内部调用）
# ============================================================

def check_alerts(app_id, status, duration_ms=None, error_msg=None):
    """检查是否触发告警，如触发则创建通知"""
    triggered = []

    if status in ('failed', 'error') and _alert_configs.get('node_err', {}).get('enabled'):
        triggered.append(('node_err', f'工作流 {app_id} 执行失败'))

    if duration_ms and duration_ms > _alert_configs.get('duration', {}).get('threshold', 30000) and _alert_configs.get('duration', {}).get('enabled'):
        triggered.append(('duration', f'工作流 {app_id} 执行耗时过长: {duration_ms}ms'))

    return triggered


# ============================================================
# 注册路由
# ============================================================

def register_workflow_monitor_routes(app):
    """注册工作流监控路由"""
    app.register_blueprint(bp)
