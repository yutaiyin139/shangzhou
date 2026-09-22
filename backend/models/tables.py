# -*- coding: utf-8 -*-
"""数据表结构定义"""

# ============================================================
# 用户权限表（登录、角色、权限管理）
# ============================================================

USERS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    account_id VARCHAR(36) NOT NULL COMMENT '关联 dify_accounts.id',
    phone VARCHAR(20) DEFAULT '',
    status TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_account_id (account_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

ROLES_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(500) DEFAULT '',
    status TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_role_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

USER_ROLES_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS user_roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL COMMENT '关联 dify_accounts.id',
    role_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_role_id (role_id),
    UNIQUE KEY uk_user_role (user_id, role_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

PERMISSIONS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(100) NOT NULL,
    module VARCHAR(50) DEFAULT '',
    description VARCHAR(500) DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_perm_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

ROLE_PERMISSIONS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS role_permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    role_id INT NOT NULL,
    permission_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_role_id (role_id),
    INDEX idx_permission_id (permission_id),
    UNIQUE KEY uk_role_perm (role_id, permission_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

AGENTS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS agents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(100) DEFAULT '',
    description TEXT,
    icon VARCHAR(16) DEFAULT '🤖',
    status VARCHAR(20) DEFAULT 'draft',
    created_at DATETIME,
    updated_at DATETIME
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

MEMORIES_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS memories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    agent_id INT NOT NULL,
    content TEXT,
    -- 向量化字段（与 dify_document_segments 同构，便于统一检索）
    embedding JSON COMMENT 'embedding 向量',
    embedding_model VARCHAR(100) DEFAULT '' COMMENT 'embedding 模型',
    embedding_status VARCHAR(20) DEFAULT 'pending' COMMENT 'pending/completed/failed',
    created_at DATETIME,
    updated_at DATETIME,
    INDEX idx_agent_id (agent_id),
    INDEX idx_embedding_status (embedding_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

TOOL_INSTALLS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS tool_installs (
    tool_id VARCHAR(50) PRIMARY KEY,
    installed_at VARCHAR(30)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

TOOL_CALL_LOGS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS tool_call_logs (
    id VARCHAR(36) PRIMARY KEY,
    workflow_run_id VARCHAR(36) COMMENT '关联的工作流运行 ID',
    node_id VARCHAR(50) NOT NULL,
    node_type VARCHAR(30) NOT NULL,
    provider_id VARCHAR(50) NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    parameters TEXT COMMENT '调用参数 JSON',
    result TEXT COMMENT '调用结果',
    status VARCHAR(20) NOT NULL COMMENT 'success/error',
    error_message TEXT,
    elapsed_ms INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_workflow_run (workflow_run_id),
    INDEX idx_provider (provider_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

WORKFLOW_TOOLS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS workflow_tools (
    id VARCHAR(36) PRIMARY KEY,
    app_id VARCHAR(36) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    input_schema TEXT NOT NULL COMMENT '输入参数 JSON Schema',
    output_schema TEXT COMMENT '输出参数 JSON Schema',
    api_token VARCHAR(64) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    call_count INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_app_id (app_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

TOOL_SETTINGS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS tool_settings (
    id INT PRIMARY KEY,
    mode VARCHAR(20) NOT NULL DEFAULT 'patch',
    update_time VARCHAR(10) NOT NULL DEFAULT '19:45',
    scope VARCHAR(20) NOT NULL DEFAULT 'all',
    updated_at VARCHAR(30)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

SKILLS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS skills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(500) DEFAULT '',
    icon VARCHAR(50) DEFAULT '✨',
    category VARCHAR(50) DEFAULT '其他',
    kind VARCHAR(20) NOT NULL DEFAULT 'custom',
    content MEDIUMTEXT,
    created_at VARCHAR(30),
    updated_at VARCHAR(30)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

SKILL_INSTALLS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS skill_installs (
    skill_key VARCHAR(100) PRIMARY KEY,
    installed_at VARCHAR(30)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

AGENT_SKILL_BINDINGS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS agent_skill_bindings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    agent_id INT NOT NULL,
    skill_key VARCHAR(100) NOT NULL,
    skill_name VARCHAR(100) DEFAULT '',
    skill_icon VARCHAR(50) DEFAULT '✨',
    skill_kind VARCHAR(20) DEFAULT 'builtin',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_agent_skill (agent_id, skill_key),
    INDEX idx_agent_id (agent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

AGENT_CONFIG_REVISIONS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS agent_config_revisions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    agent_id INT NOT NULL,
    config_json TEXT NOT NULL COMMENT '配置快照 JSON',
    strategy VARCHAR(30) DEFAULT 'react' COMMENT '策略类型',
    change_note VARCHAR(200) DEFAULT '' COMMENT '变更说明',
    created_by INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_agent_id (agent_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

MCP_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS mcp_servers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  mtype VARCHAR(20) NOT NULL DEFAULT 'http',
  url VARCHAR(500) DEFAULT '',
  command VARCHAR(500) DEFAULT '',
  headers TEXT,
  env TEXT,
  remark VARCHAR(500) DEFAULT '',
  enabled TINYINT(1) DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'''

DATA_SOURCES_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS data_sources (
  id INT AUTO_INCREMENT PRIMARY KEY,
  ds_key VARCHAR(50) NOT NULL UNIQUE,
  status VARCHAR(20) NOT NULL DEFAULT 'installed',
  config TEXT,
  installed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'''

CUSTOM_CONNECTORS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS custom_connectors (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  ctype VARCHAR(20) NOT NULL DEFAULT 'http',
  endpoint VARCHAR(500) DEFAULT '',
  auth_type VARCHAR(20) NOT NULL DEFAULT 'none',
  auth_value VARCHAR(500) DEFAULT '',
  description VARCHAR(500) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'''

APP_TEMPLATES_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS app_templates (
  id INT AUTO_INCREMENT PRIMARY KEY,
  marketplace_id VARCHAR(50) NOT NULL UNIQUE,
  name VARCHAR(200) NOT NULL,
  description TEXT,
  overview LONGTEXT,
  kind VARCHAR(50) DEFAULT '',
  icon VARCHAR(50) DEFAULT '',
  icon_background VARCHAR(50) DEFAULT '',
  categories_json TEXT,
  display_category VARCHAR(50) DEFAULT '',
  tags_json TEXT,
  icon_url VARCHAR(500) DEFAULT '',
  dsl_path VARCHAR(500) DEFAULT '',
  dsl_yaml LONGTEXT,
  deps_json TEXT,
  source VARCHAR(50) DEFAULT 'dify-marketplace',
  status VARCHAR(20) DEFAULT 'active',
  synced_at DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'''

WORKFLOW_VERSIONS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS workflow_versions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  app_id VARCHAR(36) NOT NULL,
  version_number INT NOT NULL DEFAULT 1,
  name VARCHAR(200) DEFAULT '',
  comment VARCHAR(500) DEFAULT '',
  graph_json LONGTEXT,
  features_json TEXT,
  env_vars_json TEXT,
  conv_vars_json TEXT,
  created_by VARCHAR(50) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_app_id (app_id),
  INDEX idx_version_number (app_id, version_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'''

WORKFLOW_TEST_RUNS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS workflow_test_runs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  app_id VARCHAR(36) NOT NULL,
  run_name VARCHAR(200) DEFAULT '',
  inputs_json TEXT,
  outputs_json TEXT,
  status VARCHAR(30) DEFAULT '',
  error TEXT,
  elapsed_time FLOAT DEFAULT NULL,
  total_tokens INT DEFAULT 0,
  total_steps INT DEFAULT 0,
  nodes_json TEXT,
  created_by VARCHAR(50) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_app_id (app_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'''

# ============================================================
# 模型配置表（LLM/Embedding 模型配置）
# ============================================================

MODEL_CONFIGS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS model_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    credential_name VARCHAR(255) NOT NULL COMMENT '凭据名称',
    provider VARCHAR(255) NOT NULL COMMENT '供应商标识（如 openai, deepseek）',
    provider_label VARCHAR(255) DEFAULT '' COMMENT '供应商显示名称（如 OpenAI, DeepSeek）',
    model_name VARCHAR(255) NOT NULL COMMENT '模型名称',
    model_type VARCHAR(50) NOT NULL DEFAULT 'llm' COMMENT '模型类型：llm/embedding/rerank/tts/stt',
    model_label VARCHAR(255) DEFAULT '' COMMENT '模型显示名称',
    api_key VARCHAR(500) NOT NULL COMMENT 'API Key（加密存储）',
    api_base_url VARCHAR(500) DEFAULT '' COMMENT 'API Base URL',
    -- 模型参数配置
    temperature DECIMAL(3,2) DEFAULT 0.7 COMMENT '温度',
    max_tokens INT DEFAULT 2048 COMMENT '最大 token 数',
    top_p DECIMAL(3,2) DEFAULT 1.0 COMMENT 'Top P',
    presence_penalty DECIMAL(3,2) DEFAULT 0.0 COMMENT '存在惩罚',
    frequency_penalty DECIMAL(3,2) DEFAULT 0.0 COMMENT '频率惩罚',
    -- 模型能力
    supports_vision TINYINT(1) DEFAULT 0 COMMENT '支持视觉',
    supports_function_calling TINYINT(1) DEFAULT 0 COMMENT '支持函数调用',
    supports_streaming TINYINT(1) DEFAULT 1 COMMENT '支持流式',
    context_size INT DEFAULT 4096 COMMENT '上下文窗口大小',
    -- 配置类型
    config_type VARCHAR(20) DEFAULT 'credential' COMMENT '配置类型：credential/model',
    extra_config TEXT COMMENT '扩展配置 JSON',
    status TINYINT(1) DEFAULT 1 COMMENT '状态：1=启用，0=禁用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_credential (credential_name),
    INDEX idx_provider (provider),
    INDEX idx_model_type (model_type),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 模型供应商配置表（存储 93 个供应商的元数据和配置模板）
# ============================================================

MODEL_PROVIDER_CONFIGS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS model_provider_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    provider_name VARCHAR(100) NOT NULL COMMENT '供应商标识（如 openai）',
    provider_label VARCHAR(100) NOT NULL COMMENT '供应商显示名称（如 OpenAI）',
    description TEXT COMMENT '供应商描述',
    icon VARCHAR(50) DEFAULT '🤖' COMMENT '图标 emoji',
    icon_background VARCHAR(20) DEFAULT '#E8F3FF' COMMENT '图标背景色',
    -- 配置方式
    credential_type VARCHAR(20) DEFAULT 'api_key' COMMENT '认证方式：api_key/oauth2/none',
    authorization_url VARCHAR(500) DEFAULT '' COMMENT 'OAuth 授权 URL',
    token_url VARCHAR(500) DEFAULT '' COMMENT 'OAuth Token URL',
    -- 默认配置
    default_base_url VARCHAR(500) DEFAULT '' COMMENT '默认 API Base URL',
    -- 支持的模型类型
    supported_model_types TEXT COMMENT '支持的模型类型 JSON 数组',
    -- 配置 schema（定义前端表单字段）
    config_schema TEXT COMMENT '配置字段 JSON Schema',
    -- 帮助信息
    help_url VARCHAR(500) DEFAULT '' COMMENT '帮助文档 URL',
    help_text TEXT COMMENT '帮助提示文本',
    -- 状态
    is_built_in TINYINT(1) DEFAULT 0 COMMENT '是否内置',
    status TINYINT(1) DEFAULT 1 COMMENT '状态：1=可用，0=禁用',
    install_count INT DEFAULT 0 COMMENT '安装次数统计',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_provider_name (provider_name),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 模型定义表（每个供应商的可用模型列表）
# ============================================================

MODEL_DEFINITIONS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS model_definitions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    provider_name VARCHAR(100) NOT NULL COMMENT '供应商标识',
    model_name VARCHAR(100) NOT NULL COMMENT '模型标识（如 gpt-4）',
    model_label VARCHAR(100) DEFAULT '' COMMENT '模型显示名称',
    model_type VARCHAR(20) NOT NULL DEFAULT 'llm' COMMENT '模型类型：llm/embedding/rerank/tts/stt',
    -- 模型属性
    context_size INT DEFAULT 4096 COMMENT '上下文窗口',
    max_output_tokens INT DEFAULT 2048 COMMENT '最大输出 token',
    supports_vision TINYINT(1) DEFAULT 0 COMMENT '支持视觉',
    supports_function_calling TINYINT(1) DEFAULT 0 COMMENT '支持函数调用',
    supports_streaming TINYINT(1) DEFAULT 1 COMMENT '支持流式',
    -- 定价（可选）
    input_price DECIMAL(10,6) DEFAULT 0 COMMENT '输入价格（每 1K tokens）',
    output_price DECIMAL(10,6) DEFAULT 0 COMMENT '输出价格（每 1K tokens）',
    -- 状态
    status TINYINT(1) DEFAULT 1 COMMENT '状态：1=可用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_provider_model (provider_name, model_name),
    INDEX idx_provider (provider_name),
    INDEX idx_model_type (model_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# Dify 兼容表（迁移到 MySQL，替代 Dify PostgreSQL）
# ============================================================

DIFY_APPS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_apps (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    mode VARCHAR(50) NOT NULL DEFAULT 'workflow',
    icon VARCHAR(50) DEFAULT '🤖',
    icon_background VARCHAR(50) DEFAULT '#FFEAD5',
    icon_type VARCHAR(20) DEFAULT 'emoji',
    description TEXT,
    app_model_config_id VARCHAR(36) DEFAULT NULL,
    status VARCHAR(20) DEFAULT 'normal',
    enable_site TINYINT(1) DEFAULT 1,
    enable_api TINYINT(1) DEFAULT 1,
    api_rpm INT DEFAULT 0,
    api_rph INT DEFAULT 0,
    is_demo TINYINT(1) DEFAULT 0,
    is_public TINYINT(1) DEFAULT 0,
    is_universal TINYINT(1) DEFAULT 0,
    workflow_id VARCHAR(36) DEFAULT NULL,
    created_by VARCHAR(36) DEFAULT NULL,
    updated_by VARCHAR(36) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    use_icon_as_answer_icon TINYINT(1) DEFAULT 0,
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_status (status),
    INDEX idx_mode (mode)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

DIFY_WORKFLOWS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_workflows (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    app_id VARCHAR(36) NOT NULL,
    type VARCHAR(20) NOT NULL DEFAULT 'workflow',
    version VARCHAR(50) DEFAULT 'draft',
    graph LONGTEXT,
    features TEXT,
    environment_variables TEXT,
    conversation_variables TEXT,
    rag_pipeline_variables TEXT,
    marked_name VARCHAR(255) DEFAULT '',
    marked_comment VARCHAR(500) DEFAULT '',
    kind VARCHAR(20) DEFAULT 'standard',
    version_number INT DEFAULT NULL,
    created_by VARCHAR(36) DEFAULT NULL,
    updated_by VARCHAR(36) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_app_id (app_id),
    INDEX idx_tenant_id (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

DIFY_WORKFLOW_RUNS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_workflow_runs (
    id VARCHAR(36) PRIMARY KEY,
    app_id VARCHAR(36) NOT NULL,
    tenant_id VARCHAR(36) NOT NULL,
    workflow_id VARCHAR(36) DEFAULT NULL,
    status VARCHAR(30) DEFAULT 'running',
    inputs MEDIUMTEXT,
    outputs MEDIUMTEXT,
    error TEXT,
    elapsed_time FLOAT DEFAULT NULL,
    total_tokens INT DEFAULT 0,
    total_steps INT DEFAULT 0,
    created_by VARCHAR(36) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    finished_at DATETIME DEFAULT NULL,
    INDEX idx_app_id (app_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

DIFY_WORKFLOW_NODE_EXECUTIONS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_workflow_node_executions (
    id VARCHAR(36) PRIMARY KEY,
    app_id VARCHAR(36) NOT NULL,
    workflow_run_id VARCHAR(36) NOT NULL,
    node_id VARCHAR(100) NOT NULL,
    node_type VARCHAR(50) DEFAULT '',
    title VARCHAR(255) DEFAULT '',
    inputs MEDIUMTEXT,
    outputs MEDIUMTEXT,
    status VARCHAR(30) DEFAULT 'running',
    error TEXT,
    elapsed_time FLOAT DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    finished_at DATETIME DEFAULT NULL,
    INDEX idx_workflow_run_id (workflow_run_id),
    INDEX idx_app_id (app_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

DIFY_WORKFLOW_VERSION_COUNTERS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_workflow_version_counters (
    app_id VARCHAR(36) PRIMARY KEY,
    last_version_number INT DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

DIFY_APP_MODEL_CONFIGS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_app_model_configs (
    id VARCHAR(36) PRIMARY KEY,
    app_id VARCHAR(36) NOT NULL,
    provider VARCHAR(255) DEFAULT NULL,
    model_id VARCHAR(255) DEFAULT NULL,
    configs TEXT,
    model TEXT,
    opening_statement TEXT,
    suggested_questions TEXT,
    pre_prompt TEXT,
    prompt_type VARCHAR(20) DEFAULT 'simple',
    created_by VARCHAR(36) DEFAULT NULL,
    updated_by VARCHAR(36) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_app_id (app_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

DIFY_SITES_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_sites (
    id VARCHAR(36) PRIMARY KEY,
    app_id VARCHAR(36) NOT NULL,
    title VARCHAR(255) DEFAULT '',
    icon VARCHAR(50) DEFAULT '',
    icon_background VARCHAR(50) DEFAULT '',
    description TEXT,
    default_language VARCHAR(20) DEFAULT 'zh-Hans',
    customize_token_strategy VARCHAR(30) DEFAULT 'not_allowed',
    prompt_public TINYINT(1) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'normal',
    custom_disclaimer TEXT,
    show_workflow_steps TINYINT(1) DEFAULT 1,
    use_icon_as_answer_icon TINYINT(1) DEFAULT 0,
    code VARCHAR(32) DEFAULT '',
    created_by VARCHAR(36) DEFAULT NULL,
    updated_by VARCHAR(36) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_app_id (app_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

DIFY_API_TOKENS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_api_tokens (
    id VARCHAR(36) PRIMARY KEY,
    app_id VARCHAR(36) NOT NULL,
    tenant_id VARCHAR(36) NOT NULL,
    type VARCHAR(20) DEFAULT 'app',
    token VARCHAR(100) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_app_id (app_id),
    INDEX idx_token (token)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

DIFY_DATASETS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_datasets (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    indexing_technique VARCHAR(50) DEFAULT 'high_quality',
    index_struct TEXT,
    created_by VARCHAR(36) DEFAULT NULL,
    updated_by VARCHAR(36) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tenant_id (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

DIFY_DOCUMENTS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_documents (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    dataset_id VARCHAR(36) NOT NULL,
    position INT DEFAULT 0,
    data_source_type VARCHAR(30) DEFAULT 'upload_file',
    data_source_info TEXT,
    batch VARCHAR(100) DEFAULT '',
    name VARCHAR(255) DEFAULT '',
    created_from VARCHAR(20) DEFAULT 'api',
    created_by VARCHAR(36) DEFAULT NULL,
    indexing_status VARCHAR(20) DEFAULT 'waiting',
    enabled TINYINT(1) DEFAULT 1,
    word_count INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_dataset_id (dataset_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

DIFY_DOCUMENT_SEGMENTS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_document_segments (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    dataset_id VARCHAR(36) NOT NULL,
    document_id VARCHAR(36) NOT NULL,
    position INT DEFAULT 0,
    content TEXT,
    word_count INT DEFAULT 0,
    tokens INT DEFAULT 0,
    hit_count INT DEFAULT 0,
    enabled TINYINT(1) DEFAULT 1,
    status VARCHAR(20) DEFAULT 'completed',
    embedding LONGTEXT DEFAULT NULL,
    embedding_model VARCHAR(100) DEFAULT NULL,
    embedding_status VARCHAR(20) DEFAULT 'pending',
    parent_id VARCHAR(36) DEFAULT NULL,
    segment_type VARCHAR(20) DEFAULT 'general',
    metadata TEXT,
    created_by VARCHAR(36) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_dataset_id (dataset_id),
    INDEX idx_document_id (document_id),
    INDEX idx_status (status),
    INDEX idx_embedding_status (embedding_status),
    INDEX idx_parent_id (parent_id),
    INDEX idx_segment_type (segment_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# 用户/租户表（替代 Dify accounts/tenants）
DIFY_ACCOUNTS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_accounts (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    nickname VARCHAR(255) DEFAULT '' COMMENT '昵称（可选）',
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20) DEFAULT '' COMMENT '电话号码',
    password TEXT,
    password_salt TEXT,
    interface_language VARCHAR(20) DEFAULT 'zh-Hans',
    interface_theme VARCHAR(20) DEFAULT 'light',
    status VARCHAR(20) DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_email (email),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

DIFY_TENANTS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_tenants (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    plan VARCHAR(50) DEFAULT 'basic',
    status VARCHAR(20) DEFAULT 'normal',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

DIFY_TENANT_ACCOUNT_JOINS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_tenant_account_joins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    account_id VARCHAR(36) NOT NULL,
    role VARCHAR(20) DEFAULT 'owner',
    current TINYINT(1) DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_account_id (account_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# 模型供应商表
DIFY_PROVIDERS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_providers (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) DEFAULT NULL,
    provider_name VARCHAR(255) NOT NULL,
    provider_type VARCHAR(50) DEFAULT 'custom',
    credential_id VARCHAR(36) DEFAULT NULL,
    is_valid TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tenant_id (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

DIFY_PROVIDER_MODELS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_provider_models (
    id VARCHAR(36) PRIMARY KEY,
    provider_name VARCHAR(255) NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    is_valid TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_provider_name (provider_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# 工具供应商表
DIFY_TOOL_PROVIDERS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_tool_providers (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    tool_name VARCHAR(255) NOT NULL,
    tool_type VARCHAR(50) DEFAULT 'builtin',
    credential TEXT,
    is_valid TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_tool_name (tool_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

DIFY_DATASOURCE_PROVIDERS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_datasource_providers (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    datasource_type VARCHAR(50) NOT NULL,
    credential TEXT,
    is_valid TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tenant_id (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 内置工具提供者表（P0: 工具多提供者管理）
# ============================================================

# ============================================================
# 工具标签绑定表（3.5: 工具标签体系）
# ============================================================

TOOL_LABEL_BINDINGS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS tool_label_bindings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tool_type VARCHAR(20) NOT NULL COMMENT '工具类型：builtin/api/workflow/mcp',
    tool_id VARCHAR(36) NOT NULL COMMENT '工具 ID（提供者或具体工具）',
    label VARCHAR(100) NOT NULL COMMENT '标签名',
    label_type VARCHAR(20) DEFAULT 'custom' COMMENT '标签类型：builtin/custom',
    created_by VARCHAR(36) DEFAULT NULL COMMENT '创建者 ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_tool_label (tool_type, tool_id, label),
    INDEX idx_label (label),
    INDEX idx_tool (tool_type, tool_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 工具 OAuth 客户端表（3.4: system/tenant 双端）
# ============================================================

TOOL_OAUTH_SYSTEM_CLIENTS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS tool_oauth_system_clients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    provider_name VARCHAR(100) NOT NULL COMMENT '工具提供者名称',
    client_id VARCHAR(500) NOT NULL COMMENT 'OAuth Client ID',
    client_secret VARCHAR(500) NOT NULL COMMENT 'OAuth Client Secret（加密存储）',
    auth_url VARCHAR(1024) NOT NULL COMMENT '授权 URL 模板',
    token_url VARCHAR(1024) NOT NULL COMMENT 'Token 交换 URL',
    redirect_uri VARCHAR(1024) DEFAULT '' COMMENT '回调 URI',
    scopes VARCHAR(500) DEFAULT '' COMMENT '授权范围',
    extra_params TEXT COMMENT '额外参数 JSON',
    status TINYINT(1) DEFAULT 1 COMMENT '状态：1=启用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_provider (provider_name),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

TOOL_OAUTH_TENANT_CLIENTS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS tool_oauth_tenant_clients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL COMMENT '租户 ID',
    provider_name VARCHAR(100) NOT NULL COMMENT '工具提供者名称',
    client_id VARCHAR(500) NOT NULL COMMENT 'OAuth Client ID',
    client_secret VARCHAR(500) NOT NULL COMMENT 'OAuth Client Secret（加密存储）',
    auth_url VARCHAR(1024) NOT NULL COMMENT '授权 URL 模板',
    token_url VARCHAR(1024) NOT NULL COMMENT 'Token 交换 URL',
    redirect_uri VARCHAR(1024) DEFAULT '' COMMENT '回调 URI',
    scopes VARCHAR(500) DEFAULT '' COMMENT '授权范围',
    extra_params TEXT COMMENT '额外参数 JSON',
    status TINYINT(1) DEFAULT 1 COMMENT '状态：1=启用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_tenant_provider (tenant_id, provider_name),
    INDEX idx_tenant (tenant_id),
    INDEX idx_provider (provider_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

TOOL_OAUTH_TOKENS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS tool_oauth_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL COMMENT '租户 ID',
    provider_name VARCHAR(100) NOT NULL COMMENT '工具提供者名称',
    access_token TEXT COMMENT '访问令牌（加密存储）',
    refresh_token TEXT COMMENT '刷新令牌（加密存储）',
    expires_at DATETIME DEFAULT NULL COMMENT '过期时间',
    scopes VARCHAR(500) DEFAULT '' COMMENT '授权范围',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态：active/expired/revoked',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_tenant_provider (tenant_id, provider_name),
    INDEX idx_tenant (tenant_id),
    INDEX idx_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

TOOL_BUILTIN_PROVIDERS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS tool_builtin_providers (
    id VARCHAR(36) PRIMARY KEY COMMENT '提供者 ID（与 builtin_tools.py 中的 id 一致）',
    tenant_id VARCHAR(36) DEFAULT NULL COMMENT '租户 ID（NULL = 全局）',
    provider_name VARCHAR(100) NOT NULL COMMENT '提供者名称',
    provider_label VARCHAR(100) NOT NULL COMMENT '显示名称',
    description TEXT COMMENT '提供者描述',
    icon VARCHAR(50) DEFAULT '🔧' COMMENT '图标 emoji',
    icon_background VARCHAR(20) DEFAULT '#E8F3FF' COMMENT '图标背景色',
    category VARCHAR(50) DEFAULT 'utility' COMMENT '分类：search/communication/data/utility/ai',
    actions_json TEXT NOT NULL COMMENT '工具动作 JSON 数组',
    credential_schema TEXT COMMENT '凭证配置 JSON Schema',
    is_authenticated TINYINT(1) DEFAULT 0 COMMENT '是否需要认证',
    install_scope VARCHAR(20) DEFAULT 'global' COMMENT '安装范围：global/tenant',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态：active/inactive/deprecated',
    version VARCHAR(20) DEFAULT '1.0.0' COMMENT '工具版本号',
    installed_at DATETIME DEFAULT NULL COMMENT '安装时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_provider_name (provider_name),
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_category (category),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# API 工具提供者表（P0: 自定义 OpenAPI 工具持久化）
# ============================================================

TOOL_API_PROVIDERS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS tool_api_providers (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL COMMENT '租户 ID',
    app_id VARCHAR(36) DEFAULT NULL COMMENT '关联应用 ID',
    name VARCHAR(100) NOT NULL COMMENT '提供者名称',
    description TEXT COMMENT '描述',
    icon VARCHAR(50) DEFAULT '🔌' COMMENT '图标',
    icon_background VARCHAR(20) DEFAULT '#FFF3E0' COMMENT '图标背景色',
    server_url VARCHAR(500) NOT NULL COMMENT 'API 服务器 URL',
    openapi_schema LONGTEXT COMMENT 'OpenAPI Schema JSON',
    actions_json TEXT COMMENT '工具动作 JSON 数组',
    auth_type VARCHAR(20) DEFAULT 'none' COMMENT '认证类型：none/api_key/bearer/basic/oauth2',
    auth_config TEXT COMMENT '认证配置 JSON（加密存储）',
    headers_json TEXT COMMENT '自定义请求头 JSON',
    timeout_ms INT DEFAULT 30000 COMMENT '请求超时毫秒',
    is_public TINYINT(1) DEFAULT 0 COMMENT '是否公开',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态：active/inactive/error',
    last_tested_at DATETIME DEFAULT NULL COMMENT '最后测试时间',
    last_error TEXT COMMENT '最后错误信息',
    created_by VARCHAR(36) DEFAULT NULL COMMENT '创建者 ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_app_id (app_id),
    INDEX idx_status (status),
    INDEX idx_created_by (created_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 工作流工具提供者表（P0: 工作流发布为工具后的管理）
# ============================================================

TOOL_WORKFLOW_PROVIDERS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS tool_workflow_providers (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL COMMENT '租户 ID',
    app_id VARCHAR(36) NOT NULL COMMENT '关联应用 ID',
    workflow_id VARCHAR(36) NOT NULL COMMENT '关联工作流 ID',
    workflow_tool_id VARCHAR(36) NOT NULL COMMENT '关联 workflow_tools.id',
    name VARCHAR(100) NOT NULL COMMENT '工具名称',
    description TEXT COMMENT '工具描述',
    icon VARCHAR(50) DEFAULT '⚙️' COMMENT '图标',
    icon_background VARCHAR(20) DEFAULT '#F3E5F5' COMMENT '图标背景色',
    input_schema TEXT NOT NULL COMMENT '输入参数 JSON Schema',
    output_schema TEXT COMMENT '输出参数 JSON Schema',
    is_public TINYINT(1) DEFAULT 0 COMMENT '是否公开',
    call_count INT DEFAULT 0 COMMENT '调用次数',
    avg_latency_ms INT DEFAULT 0 COMMENT '平均延迟毫秒',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态：active/inactive/deprecated',
    last_called_at DATETIME DEFAULT NULL COMMENT '最后调用时间',
    created_by VARCHAR(36) DEFAULT NULL COMMENT '创建者 ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_workflow_tool_id (workflow_tool_id),
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_app_id (app_id),
    INDEX idx_status (status),
    INDEX idx_created_by (created_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# MCP 工具提供者表（P0: MCP 工具按服务器分组管理）
# ============================================================

TOOL_MCP_PROVIDERS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS tool_mcp_providers (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL COMMENT '租户 ID',
    server_id VARCHAR(36) NOT NULL COMMENT '关联 mcp_servers.id',
    server_name VARCHAR(100) NOT NULL COMMENT 'MCP 服务器名称（冗余存储）',
    tool_name VARCHAR(100) NOT NULL COMMENT '工具名称',
    tool_label VARCHAR(100) DEFAULT '' COMMENT '工具显示名称',
    description TEXT COMMENT '工具描述',
    icon VARCHAR(50) DEFAULT '🔗' COMMENT '图标',
    input_schema TEXT COMMENT '输入参数 JSON Schema',
    output_schema TEXT COMMENT '输出参数 JSON Schema',
    annotations_json TEXT COMMENT '工具注解 JSON',
    is_enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    call_count INT DEFAULT 0 COMMENT '调用次数',
    avg_latency_ms INT DEFAULT 0 COMMENT '平均延迟毫秒',
    last_called_at DATETIME DEFAULT NULL COMMENT '最后调用时间',
    last_error TEXT COMMENT '最后错误信息',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态：active/inactive/error',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_server_tool (server_id, tool_name),
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_server_id (server_id),
    INDEX idx_status (status),
    INDEX idx_is_enabled (is_enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 对话历史表（替代 Dify conversations/messages）
# ============================================================

DIFY_CONVERSATIONS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_conversations (
    id VARCHAR(36) PRIMARY KEY,
    app_id VARCHAR(36) DEFAULT NULL,
    agent_id INT DEFAULT NULL,
    user_id VARCHAR(36) DEFAULT NULL,
    title VARCHAR(255) DEFAULT '新对话',
    summary TEXT,
    model_provider VARCHAR(100) DEFAULT '',
    model_name VARCHAR(100) DEFAULT '',
    system_prompt TEXT,
    knowledge_ids TEXT,
    message_count INT DEFAULT 0,
    total_tokens INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',
    is_pinned TINYINT(1) DEFAULT 0,
    last_message_at DATETIME DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_app_id (app_id),
    INDEX idx_agent_id (agent_id),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_last_message_at (last_message_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

DIFY_MESSAGES_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_messages (
    id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL,
    role VARCHAR(20) NOT NULL,
    content LONGTEXT,
    tokens INT DEFAULT 0,
    model_provider VARCHAR(100) DEFAULT '',
    model_name VARCHAR(100) DEFAULT '',
    feedback TINYINT(1) DEFAULT 0,
    feedback_reason VARCHAR(255) DEFAULT '',
    metadata TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_role (role),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 消息反馈表（用户点赞/踩）
# ============================================================

DIFY_MESSAGE_FEEDBACKS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_message_feedbacks (
    id VARCHAR(36) PRIMARY KEY,
    message_id VARCHAR(36) NOT NULL COMMENT '关联 dify_messages.id',
    conversation_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) DEFAULT NULL,
    rating TINYINT(1) NOT NULL DEFAULT 1 COMMENT '1=点赞, -1=点踩',
    reason VARCHAR(500) DEFAULT '' COMMENT '反馈原因',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_message_user (message_id, user_id),
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_user_id (user_id),
    INDEX idx_rating (rating)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 上传文件表
# ============================================================

DIFY_UPLOAD_FILES_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_upload_files (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) DEFAULT NULL,
    conversation_id VARCHAR(36) DEFAULT NULL,
    message_id VARCHAR(36) DEFAULT NULL,
    original_name VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    file_size BIGINT DEFAULT 0,
    file_type VARCHAR(100) DEFAULT '',
    mime_type VARCHAR(100) DEFAULT '',
    extension VARCHAR(20) DEFAULT '',
    source VARCHAR(50) DEFAULT 'upload' COMMENT 'upload/paste/url',
    status VARCHAR(20) DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_user_id (user_id),
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 数据集权限表
# ============================================================

DIFY_DATASET_PERMISSIONS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_dataset_permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    dataset_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) DEFAULT NULL,
    role_id INT DEFAULT NULL,
    permission VARCHAR(20) NOT NULL DEFAULT 'read' COMMENT 'read/write/admin',
    granted_by VARCHAR(36) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_dataset_user (dataset_id, user_id),
    INDEX idx_dataset_id (dataset_id),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 应用-数据集关联表
# ============================================================

DIFY_APP_DATASET_JOINS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_app_dataset_joins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    app_id VARCHAR(36) NOT NULL,
    dataset_id VARCHAR(36) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_app_dataset (app_id, dataset_id),
    INDEX idx_app_id (app_id),
    INDEX idx_dataset_id (dataset_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 消息标注表（用于数据质量标注）
# ============================================================

DIFY_MESSAGE_ANNOTATIONS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_message_annotations (
    id VARCHAR(36) PRIMARY KEY,
    message_id VARCHAR(36) NOT NULL,
    conversation_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) DEFAULT NULL,
    annotation_type VARCHAR(50) DEFAULT 'quality' COMMENT 'quality/safety/relevance',
    content TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_message_id (message_id),
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 标注回复系统（Annotation Reply）
# ============================================================

# 标注 Q&A 库
DIFY_ANNOTATIONS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_annotations (
    id VARCHAR(36) PRIMARY KEY,
    app_id VARCHAR(36) NOT NULL,
    question TEXT NOT NULL COMMENT '问题',
    content TEXT NOT NULL COMMENT '标注答案',
    account_id VARCHAR(36) DEFAULT NULL COMMENT '创建者',
    collection_binding_id VARCHAR(36) DEFAULT NULL COMMENT '向量集合绑定',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_app_id (app_id),
    INDEX idx_account_id (account_id),
    INDEX idx_collection_binding (collection_binding_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# 应用标注回复设置
APP_ANNOTATION_SETTINGS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS app_annotation_settings (
    id VARCHAR(36) PRIMARY KEY,
    app_id VARCHAR(36) NOT NULL UNIQUE,
    score_threshold FLOAT DEFAULT 0.8 COMMENT '相似度阈值',
    collection_binding_id VARCHAR(36) DEFAULT NULL COMMENT '向量集合绑定',
    embedding_provider_name VARCHAR(100) DEFAULT NULL COMMENT '嵌入模型提供商',
    embedding_model_name VARCHAR(100) DEFAULT NULL COMMENT '嵌入模型名称',
    created_user_id VARCHAR(36) DEFAULT NULL,
    updated_user_id VARCHAR(36) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_app_id (app_id),
    INDEX idx_collection_binding (collection_binding_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# 标注命中历史
APP_ANNOTATION_HIT_HISTORY_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS app_annotation_hit_history (
    id VARCHAR(36) PRIMARY KEY,
    annotation_id VARCHAR(36) NOT NULL COMMENT '命中的标注ID',
    app_id VARCHAR(36) NOT NULL,
    message_id VARCHAR(36) DEFAULT NULL COMMENT '触发命中的消息ID',
    account_id VARCHAR(36) DEFAULT NULL COMMENT '用户ID',
    source VARCHAR(50) DEFAULT 'service_api' COMMENT '来源',
    score FLOAT DEFAULT 0 COMMENT '相似度分数',
    question TEXT COMMENT '用户原始问题',
    answer TEXT COMMENT '返回的标注答案',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_annotation_id (annotation_id),
    INDEX idx_app_id (app_id),
    INDEX idx_message_id (message_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# 数据集向量集合绑定
DATASET_COLLECTION_BINDINGS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dataset_collection_bindings (
    id VARCHAR(36) PRIMARY KEY,
    provider_name VARCHAR(100) NOT NULL COMMENT '嵌入提供商',
    model_name VARCHAR(100) NOT NULL COMMENT '嵌入模型',
    type VARCHAR(50) DEFAULT 'annotation' COMMENT 'collection类型',
    collection_name VARCHAR(255) NOT NULL COMMENT '向量集合名称',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_type (type),
    INDEX idx_collection_name (collection_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# 标注回复异步任务状态
ANNOTATION_REPLY_JOBS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS annotation_reply_jobs (
    id VARCHAR(36) PRIMARY KEY,
    app_id VARCHAR(36) NOT NULL,
    action VARCHAR(20) NOT NULL COMMENT 'enable/disable',
    status VARCHAR(20) DEFAULT 'running' COMMENT 'running/success/failed',
    total_annotations INT DEFAULT 0 COMMENT '总标注数',
    processed_annotations INT DEFAULT 0 COMMENT '已处理数',
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_app_id (app_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 操作日志表（审计日志）
# ============================================================

AUDIT_LOGS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dify_audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) DEFAULT NULL,
    user_name VARCHAR(255) DEFAULT '',
    user_email VARCHAR(255) DEFAULT '',
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) DEFAULT '',
    resource_id VARCHAR(100) DEFAULT '',
    resource_name VARCHAR(255) DEFAULT '',
    description TEXT,
    ip_address VARCHAR(50) DEFAULT '',
    user_agent VARCHAR(500) DEFAULT '',
    request_method VARCHAR(10) DEFAULT '',
    request_path VARCHAR(500) DEFAULT '',
    request_body TEXT,
    response_code INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'success',
    error_message TEXT,
    extra_data TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_action (action),
    INDEX idx_resource_type (resource_type),
    INDEX idx_resource_id (resource_id),
    INDEX idx_created_at (created_at),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 工作流模板库（P4: 保存/复用/分类/搜索）
# ============================================================

WORKFLOW_TEMPLATES_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS workflow_templates (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(200) NOT NULL COMMENT '模板名称',
    description TEXT COMMENT '模板描述',
    category VARCHAR(50) DEFAULT 'general' COMMENT '分类：general/analysis/automation/integration/data',
    tags_json TEXT COMMENT '标签 JSON 数组',
    icon VARCHAR(50) DEFAULT '📋' COMMENT '图标 emoji',
    icon_background VARCHAR(20) DEFAULT '#EAF1FE' COMMENT '图标背景色',
    graph_json LONGTEXT NOT NULL COMMENT '工作流图 JSON',
    inputs_json TEXT COMMENT '输入参数定义 JSON',
    outputs_json TEXT COMMENT '输出参数定义 JSON',
    version VARCHAR(20) DEFAULT '1.0.0' COMMENT '模板版本',
    author_id VARCHAR(36) DEFAULT NULL COMMENT '创建者 ID',
    author_name VARCHAR(100) DEFAULT '' COMMENT '创建者名称',
    is_public TINYINT(1) DEFAULT 1 COMMENT '是否公开',
    is_official TINYINT(1) DEFAULT 0 COMMENT '是否官方模板',
    usage_count INT DEFAULT 0 COMMENT '使用次数',
    rating DECIMAL(3,2) DEFAULT 0.00 COMMENT '评分 0-5',
    rating_count INT DEFAULT 0 COMMENT '评分次数',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态：active/inactive/deprecated',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category (category),
    INDEX idx_author (author_id),
    INDEX idx_status (status),
    INDEX idx_is_public (is_public),
    INDEX idx_created_at (created_at),
    FULLTEXT INDEX ft_name_desc (name, description)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# Agent 评估系统（P4: 自动评测/指标）
# ============================================================

AGENT_EVALUATIONS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS agent_evaluations (
    id VARCHAR(36) PRIMARY KEY,
    app_id VARCHAR(36) NOT NULL COMMENT '关联应用 ID',
    name VARCHAR(200) NOT NULL COMMENT '评估名称',
    description TEXT COMMENT '评估描述',
    dataset_json LONGTEXT NOT NULL COMMENT '评估数据集 JSON（输入+期望输出）',
    metrics_json TEXT COMMENT '评估指标配置 JSON',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态：pending/running/completed/failed',
    total_cases INT DEFAULT 0 COMMENT '总测试用例数',
    completed_cases INT DEFAULT 0 COMMENT '已完成用例数',
    passed_cases INT DEFAULT 0 COMMENT '通过用例数',
    avg_score DECIMAL(5,2) DEFAULT 0.00 COMMENT '平均得分',
    avg_latency_ms INT DEFAULT 0 COMMENT '平均延迟毫秒',
    total_tokens INT DEFAULT 0 COMMENT '总消耗 token',
    result_json LONGTEXT COMMENT '详细结果 JSON',
    started_at DATETIME DEFAULT NULL,
    completed_at DATETIME DEFAULT NULL,
    created_by VARCHAR(36) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_app_id (app_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 插件市场（P4: 发布/安装/管理）
# ============================================================

PLUGINS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS plugins (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '插件名称',
    plugin_type VARCHAR(30) NOT NULL COMMENT '类型：tool/workflow/agent/mcp',
    description TEXT COMMENT '插件描述',
    version VARCHAR(20) DEFAULT '1.0.0' COMMENT '版本号',
    author_id VARCHAR(36) DEFAULT NULL COMMENT '作者 ID',
    author_name VARCHAR(100) DEFAULT '' COMMENT '作者名称',
    icon VARCHAR(50) DEFAULT '🧩' COMMENT '图标',
    icon_background VARCHAR(20) DEFAULT '#F5E8FF' COMMENT '图标背景色',
    category VARCHAR(50) DEFAULT 'utility' COMMENT '分类',
    tags_json TEXT COMMENT '标签 JSON',
    package_json LONGTEXT COMMENT '插件包配置 JSON',
    manifest_json LONGTEXT COMMENT '插件清单 JSON',
    download_url VARCHAR(500) DEFAULT '' COMMENT '下载地址',
    file_size INT DEFAULT 0 COMMENT '文件大小 bytes',
    checksum VARCHAR(64) DEFAULT '' COMMENT '文件校验和',
    is_public TINYINT(1) DEFAULT 1 COMMENT '是否公开',
    is_official TINYINT(1) DEFAULT 0 COMMENT '是否官方',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态',
    download_count INT DEFAULT 0 COMMENT '下载次数',
    rating DECIMAL(3,2) DEFAULT 0.00 COMMENT '评分',
    rating_count INT DEFAULT 0 COMMENT '评分次数',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_plugin_type (plugin_type),
    INDEX idx_category (category),
    INDEX idx_author (author_id),
    INDEX idx_status (status),
    INDEX idx_is_public (is_public)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

PLUGIN_INSTALLS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS plugin_installs (
    id VARCHAR(36) PRIMARY KEY,
    plugin_id VARCHAR(36) NOT NULL COMMENT '插件 ID',
    installed_by VARCHAR(36) NOT NULL COMMENT '安装者 ID',
    installed_version VARCHAR(20) DEFAULT '' COMMENT '安装时版本',
    status VARCHAR(20) DEFAULT 'installed' COMMENT '状态：installed/enabled/disabled/uninstalled',
    config_json TEXT COMMENT '安装配置 JSON',
    installed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_plugin_id (plugin_id),
    INDEX idx_installed_by (installed_by),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# Agent 模板（快速创建预配置 Agent）
# ============================================================

AGENT_TEMPLATES_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS agent_templates (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '模板名称',
    description TEXT COMMENT '模板描述',
    icon VARCHAR(50) DEFAULT '🤖' COMMENT '图标',
    icon_background VARCHAR(20) DEFAULT '#E8F3FF' COMMENT '图标背景色',
    category VARCHAR(50) DEFAULT 'general' COMMENT '分类：general/customer/analysis/creative/code',
    tags_json TEXT COMMENT '标签 JSON 数组',
    model_provider VARCHAR(100) DEFAULT '' COMMENT '模型提供者',
    model_name VARCHAR(100) DEFAULT '' COMMENT '模型名称',
    system_prompt TEXT COMMENT '系统提示词模板',
    user_prompt_template TEXT COMMENT '用户提示词模板',
    tools_json TEXT COMMENT '工具配置 JSON 数组',
    mcp_servers_json TEXT COMMENT '关联 MCP 服务器 ID 数组',
    knowledge_ids_json TEXT COMMENT '关联知识库 ID 数组',
    max_iterations INT DEFAULT 5 COMMENT '最大迭代次数',
    temperature DECIMAL(3,2) DEFAULT 0.7 COMMENT '温度参数',
    is_public TINYINT(1) DEFAULT 1 COMMENT '是否公开',
    is_official TINYINT(1) DEFAULT 0 COMMENT '是否官方',
    author_id VARCHAR(36) DEFAULT NULL COMMENT '作者 ID',
    author_name VARCHAR(100) DEFAULT '' COMMENT '作者名称',
    usage_count INT DEFAULT 0 COMMENT '使用次数',
    rating DECIMAL(3,2) DEFAULT 0.00 COMMENT '评分',
    rating_count INT DEFAULT 0 COMMENT '评分次数',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态：active/inactive',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category (category),
    INDEX idx_author (author_id),
    INDEX idx_status (status),
    INDEX idx_is_public (is_public),
    FULLTEXT INDEX ft_name_desc (name, description)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 对话摘要（多轮对话记忆压缩）
# ============================================================

CONVERSATION_SUMMARIES_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS conversation_summaries (
    id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL COMMENT '关联对话 ID',
    app_id VARCHAR(36) NOT NULL COMMENT '关联应用 ID',
    account_id VARCHAR(36) NOT NULL COMMENT '用户 ID',
    summary_text TEXT NOT NULL COMMENT '摘要内容',
    message_count INT DEFAULT 0 COMMENT '摘要覆盖的消息数',
    start_message_id VARCHAR(36) DEFAULT '' COMMENT '起始消息 ID',
    end_message_id VARCHAR(36) DEFAULT '' COMMENT '结束消息 ID',
    token_count INT DEFAULT 0 COMMENT '摘要 token 数',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_conversation (conversation_id),
    INDEX idx_app (app_id),
    INDEX idx_account (account_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# Webhook 配置（工作流触发器）
# ============================================================

WEBHOOKS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS webhooks (
    id VARCHAR(36) PRIMARY KEY,
    app_id VARCHAR(36) NOT NULL COMMENT '关联应用 ID',
    name VARCHAR(100) NOT NULL COMMENT 'Webhook 名称',
    description TEXT COMMENT '描述',
    webhook_key VARCHAR(64) NOT NULL COMMENT '唯一触发密钥',
    trigger_url VARCHAR(500) NOT NULL COMMENT '完整触发 URL',
    input_schema TEXT COMMENT '输入参数 JSON Schema',
    is_active TINYINT(1) DEFAULT 1 COMMENT '是否激活',
    call_count INT DEFAULT 0 COMMENT '调用次数',
    last_called_at DATETIME DEFAULT NULL COMMENT '最后调用时间',
    last_status VARCHAR(20) DEFAULT '' COMMENT '最后调用状态',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_webhook_key (webhook_key),
    INDEX idx_app_id (app_id),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# Webhook 调用日志
# ============================================================

WEBHOOK_LOGS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS webhook_logs (
    id VARCHAR(36) PRIMARY KEY,
    webhook_id VARCHAR(36) NOT NULL COMMENT '关联 Webhook ID',
    trigger_key VARCHAR(64) NOT NULL COMMENT '触发密钥',
    request_body TEXT COMMENT '请求体 JSON',
    request_headers TEXT COMMENT '请求头 JSON',
    status VARCHAR(20) NOT NULL COMMENT 'success/error',
    response_code INT DEFAULT 0 COMMENT 'HTTP 响应码',
    workflow_run_id VARCHAR(36) DEFAULT '' COMMENT '关联工作流运行 ID',
    error_message TEXT COMMENT '错误信息',
    elapsed_ms INT DEFAULT 0 COMMENT '耗时毫秒',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_webhook_id (webhook_id),
    INDEX idx_status (status),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 工作流调试会话（断点调试）
# ============================================================

WORKFLOW_DEBUG_SESSIONS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS workflow_debug_sessions (
    id VARCHAR(36) PRIMARY KEY,
    app_id VARCHAR(36) NOT NULL COMMENT '关联应用 ID',
    account_id VARCHAR(36) NOT NULL COMMENT '调试者 ID',
    inputs_json TEXT COMMENT '输入参数 JSON',
    current_node_id VARCHAR(50) DEFAULT '' COMMENT '当前执行到的节点 ID',
    status VARCHAR(20) DEFAULT 'running' COMMENT 'running/paused/completed/error',
    context_json LONGTEXT COMMENT '当前上下文变量 JSON',
    breakpoints_json TEXT COMMENT '断点节点 ID 数组 JSON',
    node_results_json LONGTEXT COMMENT '已执行节点结果 JSON',
    current_node_result TEXT COMMENT '当前节点执行结果',
    error_message TEXT COMMENT '错误信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_app_id (app_id),
    INDEX idx_account (account_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 工作流批量运行任务
# ============================================================

WORKFLOW_BATCH_RUNS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS workflow_batch_runs (
    id VARCHAR(36) PRIMARY KEY,
    app_id VARCHAR(36) NOT NULL COMMENT '关联应用 ID',
    account_id VARCHAR(36) NOT NULL COMMENT '创建者 ID',
    name VARCHAR(100) NOT NULL COMMENT '批量任务名称',
    status VARCHAR(20) DEFAULT 'pending' COMMENT 'pending/running/completed/error',
    total_count INT DEFAULT 0 COMMENT '总任务数',
    success_count INT DEFAULT 0 COMMENT '成功数',
    fail_count INT DEFAULT 0 COMMENT '失败数',
    input_data_json LONGTEXT COMMENT '输入数据 JSON 数组',
    output_data_json LONGTEXT COMMENT '输出结果 JSON 数组',
    error_message TEXT COMMENT '错误信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_app_id (app_id),
    INDEX idx_account (account_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 已安装应用表（P1: 模板安装后追踪来源和状态）
# ============================================================

INSTALLED_APPS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS installed_apps (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL COMMENT '租户 ID',
    app_id VARCHAR(36) DEFAULT NULL COMMENT '安装后创建的应用 ID',
    source_type VARCHAR(30) NOT NULL COMMENT '来源类型：template/marketplace/import/plugin',
    source_id VARCHAR(100) DEFAULT NULL COMMENT '来源 ID（模板 ID/市场 ID）',
    source_name VARCHAR(200) DEFAULT '' COMMENT '来源名称',
    app_name VARCHAR(200) NOT NULL COMMENT '应用名称',
    app_mode VARCHAR(50) DEFAULT 'workflow' COMMENT '应用模式',
    app_icon VARCHAR(50) DEFAULT '🤖' COMMENT '应用图标',
    app_description TEXT COMMENT '应用描述',
    install_type VARCHAR(20) DEFAULT 'new' COMMENT '安装类型：new/upgrade/reinstall',
    installed_version VARCHAR(20) DEFAULT '1.0.0' COMMENT '安装版本',
    current_version VARCHAR(20) DEFAULT '1.0.0' COMMENT '当前版本',
    status VARCHAR(20) DEFAULT 'installed' COMMENT '状态：installed/active/archived/error',
    config_json TEXT COMMENT '安装配置 JSON',
    installed_by VARCHAR(36) DEFAULT NULL COMMENT '安装者 ID',
    installed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_app_id (app_id),
    INDEX idx_source (source_type, source_id),
    INDEX idx_status (status),
    INDEX idx_installed_by (installed_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 应用-MCP 关联表（P1: 应用绑定 MCP 服务器）
# ============================================================

APP_MCP_SERVERS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS app_mcp_servers (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL COMMENT '租户 ID',
    app_id VARCHAR(36) NOT NULL COMMENT '关联应用 ID',
    server_id VARCHAR(36) NOT NULL COMMENT '关联 mcp_servers.id',
    server_name VARCHAR(100) NOT NULL COMMENT 'MCP 服务器名称（冗余存储）',
    is_enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    tool_whitelist_json TEXT COMMENT '工具白名单 JSON 数组',
    tool_blacklist_json TEXT COMMENT '工具黑名单 JSON 数组',
    custom_config TEXT COMMENT '自定义配置 JSON',
    priority INT DEFAULT 0 COMMENT '优先级（多服务器时排序）',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态：active/inactive/error',
    last_connected_at DATETIME DEFAULT NULL COMMENT '最后连接时间',
    last_error TEXT COMMENT '最后错误信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_app_server (app_id, server_id),
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_app_id (app_id),
    INDEX idx_server_id (server_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# Human Input 表单表（P1: 工作流暂停交互表单）
# ============================================================

HUMAN_INPUT_FORMS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS human_input_forms (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL COMMENT '租户 ID',
    app_id VARCHAR(36) NOT NULL COMMENT '关联应用 ID',
    workflow_run_id VARCHAR(36) NOT NULL COMMENT '关联工作流运行 ID',
    node_id VARCHAR(50) NOT NULL COMMENT '触发暂停的节点 ID',
    form_key VARCHAR(100) NOT NULL COMMENT '表单唯一标识',
    title VARCHAR(200) NOT NULL COMMENT '表单标题',
    description TEXT COMMENT '表单描述',
    input_fields_json LONGTEXT NOT NULL COMMENT '输入字段定义 JSON 数组',
    submit_url VARCHAR(500) NOT NULL COMMENT '提交 URL',
    submit_token VARCHAR(100) NOT NULL COMMENT '提交令牌（防篡改）',
    status VARCHAR(20) DEFAULT 'waiting' COMMENT '状态：waiting/submitted/expired/cancelled',
    submitted_by VARCHAR(36) DEFAULT NULL COMMENT '提交者 ID',
    submitted_data_json TEXT COMMENT '提交的数据 JSON',
    submitted_at DATETIME DEFAULT NULL COMMENT '提交时间',
    expired_at DATETIME DEFAULT NULL COMMENT '过期时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_form_key (form_key),
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_app_id (app_id),
    INDEX idx_workflow_run (workflow_run_id),
    INDEX idx_status (status),
    INDEX idx_expired_at (expired_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 工作流暂停状态表（P1: 工作流暂停/恢复控制）
# ============================================================

WORKFLOW_PAUSES_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS workflow_pauses (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL COMMENT '租户 ID',
    app_id VARCHAR(36) NOT NULL COMMENT '关联应用 ID',
    workflow_id VARCHAR(36) NOT NULL COMMENT '关联工作流 ID',
    workflow_run_id VARCHAR(36) NOT NULL COMMENT '关联工作流运行 ID',
    node_id VARCHAR(50) NOT NULL COMMENT '暂停节点 ID',
    node_type VARCHAR(50) NOT NULL COMMENT '暂停节点类型',
    pause_reason VARCHAR(100) DEFAULT 'human_input' COMMENT '暂停原因：human_input/approval/debug/schedule',
    pause_context_json LONGTEXT COMMENT '暂停上下文 JSON（节点输入/变量快照）',
    resume_strategy VARCHAR(30) DEFAULT 'manual' COMMENT '恢复策略：manual/auto/conditional',
    resume_condition TEXT COMMENT '自动恢复条件 JSON',
    human_input_form_id VARCHAR(36) DEFAULT NULL COMMENT '关联 Human Input 表单 ID',
    status VARCHAR(20) DEFAULT 'paused' COMMENT '状态：paused/resumed/cancelled/timeout',
    paused_by VARCHAR(36) DEFAULT NULL COMMENT '暂停者 ID',
    paused_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    resumed_by VARCHAR(36) DEFAULT NULL COMMENT '恢复者 ID',
    resumed_at DATETIME DEFAULT NULL COMMENT '恢复时间',
    timeout_seconds INT DEFAULT 86400 COMMENT '超时秒数（默认 24 小时）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_app_id (app_id),
    INDEX idx_workflow_run (workflow_run_id),
    INDEX idx_status (status),
    INDEX idx_paused_at (paused_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 工作流对话变量表（P1: 对话级变量持久化）
# ============================================================

WORKFLOW_CONVERSATION_VARIABLES_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS workflow_conversation_variables (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL COMMENT '租户 ID',
    app_id VARCHAR(36) NOT NULL COMMENT '关联应用 ID',
    conversation_id VARCHAR(36) NOT NULL COMMENT '关联对话 ID',
    workflow_run_id VARCHAR(36) DEFAULT NULL COMMENT '关联工作流运行 ID',
    variable_name VARCHAR(100) NOT NULL COMMENT '变量名称',
    variable_type VARCHAR(30) DEFAULT 'string' COMMENT '变量类型：string/number/boolean/object/array',
    variable_value LONGTEXT COMMENT '变量值 JSON',
    variable_scope VARCHAR(20) DEFAULT 'conversation' COMMENT '变量范围：conversation/session/global',
    source_node_id VARCHAR(50) DEFAULT NULL COMMENT '变量来源节点 ID',
    source_run_id VARCHAR(36) DEFAULT NULL COMMENT '变量来源运行 ID',
    is_persistent TINYINT(1) DEFAULT 1 COMMENT '是否持久化（跨轮次保留）',
    expires_at DATETIME DEFAULT NULL COMMENT '过期时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_conv_var (conversation_id, variable_name),
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_app_id (app_id),
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_variable_name (variable_name),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 工作流草稿变量表（P1: 草稿编辑时变量持久化）
# ============================================================

WORKFLOW_DRAFT_VARIABLES_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS workflow_draft_variables (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL COMMENT '租户 ID',
    app_id VARCHAR(36) NOT NULL COMMENT '关联应用 ID',
    workflow_id VARCHAR(36) NOT NULL COMMENT '关联工作流 ID',
    draft_key VARCHAR(100) DEFAULT 'default' COMMENT '草稿标识（支持多草稿）',
    variable_name VARCHAR(100) NOT NULL COMMENT '变量名称',
    variable_type VARCHAR(30) DEFAULT 'string' COMMENT '变量类型：string/number/boolean/object/array',
    variable_value LONGTEXT COMMENT '变量值 JSON',
    default_value LONGTEXT COMMENT '默认值 JSON',
    description VARCHAR(500) DEFAULT '' COMMENT '变量描述',
    is_required TINYINT(1) DEFAULT 0 COMMENT '是否必填',
    validation_rule TEXT COMMENT '校验规则 JSON',
    ui_config_json TEXT COMMENT 'UI 配置 JSON（输入控件类型/选项）',
    created_by VARCHAR(36) DEFAULT NULL COMMENT '创建者 ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_draft_var (app_id, draft_key, variable_name),
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_app_id (app_id),
    INDEX idx_workflow_id (workflow_id),
    INDEX idx_draft_key (draft_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 定时触发计划表（P0: trigger-schedule 节点）
# ============================================================

WORKFLOW_SCHEDULE_PLANS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS workflow_schedule_plans (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) DEFAULT NULL COMMENT '租户 ID',
    app_id VARCHAR(36) NOT NULL COMMENT '关联应用 ID',
    node_id VARCHAR(50) NOT NULL COMMENT '画布中 trigger-schedule 节点 ID',
    node_title VARCHAR(200) DEFAULT '' COMMENT '节点标题',
    cron_expr VARCHAR(100) NOT NULL COMMENT 'Cron 表达式（5 段：分 时 日 月 周）',
    timezone VARCHAR(50) DEFAULT 'Asia/Shanghai' COMMENT '时区',
    enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    last_run_at DATETIME DEFAULT NULL COMMENT '上次触发时间',
    next_run_at DATETIME DEFAULT NULL COMMENT '下次触发时间',
    run_count INT DEFAULT 0 COMMENT '已触发次数',
    last_status VARCHAR(20) DEFAULT '' COMMENT '上次触发状态',
    last_error TEXT COMMENT '上次触发错误',
    created_by VARCHAR(36) DEFAULT NULL COMMENT '创建者 ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_app_node (app_id, node_id),
    INDEX idx_next_run (enabled, next_run_at),
    INDEX idx_app_id (app_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 触发器执行日志表（P0: 定时/Webhook/插件触发统一日志）
# ============================================================

WORKFLOW_TRIGGER_LOGS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS workflow_trigger_logs (
    id VARCHAR(36) PRIMARY KEY,
    trigger_type VARCHAR(20) NOT NULL COMMENT '触发类型：schedule/webhook/plugin',
    plan_id VARCHAR(36) DEFAULT NULL COMMENT '关联触发计划/订阅 ID',
    webhook_id VARCHAR(36) DEFAULT NULL COMMENT '关联 Webhook ID',
    app_id VARCHAR(36) NOT NULL COMMENT '关联应用 ID',
    node_id VARCHAR(50) DEFAULT NULL COMMENT '画布中触发节点 ID',
    run_id VARCHAR(36) DEFAULT NULL COMMENT '关联工作流运行 ID',
    task_id VARCHAR(64) DEFAULT NULL COMMENT 'Celery 任务 ID',
    status VARCHAR(20) NOT NULL DEFAULT 'triggered' COMMENT '状态：triggered/succeeded/failed',
    error_message TEXT COMMENT '错误信息',
    elapsed_ms INT DEFAULT 0 COMMENT '耗时（毫秒）',
    triggered_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '触发时间',
    finished_at DATETIME DEFAULT NULL COMMENT '完成时间',
    INDEX idx_app_id (app_id),
    INDEX idx_trigger_type (trigger_type),
    INDEX idx_triggered_at (triggered_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 触发器订阅表（订阅定时/Webhook 触发结果，邮件/Webhook/API 回调通知）
# ============================================================

TRIGGER_SUBSCRIPTIONS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS trigger_subscriptions (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) DEFAULT NULL,
    app_id VARCHAR(36) NOT NULL COMMENT '关联应用 ID',
    trigger_type VARCHAR(20) NOT NULL COMMENT '触发类型：schedule/webhook/plugin',
    target_id VARCHAR(36) NOT NULL COMMENT '定时计划 ID / Webhook ID / 插件触发器 ID',
    node_id VARCHAR(50) DEFAULT NULL COMMENT '工作流触发节点 ID',
    node_title VARCHAR(255) DEFAULT '' COMMENT '触发节点标题',
    subscriber_type VARCHAR(20) NOT NULL COMMENT '订阅方式：email/webhook/api',
    subscriber_target VARCHAR(500) NOT NULL COMMENT '邮箱地址 / 回调 URL / API 标识',
    enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    last_triggered_at DATETIME DEFAULT NULL COMMENT '最近一次触发时间',
    trigger_count INT DEFAULT 0 COMMENT '累计触发次数',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_app_id (app_id),
    INDEX idx_target (trigger_type, target_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# Agent 思考链表（Agent 节点 ReAct 循环逐步推理/工具调用记录）
# ============================================================

MESSAGE_AGENT_THOUGHTS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS message_agent_thoughts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_id VARCHAR(36) NOT NULL COMMENT '关联 dify_messages.id',
    position INT NOT NULL DEFAULT 0 COMMENT '思考步骤序号（从 0 开始）',
    thought TEXT COMMENT 'LLM 推理内容（原始响应）',
    tool_name VARCHAR(200) DEFAULT '' COMMENT '调用的工具名称',
    tool_input TEXT COMMENT '工具输入参数（JSON 字符串）',
    tool_output TEXT COMMENT '工具执行结果',
    observation TEXT COMMENT '观察结果反馈给 LLM 的内容',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_message_id (message_id),
    INDEX idx_message_pos (message_id, position)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 知识库元数据表（数据集级别的结构化元数据字段定义 + 分段绑定）
# ============================================================

DATASET_METADATAS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dataset_metadatas (
    id VARCHAR(36) PRIMARY KEY,
    dataset_id VARCHAR(36) NOT NULL COMMENT '关联 dify_datasets.id',
    tenant_id VARCHAR(36) DEFAULT NULL,
    name VARCHAR(100) NOT NULL COMMENT '元数据字段名（如：部门、年份、分类）',
    type VARCHAR(20) NOT NULL DEFAULT 'string' COMMENT '数据类型：string/number/date/enum',
    description VARCHAR(500) DEFAULT '' COMMENT '字段说明',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_dataset_id (dataset_id),
    UNIQUE KEY uk_dataset_name (dataset_id, name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

DATASET_METADATA_BINDINGS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dataset_metadata_bindings (
    id VARCHAR(36) PRIMARY KEY,
    dataset_id VARCHAR(36) NOT NULL COMMENT '关联 dify_datasets.id',
    metadata_id VARCHAR(36) NOT NULL COMMENT '关联 dataset_metadatas.id',
    segment_id VARCHAR(36) NOT NULL COMMENT '关联 dify_document_segments.id',
    value VARCHAR(500) NOT NULL COMMENT '元数据值（字符串形式存储，数字/日期也转为字符串）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_dataset_id (dataset_id),
    INDEX idx_metadata_id (metadata_id),
    INDEX idx_segment_id (segment_id),
    UNIQUE KEY uk_meta_segment (metadata_id, segment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 知识库引用追踪表（检索结果的结构化引用记录）
# ============================================================

DATASET_RETRIEVER_RESOURCES_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dataset_retriever_resources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_id VARCHAR(36) NOT NULL COMMENT '关联 dify_messages.id',
    dataset_id VARCHAR(36) NOT NULL COMMENT '关联 dify_datasets.id',
    document_id VARCHAR(36) NOT NULL COMMENT '关联 dify_documents.id',
    segment_id VARCHAR(36) NOT NULL COMMENT '关联 dify_document_segments.id',
    document_name VARCHAR(255) DEFAULT '' COMMENT '文档名（冗余，便于展示）',
    segment_content TEXT COMMENT '分段内容摘要',
    score FLOAT DEFAULT 0 COMMENT '检索匹配分数',
    position INT DEFAULT 0 COMMENT '在检索结果中的排序位置',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_message_id (message_id),
    INDEX idx_dataset_id (dataset_id),
    INDEX idx_segment_id (segment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 知识库关键词表（jieba 分词索引，支持混合检索）
# ============================================================

DATASET_KEYWORD_TABLES_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS dataset_keyword_tables (
    id INT AUTO_INCREMENT PRIMARY KEY,
    dataset_id VARCHAR(36) NOT NULL COMMENT '关联 dify_datasets.id',
    keyword VARCHAR(200) NOT NULL COMMENT '分词后的关键词',
    segment_id VARCHAR(36) NOT NULL COMMENT '关联 dify_document_segments.id',
    term_frequency INT DEFAULT 1 COMMENT '词频（该词在分段中出现次数）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_dataset_keyword (dataset_id, keyword),
    INDEX idx_segment_id (segment_id),
    UNIQUE KEY uk_dataset_kw_seg (dataset_id, keyword, segment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 外部知识 API 表（3.3）
# ============================================================

EXTERNAL_KNOWLEDGE_APIS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS external_knowledge_apis (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL COMMENT '关联 dify_tenants.id',
    name VARCHAR(255) NOT NULL COMMENT 'API 名称',
    description TEXT COMMENT '描述',
    endpoint_url VARCHAR(1024) NOT NULL COMMENT '外部检索 API 地址',
    api_key VARCHAR(500) DEFAULT '' COMMENT 'API 密钥（可选）',
    timeout INT DEFAULT 30 COMMENT '超时时间（秒）',
    status TINYINT(1) DEFAULT 1 COMMENT '状态：1=启用，0=禁用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

EXTERNAL_KNOWLEDGE_BINDINGS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS external_knowledge_bindings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    dataset_id VARCHAR(36) NOT NULL COMMENT '关联 dify_datasets.id',
    external_api_id INT NOT NULL COMMENT '关联 external_knowledge_apis.id',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_dataset_api (dataset_id, external_api_id),
    INDEX idx_dataset_id (dataset_id),
    INDEX idx_api_id (external_api_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 系统设置表（3.6: SMTP 配置等）
# ============================================================

SYSTEM_SETTINGS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS system_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    `key` VARCHAR(100) NOT NULL COMMENT '设置键',
    `value` TEXT COMMENT '设置值（JSON 字符串）',
    description VARCHAR(500) DEFAULT '',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_setting_key (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 工作流评论协作表（P2 #15）
# ============================================================

WORKFLOW_COMMENTS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS workflow_comments (
    id VARCHAR(36) PRIMARY KEY COMMENT '评论 ID',
    app_id VARCHAR(36) NOT NULL COMMENT '工作流应用 ID',
    node_id VARCHAR(64) DEFAULT '' COMMENT '关联节点 ID（可选）',
    user_id VARCHAR(36) NOT NULL COMMENT '评论者 ID',
    user_name VARCHAR(100) DEFAULT '' COMMENT '评论者名称',
    content TEXT NOT NULL COMMENT '评论内容',
    parent_id VARCHAR(36) DEFAULT NULL COMMENT '父评论 ID（回复）',
    position_x FLOAT DEFAULT 0 COMMENT '画布 X 坐标',
    position_y FLOAT DEFAULT 0 COMMENT '画布 Y 坐标',
    resolved TINYINT DEFAULT 0 COMMENT '是否已解决',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_app_id (app_id),
    INDEX idx_parent_id (parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# 知识 Pipeline 引擎（P2 #13）
# ============================================================

PIPELINES_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS knowledge_pipelines (
    id VARCHAR(36) PRIMARY KEY COMMENT 'Pipeline ID',
    name VARCHAR(200) NOT NULL COMMENT 'Pipeline 名称',
    description TEXT COMMENT 'Pipeline 描述',
    dataset_id VARCHAR(36) DEFAULT NULL COMMENT '关联知识库 ID',
    status VARCHAR(20) DEFAULT 'draft' COMMENT '状态: draft/paused/running',
    stages JSON NOT NULL COMMENT 'Pipeline 阶段配置 [{type, config, order}]',
    schedule VARCHAR(100) DEFAULT NULL COMMENT '定时调度 cron 表达式',
    last_run_at DATETIME DEFAULT NULL COMMENT '最后运行时间',
    total_docs INT DEFAULT 0 COMMENT '累计处理文档数',
    created_by VARCHAR(36) NOT NULL COMMENT '创建者 ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_dataset_id (dataset_id),
    INDEX idx_status (status),
    INDEX idx_created_by (created_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

PIPELINE_EXECUTION_LOGS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS pipeline_execution_logs (
    id VARCHAR(36) PRIMARY KEY COMMENT '执行日志 ID',
    pipeline_id VARCHAR(36) NOT NULL COMMENT 'Pipeline ID',
    trigger_type VARCHAR(20) DEFAULT 'manual' COMMENT '触发类型',
    status VARCHAR(20) DEFAULT 'running' COMMENT '执行状态',
    current_stage VARCHAR(50) DEFAULT NULL COMMENT '当前阶段',
    stages_result JSON COMMENT '各阶段执行结果',
    docs_processed INT DEFAULT 0 COMMENT '处理文档数',
    docs_succeeded INT DEFAULT 0 COMMENT '成功文档数',
    docs_failed INT DEFAULT 0 COMMENT '失败文档数',
    error_message TEXT COMMENT '错误信息',
    started_at DATETIME DEFAULT NULL COMMENT '开始时间',
    completed_at DATETIME DEFAULT NULL COMMENT '完成时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_pipeline_id (pipeline_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

PIPELINE_DOCUMENTS_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS pipeline_documents (
    id VARCHAR(36) PRIMARY KEY COMMENT '记录 ID',
    pipeline_id VARCHAR(36) NOT NULL COMMENT 'Pipeline ID',
    execution_id VARCHAR(36) DEFAULT NULL COMMENT '执行日志 ID',
    source_type VARCHAR(30) NOT NULL COMMENT '来源: file/url/api/text',
    source_path VARCHAR(1024) DEFAULT NULL COMMENT '来源路径/URL',
    source_config JSON COMMENT '来源配置',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/processing/success/failed',
    raw_content LONGTEXT COMMENT '原始内容',
    processed_content LONGTEXT COMMENT '处理后内容',
    segments_created INT DEFAULT 0 COMMENT '创建分段数',
    error_message TEXT COMMENT '错误信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_pipeline_id (pipeline_id),
    INDEX idx_execution_id (execution_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

# ============================================================
# Human Input 邮件投递记录表（3.6）
# ============================================================

HUMAN_INPUT_FORM_DELIVERIES_TABLE_SQL = r'''
CREATE TABLE IF NOT EXISTS human_input_form_deliveries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    run_id VARCHAR(36) NOT NULL COMMENT '工作流运行 ID',
    app_id VARCHAR(36) NOT NULL COMMENT '应用 ID',
    node_id VARCHAR(64) NOT NULL COMMENT 'Human Input 节点 ID',
    email VARCHAR(255) NOT NULL COMMENT '接收邮箱',
    subject VARCHAR(500) DEFAULT '' COMMENT '邮件主题',
    form_url VARCHAR(1024) DEFAULT '' COMMENT '表单链接',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/sent/failed/opened/submitted',
    error TEXT COMMENT '错误信息',
    delivered_at DATETIME DEFAULT NULL COMMENT '投递时间',
    submitted_at DATETIME DEFAULT NULL COMMENT '提交时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_run_id (run_id),
    INDEX idx_app_id (app_id),
    INDEX idx_email (email),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''
