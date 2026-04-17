from galbot_sdk.s1 import GalbotRobot
from galbot_sdk.s1 import ControlStatus
import time

# Get and initialize the GalbotRobot singleton
robot = GalbotRobot()
robot.init()
time.sleep(2)
print("Initialization succeeded")

# Stop trajectory execution
while True:
    status = robot.stop_trajectory_execution()

    # Check execution results
    if status == ControlStatus.SUCCESS:
        print('Stop trajectory execution succeeded')
        break

    print("Trajectory stop failed, retrying...")

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')