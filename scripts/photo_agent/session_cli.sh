#!/usr/bin/env bash
# Remote session control for headless Jetson (no kiosk click needed).
#
# Usage (on Jetson, after uvicorn is running):
#   ./scripts/photo_agent/session_cli.sh start
#   ./scripts/photo_agent/session_cli.sh stop
#   ./scripts/photo_agent/session_cli.sh status
#
# From your laptop over SSH:
#   ssh jetson 'cd PhotoMate-Moonbot-Hackthon && ./scripts/photo_agent/session_cli.sh start'
#
# Override backend URL:
#   PHOTOMATE_API=http://127.0.0.1:8000 ./scripts/photo_agent/session_cli.sh start

set -euo pipefail

API="${PHOTOMATE_API:-http://127.0.0.1:8000}"
CMD="${1:-status}"

case "$CMD" in
  start)
    curl -sfS -X POST "${API}/api/photo-agent/session/start" \
      -H "Content-Type: application/json" \
      -d "${2:-{}}" | python3 -m json.tool
    ;;
  stop)
    curl -sfS -X POST "${API}/api/photo-agent/session/stop" | python3 -m json.tool
    ;;
  status)
    curl -sfS "${API}/api/photo-agent/session/state" | python3 -m json.tool
    ;;
  *)
    echo "Usage: $0 {start|stop|status} [json-body-for-start]" >&2
    exit 1
    ;;
esac
