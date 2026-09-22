# -*- coding: utf-8 -*-
"""聊天与知识库路由（MySQL 版，脱离 Dify）"""

import uuid
import threading
from datetime import datetime
from flask import jsonify, request, Response
import json
import urllib.request
import urllib.error
from config import get_db
from utils.helpers import now
from utils.llm import _extract_json, decrypt_api_key, build_openai_url
from utils.redis_cache import (
    llm_cache_get, llm_cache_set, redis_available,
    rate_limit, cache_get, cache_set
)

# ============================================================
#  长期记忆注入 —— 当 agent_id 存在且启用记忆时，注入相似记忆到 system prompt
# ============================================================

def _inject_memory_context(system_prompt: str, agent_id, message: str) -> str:
    """
    检索 agent 的长期记忆并注入 system prompt。
    仅当 agent_id 非空、agent 启用记忆、且检索到命中时生效。
    无命中或异常时返回原始 prompt（安全降级）。
    """
    if not agent_id or not message:
        return system_prompt
    try:
        # 加载 agent 配置，检查 memory_enabled 开关
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r"SELECT config FROM agents WHERE id = %s AND type = 'single'", (agent_id,))
            row = cur.fetchone()
        finally:
            db.close()
        if not row:
            return system_prompt
        import json as _json
        cfg = _json.loads(row['config']) if row['config'] else {}
        # memory_enabled 默认 True（向后兼容），仅显式 False 时关闭
        if cfg.get('memory_enabled') is False:
            return system_prompt
        # 检索记忆
        from engine.agent_memory import build_memory_context
        mem_ctx = build_memory_context(int(agent_id), message, limit=5, min_score=0.35)
        if mem_ctx:
            return system_prompt + '\n\n' + mem_ctx
    except Exception:
        pass
    return system_prompt


def _auto_save_memory(agent_id, user_message: str, assistant_reply: str):
    """
    对话结束后自动提取关键信息写入记忆（异步，不阻塞响应）。
    仅当 agent_id 非空且启用记忆时执行。
    """
    if not agent_id or not user_message:
        return
    try:
        import json as _json
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r"SELECT config FROM agents WHERE id = %s AND type = 'single'", (agent_id,))
            row = cur.fetchone()
        finally:
            db.close()
        if not row:
            return
        cfg = _json.loads(row['config']) if row['config'] else {}
        if cfg.get('memory_enabled') is False:
            return
        # 异步写入记忆（Celery 不可用时同步降级）
        try:
            from tasks.embedding_tasks import save_conversation_memory
            save_conversation_memory.delay(
                agent_id=int(agent_id),
                user_message=user_message,
                assistant_reply=assistant_reply
            )
        except Exception:
            # Celery 不可用时，直接写入一条简单记忆
            from engine.agent_memory import add_memory
            summary = f"用户：{user_message[:100]}\n回复：{assistant_reply[:200]}"
            add_memory(int(agent_id), summary)
    except Exception:
        pass
from models.tables import (
    DIFY_DOCUMENT_SEGMENTS_TABLE_SQL,
    DIFY_DATASETS_TABLE_SQL,
    DIFY_CONVERSATIONS_TABLE_SQL,
    DIFY_MESSAGES_TABLE_SQL,
)

# ============================================================
# 流式任务管理 —— 支持停止正在进行的流式生成
# ============================================================

# 活跃的流式任务 {task_id: {"cancelled": bool, "user": str}}
_active_stream_tasks = {}
_lock = threading.Lock()


def _register_stream_task(task_id, user=''):
    """注册一个流式任务"""
    with _lock:
        _active_stream_tasks[task_id] = {'cancelled': False, 'user': user}


def _cancel_stream_task(task_id):
    """取消一个流式任务"""
    with _lock:
        if task_id in _active_stream_tasks:
            _active_stream_tasks[task_id]['cancelled'] = True
            return True
    return False


def _is_stream_task_cancelled(task_id):
    """检查流式任务是否已被取消"""
    with _lock:
        task = _active_stream_tasks.get(task_id)
        return task['cancelled'] if task else False


def _unregister_stream_task(task_id):
    """注销一个流式任务"""
    with _lock:
        _active_stream_tasks.pop(task_id, None)


_KB_STOPWORDS = {'如何', '什么', '怎么', '可以', '一个', '这个', '那个', '我们', '你们', '他们', '是否', '请问', '帮我', '一下', '进行', '使用', '需要', '没有', '不是'}


