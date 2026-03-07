import time
from galbot_sdk.g1 import GalbotRobot


def print_bms_information(bms_info: dict):
    """
    bms_info: dict，包含:
        - 'voltage'            : float (V)
        - 'current'            : float (A)
        - 'battery_level'      : float (0-100)
        - 'temperature'        : float (°C)
        - 'charging_status'    : str or int
        - 'health_status'      : str or int
        - 'capacity'           : float (Ah)
    """
    if not bms_info:
        print("BMS information is empty")
        return

    print(f"Voltage (V): {bms_info.get('voltage')}")
    print(f"Current (A): {bms_info.get('current')}")
    print(f"Battery level (%): {bms_info.get('battery_level')}")
    print(f"Temperature (C): {bms_info.get('temperature')}")
    print(f"Charging status: {bms_info.get('charging_status')}")
    print(f"Health status: {bms_info.get('health_status')}")
    print(f"Capacity (Ah): {bms_info.get('capacity')}")


# 获取 GalbotRobot 的单例并初始化
robot = GalbotRobot.get_instance()
robot.init()

# 程序立即启动，稍等数据就绪时间
time.sleep(3)
print("初始化成功")

bms_info = robot.get_bms_information()
print_bms_information(bms_info)

# 主动发出SIGINT退出信号
robot.request_shutdown()
# 等待进入shutdown状态
robot.wait_for_shutdown()
# 进行SDK资源释放
robot.destroy()
print("资源释放成功")
