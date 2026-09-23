#!/usr/bin/env bash
# =============================================================================
#  熵舟·智能体工作台 —— Ubuntu 服务统一控制脚本 (V1.0)
#  与 Windows 端 start-all.bat / stop-all.bat / stop-front.bat / stop-backend.bat
#  对应，基于 systemd 管理各服务。
#
#  服务分组：
#    front    = nginx                         （托管前端 dist + 反向代理 /api）
#    backend  = szagent-backend (gunicorn)     + szagent-worker (Celery)
#               + szagent-beat   (Celery Beat)
#    infra    = redis-server, qdrant          （qdrant 缺失时自动跳过）
#    all      = infra + backend + front
#
#  用法：
#    sudo bash szagent-ctl.sh start   [all|backend|front|infra]   # 缺省 all
#    sudo bash szagent-ctl.sh stop    [all|backend|front|infra]   # 缺省 all
#    sudo bash szagent-ctl.sh restart [all|backend|front]         # 缺省 all
#    sudo bash szagent-ctl.sh status                              # 查看全部
#
#  一键命令对（示例）：
#    启动全部：  sudo bash scripts/szagent-ctl.sh start all
#    停止全部：  sudo bash scripts/szagent-ctl.sh stop  all
#    启动前端：  sudo bash scripts/szagent-ctl.sh start front
#    停止前端：  sudo bash scripts/szagent-ctl.sh stop  front
#    启动后端：  sudo bash scripts/szagent-ctl.sh start backend
#    停止后端：  sudo bash scripts/szagent-ctl.sh stop  backend
# =============================================================================
set -uo pipefail

# ---------------------------- 服务清单 ---------------------------------------
FRONT_UNITS=(nginx)
BACKEND_UNITS=(szagent-backend szagent-worker szagent-beat)
# 基础设施：redis 必需，qdrant 可选（未安装则跳过）
INFRA_UNITS=(redis-server qdrant)

# 需要 enable 的服务（保证开机自启 + 现在启动）；nginx 只 start/restart
ENABLE_ON_START=("${BACKEND_UNITS[@]}" redis-server qdrant)

log()  { echo -e "\033[1;36m[ctl]\033[0m $*"; }
warn() { echo -e "\033[1;33m[warn]\033[0m $*"; }
die()  { echo -e "\033[1;31m[error]\033[0m $*" >&2; exit 1; }

# ---------------------------- 前置校验 ---------------------------------------
# help / status 免 root；start|stop|restart 需 root（在下方入口处分派）

have_unit() { systemctl list-unit-files "$1.service" >/dev/null 2>&1 && \
    [ -n "$(systemctl list-unit-files "$1.service" 2>/dev/null | grep -F "$1.service")" ]; }

# 启动单个单元（容忍缺失：qdrant 可能未安装）
do_start() {
    local u="$1"
    if ! have_unit "$u"; then
        [ "$u" = "qdrant" ] && { warn "未安装 $u，跳过（后端将回退 MySQL 向量检索）"; return 0; }
        warn "未找到服务单元 $u.service，跳过"; return 0
    fi
    systemctl start "$u" && log "started: $u" || warn "启动失败: $u（查看 journalctl -u $u）"
}
do_stop() {
    local u="$1"
    have_unit "$u" || return 0
    systemctl stop "$u" && log "stopped: $u" || warn "停止失败: $u"
}
do_restart() {
    local u="$1"
    if ! have_unit "$u"; then warn "未找到 $u.service，跳过"; return 0; fi
    systemctl restart "$u" && log "restarted: $u" || warn "重启失败: $u"
}

# ---------------------------- 目标解析 ---------------------------------------
# 按 START/STOP 顺序返回单元数组（通过全局数组 RESULT 传递）
units_for() {
    case "$1" in
        front)   RESULT=("${FRONT_UNITS[@]}") ;;
        backend) RESULT=("${BACKEND_UNITS[@]}") ;;
        infra)   RESULT=("${INFRA_UNITS[@]}") ;;
        all)     RESULT=("${INFRA_UNITS[@]}" "${BACKEND_UNITS[@]}" "${FRONT_UNITS[@]}") ;;
        *)       die "未知目标：$1（可选 all|backend|front|infra）" ;;
    esac
}

# ---------------------------- 动作 -------------------------------------------
start_target() {
    local t="$1"; units_for "$t"
    log "启动 [$t] ..."
    for u in "${RESULT[@]}"; do do_start "$u"; done
    # 对需要的服务设置开机自启
    if [ "$t" = "all" ] || [ "$t" = "backend" ]; then
        for u in "${ENABLE_ON_START[@]}"; do have_unit "$u" && systemctl enable "$u" >/dev/null 2>&1 || true; done
    fi
}
stop_target() {
    local t="$1"; units_for "$t"
    # 停止用逆序：先 front，再 backend，最后 infra
    local rev=()
    local i
    for (( i=${#RESULT[@]}-1; i>=0; i-- )); do rev+=("${RESULT[i]}"); done
    log "停止 [$t] ..."
    for u in "${rev[@]}"; do do_stop "$u"; done
}
restart_target() {
    local t="$1"; units_for "$t"
    log "重启 [$t] ..."
    for u in "${RESULT[@]}"; do do_restart "$u"; done
}

show_status() {
    echo
    printf '%-22s %s\n' "UNIT" "STATE"
    printf '%.0s-' {1..34}; echo
    local groups=("infra:${INFRA_UNITS[*]}" "backend:${BACKEND_UNITS[*]}" "front:${FRONT_UNITS[*]}")
    local g
    for g in "${groups[@]}"; do
        local label="${g%%:*}"; local us="${g#*:}"
        echo "[$label]"
        for u in $us; do
            if ! have_unit "$u"; then printf '  %-20s %s\n' "$u" "(未安装)"; continue; fi
            local st; st=$(systemctl is-active "$u" 2>/dev/null || true)
            printf '  %-20s %s\n' "$u" "${st:-unknown}"
        done
    done
    echo
}

# ---------------------------- 入口 -------------------------------------------
ACTION="${1:-}"; TARGET="${2:-all}"
# 帮助信息（无需 root）
case "$ACTION" in
    ""|"-h"|"--help"|"help")
        grep -E '^#( |$)' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
esac
# 变更类动作需 root
if [ "$ACTION" != "status" ]; then
    [ "$(id -u)" -eq 0 ] || die "请以 root 运行：sudo bash $0 ..."
fi
case "$ACTION" in
    start)   start_target "$TARGET" ;;
    stop)    stop_target  "$TARGET" ;;
    restart) restart_target "$TARGET" ;;
    status)  show_status ;;
    *) die "未知动作：$ACTION（可用 start|stop|restart|status）" ;;
esac

[ "$ACTION" = "status" ] || { echo; show_status; }
