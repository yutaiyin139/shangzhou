# -*- coding: utf-8 -*-
"""
数据库索引优化 —— 索引定义与迁移脚本

设计原则：
1. 高频查询字段优先索引
2. 联合索引遵循最左前缀原则
3. 避免过度索引（影响写入性能）
4. 定期使用 EXPLAIN 分析查询计划

索引分类：
- PRIMARY: 主键索引（已存在）
- UNIQUE: 唯一索引（已存在）
- INDEX: 普通索引（新增）
- COMPOSITE: 联合索引（新增）
- FULLTEXT: 全文索引（已存在）

使用方法：
    python -c "from models.indexes import apply_indexes; apply_indexes()"
"""

import logging
from config import get_db

logger = logging.getLogger(__name__)

# ============================================================
# 索引定义
# 格式: (table_name, index_name, columns, index_type)
# ============================================================

# 用户认证相关索引
AUTH_INDEXES = [
    # dify_accounts: 登录查询优化 (name OR email)
    ('dify_accounts', 'idx_name_status', 'name, status', 'INDEX'),
    ('dify_accounts', 'idx_email_status', 'email, status', 'INDEX'),

    # dify_tenant_account_joins: 用户工作区查询
    ('dify_tenant_account_joins', 'idx_account_role', 'account_id, role', 'INDEX'),
    ('dify_tenant_account_joins', 'idx_tenant_account_current', 'tenant_id, account_id, current', 'INDEX'),

    # user_roles: 角色查询优化
    ('user_roles', 'idx_user_role_status', 'user_id, role_id', 'INDEX'),
]

# 应用/智能体相关索引
APP_INDEXES = [
    # dify_apps: 应用列表查询
    ('dify_apps', 'idx_tenant_status', 'tenant_id, status', 'INDEX'),
    ('dify_apps', 'idx_tenant_mode', 'tenant_id, mode', 'INDEX'),
    ('dify_apps', 'idx_status_created', 'status, created_at', 'INDEX'),
    ('dify_apps', 'idx_public_demo', 'is_public, is_demo', 'INDEX'),

    # dify_app_model_configs: 模型配置查询
    ('dify_app_model_configs', 'idx_app_provider', 'app_id, provider', 'INDEX'),
]

# 工作流相关索引
WORKFLOW_INDEXES = [
    # dify_workflows: 工作流查询
    ('dify_workflows', 'idx_app_type', 'app_id, type', 'INDEX'),
    ('dify_workflows', 'idx_tenant_app', 'tenant_id, app_id', 'INDEX'),
    ('dify_workflows', 'idx_app_version', 'app_id, version', 'INDEX'),

    # dify_workflow_runs: 运行记录查询
    ('dify_workflow_runs', 'idx_app_status', 'app_id, status', 'INDEX'),
    ('dify_workflow_runs', 'idx_tenant_created', 'tenant_id, created_at', 'INDEX'),
    ('dify_workflow_runs', 'idx_status_finished', 'status, finished_at', 'INDEX'),
    ('dify_workflow_runs', 'idx_created_sort', 'created_at DESC', 'INDEX'),

    # dify_workflow_node_executions: 节点执行记录
    ('dify_workflow_node_executions', 'idx_run_node', 'workflow_run_id, node_id', 'INDEX'),
    ('dify_workflow_node_executions', 'idx_app_status', 'app_id, status', 'INDEX'),
    ('dify_workflow_node_executions', 'idx_finished_at', 'finished_at', 'INDEX'),
]

# 知识库相关索引
KNOWLEDGE_INDEXES = [
    # dify_datasets: 知识库查询
    ('dify_datasets', 'idx_tenant_created', 'tenant_id, created_at', 'INDEX'),

    # dify_documents: 文档查询
    ('dify_documents', 'idx_dataset_status', 'dataset_id, indexing_status', 'INDEX'),
    ('dify_documents', 'idx_tenant_dataset', 'tenant_id, dataset_id', 'INDEX'),
    ('dify_documents', 'idx_indexing_status', 'indexing_status, enabled', 'INDEX'),
    ('dify_documents', 'idx_created_sort', 'created_at DESC', 'INDEX'),

    # dify_document_segments: 文档分段查询
    ('dify_document_segments', 'idx_dataset_document', 'dataset_id, document_id', 'INDEX'),
    ('dify_document_segments', 'idx_document_position', 'document_id, position', 'INDEX'),
    ('dify_document_segments', 'idx_enabled_status', 'enabled, status', 'INDEX'),
    ('dify_document_segments', 'idx_dataset_enabled', 'dataset_id, enabled', 'INDEX'),
]

