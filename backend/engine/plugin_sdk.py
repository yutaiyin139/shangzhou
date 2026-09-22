# -*- coding: utf-8 -*-
"""
插件 SDK —— 插件开发框架

插件开发者继承 BasePlugin 类，实现 hook 方法即可扩展平台能力。

示例：
    class MyPlugin(BasePlugin):
        name = "My Plugin"
        version = "1.0.0"
        plugin_type = "tool"

        def on_workflow_start(self, context):
            context['my_data'] = 'hello'
            return context

        def on_node_execute(self, node_type, node_data, context):
            return context

        def on_workflow_end(self, result, context):
            result['processed_by'] = self.name
            return result
"""
import json
import os
import sys
import importlib
import importlib.util
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime


# ============================================================
# 插件基类
# ============================================================

class BasePlugin(ABC):
    """插件基类，所有插件必须继承此类"""

    # 子类必须定义
    name: str = ""
    version: str = "1.0.0"
    plugin_type: str = "tool"  # tool / workflow / agent / mcp
    description: str = ""
    author: str = ""

    # 可选配置
    hooks: List[str] = []  # 启用的 hook 列表，空表示全部
    config_schema: Dict = {}  # 配置 JSON Schema

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.enabled = True
        self._errors = []

    # --------------------------------------------------------
    # 工作流生命周期 Hook
    # --------------------------------------------------------

    def on_workflow_start(self, context: Dict) -> Dict:
        """
        工作流开始前调用
        :param context: 工作流上下文（inputs + env）
        :return: 修改后的 context
        """
        return context

    def on_node_execute(self, node_type: str, node_data: Dict, context: Dict) -> Dict:
        """
        每个节点执行前调用
        :param node_type: 节点类型 (start/llm/code/http/...)
        :param node_data: 节点配置数据
        :param context: 当前上下文
        :return: 修改后的 context
        """
        return context

    def on_node_complete(self, node_type: str, node_id: str, result: Dict, context: Dict) -> Dict:
        """
        节点执行完成后调用
        :param node_type: 节点类型
        :param node_id: 节点 ID
        :param result: 节点执行结果
        :param context: 当前上下文
        :return: 修改后的 result
        """
        return result

    def on_workflow_end(self, result: Dict, context: Dict) -> Dict:
        """
        工作流结束后调用
        :param result: 最终执行结果
        :param context: 完整上下文
        :return: 修改后的 result
        """
        return result

    def on_error(self, error: Exception, context: Dict) -> Optional[Dict]:
        """
        工作流出错时调用
        :param error: 异常对象
        :param context: 当前上下文
        :return: 可选的错误处理结果
        """
        self._errors.append(str(error))
        return None

    # --------------------------------------------------------
    # 工具 Hook（当 plugin_type == 'tool' 时）
    # --------------------------------------------------------

    def get_tools(self) -> List[Dict]:
        """
        返回此插件提供的工具列表
        :return: [{"name": "...", "description": "...", "parameters": {...}}]
        """
        return []

    def execute_tool(self, tool_name: str, params: Dict) -> Dict:
        """
        执行工具
        :param tool_name: 工具名称
        :param params: 工具参数
        :return: 执行结果
        """
        raise NotImplementedError(f"Tool '{tool_name}' not implemented")

    # --------------------------------------------------------
    # 配置验证
    # --------------------------------------------------------

    def validate_config(self, config: Dict) -> tuple:
        """
        验证配置是否合法
        :return: (is_valid, error_message)
        """
        if not self.config_schema:
            return True, ""

        required = self.config_schema.get('required', [])
        for key in required:
            if key not in config:
                return False, f"缺少必填配置项: {key}"

        return True, ""


# ============================================================
# 插件管理器
# ============================================================

