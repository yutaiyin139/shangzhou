# -*- coding: utf-8 -*-
"""操作日志（审计日志）路由

记录平台关键操作，用于安全审计、合规检查和问题追溯。
支持的操作类型：
- 认证相关：登录、登出、密码修改、Token 刷新
- 工作流相关：创建、编辑、删除、运行、发布
- 知识库相关：创建、编辑、删除、上传文档
- 智能体相关：创建、编辑、删除
- 用户管理：创建、编辑、删除、角色变更
- 模型配置：创建、编辑、删除
"""

import json
import uuid
from datetime import datetime
from flask import jsonify, request
from config import get_db
from models.tables import AUDIT_LOGS_TABLE_SQL


def _ensure_audit_table():
    """确保审计日志表已创建"""
    try:
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(AUDIT_LOGS_TABLE_SQL)
            db.commit()
        finally:
            db.close()
    except Exception:
        # 表创建失败不影响主流程
        pass


def log_audit_event(action, resource_type='', resource_id='', resource_name='',
                    description='', status='success', error_message='',
                    user_id=None, user_name='', user_email='',
                    request_obj=None, response_code=0, extra_data=None):
    """
    记录一条审计日志

    参数:
        action: 操作类型（如 login, create_workflow, delete_knowledge）
        resource_type: 资源类型（如 workflow, knowledge, agent, user, model）
        resource_id: 资源 ID
        resource_name: 资源名称
        description: 操作描述
        status: 操作状态（success/failed）
        error_message: 错误信息（失败时）
        user_id: 操作用户 ID
        user_name: 操作用户名称
        user_email: 操作用户邮箱
        request_obj: Flask request 对象（可选，自动提取 IP/UA/路径）
        response_code: HTTP 响应码
        extra_data: 额外数据（字典，自动 JSON 序列化）
    """
    try:
        _ensure_audit_table()

        # 从 request 对象提取信息
        ip_address = ''
        user_agent = ''
        request_method = ''
        request_path = ''
        request_body = ''

        if request_obj is not None:
            try:
                ip_address = request_obj.remote_addr or ''
                user_agent = request_obj.headers.get('User-Agent', '')[:500]
                request_method = request_obj.method or ''
                request_path = request_obj.path or ''

                # 记录请求体（排除敏感字段）
                if request_obj.is_json:
                    body = request_obj.get_json(silent=True) or {}
                    # 过滤敏感字段
                    sensitive_fields = {'password', 'token', 'api_key', 'secret', 'credential'}
                    filtered_body = {k: v for k, v in body.items()
                                    if k.lower() not in sensitive_fields}
                    request_body = json.dumps(filtered_body, ensure_ascii=False)[:2000]
            except Exception:
                pass

        # 序列化额外数据
        extra_data_str = ''
        if extra_data is not None:
            try:
                extra_data_str = json.dumps(extra_data, ensure_ascii=False)[:2000]
            except Exception:
                extra_data_str = str(extra_data)[:2000]

        # 写入数据库
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('''
                INSERT INTO dify_audit_logs
                (id, user_id, user_name, user_email, action, resource_type,
                 resource_id, resource_name, description, ip_address, user_agent,
                 request_method, request_path, request_body, response_code,
                 status, error_message, extra_data, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                str(uuid.uuid4()),
                user_id or '',
                user_name or '',
                user_email or '',
                action,
                resource_type,
                resource_id or '',
                resource_name or '',
                description or '',
                ip_address,
                user_agent,
                request_method,
                request_path,
                request_body,
                response_code,
                status,
                error_message or '',
                extra_data_str,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            ))
            db.commit()
        except Exception as e:
            # 日志记录失败不应影响主流程
            import logging
            logging.error(f'写入审计日志失败: {str(e)}')
        finally:
            db.close()
    except Exception:
        # 确保任何异常都不会影响主流程
        pass


def register_audit_routes(app):
    """注册审计日志路由"""

    @app.route('/api/audit/logs', methods=['GET'])
    def get_audit_logs():
        """查询审计日志列表

        查询参数:
            page: 页码（默认 1）
            page_size: 每页条数（默认 20，最大 100）
            action: 操作类型筛选
            resource_type: 资源类型筛选
            user_id: 用户 ID 筛选
            status: 状态筛选（success/failed）
            start_time: 开始时间（YYYY-MM-DD HH:MM:SS）
            end_time: 结束时间（YYYY-MM-DD HH:MM:SS）
            keyword: 关键词搜索（描述、资源名称）
        """
        _ensure_audit_table()

        # 解析查询参数
        page = max(1, request.args.get('page', 1, type=int))
        page_size = min(100, max(1, request.args.get('page_size', 20, type=int)))
        offset = (page - 1) * page_size

        action = request.args.get('action', '').strip()
        resource_type = request.args.get('resource_type', '').strip()
        user_id = request.args.get('user_id', '').strip()
        status = request.args.get('status', '').strip()
        start_time = request.args.get('start_time', '').strip()
        end_time = request.args.get('end_time', '').strip()
        keyword = request.args.get('keyword', '').strip()

        # 构建查询条件
        conditions = []
        params = []

        if action:
            conditions.append('action = %s')
            params.append(action)
        if resource_type:
            conditions.append('resource_type = %s')
            params.append(resource_type)
        if user_id:
            conditions.append('user_id = %s')
            params.append(user_id)
        if status:
            conditions.append('status = %s')
            params.append(status)
        if start_time:
            conditions.append('created_at >= %s')
            params.append(start_time)
        if end_time:
            conditions.append('created_at <= %s')
            params.append(end_time)
        if keyword:
            conditions.append('(description LIKE %s OR resource_name LIKE %s OR user_name LIKE %s)')
            params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])

        where_clause = 'WHERE ' + ' AND '.join(conditions) if conditions else ''

        db = get_db()
        try:
            cur = db.cursor()

            # 查询总数
            cur.execute(f'SELECT COUNT(*) as total FROM dify_audit_logs {where_clause}', params)
            total = cur.fetchone()['total']

            # 查询数据
            cur.execute(f'''
                SELECT * FROM dify_audit_logs
                {where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            ''', params + [page_size, offset])
            logs = cur.fetchall()

            # 格式化输出
            items = []
            for log in logs:
                items.append({
                    'id': log['id'],
                    'user_id': log['user_id'],
                    'user_name': log['user_name'],
                    'user_email': log['user_email'],
                    'action': log['action'],
                    'resource_type': log['resource_type'],
                    'resource_id': log['resource_id'],
                    'resource_name': log['resource_name'],
                    'description': log['description'],
                    'ip_address': log['ip_address'],
                    'user_agent': log['user_agent'],
                    'request_method': log['request_method'],
                    'request_path': log['request_path'],
                    'response_code': log['response_code'],
                    'status': log['status'],
                    'error_message': log['error_message'],
                    'created_at': str(log['created_at']) if log['created_at'] else '',
                })

            return jsonify(code=200, data={
                'items': items,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size,
            })
        except Exception as e:
            return jsonify(code=500, msg=f'查询审计日志失败: {str(e)}')
        finally:
            db.close()

    @app.route('/api/audit/logs/<log_id>', methods=['GET'])
    def get_audit_log_detail(log_id):
        """查询单条审计日志详情"""
        _ensure_audit_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('SELECT * FROM dify_audit_logs WHERE id = %s', (log_id,))
            log = cur.fetchone()
            if not log:
                return jsonify(code=404, msg='日志不存在')

            return jsonify(code=200, data={
                'id': log['id'],
                'user_id': log['user_id'],
                'user_name': log['user_name'],
                'user_email': log['user_email'],
                'action': log['action'],
                'resource_type': log['resource_type'],
                'resource_id': log['resource_id'],
                'resource_name': log['resource_name'],
                'description': log['description'],
                'ip_address': log['ip_address'],
                'user_agent': log['user_agent'],
                'request_method': log['request_method'],
                'request_path': log['request_path'],
                'request_body': log['request_body'],
                'response_code': log['response_code'],
                'status': log['status'],
                'error_message': log['error_message'],
                'extra_data': log['extra_data'],
                'created_at': str(log['created_at']) if log['created_at'] else '',
            })
        except Exception as e:
            return jsonify(code=500, msg=f'查询日志详情失败: {str(e)}')
        finally:
            db.close()

    @app.route('/api/audit/stats', methods=['GET'])
    def get_audit_stats():
        """获取审计统计信息

        查询参数:
            days: 统计天数（默认 7）
        """
        _ensure_audit_table()
        days = min(90, max(1, request.args.get('days', 7, type=int)))

        db = get_db()
        try:
            cur = db.cursor()

            # 按操作类型统计
            cur.execute('''
                SELECT action, COUNT(*) as count
                FROM dify_audit_logs
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY action
                ORDER BY count DESC
                LIMIT 20
            ''', (days,))
            action_stats = [{'action': r['action'], 'count': r['count']} for r in cur.fetchall()]

            # 按日期统计
            cur.execute('''
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM dify_audit_logs
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            ''', (days,))
            date_stats = [{'date': str(r['date']), 'count': r['count']} for r in cur.fetchall()]

            # 按状态统计
            cur.execute('''
                SELECT status, COUNT(*) as count
                FROM dify_audit_logs
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY status
            ''', (days,))
            status_stats = {r['status']: r['count'] for r in cur.fetchall()}

            # 总操作数
            cur.execute('SELECT COUNT(*) as total FROM dify_audit_logs')
            total = cur.fetchone()['total']

            return jsonify(code=200, data={
                'total': total,
                'period_days': days,
                'action_stats': action_stats,
                'date_stats': date_stats,
                'status_stats': status_stats,
            })
        except Exception as e:
            return jsonify(code=500, msg=f'查询统计失败: {str(e)}')
        finally:
            db.close()

    @app.route('/api/audit/logs', methods=['DELETE'])
    def delete_audit_logs():
        """清理审计日志（保留最近 N 天）

        请求体:
            retain_days: 保留天数（默认 90，最少 7）
        """
        _ensure_audit_table()
        body = request.get_json(silent=True) or {}
        retain_days = max(7, min(365, int(body.get('retain_days', 90))))

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('''
                DELETE FROM dify_audit_logs
                WHERE created_at < DATE_SUB(NOW(), INTERVAL %s DAY)
            ''', (retain_days,))
            deleted = cur.rowcount
            db.commit()

            # 记录清理操作本身
            log_audit_event(
                action='cleanup_audit_logs',
                resource_type='audit',
                description=f'清理 {deleted} 条审计日志（保留最近 {retain_days} 天）',
                status='success',
            )

            return jsonify(code=200, msg=f'已清理 {deleted} 条日志', data={'deleted': deleted})
        except Exception as e:
            return jsonify(code=500, msg=f'清理失败: {str(e)}')
        finally:
            db.close()
