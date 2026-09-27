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

### 换机器 / 改地址：`set_ip.py`

多台机器部署时用于修正仓库里的各类地址。与早期“全文盲替换”写法不同，它**只改已登记的配置点**，
每个点带角色语义，回环与本机基础设施地址不显式点名就永不改动。

```powershell
python set_ip.py --show                                 # 先看当前地址分布（不改动任何文件）
python set_ip.py 192.168.1.20 --probe                   # 预览 + 按协议实测新地址可用性
python set_ip.py 192.168.1.20 --apply                   # 确认后写入（自动备份，可回滚）
python set_ip.py 192.168.1.20 --old-ip 10.38.3.14       # 只迁移指定旧地址
python set_ip.py 192.168.1.20 --role db,deploy --apply  # 只改数据库与部署目标
python set_ip.py 192.168.1.20 --from localhost --role backend   # 前端指向远程后端
python set_ip.py --restore                              # 回滚最近一次修改
```

角色：`db`（MySQL）/ `app`（平台对外访问地址）/ `deploy`（Ubuntu 目标机与文档示例）/
`backend`（前端 dev 代理与 e2e 基址）/ `storage`（MinIO）/ `redis`（**默认不参与**）。

要点：
- 默认只预览，`--apply` 才写盘；改前备份到 `logs/set_ip_backup/<时间戳>/`，`--restore` 一键回滚。
- 字节级按行改写，保持各文件原有行尾（`.bat` 为 CRLF、`.sh` 为 LF）与编码。
- `.env.example` 与 nginx/gunicorn/redis `bind` 等回环地址不在管辖范围内，不会被改坏。
- 新地址若属于 `vEthernet`（Hyper-V/WSL 虚拟交换机）会红色提醒：该地址重启后会被重新分配，不适合做部署地址。
- **改完必须重启服务**才生效；`backend` 角色变更后 dev 需重启 Vite、生产需重新 `npm run build`。
- `.env` 已被 gitignore（机器专属）；`scripts/`、`docs/`、`README.md` 的改动会进 git，请 review 后提交。

---

## 登录与账号

**账号的唯一真相源是 `szagent` 库的 `dify_accounts` 表**。旧 `users` 表已合并进它并删除，
`models/tables.py` 里也刻意不再定义 `users` 建表语句（否则全新部署会被 `deploy-ubuntu.sh`
按 `*_TABLE_SQL` 遍历建回一张没人读的幽灵表），已部署机器上的残留由部署脚本主动 `DROP`。
角色在 `user_roles` → `roles`（`user_roles.user_id` 直接存 `dify_accounts.id`）。

- **身份只有一个出处**：后端一律使用登录 token 里的 `user_id`（= `dify_accounts.id`，UUID），
  **客户端传来的 `?uid=` / `body.uid` / `owner_id` 全部忽略**（见 `utils/helpers.py:_safe_uid`）。
  资源归属（`agents.owner`、`dify_apps.created_by` 等）也只写这个值；拿不到登录身份时创建类接口
  直接 401，不会落库造出“对任何账号都不可见”的无主数据。
- 后端启动时 `routes/auth.py:_init_default_admin()` 创建 `admin`/`user` 角色，并把 `admin` 角色授予账号名 **`yutaiyin`**。
- **不存在统一默认口令**（历史上"admin / 000000"的说法已过时）：登录密码取自 `dify_accounts`（argon2id/PBKDF2 加盐哈希）。
  需重置密码：`python scripts/maintenance/reset_password.py`。
- **权限级别只有一个口径**：登录签发的 `role` 为 `admin` 还是 `user`，取决于该账号是否**拥有名为
  `admin` 的角色**（`utils/auth.py:get_account_role`）。不再按子串猜角色名：历史上“业务管理员”
  会被误提成 `admin`，而 `role=admin` 是跳过资源归属校验与放行管理员菜单的凭据。
  `roles` 表里遗留的中文角色（运维管理员/业务管理员/普通用户）作为“功能点分组”继续可用，
  但**不再等于管理员**；需要管理员请把账号关联到 `admin` 角色。
  - **用户/角色管理面只对管理员开放**（`utils/auth.py:platform_admin_required`，实时查库）：
    `/api/users` 的读与全部写、`/api/roles` 与 `/api/roles/<id>/permissions` 的写。
    集中闸门只保证“必须登录”，挡不住“普通用户拉到全体账号的邮箱/手机号、
    建一个 `role=admin` 的号、改任何人密码、给自己加权”这条提权路。
    这里故意不读 token 里的 `role`：access token 有效期 2h，被降权或封禁的账号
    不应还能拿旧令牌行使管理员权力。`/api/roles`、`/api/permissions` 的 **GET** 仍对登录用户开放
    （用户管理页的角色下拉要用）。
