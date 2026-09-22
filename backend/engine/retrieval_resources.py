# -*- coding: utf-8 -*-
"""
知识库引用追踪 —— 检索结果的结构化引用记录持久化

职责:
    1. 保存检索引用到 dataset_retriever_resources 表
    2. 按消息 ID 查询引用列表
    3. 与消息删除级联清理

设计要点:
    - 表结构对齐 Dify dataset_retriever_resources
    - 引用与消息分离存储，通过 message_id 关联
    - 支持批量写入（一次检索可能产生多条引用）
"""
import json
from datetime import datetime
from typing import List, Dict

from config import get_db
from models.tables import DATASET_RETRIEVER_RESOURCES_TABLE_SQL


def ensure_retriever_resources_table():
    """确保 dataset_retriever_resources 表存在"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(DATASET_RETRIEVER_RESOURCES_TABLE_SQL)
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


def save_retriever_resources(message_id: str, resources: List[Dict]) -> int:
    """
    保存检索引用到数据库。

    参数:
        message_id: 关联的消息 ID（dify_messages.id）
        resources: 引用列表，每项包含 segment_id/dataset_id/document_id/document_name/content/score/position

    返回:
        保存的条数
    """
    if not message_id or not resources:
        return 0

    ensure_retriever_resources_table()
    db = get_db()
    try:
        cur = db.cursor()
        # 先删除旧的引用（避免重复）
        cur.execute('DELETE FROM dataset_retriever_resources WHERE message_id = %s', (message_id,))
        n = 0
        for r in resources:
            if not isinstance(r, dict):
                continue
            cur.execute(
                'INSERT INTO dataset_retriever_resources'
                ' (message_id, dataset_id, document_id, segment_id, document_name, segment_content, score, position, created_at)'
                ' VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (
                    message_id,
                    r.get('dataset_id', ''),
                    r.get('document_id', ''),
                    r.get('segment_id', ''),
                    r.get('document_name', '')[:255],
                    (r.get('content') or '')[:1000],
                    float(r.get('score', 0)),
                    int(r.get('position', n)),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                ))
            n += 1
        db.commit()
        return n
    except Exception:
        db.rollback()
        return 0
    finally:
        db.close()


def get_retriever_resources(message_id: str) -> List[Dict]:
    """
    按消息 ID 查询检索引用。

    参数:
        message_id: 消息 ID

    返回:
        引用列表，按 position 升序
    """
    if not message_id:
        return []
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            'SELECT * FROM dataset_retriever_resources WHERE message_id = %s ORDER BY position ASC',
            (message_id,))
        return [dict(r) for r in cur.fetchall()]
    except Exception:
        return []
    finally:
        db.close()


def delete_retriever_resources(message_id: str) -> int:
    """删除指定消息的检索引用（消息删除时级联清理）"""
    if not message_id:
        return 0
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('DELETE FROM dataset_retriever_resources WHERE message_id = %s', (message_id,))
        db.commit()
        return cur.rowcount
    except Exception:
        db.rollback()
        return 0
    finally:
        db.close()
