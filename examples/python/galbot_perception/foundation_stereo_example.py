"""高精度双目深度估计示例：单次 run_once，将深度图伪彩色保存为一张图片"""

import time
import cv2
import numpy as np

from galbot_sdk.g1 import GalbotPerception, GalbotRobot, PerceptionModule

OUTPUT_IMAGE_PATH = "foundation_stereo_depth.png"

def main():
    robot = GalbotRobot.get_instance()
    if not robot.init():
        print("Robot 初始化失败")
        return
    print("Robot 初始化成功")

    perception = GalbotPerception.get_instance()
    if not perception.init({PerceptionModule.FOUNDATION_STEREO, PerceptionModule.LIGHT_STEREO}):
        print("感知模块初始化失败")
        return
    print("感知模块初始化成功")

    time.sleep(12)  # 等待感知模型 load 成功
    print("触发单次推理...")

    if not perception.run_once(PerceptionModule.FOUNDATION_STEREO):
        print("run_once 命令发送失败")
        return

    print("等待推理结果...")
    if not perception.wait_for_new_result(
        PerceptionModule.FOUNDATION_STEREO, timeout_s=6.0
    ):
        print("等待超时，未收到推理结果")
        return

    ok, result = perception.get_latest_result(PerceptionModule.FOUNDATION_STEREO)
    if not ok:
        print("获取结果失败")
        return

    print(result.get_result_info())

    depth_map = result.instance_mask
    if depth_map is None:
        print("未收到深度图 (instance_mask 为空)")
        return

    print(f"深度图 shape: {depth_map.shape}, dtype: {depth_map.dtype}")
    print(f"深度值范围: [{np.nanmin(depth_map)}, {np.nanmax(depth_map)}]")

    depth_f = depth_map.astype(np.float32)
    valid = depth_f[depth_f > 0]
    if valid.size > 0:
        vmin, vmax = np.percentile(valid, [1, 99])
        normalized = np.clip((depth_f - vmin) / (vmax - vmin + 1e-6), 0, 1)
    else:
        normalized = np.zeros_like(depth_f)
    colored = cv2.applyColorMap(
        (normalized * 255).astype(np.uint8), cv2.COLORMAP_TURBO
    )

    if cv2.imwrite(OUTPUT_IMAGE_PATH, colored):
        print(f"已保存: {OUTPUT_IMAGE_PATH}")
    else:
        print(f"保存失败: {OUTPUT_IMAGE_PATH}")


if __name__ == "__main__":
    main()
    GalbotRobot.get_instance().request_shutdown()
    GalbotRobot.get_instance().wait_for_shutdown()
    GalbotRobot.get_instance().destroy()
