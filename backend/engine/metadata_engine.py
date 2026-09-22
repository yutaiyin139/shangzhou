# -*- coding: utf-8 -*-
"""
知识库元数据引擎 —— 数据集级别的结构化元数据管理 + 分段绑定 + 检索过滤

职责:
    1. 元数据字段 CRUD（dataset_metadatas 表）
    2. 分段-元数据绑定 CRUD（dataset_metadata_bindings 表）
    3. 检索过滤（按 metadata 条件过滤分段）

设计要点:
    - 元数据字段在数据集级别定义（名称/类型/说明）
    - 分段通过绑定表关联元数据字段和值
    - 检索时支持下推过滤到 SQL WHERE 条件
    - 兼容 dify_document_segments.metadata JSON 字段（冗余存储，加速查询）
"""
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional

from config import get_db
from models.tables import DATASET_METADATAS_TABLE_SQL, DATASET_METADATA_BINDINGS_TABLE_SQL
from utils.logger import get_logger

logger = get_logger(__name__)


def ensure_metadata_tables():
    """确保元数据相关表已创建"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(DATASET_METADATAS_TABLE_SQL)
        cur.execute(DATASET_METADATA_BINDINGS_TABLE_SQL)
        db.commit()
    except Exception:
        # 表已存在等情况属正常幂等；仅记一次调试日志，不中断业务
        logger.debug('确保元数据表已存在时忽略异常（可能表已存在）', exc_info=True)
    finally:
        db.close()


# ============================================================
# 元数据字段 CRUD
# ============================================================

def list_metadata_fields(dataset_id: str) -> List[Dict]:
    """列出数据集的所有元数据字段"""
    ensure_metadata_tables()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            'SELECT * FROM dataset_metadatas WHERE dataset_id = %s ORDER BY name ASC',
            (dataset_id,))
        return [dict(r) for r in cur.fetchall()]
    except Exception:
        logger.exception('列出元数据字段失败 (dataset_id=%s)，返回空列表', dataset_id)
        return []
    finally:
        db.close()


def create_metadata_field(dataset_id: str, name: str, field_type: str = 'string',
                          description: str = '', tenant_id: str = '') -> Optional[Dict]:
    """
    创建元数据字段。

    参数:
        dataset_id: 数据集 ID
        name: 字段名（如：部门、年份）
        field_type: 数据类型（string/number/date/enum）
        description: 字段说明
        tenant_id: 租户 ID

    返回:
        创建的字段 dict；失败返回 None
    """
    name = (name or '').strip()
    if not name:
        return None
    if field_type not in ('string', 'number', 'date', 'enum'):
        field_type = 'string'
    if len(name) > 100:
        return None

    ensure_metadata_tables()
    field_id = str(uuid.uuid4())
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            'INSERT INTO dataset_metadatas (id, dataset_id, tenant_id, name, type, description, created_at, updated_at)'
            ' VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
            (field_id, dataset_id, tenant_id, name, field_type, description, now, now))
        db.commit()
        return {
            'id': field_id,
            'dataset_id': dataset_id,
            'name': name,
            'type': field_type,
            'description': description,
            'created_at': now,
            'updated_at': now,
        }
    except Exception:
        db.rollback()
        logger.exception('创建元数据字段失败 (dataset_id=%s, name=%s)', dataset_id, name)
        return None
    finally:
        db.close()


def update_metadata_field(field_id: str, dataset_id: str,
                          name: str = None, field_type: str = None,
                          description: str = None) -> bool:
    """更新元数据字段"""
    sets, params = [], []
    if name is not None:
        name = name.strip()
        if not name or len(name) > 100:
            return False
        sets.append('name = %s')
        params.append(name)
    if field_type is not None:
        if field_type not in ('string', 'number', 'date', 'enum'):
            return False
        sets.append('type = %s')
        params.append(field_type)
    if description is not None:
        sets.append('description = %s')
        params.append(description)
    if not sets:
        return False

    sets.append('updated_at = %s')
    params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    params.extend([field_id, dataset_id])

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            'UPDATE dataset_metadatas SET ' + ', '.join(sets) + ' WHERE id = %s AND dataset_id = %s',
            params)
        db.commit()
        return cur.rowcount > 0
    except Exception:
        db.rollback()
        logger.exception('更新元数据字段失败 (field_id=%s, dataset_id=%s)', field_id, dataset_id)
        return False
    finally:
        db.close()


def delete_metadata_field(field_id: str, dataset_id: str) -> bool:
    """删除元数据字段（级联删除绑定）"""
    db = get_db()
    try:
        cur = db.cursor()
        # 先删除绑定
        cur.execute('DELETE FROM dataset_metadata_bindings WHERE metadata_id = %s', (field_id,))
        # 再删除字段
        cur.execute('DELETE FROM dataset_metadatas WHERE id = %s AND dataset_id = %s', (field_id, dataset_id))
        db.commit()
        return cur.rowcount > 0
    except Exception:
        db.rollback()
        logger.exception('删除元数据字段失败 (field_id=%s, dataset_id=%s)', field_id, dataset_id)
        return False
    finally:
        db.close()


# ============================================================
# 分段-元数据绑定 CRUD
# ============================================================

def bind_segment_metadata(dataset_id: str, metadata_id: str, segment_id: str,
                          value: str) -> Optional[Dict]:
    """
    绑定分段与元数据值。

    参数:
        dataset_id: 数据集 ID
        metadata_id: 元数据字段 ID
        segment_id: 分段 ID
        value: 元数据值

    返回:
        绑定记录 dict；失败返回 None
    """
    value = str(value or '').strip()
    if not value or len(value) > 500:
        return None

    ensure_metadata_tables()
    binding_id = str(uuid.uuid4())
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    db = get_db()
    try:
        cur = db.cursor()
        # 验证元数据字段属于该数据集
        cur.execute('SELECT id FROM dataset_metadatas WHERE id = %s AND dataset_id = %s', (metadata_id, dataset_id))
        if not cur.fetchone():
            return None
        # 验证分段属于该数据集
        cur.execute('SELECT id FROM dify_document_segments WHERE id = %s AND dataset_id = %s', (segment_id, dataset_id))
        if not cur.fetchone():
            return None
        # UPSERT
        cur.execute(
            'INSERT INTO dataset_metadata_bindings (id, dataset_id, metadata_id, segment_id, value, created_at)'
            ' VALUES (%s, %s, %s, %s, %s, %s)'
            ' ON DUPLICATE KEY UPDATE value = VALUES(value)',
            (binding_id, dataset_id, metadata_id, segment_id, value, now))
        db.commit()

        # 同步更新 dify_document_segments.metadata JSON 字段（冗余存储）
        _sync_segment_metadata_json(segment_id)

        return {'id': binding_id, 'dataset_id': dataset_id, 'metadata_id': metadata_id,
                'segment_id': segment_id, 'value': value}
    except Exception:
        db.rollback()
        logger.exception('绑定分段元数据失败 (dataset_id=%s, metadata_id=%s, segment_id=%s)', dataset_id, metadata_id, segment_id)
        return None
    finally:
        db.close()


def unbind_segment_metadata(dataset_id: str, metadata_id: str, segment_id: str) -> bool:
    """解绑分段与元数据"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            'DELETE FROM dataset_metadata_bindings WHERE metadata_id = %s AND segment_id = %s AND dataset_id = %s',
            (metadata_id, segment_id, dataset_id))
        db.commit()
        ok = cur.rowcount > 0
        if ok:
            _sync_segment_metadata_json(segment_id)
        return ok
    except Exception:
        db.rollback()
        logger.exception('解绑分段元数据失败 (dataset_id=%s, metadata_id=%s, segment_id=%s)', dataset_id, metadata_id, segment_id)
        return False
    finally:
        db.close()


