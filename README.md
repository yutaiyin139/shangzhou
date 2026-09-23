# 熵舟·智能体工作台（V1.0）

前后端分离架构：**Vue 3 + Vite + Pinia + TypeScript** 前端（`front/`）与 **Flask + Flask-SocketIO + Celery** 后端（`backend/`）；数据持久化使用 **MySQL**（库名 `szagent`，须 `utf8mb4`），**Redis** 作 Celery broker/缓存，**Qdrant** 为可选向量库（缺失自动回退 MySQL 余弦检索）。

## 目录结构

```
shangzhou/
├── front/                      # 前端（Vue3 + Vite + Pinia + TypeScript）
│   ├── package.json            # 前端依赖清单
│   ├── vite.config.ts          # Vite 配置（dev 端口 5173，/api 代理到后端 5000）
│   ├── index.html              # 应用入口 HTML
│   ├── src/
│   │   ├── main.ts             # 应用入口
│   │   ├── App.vue             # 根组件（router-view）
│   │   ├── router/index.ts     # 路由表（hash 模式，48 个视图）
│   │   ├── locales/            # 中英文双语 i18n（t()/setLocale/locale）
│   │   ├── components/         # 组件（AppShell + ui/ 统一组件库 + workflow/ 等）
│   │   ├── stores/  api/  utils/  styles/
│   │   └── views/              # 48 个页面组件（Login/Home/WorkflowStudio/Knowledge/...）
│   └── dist/                   # 生产构建产物（由 Nginx 托管）
├── backend/                    # 后端（Flask）
│   ├── app.py                  # Flask 应用入口（注册 CORS / 路由 / SocketIO）
│   ├── config.py               # DB/Redis/密钥配置（自动加载项目根 .env）
│   ├── routes/                 # 业务路由模块（34 文件 / 326 端点）
│   ├── engine/                 # 工作流引擎（node_factory + nodes/ 节点包）
│   ├── models/                 # 数据表结构、内置工具/技能/数据源定义
│   ├── tasks/                  # Celery 任务（workflow/embedding/scheduled/backup）
│   ├── utils/                  # 工具（auth/encryption/llm/vector_store/login_lockout/...）
│   └── requirements.txt        # 后端依赖清单
├── scripts/
│   ├── deploy-ubuntu.sh            # Ubuntu 目标机交互式一键部署
│   ├── deploy-ubuntu-online.sh     # Ubuntu 服务端一键部署脚本（在线部署用）
│   ├── deploy_ubuntu_online.py     # 跨网 SSH 部署驱动（从 Windows 编排）
│   ├── szagent-ctl.sh              # Ubuntu 统一服务控制（start/stop/restart/status）
│   ├── init_db.py / db_backup.py   # 建库 / 备份
│   ├── test_deep_research_assistant.py  # 工作流端到端冒烟
│   └── maintenance/                # 一次性运维脚本（reset_password/diagnose/迁移脚本）
├── docs/                       # 文档（生产环境部署手册 / Dify 差距分析 / 工作流对比）
├── Redis-8.10.1/               # 本地 Windows Redis（含 start.bat）
├── qdrant/                     # 本地 Windows Qdrant
├── .env                        # 运行配置（DB/Redis/JWT/ENCRYPTION_KEY；勿入库）
└── start-*.bat / stop-*.bat / *-services.ps1   # Windows 一键启停脚本
```

## 环境要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Node.js + npm | 18+ | 前端编译/运行 |
| Python | 3.10+（3.12/3.13 推荐） | 后端运行 |
| MySQL | 8.0（utf8mb4） | 库名 `szagent` |
| Redis | 7.x | Celery broker + 缓存 |
| Qdrant | 可选 | 向量库；缺失回退 MySQL 检索 |

## 配置（`.env`）

数据库等配置**不再硬编码**：`backend/config.py` 启动时自动加载项目根 `.env`（systemd 亦通过 `EnvironmentFile` 注入）。关键变量：`DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME`、`REDIS_HOST` / `REDIS_PORT` / `REDIS_PASSWORD`、`JWT_SECRET`、`ENCRYPTION_KEY`（加密模型 API Key，启用后不可更换）。可从 `.env.example` 复制起步。

---

## Windows 本地开发 / 联调

### 首次安装依赖

```bash
cd backend && pip install -r requirements.txt
cd front   && npm install
```

### 一键启动 / 停止

| 目的 | 命令 |
|------|------|
| 启动全部（Redis + Qdrant + 后端 + 前端 + Celery） | `start-all.bat` |
| 停止全部 | `stop-all.bat` |
| 仅启动后端 / 前端 / Worker | `start-backend.bat` / `start-front.bat` / `start-worker.bat` |
| **仅停止前端（Vite :5173）** | `stop-front.bat`（传 `/auto` 免停顿） |
| **仅停止后端（Flask :5000）** | `stop-backend.bat`（传 `/auto` 免停顿） |
| 端口轮询式启停（推荐脚本化） | `start-services.ps1` / `stop-services.ps1` |
| 健康检查 | `check-health.bat`（或 `check-health.bat --json`） |

