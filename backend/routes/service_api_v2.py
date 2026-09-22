# -*- coding: utf-8 -*-
"""
Service API v2 扩展 —— 对齐 Dify 1.17 完整端点
新增：站点配置、消息详情、节点执行详情、API 文档
"""
import json
import uuid
from flask import Blueprint, request, jsonify
from datetime import datetime

from config import get_db
from utils.auth import api_key_required, get_current_app

bp = Blueprint('service_api_v2', __name__)


# ============================================================
# 站点配置（嵌入聊天窗口用）
# ============================================================

@bp.route('/v1/site', methods=['GET'])
@api_key_required
def site_config():
    """
    获取站点配置（Dify: GET /v1/site）
    用于嵌入聊天窗口的前端初始化
    """
    app = get_current_app()
    if not app:
        return jsonify(code=401, msg='无效的 API Key')

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT * FROM dify_sites WHERE app_id = %s LIMIT 1', (app['id'],))
        site = cur.fetchone()

        features = {}
        try:
            cur.execute(r'SELECT features FROM dify_workflows WHERE app_id = %s ORDER BY created_at DESC LIMIT 1', (app['id'],))
            wf_row = cur.fetchone()
            if wf_row and wf_row['features']:
                features = json.loads(wf_row['features'] or '{}')
        except Exception:
            pass

        return jsonify(code=200, data={
            'title': (site and site['title']) or app.get('name', '熵舟应用'),
            'icon': (site and site['icon']) or app.get('icon', '🤖'),
            'icon_background': (site and site['icon_background']) or app.get('icon_background', '#FFEAD5'),
            'description': (site and site['description']) or (app.get('description') or ''),
            'default_language': (site and site['default_language']) or 'zh-Hans',
            'prompt_public': bool(site and site['prompt_public']),
            'show_workflow_steps': bool(site and site.get('show_workflow_steps', 1)),
            'custom_disclaimer': (site and site['custom_disclaimer']) or '',
            'opening_statement': features.get('opening_statement') or '',
            'suggested_questions': features.get('suggested_questions') or [],
            'file_upload': {
                'enabled': bool(features.get('file_upload', {}).get('enabled', False)),
                'allowed_file_types': features.get('file_upload', {}).get('allowed_file_types', []),
                'allowed_file_extensions': features.get('file_upload', {}).get('allowed_file_extensions', []),
                'number_limits': features.get('file_upload', {}).get('number_limits', 5),
                'file_size_limit': features.get('file_upload', {}).get('file_size_limit', 15),
            },
        })
    finally:
        db.close()


# ============================================================
# 单条消息详情
# ============================================================

@bp.route('/v1/messages/<message_id>', methods=['GET'])
@api_key_required
def get_message(message_id):
    """
    获取单条消息详情（Dify: GET /v1/messages/<id>）
    """
    app = get_current_app()
    if not app:
        return jsonify(code=401, msg='无效的 API Key')

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            r'''SELECT m.*, c.app_id as c_app_id
                FROM dify_messages m
                INNER JOIN dify_conversations c ON m.conversation_id = c.id
                WHERE m.id = %s AND c.app_id = %s''',
            (message_id, app['id'])
        )
        row = cur.fetchone()
        if not row:
            return jsonify(code=404, msg='消息不存在')

        # 获取反馈
        feedback = None
        cur.execute(
            r'SELECT rating FROM dify_message_feedbacks WHERE message_id = %s LIMIT 1',
            (message_id,)
        )
        fb_row = cur.fetchone()
        if fb_row:
            if fb_row['rating'] == 1:
                feedback = {'rating': 'like'}
            elif fb_row['rating'] == -1:
                feedback = {'rating': 'dislike'}

        meta = {}
        if row.get('metadata'):
            try:
                meta = json.loads(row['metadata'])
            except Exception:
                pass

        is_user = row.get('role') == 'user'
        return jsonify(code=200, data={
            'id': row['id'],
            'conversation_id': row['conversation_id'],
            'inputs': meta.get('inputs') or {},
            'query': meta.get('query') if is_user else '',
            'message': row['content'] if is_user else '',
            'answer': '' if is_user else (row['content'] or ''),
            'answer_tokens': 0 if is_user else (row['tokens'] or 0),
            'message_tokens': row['tokens'] or 0 if is_user else 0,
            'model_provider': row.get('model_provider') or '',
            'model_id': row.get('model_name') or '',
            'feedback': feedback,
            'created_at': _epoch_time(row.get('created_at')),
        })
    finally:
        db.close()


