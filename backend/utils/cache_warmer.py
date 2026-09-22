# -*- coding: utf-8 -*-
"""
缓存预热与失效策略 —— 系统启动时预热高频数据，变更时自动失效

功能：
1. 缓存预热 (Cache Warming) - 启动时加载热点数据
2. 智能失效 (Smart Invalidation) - 数据变更时自动清除相关缓存
3. 批量预热接口 - 管理员可手动触发预热
4. 缓存健康检查 - 检查缓存系统状态

预热策略：
- 用户数据: 最近活跃的 100 个用户
- 应用配置: 所有已发布应用的配置
- 模型配置: 所有启用的模型配置
- 角色权限: 所有角色和权限映射
- 知识库元数据: 所有知识库基本信息

失效策略：
- 主动失效: 数据变更时立即清除
- 被动过期: TTL 到期自动失效
- 批量失效: 按前缀批量清除
"""

import logging
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================================
# 缓存预热器
# ============================================================

class CacheWarmer:
    """缓存预热器"""

    def __init__(self):
        self._warming_tasks: List[Dict] = []
        self._results: List[Dict] = []

    def register_task(self, name: str, func: Callable, priority: int = 50):
        """
        注册预热任务

        参数:
            name: 任务名称
            func: 执行函数，返回预热数据条数
            priority: 优先级 (数字越小优先级越高)
        """
        self._warming_tasks.append({
            'name': name,
            'func': func,
            'priority': priority,
        })
        # 按优先级排序
        self._warming_tasks.sort(key=lambda x: x['priority'])

    def warm_all(self) -> Dict:
        """
        执行所有预热任务

        返回:
            dict: 预热结果统计
        """
        self._results = []
        total_items = 0
        total_time = 0
        errors = 0

        logger.info(f'开始缓存预热，共 {len(self._warming_tasks)} 个任务')

        for task in self._warming_tasks:
            start = time.time()
            try:
                count = task['func']()
                duration = time.time() - start
                total_items += count
                total_time += duration
                self._results.append({
                    'name': task['name'],
                    'status': 'success',
                    'items': count,
                    'duration_ms': round(duration * 1000, 2),
                })
                logger.info(f'预热完成: {task["name"]}, {count} 条数据, {duration:.2f}s')
            except Exception as e:
                duration = time.time() - start
                errors += 1
                self._results.append({
                    'name': task['name'],
                    'status': 'failed',
                    'error': str(e),
                    'duration_ms': round(duration * 1000, 2),
                })
                logger.error(f'预热失败: {task["name"]}: {e}')

        result = {
            'total_tasks': len(self._warming_tasks),
            'success': len(self._warming_tasks) - errors,
            'failed': errors,
            'total_items': total_items,
            'total_time_ms': round(total_time * 1000, 2),
            'details': self._results,
        }

        logger.info(f'缓存预热完成: {result["success"]}/{result["total_tasks"]} 成功, '
                    f'{total_items} 条数据, {total_time:.2f}s')

        return result

    def warm_task(self, name: str) -> Optional[Dict]:
        """执行指定名称的预热任务"""
        for task in self._warming_tasks:
            if task['name'] == name:
                start = time.time()
                try:
                    count = task['func']()
                    return {
                        'name': name,
                        'status': 'success',
                        'items': count,
                        'duration_ms': round((time.time() - start) * 1000, 2),
                    }
                except Exception as e:
                    return {
                        'name': name,
                        'status': 'failed',
                        'error': str(e),
                        'duration_ms': round((time.time() - start) * 1000, 2),
                    }
        return None


# ============================================================
# 全局预热器实例
# ============================================================

warmer = CacheWarmer()


# ============================================================
# 预热任务函数
# ============================================================

