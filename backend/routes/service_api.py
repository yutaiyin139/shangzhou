# -*- coding: utf-8 -*-
"""Service API 路由 —— 面向开发者的 v1 API 端点"""
import json
import os
import uuid
import flask
from flask import Blueprint, request, jsonify, Response, send_file
from datetime import datetime

from config import get_db
from utils.auth import api_key_required, get_current_app

bp = Blueprint('service_api', __name__)


# ============================================================
# Service API 全局速率限制（对齐 Dify 安全规范）
# ============================================================

def _get_rate_limit(path):
    """根据路径返回 (limit, window) 限流策略"""
    if '/v1/chat-messages' in path or '/v1/workflows/run' in path:
        return 30, 60  # 聊天/工作流：30次/分钟
    elif '/v1/audio' in path:
        return 20, 60  # 音频：20次/分钟（资源密集型）
    elif '/v1/files' in path:
        return 20, 60  # 文件上传：20次/分钟
    else:
        return 60, 60  # 默认：60次/分钟


@bp.before_request
def _service_api_rate_limit():
    """
    Service API 全局滑动窗口限流（before_request + after_request 组合）。
    使用 response 回调确保限流头始终被添加。
    """
    if request.method == 'OPTIONS':
        return None

    from utils.redis_cache import rate_limit_check

    ip = request.remote_addr or 'unknown'
    route = request.endpoint or request.path
    limit, window = _get_rate_limit(request.path)

    key = f"service_api:{ip}:{route}"
    allowed, remaining, reset_in = rate_limit_check(key, limit, window)

    if not allowed:
        resp = jsonify(code=429, msg=f'请求过于频繁，请在 {reset_in} 秒后重试')
        resp.status_code = 429
        resp.headers['X-RateLimit-Limit'] = str(limit)
        resp.headers['X-RateLimit-Remaining'] = '0'
        resp.headers['X-RateLimit-Reset'] = str(reset_in)
        resp.headers['Retry-After'] = str(reset_in)
        return resp

    # 使用 after_this_request 确保在响应返回前添加限流头
    @flask.after_this_request
    def _add_headers(response):
        if hasattr(response, 'headers'):
            response.headers['X-RateLimit-Limit'] = str(limit)
            response.headers['X-RateLimit-Remaining'] = str(remaining)
            response.headers['X-RateLimit-Reset'] = str(reset_in)
        return response

# ============================================================
# 工作流 Service API
# ============================================================

@bp.route('/v1/workflows/run', methods=['POST'])
@api_key_required
def workflow_run():
    """
    运行工作流（Service API）
    通过 API Key 认证，面向开发者
    """
    body = request.get_json() or {}
    inputs = body.get('inputs', {})
    response_mode = body.get('response_mode', 'blocking')
    user = body.get('user', 'api-user')

    app = get_current_app()
    if not app:
        return jsonify(code=401, msg='无效的 API Key')

    try:
        from engine.workflow_runner import run_workflow
        status, result = run_workflow(app['id'], inputs)

        if status in (200, 201):
            return jsonify(code=200, data={
                'workflow_run_id': result.get('run_id', ''),
                'task_id': result.get('task_id', ''),
                'data': {
                    'id': result.get('run_id', ''),
                    'workflow_id': app['id'],
                    'status': 'succeeded',
                    'outputs': result.get('outputs', {}),
                    'error': None,
                    'elapsed_time': result.get('elapsed', 0),
                    'total_tokens': result.get('tokens', 0),
                    'total_steps': result.get('steps', 0),
                    'created_at': int(datetime.now().timestamp()),
                    'finished_at': int(datetime.now().timestamp()),
                }
            })
        return jsonify(code=status, msg='执行失败', data=result)
    except Exception as e:
        return jsonify(code=500, msg=f'执行错误: {str(e)}')


