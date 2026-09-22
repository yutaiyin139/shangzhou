
# 熵舟 vs Dify 1.17.0 — 功能差距深度分析（第十六版 · 实测刷新版）

> 生成日期：2026-09-04 | 最后实测刷新：2026-09-08 | 阶段 0 清理复核：2026-09-22 | 阶段 1（P0）实现与回归复核：2026-09-22 | 阶段 2（P1）实现与回归复核：2026-09-22 | 阶段 3（P1 收尾 + P2）实现与回归复核：2026-09-22 | 阶段 4（P2 模型管理 + 前端工程化）实现与回归复核：2026-09-22
> 对照版本：Dify 1.17.0（**本机运行中实测**，`git describe` = 1.17.0，15 个容器 Up 3 小时以上）
> 核验方式：**实机探测**（Docker / PostgreSQL / MySQL / HTTP / 代码静态统计），非文档转抄
> 分析范围：Dify 1.17.0（144 表 / 846 端点 / graphon 引擎 30 节点 / 15 容器） vs 熵舟（90 表 / 326 端点 / 29 节点 / 裸机部署；表数/节点数为 2026-09-22 实测）
> 当前版本：v5.9（**V1.0 发布定版：P1 功能对齐/健壮性 + P2 工程整洁收尾（本轮实测核验+落地）**：①P2-11 健壮性——`backend/utils/auth.py`（权限/Token 层 8 处吞异常分支）与 `backend/engine/metadata_engine.py`（DB 层 11 处吞异常分支）此前裸 `except Exception: return False/None` 会静默掩盖 SQL/schema 错误（曾致知识库详情接口人人 403），现统一在各异常分支补 `logger.exception/warning`（**返回值语义完全不变**），并各自引入 `from utils.logger import get_logger`；②P2-9 工程整洁——一次性运维脚本 `diagnose.py`/`reset_password.py`/`seed_plugins.py` 从 `backend/` 归档至 `scripts/maintenance/`（`git mv` 保留历史，修 `sys.path` bootstrap 为 `../../backend`，同步更新归档 README）；③P1-4 i18n——核验 `front/src/locales/index.ts` 为**功能完整**的中英文双语模块（`t()`/`setLocale`/`locale`，AppShell 导航 + 搜索 + Pinia store 已接线，运行时切换 + localStorage 持久化），**并非空转脚手架，予以保留**；④P1-5 Service API——核验 `/v1/info`、`/v1/parameters`、`/v1/messages`(+feedbacks)、`/v1/conversations`(列表/删/重命名)、`/v1/meta`、`/v1/site`、audio 双端点**均已实现**（仅非标准 `/v1/apps` 发布渠道未做，判为可裁剪），据实刷新 §3.5/§4.2（Service API 68→92%）；⑤P1-6 多租户/SAML-LDAP——按 V1.0 范围**明确延后**（单租户 owner/admin/published 模型 + OAuth2 已足，多租户隔离与 SAML/LDAP 记为 post-V1.0）；⑥P1-7 部署——`scripts/deploy-ubuntu.sh` 一键部署完整，★修复其数据库初始化步骤引用不存在的 `models.tables.init_db()` 致 `ImportError` 的缺陷（改为遍历 `models.tables` 全部 `*_TABLE_SQL` 逐一 `CREATE TABLE IF NOT EXISTS`），该块 `bash -n` 语法校验通过；⑦回归全绿：后端 `compileall` 退出 0、受影响两模块 `py_compile`+fresh import 通过、`e2e_metadata_check` **15/15**、`e2e_phase5_rbac_sso_check` **14/14**、`e2e_register_control_check` **8/8**、前端 `vue-tsc && vite build` **✓ built（退出 0）**。前后端代码完整性梳理定版 V1.0。前续 v5.8（**P0 注册管控落地（V1.0 安全）**：此前“是否开放注册”仅有前端 UI 与写库、后端 `/api/register` 从不读取（“设了不用”）——本轮打通并扩展：后端注册接口强制读 `system_settings.allow_register`（关闭→403）、新增 `register_invite_code`（非空→邀请码必校验）、新增公开 `/api/register-config`（返回 allow_register/require_invite_code，不含邀请码明文）；前端 RegisterView 据配置隐藏表单/按需展示邀请码框、SystemSettingsView 新增邀请码设置项；新增确定性回归 `e2e_register_control_check` **8/8 PASS**；回归 compileall 退出 0 + phase5 14/14 + 前端 `vue-tsc && vite build` ✓。前续 v5.7（**V1.0 发布前代码清理与安全加固**：删除死代码 `engine/workflow_runner_orig.py`（4388 行/0 引用）与临时诊断脚本、`git rm` 前端遗留原型 `front/legacy/`（42）、一次性迁移/清理脚本归档至 `scripts/maintenance/`、★清除仓库内明文口令（个人口令与 DB 口令，改环境变量/命令行注入）、`.env.example` 脱敏、`.gitignore` 防复发；回归 compileall + build + 14/14 全绿。前续 v5.6（**阶段 5 P3 平台化已落地并复核**：5.1 资源级 RBAC（`utils/auth.py` `_RESOURCE_REGISTRY` 覆盖 app/workflow/dataset/tool + `check_resource_permission`/`resource_permission_required`）/5.2 SSO OAuth2 登录（`utils/oauth_user.py` Google/GitHub 全流程 + `/api/oauth/*`，★修复用户配给引用 `dify_accounts` 不存在列致登录失败的缺陷 + 白空 email 守卫）/5.3 workflow_runner 拆分（runner 1067 行、`engine/nodes/` 21 文件、NodeFactory 40 注册）/5.4 CI/CD（`.gitignore` 零密钥白名单 402 文件 + `.github/workflows/ci.yml` 后端 compileall + 前端 vue-tsc/build，本地双闸门验证绿；`git init -b main` 已连 origin）四项**全部落地**；新增确定性回归 `e2e_phase5_rbac_sso_check` **14/14 PASS**；措辞更正：SSO 配置存 `system_settings.oauth_providers` 而非独立 `oauth_provider_apps` 表。前续：v5.5（**阶段 4 P2 已落地并复核**：4.1 模型连接测试端点（by-id + body，返回 elapsed_ms 延迟，支持 llm/embedding/tts/stt）/4.2 模型负载均衡（多 Key 轮询 + 失败自动切换）/4.3 语音 Service API（/v1/audio-to-text + /v1/text-to-audio）/4.4 工作流版本 Diff（后端结构化 diff API + 前端 VersionPanel 对比视图）/4.5 组件库扩展（**20 个**统一 UI 组件 + index.ts）/4.6 响应式适配（style.css 1400/1280/1024/768/480px + 触控断点）六项**均已实现**；新增确定性回归 `e2e_phase4_model_lb_diff_check` **11/11 PASS**（真实多 Key 轮询循环 + 结构化 diff 精确断言）；`e2e_phase4_check` 9/9、`e2e_p1_fixes_check` 17/17、`e2e_audio_api_check` 19/19 全绿；前端 `vue-tsc --noEmit && vite build` 退出码 **0**（✓ built）。前续：阶段 3 七项全绿（3.1-3.7），阶段 2 P1 四项已实现，阶段 1 P0 实测通过。历史：v5.4 配置通义 embedding打通记忆向量化端到端）

---

## 〇、本轮实测方法（2026-09-08）

| 核验项 | 方法 | 实测结果 |
|--------|------|---------|
| Dify 容器 | `docker ps` | **15 容器运行中**（nginx/web/api/api_websocket/worker/worker_beat/sandbox/local_sandbox/plugin_daemon/agent_backend/ssrf_proxy×2/db_postgres/pgvector/redis） |
| Dify 版本 | `git describe --tags` + `pyproject.toml` | `1.17.0`（commit 09a855dcef） |
| Dify 表数 | `psql information_schema`（dify 库 public 模式） | **144 张**（143 业务表 + `alembic_version`） |
| Dify 端点数 | `grep "@*_ns.route(" controllers/` + `add_resource` | **830 + 16 ≈ 846 个** |
| Dify 节点类型 | 容器内 `graphon.enums.BuiltinNodeTypes` + `core/workflow/nodes/` | 24 内置 + datasource/agent_v2/human_input/knowledge_index/trigger×3 ≈ **30 种** |
| Dify 引擎架构 | 源码阅读 | **1.17.0 已将工作流运行时抽离为独立包 `graphon`**（重大架构变更，v15 未记录） |
| 熵舟表数 | `information_schema.tables`（szagent 库） | **90 张**（全部 BASE TABLE 业务表；原遗留备份表 `users_backup_20260903_150012` 经 2026-09-22 复核已不存在） |
| 熵舟端点数 | `grep "@(app|bp).route(" routes/` | **326 个**，34 个路由文件 |
| 熵舟节点类型 | `engine/node_factory.py` + `engine/nodes/` 注册表 | **29 种**（NodeFactory 注册；含阶段 1 新增 trigger-schedule/trigger-webhook/datasource/knowledge-index；原 workflow_runner 单体已按 graphon 模式拆分） |
| 熵舟前端 | `front/src/views/` + `router/index.ts` | **42 个视图 / 43 条路由** |
| 熵舟服务状态 | `curl localhost:5000 / 5173 /api/metrics` | **全部 200，运行中** |

---

## 一、Dify 1.17.0 架构总览（实测校正）

### 1.1 服务架构（15 容器实测）

```
Dify 1.17.0（docker-compose，实测 15 容器运行中）
├── nginx               # 反向代理（80/443）
├── web (Next.js)       # 前端（容器内 3000）
├── api (Flask)         # 主 API（容器内 5001，healthy）
├── api_websocket       # WebSocket 独立服务
├── worker (Celery)     # 异步任务
├── worker_beat         # Celery 定时调度
├── sandbox             # 代码沙箱（healthy）
├── local_sandbox       # 本地沙箱（5004，healthy）
├── plugin_daemon       # 插件运行时（5003 映射宿主机）
├── agent_backend       # Agent 独立后端（5050）★ 1.17 新增
├── ssrf_proxy          # SSRF 防护代理
├── agent_ssrf_proxy    # Agent SSRF 代理
├── db_postgres         # 主库 PostgreSQL（143 表）
├── pgvector            # 向量库（PostgreSQL 插件版）
└── redis               # 缓存/队列
```

