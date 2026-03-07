import time
import math
from galbot_sdk.g1 import GalbotRobot, JointCommand

def head_high_frequency_control():
    """
    头部高频控制示例
    """

    control_frequency = 100.0  # Hz
    dt = 1.0 / control_frequency
    duration = 4.0  # 控制 4 秒

    amplitude = 0.3  # 最大摆动幅度 (rad)
    frequency = 0.5  # 正弦频率 (Hz)
    # 要控制的关节组名称
    joint_groups = ["head"]
    # 如果要控制指定关节，填充该字段，将会覆盖joint_groups参数。如不填充则默认控制joint_groups中的所有关节
    joint_names = []

    print("开始头部高频控制")

    joint_commands = [JointCommand(), JointCommand()]

    start_time = time.time()

    while True:
        current_time = time.time() - start_time
        if current_time > duration:
            break

        # 生成正弦轨迹
        target_position = amplitude * math.sin(
            2 * math.pi * frequency * current_time
        )

        # 设置头部关节角度
        joint_commands[0].position = target_position
        joint_commands[1].position = target_position
        print(f"当前时间: {current_time:.2f}s, 目标位置: {target_position:.3f} rad")

        # 期望到达时间
        time_from_start_sec = 0.0

        execution_status = GalbotRobot.get_instance().set_joint_commands(
            joint_commands,
            joint_groups,
            joint_names,
            time_from_start_sec
        )

        # 固定周期 sleep
        time.sleep(dt)

    print("头部控制结束")

def main():
    # 获取 GalbotRobot 的单例并初始化
    robot = GalbotRobot.get_instance()

    if robot.init():
        print("系统初始化成功！")
    else:
        print("系统初始化失败！")
        return

    # 程序立即启动，稍等数据就绪时间
    time.sleep(2)
    
    head_high_frequency_control()

    # 退出系统并进行 SDK 资源释放
    robot.request_shutdown()
    robot.wait_for_shutdown()
    robot.destroy()
    print("程序已退出")


if __name__ == "__main__":
    main()
