import sys
import time

import galbot_sdk.s1 as gm
from galbot_sdk.s1 import GalbotMotion, GalbotRobot

motion = GalbotMotion()
robot = GalbotRobot()


def print_pose(label, status, pose_vec, planner):
    status_str = planner.status_to_string(status)
    print(f"[{label}] Status: {status_str}")
    if status == gm.MotionStatus.SUCCESS:
        print("End-effector pose: " + " ".join(str(v) for v in pose_vec) + "\n")
    else:
        print("Calculation failed!")


def main():
    if motion.init():
        print("Planner initialized successfully!")
    else:
        print("Planner initialization failed!", file=sys.stderr)
        return -1

    if robot.init():
        print("System initialized successfully!")
    else:
        print("System initialization failed!", file=sys.stderr)
        return -1

    # Program started, waiting for data
    time.sleep(3)

    chain_joints = {
        "torso": [1.1],
        "head": [0.0000, -0.26],
        "left_arm": [-0.47, -0.94, -0.54, -1.92, 0.2, 0.0, 0.0],
        "right_arm": [0.47, 0.94, 0.54, 1.92, -0.2, 0.0, 0.0],
    }
    end_link = "left_arm_end_effector_mount_link"
    reference_frame = "base_link"
    custom_param = gm.Parameter()

    # --- test 1: default parameters (current status) ---
    try:
        print(">> Executing: Basic forward kinematics...")
        res1 = motion.forward_kinematics(end_link, reference_frame)
        print_pose("Basic version", res1[0], res1[1], motion)
    except Exception as e:
        print(f"❌ Basic version exception: {e}", file=sys.stderr)

    # --- test 2: joint state + parameters ---
    try:
        print(">> Executing: Forward kinematics with custom joints...")
        custom_joint_state = {"left_arm": chain_joints["left_arm"]}
        res2 = motion.forward_kinematics(
            end_link, reference_frame, custom_joint_state, custom_param
        )
        print_pose("Custom parameters", res2[0], res2[1], motion)
    except Exception as e:
        print(f"❌ Custom-parameter exception: {e}", file=sys.stderr)

    # --- test 3: RobotStates forward kinematics (current status, planning) ---
    try:
        print(">> Executing: Forward kinematics based on RobotStates...")
        current_state = motion.get_robot_states()
        if not current_state.whole_body_joint:
            print(
                "❌ RobotStates-based: Unable to get current body joint states; "
                "ensure WBC/sensors are ready.",
                file=sys.stderr,
            )
        else:
            res3 = motion.forward_kinematics_by_state(
                end_link,
                current_state,
                reference_frame,
                gm.Parameter(),
            )
            print_pose("Based on RobotStates", res3[0], res3[1], motion)
    except Exception as e:
        print(f"❌ RobotStates-based exception: {e}", file=sys.stderr)

    robot.request_shutdown()
    robot.wait_for_shutdown()
    robot.destroy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
