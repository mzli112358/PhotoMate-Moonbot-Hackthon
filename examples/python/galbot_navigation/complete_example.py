from galbot_sdk.g1 import GalbotRobot, GalbotNavigation, ControllerName, ControlStatus
import numpy as np
import time
import sys

robot = GalbotRobot.get_instance()
robot.init()
nav = GalbotNavigation.get_instance()
nav.init()

init_pose = np.array([0.0, 0.0, 0.0, 0, 0, 0.0, 1.0])
goal_pose = np.array([1.0, 0.0, 0.0, 0, 0, 0.0, 1.0])

res = robot.switch_controller(ControllerName.CHASSIS_POSE_CTRL)
if res != ControlStatus.SUCCESS:
    print("切换控制器失败！")
    sys.exit(1)
else:
    print("切换控制器成功！")

while not nav.is_localized():
    nav.relocalize(init_pose)
    time.sleep(0.5)

if nav.check_path_reachability(goal_pose, nav.get_current_pose()):
    nav.navigate_to_goal(goal_pose, enable_collision_check=True, is_blocking=True, timeout=30)
    print("是否已到达:", nav.check_goal_arrival())

nav.stop_navigation()
# 关闭系统
robot.request_shutdown()
robot.wait_for_shutdown()
robot.destroy()