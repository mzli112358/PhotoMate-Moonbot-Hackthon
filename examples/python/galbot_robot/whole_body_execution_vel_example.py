from galbot_sdk.g1 import GalbotRobot
import time


def main():
    robot = GalbotRobot.get_instance()
    if robot.init():
        print("系统初始化成功！")
    else:
        print("系统初始化失败！")
        return

    time.sleep(2)

    # Whole-body joints: leg(5) + head(2) + left_arm(7) + right_arm(7)
    whole_body_joint_1 = [
        0.3, 1.2, 0.85, 0.0, 0.0,        # leg
        0.5, 0.5,                        # head
        2.0, -1.55, -0.55, -1.7, -0.0, -0.8, 0.0,   # left_arm
        -2.0, 1.55, 0.55, 1.7, 0.0, 0.8, 0.0        # right_arm
    ]
    whole_body_joint_2 = [
        0.3, 1.2, 0.85, 0.0, 0.0,        # leg
        0.0, 0.0,                        # head
        2.0, -1.55, -0.55, -1.7, -0.0, -0.8, 0.0,   # left_arm
        -2.0, 1.55, 0.55, 1.7, 0.0, 0.8, 0.0        # right_arm
    ]

    # Base velocity command (twist)
    linear_velocity_1 = [0.1, 0.0, 0.0]
    angular_velocity_1 = [0.0, 0.0, 0.0]
    linear_velocity_2 = [-0.1, 0.0, 0.0]
    angular_velocity_2 = [0.0, 0.0, 0.0]

    print("=== Whole-body + base velocity ===")
    vel_status = robot.execute_whole_body_target(
        whole_body_joint_1,
        linear_velocity_1,
        angular_velocity_1,
        False,
        0.1,
        10.0,
    )
    print("execute_whole_body_target (twist) status:", vel_status)

    # 底盘运动1s后停止
    time.sleep(1)
    robot.stop_base()

    # 等待5s关节运动完成
    time.sleep(5)

    vel_status = robot.execute_whole_body_target(
        whole_body_joint_2,
        linear_velocity_2,
        angular_velocity_2,
        False,
        0.1,
        10.0,
    )
    print("execute_whole_body_target (twist) status:", vel_status)

    # 底盘运动1s后停止
    time.sleep(1)
    robot.stop_base()

    # 等待5s关节运动完成
    time.sleep(5)

    robot.request_shutdown()
    robot.wait_for_shutdown()
    robot.destroy()


if __name__ == "__main__":
    main()
