# scripts/maintenance —— 一次性运维/迁移脚本归档

本目录存放**已完成的一次性数据迁移 / 清理脚本**，与运行时的 `backend/` 业务代码隔离，
避免与线上逻辑混淆。它们**不参与后端启动、不被应用 import、也不纳入 CI 构建**，仅按需手动执行。

| 脚本 | 用途 | 状态 |
|------|------|------|
| `migrate_users.py` | 旧 `users` → `dify_accounts` 账号数据同步/备份 | 已执行，留档 |
| `migrate_merge_tables.py` | 合并 users/dify_accounts 表结构迁移（加 phone/account_id，删 users） | 已执行，留档 |
| `cleanup_users.py` / `cleanup_users.sql` | 用户表数据清理（仅保留指定管理员） | 已执行，留档 |
| `diagnose.py` | 登录 500 问题诊断（逐一检查 DB/导入/密码校验） | 按需手动执行 |
| `reset_password.py` | 重置指定用户密码（口令走命令行参数或环境变量） | 按需手动执行 |
| `seed_plugins.py` | 插件市场种子数据（首次无数据时插入 8 个示例插件） | 按需手动执行 |

> 注：`migrate_from_dify.py` 仍位于 `backend/`，因为被 `backend/tests/test_migration.py` 导入（单元测试依赖），不可移动。

## 运行方式
这些脚本依赖 `backend/` 下的 `config.py` / `utils/`，且数据库凭据通过环境变量注入。执行前：

```bash
# 在项目根，先加载 .env（或显式设置 DB_* 环境变量）
cd backend
python ../scripts/maintenance/migrate_users.py --dry-run   # 先预览
python ../scripts/maintenance/migrate_users.py              # 正式执行
```

各脚本自带 `--dry-run` 预览模式，**务必先 dry-run 确认再执行**。

## 安全约定
- ❌ 严禁在脚本中硬编码数据库密码、账号口令、API Key。
- ✅ 一律通过环境变量读取：`DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME`，
  以及各脚本专用变量（如 `RESET_USERNAME` / `RESET_PASSWORD`、`CLEANUP_TARGET_USERNAME` / `CLEANUP_TARGET_PASSWORD`）。