### 1.2 重大架构变更：graphon 引擎（v15 文档未记录）

Dify 1.17.0 将工作流执行运行时抽离为独立 Python 包 **`graphon`**：

```
graphon（.venv/site-packages/graphon/）
├── enums.py            # BuiltinNodeTypes：节点类型字符串常量（NodeType = str，开放扩展）
├── graph/graph.py      # NodeFactory / GraphRuntimeState
├── nodes/              # 通用节点实现（code/llm/http_request/document_extractor/...）
├── model_runtime/      # 模型运行时抽象（与 Dify 主包解耦）
├── variables/          # 变量池（segments）
└── file/file_manager   # 文件抽象
```

Dify 主包（`api/core/workflow/`）退化为适配层：`node_factory.py`（DifyNodeFactory 注入模型访问、代码执行器、SSRF 代理、记忆等运行时依赖）、`llm_node.py`、`nodes/` 仅剩 10 个 Dify 专属目录（agent / agent_v2 / datasource / human_input / knowledge_index / knowledge_retrieval / trigger_plugin / trigger_schedule / trigger_webhook）。

**对熵舟的启示**：节点类型在 1.17 中已是**纯字符串开放注册**（`type NodeType = str`，"downstream packages can use additional strings without extending this class"），节点实现与运行时解耦。熵舟 `workflow_runner.py` 的 `if-elif` 分发器与 Dify 1.17 前的架构一致，属合理设计；后续若做插件化节点，可参考 graphon 的 NodeFactory 注入模式。

### 1.3 节点类型（实测枚举，30 种）

| 类别 | 节点（实测 graphon + core/workflow/nodes） |
|------|-------------------------------------------|
| graphon 内置 24 | start, end, answer, llm, knowledge-retrieval, if-else, code, template-transform, question-classifier, http-request, tool, datasource, variable-aggregator, variable-assigner(legacy), loop, loop-start, loop-end, iteration, iteration-start, parameter-extractor, assigner, document-extractor, list-operator, agent |
| Dify 专属 6 | agent_v2（DifyAgentNode）、human-input、knowledge-index、trigger-webhook、trigger-schedule、trigger-plugin |
| 其他 | custom-note（注释） |

### 1.4 后端 API 模块（实测 846 端点）

1.17 全面迁移至 flask_restx 命名空间路由（`@console_ns.route(...)` 830 处 + `add_resource` 16 处）。

| 模块 | 说明 |
|------|------|
| `controllers/console/` | 控制台（app/agent/datasets/billing/explore/extension/feature/snippet/tag/workspace/admin/auth 等 25 个子包） |
| `controllers/service_api/` | 面向开发者 API（workflow/chat/completion/audio/file/site/meta/parameters/messages/conversations） |
| `controllers/web/` | Web 端公开 API |
| `controllers/mcp/` | MCP 服务端点 |
| `controllers/trigger/` | 触发器 API |
| `controllers/inner_api/` | 服务间内部 API |

### 1.5 数据库（实测 144 表，较 v15 记录的 142 表新增）

| 较 v15 新增表 | 说明 |
|--------------|------|
| `human_input_form_deliveries` / `recipients` / `upload_files` / `upload_tokens` | Human Input 表单投递体系（4 张，替代单一 human_input_forms） |
| `pipelines` / `document_pipeline_execution_logs` | 知识 Pipeline 引擎 |
| `tool_mcp_provider_members` | MCP 工具提供者成员 |
| `trigger_subscriptions` / `trigger_oauth_system_clients` / `trigger_oauth_tenant_clients` | 触发器订阅与 OAuth |
| `oauth_provider_apps` / `oauth_access_tokens` | OAuth 服务端 |
| `load_balancing_model_configs` | 模型负载均衡 |
| `account_trial_app_records` | 试用应用 |

---

## 二、熵舟当前状态（2026-09-08 实测）

### 2.1 运行状态

| 服务 | 地址 | 状态 |
|------|------|------|
| Flask 后端 | :5000 | ✅ 200（`/api/stats/overview`） |
| 前端（Vite dev） | :5173 | ✅ 200 |
| Prometheus 指标 | :5000/api/metrics | ✅ 200 |
| MySQL 9.7 | szagent 库 | ✅ 57 表 |
| Redis 8.10.1 / Qdrant | 本机 | ✅ 随 start-all 启动 |

### 2.2 后端（Flask + MySQL + Celery + Redis）

| 维度 | 实测值 | 证据 |
|------|--------|------|
| 路由文件 | **34 个** | `routes/`（v15 记 28，新增 backup/cache/share 等） |
| API 端点 | **326 个** | grep `@bp.route/@app.route` |
| 工作流节点 | **29 种** | `engine/node_factory.py` + `engine/nodes/`（workflow_runner 已按 graphon 模式拆分为节点包） |
| 内置工具 | **12 提供者 / 49 动作** | `models/builtin_tools.py`（v15 记 18 动作，实际 49） |
| 内置技能 | **8 个** | `models/builtin_skills.py` |
| 内置数据源 | **12 个** | `models/builtin_data_sources.py`（Google Drive/GitLab/Notion/Jina/GitHub/SharePoint/Confluence/Tavily/OneDrive/S3/COS/Firecrawl） |
| 数据库表 | **90 张**（全部业务表，遗留备份表已删除） | information_schema 实测（2026-09-22 复核） |
| Celery 任务 | 5 文件（workflow/embedding/scheduled/backup + app） | `tasks/` |
| 工具模块 | 16 个 | `utils/`：auth/cache_manager/cache_warmer/encryption/helpers/llm/logger/login_lockout/metrics/redis_cache/rerank/sandbox/ssrf/storage/vector_store/ws |

**v15 之后新增实测确认**：
- `routes/share.py`（7 端点）：公开分享链接创建/查询/禁用、分享聊天/工作流信息、匿名运行 → 前端 `ShareChatView.vue` / `ShareWorkflowView.vue` 已就绪
- `routes/backup.py`（7 端点）、`routes/cache.py`（6 端点，缓存管理/预热）
- `workflows.py` 新增 `POST /api/workflows/<id>/pause` + `POST /api/workflows/<id>/resume`（`workflow_pauses` 表，含 resume_strategy/timeout_seconds）
- 模型配置 Fernet 加解密（`routes/models.py`：`decrypt` 端点 + `_encrypt_sensitive_fields`）
- `ExploreView.vue` 已接入真实 API（`/api/installed-apps`、`/api/app-templates`、`/api/agent-templates`、`/api/workflow-templates`）
- 新增 10 张表（v15 曾列为"缺失"）：`human_input_forms`、`installed_apps`、`app_mcp_servers`、`tool_api_providers`、`tool_builtin_providers`、`tool_mcp_providers`、`tool_workflow_providers`、`workflow_pauses`、`workflow_conversation_variables`、`workflow_draft_variables`

### 2.3 后端路由实测明细（34 文件 / 326 端点，按端点数排序）

| 路由文件 | 端点数 | 核心功能 |
|---------|--------|---------|
| `workflows.py` | 39 | 工作流 CRUD + 运行 + **暂停/恢复** + 版本 |
| `tools.py` | 24 | 内置工具/工作流工具/调用日志 |
| `knowledge.py` | 20 | 知识库 CRUD/分段/召回测试/权限 |
| `auth.py` | 18 | 用户/角色/权限/API Key |
| `agents.py` | 18 | 单智能体 CRUD/聊天 |
| `multi_agents.py` | 15 | 多智能体 |
| `plugins.py` | 13 | 插件市场发布/安装/启停 |
| `mcps.py` | 12 | MCP 服务器管理/工具探测 |
| `workflow_debug.py` | 11 | 断点调试/批量运行 |
| `workflow_templates.py` | 9 | 工作流模板市场 |
| `service_api.py` | 9 | /v1 workflows/chat/completion/files |
| `app_templates.py` | 9 | 应用模板 |
| `webhooks.py` | 8 | Webhook 注册/触发/日志 |
| `site.py` | 8 | 站点信息/功能开关/OpenAPI 导入 |
| `conversations.py` | 8 | 对话历史 |
| `agent_templates.py` | 8 | Agent 模板 |
| `share.py` | 7 | **公开分享（新）** |
| `evaluations.py` | 7 | Agent 评测 |
| `backup.py` | 7 | **数据库备份管理（新）** |
| `annotations.py` | 7 | 标注 CRUD/审核 |
| `skills.py` | 6 | 技能 |
| `cache.py` | 6 | **缓存管理/预热（新）** |
| `tasks.py` | 5 | 异步任务查询 |
| `stats.py` | 5 | 统计 + /api/metrics |
| `models.py` | 5 | 模型配置（含加解密） |
| `files.py` | 5 | 文件上传 |
| `feedback.py` | 5 | 消息反馈 |
| `conversation_summaries.py` | 5 | 对话摘要 |
| `account.py` | 5 | 当前用户 |
| `data_sources.py` | 4 | 数据源 |
| `custom_connectors.py` | 4 | 自定义连接器 |
| `chat.py` | 4 | 聊天流式 |
| `audit.py` | 4 | 审计日志 |
| `my_agents.py` / `memories.py` | 3+3 | 我的智能体 / 记忆 |

### 2.4 数据库表实测清单（v5.0 快照 57 张 · 2026-09-22 实测 90 张）

**v15 记录 58 张，v5.0 实测 57 张**（差异：v15 中 `vector_collections` 等已不在库中，新增下表 ★ 10 张；另有 1 张遗留表建议删除）。

> **2026-09-22 复核**：当前实测 **90 张**（原 57 张 + 阶段 1-4 陆续落地的约 33 张，如 `workflow_schedule_plans`、`trigger_subscriptions`、`workflow_trigger_logs`、`dataset_metadatas`/`_bindings`、`dataset_keyword_tables`、`external_knowledge_apis`/`_bindings`、`dataset_retriever_resources`、`message_agent_thoughts`、`agent_config_revisions`、`agent_skill_bindings`、`tool_oauth_*`、`tool_label_bindings`、`human_input_form_deliveries`、`knowledge_pipelines`、`workflow_comments` 等）。原 1 张遗留备份表 `users_backup_20260903_150012` **已删除 ✅**。下方分类清单为历史快照，保留作对照。

