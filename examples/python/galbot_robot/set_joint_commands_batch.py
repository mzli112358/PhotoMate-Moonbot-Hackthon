from galbot_sdk.g1 import GalbotRobot, JointGroup, ControlStatus, Trajectory, TrajectoryPoint, JointCommand
import time
import numpy as np
from typing import List

# 生成轨迹单点，包含位置与时间信息
def generate_target_point(q: List[float], target_time: float = 10):
    """Generate target for joints"""
    joint_position = TrajectoryPoint()
    joint_position.time_from_start_second = target_time
    joint_command_vec = []
    for joint in q:
        joint_cmd = JointCommand()
        joint_cmd.position = joint
        joint_cmd.velocity = 0.0
        joint_cmd.acceleration = 0.0
        joint_cmd.effort = 0.0
        # joint_cmd.Kp = 0.0
        # joint_cmd.Kd = 0.0
        joint_command_vec.append(joint_cmd)
    joint_position.joint_command_vec = joint_command_vec
    return joint_position

def generate_batch_trajectory(trajectory, joint_groups=[], joint_names=[], dt=0.008):
    """Generate batch trajectory for joints"""
    if trajectory is None or np.ndim(trajectory) != 2 or len(trajectory) == 0:
        return None

    # 创建 Trajectory
    traj = Trajectory()
    traj.joint_groups = joint_groups
    traj.joint_names = joint_names

    time = 0.0
    points = []
    for state in trajectory:
        time += dt
        # 创建单个轨迹点
        traj_point = generate_target_point(state, time)
        points.append(traj_point)

    traj.points = points
    return traj

# 批量设置关节指令函数
def batch_commands_exec():
    # 获取 GalbotRobot 的单例并初始化，仅需初始化一次
    robot = GalbotRobot.get_instance()
    robot.init()
    time.sleep(1)
    print("初始化成功")

    # 生成批量轨迹数据（包含多个时间点的关节指令）
    head_traj = np.linspace(
        [0.0, 0.0],
        [0.5, 0.0],
        num=10,  # 批量轨迹点数量
    )
    # 指定执行哪个关节组轨迹
    joint_groups = ["head"]
    # 执行指定关节轨迹，如填充将覆盖joint_groups关节组参数
    joint_names = []
    
    # 批量设置关节指令（非阻塞，立即返回）
    status = robot.set_joint_commands_batch(generate_batch_trajectory(head_traj.tolist(), joint_groups, joint_names))

    # 检查执行结果
    if status != ControlStatus.SUCCESS:
        print("批量指令提交失败")
    else:
        print("批量指令已提交，正在后台执行（非阻塞）")

    # 等待一段时间让指令执行
    time.sleep(1)

    # 主动发出SIGINT退出信号
    robot.request_shutdown()
    # 等待进入shutdown状态
    robot.wait_for_shutdown()
    # 进行SDK资源释放
    robot.destroy()
    print('资源释放成功')

batch_commands_exec()