def _ensure_chat_tables():
    """确保聊天相关表已创建"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(DIFY_DOCUMENT_SEGMENTS_TABLE_SQL)
        cur.execute(DIFY_DATASETS_TABLE_SQL)
        cur.execute(DIFY_CONVERSATIONS_TABLE_SQL)
        cur.execute(DIFY_MESSAGES_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def _generate_title(message):
    """根据首条消息自动生成会话标题"""
    title = (message or '').strip()
    if len(title) > 30:
        title = title[:30] + '...'
    return title or '新对话'


def _save_message(conv_id, role, content, tokens=0, model_provider='', model_name=''):
    """保存消息到数据库"""
    db = get_db()
    try:
        cur = db.cursor()
        msg_id = str(uuid.uuid4())
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute(
            '''INSERT INTO dify_messages
               (id, conversation_id, role, content, tokens, model_provider, model_name, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
            (msg_id, conv_id, role, content, tokens, model_provider, model_name, ts)
        )
        return msg_id
    finally:
        db.close()


def _save_message_with_thinking(conv_id, role, content, thinking_chain='', tokens=0, model_provider='', model_name=''):
    """保存消息到数据库（含思维链）"""
    db = get_db()
    try:
        cur = db.cursor()
        msg_id = str(uuid.uuid4())
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # 思维链存入 metadata 字段（JSON 格式）
        metadata = ''
        if thinking_chain:
            metadata = json.dumps({'thinking_chain': thinking_chain}, ensure_ascii=False)
        cur.execute(
            '''INSERT INTO dify_messages
               (id, conversation_id, role, content, tokens, model_provider, model_name, metadata, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
            (msg_id, conv_id, role, content, tokens, model_provider, model_name, metadata, ts)
        )
        db.commit()
        return msg_id
    finally:
        db.close()


def _update_conversation_stats(conv_id, tokens_added=0):
    """更新会话统计信息"""
    db = get_db()
    try:
        cur = db.cursor()
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute(
            '''UPDATE dify_conversations
               SET message_count = message_count + 2,
                   total_tokens = total_tokens + %s,
                   last_message_at = %s,
                   updated_at = %s
               WHERE id = %s''',
            (tokens_added, ts, ts, conv_id)
        )
        db.commit()
    finally:
        db.close()


def _update_conversation_title(conv_id, title):
    """更新会话标题"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            'UPDATE dify_conversations SET title = %s WHERE id = %s',
            (title, conv_id)
        )
        db.commit()
    finally:
        db.close()


def _retrieve_knowledge(knowledge_ids, query, limit=6):
    """在 dify_document_segments 中检索与问题相关的段落（关键词匹配打分）
    返回: [(row, score), ...] 按相关度降序
    """
    import re as _re
    if not knowledge_ids:
        return []
    # 关键词：英文单词/编号 + 中文 2-gram
    kws = _re.findall(r'[A-Za-z][A-Za-z0-9._\-]*', query)
    zh_parts = _re.findall(r'[一-龥]{2,}', query)
    for p in zh_parts:
        for i in range(len(p) - 1):
            gram = p[i:i + 2]
            if gram not in _KB_STOPWORDS:
                kws.append(gram)
    kws = list(dict.fromkeys(kws))
    if not kws:
        kws = [query]
    db = get_db()
    try:
        cur = db.cursor()
        placeholders = ','.join(['%s'] * len(knowledge_ids))
        cur.execute("""
            SELECT seg.id, seg.content, seg.dataset_id, seg.document_id, d.name AS dataset_name, seg.word_count
            FROM dify_document_segments seg
            JOIN dify_datasets d ON d.id = seg.dataset_id
            WHERE seg.dataset_id IN (%s) AND seg.enabled = true AND seg.status = 'completed'
        """ % placeholders, knowledge_ids)
        rows = cur.fetchall()
    finally:
        db.close()
    scored = []
    for r in rows:
        c = (r['content'] or '').lower()
        score = sum(1 for kw in kws if kw.lower() in c)
        if score:
            scored.append((score, r))
    scored.sort(key=lambda x: (-x[0], -x[1]['word_count']))
    return scored[:limit]


def _retrieve_skills(skill_keys):
    """根据 skill key 列表获取技能内容
    返回: [{'key': ..., 'name': ..., 'content': ...}, ...]
    """
    if not skill_keys:
        return []
    from models.builtin_skills import BUILTIN_SKILLS
    skill_map = {s['key']: s for s in BUILTIN_SKILLS}
    result = []
    custom_ids = []
    for key in skill_keys:
        if key.startswith('custom_'):
            try:
                custom_ids.append(int(key[7:]))
            except ValueError:
                continue
        elif key in skill_map:
            s = skill_map[key]
            result.append({'key': key, 'name': s['name'], 'content': s.get('content', '')})
    if custom_ids:
        db = get_db()
        try:
            cur = db.cursor()
            placeholders = ','.join(['%s'] * len(custom_ids))
            cur.execute(f"SELECT id, name, content FROM skills WHERE id IN ({placeholders}) AND kind = 'custom'", custom_ids)
            for r in cur.fetchall():
                result.append({'key': 'custom_' + str(r['id']), 'name': r['name'], 'content': r.get('content', '') or ''})
        finally:
            db.close()
    return result