| 分类 | 表 | 数量 |
|------|-----|------|
| 用户/权限 | ~~users_backup_20260903_150012~~（**已删除 ✅**）、dify_accounts、dify_tenants、dify_tenant_account_joins、roles、user_roles、permissions、role_permissions | 7 |
| 应用/智能体 | dify_apps、dify_app_model_configs、dify_sites、dify_api_tokens、agents、memories、app_templates、agent_templates、**installed_apps ★**、**app_mcp_servers ★** | 10 |
| 知识库 | dify_datasets、dify_documents、dify_document_segments、dify_annotations | 4 |
| 工作流 | dify_workflows、dify_workflow_runs、dify_workflow_node_executions、dify_workflow_version_counters、workflow_versions、workflow_test_runs、workflow_debug_sessions、workflow_batch_runs、**workflow_pauses ★**、**workflow_conversation_variables ★**、**workflow_draft_variables ★** | 11 |
| Human Input | **human_input_forms ★** | 1 |
| 工具/插件 | dify_tool_providers、dify_datasource_providers、tool_installs、tool_call_logs、workflow_tools、tool_settings、skills、skill_installs、mcp_servers、data_sources、custom_connectors、plugins、plugin_installs、webhooks、webhook_logs、**tool_api_providers ★**、**tool_builtin_providers ★**、**tool_mcp_providers ★**、**tool_workflow_providers ★** | 19 |
| 对话/消息 | dify_conversations、dify_messages、dify_message_feedbacks、dify_message_annotations、conversation_summaries | 5 |
| 模型/系统 | model_configs、dify_providers、dify_provider_models、dify_audit_logs | 4 |

### 2.5 前端（Vue 3 + Vite + Pinia + TypeScript，42 视图实测）

视图清单（`front/src/views/`，42 个）：Login / Home / AccountInfo / MyAgents / SingleAgent(+Edit) / MultiAgent(+Edit) / AgentDetail / AgentConfig / AgentChat / AgentLogs / AgentMonitor / WebAgent / AgentTemplates / WorkflowApp / WorkflowStudio / WorkflowTemplates / AppTemplates / TemplateStudio / Knowledge(+Create/Detail/Process) / Models / Skills(+Detail) / Mcp / Connectors / Tools / Users / Roles / Permissions / Audit / **Annotation** / Functions / **Explore ★（新）** / **ShareChat ★（新）** / **ShareWorkflow ★（新）** / Plugins / Webhooks / Evaluation。

路由 43 条（`router/index.ts`）。

---

## 三、功能差距详细对比（逐项实测，2026-09-08）

### 3.1 工作流引擎

| 功能 | Dify 1.17.0（实测） | 熵舟（实测） | 差距与结论 |
|------|---------------------|-------------|-----------|
| 节点类型 | 30 种 | 25 种 | 🟡 缺 5 种：`datasource`、`knowledge-index`、`trigger-webhook`、`trigger-schedule`、`trigger-plugin`（`reply`/`pause` 已由 answer/human-input + 暂停 API 覆盖） |
| 引擎架构 | graphon 独立运行时 + NodeFactory 注入 | 单文件 `workflow_runner.py`（4121 行）分发 | 🟡 功能等价，架构待解耦（见 3.1.1） |
| 错误处理 | 重试+超时+退避 | ✅ 重试+超时（`_execute_node_with_retry/with_timeout`） | ✅ 已对齐 |
| 异步执行 | Celery + worker | ✅ Celery + Redis | ✅ 已对齐 |
| 定时触发 | ✅ trigger-schedule 节点 + schedule_plans | ❌ 仅有内部维护任务（embedding/清理/健康检查） | 🔴 **P0**：用户可定义 Cron 触发缺失 |
| Webhook 触发 | ✅ trigger-webhook **节点** + 触发器 API | ✅ Webhook 注册/触发/日志（路由级），非节点 | 🟡 P1：画布内触发节点缺失 |
| 暂停/恢复 | ✅ workflow_pauses + 表单投递体系（4 表） | ✅ workflow_pauses 表 + pause/resume API + **Human Input 邮件投递**（`human_input_form_deliveries`+SMTP，阶段3，38/38） | ✅ 已对齐 |
| 断点调试 | ✅ | ✅ 单步/断点/变量（workflow_debug.py 11 端点） | ✅ 已对齐 |
| 批量运行 | ✅ | ✅ CSV 批量 + 结果导出 | ✅ 已对齐 |
| 版本管理 | draft variables + 版本计数器 | ✅ workflow_versions + draft variables 表 | ✅ 已对齐 |
| 评论协作 | ✅ workflow_comments/replies/mentions（3 表） | ❌ | 🟡 P2 |
| 变量池 | graphon variables/segments | ✅ conversation/draft variables 表 | ✅ 表已建，需打通运行时读写 |

**3.1.1 架构债务**：`workflow_runner.py` 已 4121 行，节点实现内联。建议按 graphon 模式拆分为 `engine/nodes/<node>.py` + `engine/node_factory.py`，否则每加一个节点都加重单文件风险。（P2，重构不改变行为）

### 3.2 知识库/RAG

| 功能 | Dify 1.17.0 | 熵舟 | 差距与结论 |
|------|-------------|------|-----------|
| 分段策略 | 通用+父子+Q&A+表格 | ✅ 4 种 | ✅ 已对齐 |
| Rerank | 多模型 | ✅ 4 级回退 | ✅ 已对齐 |
| 召回测试 | ✅ | ✅ 可视化 + rerank | ✅ 已对齐 |
| 元数据系统 | ✅ metadatas/bindings（结构化字段+过滤） | ✅ `dataset_metadatas`/`dataset_metadata_bindings` + 字段 CRUD + 分段绑定 + SQL 过滤（阶段2） | ✅ 已对齐（过滤走关系型预/后过滤，非 Qdrant payload） |
| 关键词表 | ✅ dataset_keyword_tables | ✅ `dataset_keyword_tables` + jieba 分词 + 向量/关键词混合检索（阶段3，`e2e_keyword_check` 28/28） | ✅ 已对齐 |
| 外部知识 API | ✅ external_knowledge_apis/bindings | ✅ `external_knowledge_apis` 表 + 检索代理，外部 API 结果并入召回（阶段3，32/32） | ✅ 已对齐 |
| 图片 OCR | ✅ | ❌ | 🟡 P2 |
| 引用追踪 | ✅ dataset_retriever_resources | ✅ `engine/retrieval_resources.py` + `dataset_retriever_resources` 表 + `chat.py` 落库/回传 + AgentChatView 引用气泡（阶段3，18/18） | ✅ 已对齐 |
| Pipeline | ✅ pipelines + 执行日志 | ❌ | 🟡 P2 |
| 分段摘要 | ✅ document_segment_summaries | ❌ | 🟡 P2 |
| Embedding 异步 | ✅ Worker | ✅ Celery（generate_pending_embeddings 定时兜底） | ✅ 已对齐 |

### 3.3 Agent 能力

| 功能 | Dify 1.17.0 | 熵舟 | 差距与结论 |
|------|-------------|------|-----------|
| Agent 节点 | ✅ 双实现（agent legacy + **agent_v2 DifyAgentNode**） | ✅ 策略注册表 react/function_call/plan_execute + on_thought + 配置版本（阶段2） | 🟡 进程内实现 vs Dify 插件型 provider（已接受架构差异） |
| 长期记忆 | ✅ 持久化 + 向量检索 | ✅ `agent_memory.py` 向量双写 MySQL+Qdrant + 语义检索注入（阶段2，含 MySQL 回退余弦兜底） | ✅ 已对齐（实时向量需先配 embedding 模型） |
| 多轮记忆压缩 | ✅ | ✅ 摘要 + 滑动窗口 | ✅ 已对齐 |
| 思考链 | ✅ message_agent_thoughts | ✅ `thought_chain.py` + `message_agent_thoughts` + `ThoughtChain.vue`（阶段2） | ✅ 已对齐 |
| 配置版本 | ✅ drafts/snapshots/revisions（3 表） | ✅ `agent_config_revisions`（ConfigRevisionManager） | 🟡 已有 revisions，缺 drafts/snapshots |
| 工作空间 | ✅ agent_workspaces/bindings | ❌ | 🟡 P3 |
| 技能绑定 | ✅ agent_skill_bindings + snapshots | ⚠️ skills/skill_installs 存在，未绑定到 Agent | 🟡 P1 |
| 沙箱 | ✅ Docker 隔离 | ⚠️ 子进程隔离 | 🟡 已知折衷（非 Docker 约束） |
| 独立 Agent 后端 | ✅ agent_backend 容器（5050） | ❌ 同进程 | 🟡 P3：进程级隔离可选 |

### 3.4 工具/插件生态

| 功能 | Dify 1.17.0 | 熵舟 | 差距与结论 |
|------|-------------|------|-----------|
| 内置工具 | 100+ | 12 提供者/49 动作 | 🟡 P2：可分批扩至 Dify 官方常用集（计算器/翻译/Stable Diffusion/DALL-E 等） |
| 工具提供者四表 | ✅ builtin/api/workflow/mcp | ✅ **四表已建 ★** | ✅ 表结构对齐，需补管理 API/UI |
| 自定义工具 | ✅ OpenAPI 导入 | ✅ | ✅ 已对齐 |
| 工作流作为工具 | ✅ | ✅ | ✅ 已对齐 |
| 插件市场 | ✅ Marketplace + Plugin Daemon | ✅ 发布/安装/管理（无守护进程） | 🟡 已知折衷 |
| 工具 OAuth | ✅ system/tenant 双端客户端 | ✅ `tool_oauth_system/tenant_clients`+`tool_oauth_tokens` 表 + 授权回调 + token 刷新（阶段3，49/49） | ✅ 已对齐 |
| 工具标签 | ✅ tool_label_bindings | ✅ `tool_label_bindings` 表 + 版本字段 + ToolsView 标签筛选（阶段3，36/36） | ✅ 已对齐 |
| 工具调用日志 | ✅ | ✅ tool_call_logs + ToolsView | ✅ 已对齐 |
| MCP | ✅ 客户端 + 服务端 | ✅ 节点 + 12 端点 + **MCP Server `/mcp/v1`（SSE）**，暴露熵舟工具为 MCP Server（阶段3，28/28） | ✅ 已对齐 |

