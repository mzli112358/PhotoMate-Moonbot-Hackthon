#!/usr/bin/env bash
# 运行本地 galbot_sdk 镜像
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VERSION="$(tr -d ' \n\r' < "${PROJECT_ROOT}/VERSION")"
IMAGE="galbot/galbot_sdk:${VERSION}"
LEGACY_IMAGE="galbot_sdk:${VERSION}"
HOST_HOME="${HOME:?未设置 HOME}"
COMPOSE_FILE="${SCRIPT_DIR}/compose.yaml"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    echo "用法: $0"
    echo "  将使用 ${COMPOSE_FILE} 启动容器"
    echo "  镜像: ${IMAGE} (兼容 ${LEGACY_IMAGE})"
    echo "  或按本机架构自动选择 -x86_64 / -arm64 后缀镜像"
    exit 0
fi

RUN_IMAGE=""
if docker image inspect "${IMAGE}" &>/dev/null; then
    RUN_IMAGE="${IMAGE}"
elif docker image inspect "${LEGACY_IMAGE}" &>/dev/null; then
    RUN_IMAGE="${LEGACY_IMAGE}"
else
    case "$(uname -m)" in
        x86_64)
            docker image inspect "${IMAGE}-x86_64" &>/dev/null && RUN_IMAGE="${IMAGE}-x86_64"
            [[ -z "${RUN_IMAGE}" ]] && docker image inspect "${LEGACY_IMAGE}-x86_64" &>/dev/null && RUN_IMAGE="${LEGACY_IMAGE}-x86_64"
            ;;
        aarch64|arm64)
            docker image inspect "${IMAGE}-arm64" &>/dev/null && RUN_IMAGE="${IMAGE}-arm64"
            [[ -z "${RUN_IMAGE}" ]] && docker image inspect "${LEGACY_IMAGE}-arm64" &>/dev/null && RUN_IMAGE="${LEGACY_IMAGE}-arm64"
            ;;
    esac
fi
if [[ -z "${RUN_IMAGE}" ]]; then
    echo "[错误] 未找到 ${IMAGE}（或兼容镜像 ${LEGACY_IMAGE}）" >&2
    exit 1
fi

export GALBOT_DOCKER_IMAGE="${RUN_IMAGE}"
export GALBOT_DOCKER_UID="$(id -u)"
export GALBOT_DOCKER_GID="$(id -g)"
export GALBOT_DOCKER_USER="$(id -un)"
export GALBOT_DOCKER_HOME="${HOST_HOME}"
export GALBOT_DOCKER_DISPLAY="${DISPLAY:-}"

if ! docker compose version &>/dev/null; then
    echo "[错误] 未找到「docker compose」插件，请安装 Docker Compose" >&2
    exit 1
fi

exec docker compose -f "${COMPOSE_FILE}" run --rm -it galbot_sdk
