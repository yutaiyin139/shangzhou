#!/usr/bin/env bash
# =============================================================================
#  熵舟·智能体工作台 —— Ubuntu 在线一键部署脚本 (V1.0)
#  适用：代码(backend/ + front/dist)已上传到 $APP_DIR 之后，在目标机执行。
#  特性：
#    - 使用远端 MySQL（PyMySQL 纯驱动，无需编译 mysqlclient）
#    - 本机 apt 提供 venv / pip / redis / nginx / 构建工具
#    - HTTP 端口可配（默认 8080，避让已占用 80/443 的其他服务如 Dify）
#    - Qdrant 可选，缺失时后端自动回退 MySQL 余弦检索
#    - gunicorn gthread 工作模式（纯 Python，规避 Py3.14 gevent wheel 缺失）
#  用法：
#    sudo bash deploy-ubuntu-online.sh
#    可用环境变量覆盖：APP_DIR BACKEND_PORT HTTP_PORT DB_HOST DB_PORT DB_USER
#                      DB_PASSWORD DB_NAME REDIS_HOST REDIS_PORT QDRANT_ENABLE
# =============================================================================
set -euo pipefail

# ---------------------------- 可配置参数 -------------------------------------
APP_DIR="${APP_DIR:-/home/yuty/shangzhou}"
APP_USER="${APP_USER:-yuty}"
BACKEND_PORT="${BACKEND_PORT:-5000}"
HTTP_PORT="${HTTP_PORT:-80}"

DB_HOST="${DB_HOST:-172.28.240.1}"
DB_PORT="${DB_PORT:-3306}"
# 注：该 MySQL 仅授予 root@'localhost' 与 yuty@'%'；远程必须用 yuty（root 远程会被拒）。
DB_USER="${DB_USER:-yuty}"
DB_PASSWORD="${DB_PASSWORD:-0000}"
DB_NAME="${DB_NAME:-szagent}"

REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"

# Qdrant 向量库。enable=1 时使用本机 /usr/local/bin/qdrant（systemd 管理）；
# 若二进制缺失则自动跳过，后端回退 MySQL 余弦检索。
QDRANT_ENABLE="${QDRANT_ENABLE:-1}"

SERVER_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
[ -z "$SERVER_IP" ] && SERVER_IP="127.0.0.1"

log()  { echo -e "\033[1;36m[deploy]\033[0m $*"; }
warn() { echo -e "\033[1;33m[warn]\033[0m $*"; }
die()  { echo -e "\033[1;31m[error]\033[0m $*" >&2; exit 1; }

# ---------------------------- 前置校验 ---------------------------------------
[ "$(id -u)" -eq 0 ] || die "请以 root 运行：sudo bash $0"
[ -f "$APP_DIR/backend/app.py" ] || die "未找到 $APP_DIR/backend/app.py —— 请先上传后端代码"
[ -f "$APP_DIR/front/dist/index.html" ] || die "未找到 $APP_DIR/front/dist/index.html —— 请先上传前端构建产物"

log "部署目录=$APP_DIR  后端端口=$BACKEND_PORT  HTTP端口=$HTTP_PORT"
log "数据库=$DB_USER@$DB_HOST:$DB_PORT/$DB_NAME  Redis=$REDIS_HOST:$REDIS_PORT"

# ---------------------------- 1. 安装系统依赖 --------------------------------
log "步骤 1/8  安装系统依赖 (apt)"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip python3-dev \
    build-essential libffi-dev libssl-dev pkg-config \
    redis-server nginx curl rsync

# ---------------------------- 2. 写入 .env -----------------------------------
log "步骤 2/8  生成 $APP_DIR/.env"
cat > "$APP_DIR/.env" <<EOF
DB_HOST=$DB_HOST
DB_PORT=$DB_PORT
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_NAME=$DB_NAME

REDIS_HOST=$REDIS_HOST
REDIS_PORT=$REDIS_PORT
REDIS_PASSWORD=$REDIS_PASSWORD

JWT_SECRET=$(python3 -c 'import secrets;print(secrets.token_hex(32))')
JWT_ACCESS_EXPIRY=7200
JWT_REFRESH_EXPIRY=604800
ENCRYPTION_KEY=

LOG_LEVEL=INFO
LOG_FORMAT=text
FLASK_DEBUG=0
SECRET_KEY=$(python3 -c 'import secrets;print(secrets.token_hex(24))')

CELERY_BROKER_URL=redis://$REDIS_HOST:$REDIS_PORT/0
CELERY_RESULT_BACKEND=redis://$REDIS_HOST:$REDIS_PORT/1

MARKETPLACE_API_BASE=https://marketplace.dify.ai/api/v1
MARKETPLACE_SYNC_ALL=true
EOF
chmod 600 "$APP_DIR/.env"

# ---------------------------- 3. Python 虚拟环境 + 依赖 ----------------------
log "步骤 3/8  创建虚拟环境并安装后端依赖（首次较慢）"
if [ ! -x "$APP_DIR/venv/bin/gunicorn" ] || [ ! -d "$APP_DIR/venv" ]; then
    rm -rf "$APP_DIR/venv"
    python3 -m venv "$APP_DIR/venv"
fi
PIP="$APP_DIR/venv/bin/pip"
"$PIP" install --upgrade pip wheel setuptools >/dev/null
# 后端运行依赖
"$PIP" install -r "$APP_DIR/backend/requirements.txt"
# 生产 WSGI 服务器（纯 Python gthread，无需 gevent）
"$PIP" install "gunicorn>=21.0.0"

