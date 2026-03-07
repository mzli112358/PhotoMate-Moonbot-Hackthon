import time
from galbot_sdk.g1 import GalbotRobot
from typing import Dict

def print_device_info(device_info: dict):
    """
    device_info: dict，包含:
        - 'model': 设备型号 (str)
        - 'serial_number': 序列号 (str)
        - 'firmware_version': 固件版本 (str)
        - 'hardware_version': 硬件版本 (str)
        - 'manufacturer': 制造商 (str)
    """
    if not device_info:
        print("设备信息为空")
        return

    print("设备信息：")
    print(f"  型号: {device_info.get('model', 'N/A')}")
    print(f"  序列号: {device_info.get('serial_number', 'N/A')}")
    print(f"  固件版本: {device_info.get('firmware_version', 'N/A')}")
    print(f"  硬件版本: {device_info.get('hardware_version', 'N/A')}")
    print(f"  制造商: {device_info.get('manufacturer', 'N/A')}")

# 获取 GalbotRobot 的单例并初始化
robot = GalbotRobot.get_instance()
robot.init()

# 程序立即启动，稍等数据就绪时间
time.sleep(1)
print("初始化成功")

device_info = robot.get_device_information()
if not device_info:
    print("设备信息获取失败！")
else:
    print("设备信息获取成功！")
    print_device_info(device_info)

# 主动发出SIGINT退出信号
robot.request_shutdown()
# 等待进入shutdown状态
robot.wait_for_shutdown()
# 进行SDK资源释放
robot.destroy()
print('资源释放成功')