def get_segment_metadata(segment_id: str) -> Dict[str, str]:
    """
    获取分段的所有元数据绑定。
    返回: {metadata_name: value, ...}
    """
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            'SELECT m.name, b.value FROM dataset_metadata_bindings b'
            ' JOIN dataset_metadatas m ON b.metadata_id = m.id'
            ' WHERE b.segment_id = %s',
            (segment_id,))
        return {r['name']: r['value'] for r in cur.fetchall()}
    except Exception:
        logger.exception('获取分段元数据绑定失败 (segment_id=%s)，返回空字典', segment_id)
        return {}
    finally:
        db.close()


def _sync_segment_metadata_json(segment_id: str):
    """将绑定表中的元数据同步到 dify_document_segments.metadata JSON 字段"""
    try:
        metadata = get_segment_metadata(segment_id)
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                'UPDATE dify_document_segments SET metadata = %s WHERE id = %s',
                (json.dumps(metadata, ensure_ascii=False) if metadata else None, segment_id))
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.exception('同步分段 metadata JSON 字段失败 (segment_id=%s)', segment_id)


# ============================================================
# 检索过滤
# ============================================================

def build_metadata_filter_sql(dataset_id: str, metadata_filters: List[Dict]) -> tuple:
    """
    根据元数据过滤条件构建 SQL WHERE 片段。

    参数:
        dataset_id: 数据集 ID
        metadata_filters: 过滤条件列表 [{name, value, operator}]，operator 支持 eq/ne/contains/gt/lt

    返回:
        (where_sql, params) 元组
    """
    if not metadata_filters:
        return '', []

    conditions = []
    params = []

    for f in metadata_filters:
        name = (f.get('name') or '').strip()
        value = str(f.get('value', '')).strip()
        op = f.get('operator', 'eq')

        if not name:
            continue

        # 查找元数据字段 ID
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                'SELECT id FROM dataset_metadatas WHERE dataset_id = %s AND name = %s',
                (dataset_id, name))
            row = cur.fetchone()
            if not row:
                continue
            metadata_id = row['id']
        finally:
            db.close()

        if op == 'eq':
            conditions.append(
                'EXISTS (SELECT 1 FROM dataset_metadata_bindings b'
                ' WHERE b.segment_id = s.id AND b.metadata_id = %s AND b.value = %s)')
            params.extend([metadata_id, value])
        elif op == 'ne':
            conditions.append(
                'NOT EXISTS (SELECT 1 FROM dataset_metadata_bindings b'
                ' WHERE b.segment_id = s.id AND b.metadata_id = %s AND b.value = %s)')
            params.extend([metadata_id, value])
        elif op == 'contains':
            conditions.append(
                'EXISTS (SELECT 1 FROM dataset_metadata_bindings b'
                ' WHERE b.segment_id = s.id AND b.metadata_id = %s AND b.value LIKE %s)')
            params.extend([metadata_id, f'%{value}%'])
        elif op in ('gt', 'lt', 'gte', 'lte'):
            sql_op = {'gt': '>', 'lt': '<', 'gte': '>=', 'lte': '<='}[op]
            conditions.append(
                f'EXISTS (SELECT 1 FROM dataset_metadata_bindings b'
                f' WHERE b.segment_id = s.id AND b.metadata_id = %s AND CAST(b.value AS DECIMAL) {sql_op} %s)')
            params.extend([metadata_id, value])

    if not conditions:
        return '', []

    return ' AND ' + ' AND '.join(conditions), params


def filter_segments_by_metadata(dataset_id: str, segment_ids: List[str],
                                metadata_filters: List[Dict]) -> List[str]:
    """
    按元数据条件过滤分段 ID 列表。

    参数:
        dataset_id: 数据集 ID
        segment_ids: 待过滤的分段 ID 列表
        metadata_filters: 过滤条件

    返回:
        过滤后的分段 ID 列表
    """
    if not segment_ids or not metadata_filters:
        return segment_ids or []

    where_sql, params = build_metadata_filter_sql(dataset_id, metadata_filters)
    if not where_sql:
        return segment_ids

    db = get_db()
    try:
        cur = db.cursor()
        fmt = ','.join(['%s'] * len(segment_ids))
        cur.execute(
            f'SELECT s.id FROM dify_document_segments s'
            f' WHERE s.id IN ({fmt})' + where_sql,
            segment_ids + params)
        return [r['id'] for r in cur.fetchall()]
    except Exception:
        logger.exception('按元数据过滤分段失败 (dataset_id=%s)，回退为不过滤原分段列表', dataset_id)
        return segment_ids
    finally:
        db.close()
