#!/bin/bash
# 安装 / 更新 systemd 用户服务 transtool-py（不需要 sudo，首次需管理员开启 linger 一次）
# 用法：deploy/install_service.sh    可用环境变量 MEMORY_HIGH / MEMORY_MAX 覆盖内存上限
set -e

APP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_DIR="$HOME/.config/systemd/user"
UNIT="$UNIT_DIR/transtool-py.service"
MEMORY_HIGH="${MEMORY_HIGH:-900M}"
MEMORY_MAX="${MEMORY_MAX:-1100M}"

case "$APP_ROOT" in
    *'|'*) echo "错误：安装路径不能包含 | 字符：$APP_ROOT" >&2; exit 1 ;;
esac

mkdir -p "$UNIT_DIR" "$APP_ROOT/logs"
sed -e "s|__APP_ROOT__|$APP_ROOT|g" \
    -e "s|__MEMORY_HIGH__|$MEMORY_HIGH|g" \
    -e "s|__MEMORY_MAX__|$MEMORY_MAX|g" \
    "$APP_ROOT/deploy/transtool-py.service.template" > "$UNIT"

systemctl --user daemon-reload
systemctl --user enable transtool-py.service >/dev/null
echo "已安装：$UNIT（MemoryHigh=$MEMORY_HIGH MemoryMax=$MEMORY_MAX）"

if [ "$(loginctl show-user "$USER" -p Linger --value 2>/dev/null)" != "yes" ]; then
    echo ""
    echo "注意：尚未开启 linger，退出登录或重启后服务不会自动运行。请执行一次："
    echo "    sudo loginctl enable-linger $USER"
fi

# 用户服务的内存上限依赖 cgroup v2 把 memory 控制器委派给用户管理器，否则 MemoryMax 会被静默忽略
USER_CG="/sys/fs/cgroup/user.slice/user-$(id -u).slice/user@$(id -u).service/cgroup.controllers"
if [ -r "$USER_CG" ] && ! grep -qw memory "$USER_CG"; then
    echo ""
    echo "注意：当前用户的 systemd 未启用 memory 控制器，MemoryHigh/MemoryMax 不会生效。"
    echo "可由管理员创建 /etc/systemd/system/user@.service.d/delegate.conf，内容："
    echo "    [Service]"
    echo "    Delegate=cpu cpuset io memory pids"
    echo "然后执行 sudo systemctl daemon-reload 并重新登录。"
fi
