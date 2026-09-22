# -*- coding: utf-8 -*-
"""路由注册入口"""

from routes.account import register_account_routes
from routes.agents import register_agent_routes
from routes.app_templates import register_app_template_routes
from routes.audit import register_audit_routes
from routes.auth import register_auth_routes
from routes.backup import register_backup_routes
from routes.cache import register_cache_routes
from routes.chat import register_chat_routes
from routes.conversations import register_conversation_routes
from routes.custom_connectors import register_custom_connector_routes
from routes.data_sources import register_data_source_routes
from routes.feedback import register_feedback_routes
from routes.files import register_file_routes
from routes.knowledge import register_knowledge_routes
from routes.knowledge_pipelines import register_knowledge_pipeline_routes
from routes.mcps import register_mcp_routes
from routes.memories import register_memory_routes
from routes.models import register_model_routes
from routes.notifications import register_notification_routes
from routes.multi_agents import register_multi_agent_routes
from routes.my_agents import register_my_agents_routes
from routes.skills import register_skill_routes
from routes.stats import register_stats_routes
from routes.tasks import register_task_routes
from routes.evaluations import register_evaluation_routes
from routes.tools import register_tool_routes
from routes.workflow_templates import register_workflow_template_routes
from routes.agent_templates import register_agent_template_routes
from routes.agent_memory import register_agent_memory_routes
from routes.webhooks import register_webhook_routes
from routes.conversation_summaries import register_conversation_summary_routes
from routes.workflow_debug import register_workflow_debug_routes
from routes.workflow_monitor import register_workflow_monitor_routes
from routes.service_api_v2 import register_service_api_v2_routes
from routes.plugin_runtime import register_plugin_runtime_routes
from routes.plugins import register_plugin_routes
from routes.service_api import register_service_api_routes
from routes.dsl import register_dsl_routes
from routes.files import register_file_routes
from routes.site import register_site_routes
from routes.workflows import register_workflow_routes
from routes.trigger_subscriptions import register_trigger_subscription_routes
from routes.share import register_share_routes
from routes.workflow_comments import register_workflow_comments_routes



def register_all_routes(app):
    """统一注册所有业务路由"""
    register_account_routes(app)
    register_agent_routes(app)
    register_app_template_routes(app)
    register_audit_routes(app)
    register_auth_routes(app)
    register_backup_routes(app)
    register_cache_routes(app)
    register_chat_routes(app)
    register_conversation_routes(app)
    register_custom_connector_routes(app)
    register_data_source_routes(app)
    register_evaluation_routes(app)
    register_feedback_routes(app)
    register_file_routes(app)
    register_knowledge_routes(app)
    register_knowledge_pipeline_routes(app)
    register_mcp_routes(app)
    register_memory_routes(app)
    register_model_routes(app)
    register_multi_agent_routes(app)
    register_my_agents_routes(app)
    register_notification_routes(app)
    register_skill_routes(app)
    register_stats_routes(app)
    register_task_routes(app)
    register_tool_routes(app)
    register_workflow_routes(app)
    register_trigger_subscription_routes(app)
    register_workflow_template_routes(app)
    register_agent_template_routes(app)
    register_agent_memory_routes(app)
    register_webhook_routes(app)
    register_conversation_summary_routes(app)
    register_workflow_debug_routes(app)
    register_workflow_monitor_routes(app)
    register_service_api_v2_routes(app)
    register_plugin_runtime_routes(app)
    register_plugin_routes(app)
    register_service_api_routes(app)
    register_dsl_routes(app)
    register_site_routes(app)
    register_share_routes(app)
    register_workflow_comments_routes(app)
    # 3.7: MCP 服务端（暴露熵舟工具为 MCP Server）
    from engine.mcp_server import register_mcp_server_routes
    register_mcp_server_routes(app)
