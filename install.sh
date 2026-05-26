#!/bin/bash
#
# install.sh - GALBOT_G1_SDK 增量安装脚本
#
# 功能：
# 1. 读取 deps/*.json 获取依赖声明
# 2. 通过校验缓存压缩包的 SHA256 判断哪些依赖需要更新
# 3. 下载/复制并安装需要更新的依赖（保存到 .cache/ 目录）
# 4. 安装 SDK 核心库
#
# 缓存机制：
# - 所有下载的压缩包都保存在 $INSTALL_DIR/.cache/ 目录
# - 每次安装前会校验缓存文件的实际 SHA256 值
# - 如果校验失败或缓存不存在，则重新下载
#
# 用法：
#   ./install.sh [选项]
#
# 选项：
#   --platform <platform>   指定目标平台（如 linux-aarch64-gcc940）
#   --install-dir <path>    安装目录（默认 /opt/galbot）
#   --check                 仅校验版本，不下载或安装
#   --force                 强制重新下载所有依赖
#   --offline               禁止网络访问，仅使用已安装的依赖
#   -y, --yes               非交互模式，使用默认值
#   -h, --help              显示帮助信息
#

set -e

# 脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# SDK 源目录（用于本地模式查找依赖压缩包）
# 可通过环境变量 SDK_SOURCE_DIR 指定，用于本地测试
if [ -n "$SDK_SOURCE_DIR" ]; then
    # 使用环境变量指定的目录
    :
elif [ -d "$SCRIPT_DIR/deps/toolchain/releases" ] || [ -d "$SCRIPT_DIR/deps/third_party/releases" ]; then
    # 当前目录下有完整的 deps 结构（包含压缩包）
    SDK_SOURCE_DIR="$SCRIPT_DIR"
elif [ -d "$SCRIPT_DIR/../deps/toolchain/releases" ] || [ -d "$SCRIPT_DIR/../deps/third_party/releases" ]; then
    # 父目录下有完整的 deps 结构（本地测试模式，install.sh 在 output/ 下）
    SDK_SOURCE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
elif [ -d "$SCRIPT_DIR/deps" ]; then
    # 当前目录有 deps（可能只有 JSON，用于在线下载模式）
    SDK_SOURCE_DIR="$SCRIPT_DIR"
else
    SDK_SOURCE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

# 默认值
DEFAULT_INSTALL_DIR="/opt/galbot"
SDK_VERSION="1.7.2"
EMBOSA_LOG_DIR="/userdata/log/embosa"

# 参数
INSTALL_DIR=""
TARGET_PLATFORM=""
ALL_PLATFORMS=true  # 默认安装所有平台
CHECK_ONLY=false
FORCE_INSTALL=false
OFFLINE_MODE=false
NON_INTERACTIVE=false
USE_SUDO=true

# 所有支持的平台
SUPPORTED_PLATFORMS=("linux-aarch64-gcc940" "linux-x86_64-gcc940")

# 颜色输出
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

# sudo 包装函数
run_cmd() {
    if [ "$USE_SUDO" = true ]; then
        sudo "$@"
    else
        "$@"
    fi
}