def warm_users():
    """预热用户数据"""
    from config import get_db
    from utils.cache_manager import cache, CachePrefix

    db = get_db()
    try:
        cur = db.cursor()
        # 加载最近活跃的 100 个用户
        cur.execute('''
            SELECT id, name, nickname, email, phone, status
            FROM dify_accounts
            WHERE status = 'active'
            ORDER BY updated_at DESC
            LIMIT 100
        ''')
        users = cur.fetchall()
        for user in users:
            cache_key = f'{CachePrefix.USER}:{user["id"]}'
            cache.set(cache_key, dict(user), ttl=600)
        return len(users)
    finally:
        db.close()


def warm_apps():
    """预热应用数据"""
    from config import get_db
    from utils.cache_manager import cache, CachePrefix

    db = get_db()
    try:
        cur = db.cursor()
        # 加载所有已发布应用
        cur.execute('''
            SELECT id, tenant_id, name, mode, status
            FROM dify_apps
            WHERE status = 'normal'
            LIMIT 200
        ''')
        apps = cur.fetchall()
        for app in apps:
            cache_key = f'{CachePrefix.APP}:{app["id"]}'
            cache.set(cache_key, dict(app), ttl=300)
        return len(apps)
    finally:
        db.close()


def warm_model_configs():
    """预热模型配置"""
    from config import get_db
    from utils.cache_manager import cache, CachePrefix

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('''
            SELECT id, credential_name, provider, model_name, model_type, status
            FROM model_configs
            WHERE status = 1
        ''')
        configs = cur.fetchall()
        for cfg in configs:
            cache_key = f'{CachePrefix.MODEL}:{cfg["id"]}'
            cache.set(cache_key, dict(cfg), ttl=600)
        return len(configs)
    finally:
        db.close()


def warm_roles_permissions():
    """预热角色权限"""
    from config import get_db
    from utils.cache_manager import cache, CachePrefix

    db = get_db()
    try:
        cur = db.cursor()
        # 加载所有角色
        cur.execute('SELECT id, name, description FROM roles WHERE status = 1')
        roles = cur.fetchall()

        count = 0
        for role in roles:
            # 缓存角色信息
            role_key = f'{CachePrefix.ROLE}:{role["id"]}'
            cache.set(role_key, dict(role), ttl=1800)

            # 缓存角色权限
            cur.execute('''
                SELECT p.code
                FROM role_permissions rp
                JOIN permissions p ON p.id = rp.permission_id
                WHERE rp.role_id = %s
            ''', (role['id'],))
            permissions = [r['code'] for r in cur.fetchall()]
            perm_key = f'{CachePrefix.PERMISSION}:role:{role["id"]}'
            cache.set(perm_key, permissions, ttl=1800)
            count += 1

        return count
    finally:
        db.close()


def warm_knowledge_bases():
    """预热知识库元数据"""
    from config import get_db
    from utils.cache_manager import cache, CachePrefix

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('''
            SELECT id, tenant_id, name, description
            FROM dify_datasets
            LIMIT 100
        ''')
        datasets = cur.fetchall()
        for ds in datasets:
            cache_key = f'{CachePrefix.KNOWLEDGE}:{ds["id"]}'
            cache.set(cache_key, dict(ds), ttl=600)
        return len(datasets)
    finally:
        db.close()


def warm_tools():
    """预热工具配置"""
    from config import get_db
    from utils.cache_manager import cache, CachePrefix

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('SELECT tool_id FROM tool_installs')
        tools = cur.fetchall()
        for tool in tools:
            cache_key = f'{CachePrefix.TOOL}:{tool["tool_id"]}'
            cache.set(cache_key, {'installed': True}, ttl=3600)
        return len(tools)
    finally:
        db.close()


# ============================================================
# 注册预热任务
# ============================================================

def register_warming_tasks():
    """注册所有预热任务"""
    warmer.register_task('roles_permissions', warm_roles_permissions, priority=10)
    warmer.register_task('users', warm_users, priority=20)
    warmer.register_task('apps', warm_apps, priority=30)
    warmer.register_task('model_configs', warm_model_configs, priority=40)
    warmer.register_task('knowledge_bases', warm_knowledge_bases, priority=50)
    warmer.register_task('tools', warm_tools, priority=60)


