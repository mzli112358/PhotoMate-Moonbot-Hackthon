from galbot_sdk.s1 import GalbotRobot, ControlStatus
import time

# Get GalbotRobot
robot = GalbotRobot()
robot.init()
time.sleep(1)
print("Initialization succeeded")

# Set chassis speed
linear_velocity = [0.05, 0.0, 0.0]  # 0.5 m/s
angular_velocity = [0.0, 0.0, 0.1]  # 0.1 rad/s

duration_s = 2.0  # Automatically stop after 2 seconds
status = robot.set_base_velocity(linear_velocity, angular_velocity, duration_s)

if status == ControlStatus.SUCCESS:
    print(f"Chassis speed set successfully; will auto-stop after {duration_s} seconds.")
else:
    print("Set chassis speed failed.")

time.sleep(duration_s + 0.5)

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')