### 3.5 Service API（开发者 API）— 差距最大的模块之一

| Dify 端点 | 熵舟 | 结论 |
|-----------|------|------|
| /v1/workflows/run(+status/stop/logs) | ✅ 4 端点 | ✅ 已对齐 |
| /v1/chat-messages(+stop) | ✅ 2 端点 | ✅ 已对齐 |
| /v1/completion-messages | ✅ | ✅ 已对齐 |
| /v1/files/upload + /v1/files/<id> | ✅ 2 端点 | ✅ 已对齐 |
| /v1/info | ✅ `service_api.py:445` | ✅ 已对齐（应用名称/描述/标签） |
| /v1/parameters | ✅ `service_api.py:460` | ✅ 已对齐（开场白/建议问题/文件上传/annotation_reply） |
| /v1/messages（列表/反馈） | ✅ `service_api.py:546` + `/v1/messages/<id>/feedbacks:608` | ✅ 已对齐 |
| /v1/conversations（列表/删/重命名） | ✅ `service_api.py:668` + `DELETE:707` + `POST /name:734` | ✅ 已对齐 |
| /v1/meta（工具图标/元数据） | ✅ `service_api.py:1074` | ✅ 已对齐 |
| /v1/apps（发布渠道列表） | ❌ | 🟡 非 Dify 标准 service-api 命名空间端点，可按需补 |
| /v1/audio-to-text / text-to-audio | ✅ 2 端点（复用 audio 内置工具；`e2e_audio_api_check` 19/19） | ✅ 已对齐（阶段4） |

### 3.6 触发器体系

| 功能 | Dify 1.17.0 | 熵舟 | 结论 |
|------|-------------|------|------|
| Webhook 触发 | ✅ 节点 + API + 订阅 | ✅ 路由级 Webhook（8 端点完整） | 🟡 P1：节点化 + 订阅管理 |
| 定时触发 | ✅ trigger-schedule + workflow_schedule_plans | ❌ 仅内部维护 Beat | 🔴 **P0** |
| 插件触发 | ✅ trigger-plugin | ❌ | 🟡 P2 |
| 触发日志 | ✅ workflow_trigger_logs | ✅ webhook_logs | ✅ 已对齐（webhook 范围） |
| 触发器 OAuth | ✅ 双端客户端 | ❌ | 🟡 P3 |

### 3.7 前端工程化

| 功能 | Dify 1.17.0 | 熵舟 | 结论 |
|------|-------------|------|------|
| TypeScript | ✅ | ✅ 100% | ✅ 已对齐 |
| 探索/Explore | ✅ | ✅ ExploreView（真实 API） | ✅ 已对齐（★ v15 后补齐） |
| 公开分享 | ✅ shareLayout | ✅ ShareChat/ShareWorkflow + share.py | ✅ 已对齐（★ v15 后补齐） |
| 组件库 | shadcn/ui 50+ | ✅ **20 个**统一基础组件（Modal/Select/Tabs/Toast/Button/Input/Card/Badge/Dropdown/Collapse/Tooltip/Switch/Progress/Spinner/Textarea/Divider/EmptyState/Breadcrumb… + `index.ts`） | ✅ 已对齐（阶段4） |
| 响应式 | ✅ | ✅ `style.css` 1400/1280/1024/768/480px + `(hover:none)` 触控断点（阶段4） | ✅ 已对齐 |
| 国际化 | 20+ 语言 | ✅ 中英文双语（`locales/index.ts` 轻量 i18n：`t()`/`setLocale`/`locale`；导航 `AppShell`/搜索/`stores/app` 已接线，可运行时切换并 localStorage 持久化） | 🟢 已具备（v5.9 核验：功能完整，非空转脚手架；仅覆盖中英，距 20+ 语言为量差） |
| 版本 Diff 视图 | ✅ | ✅ `VersionPanel.vue` 对比视图（选定两版本调 `/versions/diff`，节点/边增删改结构化展示）（阶段4） | ✅ 已对齐 |
| 评论协作 | ✅ | ❌ | 🟡 P2 |
| 快捷键 | 完整 | Cmd+K | 🟡 P3 |

### 3.8 部署运维（非 Docker 约束下的对齐）

| 功能 | Dify 1.17.0 | 熵舟 | 结论 |
|------|-------------|------|------|
| 容器编排 | ✅ Compose 15 容器 | ✅ bat/ps1 脚本体系（start-all/check-health/backup） | ✅ 按非 Docker 约束对齐 |
| 结构化日志 | ✅ | ✅ utils/logger.py JSON + 轮转 | ✅ 已对齐 |
| 指标 | ✅ | ✅ /api/metrics + utils/metrics.py | ✅ 已对齐 |
| 备份 | ✅ | ✅ backup-mysql.bat + backup.py 管理端点 | ✅ 已对齐（★ 新增管理端点） |
| 缓存管理 | ✅ | ✅ cache.py + cache_manager/cache_warmer | ✅ 已对齐（★ 新增） |
| 登录锁定 | ✅ | ✅ utils/login_lockout.py | ✅ 已对齐 |
| 对象存储 | ✅ S3/MinIO | ✅ utils/storage.py 抽象（Local + MinIO/S3） | ✅ 已对齐 |
| CI/CD | ✅ GitHub Actions | ✅ GitHub Actions（后端 compileall + 前端 build） | 🟢 已落地（v5.6） |
| SSO | ✅ OAuth2/SAML/LDAP | ✅ OAuth2（Google/GitHub） | 🟢 OAuth2 已落地；SAML/LDAP 未做（P3 可裁剪） |
| 多租户 | ✅ 完整隔离 | ⚠️ tenant 表存在，单租户运行 | 🟡 P2 |

### 3.9 安全

| 功能 | Dify 1.17.0 | 熵舟 | 结论 |
|------|-------------|------|------|
| 认证 | JWT + API Key + OAuth | ✅ JWT（Access+Refresh）+ API Key + Fernet | ✅ 已对齐 |
| 模型密钥加密 | ✅ | ✅ `_encrypt_sensitive_fields` + decrypt 端点（★） | ✅ 已对齐 |
| RBAC | ✅ Owner/Admin/Normal + 资源级 | ⚠️ admin/user + 权限点，无资源级 | 🟡 P2：app 级权限矩阵 |
| 沙箱 | ✅ Docker | ⚠️ 子进程 | 🟡 已知折衷 |
| SSRF | ✅ 独立代理 | ⚠️ 代码层 utils/ssrf.py | 🟡 已知折衷 |
| 审计 | ✅ operation_logs | ✅ dify_audit_logs + AuditView | ✅ 已对齐 |

---

## 四、覆盖度实测

### 4.1 总量对比

```
                Dify 1.17.0          熵舟                覆盖率
数据库表:       143 业务表            90 业务表            63%
API 端点:       ~846                 326                 38%
工作流节点:     30                   29                  97%
容器/服务:      15                   5 进程              非 Docker 对齐
```

### 4.2 分维度完成度评分（功能等价口径，非表数量口径）

| 维度 | 熵舟 | 差距要点 |
|------|------|---------|
| 工作流引擎 | 95% | 阶段 1 已补齐 datasource/knowledge-index/trigger-schedule/trigger-webhook 4 节点 + 定时触发；仅剩 trigger-plugin 等 |
| 知识库/RAG | 94% | 阶段3 已补关键词混合检索/外部知识 API/引用追踪（仅余 OCR/分段摘要/Pipeline） |
| Agent 能力 | 92% | 阶段2 已补策略注册表(react/fc/plan_execute)/长期记忆向量化（本轮 embedding 配置后端到端打通）/思考链/配置版本；待技能绑定到Agent/Docker 沙箱/agent 工作空间 |
| 工具生态 | 90% | 阶段3 已补 OAuth/标签版本/MCP 服务端；待内置工具批量扩展 |
| Service API | 92% | info/parameters/messages/feedbacks/conversations(列表/删/重命名)/meta/site/files/audio 均已实现（本轮 v5.9 核验）；仅缺非标准的 /v1/apps 发布渠道端点 |
| 触发器 | 85% | trigger-schedule 节点+croniter 调度+beat 派发+触发日志、trigger-webhook 节点、订阅管理 API 已落地；缺插件触发 |
| 前端 | 96% | Explore/分享/版本Diff视图/20 组件库/响应式断点/中英文双语 i18n 已齐（`vite build` 退出码 0）；仅剩评论协作 |
| 部署运维 | 92% | 非 Docker 约束下基本对齐；CI/CD（GitHub Actions）+ OAuth2 SSO 已落地（v5.6） |
| 安全 | 95% | 资源级 RBAC（app/workflow/dataset/tool 权限矩阵 + 装饰器）已落地（v5.6，单租户 owner/admin/published 模型）；缺跨成员细粒度共享授权 |

---

## 五、详细实施计划（2026-09-08 起，按优先级）

> 每项任务给出：目标 / 涉及文件 / 实施要点 / 验收标准。工作量按单人日估算。
> 原则：**以实测差距为准，逐项落地为可运行功能**，每阶段结束做端到端验证（curl + 页面操作）。

### 阶段 0：清理与技术准备（0.5 天）  ✅ 已完成（2026-09-22 复核）

| 任务 | 文件 | 要点 | 验收 | 状态 |
|------|------|------|------|------|
| 删除遗留备份表 | MySQL | 遗留备份表 `users_backup_20260903_150012` 经代码全局检索**无任何引用**，且 2026-09-22 实测该表**已不存在**（`SHOW TABLES LIKE 'users%'` 为空），无需再执行 DROP | ✅ 目标已达成：无遗留/备份表；当前业务表 **90 张** | ✅ |
| 前端遗留原型清理 | `front/legacy/` | 静态原型 HTML（转换前备份）经检索**未被** `index.html`/`vite.config.ts`/`src/**` 引用；**v5.7 V1.0 发布前已 `git rm` 移除（共 42 文件）**，历史可经 git 查阅；README 相应引用同步修正 | ✅ 移除后 `vue-tsc --noEmit && vite build` 退出码 **0** | ✅ |