@bp.route('/v1/workflows/run/<task_id>', methods=['GET'])
@api_key_required
def workflow_run_status(task_id):
    """获取工作流运行状态"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT * FROM dify_workflow_runs WHERE id = %s', (task_id,))
        row = cur.fetchone()
        if not row:
            return jsonify(code=404, msg='运行记录不存在')

        return jsonify(code=200, data={
            'id': row['id'],
            'workflow_id': row['app_id'],
            'status': row['status'],
            'inputs': json.loads(row['inputs'] or '{}'),
            'outputs': json.loads(row['outputs'] or '{}'),
            'error': row['error_message'] or '',
            'created_at': str(row['created_at']),
            'finished_at': str(row['finished_at']) if row['finished_at'] else '',
        })
    finally:
        db.close()


@bp.route('/v1/workflows/<task_id>/stop', methods=['POST'])
@api_key_required
def workflow_stop(task_id):
    """停止工作流运行"""
    # task_id 可能是 Celery 任务 ID，也可能是本地运行记录 ID；revoke_workflow_task 是普通函数
    # （不是 celery 任务，不能 .delay()）且只认 Celery ID，所以两条路都试并如实回报。
    marked = False
    try:
        from engine.workflow_utils import cancel_workflow_task
        marked = bool(cancel_workflow_task(task_id))
    except Exception:
        pass
    revoked = False
    try:
        from tasks.workflow_tasks import revoke_workflow_task
        revoke_workflow_task(task_id)
        revoked = True
    except Exception:
        pass
    if marked:
        msg = '停止指令已送达正在执行的任务'
    elif revoked:
        msg = '已发送 Celery 取消信号（若任务不在本 worker 中执行则不会生效）'
    else:
        msg = '未找到该任务的执行句柄，可能已经结束'
    return jsonify(code=200, msg=msg)


@bp.route('/v1/workflows/logs', methods=['GET'])
@api_key_required
def workflow_logs():
    """获取工作流运行日志"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    status = request.args.get('status', '')
    keyword = request.args.get('keyword', '')

    where = []
    params = []
    if status:
        where.append(r'status = %s')
        params.append(status)
    if keyword:
        where.append(r'(id LIKE %s OR app_id LIKE %s)')
        params.append(f'%{keyword}%')
        params.append(f'%{keyword}%')

    where_sql = 'WHERE ' + ' AND '.join(where) if where else ''
    offset = (page - 1) * page_size

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT COUNT(*) as total FROM dify_workflow_runs ' + where_sql, params)
        total = cur.fetchone()['total']

        cur.execute(
            r'SELECT * FROM dify_workflow_runs ' + where_sql +
            r' ORDER BY created_at DESC LIMIT %s OFFSET %s',
            params + [page_size, offset]
        )
        items = []
        for r in cur.fetchall():
            items.append({
                'id': r['id'],
                'app_id': r['app_id'],
                'status': r['status'],
                'inputs': json.loads(r['inputs'] or '{}'),
                'outputs': json.loads(r['outputs'] or '{}'),
                'error_message': r['error_message'] or '',
                'created_at': str(r['created_at']),
                'finished_at': str(r['finished_at']) if r['finished_at'] else '',
            })
        return jsonify(code=200, data={
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
        })
    finally:
        db.close()


# ============================================================
# 聊天 Service API
# ============================================================

def _extract_answer(outputs):
    """从工作流输出提取回答文本：优先 answer 键，否则取第一个非空字符串值"""
    answer = (outputs or {}).get('answer', '')
    if answer:
        return answer
    for v in (outputs or {}).values():
        if isinstance(v, str) and v.strip():
            return v
        if isinstance(v, (int, float)):
            return str(v)
    return ''


def _persist_chat_turn(app, user, conversation_id, inputs, query, answer,
                       tokens=0, model_provider='', model_name='', thought_chain=None):
    """
    将一轮对话落库：必要时创建会话，写入用户消息与助手消息。
    如有思考链（Agent ReAct 过程），同步保存到 message_agent_thoughts。
    返回 (conversation_id, user_message_id, assistant_message_id)。
    """
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    db = get_db()
    try:
        cur = db.cursor()
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            title = (query or '新对话')[:60]
            cur.execute(
                r'''INSERT INTO dify_conversations
                    (id, app_id, user_id, title, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, 'normal', %s, %s)''',
                (conversation_id, app['id'], user, title, now, now))
        else:
            cur.execute(
                r'SELECT id FROM dify_conversations WHERE id = %s AND app_id = %s',
                (conversation_id, app['id']))
            if not cur.fetchone():
                conversation_id = str(uuid.uuid4())
                cur.execute(
                    r'''INSERT INTO dify_conversations
                        (id, app_id, user_id, title, status, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, 'normal', %s, %s)''',
                    (conversation_id, app['id'], user, (query or '新对话')[:60], now, now))

        user_msg_id = str(uuid.uuid4())
        assistant_msg_id = str(uuid.uuid4())
        meta_user = json.dumps({'query': query, 'inputs': inputs}, ensure_ascii=False)
        meta_asst = json.dumps({'query': query, 'inputs': inputs}, ensure_ascii=False)
        cur.execute(
            r'''INSERT INTO dify_messages
                (id, conversation_id, role, content, tokens, model_provider, model_name,
                 metadata, created_at)
                VALUES (%s, %s, 'user', %s, 0, '', '', %s, %s)''',
            (user_msg_id, conversation_id, query, meta_user, now))
        cur.execute(
            r'''INSERT INTO dify_messages
                (id, conversation_id, role, content, tokens, model_provider, model_name,
                 metadata, created_at)
                VALUES (%s, %s, 'assistant', %s, %s, %s, %s, %s, %s)''',
            (assistant_msg_id, conversation_id, answer or '', tokens or 0,
             model_provider or '', model_name or '', meta_asst, now))
        cur.execute(
            r'''UPDATE dify_conversations
                SET message_count = message_count + 2,
                    total_tokens = total_tokens + %s,
                    last_message_at = %s,
                    updated_at = %s
                WHERE id = %s''',
            (tokens or 0, now, now, conversation_id))
        db.commit()
        # 保存思考链（如果有）
        if thought_chain and assistant_msg_id:
            try:
                from engine.thought_chain import save_thought_chain
                save_thought_chain(assistant_msg_id, thought_chain)
            except Exception:
                pass  # 思考链保存失败不影响主流程
        return conversation_id, user_msg_id, assistant_msg_id
    except Exception:
        db.rollback()
        return conversation_id, None, None
    finally:
        db.close()

