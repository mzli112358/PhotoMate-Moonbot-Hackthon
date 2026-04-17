from galbot_sdk.g1 import GalbotNavigation
from galbot_sdk.g1 import GalbotRobot
from galbot_sdk.g1 import ControlStatus, G1ControllerName
import numpy as np
import sys

nav = GalbotNavigation()
nav.init()
robot = GalbotRobot()
robot.init()

start = nav.get_current_pose()
goal = np.array([1.0, 1.0, 0.0, 0, 0, 0.4794255, 0.8775826])

res = robot.switch_controller(G1ControllerName.CHASSIS_POSE_CTRL)
if res != ControlStatus.SUCCESS:
    print("Failed to switch controller!")
    sys.exit(1)
else:
    print("Controller switched successfully!")

if nav.check_path_reachability(goal, start):
    status = nav.navigate_to_goal(
        goal, enable_collision_check=True, is_blocking=True, timeout=30
    )
    print("navigate_to_goal returned status:", status)
    print("Reached or not:", nav.check_goal_arrival())
else:
    print("Path unreachable or unsafe")

nav.stop_navigation()
# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print("Resources released successfully")
