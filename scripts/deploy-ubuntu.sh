#!/bin/bash
# ============================================
# 熵舟·智能体工作台 — Ubuntu 24.04 一键部署脚本
#
# 用法:
#   1. 上传项目到服务器: scp -r shangzhou/ user@server:/tmp/
#   2. SSH 登录: ssh user@server
#   3. 执行部署: sudo bash /tmp/shangzhou/scripts/deploy-ubuntu.sh
#
# 或直接从 Git 仓库部署:
#   sudo bash -c "$(curl -fsSL https://your-repo/deploy-ubuntu.sh)"
#
# 系统要求:
#   - Ubuntu 24.04 LTS (也支持 22.04)
#   - 最低 4 核 8GB 内存
#   - 50GB 磁盘空间
# ============================================

set -euo pipefail

# ============================================================
# 颜色定义
# ============================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# ============================================================
# 日志函数
# ============================================================
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%H:%M:%S') $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%H:%M:%S') $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $1"
}

log_step() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_fail() {
    echo -e "${RED}✗${NC} $1"
}

# ============================================================
# 配置变量 (可通过环境变量覆盖)
# ============================================================
DEPLOY_USER="${DEPLOY_USER:-szagent}"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/szagent}"
DATA_DIR="${DATA_DIR:-/var/lib/szagent}"
LOG_DIR="${DATA_DIR}/logs"
BACKUP_DIR="${DATA_DIR}/backups"
UPLOAD_DIR="${DATA_DIR}/uploads"

# MySQL 配置
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-$(openssl rand -base64 24)}"
MYSQL_DB_NAME="${MYSQL_DB_NAME:-szagent}"
MYSQL_DB_USER="${MYSQL_DB_USER:-szagent}"
MYSQL_DB_PASSWORD="${MYSQL_DB_PASSWORD:-$(openssl rand -base64 24)}"

# Redis 配置
REDIS_PASSWORD="${REDIS_PASSWORD:-$(openssl rand -base64 24)}"

# JWT 配置
JWT_SECRET="${JWT_SECRET:-$(openssl rand -base64 32)}"
FLASK_SECRET="${FLASK_SECRET:-$(openssl rand -base64 32)}"

# 域名配置
DOMAIN="${DOMAIN:-}"
EMAIL="${EMAIL:-}"

# 服务端口
BACKEND_PORT="${BACKEND_PORT:-5000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

# Git 配置 (可选)
GIT_REPO="${GIT_REPO:-}"
GIT_BRANCH="${GIT_BRANCH:-main}"

# 是否使用 Docker 部署 Qdrant
USE_DOCKER_QDRANT="${USE_DOCKER_QDRANT:-true}"

# 是否配置 SSL
SETUP_SSL="${SETUP_SSL:-false}"

# ============================================================
# 检查函数
# ============================================================

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "请使用 root 权限运行此脚本: sudo bash $0"
        exit 1
    fi
}

check_os() {
    log_step "检查系统环境"

    if ! grep -q "Ubuntu" /etc/os-release 2>/dev/null; then
        log_warn "未检测到 Ubuntu 系统，继续执行但可能不兼容"
    else
        local version=$(grep VERSION_ID /etc/os-release | cut -d'"' -f2)
        log_success "检测到 Ubuntu ${version}"
    fi

    # 检查内存
    local mem_total=$(free -m | awk '/^Mem:/{print $2}')
    if [[ $mem_total -lt 4000 ]]; then
        log_warn "内存不足 4GB (当前: ${mem_total}MB)，可能影响性能"
    else
        log_success "内存充足: ${mem_total}MB"
    fi

    # 检查磁盘
    local disk_free=$(df -BG / | awk 'NR==2 {print $4}' | tr -d 'G')
    if [[ $disk_free -lt 20 ]]; then
        log_warn "磁盘空间不足 20GB (可用: ${disk_free}GB)"
    else
        log_success "磁盘空间充足: ${disk_free}GB 可用"
    fi

    # 检查网络
    if ping -c 1 -W 5 8.8.8.8 &>/dev/null; then
        log_success "网络连接正常"
    else
        log_warn "网络连接可能有问题"
    fi
}

# ============================================================
# 交互式配置
# ============================================================

