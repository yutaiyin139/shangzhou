# -*- coding: utf-8 -*-
"""
监控指标采集模块 —— Prometheus 兼容格式

功能：
1. 系统指标（CPU/内存/磁盘/网络）
2. 应用指标（请求数/延迟/错误率）
3. 业务指标（工作流/工具调用/Token 使用）
4. 数据库指标（连接数/慢查询）
5. Redis 指标（命中率/内存使用）

依赖：psutil（可选，用于系统指标）
"""

import os
import time
import logging
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)

# 指标存储（线程安全）
_metrics_lock = Lock()
_request_count = 0
_request_duration_sum = 0.0
_request_duration_buckets = defaultdict(int)
_error_count = 0
_endpoint_metrics = defaultdict(lambda: {'count': 0, 'duration_sum': 0.0, 'errors': 0})

# 业务指标
_business_metrics = {
    'workflow_runs_total': 0,
    'workflow_runs_success': 0,
    'workflow_runs_failed': 0,
    'tool_calls_total': 0,
    'tool_calls_success': 0,
    'tool_calls_failed': 0,
    'llm_tokens_total': 0,
    'llm_calls_total': 0,
}


def record_request(endpoint, duration_ms, status_code):
    """
    记录 API 请求指标

    参数:
        endpoint: 端点路径
        duration_ms: 请求耗时（毫秒）
        status_code: HTTP 状态码
    """
    global _request_count, _request_duration_sum, _error_count
    with _metrics_lock:
        _request_count += 1
        _request_duration_sum += duration_ms
        # 延迟分桶（用于计算百分位）
        if duration_ms < 10:
            _request_duration_buckets['0-10ms'] += 1
        elif duration_ms < 50:
            _request_duration_buckets['10-50ms'] += 1
        elif duration_ms < 100:
            _request_duration_buckets['50-100ms'] += 1
        elif duration_ms < 500:
            _request_duration_buckets['100-500ms'] += 1
        elif duration_ms < 1000:
            _request_duration_buckets['500-1000ms'] += 1
        else:
            _request_duration_buckets['1000ms+'] += 1
        # 端点指标
        _endpoint_metrics[endpoint]['count'] += 1
        _endpoint_metrics[endpoint]['duration_sum'] += duration_ms
        if status_code >= 400:
            _error_count += 1
            _endpoint_metrics[endpoint]['errors'] += 1


def record_workflow_run(success=True, tokens=0):
    """记录工作流执行指标"""
    with _metrics_lock:
        _business_metrics['workflow_runs_total'] += 1
        if success:
            _business_metrics['workflow_runs_success'] += 1
        else:
            _business_metrics['workflow_runs_failed'] += 1
        _business_metrics['llm_tokens_total'] += tokens


def record_tool_call(success=True):
    """记录工具调用指标"""
    with _metrics_lock:
        _business_metrics['tool_calls_total'] += 1
        if success:
            _business_metrics['tool_calls_success'] += 1
        else:
            _business_metrics['tool_calls_failed'] += 1


def record_llm_call(tokens=0):
    """记录 LLM 调用指标"""
    with _metrics_lock:
        _business_metrics['llm_calls_total'] += 1
        _business_metrics['llm_tokens_total'] += tokens


def get_system_metrics():
    """
    获取系统指标

    返回:
        dict: 系统指标字典
    """
    metrics = {}
    try:
        import psutil
        # CPU
        metrics['cpu_percent'] = psutil.cpu_percent(interval=0.1)
        metrics['cpu_count'] = psutil.cpu_count()
        # 内存
        memory = psutil.virtual_memory()
        metrics['memory_total_mb'] = round(memory.total / 1024 / 1024, 1)
        metrics['memory_used_mb'] = round(memory.used / 1024 / 1024, 1)
        metrics['memory_percent'] = memory.percent
        # 磁盘
        disk = psutil.disk_usage('/')
        metrics['disk_total_gb'] = round(disk.total / 1024 / 1024 / 1024, 2)
        metrics['disk_used_gb'] = round(disk.used / 1024 / 1024 / 1024, 2)
        metrics['disk_percent'] = disk.percent
        # 网络
        net = psutil.net_io_counters()
        metrics['network_bytes_sent'] = net.bytes_sent
        metrics['network_bytes_recv'] = net.bytes_recv
        # 进程
        metrics['process_count'] = len(psutil.pids())
    except ImportError:
        metrics['error'] = 'psutil not installed'
    except Exception as e:
        metrics['error'] = str(e)
    return metrics


def get_redis_metrics():
    """获取 Redis 指标"""
    metrics = {}
    try:
        from utils.redis_cache import get_redis_client
        r = get_redis_client()
        info = r.info()
        metrics['redis_connected'] = True
        metrics['redis_used_memory_mb'] = round(info.get('used_memory', 0) / 1024 / 1024, 2)
        metrics['redis_connected_clients'] = info.get('connected_clients', 0)
        metrics['redis_total_commands_processed'] = info.get('total_commands_processed', 0)
        metrics['redis_keyspace_hits'] = info.get('keyspace_hits', 0)
        metrics['redis_keyspace_misses'] = info.get('keyspace_misses', 0)
        # 计算命中率
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 0)
        total = hits + misses
        metrics['redis_hit_rate'] = round(hits / total * 100, 2) if total > 0 else 0
    except Exception as e:
        metrics['redis_connected'] = False
        metrics['error'] = str(e)[:100]
    return metrics


