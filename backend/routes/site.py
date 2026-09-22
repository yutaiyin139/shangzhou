# -*- coding: utf-8 -*-
"""站点配置路由 —— 站点信息和功能配置"""
import json
from flask import Blueprint, request, jsonify
from datetime import datetime

from config import get_db
from utils.auth import login_required

bp = Blueprint('site', __name__)

# ============================================================
# 站点配置存储
# ============================================================

SITE_CONFIG = {
    'title': '熵舟·智能体工作台',
    'description': '基于工作流编排的智能体开发平台',
    'icon': '🚀',
    'icon_background': '#E8F3FF',
    'default_language': 'zh-Hans',
    'default_theme': 'light',
    'workspace_models': True,
    'allow_registration': True,
    'webapi': True,
    'sso_enforced_for_signin': False,
    'sso_enforced_for_web': False,
    'copyright': '© 2026 熵舟',
    'privacy_policy': '',
    'custom_disclaimer': '',
}

# 功能开关
FEATURES = {
    'can_replace_logo': True,
    'model_load_balancing': True,
    'dataset_operator': False,
    'billing': False,
    'workspace_members': True,
    'invite_members': True,
    'plugins': True,
    'api_based_extension': True,
    'sso_enforced_for_signin': False,
    'sso_enforced_for_web': False,
}

# ============================================================
# 站点信息 API
# ============================================================

@bp.route('/console/api/site-info', methods=['GET'])
def site_info():
    """获取站点信息（公开访问）"""
    return jsonify(code=200, data={
        'title': SITE_CONFIG['title'],
        'description': SITE_CONFIG['description'],
        'icon': SITE_CONFIG['icon'],
        'icon_background': SITE_CONFIG['icon_background'],
        'default_language': SITE_CONFIG['default_language'],
        'default_theme': SITE_CONFIG['default_theme'],
        'workspace_models': SITE_CONFIG['workspace_models'],
        'allow_registration': SITE_CONFIG['allow_registration'],
        'webapi': SITE_CONFIG['webapi'],
        'sso_enforced_for_signin': SITE_CONFIG['sso_enforced_for_signin'],
        'sso_enforced_for_web': SITE_CONFIG['sso_enforced_for_web'],
        'copyright': SITE_CONFIG['copyright'],
        'privacy_policy': SITE_CONFIG['privacy_policy'],
        'custom_disclaimer': SITE_CONFIG['custom_disclaimer'],
        'version': '1.0.0',
        'feature': FEATURES,
    })


@bp.route('/console/api/site-info', methods=['PUT'])
@login_required
def update_site_info():
    """更新站点信息（管理员）"""
    body = request.get_json() or {}

    # 更新配置
    for key in SITE_CONFIG:
        if key in body:
            SITE_CONFIG[key] = body[key]

    return jsonify(code=200, msg='更新成功', data=SITE_CONFIG)


@bp.route('/console/api/features', methods=['GET'])
def get_features():
    """获取功能开关配置"""
    return jsonify(code=200, data=FEATURES)


@bp.route('/console/api/features', methods=['PUT'])
@login_required
def update_features():
    """更新功能开关（管理员）"""
    body = request.get_json() or {}

    for key in FEATURES:
        if key in body:
            FEATURES[key] = bool(body[key])

    return jsonify(code=200, msg='更新成功', data=FEATURES)


# ============================================================
# 系统状态 API
# ============================================================

@bp.route('/console/api/system/status', methods=['GET'])
def system_status():
    """获取系统状态"""
    import os
    import psutil

    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return jsonify(code=200, data={
            'status': 'healthy',
            'cpu': {
                'percent': cpu_percent,
                'count': psutil.cpu_count(),
            },
            'memory': {
                'total': memory.total,
                'available': memory.available,
                'percent': memory.percent,
                'used': memory.used,
            },
            'disk': {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': disk.percent,
            },
            'timestamp': datetime.now().isoformat(),
        })
    except Exception:
        return jsonify(code=200, data={
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
        })


@bp.route('/console/api/system/version', methods=['GET'])
def system_version():
    """获取系统版本信息"""
    return jsonify(code=200, data={
        'version': '1.0.0',
        'build_date': '2026-09-04',
        'api_version': 'v1',
        'features': [
            'workflow',
            'agent',
            'knowledge',
            'mcp',
            'tools',
            'plugins',
            'webhooks',
            'batch_run',
            'debug',
        ],
    })


# ============================================================
# OpenAPI 工具导入
# ============================================================

