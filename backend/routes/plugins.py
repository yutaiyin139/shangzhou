# -*- coding: utf-8 -*-
"""插件市场路由 —— 插件发布、安装、管理"""
import json
import uuid
from flask import Blueprint, request, jsonify
from datetime import datetime

from utils.helpers import _safe_uid

from models.tables import PLUGINS_TABLE_SQL, PLUGIN_INSTALLS_TABLE_SQL
from config import get_db
from utils.auth import login_required

bp = Blueprint('plugins', __name__)

# ============================================================
# 初始化表
# ============================================================

def init_tables():
    """初始化插件相关表"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(PLUGINS_TABLE_SQL)
        cur.execute(PLUGIN_INSTALLS_TABLE_SQL)
        db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()

init_tables()

# ============================================================
# 辅助函数
# ============================================================

def _row_to_plugin(row):
    """数据库行转插件字典"""
    return {
        'id': row['id'],
        'name': row['name'],
        'plugin_type': row['plugin_type'],
        'description': row['description'] or '',
        'version': row['version'] or '1.0.0',
        'author_id': row['author_id'] or '',
        'author_name': row['author_name'] or '',
        'icon': row['icon'] or '🧩',
        'icon_background': row['icon_background'] or '#F5E8FF',
        'category': row['category'] or 'utility',
        'tags': json.loads(row['tags_json'] or '[]'),
        'package': json.loads(row['package_json'] or '{}'),
        'manifest': json.loads(row['manifest_json'] or '{}'),
        'download_url': row['download_url'] or '',
        'file_size': row['file_size'] or 0,
        'checksum': row['checksum'] or '',
        'is_public': bool(row['is_public']),
        'is_official': bool(row['is_official']),
        'status': row['status'] or 'active',
        'download_count': row['download_count'] or 0,
        'rating': float(row['rating'] or 0),
        'rating_count': row['rating_count'] or 0,
        'created_at': str(row['created_at']),
        'updated_at': str(row['updated_at']),
    }

def _get_plugin_by_id(plugin_id):
    """根据 ID 获取插件"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT * FROM plugins WHERE id = %s', (plugin_id,))
        return cur.fetchone()
    finally:
        db.close()

# ============================================================
# 插件 CRUD
# ============================================================