# 对话相关索引
CONVERSATION_INDEXES = [
    # dify_conversations: 对话查询
    ('dify_conversations', 'idx_app_user', 'app_id, user_id', 'INDEX'),
    ('dify_conversations', 'idx_user_status', 'user_id, status', 'INDEX'),
    ('dify_conversations', 'idx_app_lastmsg', 'app_id, last_message_at', 'INDEX'),
    ('dify_conversations', 'idx_user_lastmsg', 'user_id, last_message_at', 'INDEX'),
    ('dify_conversations', 'idx_pinned_sort', 'is_pinned DESC, last_message_at DESC', 'INDEX'),

    # dify_messages: 消息查询
    ('dify_messages', 'idx_conv_created', 'conversation_id, created_at', 'INDEX'),
    ('dify_messages', 'idx_conv_role', 'conversation_id, role', 'INDEX'),

    # dify_message_feedbacks: 反馈查询
    ('dify_message_feedbacks', 'idx_message_rating', 'message_id, rating', 'INDEX'),
]

# 工具/插件相关索引
TOOL_INDEXES = [
    # dify_tool_providers: 工具查询
    ('dify_tool_providers', 'idx_tenant_name', 'tenant_id, tool_name', 'INDEX'),
    ('dify_tool_providers', 'idx_tenant_type', 'tenant_id, tool_type', 'INDEX'),

    # tool_call_logs: 调用日志查询
    ('tool_call_logs', 'idx_node_tool', 'node_id, tool_name', 'INDEX'),
    ('tool_call_logs', 'idx_status_created', 'status, created_at', 'INDEX'),
    ('tool_call_logs', 'idx_elapsed', 'elapsed_ms', 'INDEX'),

    # plugins: 插件查询
    ('plugins', 'idx_type_status', 'plugin_type, status', 'INDEX'),
    ('plugins', 'idx_category_status', 'category, status', 'INDEX'),
    ('plugins', 'idx_download_sort', 'download_count DESC', 'INDEX'),
    ('plugins', 'idx_rating_sort', 'rating DESC', 'INDEX'),

    # plugin_installs: 安装记录
    ('plugin_installs', 'idx_plugin_status', 'plugin_id, status', 'INDEX'),
    ('plugin_installs', 'idx_user_status', 'installed_by, status', 'INDEX'),
]

# 审计日志相关索引
AUDIT_INDEXES = [
    # dify_audit_logs: 审计查询
    ('dify_audit_logs', 'idx_user_action', 'user_id, action', 'INDEX'),
    ('dify_audit_logs', 'idx_action_created', 'action, created_at', 'INDEX'),
    ('dify_audit_logs', 'idx_resource', 'resource_type, resource_id', 'INDEX'),
    ('dify_audit_logs', 'idx_ip_created', 'ip_address, created_at', 'INDEX'),
    ('dify_audit_logs', 'idx_response_code', 'response_code', 'INDEX'),
]

# 标注相关索引
ANNOTATION_INDEXES = [
    # dify_annotations: 标注查询
    ('dify_annotations', 'idx_dataset_status', 'dataset_id, status', 'INDEX'),
    ('dify_annotations', 'idx_annotated_by', 'annotated_by, created_at', 'INDEX'),
    ('dify_annotations', 'idx_reviewed_by', 'reviewed_by, status', 'INDEX'),

    # dify_message_annotations: 消息标注
    ('dify_message_annotations', 'idx_user_status', 'user_id, status', 'INDEX'),
    ('dify_message_annotations', 'idx_type_status', 'annotation_type, status', 'INDEX'),
]

# 文件上传相关索引
FILE_INDEXES = [
    # dify_upload_files: 文件查询
    ('dify_upload_files', 'idx_tenant_user', 'tenant_id, user_id', 'INDEX'),
    ('dify_upload_files', 'idx_tenant_type', 'tenant_id, file_type', 'INDEX'),
    ('dify_upload_files', 'idx_message', 'message_id', 'INDEX'),
    ('dify_upload_files', 'idx_status_created', 'status, created_at', 'INDEX'),
]

