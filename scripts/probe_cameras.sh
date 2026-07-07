#!/usr/bin/env bash
# 8 号上机：探测 USB 相机（Insta360 Link 2C 多为 UVC）
set -euo pipefail

echo "=== lsusb (找 Insta360 / Arashi Vision) ==="
lsusb || true

echo ""
echo "=== v4l2 设备 ==="
if command -v v4l2-ctl >/dev/null 2>&1; then
  v4l2-ctl --list-devices || true
else
  echo "未安装 v4l2-utils，可: sudo apt install v4l-utils"
fi

echo ""
echo "=== OpenCV 快速探测 (0-3) ==="
python3 - <<'PY'
import sys
try:
    import cv2
except ImportError:
    print("pip install opencv-python-headless")
    sys.exit(0)

for i in range(4):
    cap = cv2.VideoCapture(i)
    ok = cap.isOpened()
    if ok:
        ret, frame = cap.read()
        print(f"  /dev/video{i}: opened={ok} frame={ret} shape={frame.shape if ret else None}")
    else:
        print(f"  /dev/video{i}: not available")
    cap.release()
PY