# ---------------------------- 4. 权限 ----------------------------------------
log "步骤 4/8  修正目录权限"
mkdir -p "$APP_DIR/backend/logs"
# 应用目录归属运行用户（服务以 $APP_USER 身份运行）
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod 750 "$APP_DIR"
chmod 640 "$APP_DIR/.env"
# 让 nginx(www-data) 能读取 home 下的 dist：逐级放开目录穿越位 + 文件可读
P="$APP_DIR/front/dist"
while [ "$P" != "/" ]; do chmod o+x "$P" 2>/dev/null || true; P="$(dirname "$P")"; done
chmod -R a+rX "$APP_DIR/front/dist"

# ---------------------------- 5. systemd: 后端/worker/beat -------------------
log "步骤 5/8  安装 systemd 服务"
VENV_BIN="$APP_DIR/venv/bin"

cat > /etc/systemd/system/szagent-backend.service <<EOF
[Unit]
Description=Shangzhou Backend (gunicorn)
After=network-online.target redis-server.service
Wants=redis-server.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR/backend
EnvironmentFile=$APP_DIR/.env
ExecStart=$VENV_BIN/gunicorn -w 4 -k gthread --threads 8 -b 127.0.0.1:$BACKEND_PORT --timeout 120 "app:app"
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/szagent-worker.service <<EOF
[Unit]
Description=Shangzhou Celery Worker
After=network-online.target redis-server.service
Wants=redis-server.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR/backend
EnvironmentFile=$APP_DIR/.env
ExecStart=$VENV_BIN/celery -A tasks.celery_app worker -Q celery,workflow,embedding,scheduled --loglevel=info
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/szagent-beat.service <<EOF
[Unit]
Description=Shangzhou Celery Beat
After=network-online.target redis-server.service
Wants=redis-server.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR/backend
EnvironmentFile=$APP_DIR/.env
ExecStart=$VENV_BIN/celery -A tasks.celery_app beat --loglevel=info
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Qdrant systemd 服务（本机二进制 /usr/local/bin/qdrant）
if [ "$QDRANT_ENABLE" = "1" ] && [ -x /usr/local/bin/qdrant ]; then
    mkdir -p /var/lib/qdrant/config
    cat > /var/lib/qdrant/config/config.yaml <<QEOF
storage:
  storage_path: /var/lib/qdrant/storage
  snapshots_path: /var/lib/qdrant/snapshots
service:
  host: 0.0.0.0
  http_port: 6333
  grpc_port: 6334
QEOF
    cat > /etc/systemd/system/qdrant.service <<UEOF
[Unit]
Description=Qdrant Vector Database
After=network.target

[Service]
Type=simple
WorkingDirectory=/var/lib/qdrant
ExecStart=/usr/local/bin/qdrant
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UEOF
fi

# ---------------------------- 6. Nginx 站点（避让 80/443）-------------------
log "步骤 6/8  配置 Nginx (监听 $HTTP_PORT)"
cat > /etc/nginx/sites-available/szagent <<EOF
server {
    listen $HTTP_PORT;
    listen [::]:$HTTP_PORT;
    server_name _;

    root $APP_DIR/front/dist;
    index index.html;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # 前端 SPA：静态优先，回退 index.html
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:$BACKEND_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 600s;
        proxy_buffering off;         # 支持 SSE 流式
    }

    # WebSocket / Socket.IO
    location /socket.io {
        proxy_pass http://127.0.0.1:$BACKEND_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_read_timeout 3600s;
    }
}
EOF
ln -sf /etc/nginx/sites-available/szagent /etc/nginx/sites-enabled/szagent
rm -f /etc/nginx/sites-enabled/default   # 避让默认站点，防止 server_name 冲突
nginx -t

# ---------------------------- 7. 启动服务 ------------------------------------
log "步骤 7/8  启动服务"
systemctl daemon-reload
systemctl enable --now redis-server >/dev/null 2>&1 || true
# Qdrant（本机二进制，systemd 管理）
if [ "$QDRANT_ENABLE" = "1" ]; then
    if [ -x /usr/local/bin/qdrant ]; then
        systemctl enable --now qdrant >/dev/null 2>&1 || true
        systemctl restart qdrant || true
        log "Qdrant 已启动 (127.0.0.1:6333)"
    else
        warn "未找到 /usr/local/bin/qdrant，跳过（后端回退 MySQL 向量检索）"
    fi
fi
systemctl restart nginx
systemctl enable --now szagent-backend szagent-worker szagent-beat >/dev/null 2>&1 || true
systemctl restart szagent-backend szagent-worker szagent-beat || true

# ---------------------------- 8. 健康检查 ------------------------------------
log "步骤 8/8  健康检查"
ok=1
for i in $(seq 1 20); do
    if curl -fs -m 5 "http://127.0.0.1:$BACKEND_PORT/api/health" >/dev/null 2>&1; then break; fi
    sleep 2
done
if curl -fs -m 5 "http://127.0.0.1:$BACKEND_PORT/api/health"; then
    echo; log "后端健康检查通过"
else
    warn "后端健康检查失败，查看： journalctl -u szagent-backend -n 50"; ok=0
fi

if curl -fs -m 5 "http://127.0.0.1:$HTTP_PORT/" >/dev/null 2>&1; then
    log "前端可访问： http://$SERVER_IP:$HTTP_PORT/"
else
    warn "前端访问失败，查看： journalctl -u nginx -n 50; nginx -t"; ok=0
fi

echo
log "==================== 部署完成 ===================="
log "访问地址： http://$SERVER_IP:$HTTP_PORT/"
log "服务管理： systemctl status szagent-backend szagent-worker szagent-beat"
log "日志查看： journalctl -u szagent-backend -f"
log "=================================================="
[ "$ok" -eq 1 ] && exit 0 || exit 1
