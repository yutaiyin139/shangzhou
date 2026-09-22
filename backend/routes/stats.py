# -*- coding: utf-8 -*-
"""统计数据路由（首页仪表板）"""

from datetime import datetime, timedelta
from flask import jsonify, request
from config import get_db


def register_stats_routes(app):
    """注册统计相关路由"""

    @app.route('/api/stats/overview', methods=['GET'])
    def get_overview_stats():
        """获取首页概览统计数据"""
        tenant_id = request.args.get('tenant_id', 'default')
        db = get_db()
        try:
            cur = db.cursor()

            # 应用数量
            cur.execute(r'SELECT COUNT(*) as cnt FROM dify_apps WHERE status = "normal"')
            app_count = cur.fetchone()['cnt']

            # 知识库数量
            cur.execute(r'SELECT COUNT(*) as cnt FROM dify_datasets')
            dataset_count = cur.fetchone()['cnt']

            # 文档数量
            cur.execute(r'SELECT COUNT(*) as cnt FROM dify_documents WHERE enabled = 1')
            document_count = cur.fetchone()['cnt']

            # 会话数量
            cur.execute(r'SELECT COUNT(*) as cnt FROM dify_conversations WHERE status = "active"')
            conversation_count = cur.fetchone()['cnt']

            # 消息数量
            cur.execute(r'SELECT COUNT(*) as cnt FROM dify_messages')
            message_count = cur.fetchone()['cnt']

            # 工作流数量
            cur.execute(r'SELECT COUNT(*) as cnt FROM dify_workflows')
            workflow_count = cur.fetchone()['cnt']

            # 工作流运行次数
            cur.execute(r'SELECT COUNT(*) as cnt FROM dify_workflow_runs')
            workflow_run_count = cur.fetchone()['cnt']

            # 工具数量
            cur.execute(r'SELECT COUNT(*) as cnt FROM dify_tool_providers')
            tool_count = cur.fetchone()['cnt']

            # 用户数量
            cur.execute(r'SELECT COUNT(*) as cnt FROM dify_accounts WHERE status = "active"')
            user_count = cur.fetchone()['cnt']

            # Token 消耗总量
            cur.execute(r'SELECT COALESCE(SUM(total_tokens), 0) as total FROM dify_conversations')
            total_tokens = cur.fetchone()['total']

            return jsonify(code=200, data={
                'apps': app_count,
                'datasets': dataset_count,
                'documents': document_count,
                'conversations': conversation_count,
                'messages': message_count,
                'workflows': workflow_count,
                'workflow_runs': workflow_run_count,
                'tools': tool_count,
                'users': user_count,
                'total_tokens': int(total_tokens or 0),
            })
        finally:
            db.close()

    @app.route('/api/stats/activity', methods=['GET'])
    def get_activity_stats():
        """获取最近活动数据（图表用）"""
        tenant_id = request.args.get('tenant_id', 'default')
        days = min(int(request.args.get('days', 7)), 30)
        db = get_db()
        try:
            cur = db.cursor()

            # 最近 N 天的会话数
            cur.execute(r'''
                SELECT DATE(created_at) AS date, COUNT(*) AS count
                FROM dify_conversations
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            ''', (days,))
            conversation_trend = []
            for r in cur.fetchall():
                conversation_trend.append({
                    'date': str(r['date']),
                    'count': int(r['count']),
                })

            # 最近 N 天的消息数
            cur.execute(r'''
                SELECT DATE(created_at) AS date, COUNT(*) AS count
                FROM dify_messages
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            ''', (days,))
            message_trend = []
            for r in cur.fetchall():
                message_trend.append({
                    'date': str(r['date']),
                    'count': int(r['count']),
                })

            # 最近 N 天的工作流运行数
            cur.execute(r'''
                SELECT DATE(created_at) AS date, COUNT(*) AS count
                FROM dify_workflow_runs
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            ''', (days,))
            workflow_trend = []
            for r in cur.fetchall():
                workflow_trend.append({
                    'date': str(r['date']),
                    'count': int(r['count']),
                })

            # 最近 N 天的 Token 消耗
            cur.execute(r'''
                SELECT DATE(created_at) AS date, COALESCE(SUM(tokens), 0) AS tokens
                FROM dify_messages
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            ''', (days,))
            token_trend = []
            for r in cur.fetchall():
                token_trend.append({
                    'date': str(r['date']),
                    'tokens': int(r['tokens']),
                })

            return jsonify(code=200, data={
                'conversation_trend': conversation_trend,
                'message_trend': message_trend,
                'workflow_trend': workflow_trend,
                'token_trend': token_trend,
                'days': days,
            })
        finally:
            db.close()

    @app.route('/api/stats/recent', methods=['GET'])
    def get_recent_activity():
        """获取最近活动列表"""
        tenant_id = request.args.get('tenant_id', 'default')
        limit = min(int(request.args.get('limit', 10)), 50)
        db = get_db()
        try:
            cur = db.cursor()

            # 最近会话
            cur.execute(r'''
                SELECT c.id, c.title, c.message_count, c.total_tokens, c.created_at, c.app_id, a.name AS app_name
                FROM dify_conversations c
                LEFT JOIN dify_apps a ON a.id = c.app_id
                ORDER BY c.created_at DESC
                LIMIT %s
            ''', (limit,))
            recent_conversations = []
            for r in cur.fetchall():
                recent_conversations.append({
                    'id': r['id'],
                    'title': r['title'],
                    'message_count': r['message_count'],
                    'total_tokens': r['total_tokens'],
                    'app_name': r['app_name'],
                    'created_at': str(r['created_at']),
                })

            # 最近工作流运行
            cur.execute(r'''
                SELECT w.id, w.status, w.created_at, w.elapsed_time, w.total_tokens, a.name AS app_name
                FROM dify_workflow_runs w
                LEFT JOIN dify_apps a ON a.id = w.app_id
                ORDER BY w.created_at DESC
                LIMIT %s
            ''', (limit,))
            recent_workflows = []
            for r in cur.fetchall():
                recent_workflows.append({
                    'id': r['id'],
                    'status': r['status'],
                    'app_name': r['app_name'],
                    'elapsed_time': r['elapsed_time'],
                    'total_tokens': r['total_tokens'],
                    'created_at': str(r['created_at']),
                })

            # 最近上传的文档
            cur.execute(r'''
                SELECT d.id, d.name, d.indexing_status, d.word_count, d.created_at, ds.name AS dataset_name
                FROM dify_documents d
                LEFT JOIN dify_datasets ds ON ds.id = d.dataset_id
                ORDER BY d.created_at DESC
                LIMIT %s
            ''', (limit,))
            recent_documents = []
            for r in cur.fetchall():
                recent_documents.append({
                    'id': r['id'],
                    'name': r['name'],
                    'indexing_status': r['indexing_status'],
                    'word_count': r['word_count'],
                    'dataset_name': r['dataset_name'],
                    'created_at': str(r['created_at']),
                })

            return jsonify(code=200, data={
                'recent_conversations': recent_conversations,
                'recent_workflows': recent_workflows,
                'recent_documents': recent_documents,
            })
        finally:
            db.close()

    @app.route('/api/stats/models', methods=['GET'])
    def get_model_stats():
        """获取模型使用统计"""
        tenant_id = request.args.get('tenant_id', 'default')
        db = get_db()
        try:
            cur = db.cursor()

            # 按模型统计消息数和 Token
            cur.execute(r'''
                SELECT model_name, model_provider,
                       COUNT(*) AS message_count,
                       COALESCE(SUM(tokens), 0) AS total_tokens
                FROM dify_messages
                WHERE model_name != ''
                GROUP BY model_name, model_provider
                ORDER BY message_count DESC
            ''')
            model_stats = []
            for r in cur.fetchall():
                model_stats.append({
                    'model_name': r['model_name'],
                    'model_provider': r['model_provider'],
                    'message_count': int(r['message_count']),
                    'total_tokens': int(r['total_tokens']),
                })

            return jsonify(code=200, data=model_stats)
        finally:
            db.close()

    @app.route('/api/stats/workflows', methods=['GET'])
    def get_workflow_stats():
        """获取工作流运行统计"""
        tenant_id = request.args.get('tenant_id', 'default')
        db = get_db()
        try:
            cur = db.cursor()

            # 工作流运行状态分布
            cur.execute(r'''
                SELECT status, COUNT(*) AS count
                FROM dify_workflow_runs
                GROUP BY status
            ''')
            status_dist = {}
            for r in cur.fetchall():
                status_dist[r['status']] = int(r['count'])

            # 平均运行时间和 Token
            cur.execute(r'''
                SELECT
                    COALESCE(AVG(elapsed_time), 0) AS avg_elapsed,
                    COALESCE(AVG(total_tokens), 0) AS avg_tokens,
                    COALESCE(MAX(elapsed_time), 0) AS max_elapsed,
                    COUNT(*) AS total_runs
                FROM dify_workflow_runs
                WHERE status = 'succeeded'
            ''')
            perf = cur.fetchone()

            return jsonify(code=200, data={
                'status_distribution': status_dist,
                'avg_elapsed_time': round(float(perf['avg_elapsed']), 2),
                'avg_tokens': round(float(perf['avg_tokens']), 0),
                'max_elapsed_time': round(float(perf['max_elapsed']), 2),
                'total_runs': int(perf['total_runs']),
            })
        finally:
            db.close()
