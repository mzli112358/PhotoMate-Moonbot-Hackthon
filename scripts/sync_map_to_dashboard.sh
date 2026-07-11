#!/usr/bin/env bash
# 将机载最新地图同步到 Dashboard 显示目录，并通知后端重载。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${1:-/var/maps/room1102/global_cloud_cleaned.pcd}"
DST="$ROOT/data/maps/global_cloud.pcd"

if [[ ! -f "$SRC" ]]; then
  echo "源地图不存在: $SRC" >&2
  exit 1
fi

cp "$SRC" "$DST"
echo "已同步: $SRC -> $DST ($(du -h "$DST" | cut -f1))"

RELOAD_URL="http://127.0.0.1:${PHOTOMATE_PORT:-8000}/api/map/reload"
if command -v curl >/dev/null 2>&1 && curl -sf -X POST "$RELOAD_URL" >/dev/null 2>&1; then
  echo "Dashboard 地图缓存已重载"
elif python3 - "$RELOAD_URL" <<'PY' 2>/dev/null
import sys
import urllib.request
urllib.request.urlopen(
    urllib.request.Request(sys.argv[1], method="POST", data=b""),
    timeout=10,
)
PY
then
  echo "Dashboard 地图缓存已重载"
else
  echo "Dashboard 未运行，启动后地图会自动读取新文件"
fi