def _epoch_time(dt):
    """datetime -> epoch seconds"""
    if not dt:
        return 0
    try:
        if isinstance(dt, str):
            dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
        return int(dt.timestamp())
    except Exception:
        return 0


# ============================================================
# 工作流节点执行详情
# ============================================================

@bp.route('/v1/workflows/run/<run_id>/node-executions', methods=['GET'])
@api_key_required
def workflow_node_executions(run_id):
    """
    获取工作流运行的节点执行详情（Dify: GET /v1/workflows/run/<id>/node-executions）
    """
    app = get_current_app()
    if not app:
        return jsonify(code=401, msg='无效的 API Key')

    db = get_db()
    try:
        cur = db.cursor()
        # 验证运行记录属于当前应用
        cur.execute(r'SELECT id FROM dify_workflow_runs WHERE id = %s AND app_id = %s', (run_id, app['id']))
        if not cur.fetchone():
            return jsonify(code=404, msg='运行记录不存在')

        cur.execute(
            r'''SELECT * FROM dify_workflow_node_executions
                WHERE workflow_run_id = %s
                ORDER BY created_at ASC''',
            (run_id,)
        )
        items = []
        for r in cur.fetchall():
            items.append({
                'id': r['id'],
                'node_id': r['node_id'],
                'node_type': r['node_type'] or '',
                'title': r['title'] or '',
                'inputs': json.loads(r['inputs'] or '{}'),
                'outputs': json.loads(r['outputs'] or '{}'),
                'status': r['status'] or '',
                'error': r['error'] or '',
                'elapsed_time': r['elapsed_time'] or 0,
                'created_at': _epoch_time(r.get('created_at')),
                'finished_at': _epoch_time(r.get('finished_at')),
            })

        return jsonify(code=200, data={'items': items})
    finally:
        db.close()


# ============================================================
# 工作流式运行进度（SSE 替代轮询）
# ============================================================

@bp.route('/v1/workflows/run/<run_id>/stream', methods=['GET'])
@api_key_required
def workflow_run_stream(run_id):
    """
    工作流运行流式进度（Dify: GET /v1/workflows/run/<id>/stream）
    SSE 推送节点执行进度
    """
    app = get_current_app()
    if not app:
        return jsonify(code=401, msg='无效的 API Key')

    def generate():
        import time
        last_count = 0
        max_wait = 120  # 最多等 2 分钟
        start = time.time()

        while time.time() - start < max_wait:
            db = get_db()
            try:
                cur = db.cursor()
                # 检查运行状态
                cur.execute(r'SELECT status FROM dify_workflow_runs WHERE id = %s AND app_id = %s', (run_id, app['id']))
                run = cur.fetchone()
                if not run:
                    yield f'event: error\ndata: {json.dumps({"message": "运行记录不存在"})}\n\n'
                    break

                # 获取最新节点执行
                cur.execute(
                    r'''SELECT * FROM dify_workflow_node_executions
                        WHERE workflow_run_id = %s
                        ORDER BY created_at DESC LIMIT 100''',
                    (run_id,)
                )
                nodes = cur.fetchall()
                if len(nodes) > last_count:
                    new_nodes = nodes[:len(nodes) - last_count] if last_count > 0 else nodes
                    for n in reversed(new_nodes):
                        yield f'event: node\ndata: {json.dumps({
                            "node_id": n['node_id'],
                            "node_type": n['node_type'],
                            "status": n['status'],
                            "error": n['error'] or '',
                        }, ensure_ascii=False)}\n\n'
                    last_count = len(nodes)

                if run['status'] in ('succeeded', 'failed', 'error', 'stopped'):
                    # 发送完成事件
                    cur.execute(r'SELECT * FROM dify_workflow_runs WHERE id = %s', (run_id,))
                    final = cur.fetchone()
                    yield f'event: finished\ndata: {json.dumps({
                        "status": final['status'],
                        "outputs": json.loads(final['outputs'] or '{}'),
                        "error": final['error'] or '',
                        "elapsed_time": final['elapsed_time'] or 0,
                    }, ensure_ascii=False)}\n\n'
                    break
            finally:
                db.close()

            time.sleep(1)

        yield f'event: timeout\ndata: {json.dumps({"message": "连接超时"})}\n\n'

    from flask import Response
    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
    })


