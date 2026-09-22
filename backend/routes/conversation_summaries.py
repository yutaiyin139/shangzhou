# -*- coding: utf-8 -*-
"""对话摘要路由 —— 多轮对话记忆压缩管理"""
import json
import uuid
from flask import Blueprint, request, jsonify
from datetime import datetime

from models.tables import CONVERSATION_SUMMARIES_TABLE_SQL
from config import get_db
from utils.auth import login_required

bp = Blueprint('conversation_summaries', __name__)

# ============================================================
# 初始化表
# ============================================================

def init_tables():
    """初始化对话摘要表"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(CONVERSATION_SUMMARIES_TABLE_SQL)
        db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()

init_tables()

# ============================================================
# 辅助函数
# ============================================================

def _row_to_summary(row):
    """数据库行转摘要字典"""
    return {
        'id': row['id'],
        'conversation_id': row['conversation_id'],
        'app_id': row['app_id'],
        'account_id': row['account_id'],
        'summary_text': row['summary_text'],
        'message_count': row['message_count'] or 0,
        'start_message_id': row['start_message_id'] or '',
        'end_message_id': row['end_message_id'] or '',
        'token_count': row['token_count'] or 0,
        'created_at': str(row['created_at']),
    }

def _estimate_tokens(text):
    """估算文本 token 数（粗略估算：中文约 1.5 char/token，英文约 4 char/token）"""
    if not text:
        return 0
    cn_chars = sum(1 for c in text if '一' <= c <= '鿿')
    other_chars = len(text) - cn_chars
    return int(cn_chars * 1.5 + other_chars / 4)

def _generate_summary(messages):
    """
    生成对话摘要。
    优先使用 LLM 生成高质量摘要；LLM 不可用时回退到启发式摘要。
    """
    if not messages:
        return ''

    # 构建对话文本
    dialogue_lines = []
    for m in messages:
        role = '用户' if m.get('role') == 'user' else '助手'
        content = m.get('content', '').strip()
        if content:
            dialogue_lines.append(f'{role}: {content}')
    dialogue_text = '\n'.join(dialogue_lines)

    if not dialogue_text.strip():
        return ''

    # 尝试使用 LLM 生成摘要
    summary = _generate_summary_with_llm(dialogue_text)
    if summary:
        return summary

    # 回退到启发式摘要
    return _generate_summary_heuristic(messages)


def _generate_summary_with_llm(dialogue_text: str) -> str:
    """
    使用 LLM 生成高质量对话摘要。
    返回空字符串表示 LLM 不可用，应回退到启发式摘要。
    """
    try:
        from utils.llm import _call_llm_with_config
        from config import get_db

        # 查找可用的 LLM 配置
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r'''SELECT provider, api_key, api_base_url, model_name, temperature
                    FROM model_configs
                    WHERE model_type = 'llm' AND status = 1
                    ORDER BY updated_at DESC, id DESC LIMIT 1''')
            llm_cfg = cur.fetchone()
        finally:
            db.close()

        if not llm_cfg:
            return ''

        from utils.llm import decrypt_api_key
        api_key = decrypt_api_key(llm_cfg['api_key'])

        system_prompt = (
            '你是一个对话摘要专家。请阅读以下对话，生成简洁的中文摘要（100-200字）。'
            '摘要应包含：1) 用户的核心问题或需求；2) 助手的关键回答或解决方案；3) 对话的最终结论或待办事项。'
            '只输出摘要文本，不要任何前缀或解释。'
        )

        # 截断过长对话（避免超出上下文窗口）
        max_chars = 4000
        if len(dialogue_text) > max_chars:
            dialogue_text = dialogue_text[:max_chars] + '\n...（对话已截断）'

        user_prompt = f'请为以下对话生成摘要：\n\n{dialogue_text}'

        content, err = _call_llm_with_config(
            system_prompt, user_prompt, llm_cfg, temperature=0.3)
        if err:
            return ''
        return content.strip()
    except Exception:
        return ''


def _generate_summary_heuristic(messages):
    """启发式摘要（LLM 不可用时的回退方案）"""
    user_messages = [m for m in messages if m.get('role') == 'user']
    assistant_messages = [m for m in messages if m.get('role') == 'assistant']

    summary_parts = []
    summary_parts.append(f'对话包含 {len(user_messages)} 轮用户提问和 {len(assistant_messages)} 轮助手回复。')

    if user_messages:
        topics = []
        for msg in user_messages[:5]:
            content = msg.get('content', '')
            if content:
                topics.append(content[:50] + ('...' if len(content) > 50 else ''))
        if topics:
            summary_parts.append('用户关注的话题: ' + '; '.join(topics))

    if assistant_messages:
        last_reply = assistant_messages[-1].get('content', '')
        if last_reply:
            summary_parts.append('最新回复摘要: ' + last_reply[:100] + ('...' if len(last_reply) > 100 else ''))

    return '\n'.join(summary_parts)

# ============================================================
# 摘要 CRUD
# ============================================================

@bp.route('/api/conversations/<conversation_id>/summaries', methods=['GET'])
@login_required
def list_summaries(conversation_id):
    """获取对话的所有摘要"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            r'SELECT * FROM conversation_summaries WHERE conversation_id = %s ORDER BY created_at DESC',
            (conversation_id,)
        )
        items = [_row_to_summary(r) for r in cur.fetchall()]
        return jsonify(code=200, data=items)
    finally:
        db.close()


