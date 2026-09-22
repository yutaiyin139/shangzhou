# -*- coding: utf-8 -*-
"""
缓存管理路由 —— 缓存状态监控、手动清理、预热

API 列表:
- GET  /api/cache/stats         - 缓存统计信息
- GET  /api/cache/health        - 缓存健康检查
- POST /api/cache/warm          - 手动触发缓存预热
- DELETE /api/cache/clear       - 清除缓存
- POST /api/cache/invalidate    - 按前缀失效缓存
"""

import logging
from flask import jsonify, request
from utils.auth import login_required, role_required

logger = logging.getLogger(__name__)


def register_cache_routes(app):
    """注册缓存管理路由"""

    @app.route('/api/cache/stats', methods=['GET'])
    @login_required
    @role_required('admin')
    def get_cache_stats():
        """
        获取缓存统计信息

        返回:
            L1 缓存统计 (命中率、大小)
            L2 Redis 统计 (内存使用、连接数)
        """
        try:
            from utils.cache_manager import get_cache_stats
            stats = get_cache_stats()
            return jsonify(code=200, data=stats)
        except Exception as e:
            return jsonify(code=500, msg=f'获取缓存统计失败: {str(e)}')

    @app.route('/api/cache/health', methods=['GET'])
    @login_required
    @role_required('admin')
    def cache_health():
        """
        缓存健康检查

        返回:
            L1/L2 健康状态
        """
        try:
            from utils.cache_warmer import check_cache_health
            health = check_cache_health()
            return jsonify(code=200, data=health)
        except Exception as e:
            return jsonify(code=500, msg=f'健康检查失败: {str(e)}')

    @app.route('/api/cache/warm', methods=['POST'])
    @login_required
    @role_required('admin')
    def warm_cache():
        """
        手动触发缓存预热

        请求体:
            { task: str }  - 指定任务名称，不传则预热全部
        """
        try:
            from utils.cache_warmer import warmer, warm_all

            d = request.get_json(silent=True) or {}
            task_name = d.get('task', '').strip()

            if task_name:
                result = warmer.warm_task(task_name)
                if result is None:
                    return jsonify(code=404, msg=f'未找到预热任务: {task_name}')
                return jsonify(code=200, data=result)
            else:
                result = warm_all()
                return jsonify(code=200, data=result)

        except Exception as e:
            return jsonify(code=500, msg=f'缓存预热失败: {str(e)}')

    @app.route('/api/cache/clear', methods=['DELETE'])
    @login_required
    @role_required('admin')
    def clear_cache():
        """
        清除缓存

        请求体:
            { prefix: str }  - 指定前缀，不传则清除全部 L1 缓存
        """
        try:
            from utils.cache_manager import cache

            d = request.get_json(silent=True) or {}
            prefix = d.get('prefix', '').strip()

            if prefix:
                cache.invalidate_prefix(prefix)
                return jsonify(code=200, msg=f'已清除前缀为 "{prefix}" 的缓存')
            else:
                cache.l1.clear()
                return jsonify(code=200, msg='已清除 L1 缓存')

        except Exception as e:
            return jsonify(code=500, msg=f'清除缓存失败: {str(e)}')

    @app.route('/api/cache/invalidate', methods=['POST'])
    @login_required
    @role_required('admin')
    def invalidate_cache():
        """
        按前缀失效缓存

        请求体:
            { prefix: str }  - 缓存键前缀
        """
        try:
            from utils.cache_manager import cache

            d = request.get_json() or {}
            prefix = d.get('prefix', '').strip()

            if not prefix:
                return jsonify(code=400, msg='请提供 prefix 参数')

            cache.invalidate_prefix(prefix)
            return jsonify(code=200, msg=f'已失效前缀为 "{prefix}" 的缓存')

        except Exception as e:
            return jsonify(code=500, msg=f'缓存失效失败: {str(e)}')

    @app.route('/api/cache/keys', methods=['GET'])
    @login_required
    @role_required('admin')
    def list_cache_keys():
        """
        列出缓存键 (Redis)

        查询参数:
            pattern: 匹配模式 (默认 *)
            limit: 返回数量限制 (默认 100)
        """
        try:
            from utils.redis_cache import get_redis, redis_available

            if not redis_available():
                return jsonify(code=500, msg='Redis 不可用')

            pattern = request.args.get('pattern', '*')
            limit = min(1000, max(1, request.args.get('limit', 100, type=int)))

            r = get_redis()
            keys = []
            cursor = 0
            while True:
                cursor, partial_keys = r.scan(cursor, match=pattern, count=100)
                keys.extend(partial_keys)
                if cursor == 0 or len(keys) >= limit:
                    break

            keys = keys[:limit]

            # 获取每个 key 的 TTL
            result = []
            pipe = r.pipeline()
            for key in keys:
                pipe.ttl(key)
            ttls = pipe.execute()

            for key, ttl in zip(keys, ttls):
                result.append({
                    'key': key,
                    'ttl': ttl,
                })

            return jsonify(code=200, data={
                'keys': result,
                'total': len(result),
                'pattern': pattern,
            })

        except Exception as e:
            return jsonify(code=500, msg=f'获取缓存键失败: {str(e)}')
