#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f vendor/GalbotSDK/galbot_sdk/linux-aarch64-gcc940/setup.sh ]]; then
  # Jetson / 机载 aarch64
  source vendor/GalbotSDK/galbot_sdk/linux-aarch64-gcc940/setup.sh
elif [[ -f vendor/GalbotSDK/galbot_sdk/linux-x86_64-gcc940/setup.sh ]]; then
  source vendor/GalbotSDK/galbot_sdk/linux-x86_64-gcc940/setup.sh
fi

export PYTHONPATH="${ROOT}:${PYTHONPATH:-}"

# 真机：export PHOTOMATE_MOCK=false
# 开发机无机器人：默认 mock（config/app.yaml）
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port "${PHOTOMATE_PORT:-8000}" --reload
