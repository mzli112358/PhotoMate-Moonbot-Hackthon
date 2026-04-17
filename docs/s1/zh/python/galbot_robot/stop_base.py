from galbot_sdk.s1 import GalbotRobot
from galbot_sdk.s1 import ControlStatus
import time

# Get and initialize the GalbotRobot singleton
robot = GalbotRobot()
robot.init()
time.sleep(1)
print("Initialization succeeded")

# Send chassis stop motion command
while True:
    status = robot.stop_base()
    # Check execution results
    if status == ControlStatus.SUCCESS:
        print("Chassis motion stopped successfully")
        break
    print("Failed to stop the chassis, retrying...")

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')