class PluginManager:
    """插件管理器 —— 加载、注册、卸载插件"""

    def __init__(self, plugin_dir: str = None):
        self.plugin_dir = plugin_dir or os.path.join(os.path.dirname(__file__), '..', 'plugins')
        self._plugins: Dict[str, BasePlugin] = {}
        self._hooks: Dict[str, List] = {}

    def discover(self) -> List[Dict]:
        """
        扫描插件目录，发现可用插件
        :return: 插件信息列表
        """
        plugins = []
        if not os.path.isdir(self.plugin_dir):
            return plugins

        for name in os.listdir(self.plugin_dir):
            plugin_path = os.path.join(self.plugin_dir, name)
            manifest_path = os.path.join(plugin_path, 'manifest.json')
            main_path = os.path.join(plugin_path, 'main.py')

            if os.path.isdir(plugin_path) and os.path.isfile(manifest_path):
                try:
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                    manifest['_path'] = plugin_path
                    manifest['_has_main'] = os.path.isfile(main_path)
                    plugins.append(manifest)
                except Exception:
                    pass

        return plugins

    def load(self, plugin_id: str, manifest: Dict, config: Dict = None) -> BasePlugin:
        """
        加载单个插件
        :param plugin_id: 插件 ID
        :param manifest: 插件清单
        :param config: 插件配置
        :return: 插件实例
        """
        plugin_path = manifest.get('_path', '')
        main_path = os.path.join(plugin_path, 'main.py')

        if not os.path.isfile(main_path):
            raise FileNotFoundError(f"插件入口文件不存在: {main_path}")

        # 动态加载模块
        spec = importlib.util.spec_from_file_location(f"plugin_{plugin_id}", main_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"plugin_{plugin_id}"] = module
        spec.loader.exec_module(module)

        # 查找 BasePlugin 子类
        plugin_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, BasePlugin) and attr is not BasePlugin:
                plugin_class = attr
                break

        if not plugin_class:
            raise TypeError(f"插件 {plugin_id} 未找到 BasePlugin 子类")

        instance = plugin_class(config=config)
        self._plugins[plugin_id] = instance
        self._register_hooks(plugin_id, instance)
        return instance

    def unload(self, plugin_id: str):
        """卸载插件"""
        if plugin_id in self._plugins:
            plugin = self._plugins[plugin_id]
            plugin.enabled = False
            del self._plugins[plugin_id]
            # 移除 hooks
            for hook_name, handlers in self._hooks.items():
                self._hooks[hook_name] = [h for h in handlers if h[0] != plugin_id]
            # 清理模块
            mod_name = f"plugin_{plugin_id}"
            if mod_name in sys.modules:
                del sys.modules[mod_name]

    def get_plugin(self, plugin_id: str) -> Optional[BasePlugin]:
        """获取插件实例"""
        return self._plugins.get(plugin_id)

    def list_plugins(self) -> List[Dict]:
        """列出已加载的插件"""
        return [
            {
                'id': pid,
                'name': p.name,
                'version': p.version,
                'plugin_type': p.plugin_type,
                'description': p.description,
                'author': p.author,
                'enabled': p.enabled,
            }
            for pid, p in self._plugins.items()
        ]

    def _register_hooks(self, plugin_id: str, plugin: BasePlugin):
        """注册插件的 hook 到全局 hook 表"""
        hook_methods = [
            'on_workflow_start',
            'on_node_execute',
            'on_node_complete',
            'on_workflow_end',
            'on_error',
        ]
        for hook_name in hook_methods:
            if hasattr(plugin, hook_name):
                if hook_name not in self._hooks:
                    self._hooks[hook_name] = []
                self._hooks[hook_name].append((hook_name, plugin))

    # --------------------------------------------------------
    # Hook 执行引擎
    # --------------------------------------------------------

    def execute_hook(self, hook_name: str, **kwargs) -> Any:
        """
        执行指定 hook 的所有注册插件
        :param hook_name: hook 名称
        :param kwargs: 传递给 hook 的参数
        :return: 修改后的结果
        """
        handlers = self._hooks.get(hook_name, [])
        result = kwargs.get('context') or kwargs.get('result')

        for _, plugin in handlers:
            if not plugin.enabled:
                continue
            try:
                method = getattr(plugin, hook_name)
                if hook_name == 'on_workflow_start':
                    result = method(kwargs.get('context', {}))
                elif hook_name == 'on_node_execute':
                    result = method(
                        kwargs.get('node_type', ''),
                        kwargs.get('node_data', {}),
                        kwargs.get('context', {})
                    )
                elif hook_name == 'on_node_complete':
                    result = method(
                        kwargs.get('node_type', ''),
                        kwargs.get('node_id', ''),
                        kwargs.get('result', {}),
                        kwargs.get('context', {})
                    )
                elif hook_name == 'on_workflow_end':
                    result = method(kwargs.get('result', {}), kwargs.get('context', {}))
                elif hook_name == 'on_error':
                    method(kwargs.get('error'), kwargs.get('context', {}))
            except Exception as e:
                # 记录错误但不中断其他插件
                plugin._errors.append(str(e))

        return result

    def get_all_tools(self) -> List[Dict]:
        """获取所有插件提供的工具"""
        tools = []
        for pid, plugin in self._plugins.items():
            if plugin.plugin_type == 'tool' and plugin.enabled:
                for tool in plugin.get_tools():
                    tool['plugin_id'] = pid
                    tool['plugin_name'] = plugin.name
                    tools.append(tool)
        return tools


# ============================================================
# 全局插件管理器实例
# ============================================================

_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """获取全局插件管理器"""
    global _manager
    if _manager is None:
        _manager = PluginManager()
    return _manager


# ============================================================
# 插件模板生成器
# ============================================================

PLUGIN_TEMPLATE_MANIFEST = '''{
  "name": "{name}",
  "version": "1.0.0",
  "plugin_type": "{plugin_type}",
  "description": "{description}",
  "author": "{author}",
  "hooks": ["on_workflow_start", "on_node_execute", "on_workflow_end"],
  "config_schema": {{
    "type": "object",
    "properties": {{
      "api_key": {{
        "type": "string",
        "description": "API Key"
      }}
    }}
  }}
}'''

PLUGIN_TEMPLATE_MAIN = '''# -*- coding: utf-8 -*-
"""
{name} 插件
"""
from engine.plugin_sdk import BasePlugin
from typing import Dict


class {class_name}Plugin(BasePlugin):
    name = "{name}"
    version = "1.0.0"
    plugin_type = "{plugin_type}"
    description = "{description}"
    author = "{author}"

    def on_workflow_start(self, context: Dict) -> Dict:
        """工作流开始前"""
        # 在这里添加你的逻辑
        return context

    def on_node_execute(self, node_type: str, node_data: Dict, context: Dict) -> Dict:
        """节点执行前"""
        return context

    def on_node_complete(self, node_type: str, node_id: str, result: Dict, context: Dict) -> Dict:
        """节点执行后"""
        return result

    def on_workflow_end(self, result: Dict, context: Dict) -> Dict:
        """工作流结束后"""
        return result
'''


def generate_plugin_template(name: str, plugin_type: str, description: str = "", author: str = "") -> Dict[str, str]:
    """
    生成插件模板文件内容
    :return: {"manifest.json": "...", "main.py": "..."}
    """
    class_name = ''.join(w.capitalize() for w in name.split('_') if w)
    return {
        'manifest.json': PLUGIN_TEMPLATE_MANIFEST.format(
            name=name, plugin_type=plugin_type, description=description, author=author
        ),
        'main.py': PLUGIN_TEMPLATE_MAIN.format(
            name=name, class_name=class_name, plugin_type=plugin_type,
            description=description, author=author
        ),
    }
