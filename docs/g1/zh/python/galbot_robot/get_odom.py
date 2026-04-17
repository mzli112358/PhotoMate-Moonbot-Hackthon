import time
from galbot_sdk.g1 import GalbotRobot


def print_odom_data(odom_data: dict):
    """
    Print odometry data
    
    odom_data: dict, includes:
        - 'timestamp_ns': Timestamp (ns)
        - 'position': [x, y, z] Position (m)
        - 'orientation': [qx, qy, qz, qw] Quaternion orientation
    """
    if not odom_data:
        print("Odom data is empty")
        return

    print(f"Timestamp (ns): {odom_data.get('timestamp_ns')}")
    
    position = odom_data.get("position", [])
    if position:
        print(f"Position (m): x={position[0]}, y={position[1]}, z={position[2]}")
    
    orientation = odom_data.get("orientation", [])
    if orientation:
        print(f"Orientation (quaternion): qx={orientation[0]}, qy={orientation[1]}, "
              f"qz={orientation[2]}, qw={orientation[3]}")


# Get and initialize the GalbotRobot singleton
robot = GalbotRobot()
robot.init()

# Program started, waiting for data
time.sleep(1)
print("Initialization succeeded")

# Get odometry data
odom_data = robot.get_odom()
if not odom_data:
    print("No odom data!")
else:
    print("Odometry data:")
    print_odom_data(odom_data)

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')