> 说明：本阶段验收基线中的“表列表 56 张”为 v5.0 旧快照；因阶段 1-4 已陆续建表，2026-09-22 实测为 **90 张**（详见 §2.4 复核说明），阶段 0 的两项清理目标均已满足。

### 阶段 1（P0）：触发器 + 缺失节点 + Service API 补齐（约 8 天）  ✅ 已完成（2026-09-22 复核）

> **实现落点与复核（与下方原计划的 `workflow_runner.py 分支` 写法不同，实际已按 graphon 模式拆分为独立引擎 + 节点包）**：
> - 触发器：`engine/trigger_engine.py`（croniter 计划同步/到期派发/日志回填）+ `tasks/scheduled.py:dispatch_due_schedule_plans` + `celery_app.py` beat 每分钟 + `routes/workflows.py` 保存图时 `sync_trigger_plans`
> - 节点引擎：`engine/datasource_engine.py`、`engine/knowledge_index_engine.py`；均在 `engine/node_factory.py` 注册（`trigger-schedule`/`trigger-webhook`/`datasource`/`knowledge-index`）
> - 前端：`front/src/utils/workflow/nodeRegistry.ts`（新增「触发」分组）、`panels/{TriggerPanel,DatasourcePanel,KnowledgeIndexPanel}.vue`、`PanelRegistry.ts`
> - 验收脚本：`backend/tests/e2e_phase1_triggers_nodes_check.py`（确定性 8 项：cron 计算/计划 upsert+停用孤儿/到期派发(桩化 Celery)/日志回填/datasource&knowledge-index 校验分支/节点注册）—— 2026-09-22 实测 **8 PASS / 0 FAIL**

**1.1 定时触发（trigger-schedule）— 2 天**  ✅ 已完成（引擎实测：cron 计算/upsert+停用孤儿/到期派发/日志回填 全通过；回归 trigger-schedule/webhook PASS）
- 新建表 `workflow_schedule_plans`（id, app_id, node_id, cron_expr, enabled, last_run_at, next_run_at）
- `models/enums.py` 无依赖，直接 SQL 建表 + `models/tables.py` 注册
- `engine/workflow_runner.py` 增加 `trigger-schedule`/`trigger-webhook` 节点分支（触发节点：产生调度计划，不执行业务）
- `tasks/scheduled.py` + `celery_app.py` beat_schedule 增加每分钟的 `dispatch_due_schedule_plans`（查 next_run_at 到期计划 → 异步启动工作流 → 写 `workflow_trigger_logs` 新表）
- 前端 `PropertyPanel.vue` 增加触发节点分组（NodeLibrary + nodeRegistry.ts）
- 验收：画布配置 cron `*/2 * * * *` → 工作流每 2 分钟自动运行，`workflow_trigger_logs` 有记录，前端触发器页可见

**1.2 datasource 节点 — 1.5 天**  ✅ 已完成（`engine/datasource_engine.py`：内置 jina/firecrawl/tavily/github/gitlab/notion + 自定义连接器；SSRF 防护 + 「错误即输出」语义实测；回归 datasource PASS）
- `engine/workflow_runner.py` 增加 `datasource` 分支：调用 `models/builtin_data_sources.py` 12 个数据源 + `custom_connectors` 表中的自定义连接器（复用现有 connector 调用逻辑）
- nodeRegistry.ts 增加节点定义（图标/输入输出 schema 参照 Dify `nodes/datasource/`）
- 验收：画布拖入数据源节点选 Notion → 运行返回文档列表

**1.3 knowledge-index 节点 — 1 天**  ✅ 已完成（`engine/knowledge_index_engine.py`：复用 `routes/knowledge.py` 分段器写库 + 异步 embedding；校验分支实测；回归 knowledge-index PASS）
- `engine/workflow_runner.py` 增加 `knowledge-index` 分支：将上游文本按数据集分段规则写入 `dify_document_segments` + 触发 `tasks/embedding_tasks.py`
- 验收：工作流输出文本 → 指定数据集出现新分段且向量化完成