@bp.route('/api/conversations/<conversation_id>/summaries', methods=['POST'])
@login_required
def create_summary(conversation_id):
    """为对话创建摘要"""
    body = request.get_json() or {}
    messages = body.get('messages', [])

    if not messages:
        return jsonify(code=400, msg='消息列表不能为空')

    # 生成摘要
    summary_text = body.get('summary_text') or _generate_summary(messages)
    token_count = _estimate_tokens(summary_text)

    summary_id = str(uuid.uuid4())
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 获取消息范围
    start_msg_id = body.get('start_message_id', messages[0].get('id', ''))
    end_msg_id = body.get('end_message_id', messages[-1].get('id', ''))

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''INSERT INTO conversation_summaries
                       (id, conversation_id, app_id, account_id, summary_text,
                        message_count, start_message_id, end_message_id,
                        token_count, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                    (
                        summary_id,
                        conversation_id,
                        body.get('app_id', ''),
                        request.user_id or '',
                        summary_text,
                        len(messages),
                        start_msg_id,
                        end_msg_id,
                        token_count,
                        now,
                    ))
        db.commit()
        return jsonify(code=200, msg='摘要创建成功', data={
            'id': summary_id,
            'summary_text': summary_text,
            'token_count': token_count,
        })
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=str(e))
    finally:
        db.close()


