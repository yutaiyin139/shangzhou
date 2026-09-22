# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
从 Dify PostgreSQL 迁移数据到 MySQL szagent 库。
一次性运行，将 Dify 的核心业务数据迁移到本地 MySQL。

特性：
    - 支持 INSERT ON DUPLICATE KEY UPDATE（合并数据，不失个性化）
    - 自动创建所有需要的表
    - 支持增量迁移（可多次运行）
    - embedding 字段自动迁移

使用方法：
    python backend/migrate_from_dify.py

前提条件：
    1. Dify PostgreSQL 数据库正在运行（localhost:5432, database=dify）
    2. MySQL szagent 库已创建（localhost:3306, database=szagent）
    3. Dify 兼容表已通过各路由的 _ensure_*_tables() 创建，或先运行一次后端服务
"""

import json
import sys
import os
import uuid
from datetime import datetime

# 确保能 import config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Dify PostgreSQL 配置（仅用于数据迁移，迁移完成后不再需要）
# 请根据实际情况修改以下配置
DIFY_DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres',
    'password': 'difyai123456',
    'database': 'dify',
}

# 是否使用 UPSERT（INSERT ON DUPLICATE KEY UPDATE）
# True = 合并数据（Dify 数据覆盖同 ID 记录，但保留 MySQL 特有字段）
# False = INSERT IGNORE（跳过已存在的记录）
USE_UPSERT = True


def pg_table_exists(pg_table):
    """检查 PostgreSQL 表是否存在"""
    import psycopg2
    pg_conn = psycopg2.connect(**DIFY_DB_CONFIG)
    try:
        cur = pg_conn.cursor()
        cur.execute(
            'SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = %s',
            ('public', pg_table)
        )
        return cur.fetchone() is not None
    finally:
        pg_conn.close()


def migrate_table_if_exists(pg_table, mysql_table, columns, transform=None):
    """如果 PostgreSQL 表存在则迁移，否则跳过"""
    if not pg_table_exists(pg_table):
        print(f'  {pg_table}: 表不存在，跳过')
        return 0
    return migrate_table(pg_table, mysql_table, columns, transform)


def migrate_table(pg_table, mysql_table, columns, transform=None, upsert_columns=None):
    """
    通用表迁移函数

    参数:
        pg_table: PostgreSQL 表名
        mysql_table: MySQL 表名
        columns: 要迁移的列名列表
        transform: 可选的转换函数(row, values, columns) -> values
        upsert_columns: 需要 UPSERT 更新的列（None 表示不使用 UPSERT）
    """
    import psycopg2
    import psycopg2.extras

    pg_conn = psycopg2.connect(**DIFY_DB_CONFIG)
    try:
        pg_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        pg_cur.execute(f'SELECT * FROM {pg_table}')
        rows = pg_cur.fetchall()
        pg_cur.close()
    finally:
        pg_conn.close()

    if not rows:
        print(f'  {pg_table}: 无数据，跳过')
        return 0

    from config import get_db
    mysql_conn = get_db()
    try:
        cur = mysql_conn.cursor()
        placeholders = ','.join(['%s'] * len(columns))
        col_names = ','.join(columns)

        if USE_UPSERT and upsert_columns:
            # INSERT ON DUPLICATE KEY UPDATE
            update_parts = [f'{col} = VALUES({col})' for col in upsert_columns]
            sql = f'''INSERT INTO {mysql_table} ({col_names}) VALUES ({placeholders})
                      ON DUPLICATE KEY UPDATE {','.join(update_parts)}'''
        elif USE_UPSERT:
            # 默认更新除 id 外的所有列
            update_parts = [f'{col} = VALUES({col})' for col in columns if col != 'id']
            sql = f'''INSERT INTO {mysql_table} ({col_names}) VALUES ({placeholders})
                      ON DUPLICATE KEY UPDATE {','.join(update_parts)}'''
        else:
            sql = f'INSERT IGNORE INTO {mysql_table} ({col_names}) VALUES ({placeholders})'

        count = 0
        update_count = 0
        for row in rows:
            values = []
            for col in columns:
                val = row.get(col)
                # 处理 dict/list → JSON 字符串
                if isinstance(val, (dict, list)):
                    val = json.dumps(val, ensure_ascii=False)
                # 处理 UUID - 确保是字符串格式
                if col == 'id' and val is not None:
                    val = str(val)
                values.append(val)
            if transform:
                values = transform(row, values, columns)
            try:
                cur.execute(sql, values)
                # rowcount: 1 = 插入, 2 = 更新, 0 = 无变化
                if cur.rowcount == 1:
                    count += 1
                elif cur.rowcount == 2:
                    update_count += 1
            except Exception as e:
                print(f'  插入失败: {e}, row id={row.get("id")}')
        mysql_conn.commit()

        msg = f'  {pg_table} → {mysql_table}: 插入 {count}'
        if update_count > 0:
            msg += f', 更新 {update_count}'
        msg += f' / 共 {len(rows)} 条'
        print(msg)
        return count + update_count
    finally:
        mysql_conn.close()


def ensure_dify_tables():
    """确保 MySQL 中 Dify 兼容表已创建"""
    from config import get_db
    from models.tables import (
        # Dify 核心表
        DIFY_APPS_TABLE_SQL,
        DIFY_WORKFLOWS_TABLE_SQL,
        DIFY_WORKFLOW_RUNS_TABLE_SQL,
        DIFY_WORKFLOW_NODE_EXECUTIONS_TABLE_SQL,
        DIFY_WORKFLOW_VERSION_COUNTERS_TABLE_SQL,
        DIFY_APP_MODEL_CONFIGS_TABLE_SQL,
        DIFY_SITES_TABLE_SQL,
        DIFY_API_TOKENS_TABLE_SQL,
        DIFY_DATASETS_TABLE_SQL,
        DIFY_DOCUMENTS_TABLE_SQL,
        DIFY_DOCUMENT_SEGMENTS_TABLE_SQL,
        DIFY_ACCOUNTS_TABLE_SQL,
        DIFY_TENANTS_TABLE_SQL,
        DIFY_TENANT_ACCOUNT_JOINS_TABLE_SQL,
        DIFY_PROVIDERS_TABLE_SQL,
        DIFY_PROVIDER_MODELS_TABLE_SQL,
        DIFY_TOOL_PROVIDERS_TABLE_SQL,
        DIFY_DATASOURCE_PROVIDERS_TABLE_SQL,
        # 对话历史表
        DIFY_CONVERSATIONS_TABLE_SQL,
        DIFY_MESSAGES_TABLE_SQL,
        # 模型配置表
        MODEL_CONFIGS_TABLE_SQL,
        # 熵舟自定义表
        AGENTS_TABLE_SQL,
        MEMORIES_TABLE_SQL,
        MCP_TABLE_SQL,
        DATA_SOURCES_TABLE_SQL,
        CUSTOM_CONNECTORS_TABLE_SQL,
        APP_TEMPLATES_TABLE_SQL,
        WORKFLOW_VERSIONS_TABLE_SQL,
        WORKFLOW_TEST_RUNS_TABLE_SQL,
        SKILLS_TABLE_SQL,
        SKILL_INSTALLS_TABLE_SQL,
        TOOL_INSTALLS_TABLE_SQL,
        TOOL_SETTINGS_TABLE_SQL,
    )

    db = get_db()
    try:
        cur = db.cursor()
        # Dify 核心表
        cur.execute(DIFY_APPS_TABLE_SQL)
        cur.execute(DIFY_WORKFLOWS_TABLE_SQL)
        cur.execute(DIFY_WORKFLOW_RUNS_TABLE_SQL)
        cur.execute(DIFY_WORKFLOW_NODE_EXECUTIONS_TABLE_SQL)
        cur.execute(DIFY_WORKFLOW_VERSION_COUNTERS_TABLE_SQL)
        cur.execute(DIFY_APP_MODEL_CONFIGS_TABLE_SQL)
        cur.execute(DIFY_SITES_TABLE_SQL)
        cur.execute(DIFY_API_TOKENS_TABLE_SQL)
        cur.execute(DIFY_DATASETS_TABLE_SQL)
        cur.execute(DIFY_DOCUMENTS_TABLE_SQL)
        cur.execute(DIFY_DOCUMENT_SEGMENTS_TABLE_SQL)
        cur.execute(DIFY_ACCOUNTS_TABLE_SQL)
        cur.execute(DIFY_TENANTS_TABLE_SQL)
        cur.execute(DIFY_TENANT_ACCOUNT_JOINS_TABLE_SQL)
        cur.execute(DIFY_PROVIDERS_TABLE_SQL)
        cur.execute(DIFY_PROVIDER_MODELS_TABLE_SQL)
        cur.execute(DIFY_TOOL_PROVIDERS_TABLE_SQL)
        cur.execute(DIFY_DATASOURCE_PROVIDERS_TABLE_SQL)
        # 对话历史表
        cur.execute(DIFY_CONVERSATIONS_TABLE_SQL)
        cur.execute(DIFY_MESSAGES_TABLE_SQL)
        # 模型配置表
        cur.execute(MODEL_CONFIGS_TABLE_SQL)
        # 熵舟自定义表
        cur.execute(AGENTS_TABLE_SQL)
        cur.execute(MEMORIES_TABLE_SQL)
        cur.execute(MCP_TABLE_SQL)
        cur.execute(DATA_SOURCES_TABLE_SQL)
        cur.execute(CUSTOM_CONNECTORS_TABLE_SQL)
        cur.execute(APP_TEMPLATES_TABLE_SQL)
        cur.execute(WORKFLOW_VERSIONS_TABLE_SQL)
        cur.execute(WORKFLOW_TEST_RUNS_TABLE_SQL)
        cur.execute(SKILLS_TABLE_SQL)
        cur.execute(SKILL_INSTALLS_TABLE_SQL)
        cur.execute(TOOL_INSTALLS_TABLE_SQL)
        cur.execute(TOOL_SETTINGS_TABLE_SQL)
        db.commit()
        print('  所有表已就绪（Dify 兼容表 + 熵舟自定义表）')
    finally:
        db.close()


def run_migration():
    """执行完整迁移（使用 UPSERT 合并数据）"""
    print('=== 开始从 Dify PostgreSQL 迁移数据到 MySQL ===')
    print(f'  UPSERT 模式: {"开启（合并数据）" if USE_UPSERT else "关闭（仅插入新数据）"}')
    print()

    # 0. 确保表存在
    print('[0/15] 检查并创建所有表...')
    ensure_dify_tables()
    print()

    # 1. 租户
    print('[1/15] 迁移租户...')
    migrate_table('tenants', 'dify_tenants',
                  ['id', 'name', 'plan', 'status', 'created_at', 'updated_at'])

    # 2. 账号
    print('[2/15] 迁移账号...')
    migrate_table('accounts', 'dify_accounts',
                  ['id', 'name', 'email', 'password', 'password_salt',
                   'interface_language', 'interface_theme', 'status',
                   'created_at', 'updated_at'])

    # 3. 租户-账号关联
    print('[3/15] 迁移租户-账号关联...')
    migrate_table('tenant_account_joins', 'dify_tenant_account_joins',
                  ['tenant_id', 'account_id', 'role', 'current',
                   'created_at', 'updated_at'])

    # 4. 应用
    print('[4/15] 迁移应用...')
    migrate_table('apps', 'dify_apps',
                  ['id', 'tenant_id', 'name', 'mode', 'icon', 'icon_background',
                   'icon_type', 'description', 'app_model_config_id', 'status',
                   'enable_site', 'enable_api', 'api_rpm', 'api_rph',
                   'is_demo', 'is_public', 'is_universal', 'workflow_id',
                   'created_by', 'updated_by', 'created_at', 'updated_at',
                   'use_icon_as_answer_icon'])

    # 5. 工作流
    print('[5/15] 迁移工作流...')
    migrate_table('workflows', 'dify_workflows',
                  ['id', 'tenant_id', 'app_id', 'type', 'version', 'graph',
                   'features', 'environment_variables', 'conversation_variables',
                   'rag_pipeline_variables', 'marked_name', 'marked_comment',
                   'kind', 'version_number', 'created_by', 'updated_by',
                   'created_at', 'updated_at'])

    # 6. 工作流运行记录
    print('[6/15] 迁移工作流运行记录...')
    migrate_table('workflow_runs', 'dify_workflow_runs',
                  ['id', 'app_id', 'tenant_id', 'workflow_id', 'status',
                   'inputs', 'outputs', 'error', 'elapsed_time', 'total_tokens',
                   'total_steps', 'created_by', 'created_at', 'finished_at'])

    # 7. 工作流节点执行记录
    print('[7/15] 迁移节点执行记录...')
    migrate_table('workflow_node_executions', 'dify_workflow_node_executions',
                  ['id', 'app_id', 'workflow_run_id', 'node_id', 'node_type',
                   'title', 'inputs', 'outputs', 'status', 'error',
                   'elapsed_time', 'created_at', 'finished_at'])

    # 8. 版本计数器
    print('[8/15] 迁移版本计数器...')
    migrate_table('workflow_version_counters', 'dify_workflow_version_counters',
                  ['app_id', 'last_version_number'])

    # 9. 应用模型配置
    print('[9/15] 迁移应用模型配置...')
    migrate_table('app_model_configs', 'dify_app_model_configs',
                  ['id', 'app_id', 'provider', 'model_id', 'configs', 'model',
                   'opening_statement', 'suggested_questions', 'pre_prompt',
                   'prompt_type', 'created_by', 'updated_by',
                   'created_at', 'updated_at'])

    # 10. Sites
    print('[10/15] 迁移 Sites...')
    migrate_table('sites', 'dify_sites',
                  ['id', 'app_id', 'title', 'icon', 'icon_background',
                   'description', 'default_language', 'customize_token_strategy',
                   'prompt_public', 'status', 'custom_disclaimer',
                   'show_workflow_steps', 'use_icon_as_answer_icon', 'code',
                   'created_by', 'updated_by', 'created_at', 'updated_at'])

    # 11. API Tokens
    print('[11/15] 迁移 API Tokens...')
    migrate_table('api_tokens', 'dify_api_tokens',
                  ['id', 'app_id', 'tenant_id', 'type', 'token', 'created_at'])

    # 12. 知识库相关
    print('[12/15] 迁移知识库...')
    migrate_table('datasets', 'dify_datasets',
                  ['id', 'tenant_id', 'name', 'description',
                   'indexing_technique', 'index_struct',
                   'created_by', 'updated_by', 'created_at', 'updated_at'])
    migrate_table('documents', 'dify_documents',
                  ['id', 'tenant_id', 'dataset_id', 'position',
                   'data_source_type', 'data_source_info', 'batch', 'name',
                   'created_from', 'created_by', 'indexing_status', 'enabled',
                   'word_count', 'created_at', 'updated_at'])
    # 知识分段 - 包含 embedding 字段
    migrate_table('document_segments', 'dify_document_segments',
                  ['id', 'tenant_id', 'dataset_id', 'document_id', 'position',
                   'content', 'word_count', 'tokens', 'hit_count', 'enabled',
                   'status', 'embedding', 'created_by', 'created_at'])

    # 13. 模型供应商
    print('[13/15] 迁移模型供应商...')
    migrate_table('providers', 'dify_providers',
                  ['id', 'tenant_id', 'provider_name', 'provider_type',
                   'credential_id', 'is_valid', 'created_at', 'updated_at'])
    migrate_table('provider_models', 'dify_provider_models',
                  ['id', 'provider_name', 'model_name', 'model_type',
                   'is_valid', 'created_at', 'updated_at'])

    # 14. 工具/数据源供应商
    print('[14/15] 迁移工具/数据源供应商...')
    # Dify 1.17 使用多个 tool_* 表，统一迁移到 dify_tool_providers
    migrate_table_if_exists('tool_api_providers', 'dify_tool_providers',
                  ['id', 'tenant_id', 'name', 'label', 'icon', 'icon_background',
                   'schema_type', 'schema', 'provider_type', 'privacy_policy',
                   'custom_disclaimer', 'created_at', 'updated_at'])
    migrate_table_if_exists('tool_builtin_providers', 'dify_tool_providers',
                  ['id', 'tenant_id', 'name', 'label', 'icon', 'icon_background',
                   'schema_type', 'schema', 'provider_type', 'privacy_policy',
                   'custom_disclaimer', 'created_at', 'updated_at'])
    migrate_table_if_exists('tool_mcp_providers', 'dify_tool_providers',
                  ['id', 'tenant_id', 'name', 'label', 'icon', 'icon_background',
                   'schema_type', 'schema', 'provider_type', 'privacy_policy',
                   'custom_disclaimer', 'created_at', 'updated_at'])
    migrate_table_if_exists('tool_workflow_providers', 'dify_tool_providers',
                  ['id', 'tenant_id', 'name', 'label', 'icon', 'icon_background',
                   'schema_type', 'schema', 'provider_type', 'privacy_policy',
                   'custom_disclaimer', 'created_at', 'updated_at'])
    migrate_table_if_exists('datasource_providers', 'dify_datasource_providers',
                  ['id', 'tenant_id', 'provider_name', 'provider_type',
                   'credential_id', 'is_valid', 'created_at', 'updated_at'])

    # 15. 对话历史和消息
    print('[15/15] 迁移对话历史...')
    migrate_table_if_exists('conversations', 'dify_conversations',
                  ['id', 'app_id', 'user_id', 'name', 'inputs', 'introduction',
                   'system_instruction', 'status', 'from_source', 'from_end_user_id',
                   'from_account_id', 'read_at', 'created_at', 'updated_at'])
    migrate_table_if_exists('messages', 'dify_messages',
                  ['id', 'app_id', 'model_provider', 'model_id', 'conversation_id',
                   'inputs', 'query', 'message', 'message_tokens', 'message_unit_price',
                   'answer', 'answer_tokens', 'answer_unit_price', 'provider_response_latency',
                   'total_price', 'currency', 'from_source', 'from_end_user_id',
                   'from_account_id', 'created_at', 'updated_at'])

    print()
    print('=== 迁移完成 ===')
    print()
    print('提示：迁移完成后，可以停止 Dify 服务（PostgreSQL + Dify API），')
    print('      熵舟平台将使用本地 MySQL 中的数据独立运行。')
    print()
    print('下一步：')
    print('  1. 运行后端服务，确认数据正常')
    print('  2. 重构后端路由，将 Dify 查询替换为 MySQL 查询')
    print('  3. 停止 Dify 服务，验证平台独立运行')


def init_mysql_database():
    """初始化 MySQL 数据库（创建 szagent 库，如果不存在）"""
    import pymysql
    from config import DB_CONFIG

    # 连接到 MySQL（不指定数据库）
    conn = pymysql.connect(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        charset=DB_CONFIG['charset']
    )
    try:
        cur = conn.cursor()
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']} "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
        print(f"  数据库 {DB_CONFIG['database']} 已就绪")
    finally:
        conn.close()


def verify_migration():
    """验证迁移结果"""
    from config import get_db

    print()
    print('=== 验证迁移结果 ===')

    db = get_db()
    try:
        cur = db.cursor()
        tables = [
            ('dify_tenants', '租户'),
            ('dify_accounts', '账号'),
            ('dify_apps', '应用'),
            ('dify_workflows', '工作流'),
            ('dify_datasets', '知识库'),
            ('dify_documents', '文档'),
            ('dify_document_segments', '知识分段'),
            ('dify_conversations', '对话'),
            ('dify_messages', '消息'),
            ('dify_providers', '模型供应商'),
        ]

        for table, label in tables:
            try:
                cur.execute(f'SELECT COUNT(*) as cnt FROM {table}')
                row = cur.fetchone()
                count = row['cnt'] if row else 0
                print(f'  {label} ({table}): {count} 条')
            except Exception as e:
                print(f'  {label} ({table}): 查询失败 - {e}')
    finally:
        db.close()


def migrate_model_configs_from_providers():
    """
    从 Dify 的 providers 表提取模型配置，迁移到 model_configs 表
    这样 LLM 和 Embedding 服务可以直接使用
    """
    import psycopg2
    import psycopg2.extras

    print()
    print('=== 从 Dify Providers 提取模型配置 ===')

    pg_conn = psycopg2.connect(**DIFY_DB_CONFIG)
    try:
        pg_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # 查询有凭证的 provider
        pg_cur.execute('''
            SELECT * FROM providers
            WHERE credential IS NOT NULL AND credential != ''
        ''')
        rows = pg_cur.fetchall()
        pg_cur.close()
    finally:
        pg_conn.close()

    if not rows:
        print('  未找到模型配置')
        return

    from config import get_db
    db = get_db()
    try:
        cur = db.cursor()
        count = 0
        for row in rows:
            provider_name = row.get('provider_name', '')
            credential = row.get('credential', {})

            if isinstance(credential, str):
                try:
                    credential = json.loads(credential)
                except json.JSONDecodeError:
                    continue

            if not isinstance(credential, dict):
                continue

            # 提取 API Key 和 Base URL
            api_key = credential.get('api_key', '')
            base_url = credential.get('openai_api_base', '') or credential.get('base_url', '')

            if not api_key:
                continue

            # 生成唯一名称
            credential_name = f"dify_{provider_name}"

            try:
                cur.execute('''
                    INSERT INTO model_configs
                    (credential_name, provider, model_name, model_type, api_key, api_base_url, extra_config)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        api_key = VALUES(api_key),
                        api_base_url = VALUES(api_base_url),
                        extra_config = VALUES(extra_config),
                        updated_at = CURRENT_TIMESTAMP
                ''', (
                    credential_name,
                    provider_name,
                    credential.get('model_name', 'unknown'),
                    'llm',
                    api_key,
                    base_url,
                    json.dumps(credential, ensure_ascii=False),
                ))
                count += 1
            except Exception as e:
                print(f'  插入失败: {e}, provider={provider_name}')

        db.commit()
        print(f'  迁移了 {count} 个模型配置')
    finally:
        db.close()


if __name__ == '__main__':
    print('╔══════════════════════════════════════════════════════════╗')
    print('║     熵舟平台 - 从 Dify 迁移数据到 MySQL                 ║')
    print('╚══════════════════════════════════════════════════════════╝')
    print()

    # 0. 初始化数据库
    print('[初始化] 检查 MySQL 数据库...')
    init_mysql_database()

    # 1. 执行主迁移
    run_migration()

    # 2. 提取模型配置
    migrate_model_configs_from_providers()

    # 3. 验证结果
    verify_migration()

    print()
    print('╔══════════════════════════════════════════════════════════╗')
    print('║     迁移完成！                                           ║')
    print('╚══════════════════════════════════════════════════════════╝')
