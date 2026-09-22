# -*- coding: utf-8 -*-
"""
工具标签引擎 —— 工具标签绑定 + 版本管理

职责:
    1. 管理工具标签（增删查）
    2. 工具版本字段管理
    3. 按标签筛选工具

设计:
    - tool_label_bindings 表按 (tool_type, tool_id, label) 唯一存储
    - 工具类型: builtin / api / workflow / mcp
    - 支持内置标签（builtin）和自定义标签（custom）
"""
import re
from typing import List, Dict, Optional, Tuple

from config import get_db
from models.tables import TOOL_LABEL_BINDINGS_TABLE_SQL


# 内置标签列表
BUILTIN_LABELS = [
    '搜索', '翻译', '图像', '音频', '视频', '代码', '数据', '办公',
    '通信', '开发', 'AI', '效率', '媒体', '网络', '文件', '数学',
]


def ensure_label_tables():
    """确保标签表存在"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(TOOL_LABEL_BINDINGS_TABLE_SQL)
        # 迁移：给已有工具表加 version 字段
        for table in ('tool_builtin_providers', 'tool_api_providers', 'tool_workflow_providers'):
            try:
                cur.execute(f'SHOW COLUMNS FROM {table} LIKE "version"')
                if not cur.fetchone():
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN version VARCHAR(20) DEFAULT '1.0.0' COMMENT '工具版本号'")
            except Exception:
                pass
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


# ============================================================
# 标签 CRUD
# ============================================================

def add_label(tool_type: str, tool_id: str, label: str,
              label_type: str = 'custom', created_by: str = None) -> Optional[Dict]:
    """
    为工具添加标签。

    参数:
        tool_type: 工具类型（builtin/api/workflow/mcp）
        tool_id: 工具 ID
        label: 标签名（最大 100 字符）
        label_type: 标签类型（builtin/custom）
        created_by: 创建者 ID

    返回:
        绑定信息或 None
    """
    if not tool_type or not tool_id or not label:
        return None
    label = label.strip()
    if not label or len(label) > 100:
        return None
    # 只允许中英文、数字、空格、连字符、下划线
    if not re.match(r'^[\w\s\-一-鿿]+$', label):
        return None

    ensure_label_tables()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            INSERT INTO tool_label_bindings (tool_type, tool_id, label, label_type, created_by)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE label_type = VALUES(label_type)
        """, (tool_type, tool_id, label, label_type, created_by))
        db.commit()
        return {'tool_type': tool_type, 'tool_id': tool_id, 'label': label, 'label_type': label_type}
    except Exception:
        db.rollback()
        return None
    finally:
        db.close()


def remove_label(tool_type: str, tool_id: str, label: str) -> bool:
    """移除工具标签"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            DELETE FROM tool_label_bindings
            WHERE tool_type = %s AND tool_id = %s AND label = %s
        """, (tool_type, tool_id, label))
        db.commit()
        return cur.rowcount > 0
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


def get_tool_labels(tool_type: str, tool_id: str) -> List[str]:
    """获取工具的标签列表"""
    ensure_label_tables()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            SELECT label FROM tool_label_bindings
            WHERE tool_type = %s AND tool_id = %s
            ORDER BY created_at
        """, (tool_type, tool_id))
        return [r['label'] for r in cur.fetchall()]
    finally:
        db.close()


def get_tools_by_label(tool_type: str = None, label: str = None) -> List[Dict]:
    """
    按标签查询工具。

    参数:
        tool_type: 可选，限定工具类型
        label: 可选，限定标签名

    返回:
        [{tool_type, tool_id, label, label_type}, ...]
    """
    ensure_label_tables()
    db = get_db()
    try:
        cur = db.cursor()
        conditions = []
        params = []
        if tool_type:
            conditions.append('tool_type = %s')
            params.append(tool_type)
        if label:
            conditions.append('label = %s')
            params.append(label)
        where = ' AND '.join(conditions) if conditions else '1=1'
        cur.execute(f"""
            SELECT tool_type, tool_id, label, label_type, created_at
            FROM tool_label_bindings
            WHERE {where}
            ORDER BY created_at DESC
        """, params)
        return [{
            'tool_type': r['tool_type'],
            'tool_id': r['tool_id'],
            'label': r['label'],
            'label_type': r['label_type'],
        } for r in cur.fetchall()]
    finally:
        db.close()


def list_all_labels() -> List[Dict]:
    """列出所有标签（去重）及使用次数"""
    ensure_label_tables()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            SELECT label, label_type, COUNT(*) as tool_count
            FROM tool_label_bindings
            GROUP BY label, label_type
            ORDER BY tool_count DESC, label
        """)
        return [{
            'label': r['label'],
            'label_type': r['label_type'],
            'tool_count': r['tool_count'],
        } for r in cur.fetchall()]
    finally:
        db.close()


