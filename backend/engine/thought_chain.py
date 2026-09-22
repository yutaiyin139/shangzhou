# -*- coding: utf-8 -*-
"""
Agent 思考链持久化 —— 将 Agent 节点的 ReAct 推理过程逐步落库

职责:
    1. 保存思考链条目到 message_agent_thoughts 表
    2. 按 message_id 查询思考链
    3. 工作流运行时从 outputs 提取并持久化

设计要点:
    - 表结构对齐 Dify message_agent_thoughts（id/message_id/position/thought/tool_name/tool_input/tool_output/observation）
    - 思考链与消息分离存储，通过 message_id 关联
    - 支持批量写入（一次 Agent 调用可能产生多条思考记录）
"""
import json
from datetime import datetime
from typing import List, Dict, Optional

from config import get_db
from models.tables import MESSAGE_AGENT_THOUGHTS_TABLE_SQL


def ensure_thoughts_table():
    """确保 message_agent_thoughts 表存在"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(MESSAGE_AGENT_THOUGHTS_TABLE_SQL)
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


def save_thought_chain(message_id: str, thought_chain: List[Dict]) -> int:
    """
    保存思考链条目到数据库。

    参数:
        message_id: 关联的消息 ID（dify_messages.id）
        thought_chain: 思考链列表，每项包含 position/thought/tool_name/tool_input/tool_output/observation

    返回:
        保存的条数
    """
    if not message_id or not thought_chain:
        return 0

    ensure_thoughts_table()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    db = get_db()
    try:
        cur = db.cursor()
        n = 0
        for entry in thought_chain:
            if not isinstance(entry, dict):
                continue
            cur.execute(
                'INSERT INTO message_agent_thoughts'
                ' (message_id, position, thought, tool_name, tool_input, tool_output, observation, created_at)'
                ' VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                (
                    message_id,
                    entry.get('position', n),
                    (entry.get('thought') or '')[:4000],
                    entry.get('tool_name', '')[:200],
                    (entry.get('tool_input') or '')[:2000] if isinstance(entry.get('tool_input'), str)
                        else json.dumps(entry.get('tool_input'), ensure_ascii=False)[:2000],
                    (entry.get('tool_output') or '')[:2000],
                    (entry.get('observation') or '')[:2000],
                    now,
                ))
            n += 1
        db.commit()
        return n
    except Exception:
        db.rollback()
        return 0
    finally:
        db.close()


def get_thought_chain(message_id: str) -> List[Dict]:
    """
    按消息 ID 查询思考链。

    参数:
        message_id: 消息 ID

    返回:
        思考链条目列表，按 position 升序
    """
    if not message_id:
        return []
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            'SELECT * FROM message_agent_thoughts WHERE message_id = %s ORDER BY position ASC',
            (message_id,))
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        db.close()


def get_thought_chain_for_run(run_id: str) -> List[Dict]:
    """
    按工作流运行 ID 查询所有相关思考链（通过 dify_messages 关联）。

    参数:
        run_id: 工作流运行 ID

    返回:
        思考链条目列表
    """
    if not run_id:
        return []
    db = get_db()
    try:
        cur = db.cursor()
        # 先查找该运行产生的消息
        cur.execute(
            "SELECT id FROM dify_messages WHERE metadata LIKE %s",
            (f'%"run_id": "{run_id}"%',))
        msg_rows = cur.fetchall()
        msg_ids = [r['id'] for r in msg_rows]
        if not msg_ids:
            return []
        # 查询这些消息的思考链
        fmt = ','.join(['%s'] * len(msg_ids))
        cur.execute(
            f'SELECT * FROM message_agent_thoughts WHERE message_id IN ({fmt}) ORDER BY message_id, position ASC',
            msg_ids)
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        db.close()


def delete_thought_chain(message_id: str) -> int:
    """删除指定消息的思考链（消息删除时级联清理）"""
    if not message_id:
        return 0
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('DELETE FROM message_agent_thoughts WHERE message_id = %s', (message_id,))
        db.commit()
        return cur.rowcount
    except Exception:
        db.rollback()
        return 0
    finally:
        db.close()
