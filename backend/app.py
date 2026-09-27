# -*- coding: utf-8 -*-
r"""熵舟·智能体工作台 - 后端 API 服务入口"""

import os
import traceback
import time
import logging
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from routes import register_all_routes

# 配置结构化日志系统
from utils.logger import setup_logging, get_logger, log_request_start, log_request_end

setup_logging()
logger = get_logger(__name__)

app = Flask(__name__)
CORS(app)

# 注册所有业务路由
register_all_routes(app)

# 全局 API 鉴权闸门：默认全拦 + 显式公开白名单（模式由根目录 .env 的 REQUIRE_LOGIN_FOR_API 控制）。
# 位置必须在 register_all_routes 之后：路由模块 import config 时才把根目录 .env 载入环境。
from utils.api_guard import install_api_guard
install_api_guard(app)

# ============================================================
# WebSocket 初始化（可选，需要 flask-socketio）
# ============================================================

socketio = None
try:
    from utils.ws import init_socketio
    socketio = init_socketio(app)
    if socketio:
        logger.info('WebSocket 服务已初始化')
    else:
        logger.info('Flask-SocketIO 未安装，WebSocket 功能已禁用')
except Exception as e:
    logger.warning(f'WebSocket 初始化失败: {e}')


# ============================================================
# 请求计时中间件（记录慢请求）
# ============================================================

@app.before_request
def before_request():
    """请求开始计时"""
    g.start_time = time.time()


@app.after_request
def after_request(response):
    """请求结束记录"""
    if hasattr(g, 'start_time'):
        duration_ms = (time.time() - g.start_time) * 1000
        # 记录慢请求（超过 1 秒）
        if duration_ms > 1000:
            logger.warning(f'慢请求: {request.method} {request.path} - {response.status_code} ({duration_ms:.1f}ms)')
        # 添加响应头（便于调试）
        response.headers['X-Response-Time'] = f'{duration_ms:.1f}ms'
    return response


