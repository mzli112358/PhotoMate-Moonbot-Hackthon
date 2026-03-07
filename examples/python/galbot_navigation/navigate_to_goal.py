from galbot_sdk.g1 import GalbotNavigation, GalbotRobot, ControllerName, ControlStatus
import numpy as np
import time
import sys

nav = GalbotNavigation.get_instance()
nav.init()
robot = GalbotRobot.get_instance()
robot.init()

goal = np.array([0.5, 0.0, 0.0, 0, 0, 0.0, 1.0])

res = robot.switch_controller(ControllerName.CHASSIS_POSE_CTRL)
if res != ControlStatus.SUCCESS:
    print("切换控制器失败！")
    sys.exit(1)
else:
    print("切换控制器成功！")

nav.navigate_to_goal(goal, enable_collision_check=True, is_blocking=False, timeout=20)

start_time = time.time()
reached = False

while True:
    if nav.check_goal_arrival():
        reached = True
        break
    if time.time() - start_time > 20:
        print("导航超时，20s 内未到达目标")
        break
    print("正在导航...")
    time.sleep(0.5)

if reached:
    print("已到达目标")
if reached:
    print("已到达目标")

nav.stop_navigation()
# 主动发出SIGINT退出信号
robot.request_shutdown()
# 等待进入shutdown状态
robot.wait_for_shutdown()
# 进行SDK资源释放
robot.destroy()
print('资源释放成功')