@bp.route('/api/conversations/<conversation_id>/summaries/latest', methods=['GET'])
@login_required
def get_latest_summary(conversation_id):
    """获取对话最新摘要"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            r'SELECT * FROM conversation_summaries WHERE conversation_id = %s ORDER BY created_at DESC LIMIT 1',
            (conversation_id,)
        )
        row = cur.fetchone()
        if not row:
            return jsonify(code=404, msg='暂无摘要')
        return jsonify(code=200, data=_row_to_summary(row))
    finally:
        db.close()


@bp.route('/api/conversations/<conversation_id>/summaries/auto', methods=['POST'])
@login_required
def auto_summarize(conversation_id):
    """
    自动摘要：根据配置自动压缩历史消息
    当消息数量超过阈值时，自动将旧消息压缩为摘要
    """
    body = request.get_json() or {}
    messages = body.get('messages', [])
    threshold = body.get('threshold', 20)  # 超过 20 条消息触发压缩
    keep_recent = body.get('keep_recent', 10)  # 保留最近 10 条

    if len(messages) <= threshold:
        return jsonify(code=200, msg='消息数量未超过阈值，无需压缩', data={
            'compressed': False,
            'message_count': len(messages),
        })

    # 需要压缩的消息
    messages_to_compress = messages[:-keep_recent]
    recent_messages = messages[-keep_recent:]

    # 生成摘要
    summary_text = body.get('summary_text') or _generate_summary(messages_to_compress)
    token_count = _estimate_tokens(summary_text)

    summary_id = str(uuid.uuid4())
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''INSERT INTO conversation_summaries
                       (id, conversation_id, app_id, account_id, summary_text,
                        message_count, start_message_id, end_message_id,
                        token_count, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                    (
                        summary_id,
                        conversation_id,
                        body.get('app_id', ''),
                        request.user_id or '',
                        summary_text,
                        len(messages_to_compress),
                        messages_to_compress[0].get('id', ''),
                        messages_to_compress[-1].get('id', ''),
                        token_count,
                        now,
                    ))
        db.commit()
        return jsonify(code=200, msg='自动压缩完成', data={
            'compressed': True,
            'summary_id': summary_id,
            'summary_text': summary_text,
            'token_count': token_count,
            'compressed_count': len(messages_to_compress),
            'recent_count': len(recent_messages),
        })
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=str(e))
    finally:
        db.close()


@bp.route('/api/conversations/<conversation_id>/summaries/<summary_id>', methods=['DELETE'])
@login_required
def delete_summary(conversation_id, summary_id):
    """删除摘要"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            r'DELETE FROM conversation_summaries WHERE id = %s AND conversation_id = %s',
            (summary_id, conversation_id)
        )
        db.commit()
        return jsonify(code=200, msg='删除成功')
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=str(e))
    finally:
        db.close()


# ============================================================
# 注册路由
# ============================================================

def auto_summarize_if_needed(conversation_id: str, app_id: str = '',
                               threshold: int = 20, keep_recent: int = 10) -> str:
    """
    自动摘要触发器：当会话消息数超过阈值时，自动压缩旧消息为摘要。

    参数:
        conversation_id: 会话 ID
        app_id: 应用 ID
        threshold: 消息数阈值（超过此值触发压缩）
        keep_recent: 保留最近 N 条消息不压缩

    返回:
        str — 如果有新摘要被创建，返回摘要文本；否则返回空字符串。
    """
    if not conversation_id:
        return ''

    db = get_db()
    try:
        cur = db.cursor()

        # 获取该会话的所有消息
        cur.execute(
            r'''SELECT id, role, content FROM dify_messages
                WHERE conversation_id = %s
                ORDER BY created_at ASC, id ASC''',
            (conversation_id,))
        messages = cur.fetchall()

        if len(messages) <= threshold:
            return ''

        # 检查最近是否已有摘要（避免重复压缩）
        cur.execute(
            r'''SELECT COUNT(*) as cnt FROM conversation_summaries
                WHERE conversation_id = %s''',
            (conversation_id,))
        existing_count = cur.fetchone()['cnt']

        # 如果已有摘要且消息数未超过阈值的两倍，不重复压缩
        if existing_count > 0 and len(messages) <= threshold * 2:
            return ''

        # 需要压缩的消息（保留最近 keep_recent 条）
        messages_to_compress = messages[:-keep_recent]
        recent_messages = messages[-keep_recent:]

        # 构建消息列表（用于摘要生成）
        msg_list = [{'id': m['id'], 'role': m['role'], 'content': m['content']}
                    for m in messages_to_compress]

        # 生成摘要
        summary_text = _generate_summary(msg_list)
        if not summary_text:
            return ''

        # 保存摘要
        summary_id = str(uuid.uuid4())
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        token_count = _estimate_tokens(summary_text)

        cur.execute(
            r'''INSERT INTO conversation_summaries
                (id, conversation_id, app_id, account_id, summary_text,
                 message_count, start_message_id, end_message_id,
                 token_count, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
            (
                summary_id,
                conversation_id,
                app_id,
                '',
                summary_text,
                len(messages_to_compress),
                messages_to_compress[0]['id'],
                messages_to_compress[-1]['id'],
                token_count,
                now,
            ))
        db.commit()
        return summary_text
    except Exception:
        db.rollback()
        return ''
    finally:
        db.close()


def register_conversation_summary_routes(app):
    """注册对话摘要路由"""
    app.register_blueprint(bp)