def _retrieve_files(file_ids):
    """根据文件 ID 列表获取文件内容（仅文本类文件）
    返回: [{'name': ..., 'content': ...}, ...]
    """
    if not file_ids:
        return []
    # 支持的文件类型（文本可读取）
    text_extensions = {'txt', 'md', 'csv', 'json', 'xml', 'yaml', 'yml', 'py', 'js', 'ts', 'java', 'c', 'cpp',
                       'h', 'go', 'rs', 'rb', 'php', 'html', 'css', 'sql', 'sh', 'bat', 'log', 'ini', 'conf'}
    db = get_db()
    try:
        cur = db.cursor()
        placeholders = ','.join(['%s'] * len(file_ids))
        cur.execute(
            f"SELECT id, original_name, file_path, extension, mime_type FROM dify_upload_files "
            f"WHERE id IN ({placeholders}) AND status = 'active'",
            file_ids
        )
        rows = cur.fetchall()
    finally:
        db.close()

    result = []
    from utils.storage import get_storage
    storage = get_storage()
    for r in rows:
        ext = (r['extension'] or '').lower()
        # 只读取文本类文件内容
        if ext not in text_extensions and not (r['mime_type'] or '').startswith('text/'):
            result.append({'name': r['original_name'], 'content': f'[文件 {r["original_name"]} 为非文本文件，无法直接读取内容]'})
            continue
        try:
            file_data = storage.read(r['file_path'])
            content = file_data.decode('utf-8', errors='replace')[:10000]  # 限制 10KB
            result.append({'name': r['original_name'], 'content': content})
        except Exception as e:
            result.append({'name': r['original_name'], 'content': f'[读取文件失败: {str(e)}]'})
    return result


def _build_retriever_resources(scored_results):
    """将检索结果转换为结构化引用列表（3.1: 引用追踪）"""
    resources = []
    for idx, (score, r) in enumerate(scored_results):
        resources.append({
            'segment_id': r.get('id', ''),
            'dataset_id': r.get('dataset_id', ''),
            'document_id': r.get('document_id', ''),
            'document_name': r.get('dataset_name', ''),
            'content': (r.get('content') or '')[:500],
            'score': min(score / 10.0, 1.0),  # 归一化到 0-1
            'position': idx,
        })
    return resources