# ============================================================
# API 文档（OpenAPI 子集）
# ============================================================

@bp.route('/v1/api-docs', methods=['GET'])
def api_docs():
    """
    获取 API 文档（OpenAPI 3.0 子集）
    用于开发者自助查阅
    """
    docs = {
        'openapi': '3.0.0',
        'info': {
            'title': '熵舟 Service API',
            'version': '1.0.0',
            'description': '熵舟·智能体工作台开发者 API，对齐 Dify 1.17 规范',
        },
        'servers': [{'url': '/v1'}],
        'paths': {
            '/info': {'get': {'summary': '应用信息', 'tags': ['应用']}},
            '/parameters': {'get': {'summary': '应用参数', 'tags': ['应用']}},
            '/site': {'get': {'summary': '站点配置', 'tags': ['应用']}},
            '/chat-messages': {'post': {'summary': '发送聊天消息', 'tags': ['对话']}},
            '/chat-messages/{task_id}/stop': {'post': {'summary': '停止生成', 'tags': ['对话']}},
            '/completion-messages': {'post': {'summary': '补全消息', 'tags': ['对话']}},
            '/messages': {'get': {'summary': '消息列表', 'tags': ['消息']}},
            '/messages/{id}': {'get': {'summary': '消息详情', 'tags': ['消息']}},
            '/messages/{id}/feedbacks': {'post': {'summary': '消息反馈', 'tags': ['消息']}},
            '/messages/{id}/suggested-questions': {'get': {'summary': '建议问题', 'tags': ['消息']}},
            '/conversations': {'get': {'summary': '会话列表', 'tags': ['会话']}},
            '/conversations/{id}': {'delete': {'summary': '删除会话', 'tags': ['会话']}},
            '/conversations/{id}/name': {'post': {'summary': '重命名会话', 'tags': ['会话']}},
            '/workflows/run': {'post': {'summary': '运行工作流', 'tags': ['工作流']}},
            '/workflows/run/{id}': {'get': {'summary': '工作流状态', 'tags': ['工作流']}},
            '/workflows/{id}/stop': {'post': {'summary': '停止工作流', 'tags': ['工作流']}},
            '/workflows/run/{id}/node-executions': {'get': {'summary': '节点执行详情', 'tags': ['工作流']}},
            '/workflows/run/{id}/stream': {'get': {'summary': '流式进度', 'tags': ['工作流']}},
            '/workflows/logs': {'get': {'summary': '工作流日志', 'tags': ['工作流']}},
            '/files/upload': {'post': {'summary': '文件上传', 'tags': ['文件']}},
            '/files/{id}': {'get': {'summary': '文件下载', 'tags': ['文件']}},
            '/audio-to-text': {'post': {'summary': '语音转文本', 'tags': ['音频']}},
            '/text-to-audio': {'post': {'summary': '文本转语音', 'tags': ['音频']}},
            '/meta': {'get': {'summary': '工具元数据', 'tags': ['工具']}},
        }
    }
    return jsonify(code=200, data=docs)


# ============================================================
# 健康检查
# ============================================================

@bp.route('/v1/health', methods=['GET'])
def health_check():
    """API 健康检查"""
    db_ok = False
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute(r'SELECT 1')
        db.close()
        db_ok = True
    except Exception:
        pass

    return jsonify(code=200, data={
        'status': 'ok' if db_ok else 'degraded',
        'database': 'connected' if db_ok else 'disconnected',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat(),
    })


# ============================================================
# 注册路由
# ============================================================

def register_service_api_v2_routes(app):
    """注册 Service API v2 路由"""
    app.register_blueprint(bp)