@bp.route('/api/plugins', methods=['GET'])
@login_required
def list_plugins():
    """列出插件（支持搜索/分类/分页/排序）"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 12)), 50)
    plugin_type = request.args.get('plugin_type', '')
    category = request.args.get('category', '')
    q = request.args.get('q', '').strip()
    sort_by = request.args.get('sort_by', 'created_at')
    is_official = request.args.get('is_official', '')

    where = [r'status = "active"']
    params = []

    # 公开插件或自己的插件
    where.append(r'(is_public = 1 OR author_id = %s)')
    params.append(_safe_uid(None))

    if plugin_type and plugin_type != 'all':
        where.append(r'plugin_type = %s')
        params.append(plugin_type)

    if category and category != 'all':
        where.append(r'category = %s')
        params.append(category)

    if q:
        where.append(r'(name LIKE %s OR description LIKE %s)')
        params.append(f'%{q}%')
        params.append(f'%{q}%')

    if is_official in ('1', 'true'):
        where.append(r'is_official = 1')

    where_sql = 'WHERE ' + ' AND '.join(where)
    offset = (page - 1) * page_size

    # 排序
    order_map = {
        'created_at': 'created_at DESC',
        'download_count': 'download_count DESC',
        'rating': 'rating DESC',
        'name': 'name ASC',
    }
    order_sql = order_map.get(sort_by, 'created_at DESC')

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT COUNT(*) as total FROM plugins ' + where_sql, params)
        total = cur.fetchone()['total']

        cur.execute(
            r'SELECT * FROM plugins ' + where_sql +
            r' ORDER BY ' + order_sql + r' LIMIT %s OFFSET %s',
            params + [page_size, offset]
        )
        items = [_row_to_plugin(r) for r in cur.fetchall()]
        return jsonify(code=200, data={
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
        })
    finally:
        db.close()


@bp.route('/api/plugins/<plugin_id>', methods=['GET'])
@login_required
def get_plugin(plugin_id):
    """获取单个插件详情"""
    row = _get_plugin_by_id(plugin_id)
    if not row:
        return jsonify(code=404, msg='插件不存在')
    return jsonify(code=200, data=_row_to_plugin(row))


@bp.route('/api/plugins', methods=['POST'])
@login_required
def create_plugin():
    """发布新插件"""
    body = request.get_json() or {}
    name = (body.get('name') or '').strip()
    plugin_type = (body.get('plugin_type') or '').strip()

    if not name:
        return jsonify(code=400, msg='插件名称不能为空')
    if plugin_type not in ('tool', 'workflow', 'agent', 'mcp'):
        return jsonify(code=400, msg='无效的插件类型')

    plugin_id = str(uuid.uuid4())
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''INSERT INTO plugins
                       (id, name, plugin_type, description, version, author_id, author_name,
                        icon, icon_background, category, tags_json, package_json, manifest_json,
                        download_url, file_size, checksum, is_public, is_official, status,
                        created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                               %s, %s, %s, %s, %s)''',
                    (
                        plugin_id, name, plugin_type,
                        body.get('description', ''),
                        body.get('version', '1.0.0'),
                        _safe_uid(None),
                        body.get('author_name', ''),
                        body.get('icon', '🧩'),
                        body.get('icon_background', '#F5E8FF'),
                        body.get('category', 'utility'),
                        json.dumps(body.get('tags', []), ensure_ascii=False),
                        json.dumps(body.get('package', {}), ensure_ascii=False),
                        json.dumps(body.get('manifest', {}), ensure_ascii=False),
                        body.get('download_url', ''),
                        body.get('file_size', 0),
                        body.get('checksum', ''),
                        1 if body.get('is_public', True) else 0,
                        1 if body.get('is_official', False) else 0,
                        'active',
                        now, now,
                    ))
        db.commit()
        return jsonify(code=200, msg='发布成功', data={'id': plugin_id, 'name': name})
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=str(e))
    finally:
        db.close()


@bp.route('/api/plugins/<plugin_id>', methods=['PUT'])
@login_required
def update_plugin(plugin_id):
    """更新插件"""
    row = _get_plugin_by_id(plugin_id)
    if not row:
        return jsonify(code=404, msg='插件不存在')

    body = request.get_json() or {}
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''UPDATE plugins SET
                       name = %s, description = %s, version = %s,
                       icon = %s, icon_background = %s, category = %s,
                       tags_json = %s, package_json = %s, manifest_json = %s,
                       download_url = %s, file_size = %s, checksum = %s,
                       is_public = %s, is_official = %s, updated_at = %s
                       WHERE id = %s''',
                    (
                        body.get('name', row['name']),
                        body.get('description', row['description'] or ''),
                        body.get('version', row['version'] or '1.0.0'),
                        body.get('icon', row['icon'] or '🧩'),
                        body.get('icon_background', row['icon_background'] or '#F5E8FF'),
                        body.get('category', row['category'] or 'utility'),
                        json.dumps(body.get('tags', json.loads(row['tags_json'] or '[]')), ensure_ascii=False),
                        json.dumps(body.get('package', json.loads(row['package_json'] or '{}')), ensure_ascii=False),
                        json.dumps(body.get('manifest', json.loads(row['manifest_json'] or '{}')), ensure_ascii=False),
                        body.get('download_url', row['download_url'] or ''),
                        body.get('file_size', row['file_size'] or 0),
                        body.get('checksum', row['checksum'] or ''),
                        1 if body.get('is_public', bool(row['is_public'])) else 0,
                        1 if body.get('is_official', bool(row['is_official'])) else 0,
                        now,
                        plugin_id,
                    ))
        db.commit()
        return jsonify(code=200, msg='更新成功')
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=str(e))
    finally:
        db.close()


@bp.route('/api/plugins/<plugin_id>', methods=['DELETE'])
@login_required
def delete_plugin(plugin_id):
    """删除插件（软删除）"""
    row = _get_plugin_by_id(plugin_id)
    if not row:
        return jsonify(code=404, msg='插件不存在')

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'UPDATE plugins SET status = "inactive" WHERE id = %s', (plugin_id,))
        db.commit()
        return jsonify(code=200, msg='删除成功')
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=str(e))
    finally:
        db.close()


# ============================================================
# 插件安装/卸载
# ============================================================

@bp.route('/api/plugins/<plugin_id>/install', methods=['POST'])
@login_required
def install_plugin(plugin_id):
    """安装插件"""
    row = _get_plugin_by_id(plugin_id)
    if not row:
        return jsonify(code=404, msg='插件不存在')

    body = request.get_json() or {}
    install_id = str(uuid.uuid4())
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    db = get_db()
    try:
        cur = db.cursor()
        # 检查是否已安装
        cur.execute(
            r'SELECT id FROM plugin_installs WHERE plugin_id = %s AND installed_by = %s AND status IN ("installed", "enabled")',
            (plugin_id, _safe_uid(None))
        )
        if cur.fetchone():
            return jsonify(code=400, msg='插件已安装')

        cur.execute(r'''INSERT INTO plugin_installs
                       (id, plugin_id, installed_by, installed_version, status, config_json,
                        installed_at, updated_at)
                       VALUES (%s, %s, %s, %s, 'installed', %s, %s, %s)''',
                    (
                        install_id, plugin_id, _safe_uid(None),
                        row['version'] or '1.0.0',
                        json.dumps(body.get('config', {}), ensure_ascii=False),
                        now, now,
                    ))
        # 更新下载计数
        cur.execute(r'UPDATE plugins SET download_count = download_count + 1 WHERE id = %s', (plugin_id,))
        db.commit()
        return jsonify(code=200, msg='安装成功', data={'install_id': install_id})
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=str(e))
    finally:
        db.close()


@bp.route('/api/plugins/<plugin_id>/uninstall', methods=['POST'])
@login_required
def uninstall_plugin(plugin_id):
    """卸载插件"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            r'UPDATE plugin_installs SET status = "uninstalled", updated_at = %s WHERE plugin_id = %s AND installed_by = %s',
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), plugin_id, _safe_uid(None))
        )
        db.commit()
        return jsonify(code=200, msg='卸载成功')
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=str(e))
    finally:
        db.close()


