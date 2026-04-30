"""
Note: When running this example, please ensure the robot's `emergency stop button` is released;
"""
import time

try:
    from galbot_sdk.g1 import GalbotRobot
    from galbot_sdk.g1 import ControlStatus
except ImportError:
    print("Failed to import galbot_sdk, please install it first or check if it is in PYTHONPATH")
    exit(1)


def demo_heart_pose(robot: GalbotRobot,
                    joint_group_names: list,
                    position_seq: list,
                    is_blocking: bool,
                    max_speed: float,
                    timeout_s: float,
                    retry_count: int = 3
                    ):
    original_pos = robot.get_joint_positions(joint_group_names, [])
    print(f"Current angles of joint group {joint_group_names}: {original_pos}")

    pos_idx = 0
    print("Starting heart gesture...")
    while True:
        time.sleep(1)
        pos = position_seq[pos_idx]
        control_status = robot.set_joint_positions(
            pos, joint_group_names, [], is_blocking, max_speed, timeout_s
        )

        retry_cnt = retry_count
        while control_status != ControlStatus.SUCCESS and retry_cnt > 0:
            print(f"Setting angles for joint group {joint_group_names} failed, retrying {retry_cnt}...")
            retry_cnt = retry_cnt - 1
            time.sleep(1)
            control_status = robot.set_joint_positions(
                pos, joint_group_names, [], is_blocking, max_speed, timeout_s
            )
        if control_status == ControlStatus.SUCCESS:
            print(f"Setting angles for joint group {joint_group_names} successful")
            pos_idx = pos_idx + 1
        else:
            print(f"Setting angles for joint group {joint_group_names} failed")
            break

        if pos_idx > len(position_seq) - 1:
            break

    print("Showing heart gesture for 15 seconds, then restoring original pose...")
    time.sleep(5)

    control_status = robot.set_joint_positions(
        original_pos, joint_group_names, [], is_blocking, max_speed, timeout_s
    )
    retry_cnt = retry_count
    while control_status != ControlStatus.SUCCESS and retry_cnt > 0:
        print(f"Setting angles for joint group {joint_group_names} failed, retrying {retry_cnt}...")
        retry_cnt = retry_cnt - 1
        time.sleep(2)
        control_status = robot.set_joint_positions(
            original_pos, joint_group_names, [], is_blocking, max_speed, timeout_s
        )
    if control_status == ControlStatus.SUCCESS:
        print(f"Restoring angles for joint group {joint_group_names} successful")
    else:
        print(f"Restoring angles for joint group {joint_group_names} failed")


def main():
    try:
        robot = GalbotRobot()
        state = robot.init()
        if not state:
            print("Initialization failed")
            exit(1)
        else:
            print("Initialization successful")
            print(f"Is robot running: {robot.is_running()}")

        time.sleep(3)

        joint_names = robot.get_joint_names()
        if len(joint_names) > 0:
            print(f"List of joint names: {joint_names}")
        else:
            print("Failed to get list of joint names")

        joint_group_names = ["left_arm", "right_arm"]
        position_seq = [
            [1.53, 0.36, -2.54, -1.80, 0.12, -0.82, 0.09,
             -1.53, -0.36, 2.54, 1.80, -0.12, 0.82, -0.09]
        ]
        is_blocking = True
        max_speed = 0.1
        timeout_s = 20

        demo_heart_pose(robot, joint_group_names, position_seq,
                        is_blocking, max_speed, timeout_s)

    except Exception as e:
        print(f"An exception occurred: {e}")
    finally:
        robot.request_shutdown()
        robot.wait_for_shutdown()
        robot.destroy()
        print("Resource release successful")


if __name__ == "__main__":
    main()