- **账号名与邮箱全库交叉唯一**：新账号名/邮箱不得与任何已有账号的 `name` 或 `email` 相同。
  因为登录是 `WHERE name = ? OR email = ?` 一个条件找两种输入，一旦“某人的邮箱恰好等于
  另一人的账号名”就会命中两行（历史上真出现过）。“忘记密码”也按邮箱寻址，因此邮箱还必须是
  合法格式。
- 新注册账号默认 `role=user`；注册开关/邀请码在系统设置中管控（后端 `/api/register` 强制读取）。
- 清理 e2e/安全探针留下的垃圾账号（含非法邮箱、`IDOR-PROBE` 哨兵）与无主应用归属：
  `python scripts/maintenance/cleanup_test_accounts.py`（缺省 dry-run，加 `--apply` 才写库）。

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

## 运维自检脚本（`scripts/maintenance/`）

这几个脚本都是只读体检（带 `--apply` 的除外），发布前跑一遍比人工对账可靠：

| 脚本 | 作用 |
|------|------|
| `check_env_parity.py` | 代码读取的环境变量 ↔ `.env.example` ↔ 部署生成的 `.env` 三方对齐；加 `--strict` 作发布门禁。**为什么必要**：`REQUIRE_LOGIN_FOR_API` 不设即为 `off`（全部接口免登录） |
| `check_agent_ownership.py` | `agents.owner` 列类型/回填/能否反查账号、每个账号可见多少自有资源、emoji 往返完整性 |
| `verify_ownership_enforcement.py` | 对运行中后端打真实 HTTP 的越权与可见性断言（登录闸门、列表、详情 403、账户 IDOR）；令牌按库中账号签发，不含口令 |
| `check_password_hash.py` | 密码哈希可验证性：PBKDF2/Argon2 两条路径往返自证 + 存量账号格式分布 |
| `check_db_charset.py` | 全库表/列字符集，找出仍会把 emoji 截成 `?` 的列（只报修复 SQL，不自行 ALTER） |
| `migrate_agent_owner.py` | `agents.owner` INT→UUID 迁移，默认 dry-run，`--apply --backup` 才写库 |
| `cleanup_test_accounts.py` | 清理 e2e 跑出的 `test_*` 账号与孤立租户；默认 dry-run，带“名下无资源 + 非主账号 + 可按名字保护”护栏 |

```bash
cd backend
python ../scripts/maintenance/check_env_parity.py --strict
python ../scripts/maintenance/check_password_hash.py
python ../scripts/maintenance/check_agent_ownership.py
python ../scripts/maintenance/check_db_charset.py
python ../scripts/maintenance/verify_ownership_enforcement.py   # 需后端已启动
```

## 发布前检查清单

1. 上面五条自检命令全部 `[OK]`/`[PASS]`，且**没有 `[SKIP]` 用例**（跳过等于没验）。
2. `cd backend && python -m pytest tests -q` 全绿；`e2e_*.py` 命名不被 pytest 收集，需改单独跑：`python tests/e2e_p2_fixes_check.py`。
3. `requirements.txt` 的版本与实跑环境一致（升级依赖要整套回归，别单包 `pip -U`）。
4. 前端 `cd front && npm run build` 通过（含 `vue-tsc` 类型检查），并确认产物内联了 `VITE_LOGIN_CAPTCHA=true`。
5. `scripts/clean-for-release.bat` 清掉 `front/dist`、`node_modules`、`qdrant/storage`（向量库数据，约 460 MB，不可随包）与一次性脚本。
6. 部署完成后按 `deploy-ubuntu.sh` 结尾的“安全步骤”收口注册（系统里没有预置账号，也没有默认密码）。

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
- 数据库须 `utf8mb4`：应用模板/图标含 emoji，utf8mb3 会写成 `?` 破坏 DSL YAML。现用
  `scripts/maintenance/check_db_charset.py` 逐列把关（表级对不代表列级对）。
