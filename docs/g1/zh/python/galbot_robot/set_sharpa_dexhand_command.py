import time
from galbot_sdk.g1 import GalbotRobot, G1JointGroup, ControlStatus, JointCommand, DexHandType

# Get and initialize the GalbotRobot singleton
robot = GalbotRobot()
robot.init()
print('Initialization succeeded')

# Program started, waiting for data
time.sleep(2)

# Set left Sharpa dexhand command (22 joints, relaxed position - all zeros)
dexhand_command = [JointCommand() for _ in range(22)]
for cmd in dexhand_command:
    cmd.position = 0.0

status = robot.set_dexhand_command(
    G1JointGroup.left_dexhand, dexhand_command, DexHandType.SHARPA, False
)

if status != ControlStatus.SUCCESS:
    print("Set left Sharpa dexhand failed")
else:
    print('Set left Sharpa dexhand (relaxed position) success')

time.sleep(1)

# Set right Sharpa dexhand command
status = robot.set_dexhand_command(
    G1JointGroup.right_dexhand, dexhand_command, DexHandType.SHARPA, False
)

if status != ControlStatus.SUCCESS:
    print("Set right Sharpa dexhand failed")
else:
    print('Set right Sharpa dexhand (relaxed position) success')

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')
