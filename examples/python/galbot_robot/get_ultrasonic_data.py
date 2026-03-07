import time
from galbot_sdk.g1 import GalbotRobot, SensorType, UltrasonicType


def ultrasonic_type_to_string(ultrasonic_type: UltrasonicType) -> str:
    """将超声波传感器类型转换为字符串"""
    type_map = {
        UltrasonicType.FRONT_LEFT: "FRONT_LEFT",
        UltrasonicType.FRONT_RIGHT: "FRONT_RIGHT",
        UltrasonicType.RIGHT_LEFT: "RIGHT_LEFT",
        UltrasonicType.RIGHT_RIGHT: "RIGHT_RIGHT",
        UltrasonicType.BACK_LEFT: "BACK_LEFT",
        UltrasonicType.BACK_RIGHT: "BACK_RIGHT",
        UltrasonicType.LEFT_LEFT: "LEFT_LEFT",
        UltrasonicType.LEFT_RIGHT: "LEFT_RIGHT",
    }
    return type_map.get(ultrasonic_type, "UNKNOWN_ULTRASONIC")


def print_ultrasonic_data(ultrasonic_type: UltrasonicType, ultrasonic_data: dict):
    """
    打印超声波传感器数据
    
    ultrasonic_data: dict，包含:
        - 'timestamp_ns': 时间戳（纳秒）
        - 'distance': 距离（米）
    """
    print(f"--- {ultrasonic_type_to_string(ultrasonic_type)} ---")
    if not ultrasonic_data:
        print("  Ultrasonic data is empty")
        return

    print(f"  Timestamp (ns): {ultrasonic_data.get('timestamp_ns')}")
    print(f"  Distance (m): {ultrasonic_data.get('distance')}")


# 获取 GalbotRobot 的单例并初始化
robot = GalbotRobot.get_instance()

# 初始化传感器，为节省资源，只有初始化中传入的传感器可获取数据
enable_sensor_set = {SensorType.BASE_ULTRASONIC}
robot.init(enable_sensor_set)

# 程序立即启动，稍等数据就绪时间
time.sleep(1)
print("初始化成功")

# 获取单个超声波传感器数据
print("\n===== 获取单个超声波传感器数据 =====")
ultrasonic_data = robot.get_ultrasonic_data(UltrasonicType.FRONT_LEFT)
print_ultrasonic_data(UltrasonicType.FRONT_LEFT, ultrasonic_data)

# 遍历获取所有8个超声波传感器数据
print("\n===== 获取所有超声波传感器数据 =====")
ultrasonic_types = [
    UltrasonicType.FRONT_LEFT,
    UltrasonicType.FRONT_RIGHT,
    UltrasonicType.RIGHT_LEFT,
    UltrasonicType.RIGHT_RIGHT,
    UltrasonicType.BACK_LEFT,
    UltrasonicType.BACK_RIGHT,
    UltrasonicType.LEFT_LEFT,
    UltrasonicType.LEFT_RIGHT,
]

for ultrasonic_type in ultrasonic_types:
    data = robot.get_ultrasonic_data(ultrasonic_type)
    print_ultrasonic_data(ultrasonic_type, data)

# 主动发出SIGINT退出信号
robot.request_shutdown()
# 等待进入shutdown状态
robot.wait_for_shutdown()
# 进行SDK资源释放
robot.destroy()
print('资源释放成功')