@bp.route('/console/api/tools/openapi/import', methods=['POST'])
@login_required
def import_openapi_tool():
    """
    从 OpenAPI/Swagger 导入自定义工具
    解析 OpenAPI Schema 并转换为工具定义
    """
    body = request.get_json() or {}
    spec_url = body.get('spec_url', '').strip()
    spec_json = body.get('spec_json', {})

    if not spec_url and not spec_json:
        return jsonify(code=400, msg='请提供 OpenAPI spec URL 或 JSON')

    try:
        import urllib.request

        # 获取 spec
        if spec_url:
            req = urllib.request.Request(spec_url, headers={'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                spec = json.loads(resp.read().decode('utf-8'))
        else:
            spec = spec_json

        # 解析 OpenAPI
        tools = _parse_openapi_to_tools(spec)

        return jsonify(code=200, msg=f'成功解析 {len(tools)} 个工具', data={
            'tools': tools,
            'spec_info': {
                'title': spec.get('info', {}).get('title', 'Unknown'),
                'version': spec.get('info', {}).get('version', '1.0.0'),
                'description': spec.get('info', {}).get('description', ''),
            }
        })
    except Exception as e:
        return jsonify(code=500, msg=f'导入失败: {str(e)}')


def _parse_openapi_to_tools(spec):
    """解析 OpenAPI Schema 为工具定义"""
    tools = []
    paths = spec.get('paths', {})
    components = spec.get('components', {})
    schemas = components.get('schemas', {})

    for path, methods in paths.items():
        for method, detail in methods.items():
            if method not in ('get', 'post', 'put', 'delete', 'patch'):
                continue

            operation_id = detail.get('operationId', f'{method}_{path.replace("/", "_")}')
            summary = detail.get('summary', detail.get('description', operation_id))
            description = detail.get('description', summary)

            # 解析参数
            parameters = []
            for param in detail.get('parameters', []):
                parameters.append({
                    'name': param.get('name', ''),
                    'in': param.get('in', 'query'),
                    'description': param.get('description', ''),
                    'required': param.get('required', False),
                    'type': param.get('schema', {}).get('type', 'string'),
                })

            # 解析请求体
            request_body = detail.get('requestBody', {})
            if request_body:
                content = request_body.get('content', {})
                for content_type, content_detail in content.items():
                    if content_type == 'application/json':
                        schema = content_detail.get('schema', {})
                        properties = schema.get('properties', {})
                        for prop_name, prop_detail in properties.items():
                            parameters.append({
                                'name': prop_name,
                                'in': 'body',
                                'description': prop_detail.get('description', ''),
                                'required': prop_name in schema.get('required', []),
                                'type': prop_detail.get('type', 'string'),
                            })

            tools.append({
                'name': operation_id,
                'label': summary,
                'description': description,
                'method': method.upper(),
                'url': _build_server_url(spec) + path,
                'parameters': parameters,
            })

    return tools


def _build_server_url(spec):
    """构建服务器 URL"""
    servers = spec.get('servers', [])
    if servers:
        return servers[0].get('url', '')
    return ''


@bp.route('/console/api/tools/openapi/save', methods=['POST'])
@login_required
def save_openapi_tool():
    """保存导入的 OpenAPI 工具"""
    body = request.get_json() or {}
    tools = body.get('tools', [])
    provider_name = body.get('provider_name', 'openapi-custom')

    if not tools:
        return jsonify(code=400, msg='工具列表不能为空')

    db = get_db()
    try:
        cur = db.cursor()
        saved_count = 0
        for tool in tools:
            provider_id = str(uuid.uuid4())
            cur.execute(r'''INSERT INTO dify_tool_providers
                           (id, tenant_id, tool_name, credentials, provider_type, created_at, updated_at)
                           VALUES (%s, %s, %s, %s, 'api', %s, %s)
                           ON DUPLICATE KEY UPDATE
                           credentials = VALUES(credentials),
                           updated_at = VALUES(updated_at)''',
                        (
                            provider_id,
                            request.user_id or '',
                            tool.get('name', ''),
                            json.dumps(tool, ensure_ascii=False),
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        ))
            saved_count += 1

        db.commit()
        return jsonify(code=200, msg=f'成功保存 {saved_count} 个工具')
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=f'保存失败: {str(e)}')
    finally:
        db.close()


# ============================================================
# 注册路由
# ============================================================

def register_site_routes(app):
    """注册站点配置路由"""
    app.register_blueprint(bp)
