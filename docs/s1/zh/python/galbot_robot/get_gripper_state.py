import time
from galbot_sdk.s1 import GalbotRobot, S1JointGroup


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

# Get gripper state
gripper_state = robot.get_gripper_state(S1JointGroup.left_gripper)

if gripper_state is None:
    print('get gripper state error')
else:
    print('Left gripper state:')
    print_gripper_state(gripper_state)

# Exit system and release SDK resources
robot.request_shutdown()
robot.wait_for_shutdown()
robot.destroy()
print('Resources released successfully')
