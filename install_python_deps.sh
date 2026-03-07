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

echo "[1/5] Installing numpy..."
python3 -m pip install numpy

echo "[2/5] Installing scipy..."
python3 -m pip install scipy

echo "[3/5] Installing open3d..."
python3 -m pip install open3d

echo "[4/5] Installing opencv-python..."
python3 -m pip install opencv-python

echo "[5/5] Re-installing numpy (ensure version)..."
python3 -m pip install numpy

echo "========== 所有依赖安装完成 ✅ =========="
