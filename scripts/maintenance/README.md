# scripts/maintenance —— 运维体检 / 数据迁移脚本

本目录存放**不参与后端启动、不被应用 import、也不纳入 CI 构建**的运维脚本，
与运行时的 `backend/` 业务代码隔离，仅按需手动执行。

## 账号与归属（users 表已废弃删除，账号唯一真相源 = dify_accounts）

| 脚本 | 用途 | 状态 |
|------|------|------|
| `cleanup_test_accounts.py` | 清理 e2e/探针留下的垃圾账号（测试命名模式、非法邮箱、IDOR-PROBE 哨兵）+ 孤立租户，可把无主应用的 created_by 回填给主账号 | 常驻，默认 dry-run |
| `check_agent_ownership.py` | 只读体检：agents.owner 列类型/分布/可反查性、账号可见性预览 | 常驻 |
| `migrate_agent_owner.py` | agents.owner INT(旧 users.id) → VARCHAR(36)(dify_accounts.id) 一次性回填 | 已执行，留作回退手册 |
| `verify_ownership_enforcement.py` | 对运行中的后端打真实 HTTP，断言越权被拒 / 本人可见（T8 会写探针手机号，发起方与拥有者两侧都先备份、结束无条件还原） | 常驻（改身份链路后必跑） |
| `check_admin_surface_exposure.py` | 用普通用户的真实令牌只读扫“疑似管理面 GET”，列出仍能读到数据的人人可达接口（集中闸门只管登录，不管管理员） | 常驻，改管理面接口后跑 |
| `check_routes_5xx.py` | 遍历 `app.url_map` 的全部 GET 路由逐条真实调用，只报 5xx（“从未被调用过就一直不报错”的那类死引用/属性不存在/pymysql `%` 未转义） | 常驻，改路由后跑；默认不打写接口 |
| `check_password_hash.py` | 存量密码哈希形状体检（argon2 原始 32 字节 / PBKDF2 hex 64 字节） | 常驻 |
| `check_db_charset.py` | 库/表/列字符集体检（emoji 被截成 '?' 的来源） | 常驻 |
| `check_env_parity.py` | `.env` 与 `.env.example` 键位差异体检 | 常驻 |
| `diagnose.py` | 登录 500 问题诊断（逐一检查 DB/表/账号/角色/密码校验/JWT） | 按需手动执行 |
| `reset_password.py` | 重置指定账号密码（口令走命令行参数或环境变量） | 按需手动执行 |
| `seed_plugins.py` | 插件市场种子数据（首次无数据时插入 8 个示例插件） | 按需手动执行 |

> **已删除的一次性迁移脚本**：`migrate_users.py`、`cleanup_users.py` / `cleanup_users.sql`、
> `migrate_merge_tables.py`。它们的共同点是读写旧 `users` 表（或只服务于“合并到
> dify_accounts”那一次动作）：表已 DROP，脚本再跑只会报错，留着反而误导“好像还
> 有两套账号体系”。需要从 git 历史可取回（`git log --diff-filter=D -- scripts/maintenance`）。
> `deploy-ubuntu.sh` 会在新部署时主动 `DROP TABLE IF EXISTS users`，`models/tables.py`
> 里也刻意不再定义 users 建表语句 —— 不要把这三样加回来。

> 用户/角色管理面的管理员边界（`/api/users` 读写、`/api/roles*` 与
> `/api/roles/<id>/permissions` 的写）另由 `backend/tests/test_account_identity_single_source.py`
> 的 `TestPlatformAdminSurface` 把守（test_client 直接打，不需跑着后端）。

> 注：`migrate_from_dify.py` 仍位于 `backend/`，因为被 `backend/tests/test_migration.py` 导入（单元测试依赖），不可移动。

## 运行方式
这些脚本依赖 `backend/` 下的 `config.py` / `utils/`，且数据库凭据通过环境变量注入。执行前：

```bash
# 在项目根，先加载 .env（或显式设置 DB_* 环境变量）
cd backend
set PYTHONIOENCODING=utf-8            # Windows 控制台缺省 GBK，中文输出会直接报 UnicodeEncodeError
python ../scripts/maintenance/cleanup_test_accounts.py --dry-run   # 先预览（缺省就是 dry-run）
python ../scripts/maintenance/cleanup_test_accounts.py --apply      # 正式执行
```

带 `--dry-run` / `--apply` 的脚本缺省都是**只看不改**，**务必先 dry-run 确认再执行**。

## 安全约定
- ❌ 严禁在脚本中硬编码数据库密码、账号口令、API Key。
- ✅ 一律通过环境变量读取：`DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME`，
  以及各脚本专用变量（如 `RESET_USERNAME` / `RESET_PASSWORD`、`DIAG_PASSWORD`、
  `SHANGZHOU_TEST_USERNAME` / `SHANGZHOU_TEST_PASSWORD`）。
- ✅ 删账号/改归属这类写库脚本必须有护栏（名下无资源、主账号永不删、单事务可回滚），
  并且把“为什么保留”一并打出来，否则运维无法判断 dry-run 输出对不对。
