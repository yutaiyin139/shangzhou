# -*- coding: utf-8 -*-
"""
外部知识 API 引擎 —— 将外部检索 API 结果并入召回

职责:
    1. 管理外部知识 API 配置（CRUD）
    2. 管理数据集与外部 API 的绑定
    3. 检索时调用外部 API 并将结果并入本地召回

外部 API 协议（Dify 兼容）:
    请求:
        POST {endpoint_url}
        Headers: Authorization: Bearer {api_key}（可选）
        Body: {
            "query": "用户查询",
            "top_k": 5,
            "metadata": {}
        }

    响应:
        {
            "results": [
                {
                    "content": "分段内容",
                    "score": 0.95,
                    "title": "文档标题",
                    "metadata": {}
                }
            ]
        }
"""
import json
import uuid
import urllib.request
import urllib.error
import socket
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from config import get_db
from models.tables import EXTERNAL_KNOWLEDGE_APIS_TABLE_SQL, EXTERNAL_KNOWLEDGE_BINDINGS_TABLE_SQL


def ensure_external_knowledge_tables():
    """确保外部知识 API 表存在"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(EXTERNAL_KNOWLEDGE_APIS_TABLE_SQL)
        cur.execute(EXTERNAL_KNOWLEDGE_BINDINGS_TABLE_SQL)
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


# ============================================================
# 外部 API CRUD
# ============================================================

def list_external_apis(tenant_id: str = None) -> List[Dict]:
    """列出所有外部知识 API"""
    ensure_external_knowledge_tables()
    db = get_db()
    try:
        cur = db.cursor()
        if tenant_id:
            cur.execute('SELECT * FROM external_knowledge_apis WHERE tenant_id = %s ORDER BY created_at DESC', (tenant_id,))
        else:
            cur.execute('SELECT * FROM external_knowledge_apis ORDER BY created_at DESC')
        rows = cur.fetchall()
        return [{
            'id': r['id'],
            'name': r['name'],
            'description': r['description'] or '',
            'endpoint_url': r['endpoint_url'],
            'api_key': r['api_key'] or '',
            'timeout': r['timeout'] or 30,
            'status': bool(r['status']),
            'created_at': r['created_at'].isoformat() if r['created_at'] else '',
            'updated_at': r['updated_at'].isoformat() if r['updated_at'] else '',
        } for r in rows]
    finally:
        db.close()


def create_external_api(name: str, endpoint_url: str, description: str = '',
                        api_key: str = '', timeout: int = 30,
                        tenant_id: str = '') -> Optional[Dict]:
    """创建外部知识 API"""
    if not name or not endpoint_url:
        return None
    ensure_external_knowledge_tables()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            INSERT INTO external_knowledge_apis
            (tenant_id, name, description, endpoint_url, api_key, timeout)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (tenant_id, name, description, endpoint_url, api_key or '', timeout))
        db.commit()
        new_id = cur.lastrowid
        return {'id': new_id, 'name': name, 'endpoint_url': endpoint_url}
    except Exception as e:
        db.rollback()
        return None
    finally:
        db.close()


def update_external_api(api_id: int, name: str = None, endpoint_url: str = None,
                        description: str = None, api_key: str = None,
                        timeout: int = None, status: int = None) -> bool:
    """更新外部知识 API"""
    db = get_db()
    try:
        cur = db.cursor()
        updates = []
        params = []
        if name is not None:
            updates.append('name = %s')
            params.append(name)
        if endpoint_url is not None:
            updates.append('endpoint_url = %s')
            params.append(endpoint_url)
        if description is not None:
            updates.append('description = %s')
            params.append(description)
        if api_key is not None:
            updates.append('api_key = %s')
            params.append(api_key)
        if timeout is not None:
            updates.append('timeout = %s')
            params.append(timeout)
        if status is not None:
            updates.append('status = %s')
            params.append(status)
        if not updates:
            return False
        params.append(api_id)
        cur.execute(f'UPDATE external_knowledge_apis SET {", ".join(updates)} WHERE id = %s', params)
        db.commit()
        return cur.rowcount > 0
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


def delete_external_api(api_id: int) -> bool:
    """删除外部知识 API（级联删除绑定）"""
    db = get_db()
    try:
        cur = db.cursor()
        # 删除绑定
        cur.execute('DELETE FROM external_knowledge_bindings WHERE external_api_id = %s', (api_id,))
        # 删除 API
        cur.execute('DELETE FROM external_knowledge_apis WHERE id = %s', (api_id,))
        db.commit()
        return cur.rowcount > 0
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


def get_external_api(api_id: int) -> Optional[Dict]:
    """获取外部知识 API 详情"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('SELECT * FROM external_knowledge_apis WHERE id = %s', (api_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            'id': row['id'],
            'name': row['name'],
            'description': row['description'] or '',
            'endpoint_url': row['endpoint_url'],
            'api_key': row['api_key'] or '',
            'timeout': row['timeout'] or 30,
            'status': bool(row['status']),
            'created_at': row['created_at'].isoformat() if row['created_at'] else '',
        }
    finally:
        db.close()


