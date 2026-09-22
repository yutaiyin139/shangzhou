# -*- coding: utf-8 -*-
"""数据库配置 —— 连接池管理"""

import pymysql
import pymysql.cursors
import importlib.util
import os

# 自动加载 .env 文件（如果存在）
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    if os.path.isfile(_env_path):
        load_dotenv(_env_path)
except ImportError:
    pass

# DBUtils 导入兼容（Python 3.14 大小写问题）
# 直接从文件加载 PooledDB 模块
_dbutils_dir = os.path.join(os.path.dirname(pymysql.__file__), '..', 'Lib', 'site-packages', 'dbutils')
if not os.path.isdir(_dbutils_dir):
    # 尝试从 sys.path 找到 dbutils
    for _p in __import__('sys').path:
        _candidate = os.path.join(_p, 'dbutils')
        if os.path.isdir(_candidate):
            _dbutils_dir = _candidate
            break

_spec_pooled = importlib.util.spec_from_file_location('dbutils.PooledDB', os.path.join(_dbutils_dir, 'pooled_db.py'))
_dbutils_pooled = importlib.util.module_from_spec(_spec_pooled)
_spec_pooled.loader.exec_module(_dbutils_pooled)
PooledDB = _dbutils_pooled.PooledDB

# ============================================================
# MySQL 配置（szagent 业务库，所有数据持久化到此）
# ============================================================

# 安全加固：数据库密码从环境变量读取，不再硬编码
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'szagent'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# ============================================================
# 连接池配置
# ============================================================

# 连接池实例（懒加载）
_db_pool = None


def _get_pool():
    """
    获取或创建数据库连接池（单例模式）

    连接池参数：
    - mincached: 初始空闲连接数（启动时创建）
    - maxcached: 最大空闲连接数
    - maxshared: 最大共享连接数（0 = 所有连接都是专用的）
    - maxconnections: 最大连接数（包括空闲+在用）
    - blocking: 连接数达到上限时是否阻塞等待
    - maxusage: 单个连接最大复用次数（None=无限）
    - setsession: 连接创建后执行的 SQL 命令列表
    """
    global _db_pool
    if _db_pool is None:
        _db_pool = PooledDB(
            creator=pymysql,           # 使用 pymysql 作为底层驱动
            mincached=2,               # 初始空闲连接
            maxcached=10,              # 最大空闲连接
            maxshared=0,               # 无共享连接（每个线程独占）
            maxconnections=20,         # 最大连接数
            blocking=True,             # 连接耗尽时阻塞等待
            maxusage=None,             # 连接无限复用
            setsession=[],             # 无初始化 SQL
            ping=1,                    # 取出连接前 ping 检测（0=不检测，1=空闲时检测）
            **DB_CONFIG
        )
    return _db_pool


def get_db():
    """
    获取 MySQL 连接（从连接池获取）

    使用方式：
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('SELECT 1')
        finally:
            db.close()  # 归还连接池，不是真正关闭

    注意：
    - 每次调用返回一个空闲连接
    - 使用完毕后必须调用 db.close() 归还连接
    - 连接池会在连接失效时自动重连
    """
    pool = _get_pool()
    return pool.connection()


def close_pool():
    """
    关闭连接池（应用退出时调用）
    """
    global _db_pool
    if _db_pool is not None:
        _db_pool.close()
        _db_pool = None


# ============================================================
# Marketplace API（可选，用于同步应用模板）
# ============================================================

MARKETPLACE_API_BASE = 'https://marketplace.dify.ai/api/v1'

# Marketplace 的英文分类到中文展示分类的映射
# 「应用模板」来自 Marketplace，按这些中文分类呈现
MARKETPLACE_CATEGORY_MAP = {
    'support': '客户服务',
    'knowledge': '知识检索',
    'operations': '办公提效',
    'marketing': '市场营销',
    'sales': '销售拓客',
    'it': '新手入门',
    'design': '新手入门',
    'others': '新手入门',
}

# 是否同步 Marketplace 全部模板（true = 严格复刻主页模板库）
MARKETPLACE_SYNC_ALL = True

# 如需只同步精选模板，可把 MARKETPLACE_SYNC_ALL 设为 False，并填写下方 ID 列表
MARKETPLACE_TEMPLATE_IDS = []


# ============================================================
# Redis / Celery 配置（异步任务队列）
# ============================================================

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
REDIS_DB_BROKER = 0      # Celery 消息代理 DB
REDIS_DB_BACKEND = 1     # Celery 结果存储 DB
REDIS_DB_CACHE = 2       # 应用缓存 DB

# Celery 配置
CELERY_CONFIG = {
    'broker_url': f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_BROKER}',
    'result_backend': f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_BACKEND}',
    'task_serializer': 'json',
    'result_serializer': 'json',
    'accept_content': ['json'],
    'timezone': 'Asia/Shanghai',
    'enable_utc': True,
    'task_track_started': True,
    'task_acks_late': True,
    'worker_prefetch_multiplier': 1,
    'task_time_limit': 1800,       # 硬超时 30 分钟
    'task_soft_time_limit': 1500,  # 软超时 25 分钟
    'result_expires': 86400,       # 结果保留 24 小时
    'task_default_retry_delay': 60,
    'task_max_retries': 3,
    'worker_max_tasks_per_child': 100,
    'worker_concurrency': 4,
}
