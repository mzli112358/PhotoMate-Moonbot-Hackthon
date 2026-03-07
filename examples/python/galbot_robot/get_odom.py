import time
from galbot_sdk.g1 import GalbotRobot


def print_odom_data(odom_data: dict):
    """
    打印里程计数据
    
    odom_data: dict，包含:
        - 'timestamp_ns': 时间戳（纳秒）
        - 'position': [x, y, z] 位置（米）
        - 'orientation': [qx, qy, qz, qw] 四元数姿态
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


# 获取 GalbotRobot 的单例并初始化
robot = GalbotRobot.get_instance()
robot.init()

# 程序立即启动，稍等数据就绪时间
time.sleep(1)
print("初始化成功")

# 获取里程计数据
odom_data = robot.get_odom()
if not odom_data:
    print("No odom data!")
else:
    print("里程计数据：")
    print_odom_data(odom_data)

# 主动发出SIGINT退出信号
robot.request_shutdown()
# 等待进入shutdown状态
robot.wait_for_shutdown()
# 进行SDK资源释放
robot.destroy()
print('资源释放成功')