# Webhook 相关索引
WEBHOOK_INDEXES = [
    # webhooks: Webhook 查询
    ('webhooks', 'idx_app_active', 'app_id, is_active', 'INDEX'),
    ('webhooks', 'idx_last_called', 'last_called_at', 'INDEX'),

    # webhook_logs: 调用日志
    ('webhook_logs', 'idx_webhook_created', 'webhook_id, created_at', 'INDEX'),
    ('webhook_logs', 'idx_trigger_key', 'trigger_key', 'INDEX'),
]

# 工作流模板/Agent 模板相关索引
TEMPLATE_INDEXES = [
    # workflow_templates: 模板查询
    ('workflow_templates', 'idx_category_status', 'category, status', 'INDEX'),
    ('workflow_templates', 'idx_public_status', 'is_public, status', 'INDEX'),
    ('workflow_templates', 'idx_official_sort', 'is_official DESC, usage_count DESC', 'INDEX'),
    ('workflow_templates', 'idx_rating_sort', 'rating DESC, rating_count DESC', 'INDEX'),

    # agent_templates: Agent 模板
    ('agent_templates', 'idx_category_status', 'category, status', 'INDEX'),
    ('agent_templates', 'idx_public_status', 'is_public, status', 'INDEX'),
    ('agent_templates', 'idx_model', 'model_provider, model_name', 'INDEX'),
    ('agent_templates', 'idx_official_sort', 'is_official DESC, usage_count DESC', 'INDEX'),
]

# 评估相关索引
EVALUATION_INDEXES = [
    # agent_evaluations: 评估查询
    ('agent_evaluations', 'idx_app_status', 'app_id, status', 'INDEX'),
    ('agent_evaluations', 'idx_score_sort', 'avg_score DESC', 'INDEX'),
    ('agent_evaluations', 'idx_latency_sort', 'avg_latency_ms', 'INDEX'),
]

# 对话摘要相关索引
SUMMARY_INDEXES = [
    # conversation_summaries: 摘要查询
    ('conversation_summaries', 'idx_conv_created', 'conversation_id, created_at', 'INDEX'),
    ('conversation_summaries', 'idx_app_account', 'app_id, account_id', 'INDEX'),
]

# 工作流调试/批量运行相关索引
DEBUG_BATCH_INDEXES = [
    # workflow_debug_sessions: 调试会话
    ('workflow_debug_sessions', 'idx_app_status', 'app_id, status', 'INDEX'),
    ('workflow_debug_sessions', 'idx_account_status', 'account_id, status', 'INDEX'),
    ('workflow_debug_sessions', 'idx_updated', 'updated_at', 'INDEX'),

    # workflow_batch_runs: 批量运行
    ('workflow_batch_runs', 'idx_app_status', 'app_id, status', 'INDEX'),
    ('workflow_batch_runs', 'idx_account_created', 'account_id, created_at', 'INDEX'),
]

# 模型配置相关索引
MODEL_INDEXES = [
    # model_configs: 模型配置查询
    ('model_configs', 'idx_provider_type', 'provider, model_type', 'INDEX'),
    ('model_configs', 'idx_type_status', 'model_type, status', 'INDEX'),
    ('model_configs', 'idx_provider_status', 'provider, status', 'INDEX'),

    # dify_providers: 供应商查询
    ('dify_providers', 'idx_tenant_name', 'tenant_id, provider_name', 'INDEX'),
    ('dify_providers', 'idx_tenant_valid', 'tenant_id, is_valid', 'INDEX'),

    # dify_provider_models: 供应商模型
    ('dify_provider_models', 'idx_provider_type', 'provider_name, model_type', 'INDEX'),
    ('dify_provider_models', 'idx_valid', 'is_valid', 'INDEX'),
]

# 数据集权限相关索引
PERMISSION_INDEXES = [
    # dify_dataset_permissions: 权限查询
    ('dify_dataset_permissions', 'idx_role', 'role_id', 'INDEX'),
    ('dify_dataset_permissions', 'idx_permission', 'permission', 'INDEX'),

    # dify_app_dataset_joins: 应用-数据集关联
    ('dify_app_dataset_joins', 'idx_dataset', 'dataset_id', 'INDEX'),
]