def batch_set_labels(tool_type: str, tool_id: str, labels: List[str],
                     label_type: str = 'custom', created_by: str = None) -> int:
    """
    批量设置工具标签（覆盖式：先删后加）。

    参数:
        tool_type: 工具类型
        tool_id: 工具 ID
        labels: 标签列表
        label_type: 标签类型
        created_by: 创建者 ID

    返回:
        成功添加的标签数
    """
    # 先删除旧标签
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            DELETE FROM tool_label_bindings
            WHERE tool_type = %s AND tool_id = %s
        """, (tool_type, tool_id))
        db.commit()
    finally:
        db.close()

    # 添加新标签
    n = 0
    for label in labels:
        if add_label(tool_type, tool_id, label.strip(), label_type, created_by):
            n += 1
    return n


# ============================================================
# 工具版本管理
# ============================================================

def set_tool_version(tool_type: str, tool_id: str, version: str) -> bool:
    """
    设置工具版本号。

    参数:
        tool_type: 工具类型
        tool_id: 工具 ID
        version: 版本号（如 1.0.0）

    返回:
        是否成功
    """
    table_map = {
        'builtin': 'tool_builtin_providers',
        'api': 'tool_api_providers',
        'workflow': 'tool_workflow_providers',
    }
    table = table_map.get(tool_type)
    if not table:
        return False

    ensure_label_tables()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(f'UPDATE {table} SET version = %s WHERE id = %s', (version, tool_id))
        db.commit()
        return cur.rowcount > 0
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


def get_tool_version(tool_type: str, tool_id: str) -> Optional[str]:
    """获取工具版本号"""
    table_map = {
        'builtin': 'tool_builtin_providers',
        'api': 'tool_api_providers',
        'workflow': 'tool_workflow_providers',
    }
    table = table_map.get(tool_type)
    if not table:
        return None

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(f'SELECT version FROM {table} WHERE id = %s', (tool_id,))
        row = cur.fetchone()
        return row['version'] if row else None
    finally:
        db.close()


# ============================================================
# 工具筛选（标签 + 版本 + 关键字）
# ============================================================

def filter_tools(tool_type: str = None, label: str = None,
                 keyword: str = None) -> List[Dict]:
    """
    综合筛选工具。

    参数:
        tool_type: 工具类型筛选
        label: 标签筛选
        keyword: 关键字筛选（匹配名称/描述）

    返回:
        工具列表（含标签和版本信息）
    """
    ensure_label_tables()
    db = get_db()
    try:
        cur = db.cursor()

        # 先按标签获取 tool_id 集合
        label_filtered_ids = None
        if label:
            cur.execute("""
                SELECT tool_type, tool_id FROM tool_label_bindings WHERE label = %s
            """, (label,))
            label_filtered_ids = {(r['tool_type'], r['tool_id']) for r in cur.fetchall()}

        results = []

        # builtin 工具
        if not tool_type or tool_type == 'builtin':
            cur.execute("SELECT id, provider_name, provider_label, description, category, version, status FROM tool_builtin_providers WHERE status = 'active'")
            for r in cur.fetchall():
                if label_filtered_ids and ('builtin', r['id']) not in label_filtered_ids:
                    continue
                if keyword and keyword.lower() not in (r['provider_name'] + (r['description'] or '')).lower():
                    continue
                labels = get_tool_labels('builtin', r['id'])
                results.append({
                    'tool_type': 'builtin',
                    'tool_id': r['id'],
                    'name': r['provider_label'],
                    'description': r['description'] or '',
                    'category': r['category'],
                    'version': r['version'] or '1.0.0',
                    'labels': labels,
                    'status': r['status'],
                })

        # api 工具
        if not tool_type or tool_type == 'api':
            cur.execute("SELECT id, name, description, version, status FROM tool_api_providers WHERE status = 'active'")
            for r in cur.fetchall():
                if label_filtered_ids and ('api', r['id']) not in label_filtered_ids:
                    continue
                if keyword and keyword.lower() not in (r['name'] + (r['description'] or '')).lower():
                    continue
                labels = get_tool_labels('api', r['id'])
                results.append({
                    'tool_type': 'api',
                    'tool_id': r['id'],
                    'name': r['name'],
                    'description': r['description'] or '',
                    'category': 'custom',
                    'version': r['version'] or '1.0.0',
                    'labels': labels,
                    'status': r['status'],
                })

        # workflow 工具
        if not tool_type or tool_type == 'workflow':
            cur.execute("SELECT id, name, description, version, status FROM tool_workflow_providers WHERE status = 'active'")
            for r in cur.fetchall():
                if label_filtered_ids and ('workflow', r['id']) not in label_filtered_ids:
                    continue
                if keyword and keyword.lower() not in (r['name'] + (r['description'] or '')).lower():
                    continue
                labels = get_tool_labels('workflow', r['id'])
                results.append({
                    'tool_type': 'workflow',
                    'tool_id': r['id'],
                    'name': r['name'],
                    'description': r['description'] or '',
                    'category': 'workflow',
                    'version': r['version'] or '1.0.0',
                    'labels': labels,
                    'status': r['status'],
                })

        return results
    finally:
        db.close()