# ============================================================
# 健康检查端点（增强版）
# ============================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    健康检查端点（增强版）

    检查项目：
    - MySQL 数据库连接
    - Redis 连接
    - 系统资源（CPU/内存/磁盘）
    - Celery Worker 状态
    """
    from datetime import datetime
    import pymysql

    health = {
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        # 跟产品定版一致（README 与 front/package.json 都是 1.0.0）；以前这里写死 2.0.0，
        # 运维拿 /api/health 一看会以为跑的是下一个大版本。
        'version': os.environ.get('APP_VERSION', '1.0.0'),
        'services': {}
    }
    all_ok = True

    # 检查 MySQL
    db_status = {'status': 'unknown', 'latency_ms': 0}
    try:
        start = time.time()
        from config import get_db
        db = get_db()
        cur = db.cursor()
        cur.execute('SELECT 1')
        cur.fetchone()
        db.close()
        db_status = {'status': 'connected', 'latency_ms': round((time.time() - start) * 1000, 2)}
    except Exception as e:
        db_status = {'status': 'error', 'message': str(e)[:100]}
        all_ok = False
    health['services']['mysql'] = db_status

    # 检查 Redis
    redis_status = {'status': 'unknown', 'latency_ms': 0}
    try:
        start = time.time()
        from utils.redis_cache import get_redis_client
        r = get_redis_client()
        r.ping()
        redis_status = {'status': 'connected', 'latency_ms': round((time.time() - start) * 1000, 2)}
    except Exception as e:
        redis_status = {'status': 'error', 'message': str(e)[:100]}
        all_ok = False
    health['services']['redis'] = redis_status

    # 检查系统资源
    system_status = {'status': 'unknown'}
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        system_status = {
            'status': 'ok',
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_available_mb': round(memory.available / 1024 / 1024, 1),
            'disk_percent': disk.percent,
            'disk_free_gb': round(disk.free / 1024 / 1024 / 1024, 2),
        }
        # 资源告警
        if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
            system_status['status'] = 'warning'
            logger.warning(f'系统资源紧张: CPU={cpu_percent}%, MEM={memory.percent}%, DISK={disk.percent}%')
    except ImportError:
        system_status = {'status': 'unavailable', 'message': 'psutil not installed'}
    except Exception as e:
        system_status = {'status': 'error', 'message': str(e)[:100]}
    health['services']['system'] = system_status

    # 检查 Celery Worker
    celery_status = {'status': 'unknown'}
    try:
        from tasks.celery_app import celery_app
        inspector = celery_app.control.inspect(timeout=2)
        active_workers = inspector.active_queues()
        if active_workers:
            celery_status = {
                'status': 'connected',
                'workers': len(active_workers),
            }
        else:
            celery_status = {'status': 'no_workers'}
    except Exception as e:
        celery_status = {'status': 'error', 'message': str(e)[:100]}
    health['services']['celery'] = celery_status

    # 总体状态
    health['status'] = 'healthy' if all_ok else 'degraded'

    status_code = 200 if all_ok else 503
    return jsonify(code=200 if all_ok else 503, msg=health['status'], data=health), status_code


@app.route('/api/ping', methods=['GET'])
def ping():
    """轻量级存活探针（用于负载均衡器）"""
    # datetime 在模块顶层并未导入（只在本文件其他函数内局部导入），
    # 以前这个探针一调用就 NameError 500，而健康检查用的是 /api/health，所以一直没被发现
    from datetime import datetime
    return jsonify(code=200, msg='pong', timestamp=datetime.now().isoformat())


# ============================================================
# 监控指标端点（Prometheus 兼容）
# ============================================================

@app.route('/api/metrics', methods=['GET'])
def metrics():
    """
    监控指标端点

    支持两种格式：
    - Prometheus 格式（?format=prometheus）
    - JSON 格式（默认）
    """
    fmt = request.args.get('format', 'json')
    if fmt == 'prometheus':
        from utils.metrics import get_prometheus_metrics
        return get_prometheus_metrics(), 200, {'Content-Type': 'text/plain; charset=utf-8'}
    else:
        from utils.metrics import get_all_metrics
        return jsonify(code=200, data=get_all_metrics())


# ============================================================
# 全局错误处理器 —— 确保所有错误都返回 JSON 格式
# ============================================================

def _is_debug():
    """是否开启调试模式（安全加固：默认关闭）"""
    return os.environ.get('FLASK_DEBUG', '0') == '1' or app.debug


@app.errorhandler(400)
def bad_request(e):
    return jsonify(code=400, msg='请求参数错误'), 400


@app.errorhandler(404)
def not_found(e):
    return jsonify(code=404, msg='接口不存在'), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify(code=405, msg='请求方法不允许'), 405


@app.errorhandler(500)
def internal_error(e):
    logging.error(f'500 错误: {str(e)}', exc_info=True)
    if _is_debug():
        return jsonify(code=500, msg=f'服务器内部错误: {str(e)}', detail=traceback.format_exc()), 500
    return jsonify(code=500, msg='服务器内部错误'), 500


@app.errorhandler(Exception)
def handle_exception(e):
    """捕获所有未处理的异常，返回 JSON 格式错误"""
    logging.error(f'未处理的异常: {str(e)}', exc_info=True)
    if _is_debug():
        return jsonify(code=500, msg=f'服务器内部错误: {str(e)}', detail=traceback.format_exc()), 500
    return jsonify(code=500, msg='服务器内部错误'), 500


def init_cache_system():
    """初始化缓存系统（应用启动时调用）"""
    try:
        from utils.cache_warmer import init_cache_system as _init
        _init()
        logger.info('缓存系统初始化完成')
    except Exception as e:
        logger.warning(f'缓存系统初始化失败: {e}')


if __name__ == '__main__':
    # 初始化缓存系统
    init_cache_system()

    # 安全加固：debug 模式从环境变量控制，默认关闭
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    if socketio:
        # 使用 SocketIO 运行（支持 WebSocket）
        socketio.run(app, host='0.0.0.0', port=5000, debug=debug_mode)
    else:
        # 普通 Flask 运行
        app.run(host='0.0.0.0', port=5000, debug=debug_mode)