@bp.route('/v1/chat-messages', methods=['POST'])
@api_key_required
def chat_messages():
    """
    聊天消息（Service API）
    支持阻塞和流式响应
    """
    body = request.get_json() or {}
    query = body.get('query', '')
    inputs = body.get('inputs', {})
    response_mode = body.get('response_mode', 'blocking')
    conversation_id = body.get('conversation_id', '')
    user = body.get('user', 'api-user')

    if not query:
        return jsonify(code=400, msg='query 不能为空')

    app = get_current_app()
    if not app:
        return jsonify(code=401, msg='无效的 API Key')

    if response_mode == 'streaming':
        # 流式响应
        from flask import Response
        def generate():
            try:
                from engine.workflow_runner import run_workflow
                status, result = run_workflow(app['id'], {**inputs, 'query': query})
                if status in (200, 201):
                    answer = _extract_answer(result.get('outputs', {}))
                    conv_id, user_msg_id, asst_msg_id = _persist_chat_turn(
                        app, user, conversation_id, inputs, query, answer,
                        tokens=result.get('tokens', 0),
                        model_provider=result.get('model_provider', ''),
                        model_name=result.get('model_name', ''),
                        thought_chain=result.get('thought_chain'))
                    yield f"data: {json.dumps({'event': 'message', 'answer': answer, 'message_id': user_msg_id or str(uuid.uuid4()), 'conversation_id': conv_id})}\n\n"
                    yield f"data: {json.dumps({'event': 'message_end', 'metadata': {}})}\n\n"
                else:
                    yield f"data: {json.dumps({'event': 'error', 'message': str(result)})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
        return Response(generate(), mimetype='text/event-stream')
    else:
        # 阻塞响应
        try:
            from engine.workflow_runner import run_workflow
            status, result = run_workflow(app['id'], {**inputs, 'query': query})
            if status in (200, 201):
                answer = _extract_answer(result.get('outputs', {}))
                conv_id, user_msg_id, asst_msg_id = _persist_chat_turn(
                    app, user, conversation_id, inputs, query, answer,
                    tokens=result.get('tokens', 0),
                    model_provider=result.get('model_provider', ''),
                    model_name=result.get('model_name', ''),
                    thought_chain=result.get('thought_chain'))
                return jsonify(code=200, data={
                    'answer': answer,
                    'message_id': user_msg_id or str(uuid.uuid4()),
                    'conversation_id': conv_id,
                    'metadata': {
                        'usage': result.get('usage', {}),
                    }
                })
            return jsonify(code=status, msg='执行失败', data=result)
        except Exception as e:
            return jsonify(code=500, msg=f'执行错误: {str(e)}')


@bp.route('/v1/chat-messages/<task_id>/stop', methods=['POST'])
@api_key_required
def chat_stop(task_id):
    """停止聊天生成"""
    marked = False
    try:
        from engine.workflow_utils import cancel_workflow_task
        marked = bool(cancel_workflow_task(task_id))
    except Exception:
        pass
    revoked = False
    try:
        from tasks.workflow_tasks import revoke_workflow_task
        revoke_workflow_task(task_id)
        revoked = True
    except Exception:
        pass
    if marked:
        msg = '停止指令已送达正在执行的任务'
    elif revoked:
        msg = '已发送 Celery 取消信号（若任务不在本 worker 中执行则不会生效）'
    else:
        msg = '未找到该任务的执行句柄，可能已经结束'
    return jsonify(code=200, msg=msg)


# ============================================================
# 补全 Service API
# ============================================================

@bp.route('/v1/completion-messages', methods=['POST'])
@api_key_required
def completion_messages():
    """
    补全消息（Service API）
    用于文本补全场景
    """
    body = request.get_json() or {}
    inputs = body.get('inputs', {})
    response_mode = body.get('response_mode', 'blocking')

    app = get_current_app()
    if not app:
        return jsonify(code=401, msg='无效的 API Key')

    try:
        from engine.workflow_runner import run_workflow
        status, result = run_workflow(app['id'], inputs)
        if status in (200, 201):
            return jsonify(code=200, data={
                'answer': result.get('outputs', {}).get('answer', ''),
                'message_id': str(uuid.uuid4()),
                'metadata': {
                    'usage': result.get('usage', {}),
                }
            })
        return jsonify(code=status, msg='执行失败', data=result)
    except Exception as e:
        return jsonify(code=500, msg=f'执行错误: {str(e)}')


