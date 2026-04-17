import time
from galbot_sdk.s1 import GalbotRobot
from galbot_sdk.s1 import ControlStatus

# Get and initialize the GalbotRobot singleton
robot = GalbotRobot()
if robot.init():
    print('System initialized successfully!')
else:
    print('System initialization failed!')
    exit(1)

# Program started, waiting for data
time.sleep(2)

# Get specified joint names; joint groups include ["torso", "head", "left_arm", "right_arm"] (S1: torso replaces G1 leg)
joint_groups = ["head"]
only_active_joint = True  # Get active joints
head_joint_names_vec = robot.get_joint_names(only_active_joint, joint_groups)
print('Head joint names:')
for i, name in enumerate(head_joint_names_vec):
    print(f"{i}: {name}")

# Passing an empty array returns all joint group information by default
all_joint_names_vec = robot.get_joint_names(only_active_joint, [])
print('All joint names:')
for i, name in enumerate(all_joint_names_vec):
    print(f"{i}: {name}")

# Joint groups to control; passing empty array defaults to torso, head, left_arm, right_arm (S1: torso replaces G1 leg)
joint_groups = ["head"]
# Specific joints to control; if provided, this overrides the joint_groups parameter
joint_names = []
# Joint positions; head joint group contains two joints
# Head angles: within S1 limits [-0.7854, 0.7854] and [-0.6109, 0.6109]
joint_pos = [0.2, 0.2]
# Whether to block and wait for joint angles to reach position or timeout
is_block = True
# Maximum joint speed (rad/s)
speed_rad_s = 0.1
# Maximum wait time (seconds)
timeout_s = 10.0

# Set joint positions
status = robot.set_joint_positions(
    joint_pos, joint_groups, joint_names, is_block, speed_rad_s, timeout_s
)

if status == ControlStatus.SUCCESS:
    print('Joint command set successfully!')
else:
    print('Failed to set joint command!')

# Query joint positions by group; empty array defaults to leg, head, dual-arm groups. Second parameter specifies joint names, which overrides joint_groups if provided.
ret_positions = robot.get_joint_positions(joint_groups, [])
for position in ret_positions:
    print(f"joint positions is {position}")

# Use specific joint names for control; this parameter overrides joint_groups
joint_names = ["head_joint1", "head_joint2"]
joint_pos = [0.0, 0.0]

# Set joint positions
status = robot.set_joint_positions(
    joint_pos, joint_groups, joint_names, is_block, speed_rad_s, timeout_s
)

if status == ControlStatus.SUCCESS:
    print('Joint command set successfully!')
else:
    print('Failed to set joint command!')

# Query joint positions by group; empty array defaults to leg, head, dual-arm groups. Second parameter specifies joint names, which overrides joint_groups if provided.
ret_positions = robot.get_joint_positions(joint_groups, [])
for position in ret_positions:
    print(f"joint positions is {position}")

# Exit system and release SDK resources
robot.request_shutdown()
robot.wait_for_shutdown()
robot.destroy()
print('Resources released successfully')
