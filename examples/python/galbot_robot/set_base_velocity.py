from galbot_sdk.g1 import GalbotRobot, ControlStatus
import time

# 获取 GalbotRobot 的单例
robot = GalbotRobot.get_instance()
robot.init()
time.sleep(1)
print("初始化成功")

# 设置底盘速度
linear_velocity = [0.05, 0.0, 0.0]  # 前进 0.5 m/s
angular_velocity = [0.0, 0.0, 0.1]  # 旋转 0.1 rad/s

duration_s = 2.0  # 持续 2 秒后自动停止
status = robot.set_base_velocity(linear_velocity, angular_velocity, duration_s)

if status == ControlStatus.SUCCESS:
    print(f"底盘速度设置成功，将在 {duration_s} 秒后自动停止。")
else:
    print("设置底盘速度失败。")

time.sleep(duration_s + 0.5)

# 主动发出SIGINT退出信号
robot.request_shutdown()
# 等待进入shutdown状态
robot.wait_for_shutdown()
# 进行SDK资源释放
robot.destroy()
print('资源释放成功')
