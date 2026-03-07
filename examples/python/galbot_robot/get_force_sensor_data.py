import time
from galbot_sdk.g1 import GalbotRobot, GalbotOneFoxtrotSensor


def force_sensor_type_to_string(sensor_type: GalbotOneFoxtrotSensor) -> str:
    """将力传感器类型转换为字符串"""
    type_map = {
        GalbotOneFoxtrotSensor.LEFT_WRIST_FORCE: "LEFT_WRIST_FORCE",
        GalbotOneFoxtrotSensor.RIGHT_WRIST_FORCE: "RIGHT_WRIST_FORCE",
    }
    return type_map.get(sensor_type, "UNKNOWN_FORCE_SENSOR")


def print_force_data(sensor_type: GalbotOneFoxtrotSensor, force_data: dict):
    """
    打印力传感器数据
    
    force_data: dict，包含:
        - 'timestamp_ns': 时间戳（纳秒）
        - 'force': {'x', 'y', 'z'} 力（牛顿）
        - 'torque': {'x', 'y', 'z'} 力矩（牛顿·米）
    """
    print(f"--- {force_sensor_type_to_string(sensor_type)} ---")
    if not force_data:
        print("  Force data is empty")
        return

    print(f"  Timestamp (ns): {force_data.get('timestamp_ns')}")
    
    force = force_data.get("force", {})
    print(f"  Force (N):  fx={force.get('x')}, fy={force.get('y')}, fz={force.get('z')}")
    
    torque = force_data.get("torque", {})
    print(f"  Torque (Nm): tx={torque.get('x')}, ty={torque.get('y')}, tz={torque.get('z')}")


# 获取 GalbotRobot 的单例并初始化
robot = GalbotRobot.get_instance()
robot.init()

# 程序立即启动，稍等数据就绪时间
time.sleep(1)
print("初始化成功")

# 获取左腕力传感器数据
print("\n===== 获取左腕力传感器数据 =====")
left_force_data = robot.get_force_sensor_data(GalbotOneFoxtrotSensor.LEFT_WRIST_FORCE)
print_force_data(GalbotOneFoxtrotSensor.LEFT_WRIST_FORCE, left_force_data)

# 获取右腕力传感器数据
print("\n===== 获取右腕力传感器数据 =====")
right_force_data = robot.get_force_sensor_data(GalbotOneFoxtrotSensor.RIGHT_WRIST_FORCE)
print_force_data(GalbotOneFoxtrotSensor.RIGHT_WRIST_FORCE, right_force_data)

# 遍历获取所有力传感器数据
print("\n===== 获取所有力传感器数据 =====")
force_sensor_types = [
    GalbotOneFoxtrotSensor.LEFT_WRIST_FORCE,
    GalbotOneFoxtrotSensor.RIGHT_WRIST_FORCE,
]

for sensor_type in force_sensor_types:
    force_data = robot.get_force_sensor_data(sensor_type)
    print_force_data(sensor_type, force_data)

# 主动发出SIGINT退出信号
robot.request_shutdown()
# 等待进入shutdown状态
robot.wait_for_shutdown()
# 进行SDK资源释放
robot.destroy()
print('资源释放成功')