show_help() {
    cat << EOF
GALBOT_G1_SDK 安装程序 v${SDK_VERSION}

用法: ./install.sh [选项]

选项:
  --platform <platform>   指定单个目标平台（覆盖默认的所有平台安装）
                          可选值: linux-aarch64-gcc940, linux-x86_64-gcc940
  --single-platform       只安装当前检测到的平台（覆盖默认的所有平台安装）
  --all-platforms         安装所有平台（默认行为，用于交叉编译）
  --install-dir <path>    安装目录（默认: $DEFAULT_INSTALL_DIR）
  --sdk-source <path>     SDK 源目录（用于本地测试，从此目录读取 deps/releases）
  --check                 仅校验版本，不下载或安装
  --force                 强制重新下载所有依赖
  --offline               离线模式，仅使用已安装的依赖
  --no-sudo               不使用 sudo（用于测试或无权限环境）
  -y, --yes               非交互模式，使用默认值
  -h, --help              显示帮助信息

环境变量:
  SDK_SOURCE_DIR          等同于 --sdk-source，用于本地测试

示例:
  ./install.sh                                    # 交互式安装（默认安装所有平台）
  ./install.sh -y                                 # 使用默认值安装（所有平台）
  ./install.sh --single-platform                 # 只安装当前检测到的平台
  ./install.sh --platform linux-x86_64-gcc940    # 只安装指定平台
  ./install.sh --install-dir /home/user/galbot   # 指定安装目录
  ./install.sh --check                            # 仅检查版本
  ./install.sh --sdk-source /path/to/sdk_source  # 本地测试，使用本地依赖
EOF
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --platform)
                TARGET_PLATFORM="$2"
                ALL_PLATFORMS=false  # 指定平台时，只安装该平台
                shift 2
                ;;
            --install-dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            --sdk-source)
                SDK_SOURCE_DIR="$2"
                shift 2
                ;;
            --all-platforms)
                ALL_PLATFORMS=true
                shift
                ;;
            --single-platform)
                ALL_PLATFORMS=false
                shift
                ;;
            --check)
                CHECK_ONLY=true
                shift
                ;;
            --force)
                FORCE_INSTALL=true
                shift
                ;;
            --offline)
                OFFLINE_MODE=true
                shift
                ;;
            -y|--yes)
                NON_INTERACTIVE=true
                shift
                ;;
            --no-sudo)
                USE_SUDO=false
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# 检测系统架构
detect_platform() {
    local arch=$(uname -m)
    case $arch in
        x86_64)
            echo "linux-x86_64-gcc940"
            ;;
        aarch64|arm64)
            echo "linux-aarch64-gcc940"
            ;;
        *)
            log_error "不支持的架构: $arch"
            exit 1
            ;;
    esac
}

# 获取工具链名称
get_toolchain_name() {
    local platform=$1
    case $platform in
        linux-aarch64-gcc940)
            echo "gcc940-aarch64-ubuntu2004-gnu"
            ;;
        linux-x86_64-gcc940)
            echo "gcc940-x86_64-ubuntu2004-gnu"
            ;;
        *)
            log_error "未知平台: $platform"
            exit 1
            ;;
    esac
}

# 下载或复制文件
download_file() {
    local url=$1
    local local_path=$2
    local output_file=$3
    local expected_sha256=$4
    
    # 优先使用本地路径
    if [ -n "$local_path" ] && [ -f "$SDK_SOURCE_DIR/$local_path" ]; then
        log_info "  从本地复制: $local_path"
        cp "$SDK_SOURCE_DIR/$local_path" "$output_file"
    elif [ "$OFFLINE_MODE" = true ]; then
        log_error "  离线模式下无法获取文件"
        return 1
    elif [ -z "$url" ]; then
        # URL 为空，且本地文件不存在
        log_error "  URL 为空，且本地文件不存在: $local_path"
        return 1
    else
        log_info "  下载: $url"
        if command -v curl &> /dev/null; then
            curl -L -o "$output_file" "$url" --progress-bar
        elif command -v wget &> /dev/null; then
            wget -O "$output_file" "$url"
        else
            log_error "  未找到 curl 或 wget"
            return 1
        fi
    fi
    
    # 校验 sha256
    if [ -n "$expected_sha256" ]; then
        local actual_sha256=$(sha256sum "$output_file" | cut -d' ' -f1)
        if [ "$actual_sha256" != "$expected_sha256" ]; then
            log_error "  SHA256 校验失败!"
            log_error "    期望: $expected_sha256"
            log_error "    实际: $actual_sha256"
            run_cmd rm -f "$output_file"
            return 1
        fi
        log_success "  SHA256 校验通过"
    fi
    
    return 0
}