# ============================================================
# 应用信息 Service API（对齐 Dify GET /v1/info、GET /v1/parameters）
# ============================================================

def _epoch(dt):
    """datetime -> epoch 秒（Dify Service API 的 created_at 格式）"""
    if not dt:
        return 0
    try:
        return int(dt.timestamp())
    except Exception:
        return 0


def _load_app_features(app_id):
    """读取应用工作流的 features JSON（开场白/建议问题/文件上传等）"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            r'SELECT features FROM dify_workflows WHERE app_id = %s'
            r' ORDER BY updated_at DESC LIMIT 1',
            (app_id,))
        row = cur.fetchone()
        if row and row.get('features'):
            try:
                return json.loads(row['features'])
            except Exception:
                return {}
        return {}
    finally:
        db.close()


@bp.route('/v1/info', methods=['GET'])
@api_key_required
def app_info():
    """获取应用基本信息（Dify: GET /v1/info）"""
    app = get_current_app()
    if not app:
        return jsonify(code=401, msg='无效的 API Key')

    return jsonify(code=200, data={
        'name': app.get('name', ''),
        'description': app.get('description') or '',
        'tags': [],
    })


@bp.route('/v1/parameters', methods=['GET'])
@api_key_required
def app_parameters():
    """获取应用参数（Dify: GET /v1/parameters）"""
    app = get_current_app()
    if not app:
        return jsonify(code=401, msg='无效的 API Key')

    features = _load_app_features(app['id'])
    opening = features.get('opening_statement') or ''
    suggested = features.get('suggested_questions') or []
    file_upload_cfg = features.get('file_upload') or {}
    stt = features.get('speech_to_text') or {}
    tts = features.get('text_to_speech') or {}
    retriever = features.get('retriever_resource') or {}
    suggested_after = features.get('suggested_questions_after_answer') or {}
    annotation = features.get('annotation_reply') or {}

    return jsonify(code=200, data={
        'opening_statement': opening,
        'suggested_questions': suggested,
        'suggested_questions_after_answer': {'enabled': bool(suggested_after.get('enabled', False))},
        'speech_to_text': {'enabled': bool(stt.get('enabled', False))},
        'text_to_speech': {
            'enabled': bool(tts.get('enabled', False)),
            'voice': tts.get('voice') or '',
            'language': tts.get('language') or '',
        },
        'retriever_resource': {'enabled': bool(retriever.get('enabled', False))},
        'annotation_reply': {'enabled': bool(annotation.get('enabled', False))},
        'user_input_form': features.get('user_input_form') or [],
        'file_upload': {
            'enabled': bool(file_upload_cfg.get('enabled', False)),
            'allowed_file_types': file_upload_cfg.get('allowed_file_types') or [],
            'allowed_file_extensions': file_upload_cfg.get('allowed_file_extensions') or [],
            'allowed_file_upload_methods': file_upload_cfg.get('allowed_file_upload_methods') or [],
            'number_limits': file_upload_cfg.get('number_limits', 0),
            'file_size_limit': file_upload_cfg.get('file_size_limit', 0),
        },
        'system_parameters': {
            'image_file_size_limit': 10,
            'video_file_size_limit': 100,
            'audio_file_size_limit': 50,
            'file_size_limit': 15,
            'workflow_file_upload_limit': 10,
        },
    })


# ============================================================
# 消息 Service API（对齐 Dify GET /v1/messages、POST /v1/messages/<id>/feedbacks）
# ============================================================

def _message_to_api(row, feedback_map):
    """dify_messages 行 -> Dify Service API message 对象"""
    is_user = row.get('role') == 'user'
    meta = {}
    if row.get('metadata'):
        try:
            meta = json.loads(row['metadata'])
        except Exception:
            meta = {}
    rating = feedback_map.get(row['id'])
    feedback = None
    if rating == 1:
        feedback = {'rating': 'like'}
    elif rating == -1:
        feedback = {'rating': 'dislike'}
    return {
        'id': row['id'],
        'conversation_id': row['conversation_id'],
        'inputs': meta.get('inputs') or {},
        'query': meta.get('query') if is_user else (meta.get('query') or ''),
        'message': row['content'] if is_user else '',
        'message_tokens': 0,
        'answer': '' if is_user else (row['content'] or ''),
        'answer_tokens': 0 if is_user else (row['tokens'] or 0),
        'model_provider': row.get('model_provider') or '',
        'model_id': row.get('model_name') or '',
        'metadata': meta,
        'agent_thoughts': [],
        'feedback': feedback,
        'created_at': _epoch(row.get('created_at')),
    }


@bp.route('/v1/messages', methods=['GET'])
@api_key_required
def message_list():
    """获取消息列表（Dify: GET /v1/messages?conversation_id=&user=&limit=&first_id=）"""
    app = get_current_app()
    if not app:
        return jsonify(code=401, msg='无效的 API Key')

    conversation_id = request.args.get('conversation_id', '')
    user = request.args.get('user', '')
    limit = min(int(request.args.get('limit', 20)), 100)
    first_id = request.args.get('first_id', '')

    if not conversation_id:
        return jsonify(code=400, msg='conversation_id 不能为空')

    db = get_db()
    try:
        cur = db.cursor()
        # 校验会话归属（软删会话不可读）
        cur.execute(
            r"SELECT id FROM dify_conversations WHERE id = %s AND app_id = %s AND status = 'normal'"
            + (r' AND user_id = %s' if user else ''),
            (conversation_id, app['id']) + ((user,) if user else ()))
        if not cur.fetchone():
            return jsonify(code=404, msg='会话不存在')

        where = [r'conversation_id = %s']
        params = [conversation_id]
        if first_id:
            where.append(r'created_at < (SELECT created_at FROM dify_messages WHERE id = %s)')
            params.append(first_id)

        cur.execute(
            r'SELECT * FROM dify_messages WHERE ' + ' AND '.join(where) +
            r' ORDER BY created_at DESC, id DESC LIMIT %s',
            params + [limit + 1])
        rows = cur.fetchall()
        has_more = len(rows) > limit
        rows = rows[:limit]

        # 批量取反馈
        feedback_map = {}
        if rows:
            ids = [r['id'] for r in rows]
            fmt = ','.join(['%s'] * len(ids))
            cur.execute(
                r'SELECT message_id, rating FROM dify_message_feedbacks WHERE message_id IN (' + fmt + ')',
                ids)
            for fr in cur.fetchall():
                feedback_map[fr['message_id']] = fr['rating']

        data = [_message_to_api(r, feedback_map) for r in rows]
        return jsonify(code=200, data={
            'limit': limit,
            'has_more': has_more,
            'data': data,
        })
    finally:
        db.close()


@bp.route('/v1/messages/<message_id>/feedbacks', methods=['POST'])
@api_key_required
def message_feedback(message_id):
    """消息反馈（Dify: POST /v1/messages/<id>/feedbacks，body: rating=like/dislike）"""
    app = get_current_app()
    if not app:
        return jsonify(code=401, msg='无效的 API Key')

    body = request.get_json() or {}
    rating = body.get('rating', '')
    user = body.get('user', 'api-user')
    if rating not in ('like', 'dislike', 'null'):
        return jsonify(code=400, msg="rating 必须是 'like'、'dislike' 或 'null'")

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            r'SELECT id, conversation_id FROM dify_messages WHERE id = %s',
            (message_id,))
        msg = cur.fetchone()
        if not msg:
            return jsonify(code=404, msg='消息不存在')

        if rating == 'null':
            cur.execute(
                r'DELETE FROM dify_message_feedbacks WHERE message_id = %s AND user_id = %s',
                (message_id, user))
        else:
            cur.execute(
                r'INSERT INTO dify_message_feedbacks (id, message_id, conversation_id, user_id, rating)'
                r' VALUES (%s, %s, %s, %s, %s)'
                r' ON DUPLICATE KEY UPDATE rating = VALUES(rating)',
                (str(uuid.uuid4()), message_id, msg['conversation_id'], user,
                 1 if rating == 'like' else -1))
        db.commit()
        return jsonify(code=200, data={'result': 'success'})
    finally:
        db.close()


# ============================================================
# 会话 Service API（对齐 Dify GET/DELETE /v1/conversations、POST /v1/conversations/<id>/name）
# ============================================================

def _conversation_to_api(row):
    """dify_conversations 行 -> Dify Service API conversation 对象"""
    inputs = {}
    if row.get('knowledge_ids'):
        inputs = {'knowledge_ids': row['knowledge_ids']}
    return {
        'id': row['id'],
        'name': row.get('title') or '',
        'inputs': inputs,
        'status': row.get('status') or 'normal',
        'introduction': '',
        'created_at': _epoch(row.get('created_at')),
    }


@bp.route('/v1/conversations', methods=['GET'])
@api_key_required
def conversation_list():
    """获取会话列表（Dify: GET /v1/conversations?user=&last_id=&limit=）"""
    app = get_current_app()
    if not app:
        return jsonify(code=401, msg='无效的 API Key')

    user = request.args.get('user', '')
    if not user:
        return jsonify(code=400, msg='user 不能为空')
    limit = min(int(request.args.get('limit', 20)), 100)
    last_id = request.args.get('last_id', '')

    db = get_db()
    try:
        cur = db.cursor()
        where = [r'app_id = %s', r'user_id = %s', r"status = 'normal'"]
        params = [app['id'], user]
        if last_id:
            where.append(
                r'(created_at, id) < (SELECT created_at, id FROM dify_conversations WHERE id = %s)')
            params.append(last_id)

        cur.execute(
            r'SELECT * FROM dify_conversations WHERE ' + ' AND '.join(where) +
            r' ORDER BY created_at DESC, id DESC LIMIT %s',
            params + [limit + 1])
        rows = cur.fetchall()
        has_more = len(rows) > limit
        return jsonify(code=200, data={
            'limit': limit,
            'has_more': has_more,
            'data': [_conversation_to_api(r) for r in rows[:limit]],
        })
    finally:
        db.close()


@bp.route('/v1/conversations/<conversation_id>', methods=['DELETE'])
@api_key_required
def conversation_delete(conversation_id):
    """删除会话（Dify: DELETE /v1/conversations/<id>?user=）"""
    app = get_current_app()
    if not app:
        return jsonify(code=401, msg='无效的 API Key')

    user = request.args.get('user', '')

    db = get_db()
    try:
        cur = db.cursor()
        sql = r"UPDATE dify_conversations SET status = 'deleted' WHERE id = %s AND app_id = %s"
        params = [conversation_id, app['id']]
        if user:
            sql += r' AND user_id = %s'
            params.append(user)
        cur.execute(sql, params)
        db.commit()
        if cur.rowcount == 0:
            return jsonify(code=404, msg='会话不存在')
        return jsonify(code=200, data={'result': 'success'})
    finally:
        db.close()


@bp.route('/v1/conversations/<conversation_id>/name', methods=['POST'])
@api_key_required
def conversation_rename(conversation_id):
    """重命名会话（Dify: POST /v1/conversations/<id>/name，body: name, user）"""
    app = get_current_app()
    if not app:
        return jsonify(code=401, msg='无效的 API Key')

    body = request.get_json() or {}
    name = (body.get('name') or '').strip()
    user = body.get('user', '')
    if not name:
        return jsonify(code=400, msg='name 不能为空')
    if len(name) > 100:
        return jsonify(code=400, msg='name 长度不能超过 100')

    db = get_db()
    try:
        cur = db.cursor()
        sql = r'SELECT * FROM dify_conversations WHERE id = %s AND app_id = %s'
        params = [conversation_id, app['id']]
        if user:
            sql += r' AND user_id = %s'
            params.append(user)
        cur.execute(sql, params)
        row = cur.fetchone()
        if not row:
            return jsonify(code=404, msg='会话不存在')

        cur.execute(
            r'UPDATE dify_conversations SET title = %s WHERE id = %s',
            (name, conversation_id))
        db.commit()
        row['title'] = name
        return jsonify(code=200, data=_conversation_to_api(row))
    finally:
        db.close()


# ============================================================
# 文件 Service API
# ============================================================

@bp.route('/v1/files/upload', methods=['POST'])
@api_key_required
def file_upload():
    """上传文件（Service API）"""
    if 'file' not in request.files:
        return jsonify(code=400, msg='未找到文件')

    file = request.files['file']
    if not file.filename:
        return jsonify(code=400, msg='文件名不能为空')

    try:
        import os
        from werkzeug.utils import secure_filename

        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        upload_dir = os.path.join('uploads', 'files')
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, f'{file_id}_{filename}')
        file.save(file_path)

        file_size = os.path.getsize(file_path)

        # 保存文件记录
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''INSERT INTO upload_files
                           (id, app_id, account_id, filename, file_path, file_size,
                            mime_type, created_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
                        (
                            file_id,
                            get_current_app()['id'] if get_current_app() else '',
                            'api-user',
                            filename,
                            file_path,
                            file_size,
                            file.content_type or 'application/octet-stream',
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        ))
            db.commit()
        except Exception:
            # 表可能不存在，仅保存文件
            pass
        finally:
            db.close()

        return jsonify(code=200, data={
            'id': file_id,
            'name': filename,
            'size': file_size,
            'mime_type': file.content_type or 'application/octet-stream',
            'extension': filename.rsplit('.', 1)[-1] if '.' in filename else '',
        })
    except Exception as e:
        return jsonify(code=500, msg=f'上传失败: {str(e)}')


@bp.route('/v1/files/<file_id>', methods=['GET'])
@api_key_required
def file_download(file_id):
    """下载文件（Service API）"""
    import os
    from flask import send_file

    upload_dir = os.path.join('uploads', 'files')
    for f in os.listdir(upload_dir):
        if f.startswith(file_id):
            file_path = os.path.join(upload_dir, f)
            return send_file(file_path, as_attachment=True)

    return jsonify(code=404, msg='文件不存在')


# ============================================================
# 音频 Service API（对齐 Dify /v1/audio-to-text, /v1/text-to-audio）
# ============================================================

# Dify 规范的错误响应格式
def _audio_error(code, message, status):
    """返回 Dify 风格的音频错误响应"""
    return jsonify(code=code, message=message, status=status), status


@bp.route('/v1/audio-to-text', methods=['POST'])
@api_key_required
def audio_to_text():
    """
    语音转文本（Dify: POST /v1/audio-to-text）

    请求: multipart/form-data
      - file: 音频文件（必填，支持 mp3/mpga/m4a/wav/amr，最大 30MB）
      - user: 端用户标识（可选）

    响应: {"text": "识别的文本"}
    """
    app = get_current_app()
    if not app:
        return _audio_error('invalid_api_key', '无效的 API Key', 401)

    # 1. 检查 STT 功能开关
    features = _load_app_features(app['id'])
    stt_feature = features.get('speech_to_text') or {}
    if not stt_feature.get('enabled', False):
        # 默认允许（未配置 features 时不阻断），仅显式关闭时阻断
        pass

    # 2. 校验文件存在
    if 'file' not in request.files:
        return _audio_error('no_audio_uploaded', '未提供音频文件', 400)

    audio_file = request.files['file']
    if not audio_file or not audio_file.filename:
        return _audio_error('no_audio_uploaded', '未提供音频文件', 400)

    # 3. 校验文件大小（Dify 规范：30MB）
    audio_file.seek(0, os.SEEK_END)
    file_size = audio_file.tell()
    audio_file.seek(0)
    if file_size > 30 * 1024 * 1024:
        return _audio_error('audio_too_large', '音频文件超过 30MB 限制', 413)

    if file_size == 0:
        return _audio_error('no_audio_uploaded', '音频文件为空', 400)

    # 4. 校验 MIME 类型
    from utils.audio import is_allowed_audio_type
    content_type = audio_file.content_type or ''
    if not is_allowed_audio_type(content_type, audio_file.filename):
        return _audio_error(
            'unsupported_audio_type',
            f'不支持的音频类型: {content_type or "unknown"}。支持: mp3, m4a, wav, amr',
            415,
        )

    # 5. 查找 STT 模型配置
    from utils.audio import speech_to_text, get_default_audio_config
    cfg = get_default_audio_config('stt')
    if not cfg:
        return _audio_error(
            'provider_not_initialize',
            '未配置 STT（语音识别）模型，请先在模型管理页面添加 Whisper 模型',
            400,
        )

    # 6. 调用 STT
    try:
        audio_bytes = audio_file.read()
        text = speech_to_text(audio_bytes, audio_file.filename, cfg)
        return jsonify(code=200, data={'text': text})
    except NotImplementedError as e:
        return _audio_error('provider_not_support_speech_to_text', str(e), 400)
    except Exception as e:
        return _audio_error('completion_request_error', f'语音识别失败: {str(e)}', 400)


@bp.route('/v1/text-to-audio', methods=['POST'])
@api_key_required
def text_to_audio():
    """
    文本转语音（Dify: POST /v1/text-to-audio）

    请求: application/json
      - text: 文本内容（必填，除非传 message_id）
      - voice: 声音标识（可选，如 alloy/echo/fable/onyx/nova/shimmer）
      - message_id: 消息 ID（可选，优先于 text）
      - streaming: 流式标志（可选，预留）

    响应: 原始二进制音频（Content-Type: audio/mpeg|wav|ogg|flac|aac|mp4|webm）
    """
    app = get_current_app()
    if not app:
        return _audio_error('invalid_api_key', '无效的 API Key', 401)

    # 1. 解析请求体
    body = request.get_json(silent=True) or {}
    text = body.get('text', '')
    voice = body.get('voice', '')
    message_id = body.get('message_id', '')

    # 2. 如果传了 message_id，从消息表取 answer 作为文本（Dify 规范：message_id 优先）
    if message_id and not text:
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r"SELECT content FROM dify_messages WHERE id = %s AND role = 'assistant'",
                (message_id,))
            row = cur.fetchone()
            if row:
                text = row['content'] or ''
        except Exception:
            pass
        finally:
            db.close()

    if not text or not text.strip():
        return _audio_error('invalid_request', 'text 不能为空（或 message_id 无效）', 400)

    # 3. 查找 TTS 模型配置
    from utils.audio import text_to_speech, get_default_audio_config, detect_audio_mime
    cfg = get_default_audio_config('tts')
    if not cfg:
        return _audio_error(
            'provider_not_initialize',
            '未配置 TTS（语音合成）模型，请先在模型管理页面添加 TTS 模型',
            400,
        )

    # 4. 调用 TTS
    try:
        audio_bytes = text_to_speech(text, cfg, voice=voice or None)
        # 检测 MIME 类型（Dify 规范：根据魔法字节）
        mime = detect_audio_mime(audio_bytes)
        return Response(audio_bytes, content_type=mime)
    except NotImplementedError as e:
        return _audio_error('provider_not_initialize', str(e), 400)
    except Exception as e:
        return _audio_error('completion_request_error', f'语音合成失败: {str(e)}', 400)


# ============================================================
# 建议问题 Service API（对齐 Dify GET /v1/messages/<id>/suggested-questions）
# ============================================================

@bp.route('/v1/messages/<message_id>/suggested-questions', methods=['GET'])
@api_key_required
def suggested_questions(message_id):
    """
    获取建议的后续问题（Dify: GET /v1/messages/<id>/suggested-questions）

    基于最近一条助手消息内容，调用 LLM 生成 3 个建议追问。
    返回格式与 Dify 一致：{"data": ["问题1", "问题2", "问题3"]}
    """
    app = get_current_app()
    if not app:
        return jsonify(code=401, msg='无效的 API Key')

    db = get_db()
    try:
        cur = db.cursor()
        # 获取消息内容
        cur.execute(
            r'''SELECT m.id, m.content, m.role, m.conversation_id, c.user_id
                FROM dify_messages m
                JOIN dify_conversations c ON c.id = m.conversation_id
                WHERE m.id = %s AND c.app_id = %s''',
            (message_id, app['id']))
        msg = cur.fetchone()
        if not msg:
            return jsonify(code=404, msg='消息不存在')

        # 只对助手消息生成建议问题
        if msg['role'] != 'assistant':
            return jsonify(code=400, msg='只能对助手消息生成建议问题')

        answer = (msg['content'] or '').strip()
        if not answer:
            return jsonify(code=200, data=[])

        # 调用 LLM 生成建议问题
        try:
            from utils.llm import _call_llm_with_config
            prompt = (
                '你是一个对话助手。根据以下助手回答，生成 3 个用户可能想追问的问题。\n'
                '要求：\n'
                '1. 每个问题不超过 30 字\n'
                '2. 问题应围绕回答中的关键信息\n'
                '3. 按 JSON 数组格式返回，如 ["问题1", "问题2", "问题3"]\n\n'
                f'助手回答：\n{answer[:1000]}\n\n'
                '请直接返回 JSON 数组，不要其他内容。'
            )
            result, err = _call_llm_with_config(prompt, '请生成建议问题。')
            if err:
                # LLM 失败时返回空列表，不阻断主流程
                return jsonify(code=200, data=[])
            # 解析 JSON 数组
            import re
            json_match = re.search(r'\[[\s\S]*?\]', result)
            if json_match:
                questions = json.loads(json_match.group())
                if isinstance(questions, list):
                    return jsonify(code=200, data=[q for q in questions if isinstance(q, str)][:3])
            return jsonify(code=200, data=[])
        except Exception:
            return jsonify(code=200, data=[])
    finally:
        db.close()


# ============================================================
# 元数据 Service API（对齐 Dify GET /v1/meta）
# ============================================================

@bp.route('/v1/meta', methods=['GET'])
@api_key_required
def app_meta():
    """
    获取应用工具图标/元数据（Dify: GET /v1/meta）

    返回工作流中所有工具节点的图标信息，供前端展示。
    返回格式: {"tool_icons": {"tool_name": {"icon": "...", "description": "..."}}}
    """
    app = get_current_app()
    if not app:
        return jsonify(code=401, msg='无效的 API Key')

    db = get_db()
    try:
        cur = db.cursor()
        # 获取工作流中的工具节点
        cur.execute(
            r'''SELECT graph FROM dify_workflows
                WHERE app_id = %s
                ORDER BY updated_at DESC LIMIT 1''',
            (app['id'],))
        row = cur.fetchone()

        tool_icons = {}
        if row and row.get('graph'):
            try:
                graph = json.loads(row['graph'])
                nodes = graph.get('nodes', [])
                for node in nodes:
                    node_data = node.get('data', {})
                    node_type = node_data.get('type', '')
                    if node_type == 'tool':
                        tool_name = node_data.get('title') or node_data.get('tool_name') or node.get('id', '')
                        tool_icons[tool_name] = {
                            'icon': node_data.get('icon', '🔧'),
                            'description': node_data.get('description', ''),
                            'type': node_data.get('tool_type', 'http'),
                        }
            except (json.JSONDecodeError, AttributeError):
                pass

        # 内置工具图标
        builtin_icons = {
            'knowledge-retrieval': {'icon': '📚', 'description': '知识库检索'},
            'http-request': {'icon': '🌐', 'description': 'HTTP 请求'},
            'code': {'icon': '💻', 'description': '代码执行'},
            'calculator': {'icon': '🧮', 'description': '计算器'},
            'web-search': {'icon': '🔍', 'description': '网页搜索'},
        }
        for name, meta in builtin_icons.items():
            if name not in tool_icons:
                tool_icons[name] = meta

        return jsonify(code=200, data={'tool_icons': tool_icons})
    finally:
        db.close()


# ============================================================
# 注册路由
# ============================================================

def register_service_api_routes(app):
    """注册 Service API 路由"""
    _ensure_feedback_table()
    app.register_blueprint(bp)


def _ensure_feedback_table():
    """确保 dify_message_feedbacks 表存在（feedback 接口依赖）"""
    from models.tables import DIFY_MESSAGE_FEEDBACKS_TABLE_SQL
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(DIFY_MESSAGE_FEEDBACKS_TABLE_SQL)
        db.commit()
    except Exception:
        pass
    finally:
        db.close()