def get_database_metrics():
    """获取数据库指标"""
    metrics = {}
    try:
        from config import get_db
        db = get_db()
        cur = db.cursor()
        # 连接数
        cur.execute("SHOW STATUS LIKE 'Threads_connected'")
        row = cur.fetchone()
        metrics['db_threads_connected'] = row['Value'] if row else 0
        # 查询数
        cur.execute("SHOW STATUS LIKE 'Queries'")
        row = cur.fetchone()
        metrics['db_queries_total'] = row['Value'] if row else 0
        # 慢查询
        cur.execute("SHOW STATUS LIKE 'Slow_queries'")
        row = cur.fetchone()
        metrics['db_slow_queries'] = row['Value'] if row else 0
        # 表数量
        cur.execute("SELECT COUNT(*) as cnt FROM information_schema.tables WHERE table_schema = DATABASE()")
        row = cur.fetchone()
        metrics['db_table_count'] = row['cnt'] if row else 0
        db.close()
        metrics['db_connected'] = True
    except Exception as e:
        metrics['db_connected'] = False
        metrics['error'] = str(e)[:100]
    return metrics


def get_all_metrics():
    """
    获取所有指标（JSON 格式）

    返回:
        dict: 所有指标
    """
    with _metrics_lock:
        metrics = {
            'timestamp': time.time(),
            'requests': {
                'total': _request_count,
                'errors': _error_count,
                'error_rate': round(_error_count / _request_count * 100, 2) if _request_count > 0 else 0,
                'avg_duration_ms': round(_request_duration_sum / _request_count, 2) if _request_count > 0 else 0,
                'duration_buckets': dict(_request_duration_buckets),
            },
            'endpoints': {k: {
                'count': v['count'],
                'errors': v['errors'],
                'avg_duration_ms': round(v['duration_sum'] / v['count'], 2) if v['count'] > 0 else 0,
            } for k, v in _endpoint_metrics.items()},
            'business': dict(_business_metrics),
            'system': get_system_metrics(),
            'redis': get_redis_metrics(),
            'database': get_database_metrics(),
        }
    return metrics


def get_prometheus_metrics():
    """
    获取 Prometheus 兼容格式的指标

    返回:
        str: Prometheus 格式的指标文本
    """
    lines = []
    with _metrics_lock:
        # 请求指标
        lines.append('# HELP http_requests_total Total HTTP requests')
        lines.append('# TYPE http_requests_total counter')
        lines.append(f'http_requests_total {_request_count}')
        lines.append('')
        lines.append('# HELP http_request_duration_seconds HTTP request duration')
        lines.append('# TYPE http_request_duration_seconds summary')
        if _request_count > 0:
            avg = _request_duration_sum / _request_count / 1000
            lines.append(f'http_request_duration_seconds_sum {_request_duration_sum / 1000}')
            lines.append(f'http_request_duration_seconds_count {_request_count}')
        lines.append('')
        lines.append('# HELP http_errors_total Total HTTP errors')
        lines.append('# TYPE http_errors_total counter')
        lines.append(f'http_errors_total {_error_count}')
        lines.append('')

        # 业务指标
        lines.append('# HELP workflow_runs_total Total workflow runs')
        lines.append('# TYPE workflow_runs_total counter')
        lines.append(f'workflow_runs_total {_business_metrics["workflow_runs_total"]}')
        lines.append('')
        lines.append('# HELP tool_calls_total Total tool calls')
        lines.append('# TYPE tool_calls_total counter')
        lines.append(f'tool_calls_total {_business_metrics["tool_calls_total"]}')
        lines.append('')
        lines.append('# HELP llm_tokens_total Total LLM tokens used')
        lines.append('# TYPE llm_tokens_total counter')
        lines.append(f'llm_tokens_total {_business_metrics["llm_tokens_total"]}')
        lines.append('')

    # 系统指标
    try:
        import psutil
        lines.append('# HELP cpu_usage_percent CPU usage percentage')
        lines.append('# TYPE cpu_usage_percent gauge')
        lines.append(f'cpu_usage_percent {psutil.cpu_percent(interval=0.1)}')
        lines.append('')
        lines.append('# HELP memory_usage_percent Memory usage percentage')
        lines.append('# TYPE memory_usage_percent gauge')
        lines.append(f'memory_usage_percent {psutil.virtual_memory().percent}')
        lines.append('')
        lines.append('# HELP disk_usage_percent Disk usage percentage')
        lines.append('# TYPE disk_usage_percent gauge')
        lines.append(f'disk_usage_percent {psutil.disk_usage("/").percent}')
        lines.append('')
    except ImportError:
        pass

    return '\n'.join(lines)


if __name__ == '__main__':
    # 测试
    print("系统指标:")
    import json
    print(json.dumps(get_system_metrics(), indent=2, ensure_ascii=False))
    print("\nRedis 指标:")
    print(json.dumps(get_redis_metrics(), indent=2, ensure_ascii=False))
    print("\n数据库指标:")
    print(json.dumps(get_database_metrics(), indent=2, ensure_ascii=False))