def register_chat_routes(app):
    """注册聊天相关路由"""

    @app.route('/api/chat', methods=['POST'])
    @rate_limit(limit=30, window=60)  # 每分钟最多 30 次聊天请求
    def chat():
        _ensure_chat_tables()
        d = request.get_json()
        message = d.get('message', '').strip()
        provider_name = d.get('provider', '').strip()  # 模型供应商名，如 deepseek、qwen
        knowledge_ids = d.get('knowledge_ids') or []  # 选中的知识库 id 列表
        file_ids = d.get('file_ids') or []  # 上传的文件 ID 列表
        custom_sys = d.get('system', '').strip()  # 自定义 system prompt（智能体提示词）
        agent_id = d.get('agent_id')  # 智能体 id（可选）
        conversation_id = d.get('conversation_id', '').strip()  # 会话 id（可选，首次对话不传）
        no_cache = d.get('no_cache', False)  # 是否跳过缓存
        if not message:
            return jsonify(code=400, msg='请输入消息内容')

        # 基于知识库检索参考段落
        scored_refs = _retrieve_knowledge(knowledge_ids, message)
        refs = [r for _, r in scored_refs]  # 兼容旧格式
        kb_names = list(dict.fromkeys([r['dataset_name'] for r in refs]))
        retriever_resources = _build_retriever_resources(scored_refs)
        system_prompt = custom_sys or '你是一个智能助手，请用简洁专业的中文回答用户问题。'
        if refs:
            ref_text = '\n\n'.join(r['content'].strip() for r in refs)
            system_prompt = (
                (custom_sys + '\n\n' if custom_sys else '') +
                '请优先依据下面提供的【知识库资料】回答用户问题；'
                '如果资料中找不到答案，请如实说明"知识库中未找到相关内容"，不要编造。\n\n'
                '【知识库资料】\n' + ref_text + '\n【资料结束】'
            )

        # 文件注入：读取用户上传的文件内容并拼接到 system prompt
        if file_ids:
            file_contents = _retrieve_files(file_ids)
            if file_contents:
                file_blocks = []
                for fc in file_contents:
                    file_blocks.append(f"【文件：{fc['name']}】\n{fc['content']}")
                if file_blocks:
                    system_prompt += '\n\n## 用户上传了以下文件，请参考文件内容回答问题：\n\n' + '\n\n'.join(file_blocks) + '\n\n'

        # 长期记忆注入：当 agent_id 存在时，检索相似记忆拼接到 system prompt
        system_prompt = _inject_memory_context(system_prompt, agent_id, message)

        # 根据 provider 查找模型配置
        db = get_db()
        try:
            cur = db.cursor()
            if provider_name and provider_name != 'auto':
                # 取该供应商最新更新的启用配置，避免选到旧的错误配置
                cur.execute(
                    r'SELECT * FROM model_configs WHERE provider = %s AND status = 1 ORDER BY updated_at DESC, id DESC LIMIT 1',
                    (provider_name,)
                )
            else:
                cur.execute(
                    r'SELECT * FROM model_configs WHERE status = 1 ORDER BY updated_at DESC LIMIT 1'
                )
            cfg = cur.fetchone()
            if not cfg:
                return jsonify(code=400, msg='没有可用的模型配置，请先在模型页面添加')
        finally:
            db.close()

        api_key = decrypt_api_key(cfg['api_key'])
        base_url = (cfg['api_base_url'] or '').rstrip('/')
        chat_url = build_openai_url(base_url, 'chat/completions')

        # 构造 OpenAI 兼容请求
        model_name = cfg['model_name'] or cfg['credential_name'] or cfg['provider']
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': message}
        ]
        # 采用模型配置里的温度/最大 token（Kimi 等模型要求 temperature=1，硬编码会导致上游 400）
        try:
            temperature = float(cfg['temperature']) if cfg['temperature'] is not None else 0.7
        except (KeyError, TypeError, ValueError):
            temperature = 0.7
        try:
            max_tokens = int(cfg['max_tokens']) if cfg['max_tokens'] else 2048
        except (KeyError, TypeError, ValueError):
            max_tokens = 2048

        # 尝试从 Redis 缓存获取（仅无知识库检索时启用缓存）
        cached_response = None
        if not no_cache and not refs and redis_available():
            cached_response = llm_cache_get(messages, model_name, temperature, max_tokens)

        cache_hit = cached_response is not None
        content = ''
        total_tokens = 0

        if cached_response:
            # 缓存命中
            content = cached_response.get('content', '')
            total_tokens = cached_response.get('total_tokens', 0)
        else:
            # 调用 LLM API
            payload = json.dumps({
                'model': model_name,
                'messages': messages,
                'temperature': temperature,
                'max_tokens': max_tokens,
                'stream': False
            }).encode('utf-8')

            req = urllib.request.Request(
                chat_url,
                data=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + api_key
                },
                method='POST'
            )

            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    result = json.loads(resp.read().decode('utf-8'))
                # 提取回复内容
                if 'choices' in result and result['choices']:
                    content = result['choices'][0].get('message', {}).get('content', '')
                if 'usage' in result:
                    total_tokens = result['usage'].get('total_tokens', 0)
                if not content:
                    content = '(模型未返回内容，原始响应: ' + json.dumps(result, ensure_ascii=False)[:200] + ')'

                # 写入 Redis 缓存（仅无知识库检索时缓存）
                if not refs and redis_available() and content:
                    llm_cache_set(messages, model_name, temperature, max_tokens,
                                  {'content': content, 'total_tokens': total_tokens},
                                  ttl=3600)  # 缓存 1 小时

            except urllib.error.HTTPError as e:
                err_body = e.read().decode('utf-8', errors='replace')[:300]
                return jsonify(code=502, msg='模型API请求: POST ' + chat_url + ' | 模型: ' + model_name + ' | 错误: ' + err_body)
            except Exception as e:
                return jsonify(code=500, msg='调用模型失败: ' + str(e))

        # 持久化对话历史
        is_new_conversation = False
        if not conversation_id:
            # 创建新会话
            is_new_conversation = True
            conversation_id = str(uuid.uuid4())
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            title = _generate_title(message)
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(
                    '''INSERT INTO dify_conversations
                       (id, agent_id, title, system_prompt, knowledge_ids,
                        model_provider, model_name, message_count, total_tokens,
                        last_message_at, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, 2, %s, %s, %s, %s)''',
                    (conversation_id, agent_id, title, system_prompt,
                     ','.join(knowledge_ids) if knowledge_ids else '',
                     cfg['provider'], model_name, total_tokens, ts, ts, ts)
                )
                db.commit()
            finally:
                db.close()
            # 保存用户消息
            _save_message(conversation_id, 'user', message, 0, cfg['provider'], model_name)
            # 保存助手回复
            _save_message(conversation_id, 'assistant', content, total_tokens, cfg['provider'], model_name)
        else:
            # 已有会话，保存消息并更新统计
            _save_message(conversation_id, 'user', message, 0, cfg['provider'], model_name)
            _save_message(conversation_id, 'assistant', content, total_tokens, cfg['provider'], model_name)
            _update_conversation_stats(conversation_id, total_tokens)

        # 获取刚保存的 assistant 消息 ID（用于反馈关联）
        assistant_msg_id = None
        try:
            db2 = get_db()
            try:
                cur2 = db2.cursor()
                cur2.execute(
                    r'''SELECT id FROM dify_messages
                        WHERE conversation_id = %s AND role = 'assistant'
                        ORDER BY created_at DESC LIMIT 1''',
                    (conversation_id,)
                )
                row = cur2.fetchone()
                if row:
                    assistant_msg_id = row['id']
            finally:
                db2.close()
        except Exception:
            pass

        # 保存检索引用（3.1: 引用追踪）
        if retriever_resources and assistant_msg_id:
            try:
                from engine.retrieval_resources import save_retriever_resources
                save_retriever_resources(assistant_msg_id, retriever_resources)
            except Exception:
                pass

        # 自动写入长期记忆（异步，不阻塞响应）
        _auto_save_memory(agent_id, message, content)

        return jsonify(code=200, data={
            'reply': content,
            'model': model_name,
            'provider': cfg['provider'],
            'knowledge_used': kb_names,
            'knowledge_matched': len(refs),
            'conversation_id': conversation_id,
            'is_new_conversation': is_new_conversation,
            'total_tokens': total_tokens,
            'cache_hit': cache_hit,  # 是否命中缓存
            'message_id': assistant_msg_id,  # 消息 ID（用于反馈）
            'retriever_resources': retriever_resources,  # 结构化引用
        })

    @app.route('/api/agent/build', methods=['POST'])
    def agent_build():
        """根据一句话需求生成 Agent 配置（LLM 返回结构化 JSON，前端自动填充表单）"""
        d = request.get_json()
        requirement = d.get('requirement', '').strip()
        if not requirement:
            return jsonify(code=400, msg='请描述你的 Agent 需求')

        # 查找模型配置（同 chat：无 provider 时取最新启用的）
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM model_configs WHERE status = 1 ORDER BY updated_at DESC LIMIT 1')
            cfg = cur.fetchone()
            if not cfg:
                return jsonify(code=400, msg='没有可用的模型配置，请先在模型页面添加')
        finally:
            db.close()

        api_key = decrypt_api_key(cfg['api_key'])
        base_url = (cfg['api_base_url'] or '').rstrip('/')
        chat_url = build_openai_url(base_url, 'chat/completions')
        model_name = cfg['model_name'] or cfg['credential_name'] or cfg['provider']

        sys_prompt = (
            '你是智能体配置生成助手。根据用户的一句话需求，输出严格的 JSON（不要 markdown 代码块标记，不要任何多余文字）。\n'
            '字段如下：\n'
            '{"name": "智能体名称（简洁），"role": "角色定位", "prompt": "完整的中文系统提示词，说明该 Agent 的职责、行为规则与输出风格", '
            '"model": "qwen3.7-max", "temperature": 0.7, "max_tokens": 4096, '
            '"skills": [{"icon": "✨", "name": "技能名"}], "tools": [{"icon": "🔧", "name": "工具名"}], '
            '"files": [{"icon": "📄", "name": "文件名"}], "kbs": [{"icon": "📚", "name": "知识库名"}]}\n'
            'skills/tools/files/kbs 根据需求合理推断，没有则为空数组；name 与 role 必须给出。'
        )
        payload = json.dumps({
            'model': model_name,
            'messages': [
                {'role': 'system', 'content': sys_prompt},
                {'role': 'user', 'content': requirement}
            ],
            'temperature': 0.4,
            'max_tokens': 2048,
            'stream': False
        }).encode('utf-8')

        req = urllib.request.Request(
            chat_url,
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + api_key
            },
            method='POST'
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode('utf-8'))
            content = ''
            if 'choices' in result and result['choices']:
                content = result['choices'][0].get('message', {}).get('content', '')
            cfg_obj = _extract_json(content)
            if not cfg_obj:
                return jsonify(code=500, msg='模型返回的配置无法解析，请重试')
            return jsonify(code=200, data=cfg_obj)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='replace')[:300]
            return jsonify(code=502, msg='模型API请求: POST ' + chat_url + ' | 错误: ' + err_body)
        except Exception as e:
            return jsonify(code=500, msg='构建失败: ' + str(e))

    @app.route('/api/chat/stream', methods=['POST'])
    def chat_stream():
        """
        流式聊天（SSE）。

        与 /api/chat 参数相同，但以 Server-Sent Events 返回流式响应。

        SSE 事件格式:
        - data: {"task_id": "..."}  —— 首条事件，返回任务 ID
        - data: {"content": "增量文本"}\n\n
        - data: {"done": true}\n\n
        - data: {"error": "错误信息"}\n\n
        - data: {"meta": {"conversation_id": "...", "model": "..."}}\n\n

        停止生成: POST /api/chat/stream/<task_id>/stop
        """
        _ensure_chat_tables()
        d = request.get_json()
        message = d.get('message', '').strip()
        provider_name = d.get('provider', '').strip()
        knowledge_ids = d.get('knowledge_ids') or []
        skill_keys = d.get('skills') or []   # 新增：选中的技能 key 列表
        file_ids = d.get('file_ids') or []   # 新增：上传的文件 ID 列表
        custom_sys = d.get('system', '').strip()
        agent_id = d.get('agent_id')
        conversation_id = d.get('conversation_id', '').strip()

        if not message:
            return jsonify(code=400, msg='请输入消息内容')

        # 基于知识库检索参考段落
        scored_refs = _retrieve_knowledge(knowledge_ids, message)
        refs = [r for _, r in scored_refs]
        kb_names = list(dict.fromkeys([r['dataset_name'] for r in refs]))
        retriever_resources = _build_retriever_resources(scored_refs)

        # 获取技能内容
        skills = _retrieve_skills(skill_keys)

        system_prompt = custom_sys or '你是一个智能助手，请用简洁专业的中文回答用户问题。'

        # 技能注入：将选中的技能指令拼接到 system prompt
        if skills:
            skill_blocks = []
            for sk in skills:
                if sk.get('content'):
                    skill_blocks.append(f"【技能：{sk['name']}】\n{sk['content']}")
            if skill_blocks:
                system_prompt += '\n\n## 用户已启用以下技能，请按照技能指令执行任务：\n\n' + '\n\n'.join(skill_blocks) + '\n\n'

        if refs:
            ref_text = '\n\n'.join(r['content'].strip() for r in refs)
            system_prompt += (
                '\n\n请优先依据下面提供的【知识库资料】回答用户问题；'
                '如果资料中找不到答案，请如实说明"知识库中未找到相关内容"，不要编造。\n\n'
                '【知识库资料】\n' + ref_text + '\n【资料结束】'
            )

        # 文件注入：读取用户上传的文件内容并拼接到 system prompt
        file_names = []
        if file_ids:
            file_contents = _retrieve_files(file_ids)
            if file_contents:
                file_blocks = []
                for fc in file_contents:
                    file_blocks.append(f"【文件：{fc['name']}】\n{fc['content']}")
                    file_names.append(fc['name'])
                if file_blocks:
                    system_prompt += '\n\n## 用户上传了以下文件，请参考文件内容回答问题：\n\n' + '\n\n'.join(file_blocks) + '\n\n'

        # 长期记忆注入：当 agent_id 存在时，检索相似记忆拼接到 system prompt
        system_prompt = _inject_memory_context(system_prompt, agent_id, message)

        # 根据 provider 查找模型配置
        db = get_db()
        try:
            cur = db.cursor()
            if provider_name and provider_name != 'auto':
                # 取该供应商最新更新的启用配置，避免选到旧的错误配置
                cur.execute(
                    r'SELECT * FROM model_configs WHERE provider = %s AND status = 1 ORDER BY updated_at DESC, id DESC LIMIT 1',
                    (provider_name,)
                )
            else:
                cur.execute(
                    r'SELECT * FROM model_configs WHERE status = 1 ORDER BY updated_at DESC LIMIT 1'
                )
            cfg = cur.fetchone()
            if not cfg:
                def _err_no_cfg():
                    yield f"data: {json.dumps({'error': '没有可用的模型配置，请先在模型页面添加'}, ensure_ascii=False)}\n\n"
                return Response(_err_no_cfg(), mimetype='text/event-stream', headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no'
                })
        finally:
            db.close()

        api_key = decrypt_api_key(cfg['api_key'])
        base_url = (cfg['api_base_url'] or '').rstrip('/')
        model_name = cfg['model_name'] or cfg['credential_name'] or cfg['provider']

        # 采用模型配置里的温度/最大 token（Kimi 等模型要求 temperature=1，硬编码会导致上游 400）
        try:
            cfg_temperature = float(cfg['temperature']) if cfg['temperature'] is not None else 0.7
        except (KeyError, TypeError, ValueError):
            cfg_temperature = 0.7
        try:
            cfg_max_tokens = int(cfg['max_tokens']) if cfg['max_tokens'] else 2048
        except (KeyError, TypeError, ValueError):
            cfg_max_tokens = 2048

        # 构造消息
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': message}
        ]

        # 生成新的 conversation_id（如果需要）
        is_new_conversation = False
        if not conversation_id:
            is_new_conversation = True
            conversation_id = str(uuid.uuid4())

        # 生成任务 ID 并注册
        task_id = str(uuid.uuid4())
        _register_stream_task(task_id)

        def generate():
            """SSE 生成器"""
            full_content = ''
            full_thinking = ''  # 累积思维链内容
            total_tokens = 0

            try:
                # 首条事件：返回 task_id
                yield f"data: {json.dumps({'task_id': task_id}, ensure_ascii=False)}\n\n"

                # 导入流式调用函数
                from engine.workflow_runner import _call_llm_stream

                for chunk in _call_llm_stream(messages, model_name, api_key, base_url,
                                              temperature=cfg_temperature, max_tokens=cfg_max_tokens):
                    # 检查是否被取消
                    if _is_stream_task_cancelled(task_id):
                        yield f"data: {json.dumps({'stopped': True, 'content': full_content}, ensure_ascii=False)}\n\n"
                        # 持久化已生成的内容
                        try:
                            if is_new_conversation:
                                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                title = _generate_title(message)
                                db2 = get_db()
                                try:
                                    cur2 = db2.cursor()
                                    cur2.execute(
                                        '''INSERT INTO dify_conversations
                                           (id, agent_id, title, system_prompt, knowledge_ids,
                                            model_provider, model_name, message_count, total_tokens,
                                            last_message_at, created_at, updated_at)
                                           VALUES (%s, %s, %s, %s, %s, %s, %s, 2, %s, %s, %s, %s)''',
                                        (conversation_id, agent_id, title, system_prompt,
                                         ','.join(knowledge_ids) if knowledge_ids else '',
                                         cfg['provider'], model_name, total_tokens, ts, ts, ts)
                                    )
                                    db2.commit()
                                finally:
                                    db2.close()
                            _save_message(conversation_id, 'user', message, 0, cfg['provider'], model_name)
                            # 保存含思维链的助手回复
                            _save_message_with_thinking(
                                conversation_id, 'assistant',
                                full_content + ' [已停止]',
                                thinking_chain=full_thinking,
                                tokens=total_tokens,
                                model_provider=cfg['provider'],
                                model_name=model_name
                            )
                        except Exception:
                            pass
                        return

                    if 'error' in chunk:
                        yield f"data: {json.dumps({'error': chunk['error']}, ensure_ascii=False)}\n\n"
                        return

                    # 处理思维链事件（DeepSeek R1 等推理模型）
                    if 'thinking' in chunk:
                        full_thinking += chunk['thinking']
                        yield f"data: {json.dumps({'thinking': chunk['thinking']}, ensure_ascii=False)}\n\n"

                    if chunk.get('done'):
                        # 流式结束，发送 meta 信息（包含完整思维链）
                        # 获取刚保存的 assistant 消息 ID（用于反馈关联）
                        assistant_msg_id = None
                        try:
                            db2 = get_db()
                            try:
                                cur2 = db2.cursor()
                                cur2.execute(
                                    r'''SELECT id FROM dify_messages
                                        WHERE conversation_id = %s AND role = 'assistant'
                                        ORDER BY created_at DESC LIMIT 1''',
                                    (conversation_id,)
                                )
                                row = cur2.fetchone()
                                if row:
                                    assistant_msg_id = row['id']
                            finally:
                                db2.close()
                        except Exception:
                            pass

                        # 检测是否注入了长期记忆（通过比较 system_prompt 与原始值）
                        memory_injected = agent_id is not None and system_prompt != (custom_sys or '你是一个智能助手，请用简洁专业的中文回答用户问题。')
                        if refs:
                            # 有知识库时比较：去掉知识库部分后是否还有额外内容（记忆）
                            ref_text = '\n\n'.join(r['content'].strip() for r in refs)
                            kb_prompt = (
                                (custom_sys + '\n\n' if custom_sys else '') +
                                '请优先依据下面提供的【知识库资料】回答用户问题；'
                                '如果资料中找不到答案，请如实说明"知识库中未找到相关内容"，不要编造。\n\n'
                                '【知识库资料】\n' + ref_text + '\n【资料结束】'
                            )
                            memory_injected = system_prompt != kb_prompt
                        # 技能使用信息
                        skills_used = [{'key': s['key'], 'name': s['name']} for s in skills] if skills else []
                        meta = {
                            'done': True,
                            'conversation_id': conversation_id,
                            'is_new_conversation': is_new_conversation,
                            'model': model_name,
                            'provider': cfg['provider'],
                            'knowledge_used': kb_names,
                            'knowledge_matched': len(refs),
                            'skills_used': skills_used,
                            'file_used': file_names,
                            'total_tokens': total_tokens,
                            'thinking_chain': full_thinking,  # 完整思维链
                            'message_id': assistant_msg_id,  # 消息 ID（用于反馈）
                            'memory_used': memory_injected,  # 是否使用了长期记忆
                        }
                        yield f"data: {json.dumps(meta, ensure_ascii=False)}\n\n"

                        # 持久化对话历史
                        try:
                            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            if is_new_conversation:
                                title = _generate_title(message)
                                db2 = get_db()
                                try:
                                    cur2 = db2.cursor()
                                    cur2.execute(
                                        '''INSERT INTO dify_conversations
                                           (id, agent_id, title, system_prompt, knowledge_ids,
                                            model_provider, model_name, message_count, total_tokens,
                                            last_message_at, created_at, updated_at)
                                           VALUES (%s, %s, %s, %s, %s, %s, %s, 2, %s, %s, %s, %s)''',
                                        (conversation_id, agent_id, title, system_prompt,
                                         ','.join(knowledge_ids) if knowledge_ids else '',
                                         cfg['provider'], model_name, total_tokens, ts, ts, ts)
                                    )
                                    db2.commit()
                                finally:
                                    db2.close()
                            else:
                                _save_message(conversation_id, 'user', message, 0, cfg['provider'], model_name)
                                _update_conversation_stats(conversation_id, total_tokens)
                            # 保存含思维链的助手回复
                            _save_message_with_thinking(
                                conversation_id, 'assistant',
                                full_content,
                                thinking_chain=full_thinking,
                                tokens=total_tokens,
                                model_provider=cfg['provider'],
                                model_name=model_name
                            )
                            # 保存检索引用（3.1: 引用追踪）
                            if retriever_resources:
                                try:
                                    asst_id = None
                                    db3 = get_db()
                                    cur3 = db3.cursor()
                                    cur3.execute(
                                        r'''SELECT id FROM dify_messages
                                            WHERE conversation_id = %s AND role = 'assistant'
                                            ORDER BY created_at DESC LIMIT 1''',
                                        (conversation_id,))
                                    row3 = cur3.fetchone()
                                    if row3:
                                        asst_id = row3['id']
                                    db3.close()
                                    if asst_id:
                                        from engine.retrieval_resources import save_retriever_resources
                                        save_retriever_resources(asst_id, retriever_resources)
                                except Exception:
                                    pass
                            # 保存用户消息（新会话时也要保存）
                            if is_new_conversation:
                                _save_message(conversation_id, 'user', message, 0, cfg['provider'], model_name)
                            # 自动写入长期记忆（异步，不阻塞响应）
                            _auto_save_memory(agent_id, message, full_content)
                        except Exception:
                            pass  # 持久化失败不影响响应
                        return

                    if 'content' in chunk:
                        full_content += chunk['content']
                        yield f"data: {json.dumps({'content': chunk['content']}, ensure_ascii=False)}\n\n"

                    if 'usage' in chunk:
                        total_tokens = chunk['usage'].get('total_tokens', 0)

            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
            finally:
                # 注销任务
                _unregister_stream_task(task_id)

        return Response(generate(), mimetype='text/event-stream', headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        })

    @app.route('/api/chat/stream/<task_id>/stop', methods=['POST'])
    def chat_stream_stop(task_id):
        """
        停止正在进行的流式生成

        参数:
            task_id: 流式任务 ID（首次 SSE 事件中返回）

        响应: { code: 200, msg: '已停止' } 或 { code: 404, msg: '任务不存在' }
        """
        if not task_id:
            return jsonify(code=400, msg='缺少 task_id')
        success = _cancel_stream_task(task_id)
        if success:
            return jsonify(code=200, msg='已停止生成')
        return jsonify(code=404, msg='任务不存在或已结束')