# 检查是否需要更新工具链
# 通过校验缓存的压缩包 sha256 来判断
needs_toolchain_update() {
    local toolchain_name=$1
    local expected_sha256=$2
    local cache_dir="$INSTALL_DIR/.cache"
    local cached_file="$cache_dir/${toolchain_name}.tar.gz"
    
    if [ "$FORCE_INSTALL" = true ]; then
        return 0
    fi
    
    # 检查缓存的压缩包是否存在
    if [ ! -f "$cached_file" ]; then
        log_info "  缓存不存在: ${toolchain_name}.tar.gz"
        return 0
    fi
    
    # 计算缓存压缩包的实际 sha256
    log_info "  校验缓存: ${toolchain_name}.tar.gz ..."
    local actual_sha256=$(sha256sum "$cached_file" | cut -d' ' -f1)
    
    if [ "$actual_sha256" != "$expected_sha256" ]; then
        log_warn "  缓存校验失败，需要重新下载"
        log_warn "    期望: ${expected_sha256:0:16}..."
        log_warn "    实际: ${actual_sha256:0:16}..."
        return 0
    fi
    
    # 检查工具链是否已安装
    local toolchain_dir="$INSTALL_DIR/toolchain/$toolchain_name"
    if [ ! -d "$toolchain_dir" ]; then
        log_info "  工具链目录不存在，需要安装"
        return 0
    fi
    
    # 缓存存在且校验通过，无需更新
    return 1
}

# 检查是否需要更新三方库
# 通过校验缓存的压缩包 sha256 来判断
needs_thirdparty_update() {
    local pkg_name=$1
    local platform=$2
    local expected_sha256=$3
    local version=$4
    local cache_dir="$INSTALL_DIR/.cache"
    local cached_file="$cache_dir/${pkg_name}-${version}-${platform}.tar.gz"
    
    if [ "$FORCE_INSTALL" = true ]; then
        return 0
    fi
    
    # 检查缓存的压缩包是否存在
    if [ ! -f "$cached_file" ]; then
        return 0
    fi
    
    # 计算缓存压缩包的实际 sha256
    local actual_sha256=$(sha256sum "$cached_file" | cut -d' ' -f1)
    
    if [ "$actual_sha256" != "$expected_sha256" ]; then
        log_warn "  $pkg_name 缓存校验失败，需要重新下载"
        return 0
    fi
    
    # 缓存存在且校验通过，无需更新
    return 1
}

