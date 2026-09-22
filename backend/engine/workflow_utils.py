# -*- coding: utf-8 -*-
"""
工作流引擎工具函数 —— 从 workflow_runner.py 提取的公共模块

包含:
- HTTP 客户端（连接检查 + 重试）
- 任务管理（注册/取消/查询活跃任务）
- 模型配置查找
- 节点执行记录
- 思考链提取
- 安全序列化

此模块可被 workflow_runner、routes、tasks 等多处复用。
"""

import json
import logging
import socket
import ssl
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime
from config import get_db

logger = logging.getLogger(__name__)


# ============================================================
# HTTP 客户端配置
# ============================================================

def create_ssl_context():
    """创建 SSL 上下文，兼容各种证书配置"""
    return ssl.create_default_context()


def check_connectivity(host, port=443, timeout=5):
    """
    检查目标主机端口是否可达

    返回: (是否可达, 错误信息)
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            return True, None
        return False, f'无法连接到 {host}:{port} (错误码: {result})'
    except socket.gaierror:
        return False, f'DNS 解析失败: {host}'
    except Exception as e:
        return False, f'网络检查失败: {e}'


def http_request(url, data=None, headers=None, method='POST', timeout=120, retries=2):
    """
    带重试机制的 HTTP 请求函数（带连接预检查）

    参数:
        url: 请求 URL
        data: 请求体 (bytes)
        headers: 请求头字典
        method: HTTP 方法
        timeout: 超时时间 (秒)
        retries: 重试次数

    返回: 响应对象
    """
    # 预检查连通性
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        if host:
            reachable, conn_err = check_connectivity(host, port, timeout=5)
            if not reachable:
                error_msg = (
                    f'无法连接到模型 API 服务器 ({host}:{port})。'
                    f'请检查网络连接或更换为可访问的模型提供商（如 DeepSeek）。'
                    f'详情: {conn_err}'
                )
                logger.error(f'[HTTP] {error_msg}')
                raise ConnectionError(error_msg)
    except (ValueError, ImportError):
        pass

    last_error = None
    ctx = create_ssl_context()

    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
            response = urllib.request.urlopen(req, timeout=timeout, context=ctx)
            return response
        except (urllib.error.URLError, socket.timeout, TimeoutError) as e:
            last_error = e
            if 'WinError 10060' in str(e) or 'timed out' in str(e).lower():
                error_msg = (
                    f'连接模型 API 超时 ({url})。'
                    f'可能原因：1) 网络不稳定 2) API 服务器被防火墙阻止 3) 需要使用代理。'
                    f'建议更换为 DeepSeek 等国内可访问的模型。'
                )
                logger.error(f'[HTTP] {error_msg}')
                raise ConnectionError(error_msg) from e
            if attempt < retries:
                wait_time = 2 * (attempt + 1)
                logger.warning(f'[HTTP] 请求失败 (尝试 {attempt+1}/{retries+1}): {url}, 错误: {e}, {wait_time}秒后重试...')
                time.sleep(wait_time)
            else:
                logger.error(f'[HTTP] 请求最终失败: {url}, 错误: {e}')
                raise
        except Exception as e:
            logger.error(f'[HTTP] 请求异常: {url}, 错误: {type(e).__name__}: {e}')
            raise

    raise last_error


# ============================================================
# 工作流任务管理
# ============================================================

_active_workflow_tasks = {}
_workflow_lock = threading.Lock()


def register_workflow_task(run_id, thread_id=None):
    """注册一个工作流任务"""
    if thread_id is None:
        thread_id = threading.current_thread().ident
    with _workflow_lock:
        _active_workflow_tasks[run_id] = {
            'cancelled': False,
            'thread_id': thread_id,
            'started_at': time.time()
        }


def cancel_workflow_task(run_id):
    """取消一个工作流任务（返回是否成功）"""
    with _workflow_lock:
        if run_id in _active_workflow_tasks:
            _active_workflow_tasks[run_id]['cancelled'] = True
            return True
    return False


def is_workflow_task_cancelled(run_id):
    """检查工作流任务是否已被取消"""
    with _workflow_lock:
        task = _active_workflow_tasks.get(run_id)
        return task['cancelled'] if task else False


def unregister_workflow_task(run_id):
    """注销一个工作流任务"""
    with _workflow_lock:
        _active_workflow_tasks.pop(run_id, None)


def get_active_workflow_tasks():
    """获取当前活跃的工作流任务列表"""
    with _workflow_lock:
        return {
            run_id: {
                'cancelled': info['cancelled'],
                'thread_id': info['thread_id'],
                'running_for': time.time() - info['started_at']
            }
            for run_id, info in _active_workflow_tasks.items()
        }


# ============================================================
# 模型配置查找
# ============================================================

def find_model_config(provider):
    """
    查找模型配置，支持多种 provider 格式匹配：
    - 精确匹配
    - langgenius 前缀提取
    - 后缀匹配
    - 最后一段匹配

    参数:
        provider: 供应商名称，None 时取最新启用的配置

    返回: 配置字典或 None
    """
    db = get_db()
    try:
        cur = db.cursor()
        if not provider:
            cur.execute('SELECT * FROM model_configs WHERE status = 1 ORDER BY updated_at DESC LIMIT 1')
            return cur.fetchone()

        # 1. 精确匹配
        cur.execute('SELECT * FROM model_configs WHERE provider = %s AND status = 1 LIMIT 1', (provider,))
        cfg = cur.fetchone()
        if cfg:
            return cfg

        # 2. 从 langgenius/provider/provider 格式提取短名称匹配
        if provider.startswith('langgenius/'):
            parts = provider.split('/')
            if len(parts) >= 2:
                short_provider = parts[1]
                cur.execute('SELECT * FROM model_configs WHERE provider = %s AND status = 1 LIMIT 1', (short_provider,))
                cfg = cur.fetchone()
                if cfg:
                    return cfg

        # 3. 反向匹配
        cur.execute('SELECT * FROM model_configs WHERE provider LIKE %s AND status = 1 LIMIT 1', ('%/' + provider,))
        cfg = cur.fetchone()
        if cfg:
            return cfg

        # 4. 取最后一段匹配
        if '/' in provider:
            last_part = provider.split('/')[-1]
            cur.execute('SELECT * FROM model_configs WHERE provider = %s AND status = 1 LIMIT 1', (last_part,))
            return cur.fetchone()

        return None
    finally:
        db.close()


def get_model_config(provider_name=None):
    """
    获取模型配置（简化版，直接查询 model_configs 表）

    参数:
        provider_name: 供应商名称，None 时取最新启用的配置
    """
    db = get_db()
    try:
        cur = db.cursor()
        if provider_name and provider_name != 'auto':
            cur.execute(
                'SELECT * FROM model_configs WHERE provider = %s AND status = 1 LIMIT 1',
                (provider_name,))
        else:
            cur.execute(
                'SELECT * FROM model_configs WHERE status = 1 ORDER BY updated_at DESC LIMIT 1')
        return cur.fetchone()
    finally:
        db.close()


# ============================================================
# 节点执行记录
# ============================================================

def record_node_start(run_id, app_id, exec_id, node_id, node_type, title=''):
    """记录节点开始执行"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            '''INSERT INTO workflow_node_executions
               (run_id, app_id, node_id, node_type, title, status, started_at)
               VALUES (%s, %s, %s, %s, %s, 'running', NOW())''',
            (run_id, app_id, node_id, node_type, title))
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


def record_node_end(exec_id, status, outputs=None, error=None):
    """记录节点执行完成"""
    db = get_db()
    try:
        cur = db.cursor()
        outputs_json = json.dumps(outputs, ensure_ascii=False, default=str)[:5000] if outputs else ''
        error_str = str(error)[:1000] if error else ''
        cur.execute(
            '''UPDATE workflow_node_executions
               SET status = %s, outputs = %s, error = %s, completed_at = NOW()
               WHERE id = %s''',
            (status, outputs_json, error_str, exec_id))
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


# ============================================================
# 思考链提取
# ============================================================

def extract_thought_chains(result):
    """
    从工作流执行结果中提取所有 Agent 节点的思考链。
    返回合并后的思考链列表（带节点标识）。
    """
    if not isinstance(result, dict):
        return []
    chains = []
    for key, value in result.items():
        if key == 'thought_chain' and isinstance(value, list):
            for entry in value:
                if isinstance(entry, dict):
                    chains.append(entry)
    chains.sort(key=lambda x: x.get('position', 0))
    return chains


# ============================================================
# 安全序列化
# ============================================================

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


# ============================================================
# 便捷函数：检查取消状态（用于长循环中）
# ============================================================

def check_cancelled(run_id):
    """
    检查任务是否被取消，如果取消则返回 True。
    可在长循环中调用以支持优雅退出。
    """
    return is_workflow_task_cancelled(run_id)
