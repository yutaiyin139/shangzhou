# -*- coding: utf-8 -*-
"""
插件运行时 API —— 插件加载、卸载、执行、模板生成
"""
import json
import os
import shutil
import uuid
from flask import Blueprint, request, jsonify
from datetime import datetime

from config import get_db
from utils.auth import login_required
from engine.plugin_sdk import get_plugin_manager, generate_plugin_template

bp = Blueprint('plugin_runtime', __name__)

# 插件安装目录
PLUGINS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'plugins')


# ============================================================
# 插件运行时管理
# ============================================================

@bp.route('/api/v1/plugins/runtime', methods=['GET'])
@login_required
def list_runtime_plugins():
    """列出已加载到运行时的插件"""
    pm = get_plugin_manager()
    return jsonify(code=200, data=pm.list_plugins())


@bp.route('/api/v1/plugins/discover', methods=['GET'])
@login_required
def discover_plugins():
    """扫描插件目录，发现可用插件"""
    pm = get_plugin_manager()
    plugins = pm.discover()
    return jsonify(code=200, data=plugins)


@bp.route('/api/v1/plugins/<plugin_id>/load', methods=['POST'])
@login_required
def load_plugin(plugin_id):
    """加载插件到运行时"""
    pm = get_plugin_manager()

    # 查找插件 manifest
    plugin_dir = os.path.join(PLUGINS_DIR, plugin_id)
    manifest_path = os.path.join(plugin_dir, 'manifest.json')

    if not os.path.isfile(manifest_path):
        return jsonify(code=404, msg='插件清单不存在')

    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        body = request.get_json() or {}
        config = body.get('config', {})

        plugin = pm.load(plugin_id, manifest, config)
        return jsonify(code=200, msg='加载成功', data={
            'id': plugin_id,
            'name': plugin.name,
            'version': plugin.version,
            'plugin_type': plugin.plugin_type,
        })
    except Exception as e:
        return jsonify(code=500, msg=f'加载失败: {str(e)}')


@bp.route('/api/v1/plugins/<plugin_id>/unload', methods=['POST'])
@login_required
def unload_plugin(plugin_id):
    """从运行时卸载插件"""
    pm = get_plugin_manager()
    if not pm.get_plugin(plugin_id):
        return jsonify(code=404, msg='插件未加载')

    pm.unload(plugin_id)
    return jsonify(code=200, msg='卸载成功')


@bp.route('/api/v1/plugins/tools', methods=['GET'])
@login_required
def list_plugin_tools():
    """获取所有插件提供的工具"""
    pm = get_plugin_manager()
    tools = pm.get_all_tools()
    return jsonify(code=200, data=tools)


@bp.route('/api/v1/plugins/tools/execute', methods=['POST'])
@login_required
def execute_plugin_tool():
    """执行插件工具"""
    body = request.get_json() or {}
    plugin_id = body.get('plugin_id', '')
    tool_name = body.get('tool_name', '')
    params = body.get('params', {})

    if not plugin_id or not tool_name:
        return jsonify(code=400, msg='缺少 plugin_id 或 tool_name')

    pm = get_plugin_manager()
    plugin = pm.get_plugin(plugin_id)
    if not plugin:
        return jsonify(code=404, msg='插件未加载')

    try:
        result = plugin.execute_tool(tool_name, params)
        return jsonify(code=200, data=result)
    except Exception as e:
        return jsonify(code=500, msg=f'执行失败: {str(e)}')


# ============================================================
# 插件模板生成
# ============================================================

@bp.route('/api/v1/plugins/generate-template', methods=['POST'])
@login_required
def generate_template():
    """
    生成插件模板文件
    在 plugins/ 目录下创建插件骨架
    """
    body = request.get_json() or {}
    name = (body.get('name') or '').strip()
    plugin_type = (body.get('plugin_type') or 'tool').strip()
    description = body.get('description', '')
    author = body.get('author', '')

    if not name:
        return jsonify(code=400, msg='插件名称不能为空')
    if plugin_type not in ('tool', 'workflow', 'agent', 'mcp'):
        return jsonify(code=400, msg='无效的插件类型')

    # 生成目录名（小写+下划线）
    dir_name = name.lower().replace(' ', '_').replace('-', '_')
    plugin_dir = os.path.join(PLUGINS_DIR, dir_name)

    if os.path.exists(plugin_dir):
        return jsonify(code=400, msg='插件目录已存在')

    try:
        os.makedirs(plugin_dir, exist_ok=True)
        templates = generate_plugin_template(name, plugin_type, description, author)

        for filename, content in templates.items():
            filepath = os.path.join(plugin_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

        return jsonify(code=200, msg='模板已生成', data={
            'plugin_dir': dir_name,
            'files': list(templates.keys()),
        })
    except Exception as e:
        # 清理失败的目录
        if os.path.exists(plugin_dir):
            shutil.rmtree(plugin_dir, ignore_errors=True)
        return jsonify(code=500, msg=f'生成失败: {str(e)}')


# ============================================================
# 插件 Hook 执行（内部调用）
# ============================================================

@bp.route('/api/v1/plugins/hooks/execute', methods=['POST'])
@login_required
def execute_hook():
    """
    手动触发插件 hook（调试用）
    """
    body = request.get_json() or {}
    hook_name = body.get('hook', '')
    params = body.get('params', {})

    valid_hooks = ['on_workflow_start', 'on_node_execute', 'on_node_complete', 'on_workflow_end']
    if hook_name not in valid_hooks:
        return jsonify(code=400, msg=f'无效的 hook 名称，可选: {valid_hooks}')

    pm = get_plugin_manager()
    result = pm.execute_hook(hook_name, **params)
    return jsonify(code=200, data={'result': result})


# ============================================================
# 插件配置
# ============================================================

@bp.route('/api/v1/plugins/<plugin_id>/config', methods=['GET'])
@login_required
def get_plugin_config(plugin_id):
    """获取插件配置"""
    pm = get_plugin_manager()
    plugin = pm.get_plugin(plugin_id)
    if not plugin:
        return jsonify(code=404, msg='插件未加载')

    return jsonify(code=200, data={
        'config': plugin.config,
        'config_schema': plugin.config_schema,
        'errors': plugin._errors[-10:],  # 最近 10 条错误
    })


@bp.route('/api/v1/plugins/<plugin_id>/config', methods=['PUT'])
@login_required
def update_plugin_config(plugin_id):
    """更新插件配置"""
    pm = get_plugin_manager()
    plugin = pm.get_plugin(plugin_id)
    if not plugin:
        return jsonify(code=404, msg='插件未加载')

    body = request.get_json() or {}
    new_config = body.get('config', {})

    # 验证配置
    is_valid, error = plugin.validate_config(new_config)
    if not is_valid:
        return jsonify(code=400, msg=error)

    plugin.config = new_config
    return jsonify(code=200, msg='配置已更新')


# ============================================================
# 注册路由
# ============================================================

def register_plugin_runtime_routes(app):
    """注册插件运行时路由"""
    app.register_blueprint(bp)