# MCP 相关索引
MCP_INDEXES = [
    # mcp_servers: MCP 服务器查询
    ('mcp_servers', 'idx_enabled_type', 'enabled, mtype', 'INDEX'),
    ('mcp_servers', 'idx_name', 'name', 'INDEX'),
]

# 所有索引汇总
ALL_INDEXES = (
    AUTH_INDEXES +
    APP_INDEXES +
    WORKFLOW_INDEXES +
    KNOWLEDGE_INDEXES +
    CONVERSATION_INDEXES +
    TOOL_INDEXES +
    AUDIT_INDEXES +
    ANNOTATION_INDEXES +
    FILE_INDEXES +
    WEBHOOK_INDEXES +
    TEMPLATE_INDEXES +
    EVALUATION_INDEXES +
    SUMMARY_INDEXES +
    DEBUG_BATCH_INDEXES +
    MODEL_INDEXES +
    PERMISSION_INDEXES +
    MCP_INDEXES
)


# ============================================================
# 索引管理函数
# ============================================================

def index_exists(table_name, index_name):
    """检查索引是否已存在"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('''
            SELECT COUNT(*) as cnt
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = %s
            AND INDEX_NAME = %s
        ''', (table_name, index_name))
        result = cur.fetchone()
        return result['cnt'] > 0
    except Exception:
        return False
    finally:
        db.close()


def apply_indexes(dry_run=False):
    """
    应用所有索引

    参数:
        dry_run: 如果为 True，只打印将要执行的 SQL 而不实际执行

    返回:
        dict: {applied, skipped, failed, details}
    """
    result = {
        'applied': 0,
        'skipped': 0,
        'failed': 0,
        'details': [],
    }

    db = get_db()
    try:
        cur = db.cursor()

        for table_name, index_name, columns, index_type in ALL_INDEXES:
            # 检查索引是否已存在
            if index_exists(table_name, index_name):
                result['skipped'] += 1
                result['details'].append({
                    'table': table_name,
                    'index': index_name,
                    'status': 'skipped',
                    'message': '索引已存在',
                })
                continue

            # 检查表是否存在
            cur.execute('''
                SELECT COUNT(*) as cnt
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = %s
            ''', (table_name,))
            if cur.fetchone()['cnt'] == 0:
                result['skipped'] += 1
                result['details'].append({
                    'table': table_name,
                    'index': index_name,
                    'status': 'skipped',
                    'message': '表不存在',
                })
                continue

            # 构建 SQL
            sql = f"CREATE {index_type} INDEX `{index_name}` ON `{table_name}` ({columns})"

            if dry_run:
                result['details'].append({
                    'table': table_name,
                    'index': index_name,
                    'status': 'dry_run',
                    'sql': sql,
                })
                continue

            # 执行创建索引
            try:
                cur.execute(sql)
                result['applied'] += 1
                result['details'].append({
                    'table': table_name,
                    'index': index_name,
                    'status': 'applied',
                    'sql': sql,
                })
                logger.info(f'创建索引成功: {table_name}.{index_name}')
            except Exception as e:
                result['failed'] += 1
                result['details'].append({
                    'table': table_name,
                    'index': index_name,
                    'status': 'failed',
                    'error': str(e),
                    'sql': sql,
                })
                logger.error(f'创建索引失败: {table_name}.{index_name}: {e}')

        if not dry_run:
            # 分析表以更新统计信息
            analyzed_tables = set()
            for table_name, _, _, _ in ALL_INDEXES:
                if table_name not in analyzed_tables:
                    analyzed_tables.add(table_name)
                    try:
                        cur.execute(f'ANALYZE TABLE `{table_name}`')
                    except Exception:
                        pass

    finally:
        db.close()

    return result


def drop_index(table_name, index_name):
    """
    删除指定索引

    参数:
        table_name: 表名
        index_name: 索引名

    返回:
        bool: 是否成功
    """
    if not index_exists(table_name, index_name):
        return False

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(f'DROP INDEX `{index_name}` ON `{table_name}`')
        return True
    except Exception as e:
        logger.error(f'删除索引失败: {table_name}.{index_name}: {e}')
        return False
    finally:
        db.close()


def get_table_indexes(table_name):
    """
    获取表的所有索引信息

    参数:
        table_name: 表名

    返回:
        list: 索引信息列表
    """
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('''
            SELECT
                INDEX_NAME,
                GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) as COLUMNS,
                INDEX_TYPE,
                NON_UNIQUE,
                CASE WHEN INDEX_NAME = 'PRIMARY' THEN 'PRI'
                     WHEN NON_UNIQUE = 0 THEN 'UNI'
                     ELSE 'MUL' END as KEY_TYPE
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = %s
            GROUP BY INDEX_NAME, INDEX_TYPE, NON_UNIQUE
            ORDER BY INDEX_NAME
        ''', (table_name,))
        return cur.fetchall()
    except Exception as e:
        logger.error(f'获取索引信息失败: {table_name}: {e}')
        return []
    finally:
        db.close()


def get_slow_query_suggestions():
    """
    获取慢查询索引建议（基于现有索引使用情况）

    返回:
        list: 建议列表
    """
    db = get_db()
    try:
        cur = db.cursor()
        # 查询没有索引或索引使用效率低的表
        cur.execute('''
            SELECT
                t.TABLE_NAME,
                t.TABLE_ROWS,
                s.INDEX_NAME,
                s.COLUMN_NAME
            FROM information_schema.TABLES t
            LEFT JOIN information_schema.STATISTICS s
                ON t.TABLE_NAME = s.TABLE_NAME
                AND t.TABLE_SCHEMA = s.TABLE_SCHEMA
            WHERE t.TABLE_SCHEMA = DATABASE()
            AND t.TABLE_ROWS > 1000
            ORDER BY t.TABLE_ROWS DESC
        ''')
        return cur.fetchall()
    except Exception as e:
        logger.error(f'获取索引建议失败: {e}')
        return []
    finally:
        db.close()


# ============================================================
# 索引统计视图
# ============================================================

INDEX_STATS_SQL = '''
CREATE OR REPLACE VIEW IF NOT EXISTS v_index_stats AS
SELECT
    TABLE_NAME,
    INDEX_NAME,
    GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) as COLUMNS,
    INDEX_TYPE,
    CASE WHEN NON_UNIQUE = 0 THEN 'UNIQUE' ELSE 'NON-UNIQUE' END as UNIQUENESS,
    TABLE_ROWS,
    ROUND(DATA_LENGTH / 1024 / 1024, 2) as DATA_SIZE_MB
FROM information_schema.STATISTICS s
JOIN information_schema.TABLES t
    USING (TABLE_SCHEMA, TABLE_NAME)
WHERE TABLE_SCHEMA = DATABASE()
GROUP BY TABLE_NAME, INDEX_NAME, INDEX_TYPE, NON_UNIQUE, TABLE_ROWS, DATA_LENGTH
ORDER BY TABLE_NAME, INDEX_NAME
'''


if __name__ == '__main__':
    import sys

    if '--dry-run' in sys.argv:
        result = apply_indexes(dry_run=True)
        print(f"将要创建的索引数: {len([d for d in result['details'] if d['status'] == 'dry_run'])}")
        for detail in result['details']:
            if detail['status'] == 'dry_run':
                print(f"  {detail['table']}.{detail['index']}: {detail['sql']}")
    elif '--list' in sys.argv:
        if len(sys.argv) > 2:
            table_name = sys.argv[2]
            indexes = get_table_indexes(table_name)
            print(f"\n表 {table_name} 的索引:")
            for idx in indexes:
                print(f"  {idx['INDEX_NAME']}: {idx['COLUMNS']} ({idx['KEY_TYPE']})")
        else:
            print("用法: python models/indexes.py --list <table_name>")
    else:
        print("应用索引中...")
        result = apply_indexes()
        print(f"\n结果:")
        print(f"  已创建: {result['applied']}")
        print(f"  已跳过: {result['skipped']}")
        print(f"  失败: {result['failed']}")
        if result['failed'] > 0:
            print("\n失败的索引:")
            for detail in result['details']:
                if detail['status'] == 'failed':
                    print(f"  {detail['table']}.{detail['index']}: {detail.get('error', '')}")
