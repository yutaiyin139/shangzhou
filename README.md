# 熵舟·智能体工作台

前后端分离架构：**Vue3 + Vite** 前端（`front/`）与 **Flask** 后端（`backend/`），数据库使用 MySQL（库名 `szagent`）。

## 目录结构

```
shangzhou/
├── front/                      # 前端（Vue3 + Vite + vue-router）
│   ├── package.json            # 前端依赖清单（编译依赖）
│   ├── vite.config.js          # Vite 配置（端口 5173，/api 代理到后端 5000）
│   ├── index.html              # 应用入口 HTML
│   ├── public/                 # 静态资源（login-bg.png 等）
│   ├── src/
│   │   ├── main.js             # 应用入口
│   │   ├── App.vue             # 根组件（router-view）
│   │   ├── router/index.js     # 路由表（32 个页面）
│   │   ├── styles/style.css    # 全局样式（迁移自 assets/style.css）
│   │   ├── utils/global.js     # 公共工具（导航/图标/toast/模态框）
│   │   ├── components/AppShell.vue  # 顶栏+侧栏公共外壳
│   │   └── views/              # 32 个页面组件（LoginView/HomeView/...）
│   └── convert_html_to_vue.py  # HTML→Vue 批量转换脚本（仅维护时使用）
├── backend/                    # 后端（Flask）
│   ├── app.py                  # Flask 应用入口（注册 CORS 与路由）
│   ├── config.py               # 数据库配置（MySQL / Dify PostgreSQL）
│   ├── routes/                 # 业务路由模块（account/agents/auth/chat/...）
│   ├── models/                 # 数据表结构、内置工具/技能/数据源定义
│   ├── utils/                  # 工具函数（密码、LLM 调用、dify DB 操作等）
│   └── requirements.txt        # 后端依赖清单
├── start-front.bat             # 前端一键启动脚本
├── start-backend.bat           # 后端一键启动脚本
├── start-all.bat               # 前后端同时启动脚本
└── README.md
```

## 编译依赖

### 前端（Node.js 18+）

依赖声明在 `front/package.json`，首次使用执行：

```bash
cd front
npm install
```

| 依赖 | 版本 | 用途 |
|------|------|------|
| vue | ^3.4 | 前端框架 |
| vue-router | ^4.3 | 页面路由 |
| vite | ^5.2 | 开发服务器/构建工具 |
| @vitejs/plugin-vue | ^5.0 | Vue 单文件组件编译插件 |

### 后端（Python 3.x）

依赖声明在 `backend/requirements.txt`，首次使用执行：

```bash
cd backend
pip install -r requirements.txt
```

| 依赖 | 用途 |
|------|------|
| Flask | Web 服务框架 |
| Flask-Cors | 跨域支持 |
| PyMySQL | MySQL 数据库连接 |

数据库连接配置在 `backend/app.py` 的 `DB_CONFIG`（host `localhost:3306`，库名 `szagent`）。

## 启动方法

### 前置条件

| 依赖 | 版本 | 说明 |
|------|------|------|
| Node.js + npm | 18+ | 前端编译/运行环境 |
| Python | 3.x | 后端运行环境 |
| MySQL | 5.7+ | 数据库服务需已启动，库名 `szagent`（连接配置在 `backend/app.py` 的 `DB_CONFIG`） |

> **首次运行先装依赖**：分别双击 `start-backend.bat`、`start-front.bat` 会自动安装；
> 也可手动执行 `cd backend && pip install -r requirements.txt` 与 `cd front && npm install`。

### 方式一：一键同时启动（推荐）

双击 `start-all.bat`，脚本会弹出两个独立窗口：

- 「熵舟-后端(Flask:5000)」→ `http://localhost:5000`
- 「熵舟-前端(Vite:5173)」→ `http://localhost:5173`

然后浏览器访问 `http://localhost:5173` 即可（默认登录：admin / 000000）。

### 方式二：分别启动（双击脚本）

1. 双击 `start-backend.bat` → 后端运行在 `http://localhost:5000`
2. 双击 `start-front.bat` → 前端运行在 `http://localhost:5173`
3. 浏览器访问 `http://localhost:5173`

两个脚本会自动检查并安装缺失依赖（node / python 未安装时会给出提示）。

### 方式三：命令行手动启动

```bash
# 终端 1：后端
cd backend
pip install -r requirements.txt   # 仅首次
python app.py

# 终端 2：前端
cd front
npm install        # 仅首次
npm run dev
```

### 方式四：前端生产构建与预览

```bash
cd front
npm run build      # 产物输出到 front/dist/
npm run preview    # 本地预览构建产物（需后端保持运行）
```

### 验证服务是否正常

```bash
# 端口监听检查（两个端口都应 LISTENING）
netstat -ano | findstr ":5173 :5000"

# 后端接口直测（应返回 JSON）
curl http://localhost:5000/api/xxx
```

浏览器打开 `http://localhost:5173` 应显示登录页；输入 admin/000000 与验证码可登录。

### 停止服务

- 在对应服务窗口按 `Ctrl+C`，或直接关闭窗口；
- 前端页面请求 `/api` 由 Vite 自动代理到后端 5000，**必须先启动后端**，否则页面数据请求会失败。

### 常见问题

| 现象 | 处理 |
|------|------|
| 双击脚本报「未找到 node / python」 | 安装对应环境并加入 PATH 后重试 |
| 端口 5173/5000 被占用 | `netstat -ano | findstr :5173` 找到 PID 后结束该进程，或修改 `front/vite.config.js` / `backend/app.py` 端口 |
| 页面数据加载失败（接口报错） | 确认后端窗口已启动、MySQL 服务已开启 |
| 登录提示密码错误 | 账号密码来自 `szagent` 数据库 `dify_accounts` 表（可用 `backend/reset_password.py` 重置） |
| 页面样式与原型不一致 | 历史 HTML 原型已从仓库移除；如需对照请查看 git 历史 `front/legacy/` |

## 页面与路由对照

原 HTML 页面已全部转换为 Vue 组件（`front/src/views/`，共 32 个页面），路由使用 hash 模式：

| 原页面 | 路由 | 组件 |
|--------|------|------|
| login.html | `#/login` | LoginView.vue |
| home.html | `#/home` | HomeView.vue |
| models.html | `#/models` | ModelsView.vue |
| ... | ... | ... |

完整对照见 `front/src/router/index.ts`。历史 HTML 原型已移出仓库（可在 git 历史 `front/legacy/` 查阅）。

## 注意事项

- 前端开发服务（5173）已将 `/api` 代理到后端（5000），页面内请求无需写完整地址
- 登录账号使用 `szagent` 数据库中的用户（如 admin/000000）
- 模型配置管理在「模型」页面，配置后可在「智能工作台」选择并对话
