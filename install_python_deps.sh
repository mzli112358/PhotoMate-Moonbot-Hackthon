#!/bin/bash
# 智能安装 Python3 pip 依赖 - 检测优先，根据环境类型决定是否确认
# 非系统 Python 直接安装，系统 Python 提示后确认安装

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "========== 检测 Python 环境 =========="

# ---------- Python3 ----------
if command -v python3 >/dev/null 2>&1; then
    PYTHON3_BIN=$(command -v python3)
    python_version=$("$PYTHON3_BIN" --version 2>&1)
    log_info "检测到 Python3: $python_version ($PYTHON3_BIN)"
else
    log_error "未检测到 Python3"
    exit 1
fi

# 检测是否为系统 Python
IS_SYSTEM_PYTHON=0
if [ "$PYTHON3_BIN" = "/usr/bin/python3" ] || [ "$PYTHON3_BIN" = "/bin/python3" ]; then
    IS_SYSTEM_PYTHON=1
fi

# 非系统 Python 直接安装，系统 Python 才需要确认
if [ $IS_SYSTEM_PYTHON -eq 0 ]; then
    log_info "检测到非系统 Python 环境，直接安装依赖..."
else
    log_warn "检测到系统 Python 环境，建议使用虚拟环境或 Conda 环境安装依赖"
    read -p "是否继续使用当前系统 Python 安装？[y/N] (默认取消): " install_confirm
    case "$install_confirm" in
        [yY][eE][sS]|[yY])
            log_info "继续使用系统 Python 安装..."
            ;;
        *)
            log_info "已取消安装"
            echo
            echo "后续手动安装方法："
            echo "  在虚拟环境或 Conda 环境中执行："
            echo "    pip install numpy scipy opencv-python open3d"
            echo
            exit 0
            ;;
    esac
fi

# ---------- 检测 pip ----------
if ! "$PYTHON3_BIN" -m pip --version >/dev/null 2>&1; then
    log_warn "pip 未安装，开始安装..."
    curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
    sudo "$PYTHON3_BIN" /tmp/get-pip.py
    rm -f /tmp/get-pip.py
    log_success "pip 安装完成"
fi
log_success "pip: $("$PYTHON3_BIN" -m pip --version)"

echo
echo "========== 检测依赖安装状态 =========="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQUIREMENTS_FILE="${SCRIPT_DIR}/requirements.txt"

if [ ! -f "$REQUIREMENTS_FILE" ]; then
    log_error "未找到依赖文件：$REQUIREMENTS_FILE"
    exit 1
fi

# 解析 requirements.txt，提取每个包的名称（去掉版本号）
MISSING_PKGS=()
ALL_PKGS=()

while IFS= read -r line || [ -n "$line" ]; do
    # 跳过空行和注释
    [[ -z "$line" || "$line" == \#* ]] && continue

    # 提取包名（去掉版本号，如 numpy>=1.24.4 → numpy）
    pkg_name=$(echo "$line" | sed 's/[<>=!].*//')

    # 跳过空行
    [ -z "$pkg_name" ] && continue

    # 特殊处理 opencv-python，实际 import 是 cv2
    if [ "$pkg_name" = "opencv-python" ]; then
        import_name="cv2"
    else
        import_name="$pkg_name"
    fi

    ALL_PKGS+=("$pkg_name")

    # 检测是否已安装（尝试 import）
    if "$PYTHON3_BIN" -c "import $import_name" 2>/dev/null; then
        log_success "✓ $pkg_name 已安装"
    else
        log_warn "✗ $pkg_name 未安装"
        MISSING_PKGS+=("$pkg_name")
    fi
done < "$REQUIREMENTS_FILE"

# 如果全部已安装，直接退出
if [ ${#MISSING_PKGS[@]} -eq 0 ]; then
    echo
    log_success "✅ 所有依赖已安装，跳过安装步骤"
    echo
    echo "直接使用 Python3 运行示例即可"
    exit 0
fi

echo
echo "========== 开始安装依赖 =========="
log_info "检测到 ${#MISSING_PKGS[@]} 个缺失的依赖：${MISSING_PKGS[*]}"

set +e
echo "正在安装依赖..."
"$PYTHON3_BIN" -m pip install "${MISSING_PKGS[@]}" 2>&1 | tee /tmp/pip_install.log
INSTALL_CODE=${PIPESTATUS[0]}
set -e

if [ $INSTALL_CODE -ne 0 ]; then
    echo
    if grep -qiE "cannot uninstall|installed by debian|RECORD file not found|externally-managed-environment" /tmp/pip_install.log; then
        log_warn "检测到系统 Python 包管理冲突（apt 与 pip 冲突）"
        echo
        echo "问题说明："
        echo "  • 当前解释器：$PYTHON3_BIN"
        echo "  • 失败原因：pip 尝试变更由 Debian/apt 管理的包，导致安装中断"
        echo
        echo "建议处理方式："
        echo "  1) 使用虚拟环境或 Conda 环境后再安装依赖"
        echo "  2) 重新执行 ./install_python_deps.sh，选择虚拟环境或 Conda 环境"
        echo "  3) 在新的 Python 环境中手动安装："
        echo "     python -m pip install ${MISSING_PKGS[*]}"
        echo
        if [ $IS_SYSTEM_PYTHON -eq 1 ]; then
            log_warn "当前为系统 Python，脚本已停止以避免误改系统环境"
        fi
        exit $INSTALL_CODE
    else
        log_error "依赖安装失败，请根据上方日志排查"
        exit $INSTALL_CODE
    fi
fi

echo
log_success "========== 所有依赖安装完成 ✅ =========="