@bp.route('/api/plugins/<plugin_id>/enable', methods=['POST'])
@login_required
def enable_plugin(plugin_id):
    """启用插件"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            r'UPDATE plugin_installs SET status = "enabled", updated_at = %s WHERE plugin_id = %s AND installed_by = %s',
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), plugin_id, _safe_uid(None))
        )
        db.commit()
        return jsonify(code=200, msg='已启用')
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=str(e))
    finally:
        db.close()


@bp.route('/api/plugins/<plugin_id>/disable', methods=['POST'])
@login_required
def disable_plugin(plugin_id):
    """停用插件"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            r'UPDATE plugin_installs SET status = "disabled", updated_at = %s WHERE plugin_id = %s AND installed_by = %s',
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), plugin_id, _safe_uid(None))
        )
        db.commit()
        return jsonify(code=200, msg='已停用')
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=str(e))
    finally:
        db.close()


@bp.route('/api/plugins/installed', methods=['GET'])
@login_required
def list_installed_plugins():
    """获取当前用户已安装的插件"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''SELECT p.*, pi.status as install_status, pi.installed_at
                       FROM plugins p
                       INNER JOIN plugin_installs pi ON p.id = pi.plugin_id
                       WHERE pi.installed_by = %s AND pi.status IN ('installed', 'enabled')
                       ORDER BY pi.installed_at DESC''',
                    (_safe_uid(None),))
        items = []
        for r in cur.fetchall():
            plugin = _row_to_plugin(r)
            plugin['install_status'] = r['install_status']
            plugin['installed_at'] = str(r['installed_at'])
            items.append(plugin)
        return jsonify(code=200, data=items)
    finally:
        db.close()


@bp.route('/api/plugins/<plugin_id>/rate', methods=['POST'])
@login_required
def rate_plugin(plugin_id):
    """为插件评分"""
    row = _get_plugin_by_id(plugin_id)
    if not row:
        return jsonify(code=404, msg='插件不存在')

    body = request.get_json() or {}
    score = float(body.get('score', 0))
    if not (0 <= score <= 5):
        return jsonify(code=400, msg='评分必须在 0-5 之间')

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''UPDATE plugins SET
                       rating = (rating * rating_count + %s) / (rating_count + 1),
                       rating_count = rating_count + 1
                       WHERE id = %s''', (score, plugin_id))
        db.commit()
        return jsonify(code=200, msg='评分成功')
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=str(e))
    finally:
        db.close()


@bp.route('/api/plugins/categories', methods=['GET'])
def list_categories():
    """获取插件分类列表"""
    categories = [
        {'key': 'all', 'label': '全部分类', 'icon': '📋'},
        {'key': 'utility', 'label': '实用工具', 'icon': '🔧'},
        {'key': 'data', 'label': '数据处理', 'icon': '📊'},
        {'key': 'ai', 'label': 'AI 能力', 'icon': '🤖'},
        {'key': 'integration', 'label': '集成连接', 'icon': '🔗'},
        {'key': 'productivity', 'label': '生产力', 'icon': '⚡'},
        {'key': 'security', 'label': '安全', 'icon': '🔒'},
    ]
    return jsonify(code=200, data=categories)


@bp.route('/api/plugins/types', methods=['GET'])
def list_types():
    """获取插件类型列表"""
    types = [
        {'key': 'all', 'label': '全部类型', 'icon': '📦'},
        {'key': 'tool', 'label': '工具插件', 'icon': '🔧'},
        {'key': 'workflow', 'label': '工作流插件', 'icon': '⚙️'},
        {'key': 'agent', 'label': 'Agent 插件', 'icon': '🤖'},
        {'key': 'mcp', 'label': 'MCP 插件', 'icon': '🔌'},
    ]
    return jsonify(code=200, data=types)


# ============================================================
# 注册路由
# ============================================================

def register_plugin_routes(app):
    """注册插件市场路由"""
    app.register_blueprint(bp)
