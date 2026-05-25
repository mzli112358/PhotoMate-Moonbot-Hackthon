#!/bin/bash
# =============================================================================
# Galbot SDK Command Line Wrapper
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

show_help() {
    echo "Usage: galbot_sdk <command> [options]"
    echo ""
    echo "Commands:"
    echo "  check-version     Check SDK and robot version compatibility"
    echo "  -h, --help        Show this help message"
}

case "${1:-}" in
    check-version)
        shift
        exec python3 "$SCRIPT_DIR/check_robot_compat.py" "$@"
        ;;
    -h|--help|"")
        show_help
        exit 0
        ;;
    *)
        echo "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
