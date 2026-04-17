import time
from galbot_sdk.s1 import GalbotRobot, S1JointGroup
from galbot_sdk.s1 import ControlStatus


def print_gripper_state(gripper_state):
    """Print gripper status"""
    print(f"Timestamp (ns): {gripper_state.timestamp_ns}")
    print(f" width {gripper_state.width} velocity {gripper_state.velocity}"
          f" effort {gripper_state.effort} is moving {gripper_state.is_moving}")


# Get and initialize the GalbotRobot singleton
robot = GalbotRobot()
if robot.init():
    print('System initialized successfully!')
else:
    print('System initialization failed!')
    exit(1)

# Program started, waiting for data
time.sleep(2)

# Gripper width (m)
width_m = 0.02
# Gripper speed (m/s)
velocity_mps = 0.05
# Gripper torque (N·m)
effort = 10
# Whether to block until execution completes
is_blocking = False
# Set left gripper width to 0.02m, speed 0.05m/s, torque 10, block until execution completes
status = robot.set_gripper_command(S1JointGroup.left_gripper, width_m, velocity_mps, effort, is_blocking)

if status == ControlStatus.SUCCESS:
    print('Gripper command set successfully!')
else:
    print('Failed to set gripper command!')

# Get gripper state
gripper_state = robot.get_gripper_state(S1JointGroup.left_gripper)

if gripper_state is None:
    print('get gripper state error')
else:
    print_gripper_state(gripper_state)

# Gripper width (m)
width_m = 0.1
# Gripper speed (m/s)
velocity_mps = 0.05
# Gripper torque (N·m)
effort = 10
# Whether to block until execution completes
is_blocking = False
# Set left gripper width to 0.1m, speed 0.05m/s, torque 10, non-blocking wait for execution completes
status = robot.set_gripper_command(S1JointGroup.left_gripper, width_m, velocity_mps, effort, is_blocking)

if status == ControlStatus.SUCCESS:
    print('Gripper command set successfully!')
else:
    print('Failed to set gripper command!')

# Exit system and release SDK resources
robot.request_shutdown()
robot.wait_for_shutdown()
robot.destroy()
print('Resources released successfully')
