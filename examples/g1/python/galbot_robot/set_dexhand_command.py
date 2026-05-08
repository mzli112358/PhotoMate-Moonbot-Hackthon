import time
from galbot_sdk.g1 import GalbotRobot, G1JointGroup, ControlStatus, JointCommand, DexHandType

# Get and initialize the GalbotRobot singleton
robot = GalbotRobot()
robot.init()
print('Initialization succeeded')

# Program started, waiting for data
time.sleep(2)

# Set left dexhand command (6 joints)
# range depends on dexhand type: inspire 0-1000, brainco 0-100
dexhand_command = [JointCommand() for _ in range(6)]
for cmd in dexhand_command:
    cmd.position = 500.0

status = robot.set_dexhand_command(
    G1JointGroup.left_dexhand, dexhand_command, DexHandType.INSPIRE, False
)

if status != ControlStatus.SUCCESS:
    print("Set left dexhand failed")
else:
    print('Set left dexhand success')

time.sleep(2)

# Set right dexhand command with different positions
dexhand_command = [JointCommand() for _ in range(6)]
for cmd in dexhand_command:
    cmd.position = 800.0

status = robot.set_dexhand_command(
    G1JointGroup.right_dexhand, dexhand_command, DexHandType.INSPIRE, False
)

if status != ControlStatus.SUCCESS:
    print("Set right dexhand failed")
else:
    print('Set right dexhand success')

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')