interactive_config() {
    echo ""
    echo -e "${PURPLE}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║   熵舟·智能体工作台 — 一键部署向导           ║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${CYAN}此脚本将自动完成以下安装:${NC}"
    echo -e "    1. 系统更新与基础工具"
    echo -e "    2. MySQL 8.0 数据库"
    echo -e "    3. Redis 7.0+ 缓存"
    echo -e "    4. Qdrant 向量数据库"
    echo -e "    5. Python 3.10+ 虚拟环境"
    echo -e "    6. Node.js 18 LTS"
    echo -e "    7. Nginx 反向代理"
    echo -e "    8. SSL 证书 (可选)"
    echo -e "    9. 系统服务配置"
    echo -e "   10. 自动备份配置"
    echo ""

    read -p "$(echo -e "${YELLOW}是否开始部署? (y/N): ${NC}")" confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log_info "已取消部署"
        exit 0
    fi

    # 域名配置
    echo ""
    echo -e "${CYAN}--- 域名配置 ---${NC}"
    read -p "请输入域名 (留空使用 IP 访问): " DOMAIN
    if [[ -n "$DOMAIN" ]]; then
        read -p "请输入邮箱 (用于 SSL 证书): " EMAIL
        SETUP_SSL="true"
    fi

    # 数据库密码
    echo ""
    echo -e "${CYAN}--- 数据库配置 ---${NC}"
    echo -e "  留空则自动生成安全密码"
    read -p "MySQL root 密码 [自动生成]: " input_mysql_root
    [[ -n "$input_mysql_root" ]] && MYSQL_ROOT_PASSWORD="$input_mysql_root"

    read -p "MySQL 应用用户密码 [自动生成]: " input_mysql_app
    [[ -n "$input_mysql_app" ]] && MYSQL_DB_PASSWORD="$input_mysql_app"

    read -p "Redis 密码 [自动生成]: " input_redis
    [[ -n "$input_redis" ]] && REDIS_PASSWORD="$input_redis"

    # 确认配置
    echo ""
    echo -e "${CYAN}--- 配置确认 ---${NC}"
    echo -e "  部署目录: ${BOLD}${DEPLOY_DIR}${NC}"
    echo -e "  数据目录: ${BOLD}${DATA_DIR}${NC}"
    echo -e "  域名: ${BOLD}${DOMAIN:-未设置}${NC}"
    echo -e "  SSL: ${BOLD}${SETUP_SSL}${NC}"
    echo ""

    read -p "$(echo -e "${YELLOW}确认开始部署? (y/N): ${NC}")" confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log_info "已取消部署"
        exit 0
    fi
}

# ============================================================
# 第 1 步: 系统更新与基础工具
# ============================================================

step1_system_update() {
    log_step "第 1 步: 系统更新与基础工具"

    log_info "更新系统包..."
    apt-get update -y > /dev/null 2>&1
    apt-get upgrade -y > /dev/null 2>&1
    log_success "系统更新完成"

    log_info "安装基础工具..."
    apt-get install -y \
        curl \
        wget \
        git \
        vim \
        htop \
        net-tools \
        unzip \
        zip \
        build-essential \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release \
        jq \
        tree \
        rsync \
        cron \
        logrotate \
        > /dev/null 2>&1
    log_success "基础工具安装完成"
}

# ============================================================
# 第 2 步: 创建用户和目录
# ============================================================

step2_create_user() {
    log_step "第 2 步: 创建用户和目录"

    # 创建部署用户
    if id "$DEPLOY_USER" &>/dev/null; then
        log_warn "用户 $DEPLOY_USER 已存在"
    else
        useradd -m -s /bin/bash "$DEPLOY_USER"
        log_success "创建用户: $DEPLOY_USER"
    fi

    # 创建目录结构
    mkdir -p "$DEPLOY_DIR"
    mkdir -p "$DATA_DIR"/{logs,backups,uploads}
    mkdir -p /var/log/szagent
    mkdir -p /var/log/nginx/szagent

    # 设置权限
    chown -R "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR"
    chown -R "$DEPLOY_USER:$DEPLOY_USER" "$DATA_DIR"
    chown -R "$DEPLOY_USER:$DEPLOY_USER" /var/log/szagent

    log_success "目录结构创建完成"
    log_info "  项目目录: $DEPLOY_DIR"
    log_info "  数据目录: $DATA_DIR"
}

# ============================================================
# 第 3 步: 安装 MySQL 8.0
# ============================================================

