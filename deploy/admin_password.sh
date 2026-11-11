#!/bin/bash
# 管理页（croky.html）登录账号管理。密码文件只有 root 能改，需用 sudo 运行。
#
# 用法：
#   sudo deploy/admin_password.sh                设置 / 重设 admin 的密码（忘记密码时用这个）
#   sudo deploy/admin_password.sh 用户名         设置 / 重设指定账号的密码（不存在就新增）
#   sudo deploy/admin_password.sh --list         列出所有账号
#   sudo deploy/admin_password.sh --delete 用户名  删除账号
#
# 改动立即生效，不用重载 nginx。文件里只存密码的 SHA-512 哈希，不存原文。
set -euo pipefail

HTPASSWD_FILE="${HTPASSWD_FILE:-/etc/nginx/transtool-py.htpasswd}"
NGINX_GROUP="${NGINX_GROUP:-www-data}"   # nginx 运行时的用户组，需要能读这个文件

die() { echo "错误：$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "需要 root 权限，请用 sudo 运行"

valid_user() {
    [[ "$1" =~ ^[A-Za-z0-9._-]{1,32}$ ]] || die "账号名只能用英文字母、数字和 . _ -（最长 32 个字符）：$1"
}

list_users() {
    if [ ! -s "$HTPASSWD_FILE" ]; then
        echo "还没有任何账号"
        return
    fi
    echo "现有账号："
    cut -d: -f1 "$HTPASSWD_FILE" | sed 's/^/  /'
}

# 把「去掉某账号后的内容 + 可选的新行」原子写回密码文件，并保持权限 root:nginx组 640
write_file() {
    local user="$1" new_line="$2" tmp
    tmp="$(mktemp "$(dirname "$HTPASSWD_FILE")/.htpasswd.XXXXXX")"
    trap 'rm -f "$tmp"' EXIT
    if [ -f "$HTPASSWD_FILE" ]; then
        grep -v "^${user}:" "$HTPASSWD_FILE" > "$tmp" || true
    fi
    if [ -n "$new_line" ]; then
        printf '%s\n' "$new_line" >> "$tmp"
    fi
    chown "root:$NGINX_GROUP" "$tmp"
    chmod 640 "$tmp"
    mv "$tmp" "$HTPASSWD_FILE"
    trap - EXIT
}

set_password() {
    local user="$1" pw1 pw2 hash
    valid_user "$user"
    read -r -s -p "请输入 $user 的新密码：" pw1; echo
    read -r -s -p "请再输入一次：" pw2; echo
    [ -n "$pw1" ] || die "密码不能为空"
    [ "$pw1" = "$pw2" ] || die "两次输入的密码不一致，没有做任何修改"
    hash="$(printf '%s' "$pw1" | openssl passwd -6 -stdin)"
    unset pw1 pw2
    [[ "$hash" == '$6$'* ]] || die "生成密码哈希失败，没有做任何修改"

    local action="已新增"
    if [ -f "$HTPASSWD_FILE" ] && grep -q "^${user}:" "$HTPASSWD_FILE"; then
        action="已重设"
    fi
    write_file "$user" "${user}:${hash}"
    echo "${action}账号 $user 的密码，立即生效。"
}

delete_user() {
    local user="$1"
    valid_user "$user"
    [ -f "$HTPASSWD_FILE" ] && grep -q "^${user}:" "$HTPASSWD_FILE" || die "没有这个账号：$user"
    write_file "$user" ""
    echo "已删除账号 $user。"
    if [ ! -s "$HTPASSWD_FILE" ]; then
        echo "注意：现在没有任何账号，管理页将无法登录。"
    fi
}

case "${1:-}" in
    --list)   list_users ;;
    --delete) [ -n "${2:-}" ] || die "请指定要删除的账号：--delete 用户名"; delete_user "$2" ;;
    --help|-h) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//' ;;
    -*)       die "不认识的参数：$1（用 --help 查看用法）" ;;
    *)        set_password "${1:-admin}" ;;
esac
