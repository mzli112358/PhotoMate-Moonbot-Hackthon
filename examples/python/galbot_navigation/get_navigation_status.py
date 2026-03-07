"""
示例：非阻塞导航中轮询 get_navigation_status，根据 SUCCESS/FAILED 或超时及时退出，
避免卡死并走错误逻辑。
"""
from galbot_sdk.g1 import GalbotNavigation, GalbotRobot, NavigationTaskStatus, ControllerName, ControlStatus
import numpy as np
import time
import sys

nav = GalbotNavigation.get_instance()
nav.init()
robot = GalbotRobot.get_instance()
robot.init()

goal = np.array([0.5, 0.0, 0.0, 0, 0, 0.0, 1.0])
timeout_s = 20.0
poll_interval_s = 0.5

res = robot.switch_controller(ControllerName.CHASSIS_POSE_CTRL)
if res != ControlStatus.SUCCESS:
    print("切换控制器失败！")
    sys.exit(1)
else:
    print("切换控制器成功！")
# 非阻塞导航
nav.navigate_to_goal(goal, enable_collision_check=True, is_blocking=False, timeout=timeout_s)
start = time.time()

while True:
    status = nav.get_navigation_status()
    elapsed = time.time() - start

    if status == NavigationTaskStatus.SUCCESS:
        print("已到达目标")
        break
    if status == NavigationTaskStatus.FAILED:
        print("导航失败，及时退出错误逻辑")
        break
    if elapsed >= timeout_s:
        print("导航超时，及时退出")
        break

    if status == NavigationTaskStatus.RUNNING:
        print(f"正在导航... 状态: {status.name}, 已用时: {elapsed:.1f}s")
    else:
        print(f"状态: {status.name}, 已用时: {elapsed:.1f}s")

    time.sleep(poll_interval_s)

nav.stop_navigation()
robot.request_shutdown()
robot.wait_for_shutdown()
robot.destroy()
print("资源释放成功")