step3_install_mysql() {
    log_step "第 3 步: 安装 MySQL 8.0"

    if command -v mysql &>/dev/null; then
        log_warn "MySQL 已安装，跳过安装步骤"
    else
        log_info "安装 MySQL..."
        apt-get install -y mysql-server > /dev/null 2>&1
        log_success "MySQL 安装完成"
    fi

    # 启动 MySQL
    systemctl start mysql
    systemctl enable mysql > /dev/null 2>&1
    log_success "MySQL 服务已启动"

    # 配置 MySQL root 密码
    log_info "配置 MySQL root 密码..."
    mysql -u root <<EOF
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '${MYSQL_ROOT_PASSWORD}';
FLUSH PRIVILEGES;
EOF
    log_success "MySQL root 密码配置完成"

    # 创建应用数据库和用户
    log_info "创建应用数据库和用户..."
    mysql -u root -p"${MYSQL_ROOT_PASSWORD}" <<EOF
CREATE DATABASE IF NOT EXISTS ${MYSQL_DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${MYSQL_DB_USER}'@'localhost' IDENTIFIED WITH mysql_native_password BY '${MYSQL_DB_PASSWORD}';
GRANT ALL PRIVILEGES ON ${MYSQL_DB_NAME}.* TO '${MYSQL_DB_USER}'@'localhost';
FLUSH PRIVILEGES;
EOF
    log_success "数据库 ${MYSQL_DB_NAME} 和用户 ${MYSQL_DB_USER} 创建完成"

    # 优化 MySQL 配置
    log_info "优化 MySQL 配置..."
    cat > /etc/mysql/mysql.conf.d/szagent.cnf <<'EOF'
[mysqld]
# 基础配置
bind-address = 127.0.0.1
max_connections = 200
max_allowed_packet = 64M

# InnoDB 优化
innodb_buffer_pool_size = 1G
innodb_log_file_size = 256M
innodb_flush_log_at_trx_commit = 2
innodb_flush_method = O_DIRECT
innodb_file_per_table = 1

# 字符集
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

# 慢查询日志
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2

# 临时表
tmp_table_size = 64M
max_heap_table_size = 64M
EOF

    systemctl restart mysql
    log_success "MySQL 配置优化完成"
}

# ============================================================
# 第 4 步: 安装 Redis
# ============================================================

step4_install_redis() {
    log_step "第 4 步: 安装 Redis"

    if command -v redis-server &>/dev/null; then
        log_warn "Redis 已安装，跳过安装步骤"
    else
        log_info "安装 Redis..."
        apt-get install -y redis-server > /dev/null 2>&1
        log_success "Redis 安装完成"
    fi

    # 配置 Redis
    log_info "配置 Redis..."
    mkdir -p /etc/redis/redis.conf.d
    cat > /etc/redis/redis.conf.d/szagent.conf <<EOF
# 密码配置
requirepass ${REDIS_PASSWORD}

# 内存配置
maxmemory 512mb
maxmemory-policy allkeys-lru

# 持久化
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec

# 日志
loglevel notice
logfile /var/log/redis/redis-server.log
EOF

    # 确保主配置包含子配置
    if ! grep -q "include /etc/redis/redis.conf.d/szagent.conf" /etc/redis/redis.conf; then
        echo "include /etc/redis/redis.conf.d/szagent.conf" >> /etc/redis/redis.conf
    fi

    systemctl restart redis-server
    systemctl enable redis-server > /dev/null 2>&1
    log_success "Redis 配置完成"

    # 验证
    if redis-cli -a "$REDIS_PASSWORD" ping | grep -q PONG; then
        log_success "Redis 连接正常"
    else
        log_error "Redis 连接失败"
    fi
}

# ============================================================
# 第 5 步: 安装 Qdrant
# ============================================================

step5_install_qdrant() {
    log_step "第 5 步: 安装 Qdrant 向量数据库"

    if [[ "$USE_DOCKER_QDRANT" == "true" ]]; then
        step5_qdrant_docker
    else
        step5_qdrant_binary
    fi
}

step5_qdrant_docker() {
    log_info "使用 Docker 部署 Qdrant..."

    # 安装 Docker
    if ! command -v docker &>/dev/null; then
        log_info "安装 Docker..."
        curl -fsSL https://get.docker.com | sh > /dev/null 2>&1
        log_success "Docker 安装完成"
    fi

    # 将部署用户加入 docker 组
    usermod -aG docker "$DEPLOY_USER" 2>/dev/null || true

    # 创建数据目录
    mkdir -p /var/lib/qdrant/{storage,snapshots}
    chown -R "$DEPLOY_USER:$DEPLOY_USER" /var/lib/qdrant

    # 运行 Qdrant
    docker run -d \
        --name qdrant \
        --restart unless-stopped \
        -p 6333:6333 \
        -p 6334:6334 \
        -v /var/lib/qdrant/storage:/qdrant/storage \
        -v /var/lib/qdrant/snapshots:/qdrant/snapshots \
        qdrant/qdrant:latest

    log_success "Qdrant Docker 容器已启动"

    # 验证
    sleep 3
    if curl -s http://localhost:6333/healthz | grep -q ok; then
        log_success "Qdrant 运行正常"
    else
        log_warn "Qdrant 可能还在启动中"
    fi
}

step5_qdrant_binary() {
    log_info "使用二进制部署 Qdrant..."

    # 下载 Qdrant
    local qdrant_version="v1.9.1"
    local qdrant_url="https://github.com/qdrant/qdrant/releases/download/${qdrant_version}/qdrant-x86_64-unknown-linux-gnu.tar.gz"

    if [[ ! -f /usr/local/bin/qdrant ]]; then
        log_info "下载 Qdrant ${qdrant_version}..."
        wget -q "$qdrant_url" -O /tmp/qdrant.tar.gz
        tar -xzf /tmp/qdrant.tar.gz -C /tmp/
        mv /tmp/qdrant /usr/local/bin/
        chmod +x /usr/local/bin/qdrant
        rm /tmp/qdrant.tar.gz
        log_success "Qdrant 下载完成"
    fi

    # 创建配置目录
    mkdir -p /etc/qdrant
    mkdir -p /var/lib/qdrant/{storage,snapshots}
    chown -R "$DEPLOY_USER:$DEPLOY_USER" /var/lib/qdrant
    chown -R "$DEPLOY_USER:$DEPLOY_USER" /etc/qdrant

    # 创建配置文件
    cat > /etc/qdrant/config.yaml <<'EOF'
log_level: INFO
storage:
  storage_path: /var/lib/qdrant/storage
  snapshots_path: /var/lib/qdrant/snapshots
service:
  host: 0.0.0.0
  http_port: 6333
  grpc_port: 6334
EOF

    # 创建 systemd 服务
    cat > /etc/systemd/system/qdrant.service <<EOF
[Unit]
Description=Qdrant Vector Database
After=network.target

[Service]
Type=simple
User=${DEPLOY_USER}
Group=${DEPLOY_USER}
ExecStart=/usr/local/bin/qdrant --config-path /etc/qdrant/config.yaml
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl start qdrant
    systemctl enable qdrant > /dev/null 2>&1
    log_success "Qdrant 服务已启动"
}

# ============================================================
# 第 6 步: 安装 Python 和 Node.js
# ============================================================

step6_install_python_node() {
    log_step "第 6 步: 安装 Python 和 Node.js"

    # Python
    log_info "安装 Python..."
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        libffi-dev \
        libssl-dev \
        default-libmysqlclient-dev \
        pkg-config \
        > /dev/null 2>&1
    log_success "Python $(python3 --version) 安装完成"

    # Node.js 18 LTS
    log_info "安装 Node.js 18 LTS..."
    if ! command -v node &>/dev/null; then
        curl -fsSL https://deb.nodesource.com/setup_18.x | bash - > /dev/null 2>&1
        apt-get install -y nodejs > /dev/null 2>&1
    fi
    log_success "Node.js $(node --version) 安装完成"
    log_info "npm $(npm --version) 安装完成"
}

# ============================================================
# 第 7 步: 部署项目代码
# ============================================================

step7_deploy_code() {
    log_step "第 7 步: 部署项目代码"

    # 检查项目是否已存在
    if [[ -f "$DEPLOY_DIR/backend/app.py" ]]; then
        log_warn "项目已存在，跳过代码部署"
        return
    fi

    # 从 Git 克隆
    if [[ -n "$GIT_REPO" ]]; then
        log_info "从 Git 仓库克隆代码..."
        git clone -b "$GIT_BRANCH" "$GIT_REPO" "$DEPLOY_DIR"
        log_success "代码克隆完成"
    else
        # 从当前目录复制
        local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../" && pwd)"
        if [[ -f "$script_dir/backend/app.py" ]]; then
            log_info "从本地目录复制代码..."
            cp -r "$script_dir"/* "$DEPLOY_DIR/"
            cp -r "$script_dir"/.* "$DEPLOY_DIR/" 2>/dev/null || true
            log_success "代码复制完成"
        else
            log_error "未找到项目代码，请确保脚本在项目目录中运行"
            exit 1
        fi
    fi

    # 设置权限
    chown -R "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR"
    log_success "项目代码部署完成"
}

# ============================================================
# 第 8 步: 配置后端环境
# ============================================================

step8_setup_backend() {
    log_step "第 8 步: 配置后端环境"

    # 创建 .env 配置文件
    log_info "创建环境配置..."
    cat > "$DEPLOY_DIR/.env" <<EOF
# 数据库配置
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=${MYSQL_DB_USER}
DB_PASSWORD=${MYSQL_DB_PASSWORD}
DB_NAME=${MYSQL_DB_NAME}

# Redis 配置
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=${REDIS_PASSWORD}

# JWT 认证
JWT_SECRET=${JWT_SECRET}
JWT_ACCESS_EXPIRY=7200
JWT_REFRESH_EXPIRY=604800

# 加密密钥
ENCRYPTION_KEY=

# 日志配置
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=${LOG_DIR}/backend.log
LOG_MAX_SIZE=10485760
LOG_BACKUP_COUNT=10

# Flask 配置
FLASK_DEBUG=0
SECRET_KEY=${FLASK_SECRET}
APP_VERSION=1.0.0

# 安全开关：缺省值本身就是隐患——REQUIRE_LOGIN_FOR_API 不设即为 off（全部 /api/* 免登录），
# OWNERSHIP_CHECK_MODE 不设即为 warn（只记日志不拦截）。
# 这三个键必须写在这里，不能只放在 .env.example 里：本脚本生成的 .env 会直接覆盖它。
REQUIRE_LOGIN_FOR_API=strict
OWNERSHIP_CHECK_MODE=strict
LOGIN_LOCKOUT_ENABLED=true
# 登录页图形验证码（前端构建时内联）；不设则 LoginView 默认 true，写出来以免歧义
VITE_LOGIN_CAPTCHA=true

# Celery 配置
CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@127.0.0.1:6379/1

# 备份配置
BACKUP_DIR=${BACKUP_DIR}
UPLOAD_DIR=${UPLOAD_DIR}
EOF

    chown "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR/.env"
    chmod 600 "$DEPLOY_DIR/.env"
    log_success ".env 配置文件创建完成"

    # 创建 Python 虚拟环境
    log_info "创建 Python 虚拟环境..."
    sudo -u "$DEPLOY_USER" bash -c "
        python3 -m venv ${DEPLOY_DIR}/venv
        source ${DEPLOY_DIR}/venv/bin/activate
        pip install --upgrade pip setuptools wheel -q
        pip install -r ${DEPLOY_DIR}/backend/requirements.txt -q
        pip install gunicorn gevent -q
    "
    log_success "Python 虚拟环境创建完成"

    # 初始化数据库
    log_info "初始化数据库..."
    sudo -u "$DEPLOY_USER" bash -c "
        source ${DEPLOY_DIR}/venv/bin/activate
        cd ${DEPLOY_DIR}/backend
        python -c \"
import sys
sys.path.insert(0, '.')
from config import get_db
import models.tables as T
db = get_db()
cur = db.cursor()
ok = 0
for _name in dir(T):
    if _name.endswith('_TABLE_SQL'):
        _sql = getattr(T, _name)
        if isinstance(_sql, str) and _sql.lstrip().upper().startswith('CREATE'):
            try:
                cur.execute(_sql)
                ok += 1
            except Exception as _e:
                print('skip', _name, repr(_e))
# 废表收尾：账号已合并进 dify_accounts，旧部署里可能还留着一张没人读的 users 空表；
# models/tables.py 已不再定义它，这里把存量机器上的残留一并清掉。
try:
    cur.execute('DROP TABLE IF EXISTS users')
    print('废弃的 users 表已清理（如存在）')
except Exception as _e:
    print('drop users skipped:', repr(_e))
db.commit()
db.close()
print('数据库初始化完成: %d 张表已就绪' % ok)
\"
    "
    log_success "数据库初始化完成"

    # 创建 Gunicorn 配置
    log_info "创建 Gunicorn 配置..."
    cat > "$DEPLOY_DIR/backend/gunicorn.conf.py" <<'EOF'
# Gunicorn 配置文件
import multiprocessing

bind = '127.0.0.1:5000'
backlog = 2048

workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'gevent'
worker_connections = 1000
timeout = 120
keepalive = 5

accesslog = '/var/lib/szagent/logs/gunicorn_access.log'
errorlog = '/var/lib/szagent/logs/gunicorn_error.log'
loglevel = 'info'

pidfile = '/tmp/gunicorn.pid'
preload_app = True

graceful_timeout = 30
max_requests = 1000
max_requests_jitter = 50

limit_request_line = 4094
limit_request_fields = 100
EOF

    chown "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR/backend/gunicorn.conf.py"
    log_success "Gunicorn 配置创建完成"
}

# ============================================================
# 第 9 步: 构建前端
# ============================================================

step9_build_frontend() {
    log_step "第 9 步: 构建前端"

    # 安装前端依赖并构建
    log_info "安装前端依赖..."
    sudo -u "$DEPLOY_USER" bash -c "
        cd ${DEPLOY_DIR}/front
        npm install --silent
    "
    log_success "前端依赖安装完成"

    log_info "构建前端生产版本..."
    sudo -u "$DEPLOY_USER" bash -c "
        cd ${DEPLOY_DIR}/front
        npm run build
    "
    log_success "前端构建完成"

    # 设置权限
    chown -R "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR/front/dist"
    log_success "前端构建产物已生成"
}

# ============================================================
# 第 10 步: 配置 Nginx
# ============================================================

step10_setup_nginx() {
    log_step "第 10 步: 配置 Nginx"

    # 安装 Nginx
    if ! command -v nginx &>/dev/null; then
        log_info "安装 Nginx..."
        apt-get install -y nginx > /dev/null 2>&1
    fi

    # 创建 Nginx 配置
    log_info "创建 Nginx 配置..."

    if [[ -n "$DOMAIN" ]]; then
        local server_name="$DOMAIN"
    else
        local server_name="_"
    fi

    cat > /etc/nginx/sites-available/szagent <<EOF
# Shangzhou Workbench - Nginx (HTTP)
# If DOMAIN is set + SSL enabled, certbot (step 11) auto-upgrades to HTTPS.

server {
    listen 80;
    listen [::]:80;
    server_name ${server_name};

    root ${DEPLOY_DIR}/front/dist;
    index index.html;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    access_log /var/log/nginx/szagent_access.log;
    error_log /var/log/nginx/szagent_error.log;

    client_max_body_size 50M;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location = /health {
        proxy_pass http://127.0.0.1:${BACKEND_PORT}/api/health;
        access_log off;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }

    location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)\$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
        try_files \$uri =404;
    }

    location ~ /\\. {
        deny all;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
EOF

    # 启用站点
    rm -f /etc/nginx/sites-enabled/default
    ln -sf /etc/nginx/sites-available/szagent /etc/nginx/sites-enabled/

    # 测试配置
    nginx -t
    systemctl restart nginx
    systemctl enable nginx > /dev/null 2>&1
    log_success "Nginx 配置完成"
}

# ============================================================
# 第 11 步: 配置 SSL
# ============================================================

step11_setup_ssl() {
    log_step "第 11 步: 配置 SSL 证书"

    if [[ "$SETUP_SSL" != "true" ]] || [[ -z "$DOMAIN" ]]; then
        log_info "跳过 SSL 配置"
        return
    fi

    # 安装 Certbot
    log_info "安装 Certbot..."
    apt-get install -y certbot python3-certbot-nginx > /dev/null 2>&1
    mkdir -p /var/www/certbot

    # 获取证书
    log_info "获取 SSL 证书..."
    certbot --nginx \
        -d "$DOMAIN" \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        --redirect \
        --hsts

    # 自动续期
    systemctl enable certbot.timer > /dev/null 2>&1
    log_success "SSL 证书配置完成"
}

# ============================================================
# 第 12 步: 创建 systemd 服务
# ============================================================

step12_create_services() {
    log_step "第 12 步: 创建 systemd 服务"

    # 后端服务
    log_info "创建后端服务..."
    cat > /etc/systemd/system/szagent-backend.service <<EOF
[Unit]
Description=Shangzhou Agent Workbench - Backend
After=network.target mysql.service redis-server.service
Wants=mysql.service redis-server.service

[Service]
Type=simple
User=${DEPLOY_USER}
Group=${DEPLOY_USER}
WorkingDirectory=${DEPLOY_DIR}/backend
Environment="PATH=${DEPLOY_DIR}/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=${DEPLOY_DIR}/.env

ExecStart=${DEPLOY_DIR}/venv/bin/gunicorn -c gunicorn.conf.py app:app
ExecReload=/bin/kill -s HUP \$MAINPID

Restart=always
RestartSec=5

# 安全加固
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${DATA_DIR} /tmp

# 资源限制
LimitNOFILE=65536
MemoryMax=2G

[Install]
WantedBy=multi-user.target
EOF

    # Celery Worker 服务
    log_info "创建 Celery Worker 服务..."
    cat > /etc/systemd/system/szagent-worker.service <<EOF
[Unit]
Description=Shangzhou Agent Workbench - Celery Worker
After=network.target redis-server.service
Wants=redis-server.service

[Service]
Type=simple
User=${DEPLOY_USER}
Group=${DEPLOY_USER}
WorkingDirectory=${DEPLOY_DIR}/backend
Environment="PATH=${DEPLOY_DIR}/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=${DEPLOY_DIR}/.env

ExecStart=${DEPLOY_DIR}/venv/bin/celery -A tasks.celery_app worker -B --loglevel=info -Q workflow,embedding,scheduled --concurrency=4
ExecReload=/bin/kill -s HUP \$MAINPID

Restart=always
RestartSec=5

# 安全加固
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${DATA_DIR} /tmp

# 资源限制
LimitNOFILE=65536
MemoryMax=2G

[Install]
WantedBy=multi-user.target
EOF

    # 重载 systemd
    systemctl daemon-reload

    # 启动服务
    log_info "启动后端服务..."
    systemctl start szagent-backend
    systemctl enable szagent-backend > /dev/null 2>&1

    log_info "启动 Worker 服务..."
    systemctl start szagent-worker
    systemctl enable szagent-worker > /dev/null 2>&1

    log_success "systemd 服务创建并启动完成"
}

# ============================================================
# 第 13 步: 配置自动备份
# ============================================================

step13_setup_backup() {
    log_step "第 13 步: 配置自动备份"

    # 创建备份脚本
    log_info "创建备份脚本..."
    cat > "$DEPLOY_DIR/scripts/backup.sh" <<'BACKUP_EOF'
#!/bin/bash
# 熵舟·智能体工作台 - 自动备份脚本

set -e

BACKUP_DIR="${BACKUP_DIR:-/var/lib/szagent/backups}"
MYSQL_USER="${DB_USER:-szagent}"
MYSQL_PASS="${DB_PASSWORD:-}"
MYSQL_DB="${DB_NAME:-szagent}"
REDIS_PASS="${REDIS_PASSWORD:-}"
RETENTION_DAYS=30
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

mkdir -p "$BACKUP_DIR"/{mysql,redis,files}

echo "[$(date)] 开始备份..."

# MySQL 备份
echo "  备份 MySQL..."
mysqldump \
    --user="$MYSQL_USER" \
    --password="$MYSQL_PASS" \
    --single-transaction \
    --routines \
    --triggers \
    --databases "$MYSQL_DB" | gzip > "$BACKUP_DIR/mysql/mysql_${TIMESTAMP}.sql.gz"

# Redis 备份
echo "  备份 Redis..."
if [[ -n "$REDIS_PASS" ]]; then
    redis-cli -a "$REDIS_PASS" BGSAVE
else
    redis-cli BGSAVE
fi
sleep 2
cp /var/lib/redis/dump.rdb "$BACKUP_DIR/redis/redis_${TIMESTAMP}.rdb" 2>/dev/null || true

# 文件备份
echo "  备份文件..."
tar -czf "$BACKUP_DIR/files/files_${TIMESTAMP}.tar.gz" \
    -C "$(dirname "$BACKUP_DIR")" uploads/ 2>/dev/null || true

# 清理旧备份
echo "  清理旧备份..."
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "*.rdb" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

# 计算大小
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo "[$(date)] 备份完成! 总大小: $BACKUP_SIZE"
BACKUP_EOF

    chmod +x "$DEPLOY_DIR/scripts/backup.sh"
    chown "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR/scripts/backup.sh"

    # 配置 crontab
    log_info "配置定时备份..."
    cat > /etc/cron.d/szagent-backup <<EOF
# 熵舟·智能体工作台 - 定时备份
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin

# 每天凌晨 3:00 执行全量备份
0 3 * * * ${DEPLOY_USER} ${DEPLOY_DIR}/scripts/backup.sh >> ${LOG_DIR}/backup.log 2>&1

# 每周日凌晨 4:00 清理日志
0 4 * * 0 root find ${LOG_DIR} -name "*.log.*" -mtime +30 -delete
EOF

    chmod 644 /etc/cron.d/szagent-backup
    log_success "自动备份配置完成"
}

# ============================================================
# 第 14 步: 配置日志轮转
# ============================================================

step14_setup_logrotate() {
    log_step "第 14 步: 配置日志轮转"

    cat > /etc/logrotate.d/szagent <<EOF
${LOG_DIR}/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 ${DEPLOY_USER} ${DEPLOY_USER}
    sharedscripts
    postrotate
        systemctl reload szagent-backend 2>/dev/null || true
        systemctl reload szagent-worker 2>/dev/null || true
    endscript
}

/var/log/nginx/szagent_*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        systemctl reload nginx 2>/dev/null || true
    endscript
}
EOF

    log_success "日志轮转配置完成"
}

# ============================================================
# 第 15 步: 配置防火墙
# ============================================================

step15_setup_firewall() {
    log_step "第 15 步: 配置防火墙"

    # 安装 UFW
    if ! command -v ufw &>/dev/null; then
        apt-get install -y ufw > /dev/null 2>&1
    fi

    # 配置规则
    ufw default deny incoming > /dev/null 2>&1
    ufw default allow outgoing > /dev/null 2>&1
    ufw allow ssh > /dev/null 2>&1
    ufw allow 80/tcp > /dev/null 2>&1
    ufw allow 443/tcp > /dev/null 2>&1

    # 启用防火墙
    ufw --force enable > /dev/null 2>&1
    log_success "防火墙配置完成"
    ufw status | head -10
}

# ============================================================
# 第 16 步: 验证部署
# ============================================================

step16_verify_deployment() {
    log_step "第 16 步: 验证部署"

    local errors=0

    # 检查 MySQL
    if systemctl is-active --quiet mysql; then
        log_success "MySQL 运行正常"
    else
        log_fail "MySQL 未运行"
        ((errors++))
    fi

    # 检查 Redis
    if systemctl is-active --quiet redis-server; then
        log_success "Redis 运行正常"
    else
        log_fail "Redis 未运行"
        ((errors++))
    fi

    # 检查 Qdrant
    if curl -s http://localhost:6333/healthz | grep -q ok; then
        log_success "Qdrant 运行正常"
    else
        log_fail "Qdrant 未运行"
        ((errors++))
    fi

    # 检查后端
    if systemctl is-active --quiet szagent-backend; then
        log_success "后端服务运行正常"
    else
        log_fail "后端服务未运行"
        ((errors++))
    fi

    # 检查 Worker
    if systemctl is-active --quiet szagent-worker; then
        log_success "Worker 服务运行正常"
    else
        log_fail "Worker 服务未运行"
        ((errors++))
    fi

    # 检查 Nginx
    if systemctl is-active --quiet nginx; then
        log_success "Nginx 运行正常"
    else
        log_fail "Nginx 未运行"
        ((errors++))
    fi

    # 检查 API
    sleep 2
    if curl -s http://localhost:5000/api/health | grep -q "healthy\|running"; then
        log_success "API 健康检查通过"
    else
        log_warn "API 健康检查未通过 (可能还在启动中)"
    fi

    return $errors
}

# ============================================================
# 部署完成总结
# ============================================================

print_summary() {
    echo ""
    echo -e "${PURPLE}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║   熵舟·智能体工作台 — 部署完成!              ║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "${CYAN}--- 访问信息 ---${NC}"
    if [[ -n "$DOMAIN" ]]; then
        echo -e "  网站: ${BOLD}https://${DOMAIN}${NC}"
    else
        local server_ip=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
        echo -e "  网站: ${BOLD}http://${server_ip}${NC}"
    fi
    echo -e "  后端: http://localhost:5000"
    echo ""

    echo -e "${CYAN}--- 目录结构 ---${NC}"
    echo -e "  项目目录: ${BOLD}${DEPLOY_DIR}${NC}"
    echo -e "  数据目录: ${BOLD}${DATA_DIR}${NC}"
    echo -e "  日志目录: ${BOLD}${LOG_DIR}${NC}"
    echo -e "  备份目录: ${BOLD}${BACKUP_DIR}${NC}"
    echo ""

    echo -e "${CYAN}--- 数据库信息 ---${NC}"
    echo -e "  MySQL root 密码: ${BOLD}${MYSQL_ROOT_PASSWORD}${NC}"
    echo -e "  MySQL 应用用户: ${BOLD}${MYSQL_DB_USER}${NC}"
    echo -e "  MySQL 应用密码: ${BOLD}${MYSQL_DB_PASSWORD}${NC}"
    echo -e "  Redis 密码: ${BOLD}${REDIS_PASSWORD}${NC}"
    echo ""

    echo -e "${CYAN}--- 服务管理 ---${NC}"
    echo -e "  启动后端: ${BOLD}sudo systemctl start szagent-backend${NC}"
    echo -e "  停止后端: ${BOLD}sudo systemctl stop szagent-backend${NC}"
    echo -e "  重启后端: ${BOLD}sudo systemctl restart szagent-backend${NC}"
    echo -e "  查看日志: ${BOLD}sudo journalctl -u szagent-backend -f${NC}"
    echo ""

    echo -e "${CYAN}--- 备份恢复 ---${NC}"
    echo -e "  手动备份: ${BOLD}sudo -u ${DEPLOY_USER} ${DEPLOY_DIR}/scripts/backup.sh${NC}"
    echo -e "  定时备份: 每天凌晨 3:00 自动执行"
    echo ""

    echo -e "${YELLOW}⚠ 部署后必须做的安全步骤:${NC}"
    echo -e "  1. 系统里${BOLD}没有任何预置账号${NC}：请用上面的网站地址注册你自己的第一个账号，"
    echo -e "     它会自动成为创建者；登录后再去做第 2 步"
    echo -e "  2. ${BOLD}关闭开放注册${NC}（否则任何人都能自助注册进来）：登录后进「系统设置」，"
    echo -e "     取消勾选“是否开放注册”；若要保留注册但只给受邀者用，"
    echo -e "     就只填“注册邀请码”（后端 /api/register 会强制校验）"
    echo -e "  3. 凭证文件 ${DEPLOY_DIR}/.credentials 权限已是 600，建议另存后删除"
    echo -e "  4. 安全开关（REQUIRE_LOGIN_FOR_API / OWNERSHIP_CHECK_MODE）已写入"
    echo -e "     ${DEPLOY_DIR}/.env，不要改回 off/warn；改了需重启 szagent-backend"
    echo -e "  5. 定期查看备份日志: ${LOG_DIR}/backup.log"
    echo ""

    # 保存密码到文件
    cat > "$DEPLOY_DIR/.credentials" <<EOF
# 熵舟·智能体工作台 — 部署凭证
# 生成时间: $(date)
# ⚠ 请妥善保管此文件，建议删除或限制访问权限

MySQL root 密码: ${MYSQL_ROOT_PASSWORD}
MySQL 应用用户: ${MYSQL_DB_USER}
MySQL 应用密码: ${MYSQL_DB_PASSWORD}
Redis 密码: ${REDIS_PASSWORD}
JWT 密钥: ${JWT_SECRET}
Flask 密钥: ${FLASK_SECRET}
EOF

    chmod 600 "$DEPLOY_DIR/.credentials"
    chown "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR/.credentials"

    echo -e "${GREEN}✓ 凭证已保存到: ${DEPLOY_DIR}/.credentials${NC}"
    echo ""
}

# ============================================================
# 主函数
# ============================================================

main() {
    echo ""
    echo -e "${PURPLE}══════════════════════════════════════════════${NC}"
    echo -e "${PURPLE}  熵舟·智能体工作台 — Ubuntu 24.04 一键部署${NC}"
    echo -e "${PURPLE}══════════════════════════════════════════════${NC}"
    echo ""

    # 检查 root 权限
    check_root

    # 检查系统环境
    check_os

    # 交互式配置
    interactive_config

    # 记录开始时间
    local start_time=$(date +%s)

    # 执行部署步骤
    step1_system_update
    step2_create_user
    step3_install_mysql
    step4_install_redis
    step5_install_qdrant
    step6_install_python_node
    step7_deploy_code
    step8_setup_backend
    step9_build_frontend
    step10_setup_nginx
    step11_setup_ssl
    step12_create_services
    step13_setup_backup
    step14_setup_logrotate
    step15_setup_firewall
    step16_verify_deployment

    # 计算耗时
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))

    echo ""
    log_info "部署耗时: ${minutes} 分 ${seconds} 秒"
    echo ""

    # 打印总结
    print_summary
}

# 执行主函数
main "$@"
