#!/usr/bin/env bash
set -euo pipefail

binary=${1:?usage: tests/zsh_integration.sh /path/to/zako}
binary=$(cd "$(dirname "$binary")" && pwd)/$(basename "$binary")
root=$(cd "$(dirname "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

mkdir -p "$tmp/bin" "$tmp/config"
ln -s "$binary" "$tmp/bin/zako"
cat > "$tmp/.zshrc" <<ZSH
source "$root/integrations/zako.zsh"
source "$root/integrations/zako.zsh"
ZSH

greeting=$(ZAKO_CONFIG_DIR="$tmp/config" "$binary" startup)
output=$(printf 'gti status\nzako fix\necho hello\nzako fix\nzako off\ntrue\nfalse\nprint -r -- "native-status=$?"\nexit\n' | PATH="$tmp/bin:$PATH" ZAKO_CONFIG_DIR="$tmp/config" ZDOTDIR="$tmp" zsh -di 2>&1)

test "$(printf '%s\n' "$output" | grep -c -F '建议：git status')" -eq 1
printf '%s\n' "$output" | grep -F 'Zako 已关闭。' >/dev/null
test -n "$greeting"
test "$(printf '%s\n' "$output" | grep -c -F "$greeting")" -eq 1
printf '%s\n' "$output" | grep -F 'native-status=1' >/dev/null
