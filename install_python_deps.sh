#!/bin/bash
# 智能安装 pip（Python3），如果已安装则跳过
# 适用于 Ubuntu/Debian

set -e

echo "========== 检测 pip 安装状态 =========="

# ---------- Python3 ----------
if command -v python3 >/dev/null 2>&1; then
    echo "✔ 检测到 Python3"
    PYTHON3_BIN=$(command -v python3)

    if "$PYTHON3_BIN" -m pip --version >/dev/null 2>&1; then
        echo "✔ pip 已安装：$("$PYTHON3_BIN" -m pip --version)"
    else
        echo "✘ pip 未安装，开始安装..."
        curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
        sudo "$PYTHON3_BIN" /tmp/get-pip.py
        rm -f /tmp/get-pip.py
        echo "✔ pip 安装完成：$("$PYTHON3_BIN" -m pip --version)"
    fi
else
    echo "✘ 未检测到 Python3"
    exit 1
fi

echo "========== pip 检测完成 ✅ =========="

echo
echo "========== 开始安装 Python 依赖 =========="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQUIREMENTS_FILE="${SCRIPT_DIR}/requirements.txt"

if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "✘ 未找到依赖文件：$REQUIREMENTS_FILE"
    exit 1
fi

echo "[1/2] Upgrading pip/setuptools/wheel..."
python3 -m pip install --upgrade pip setuptools wheel

echo "[2/2] Installing dependencies from requirements.txt..."
python3 -m pip install -r "$REQUIREMENTS_FILE"

echo "========== 所有依赖安装完成 ✅ =========="