# ============================================================
# 绑定管理
# ============================================================

def bind_external_api(dataset_id: str, external_api_id: int) -> Optional[Dict]:
    """将外部 API 绑定到数据集"""
    ensure_external_knowledge_tables()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            INSERT INTO external_knowledge_bindings (dataset_id, external_api_id)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE external_api_id = external_api_id
        """, (dataset_id, external_api_id))
        db.commit()
        return {'dataset_id': dataset_id, 'external_api_id': external_api_id}
    except Exception:
        db.rollback()
        return None
    finally:
        db.close()


def unbind_external_api(dataset_id: str, external_api_id: int = None) -> bool:
    """解绑外部 API（external_api_id 为 None 时解绑所有）"""
    db = get_db()
    try:
        cur = db.cursor()
        if external_api_id:
            cur.execute('DELETE FROM external_knowledge_bindings WHERE dataset_id = %s AND external_api_id = %s',
                        (dataset_id, external_api_id))
        else:
            cur.execute('DELETE FROM external_knowledge_bindings WHERE dataset_id = %s', (dataset_id,))
        db.commit()
        return cur.rowcount > 0
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


def get_dataset_external_apis(dataset_id: str) -> List[Dict]:
    """获取数据集绑定的所有外部 API"""
    ensure_external_knowledge_tables()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            SELECT ek.* FROM external_knowledge_apis ek
            JOIN external_knowledge_bindings ekb ON ek.id = ekb.external_api_id
            WHERE ekb.dataset_id = %s AND ek.status = 1
        """, (dataset_id,))
        rows = cur.fetchall()
        return [{
            'id': r['id'],
            'name': r['name'],
            'endpoint_url': r['endpoint_url'],
            'api_key': r['api_key'] or '',
            'timeout': r['timeout'] or 30,
        } for r in rows]
    finally:
        db.close()


# ============================================================
# 检索代理
# ============================================================

def call_external_api(api_config: Dict, query: str, top_k: int = 5) -> Tuple[List[Dict], Optional[str]]:
    """
    调用外部检索 API。

    参数:
        api_config: API 配置 {endpoint_url, api_key, timeout, name}
        query: 查询文本
        top_k: 返回结果数

    返回:
        (结果列表, 错误信息)
    """
    endpoint = api_config.get('endpoint_url', '')
    api_key = api_config.get('api_key', '')
    timeout = api_config.get('timeout', 30)
    api_name = api_config.get('name', f'API-{api_config.get("id", "")}')

    if not endpoint:
        return [], 'endpoint_url 为空'

    payload = json.dumps({
        'query': query,
        'top_k': top_k,
        'metadata': {},
    }).encode('utf-8')

    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    req = urllib.request.Request(endpoint, data=payload, headers=headers, method='POST')

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except socket.timeout:
        return [], f'外部 API 超时（{timeout}秒）: {api_name}'
    except urllib.error.HTTPError as e:
        return [], f'外部 API HTTP {e.code}: {api_name}'
    except urllib.error.URLError as e:
        return [], f'外部 API 连接失败: {api_name} - {e.reason}'
    except json.JSONDecodeError:
        return [], f'外部 API 返回非 JSON: {api_name}'
    except Exception as e:
        return [], f'外部 API 调用失败: {api_name} - {str(e)[:200]}'

    # 解析结果（兼容多种格式）
    results = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        # Dify 格式: {records: [...]}
        items = data.get('records', data.get('results', data.get('data', [])))
    else:
        return [], f'外部 API 返回格式不支持: {api_name}'

    if not isinstance(items, list):
        return [], f'外部 API 返回格式不支持: {api_name}'

    for item in items[:top_k]:
        if not isinstance(item, dict):
            continue
        content = item.get('content', item.get('text', item.get('segment', '')))
        if not content:
            continue
        score = float(item.get('score', item.get('relevance', 0.5)))
        # 归一化分数到 0-1
        score = max(0.0, min(1.0, score))
        results.append({
            'id': str(uuid.uuid4()),
            'content': str(content),
            'score': score,
            'dataset_id': '',
            'document_id': '',
            'document_name': item.get('title', api_name),
            'is_external': True,
            'external_api_name': api_name,
        })

    return results, None


def retrieve_external_knowledge(dataset_ids: List[str], query: str,
                                top_k: int = 5) -> Tuple[List[Dict], List[str]]:
    """
    对所有绑定了外部 API 的数据集执行外部检索。

    参数:
        dataset_ids: 数据集 ID 列表
        query: 查询文本
        top_k: 每个数据集返回的最大结果数

    返回:
        (合并后的外部结果列表, 错误信息列表)
    """
    all_results = []
    errors = []

    for ds_id in dataset_ids:
        apis = get_dataset_external_apis(ds_id)
        for api in apis:
            results, error = call_external_api(api, query, top_k=top_k)
            if error:
                errors.append(error)
            for r in results:
                r['dataset_id'] = ds_id
            all_results.extend(results)

    # 按分数排序
    all_results.sort(key=lambda x: -x.get('score', 0))
    return all_results, errors
