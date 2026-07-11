#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f vendor/GalbotSDK/galbot_sdk/linux-aarch64-gcc940/setup.sh ]]; then
  source vendor/GalbotSDK/galbot_sdk/linux-aarch64-gcc940/setup.sh
elif [[ -f vendor/GalbotSDK/galbot_sdk/linux-x86_64-gcc940/setup.sh ]]; then
  source vendor/GalbotSDK/galbot_sdk/linux-x86_64-gcc940/setup.sh
else
  echo "未找到 GalbotSDK setup.sh" >&2
  exit 1
fi

export PYTHONPATH="${ROOT}:${PYTHONPATH:-}"
chmod +x scripts/xbox_teleop.py
exec python3 scripts/xbox_teleop.py "$@"