访问 `http://localhost:5173`。前端 `/api` 由 Vite 代理到后端 5000，**须先启动后端**。

### 命令行手动启动

```bash
# 终端 1：后端
cd backend && python app.py            # http://localhost:5000
# 终端 2：前端
cd front && npm run dev                # http://localhost:5173
# 生产构建与预览
cd front && npm run build && npm run preview   # 产物输出 front/dist/
```

---

## 生产环境部署（Ubuntu）

> 完整步骤见 **`docs/生产环境部署手册-V1.0.md`**。此处仅给命令入口。

**方式 A · 目标机交互式**：`sudo bash scripts/deploy-ubuntu.sh`

**方式 A-2 · 跨网 SSH 在线一键（实测 V1.0）**：从本机 Windows 上传后端 + 已构建 `dist` 并在目标机执行服务端脚本：

```powershell
$env:SZ_HOST="172.28.186.196"; $env:SZ_USER="yuty"; $env:SZ_PASS="****"
$env:SZ_APP_DIR="/home/yuty/shangzhou"
python scripts/deploy_ubuntu_online.py            # 上传 + 部署
```

### Ubuntu 服务统一控制（`scripts/szagent-ctl.sh`）

分组：`front`=nginx；`backend`=szagent-backend/worker/beat；`infra`=redis-server/qdrant（qdrant 缺失自动跳过）；`all`=infra+backend+front。

```bash
sudo bash scripts/szagent-ctl.sh start all      # 一键启动所有服务
sudo bash scripts/szagent-ctl.sh stop  all      # 一键停止所有服务
sudo bash scripts/szagent-ctl.sh start front    # 仅启动前端（nginx）
sudo bash scripts/szagent-ctl.sh stop  front    # 仅停止前端
sudo bash scripts/szagent-ctl.sh start backend  # 仅启动后端（gunicorn+Celery）
sudo bash scripts/szagent-ctl.sh stop  backend  # 仅停止后端
bash     scripts/szagent-ctl.sh status          # 状态总览（免 root）
```

> 启动顺序 infra→backend→front，停止取逆序；`restart`/`help` 亦支持。

---

## 登录与账号

- 后端启动时 `routes/auth.py:_init_default_admin()` 创建 `admin`/`user` 角色，并把 `admin` 角色授予账号名 **`yutaiyin`**。
- **不存在统一默认口令**（历史上"admin / 000000"的说法已过时）：登录密码取自 `szagent` 库 `dify_accounts` 表（argon2id/PBKDF2 加盐哈希）。
- 需重置密码：`python scripts/maintenance/reset_password.py`。
- 新注册账号默认 `role=user`；注册开关/邀请码在系统设置中管控（后端 `/api/register` 强制读取）。

## 验证服务是否正常

```bash
curl -s http://localhost:5000/api/health          # 期望 status=healthy
curl -I http://localhost                          # 生产经 Nginx，期望 200
```

工作流端到端冒烟（依赖后端 + Redis + Worker）：

```bash
cd backend && PYTHONIOENCODING=utf-8 python ../scripts/test_deep_research_assistant.py
#   期望 20 PASS / 0 FAIL（建库→向量化→澄清→检索→报告→发布→再问）
```

## 常见问题

| 现象 | 处理 |
|------|------|
| 双击脚本报「未找到 node / python」 | 安装对应环境并加入 PATH 后重试 |
| 端口 5173/5000 被占用 | `stop-backend.bat` / `stop-front.bat`，或 `netstat -ano \| findstr :5000` 找 PID 结束 |
| 登录提示密码错误 | 用 `scripts/maintenance/reset_password.py` 重置；勿反复试（有失败锁定） |
| `/api/health` = degraded | Redis 未运行 → Celery 不可达，启动 redis 并核对 `REDIS_PASSWORD` |
| 知识库向量化一直 PENDING | Worker 未消费全部队列，需 `-Q celery,workflow,embedding,scheduled` |
| 页面数据加载失败 | 确认后端已启动、MySQL 服务已开启 |

## 注意事项

- `.env` 含密钥，权限 600，**不入库、不入镜像**；`ENCRYPTION_KEY` 一旦启用不可更换（丢失将无法解密已存模型 API Key）。
- 生产 `FLASK_DEBUG=0`；`JWT_SECRET`/DB 密码/Redis 密码使用强随机值。
- 数据库须 `utf8mb4`：应用模板/图标含 emoji，utf8mb3 会写成 `?` 破坏 DSL YAML。
