import time
from galbot_sdk.s1 import GalbotRobot

# Get and initialize the GalbotRobot singleton
robot = GalbotRobot()
robot.init()
# Program started, waiting for data
time.sleep(1)
print("Initialization succeeded")

# Get joint positions by joint group names; returns all joints if empty
joint_group_names = ["left_arm"]
# get joint
only_active_joint = True
ret = robot.get_joint_names(only_active_joint, joint_group_names)
print("Left joint names:")
for i, name in enumerate(ret):
    print(f"{i + 1}: {name}")

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')