# 安装工具链（单平台）
install_toolchain_for_platform() {
    local platform=$1
    local toolchain_json=""
    
    if [ -f "$SCRIPT_DIR/deps/toolchain.json" ]; then
        toolchain_json="$SCRIPT_DIR/deps/toolchain.json"
    else
        log_warn "未找到 toolchain.json，跳过工具链安装"
        return 0
    fi
    
    log_info "处理工具链 (平台: $platform)..."
    
    local toolchain_name=$(get_toolchain_name "$platform")
    
    # 解析工具链信息
    local toolchain_info=$(python3 -c "
import json
data = json.load(open('$toolchain_json'))
for tc in data.get('toolchains', []):
    if tc.get('target_platform') == '$platform':
        print(json.dumps(tc))
        break
" 2>/dev/null)
    
    if [ -z "$toolchain_info" ]; then
        log_warn "未找到平台 $platform 的工具链配置"
        return 0
    fi
    
    local url=$(echo "$toolchain_info" | python3 -c "import json,sys; print(json.load(sys.stdin).get('url', ''))")
    local local_path=$(echo "$toolchain_info" | python3 -c "import json,sys; print(json.load(sys.stdin).get('local_path', ''))")
    local sha256=$(echo "$toolchain_info" | python3 -c "import json,sys; print(json.load(sys.stdin).get('sha256', ''))")
    local version=$(echo "$toolchain_info" | python3 -c "import json,sys; print(json.load(sys.stdin).get('version', ''))")
    
    # 缓存目录和缓存文件路径
    local cache_dir="$INSTALL_DIR/.cache"
    local cached_file="$cache_dir/${toolchain_name}.tar.gz"
    
    if needs_toolchain_update "$toolchain_name" "$sha256"; then
        if [ "$CHECK_ONLY" = true ]; then
            log_info "  需要更新: $toolchain_name (v$version)"
            return 0
        fi
        
        log_info "  安装工具链: $toolchain_name (v$version)"
        
        # 创建缓存目录
        run_cmd mkdir -p "$cache_dir"
        
        # 下载到缓存目录
        local tmp_file=$(mktemp)
        
        if ! download_file "$url" "$local_path" "$tmp_file" "$sha256"; then
            log_error "  工具链下载失败"
            run_cmd rm -f "$tmp_file"
            return 1
        fi
        
        # 移动到缓存目录
        run_cmd mv "$tmp_file" "$cached_file"
        
        # 解压到安装目录
        local toolchain_dir="$INSTALL_DIR/toolchain"
        run_cmd mkdir -p "$toolchain_dir"
        
        log_info "  解压到 $toolchain_dir/"
        run_cmd tar xzf "$cached_file" -C "$toolchain_dir" --no-same-owner
        
        log_success "  工具链安装完成: $toolchain_name"
    else
        log_success "  工具链校验通过，已是最新: $toolchain_name"
    fi
}

# 安装工具链（支持多平台）
install_toolchain() {
    if [ "$ALL_PLATFORMS" = true ]; then
        log_info "安装所有平台的工具链..."
        for platform in "${SUPPORTED_PLATFORMS[@]}"; do
            install_toolchain_for_platform "$platform"
            echo
        done
    else
        install_toolchain_for_platform "$TARGET_PLATFORM"
    fi
}

# 安装三方库（单平台）
install_thirdparty_for_platform() {
    local platform=$1
    local thirdparty_json=""
    
    if [ -f "$SCRIPT_DIR/deps/third_party.json" ]; then
        thirdparty_json="$SCRIPT_DIR/deps/third_party.json"
    else
        log_warn "未找到 third_party.json，跳过三方库安装"
        return 0
    fi
    
    log_info "处理三方库 (平台: $platform)..."
    
    # 获取所有包
    local packages=$(python3 -c "
import json
data = json.load(open('$thirdparty_json'))
for pkg in data.get('packages', []):
    name = pkg.get('name', '')
    version = pkg.get('version', '')
    pattern = pkg.get('pattern', '')
    platform_info = pkg.get('platforms', {}).get('$platform', {})
    if platform_info:
        url = platform_info.get('url', '')
        local_path = platform_info.get('local_path', '')
        sha256 = platform_info.get('sha256', '')
        print(f'{name}|{version}|{url}|{local_path}|{sha256}|{pattern}')
" 2>/dev/null)
    
    local lib_dir="$INSTALL_DIR/galbot_sdk/$platform/lib"
    local cache_dir="$INSTALL_DIR/.cache"
    
    while IFS='|' read -r name version url local_path sha256 pattern; do
        [ -z "$name" ] && continue
        
        local cached_file="$cache_dir/${name}-${version}-${platform}.tar.gz"
        
        if needs_thirdparty_update "$name" "$platform" "$sha256" "$version"; then
            if [ "$CHECK_ONLY" = true ]; then
                log_info "  需要更新: $name (v$version)"
                continue
            fi
            
            log_info "  安装: $name (v$version)"
            
            # 创建缓存目录
            run_cmd mkdir -p "$cache_dir"
            
            # 清理该库的旧版本缓存（保留当前版本）
            for old_cache in "$cache_dir/${name}"-*-"${platform}.tar.gz"; do
                if [ -f "$old_cache" ] && [ "$old_cache" != "$cached_file" ]; then
                    log_info "  清理旧版本缓存: $(basename "$old_cache")"
                    run_cmd rm -f "$old_cache"
                fi
            done
            
            # 下载到临时目录
            local tmp_file=$(mktemp)
            
            if ! download_file "$url" "$local_path" "$tmp_file" "$sha256"; then
                log_error "  $name 下载失败"
                run_cmd rm -f "$tmp_file"
                continue
            fi
            
            # 移动到缓存目录
            run_cmd mv "$tmp_file" "$cached_file"
            
            # 清理旧版本文件（在解压前）
            # 从 JSON 中读取 pattern，如果没有则使用默认规则
            local lib_pattern="$pattern"
            if [ -z "$lib_pattern" ]; then
                # 默认模式：lib{name}*
                lib_pattern="lib${name}*"
            fi
            
            if [ -n "$lib_pattern" ] && [ -d "$lib_dir" ]; then
                log_info "  清理旧版本文件: $lib_pattern"
                # 查找并删除匹配的文件（包括符号链接）
                find "$lib_dir" -maxdepth 1 \( -type f -o -type l \) -name "$lib_pattern" -exec rm -f {} \; 2>/dev/null || true
            fi
            
            # 解压到 lib 目录
            run_cmd mkdir -p "$lib_dir"
            run_cmd tar xzf "$cached_file" -C "$lib_dir" --strip-components=1 --no-same-owner
            
            log_success "  $name 安装完成"
        else
            log_success "  校验通过: $name"
        fi
    done <<< "$packages"
}

# 安装三方库（支持多平台）
install_thirdparty() {
    if [ "$ALL_PLATFORMS" = true ]; then
        log_info "安装所有平台的三方库..."
        for platform in "${SUPPORTED_PLATFORMS[@]}"; do
            install_thirdparty_for_platform "$platform"
            echo
        done
    else
        install_thirdparty_for_platform "$TARGET_PLATFORM"
    fi
}

# 安装 SDK 核心库（单平台）
install_sdk_core_for_platform() {
    local platform=$1
    log_info "安装 SDK 核心库 (平台: $platform)..."
    
    local sdk_dir="$INSTALL_DIR/galbot_sdk"
    
    # 创建目录结构
    run_cmd mkdir -p "$sdk_dir/$platform/include"
    run_cmd mkdir -p "$sdk_dir/$platform/lib"
    run_cmd mkdir -p "$sdk_dir/$platform/bin"
    
    # 复制头文件
    if [ -d "$SCRIPT_DIR/galbot_sdk/$platform/include" ]; then
        log_info "  复制头文件..."
        run_cmd cp -r "$SCRIPT_DIR/galbot_sdk/$platform/include/"* "$sdk_dir/$platform/include/"
    fi
    
    # 复制 SDK 核心库
    if [ -d "$SCRIPT_DIR/galbot_sdk/$platform/lib" ]; then
        log_info "  复制 SDK 核心库..."
        
        # 只复制 SDK 核心库（三方库通过 install_thirdparty 安装）
        for f in "$SCRIPT_DIR/galbot_sdk/$platform/lib/"libgalbot_sdk.so*; do
            if [ -e "$f" ]; then
                run_cmd cp -a "$f" "$sdk_dir/$platform/lib/"
            fi
        done
    fi
    
    # 复制 bin 目录
    if [ -d "$SCRIPT_DIR/galbot_sdk/$platform/bin" ]; then
        log_info "  复制可执行文件..."
        run_cmd cp -r "$SCRIPT_DIR/galbot_sdk/$platform/bin/"* "$sdk_dir/$platform/bin/" 2>/dev/null || true
    fi
    
    # 复制 setup.sh
    if [ -f "$SCRIPT_DIR/galbot_sdk/$platform/setup.sh" ]; then
        run_cmd cp "$SCRIPT_DIR/galbot_sdk/$platform/setup.sh" "$sdk_dir/$platform/"
    fi
    
    # 复制 common.cmake
    if [ -f "$SCRIPT_DIR/galbot_sdk/common.cmake" ]; then
        run_cmd cp "$SCRIPT_DIR/galbot_sdk/common.cmake" "$sdk_dir/"
    fi
    
    # 复制 python 绑定
    if [ -d "$SCRIPT_DIR/galbot_sdk/$platform/lib/python" ]; then
        log_info "  复制 Python 绑定..."
        run_cmd cp -r "$SCRIPT_DIR/galbot_sdk/$platform/lib/python" "$sdk_dir/$platform/lib/"
    fi
    
    log_success "  SDK 核心库安装完成: $platform"
}

# 安装 SDK 核心库（支持多平台）
install_sdk_core() {
    if [ "$ALL_PLATFORMS" = true ]; then
        log_info "安装所有平台的 SDK 核心库..."
        for platform in "${SUPPORTED_PLATFORMS[@]}"; do
            install_sdk_core_for_platform "$platform"
            echo
        done
    else
        install_sdk_core_for_platform "$TARGET_PLATFORM"
    fi
}

# 安装配置文件和示例
install_extras() {
    log_info "安装配置文件和示例..."
    
    # 安装 config 到机器人运行目录（可选，仅在有权限时）
    if [ -d "$SCRIPT_DIR/config" ]; then
        if [ "$USE_SUDO" = true ]; then
            log_info "  安装配置文件到 /data/config..."
            run_cmd mkdir -p /data/config
            run_cmd cp -rn "$SCRIPT_DIR/config/"* /data/config/ 2>/dev/null || \
                run_cmd cp -r "$SCRIPT_DIR/config/"* /data/config/
        else
            log_info "  复制配置文件到安装目录..."
            run_cmd mkdir -p "$INSTALL_DIR/config"
            run_cmd cp -r "$SCRIPT_DIR/config/"* "$INSTALL_DIR/config/"
        fi
    fi
    
    # 复制 examples
    if [ -d "$SCRIPT_DIR/examples" ]; then
        log_info "  复制示例代码..."
        run_cmd mkdir -p "$INSTALL_DIR/examples"
        run_cmd cp -r "$SCRIPT_DIR/examples/"* "$INSTALL_DIR/examples/"
        
        # 更新 examples 中的路径
        update_example_paths
    fi
    
    # 复制文档
    if [ -d "$SCRIPT_DIR/docs" ]; then
        log_info "  复制文档..."
        run_cmd mkdir -p "$INSTALL_DIR/docs"
        run_cmd cp -r "$SCRIPT_DIR/docs/"* "$INSTALL_DIR/docs/"
    fi
    
    # 复制 licenses
    if [ -d "$SCRIPT_DIR/licenses" ]; then
        run_cmd mkdir -p "$INSTALL_DIR/licenses"
        run_cmd cp -r "$SCRIPT_DIR/licenses/"* "$INSTALL_DIR/licenses/"
    fi
    
    # 复制 README
    if [ -f "$SCRIPT_DIR/README.md" ]; then
        run_cmd cp "$SCRIPT_DIR/README.md" "$INSTALL_DIR/"
    fi
    
    log_success "  配置文件和示例安装完成"
}

# 更新示例代码中的路径
update_example_paths() {
    local sdk_path="$INSTALL_DIR/galbot_sdk"
    local toolchain_path="$sdk_path/toolchain"
    local new_line="set(toolchain $INSTALL_DIR/toolchain/\${toolchain_target_plat})"
    local sdk_line="set(SDK_INSTALL_PATH $INSTALL_DIR)"

    # 更新 cmake toolchain 路径（仅 g1/s1 的 cpp/cmake）
    local cmake_locations=(
        "$INSTALL_DIR/examples/g1/cpp/cmake"
        "$INSTALL_DIR/examples/s1/cpp/cmake"
    )
    for dir in "${cmake_locations[@]}"; do
        for f in "$dir/linux-aarch64-gcc940.cmake" "$dir/linux-x86_64-gcc940.cmake"; do
            if [ -f "$f" ]; then
                run_cmd sed -i "7c\\$new_line" "$f"
            fi
        done
    done

    # 更新 CMakeLists.txt 中的 SDK 路径（g1/s1 各自 cpp 目录）
    for cmake_file in "$INSTALL_DIR/examples/g1/cpp/CMakeLists.txt" \
                      "$INSTALL_DIR/examples/s1/cpp/CMakeLists.txt"; do
        if [ -f "$cmake_file" ]; then
            run_cmd sed -i "7c\\$sdk_line" "$cmake_file"
        fi
    done
}

# 显示安装摘要
show_summary() {
echo
echo "=========================================="
    echo " 安装完成!"
    echo "=========================================="
    echo
    echo "安装目录: $INSTALL_DIR"
    echo "SDK 版本: $SDK_VERSION"
    if [ "$ALL_PLATFORMS" = true ]; then
        echo "已安装平台: ${SUPPORTED_PLATFORMS[*]}"
    else
        echo "目标平台: $TARGET_PLATFORM"
    fi
    echo
    echo "目录结构:"
    echo "  $INSTALL_DIR/"
    echo "  ├── .cache/              # 依赖压缩包缓存（用于校验）"
    echo "  ├── toolchain/"
    if [ "$ALL_PLATFORMS" = true ]; then
        for platform in "${SUPPORTED_PLATFORMS[@]}"; do
            echo "  │   ├── $(get_toolchain_name $platform)/"
        done
    else
        echo "  │   └── $(get_toolchain_name $TARGET_PLATFORM)/"
    fi
    echo "  ├── galbot_sdk/"
    if [ "$ALL_PLATFORMS" = true ]; then
        for platform in "${SUPPORTED_PLATFORMS[@]}"; do
            echo "  │   ├── $platform/"
            echo "  │   │   ├── include/"
            echo "  │   │   ├── lib/"
            echo "  │   │   └── setup.sh"
        done
    else
        echo "  │   └── $TARGET_PLATFORM/"
        echo "  │       ├── include/"
        echo "  │       ├── lib/"
        echo "  │       └── setup.sh"
    fi
    echo "  ├── examples/"
    echo "  └── docs/"
    echo
    echo "使用方法:"
    if [ "$ALL_PLATFORMS" = true ]; then
        for platform in "${SUPPORTED_PLATFORMS[@]}"; do
            echo "  # $platform:"
            echo "  source $INSTALL_DIR/galbot_sdk/$platform/setup.sh"
        done
    else
        echo "  source $INSTALL_DIR/galbot_sdk/$TARGET_PLATFORM/setup.sh"
    fi
    echo
    echo "=========================================="
}

#######################################
# 主程序
#######################################

main() {
    echo "=========================================="
    echo " GALBOT_G1_SDK 安装程序 v${SDK_VERSION}"
echo "=========================================="
    echo
    
    # 解析参数
    parse_args "$@"
    
    # 检测/确认平台
    if [ "$ALL_PLATFORMS" = true ]; then
        log_info "将安装所有支持的平台: ${SUPPORTED_PLATFORMS[*]}"
        # 设置一个默认平台用于某些单平台操作（如示例路径更新）
        if [ -z "$TARGET_PLATFORM" ]; then
            TARGET_PLATFORM=$(detect_platform)
        fi
        log_info "当前检测平台（用于示例路径）: $TARGET_PLATFORM"
    else
        # 单平台模式
        if [ -z "$TARGET_PLATFORM" ]; then
            TARGET_PLATFORM=$(detect_platform)
            log_info "检测到平台: $TARGET_PLATFORM"
        else
            log_info "指定平台: $TARGET_PLATFORM"
        fi
    fi
    
    # 确认安装目录
    if [ -z "$INSTALL_DIR" ]; then
        if [ "$NON_INTERACTIVE" = true ]; then
            INSTALL_DIR="$DEFAULT_INSTALL_DIR"
        else
            read -p "安装目录 [$DEFAULT_INSTALL_DIR]: " INSTALL_DIR
            INSTALL_DIR="${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"
        fi
    fi
    
    log_info "安装目录: $INSTALL_DIR"
    log_info "目标平台: $TARGET_PLATFORM"
    echo
    
    # 创建安装与日志目录
    run_cmd mkdir -p "$INSTALL_DIR"
    run_cmd mkdir -p "$EMBOSA_LOG_DIR"
    run_cmd chmod 777 "$EMBOSA_LOG_DIR"
    
    # 安装工具链
    install_toolchain
    echo
    
    # 安装三方库
    install_thirdparty
    echo
    
    if [ "$CHECK_ONLY" = true ]; then
        log_info "检查完成（--check 模式，未进行实际安装）"
        exit 0
    fi
    
    # 安装 SDK 核心库
    install_sdk_core
    echo
    
    # 安装配置文件和示例
    install_extras
    echo
    
    # 显示摘要
    show_summary
}

# 运行主程序
main "$@"