# ============================================================
# 缓存健康检查
# ============================================================

def check_cache_health() -> Dict:
    """
    检查缓存系统健康状态

    返回:
        dict: 健康状态信息
    """
    from utils.cache_manager import cache, get_cache_stats

    result = {
        'timestamp': datetime.now().isoformat(),
        'status': 'unknown',
        'l1': {},
        'l2': {},
    }

    # L1 检查
    try:
        l1_stats = cache.l1.stats
        result['l1'] = {
            'status': 'healthy',
            'size': l1_stats['size'],
            'max_size': l1_stats['max_size'],
            'hit_rate': l1_stats['hit_rate'],
        }
    except Exception as e:
        result['l1'] = {
            'status': 'error',
            'error': str(e),
        }

    # L2 (Redis) 检查
    try:
        from utils.redis_cache import redis_available, get_redis
        if redis_available():
            r = get_redis()
            info = r.info('memory')
            result['l2'] = {
                'status': 'healthy',
                'used_memory_human': info.get('used_memory_human', 'unknown'),
                'connected_clients': r.info('clients').get('connected_clients', 0),
                'db_size': r.dbsize(),
            }
        else:
            result['l2'] = {
                'status': 'unavailable',
                'message': 'Redis 连接失败，使用 L1 缓存',
            }
    except Exception as e:
        result['l2'] = {
            'status': 'error',
            'error': str(e),
        }

    # 总体状态
    if result['l1'].get('status') == 'healthy':
        result['status'] = 'healthy'
    else:
        result['status'] = 'degraded'

    return result


# ============================================================
# 缓存失效映射
# ============================================================

# 数据表变更时对应的缓存前缀
INVALIDATION_MAP = {
    'dify_accounts': [CachePrefix.USER],
    'dify_apps': [CachePrefix.APP],
    'dify_workflows': [CachePrefix.WORKFLOW],
    'dify_datasets': [CachePrefix.KNOWLEDGE],
    'model_configs': [CachePrefix.MODEL],
    'roles': [CachePrefix.ROLE],
    'permissions': [CachePrefix.PERMISSION],
    'user_roles': [CachePrefix.ROLE],
    'role_permissions': [CachePrefix.PERMISSION],
    'tool_installs': [CachePrefix.TOOL],
    'plugins': [CachePrefix.PLUGIN],
    'workflow_templates': [CachePrefix.TEMPLATE],
    'agent_templates': [CachePrefix.TEMPLATE],
}


def invalidate_by_table(table_name: str):
    """
    根据数据表名失效相关缓存

    参数:
        table_name: 数据表名

    返回:
        int: 失效的缓存数量
    """
    from utils.cache_manager import cache

    prefixes = INVALIDATION_MAP.get(table_name, [])
    total = 0
    for prefix in prefixes:
        cache.invalidate_prefix(prefix)
        total += 1

    if total > 0:
        logger.info(f'缓存失效: 表 {table_name} -> 前缀 {prefixes}')

    return total


def invalidate_user_cache(user_id: str):
    """失效指定用户的缓存"""
    from utils.cache_manager import cache, CachePrefix
    cache.invalidate(f'{CachePrefix.USER}:{user_id}')


def invalidate_app_cache(app_id: str):
    """失效指定应用的缓存"""
    from utils.cache_manager import cache, CachePrefix
    cache.invalidate(f'{CachePrefix.APP}:{app_id}')
    cache.invalidate_prefix(f'{CachePrefix.WORKFLOW}:{app_id}')


# ============================================================
# 初始化
# ============================================================

def init_cache_system():
    """初始化缓存系统"""
    register_warming_tasks()
    logger.info('缓存系统初始化完成')