**1.4 Service API 补齐 — 2 天**  ✅ 已完成（14/14 E2E 通过）
- `routes/service_api.py` 新增：
  - `GET /v1/info`（应用名称/描述/标签）
  - `GET /v1/parameters`（开场白/建议问题/文件上传/**annotation_reply** 等 Dify 标准字段；★ 2026-09-22 复核补齐此前缺失的 `annotation_reply`，回归 14/14）
  - `GET /v1/messages` + `POST /v1/messages/<id>/feedbacks`（like/dislike/null，批量反馈回显）
  - `GET /v1/conversations` + `DELETE /v1/conversations/<id>`（软删）+ `POST /v1/conversations/<id>/name`
- `chat-messages` 阻塞/流式双模式均补充会话+消息落库（`_persist_chat_turn`），下游 messages/conversations 接口有真实数据
- 认证修正：API Key 实际存储在 `dify_api_tokens`（`app-xxx` 格式），原装饰器误查 `dify_apps.api_key`（不存在列）→ 改为 JOIN `dify_api_tokens`；应用状态过滤由 `active` 改为 `normal`（本仓库实际状态值）
- 修复 `dify_message_feedbacks` 表缺失（原从未建表），在 `register_service_api_routes` 时自动建表
- 修复工作流输出提取：`_extract_answer` 兼容 `answer`/`text`/`output` 等多键（本仓库工作流输出不统一）
- 验收脚本：`backend/tests/e2e_service_api_check.py`（14 项：401/400/404/幂等/反馈回显/软删隐藏）

**1.5 触发器订阅管理 API — 0.5 天**  ✅ 已完成（16/16 E2E 通过）
- 新建 `trigger_subscriptions` 表（tenant_id/app_id/trigger_type/target_id/node_id/subscriber_type/subscriber_target/enabled/触发计数）
- 新建 `routes/trigger_subscriptions.py`，挂载到 `/api/workflows/<app_id>/trigger-subscriptions` 与 `/api/trigger-subscriptions/<sub_id>`，在 `routes/__init__.py` 注册
- 5 个端点：
  - `GET /api/workflows/<app_id>/trigger-subscriptions`（列表）
  - `POST`（新建；subscriber_type=email/webhook/api；邮箱/URL 格式校验；webhook 目标走 SSRF 安全校验；同 target+subscriber 幂等不重复创建）
  - `PUT /api/trigger-subscriptions/<sub_id>`（启停/改目标）
  - `DELETE`（删除）
  - `GET /api/trigger-subscriptions/<sub_id>/logs`（按 plan_id/webhook_id 过滤的触发日志分页）
- 验收脚本：`backend/tests/e2e_trigger_subs_check.py`（16 项：参数校验/SSRF 拦截/幂等/启停/日志）

**1.6 端到端回归 — 1 天**  ✅ 已完成（25 PASS / 0 FAIL / 2 SKIP，2026-09-22 复跑 111s；修复下列拆分遗留缺陷后 0 FAIL）
- 新建 `backend/tests/test_node_regression.py`，覆盖 runner 全部分支：
  - Tier 1 确定性：start/end、answer、code、if-else、template-transform、variable-aggregator、assigner、list-operator、custom-note、document-extractor、trigger-schedule、trigger-webhook、human-input、loop
  - Tier 2 LLM：llm、question-classifier、parameter-extractor、agent、batch-task、iteration
  - Tier 3 外部依赖：http-request、datasource、knowledge-index、sub-graph、tool
  - 环境依赖 SKIP：knowledge-retrieval（embedding 异步 90s 未完成）、mcp（阶段3 外部依赖）
- 修复的真实代码缺陷（非仅测试适配）：
  - 条件分支操作符映射补全：`> / < / >= / <=` 符号现在正确映射到 `greater_than` 等（前端/旧数据混用符号会走错分支）
  - 工具运行时重构 `engine/tool_runtime.py`：原 `_invoke_tool` 只认 4 个硬编码内置提供者，DB 里已安装的 calculator/json/file/time/webscraper/email 等 12 个提供者全部异常；现在按 `tool_builtin_providers → tool_api_providers → dify_tool_providers` 三层查找；内置动作完整实现（安全算术求值 `_safe_eval`、单位换算、JSON 解析/序列化、文件读写路径穿越防护、SQL 只读查询、SSRF 防护）；旧 `dify_tool_providers` 查询修正（原引用不存在的 `name` 列，实际为 `tool_name`）
  - 沙箱输出捕获：`utils/sandbox.py` 子进程现在回传顶层赋值变量（`assigned` 字典，如 `sub_out = 'SUB_OK'`），`engine/workflow_runner.py` 的 `_node_code` 输出提取逻辑从只读 `result` 改为 `assigned → result(dict) → input_vars` 三级回退
  - 子工作流输出映射兼容两种形状（dict `{"子变量": "当前变量"}` 和 list 选择器）
  - 修复 `start-services.ps1`：原生 `.exe`（qdrant/redis）现在直接 `Process.Start`，不再包 `cmd.exe /c` 隐藏控制台——qdrant 1.19 在该模式下会被静默杀掉且无日志（已确认复现并修复，冷启动全量验证 ALL OK）
  - **（2026-09-22 新增）agent 节点悬空导入**：workflow_runner 早期按 graphon 模式拆分后，`engine/agent_strategies.py` 内 5 处函数级懒导入仍指向已不存在的 `engine.workflow_runner` 名字（`_call_llm`/`_http_request`/`_build_openai_url`/`_build_tool_descriptions`/`_execute_agent_tool`），运行时 agent 节点 500；已改指向符号真实位置（`utils.llm.build_openai_url` / `engine.nodes.llm._http_request` / `engine.nodes.agent` 的两个工具函数），并将无对应实现的 `_call_llm` 就地重写为 OpenAI 兼容调用，保持 `{content,total_tokens}` 契约
  - **（2026-09-22 新增）agent 模型误匹配**：`engine/nodes/agent.py` 的 `_find_model_config` 剥离 `langgenius/deepseek/deepseek` 得到 `deepseek/deepseek` 而非 `deepseek`，导致匹配失败并回退「任意可用模型」抓到错误 provider（400 Bad Request）；已改为取中间短名匹配，与 `nodes/llm.py` 一致
  - **（2026-09-22 新增）datasource_engine** 显式 `import urllib.error`（原仅 `urllib.parse`/`urllib.request`，依赖隐式子模块绑定）

### 阶段 2（P1）：Agent 增强 + RAG 元数据（约 7 天） ✅ 已实现（2026-09-22 复核）

> **复核结论**：四项能力前后端**均已落地**（代码远早于本文档记录）。本轮据实核验并修复 1 处健壮性缺陷，补齐确定性功能测试。
> **落点总览**：`engine/agent_memory.py`(472) · `engine/thought_chain.py`(160) · `engine/agent_strategies.py`(873，注册表+3 策略) · `engine/metadata_engine.py`(385) · 表 `memories`(向量化列)/`message_agent_thoughts`/`agent_config_revisions`/`dataset_metadatas`/`dataset_metadata_bindings` · 前端 `components/ui/ThoughtChain.vue` + `views/AgentChatView.vue`/`views/KnowledgeDetailView.vue`。
> **验证资产**：`tests/e2e_agent_memory_check.py`(11) · `tests/e2e_thought_chain_check.py`(6，实测 **6/6 PASS**) · `tests/e2e_metadata_check.py`(15) · 新增 `tests/e2e_phase2_agent_rag_check.py`（确定性 **8/8 PASS**，桩化 embedding，不依赖模型/网络/真实 Qdrant）。

**2.1 Agent 长期记忆向量化 — ✅**
- 实现：`engine/agent_memory.py` `add_memory`→`_queue_embedding`（Celery `embedding` 队列 `embed_agent_memory`，降级同步）→`embed_memory` 生成向量并 `_persist_embedding` 双写 MySQL(`memories.embedding`)+Qdrant(`agent_memory__{id}` 集合，按 agent 隔离)；`search_memories`/`build_memory_context` 检索 top-k 注入 system prompt（`routes/chat.py:411,721 _inject_memory_context`，`memory_enabled` 开关；对话后 `_auto_save_memory` 回写）。
- **本轮修复（健壮性缺陷）**：当前运行解释器未安装 `qdrant_client` → 向量存储回退 MySQL，而 `_upsert_mysql` 仅保留 `content` 丢弃 `payload.memory_id`，导致 `search_memories` 命中无法回映射、检索恒为空。已在 `search_memories` 增加 **MySQL 原生余弦兜底**（`_search_memories_local`：直接对 `memories.embedding` 做 `cosine_similarity` 排序），两种后端均可用；确定性测试覆盖。
- Dify 对比：Dify 长期记忆走 `memory` 会话变量 + 数据集检索；本方案为 agent 级向量记忆（自有设计，功能对齐"跨会话召回"）。
- ⚠️ 环境前置：`e2e_agent_memory_check` 的实时向量检索需**先配置 embedding 模型**（`model_configs` 当前仅 `llm`、无 embedding 记录）；否则向量无法生成（与阶段1 knowledge-retrieval SKIP 同源）。

**2.2 Agent 思考链记录 — ✅（实测 6/6 PASS）**
- 实现：`engine/thought_chain.py` `save_thought_chain`/`get_thought_chain`/`delete_thought_chain` 落 `message_agent_thoughts`(id, message_id, position, thought, tool_name, tool_input, tool_output, observation)；策略经 `on_thought` 回调产出 `thought_chain`，workflow `agent` 节点(`engine/nodes/agent.py:166-174`)与 Service API(`routes/service_api.py:285`) 落库；`GET /api/messages/<id>/thoughts` 检索；前端 `components/ui/ThoughtChain.vue` 折叠展示（`AgentChatView`/`RunPanel` 引用）。
- Dify 对比：与 Dify `message_agent_thoughts` 表 + 思考链 UI **语义一致**（position/observation 逐步）。

**2.3 agent_v2 策略协议对齐 — ✅**
- 实现：`engine/agent_strategies.py` 进程内注册表 `@register_strategy`/`get_strategy`/`list_strategies`；内置 **react / function_call / plan_execute** 三策略，统一签名 `run(messages, tools, context, llm_config, on_thought)`，返回 `{output, tool_calls, thought_chain, tokens, iterations}`；`ReActStrategy._parse_response` 兼容 JSON 与文本 `Action/Action Input/Final Answer` 双格式；`ConfigRevisionManager` 落 `agent_config_revisions`；`agent` 节点(`nodes/agent.py:156 execute_agent_strategy`)按 `config.strategy` 分发。
- Dify 对比：Dify 1.17 策略为**插件型 provider**（`core/agent/strategy/base.py BaseAgentStrategy.invoke(...)→Generator[AgentInvokeMessage]` + `strategy/plugin.py`，内置 react/fc/cot 由策略插件提供）。熵舟为**进程内注册表 + on_thought 事件流**的等价精简实现；思考落库表一致。属已接受架构差异（进程内 vs 插件）。

**2.4 知识库元数据系统 — ✅**
- 实现：表 `dataset_metadatas`(字段) + `dataset_metadata_bindings`(分段绑定)；`engine/metadata_engine.py` 提供字段 CRUD、`bind/unbind_segment_metadata`、`get_segment_metadata`、`_sync_segment_metadata_json`（冗余同步到 `dify_document_segments.metadata`）、`build_metadata_filter_sql`/`filter_segments_by_metadata`（eq/ne/contains/gt/lt）；REST `routes/knowledge.py:1766-1851` 全套端点；召回过滤应用于 `/api/knowledge/recall-test`(1611) 与 `knowledge-retrieval` 节点(`engine/nodes/knowledge_retrieval.py:111`)；前端 `KnowledgeDetailView.vue` 元数据面板。
- **措辞更正**：检索过滤实为**关系型预/后过滤候选分段**（先召回、按绑定表 SQL 过滤 `segment_id`），**并非**原计划所述"下推到 Qdrant payload filter"；效果等价于 Dify 的元数据过滤。
- ⚠️ 环境前置：`e2e_metadata_check`（HTTP）需**认证令牌**（knowledge 蓝图鉴权，未带 token 返回 401）；本轮以 `e2e_phase2_agent_rag_check::metadata_crud` 直调 engine 确定性覆盖。

### 阶段 3（P1 收尾 + P2）：检索增强 + 工具生态 + 触发器完善（约 8 天） ✅ 已实现（2026-09-22 复核）

> **前置：embedding 模型配置（本轮完成）**：录入通义千问 DashScope `text-embedding-v3`（OpenAI 兼容端点，**dim=1024**）为默认 embedding 模型，打通长期记忆向量化端到端链路（`add_memory`→Celery `embedding` 队列 `embed_agent_memory`→`get_embedding` 1024→双写 MySQL(`memories.embedding`)+Qdrant(`agent_memory__{id}`)→`search_memories`），`e2e_agent_memory_check` **11/11 PASS**（真实 HTTP + 真 embedding）。
> **本会话修复的 4 处真实缺陷**（非仅测试适配）：
> - **Windows Celery 致命坑**：prefork/billiard spawn 下 `fast_trace_task` 抛 `ValueError: not enough values to unpack (expected 3, got 0)`，导致**所有入队任务直接失败**（记忆向量化不落库真因）→ `tasks/celery_app.py` 在 `os.name=='nt'` 强制 `worker_pool='solo'`+`worker_concurrency=1`（独立 `conf.update` 调用，避免与主配置键冲突）。
> - **Qdrant 维度漂移**：旧集合声明 384（本地降级向量），切远程 1024 后 upsert 报 400 → `vector_store.py` 新增 `get_declared_dim`，`_create_collection_qdrant` 维度不符时重建集合；`scripts/reindex_vectors.py` 幂等迁移历史数据。
> - **知识库向量全堆 `knowledge_default`**：`generate_missing_embeddings` 全量扫描传 `dataset_id=None` → 改为按 `row['dataset_id']` 路由到 `knowledge_{dataset_id}`。
> - **记忆向量 point ID 幂等**：`agent_memory.py` 采用 `uuid5(_POINT_NAMESPACE, 'memory:{id}')` 稳定 point ID + `_ensure_vector_dim` 维度漂移检测。
> **阶段3 七项均已实现并复核通过**（前后端）；3.6 测试修复 graphon 拆分遗留的 `_node_human_input` 悬空导入（`engine.workflow_runner`→`engine.nodes.human_input`）并接入无口令鉴权 helper；3.1 新增确定性测试 `e2e_retriever_resources_check`。历史环境说明：`qdrant-client>=1.19.0` 已入 `requirements.txt`。

| 任务 | 要点 | 工作量 | 状态 |
|------|------|--------|------|
| 3.1 引用追踪 | knowledge-retrieval 输出增加 `retriever_resources`（segment_id/doc_name/score/content），消息表落库，AgentChatView 引用气泡 | 1.5 天 | ✅ `e2e_retriever_resources_check` 18/18 |
| 3.2 关键词表 | jieba 分词建 `dataset_keyword_tables`，混合检索（向量+关键词加权） | 1.5 天 | ✅ `e2e_keyword_check` 28/28 |
| 3.3 外部知识 API | `external_knowledge_apis` 表 + 检索代理：外部 API 结果并入召回 | 1 天 | ✅ `e2e_external_knowledge_check` 32/32 |
| 3.4 工具 OAuth | `tool_oauth_system/tenant_clients` 表 + OAuth 授权流程（回调端点 + token 刷新） | 1.5 天 | ✅ `e2e_tool_oauth_check` 49/49 |
| 3.5 工具标签/版本 | `tool_label_bindings` + 工具版本字段 + ToolsView 标签筛选 | 1 天 | ✅ `e2e_tool_label_check` 36/36 |
| 3.6 Human Input 邮件投递 | `human_input_form_deliveries` 表 + SMTP 配置（参考 Dify mail_human_input_delivery_task） | 1 天 | ✅ `e2e_human_input_delivery_check` 38/38 |
| 3.7 MCP 服务端 | `/mcp/v1` 端点（SSE），暴露熵舟工具为 MCP Server | 1.5 天 | ✅ `e2e_mcp_server_check` 28/28 |

### 阶段 4（P2）：模型管理 + 前端工程化（约 7 天） ✅ 已实现（2026-09-22 复核）

> **复核结论**：六项前后端**均已落地**（代码远早于本文档记录）。本轮据实核验并补充确定性功能测试。
> **落点总览**：4.1 `routes/models.py:528` `POST /api/model-configs/<id>/test` + `:580` body 测试（llm/embedding/tts/stt，返回 `elapsed_ms`）· 4.2 `utils/llm.py` `get_model_configs_for_lb`/`select_model_config_lb`/`call_llm_with_lb`（内存轮询索引 `_lb_round_robin_index` + 失败自动切换）· 4.3 `routes/service_api.py:864/936` audio 双端点 · 4.4 `routes/workflows.py:757` `/versions/diff` + `_diff_workflow_graphs`（纯函数）+ 前端 `components/workflow/VersionPanel.vue` · 4.5 `front/src/components/ui/`（20 组件 + `index.ts`）· 4.6 `front/src/styles/style.css` 断点。
> **措辞更正**：4.2 未另建 `load_balancing_model_configs` 表也无权重配置，而是对同 provider 的多行 `model_configs` 做 **纯轮询（Round-Robin）+ 失败 failover**；效果等价于多 Key 负载均衡，但无加权路由（如需权重可后续扩展）。
> **验证资产**：新增 `tests/e2e_phase4_model_lb_diff_check.py`（确定性 **11/11 PASS**：造 2 行 model_configs 验真实轮询 A→B→A→B + 隔离/空配置边界；造 2 个 workflow_versions 验节点/边增删改计数、变更键、同版本零差异、反向对比、404/400）；复用 `e2e_phase4_check`(9) · `e2e_p1_fixes_check`(17) · `e2e_audio_api_check`(19，真实音频网络调用较慢)。前端 `vue-tsc --noEmit && vite build` 退出码 **0**。

| 任务 | 要点 | 工作量 | 状态 |
|------|------|--------|------|
| 4.1 模型测试端点 | `POST /api/model-configs/<id>/test`：发一条短消息验证连通，返回延迟 | 0.5 天 | ✅ `e2e_phase4_check` 9/9 |
| 4.2 模型负载均衡 | 多 Key 轮询 + 失败自动切换（实现于 `utils/llm.py`，对 `model_configs` 多行） | 1.5 天 | ✅ `e2e_p1_fixes_check` 17/17 + `model_lb_diff` LB 4/4 |
| 4.3 语音 Service API | `/v1/audio-to-text` / `/v1/text-to-audio` 复用 audio 内置工具 | 1 天 | ✅ `e2e_audio_api_check` 19/19 |
| 4.4 工作流版本 Diff | 前端 graph JSON diff 视图（节点/边增删改对比） | 1.5 天 | ✅ 后端 diff API + 前端 VersionPanel + `model_lb_diff` 7/7 |
| 4.5 组件库扩展 | 抽取通用组件（Dialog/Select/Tabs/Toast 统一） | 2 天 | ✅ 20 组件 + `vite build` OK |
| 4.6 响应式适配 | 工作台 1280px 以下断点适配 | 0.5 天 | ✅ style.css 多断点 + `vite build` OK |

### 阶段 5（P3）：平台化（约 6 天）— ✅ 已全部落地并复核（v5.6）

| 任务 | 要点 | 工作量 | 状态 |
|------|------|--------|------|
| 5.1 资源级 RBAC | app/dataset 级权限矩阵 + API 装饰器 | 2 天 | ✅ `_RESOURCE_REGISTRY`(app/workflow/dataset/tool) + `check_resource_permission` + `resource_permission_required`/`dataset_permission_required`；`e2e_phase5_rbac_sso_check` 权限矩阵 8 项全过 |
| 5.2 SSO（OAuth2 登录） | OAuth 登录框架 + Google/GitHub | 2 天 | ✅ `utils/oauth_user.py` 全流程 + `/api/oauth/{providers,authorize,callback}`；★修复用户配给引用不存在列（`password_hash/role/oauth_info/avatar`）缺陷 + 白空 email 守卫；配置存 `system_settings.oauth_providers`（非独立表）；SSO 配给测试 6 项全过 |
| 5.3 workflow_runner 拆分 | 按 graphon 模式拆 `engine/nodes/` + NodeFactory 注入 | 2 天 | ✅ 已完成（runner 1067 行、`engine/nodes/` 21 文件、NodeFactory 40 注册） |
| 5.4 CI/CD | 初始化 git 仓库 + GitHub Actions（lint/test/build） | 1 天 | ✅ `.gitignore`（402 文件白名单/零密钥）+ `.github/workflows/ci.yml`（后端 compileall + 前端 build）；本地双闸门验证绿；已 `git init -b main` + 连接 origin |

**里程碑排期（单人，全量约 36 天）**：
```
第 1 周:  阶段 0 + 阶段 1（触发器/节点/Service API）→ 工作流引擎 88%→95%
第 2 周:  阶段 2（Agent 记忆/思考链/策略 + 元数据）→ Agent 80%→92%
第 3 周:  阶段 3（检索增强 + 工具生态）→ RAG 82%→92%
第 4-5 周: 阶段 4 + 阶段 5（模型/前端/RBAC/SSO）
```

---

## 六、关键风险与缓解（实测更新）

| 风险 | 影响 | 概率 | 缓解 |
|------|------|------|------|
| ~~workflow_runner.py 单体膨胀~~ | 已缓解 | — | 2026-09-22 前已按 graphon 模式拆为 `node_factory.py`+`engine/nodes/`（runner 1328 行，旧单体存 workflow_runner_orig.py）；拆分遗留悬空懒导入已在阶段 1 回归中全部修复 |
| 定时触发 Beat 一分钟粒度 | 中 | 低 | 满足绝大多数场景；文档明示 |
| MySQL 90 表与 Dify 143 表命名差异扩大 | 中 | 中 | 新表沿用 Dify 原名（如 dataset_metadatas），保迁移兼容 |
| 沙箱/SSRF 非进程隔离 | 高 | 低 | 已有代码层防护；生产建议前置 WAF/代理（已知折衷） |
| dify-1.17.0 参考目录误删 | 中 | 低 | 本文件已全量记录实测数据；目录保留作对照 |
| 根目录 dify-gap-analysis-v2.md 与 docs/ 版本分叉 | 中 | 已发生 | 本版已同步两处；后续以 docs/ 为唯一源 |

---

## 七、更新日志

| 日期 | 版本 | 更新内容 |
|------|------|---------|
| 2026-09-22 | v5.9 | **V1.0 发布定版（P1 功能对齐/健壮性 + P2 工程整洁收尾）**：①**P2-11 健壮性**——`backend/utils/auth.py`（`_get_user_by_id`/`revoke_token`/`is_token_revoked`/`user_has_permission`/`check_dataset_permission`/`check_app_access`/`check_resource_permission`/`check_user_permission` 共 8 处）与 `backend/engine/metadata_engine.py`（字段 CRUD/绑定/检索过滤 共 11 处）的裸 `except Exception: return False/None/pass` 静默吞异常分支，均补 `logger.exception/warning` 且**保持返回值不变**；两文件各自新增 `from utils.logger import get_logger`+`logger = get_logger(__name__)`（logger.py 仅依赖标准库，无循环导入）；保留合理兑底（JWT 密钥文件 IO、Redis 不可用回退内存黑名单）。②**P2-9 工程整洁**——`git mv` 将 `backend/diagnose.py`/`reset_password.py`/`seed_plugins.py` 归档至 `scripts/maintenance/`（均无应用 import、不参与启动；`migrate_from_dify.py` 因被 `tests/test_migration.py` 导入保留），修正 `sys.path` bootstrap 为 `../../backend` 并更新归档 README。③**P1-4 i18n**——核验确认 `front/src/locales/index.ts` 为功能完整的双语模块（非空转），**保留不删**，同步修正 §3.7/§4.2。④**P1-5 Service API**——核验 info/parameters/messages+feedbacks/conversations(列表/删/重命名)/meta/site/audio 均已实现（仅非标准 /v1/apps 未做），刷新 §3.5 表（多行 ❌→✅）与 §4.2 评分 68→92%。⑤**P1-6**——多租户隔离/SAML-LDAP 明确延后 post-V1.0。⑥**P1-7 部署**——★修复 `scripts/deploy-ubuntu.sh` 数据库初始化步骤引用不存在的 `models.tables.init_db()`（`ImportError`）→ 改为遍历 `models.tables` 全部 `*_TABLE_SQL` 逐一 `CREATE TABLE IF NOT EXISTS`，`bash -n` 校验通过。回归：`compileall` 退出 0 + 两模块 fresh import 通过 + `e2e_metadata_check` **15/15** + `e2e_phase5_rbac_sso_check` **14/14** + `e2e_register_control_check` **8/8** + 前端 `vue-tsc && vite build` **✓ built**。⚠ 非 debug 下 auth.py/metadata_engine.py 变更需重启后端才对 HTTP 生效（行为不变，仅新增日志）。 |
| 2026-09-22 | v5.8 | **P0 注册管控落地（V1.0 安全）**：修复“是否开放注册”只有前端 UI 与写库、后端 `/api/register` 从不读取的“设了不用”缺陷。①后端 `routes/auth.py` 新增 `_get_register_policy(cur)`（单一真相源，读 `system_settings`）：`allow_register` 为 `0/false/off` 时注册直接 **403**；新增 `register_invite_code`，非空则注册必须携带匹配邀请码；②新增公开 `GET /api/register-config`（返回 `allow_register`/`require_invite_code`，**不回传邀请码明文**）；③前端 `RegisterView.vue` 进页拉配置，关闭时隐藏表单提示“已关闭”、需邀请码时展示输入框并随请求提交；`SystemSettingsView.vue` 新增邀请码设置项（留空=不启用）；④新增确定性回归 `backend/tests/e2e_register_control_check.py`（**8/8 PASS**：默认开放/开关解析/邀请码携带/空白归不要求/关闭优先于邀请码/相等判定）。回归：`compileall` 退出 0、`e2e_phase5_rbac_sso_check` 14/14、前端 `vue-tsc && vite build` ✓。注：非 debug 重载下需重启后端才能对 HTTP 生效 |
| 2026-09-22 | v5.7 | **V1.0 发布前代码清理与安全加固**：①死代码/临时文件——删 `backend/engine/workflow_runner_orig.py`（4388 行旧单体，全库 0 引用）、`tmp_check_dsl.py`/`_tmp_check_dsl.py`（临时诊断）、`backend/=5.0.0`（pip 误产物）；②`git rm` 前端遗留原型 `front/legacy/`（42 个未被构建引用的 HTML）并同步修正 `README.md` 引用；③一次性迁移/清理脚本归档至 `scripts/maintenance/`（`migrate_users`/`migrate_merge_tables`/`cleanup_users(.py/.sql)`；`migrate_from_dify.py` 因被 `tests/test_migration.py` 导入而保留），修复 `sys.path` bootstrap 并补归档 README；★安全加固——清除仓库内明文口令：个人账号口令（reset_password/diagnose/cleanup_users(.py/.sql)/test_deep_research_assistant）与 DB 默认口令（config/db_backup）全改环境变量/命令行注入；`.env.example` 的 DB 密码置空；⑤`.gitignore` 增补 `=*`、`tmp_*.py`、`_tmp_*.py`、`*_orig.py` 防复发；⑥前端 `MultiAgentEditView.vue` 移除 3 处调试 `console.log`。回归：后端 `compileall` 退出 0、前端 `vue-tsc && vite build` 退出 0、`e2e_phase5_rbac_sso_check` 14/14 PASS；源码 0 TODO/FIXME、无 501 占位端点 |
| 2026-09-22 | v5.6 | **阶段 5（P3 平台化）实现与回归复核**：5.1 资源级 RBAC（`_RESOURCE_REGISTRY` 覆盖 app/workflow/dataset/tool、owner/admin 全权、published 可读、权限级别 read<write<admin，已随阶段 1 校正至真实 `created_by` schema）；5.2 SSO OAuth2 登录（`utils/oauth_user.py` Google/GitHub：authorize→callback→token→userinfo→配给→JWT + `/api/oauth/{providers,authorize,callback}`）——★修复 `find_or_create_oauth_user` 引用 `dify_accounts` 不存在列（`password_hash/role/oauth_info/avatar`）致 INSERT 抛错被裸 except 吞成 None、SSO 无法配给用户的真实缺陷（改按 `password/password_salt` + `roles`/`user_roles` + 建工作区，镜像注册流程）并补白空 email 守卫；措辞更正：SSO 配置存 `system_settings.oauth_providers` JSON，未建独立 `oauth_provider_apps` 表；5.3 workflow_runner 拆分已完成；5.4 CI/CD 落地：`.gitignore`（源码 402 文件入库、零密钥/依赖/二进制/dify 参考目录）、`.github/workflows/ci.yml`（后端 `compileall` 语法闸门 + 前端 `vue-tsc && vite build`，完整 e2e 因需 MySQL/Redis/模型密钥保留本地/dispatch）、`git init -b main` 并连接 origin `github.com/yutaiyin139/shangzhou`；新增确定性回归 `backend/tests/e2e_phase5_rbac_sso_check.py`（**14/14 PASS**）；后端 `compileall` 全绿、`ci.yml` YAML 校验通过、`oauth_user.py` 编译通过；§3.9 部署运维评分 85→92%、§CI/CD/SSO 状态表更正为已落地 |
| 2026-09-22 | v5.5 | **阶段 4（P2 模型管理 + 前端工程化）实现与回归复核**：确认 4.1 模型连接测试端点（`routes/models.py` by-id + body，返回 `elapsed_ms`，支持 llm/embedding/tts/stt）、4.2 模型负载均衡（`utils/llm.py` 多 Key 轮询 + 失败 failover）、4.3 语音 Service API（`/v1/audio-to-text`、`/v1/text-to-audio`）、4.4 工作流版本 Diff（`/versions/diff` + `_diff_workflow_graphs` + 前端 `VersionPanel.vue` 对比视图）、4.5 组件库（**20** 个统一 UI 组件 + `index.ts`）、4.6 响应式（`style.css` 1400/1280/1024/768/480px + 触控断点）六项前后端**均已落地**；新增确定性回归 `backend/tests/e2e_phase4_model_lb_diff_check.py`（**11/11 PASS**：真实多 Key 轮询循环 A→B→A→B + 结构化 diff 精确断言）；`e2e_phase4_check` 9/9 · `e2e_p1_fixes_check` 17/17 · `e2e_audio_api_check` 19/19 全绿；前端 `vue-tsc --noEmit && vite build` 退出码 0；措辞更正：4.2 未建 `load_balancing_model_configs` 表/无权重，为 `model_configs` 多行纯轮询+failover；§3.5/3.7 对比表与 §4.2 评分据实上调（Service API 60→68%、前端 90→95%） |
| 2026-09-22 | v5.4 | **阶段 3（P1 收尾 + P2）实现与回归复核 + embedding 模型配置**：录入通义千问 DashScope `text-embedding-v3`（dim=1024）为默认 embedding 模型，打通长期记忆向量化端到端（`e2e_agent_memory_check` **11/11 PASS**，真实 HTTP + 真 embedding）；阶段3 七项前后端**均已实现并复核通过**——3.1 引用追踪（新增确定性 `e2e_retriever_resources_check` **18/18**）/3.2 关键词表 **28/28**/3.3 外部知识 API **32/32**/3.4 工具 OAuth **49/49**/3.5 工具标签 **36/36**/3.6 Human Input 邮件投递 **38/38**/3.7 MCP 服务端 **28/28**；★本会话修复 4 处真实运行缺陷：Windows 下 Celery prefork `fast_trace_task` 崩溃致所有入队任务失败（`celery_app.py` 强制 solo 池）、Qdrant 集合维度漂移 384→1024（`vector_store.get_declared_dim` + 不符重建 + `scripts/reindex_vectors.py` 迁移）、知识库向量误全堆 `knowledge_default`（`generate_missing_embeddings` 按 `row.dataset_id` 路由）、记忆向量 point ID 幂等（`uuid5`）；3.6 测试修复 graphon 拆分遗留 `_node_human_input` 悬空导入 + 接入无口令 `e2e_auth_helper`（规避登录锁定）；`qdrant-client>=1.19.0` 入 requirements；§3.1/3.2/3.4 对比表与 §4.2 评分据实上调（RAG 88→94%、工具生态 75→90%） |
| 2026-09-22 | v5.3 | **阶段 2（P1）实现与回归复核**：确认长期记忆向量化（`agent_memory.py`，Celery `embedding` 队列双写 MySQL+Qdrant + `chat.py` 注入/回写）、思考链记录（`thought_chain.py`+`message_agent_thoughts`+`ThoughtChain.vue`，agent 节点/Service API 落库）、策略协议（`agent_strategies.py` 注册表 react/function_call/plan_execute + on_thought + `agent_config_revisions`）、知识库元数据系统（`metadata_engine.py`+`dataset_metadatas`/`_bindings`，字段 CRUD/绑定/SQL 过滤/级联）四项前后端**均已落地**；新增确定性回归 `backend/tests/e2e_phase2_agent_rag_check.py`（**8/8 PASS**，桩化 embedding）+ 思考链 e2e **6/6 PASS**；★修复记忆检索在 Qdrant 不可用（当前部署未装 `qdrant_client`→MySQL 回退）时因 `_upsert_mysql` 丢失 `payload.memory_id` 而恒为空的健壮性缺陷（`search_memories` 新增 `_search_memories_local` 余弦兜底）；措辞更正：元数据检索过滤为关系型预/后过滤而非 Qdrant payload 下推；环境前置登记：实时向量检索需先配 embedding 模型、knowledge 接口需认证令牌；§3.2/3.3 对比表与 §4.2 评分据实上调（RAG 82→88%、Agent 80→92%） |
| 2026-09-22 | v5.2 | **阶段 1（P0）实现与回归复核**：确认定时触发（trigger_engine + croniter + beat 派发）、datasource、knowledge-index、Service API 四项前后端均已落地（NodeFactory 注册 29 节点）；新增确定性验收脚本 `backend/tests/e2e_phase1_triggers_nodes_check.py`（**8 PASS**）；触发器订阅 API **16/16**、Service API **14/14**（★ 补齐 `/v1/parameters` 缺失的 `annotation_reply`）；修复 workflow_runner 拆分遗留的 agent 节点悬空懒导入 + provider 误匹配（`_find_model_config` langgenius 前缀剥离），全节点回归复跑 **25 PASS / 0 FAIL / 2 SKIP**；节点架构描述据实更新（25→29、分发器→NodeFactory） |
| 2026-09-22 | v5.1 | **阶段 0 清理完成 + 实测复核**：确认遗留备份表 `users_backup_20260903_150012` 无代码引用且已从库中删除（无需 DROP）；前端 `front/legacy/`（39 个静态原型）未被构建引用（保留），`npm run build` 退出码 0（550 模块 / ✓ built）；szagent 实测业务表由 57 增至 **90 张**（阶段 1-4 已落地建表），表覆盖率 39%→63% |
| 2026-09-08 | v5.0 | **全量实测刷新**：docker ps 实测 15 容器；psql 实测 144 表；grep 实测 846 端点；graphon 引擎架构发现（1.17 重大变更）；熵舟实测 326 端点/57 表/25 节点/42 视图；确认 v15 后新增 share/backup/cache 路由、pause/resume API、10 张新表、Explore/Share 视图；输出五阶段 36 天实施计划 |
| 2026-09-04 | v4.0 | 独立运行评估 + 差距分析第十五版 |
| 2026-09-04 | v3.4 | 工具/插件生态 + API 覆盖完成 |
| 2026-09-04 | v3.3 | Agent 增强 + 工作流高级功能完成 |
| 2026-09-03 | v3.0 | P2 核心功能补齐完成 |
| 2026-09-03 | v2.8 | P0 安全加固完成 |
| 2026-09-01 | v1.0 | 初版发布 |

---

*文档结束 — 本版所有数据均来自 2026-09-08 对运行中 Dify 1.17.0（15 容器）与熵舟（Flask :5000 / Vite :5173 运行中）的实机探测，非转抄。*
