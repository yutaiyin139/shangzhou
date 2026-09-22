# -*- coding: utf-8 -*-
"""
备份管理路由 —— 备份状态查询、手动触发、配置管理

API 列表:
- GET  /api/backup/status        - 备份状态概览
- POST /api/backup/trigger       - 手动触发备份
- GET  /api/backup/list          - 备份文件列表
- GET  /api/backup/logs          - 备份日志
- POST /api/backup/verify        - 验证备份
- DELETE /api/backup/cleanup     - 清理过期备份
- GET  /api/backup/config        - 备份配置
- PUT  /api/backup/config        - 更新备份配置
"""

import os
import logging
from datetime import datetime, timedelta
from flask import jsonify, request
from config import get_db
from utils.auth import login_required, role_required

logger = logging.getLogger(__name__)

# 备份根目录
BACKUP_ROOT = os.getenv('BACKUP_DIR', '/var/lib/szagent/backups')


def register_backup_routes(app):
    """注册备份管理路由"""

    @app.route('/api/backup/status', methods=['GET'])
    @login_required
    @role_required('admin')
    def get_backup_status():
        """
        获取备份状态概览

        返回:
            last_backup: 最近备份时间
            total_backups: 备份总数
            total_size: 总占用空间
            mysql_status: MySQL 备份状态
            redis_status: Redis 备份状态
            files_status: 文件备份状态
        """
        try:
            status = {
                'last_backup': None,
                'total_backups': 0,
                'total_size': 0,
                'mysql': {'count': 0, 'size': 0, 'last': None},
                'redis': {'count': 0, 'size': 0, 'last': None},
                'files': {'count': 0, 'size': 0, 'last': None},
            }

            # 扫描备份目录
            backup_types = ['mysql', 'redis', 'files']
            for btype in backup_types:
                dir_path = os.path.join(BACKUP_ROOT, btype)
                if not os.path.exists(dir_path):
                    continue

                files = []
                for f in os.listdir(dir_path):
                    filepath = os.path.join(dir_path, f)
                    if os.path.isfile(filepath):
                        stat = os.stat(filepath)
                        files.append({
                            'name': f,
                            'size': stat.st_size,
                            'mtime': stat.st_mtime,
                        })

                files.sort(key=lambda x: x['mtime'], reverse=True)

                status[btype]['count'] = len(files)
                status[btype]['size'] = sum(f['size'] for f in files)
                if files:
                    status[btype]['last'] = datetime.fromtimestamp(
                        files[0]['mtime']
                    ).strftime('%Y-%m-%d %H:%M:%S')

                status['total_backups'] += len(files)
                status['total_size'] += status[btype]['size']

                # 更新最近备份时间
                if files and (status['last_backup'] is None or
                              files[0]['mtime'] > datetime.strptime(
                                  status['last_backup'], '%Y-%m-%d %H:%M:%S'
                              ).timestamp() if status['last_backup'] else True):
                    status['last_backup'] = status[btype]['last']

            # 格式化大小
            status['total_size_human'] = _format_size(status['total_size'])
            status['mysql']['size_human'] = _format_size(status['mysql']['size'])
            status['redis']['size_human'] = _format_size(status['redis']['size'])
            status['files']['size_human'] = _format_size(status['files']['size'])

            return jsonify(code=200, data=status)

        except Exception as e:
            return jsonify(code=500, msg=f'获取备份状态失败: {str(e)}')

    @app.route('/api/backup/trigger', methods=['POST'])
    @login_required
    @role_required('admin')
    def trigger_backup():
        """
        手动触发备份

        请求体:
            { type: 'full' | 'mysql' | 'redis' | 'files' }
        """
        try:
            d = request.get_json() or {}
            backup_type = d.get('type', 'full')

            from tasks.backup_task import BackupExecutor
            executor = BackupExecutor()
            results = {}

            if backup_type in ('full', 'mysql'):
                results['mysql'] = executor.backup_mysql_full()
            if backup_type in ('full', 'redis'):
                results['redis'] = executor.backup_redis()
            if backup_type in ('full', 'files'):
                results['files'] = executor.backup_files()

            # 记录备份日志
            from tasks.backup_task import _log_backup_result
            _log_backup_result(results)

            # 检查是否有失败
            has_failure = any(not r.get('success') for r in results.values())

            return jsonify(
                code=200 if not has_failure else 207,
                msg='备份完成' if not has_failure else '部分备份失败',
                data=results,
            )

        except Exception as e:
            return jsonify(code=500, msg=f'备份触发失败: {str(e)}')

    @app.route('/api/backup/list', methods=['GET'])
    @login_required
    @role_required('admin')
    def list_backups():
        """
        获取备份文件列表

        查询参数:
            type: 备份类型 (mysql/redis/files)
            limit: 返回数量限制 (默认 50)
        """
        try:
            backup_type = request.args.get('type', '')
            limit = min(100, max(1, request.args.get('limit', 50, type=int)))

            items = []
            types_to_list = [backup_type] if backup_type else ['mysql', 'redis', 'files']

            for btype in types_to_list:
                dir_path = os.path.join(BACKUP_ROOT, btype)
                if not os.path.exists(dir_path):
                    continue

                for f in os.listdir(dir_path):
                    filepath = os.path.join(dir_path, f)
                    if os.path.isfile(filepath):
                        stat = os.stat(filepath)
                        items.append({
                            'type': btype,
                            'name': f,
                            'size': stat.st_size,
                            'size_human': _format_size(stat.st_size),
                            'created_at': datetime.fromtimestamp(
                                stat.st_mtime
                            ).strftime('%Y-%m-%d %H:%M:%S'),
                        })

            # 按时间倒序
            items.sort(key=lambda x: x['created_at'], reverse=True)
            items = items[:limit]

            return jsonify(code=200, data={
                'items': items,
                'total': len(items),
            })

        except Exception as e:
            return jsonify(code=500, msg=f'获取备份列表失败: {str(e)}')

    @app.route('/api/backup/logs', methods=['GET'])
    @login_required
    @role_required('admin')
    def get_backup_logs():
        """
        获取备份日志

        查询参数:
            page: 页码
            page_size: 每页条数
            type: 备份类型筛选
            status: 状态筛选
        """
        try:
            page = max(1, request.args.get('page', 1, type=int))
            page_size = min(100, max(1, request.args.get('page_size', 20, type=int)))
            offset = (page - 1) * page_size

            backup_type = request.args.get('type', '').strip()
            status = request.args.get('status', '').strip()

            db = get_db()
            cur = db.cursor()

            # 确保表存在
            cur.execute('''
                CREATE TABLE IF NOT EXISTS backup_logs (
                    id VARCHAR(36) PRIMARY KEY,
                    backup_type VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    file_path VARCHAR(500),
                    file_size BIGINT DEFAULT 0,
                    md5_hash VARCHAR(64),
                    duration_seconds INT DEFAULT 0,
                    message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_type (backup_type),
                    INDEX idx_status (status),
                    INDEX idx_created (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')

            # 构建查询
            conditions = []
            params = []
            if backup_type:
                conditions.append('backup_type = %s')
                params.append(backup_type)
            if status:
                conditions.append('status = %s')
                params.append(status)

            where = 'WHERE ' + ' AND '.join(conditions) if conditions else ''

            # 总数
            cur.execute(f'SELECT COUNT(*) as total FROM backup_logs {where}', params)
            total = cur.fetchone()['total']

            # 数据
            cur.execute(f'''
                SELECT * FROM backup_logs
                {where}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            ''', params + [page_size, offset])

            items = []
            for row in cur.fetchall():
                items.append({
                    'id': row['id'],
                    'backup_type': row['backup_type'],
                    'status': row['status'],
                    'file_path': row['file_path'],
                    'file_size': row['file_size'],
                    'file_size_human': _format_size(row['file_size'] or 0),
                    'md5_hash': row['md5_hash'],
                    'duration_seconds': row['duration_seconds'],
                    'message': row['message'],
                    'created_at': str(row['created_at']) if row['created_at'] else '',
                })

            db.close()

            return jsonify(code=200, data={
                'items': items,
                'total': total,
                'page': page,
                'page_size': page_size,
            })

        except Exception as e:
            return jsonify(code=500, msg=f'获取备份日志失败: {str(e)}')

    @app.route('/api/backup/verify', methods=['POST'])
    @login_required
    @role_required('admin')
    def verify_backup():
        """
        验证备份文件

        请求体:
            { file_path: str }
        """
        try:
            d = request.get_json() or {}
            filepath = d.get('file_path', '').strip()

            if not filepath:
                return jsonify(code=400, msg='请提供文件路径')

            if not os.path.exists(filepath):
                return jsonify(code=404, msg='文件不存在')

            from tasks.backup_task import BackupExecutor
            executor = BackupExecutor()
            result = executor.verify_backup(filepath)

            return jsonify(code=200, data=result)

        except Exception as e:
            return jsonify(code=500, msg=f'验证失败: {str(e)}')

    @app.route('/api/backup/cleanup', methods=['POST'])
    @login_required
    @role_required('admin')
    def cleanup_backups():
        """
        清理过期备份

        请求体:
            { retain_days: int }  - 保留天数 (默认 30)
        """
        try:
            d = request.get_json() or {}
            retain_days = max(1, min(365, int(d.get('retain_days', 30))))

            from tasks.backup_task import BackupExecutor
            executor = BackupExecutor()
            executor.backup_dir = BACKUP_ROOT
            executor.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # 临时修改保留策略
            from tasks import backup_task
            original_retention = backup_task.BACKUP_RETENTION.copy()
            backup_task.BACKUP_RETENTION = {'custom': retain_days}

            result = executor.cleanup_old_backups()

            # 恢复原始策略
            backup_task.BACKUP_RETENTION = original_retention

            return jsonify(code=200, msg='清理完成', data={
                'deleted_count': result['deleted_count'],
                'freed_space': result['freed_space'],
                'freed_space_human': _format_size(result['freed_space']),
            })

        except Exception as e:
            return jsonify(code=500, msg=f'清理失败: {str(e)}')

    @app.route('/api/backup/config', methods=['GET'])
    @login_required
    @role_required('admin')
    def get_backup_config():
        """获取备份配置"""
        from tasks import backup_task

        config = {
            'backup_root': BACKUP_ROOT,
            'retention': backup_task.BACKUP_RETENTION,
            'remote_enabled': backup_task.REMOTE_BACKUP_ENABLED,
            'remote_backend': backup_task.REMOTE_BACKEND,
            'mysql_host': backup_task.MYSQL_CONFIG['host'],
            'mysql_database': backup_task.MYSQL_CONFIG['database'],
        }

        return jsonify(code=200, data=config)


def _format_size(size_bytes):
    """格式化文件大小"""
    if size_bytes < 1024:
        return f'{size_bytes} B'
    elif size_bytes < 1024 * 1024:
        return f'{size_bytes / 1024:.1f} KB'
    elif size_bytes < 1024 * 1024 * 1024:
        return f'{size_bytes / 1024 / 1024:.1f} MB'
    else:
        return f'{size_bytes / 1024 / 1024 / 1024:.2f} GB'
