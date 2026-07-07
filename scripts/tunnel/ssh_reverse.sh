#!/usr/bin/env bash
# Jetson 上：SSH 反向隧道（临时演示，需 autossh 保活）
# 用法：VPS=user@1.2.3.4 ./scripts/tunnel/ssh_reverse.sh

set -euo pipefail
VPS="${VPS:?设置环境变量 VPS，例如 user@1.2.3.4}"
LOCAL_PORT="${LOCAL_PORT:-8000}"
REMOTE_BIND="${REMOTE_BIND:-18000}"

echo "隧道: VPS 127.0.0.1:${REMOTE_BIND} -> 本机 127.0.0.1:${LOCAL_PORT}"
echo "请先在另一终端运行 ./scripts/run_dashboard.sh"
exec ssh -N \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -R "127.0.0.1:${REMOTE_BIND}:127.0.0.1:${LOCAL_PORT}" \
  "$VPS"
