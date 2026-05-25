import time

import galbot_sdk.g1 as gm
from galbot_sdk.g1 import GalbotMotion, GalbotRobot


def print_status(status):
    labels = {
        gm.MotionStatus.SUCCESS: "SUCCESS",
        gm.MotionStatus.TIMEOUT: "TIMEOUT",
        gm.MotionStatus.FAULT: "FAULT",
        gm.MotionStatus.INVALID_INPUT: "INVALID_INPUT",
        gm.MotionStatus.INIT_FAILED: "INIT_FAILED",
        gm.MotionStatus.IN_PROGRESS: "IN_PROGRESS",
        gm.MotionStatus.STOPPED_UNREACHED: "STOPPED_UNREACHED",
        gm.MotionStatus.DATA_FETCH_FAILED: "DATA_FETCH_FAILED",
        gm.MotionStatus.PUBLISH_FAIL: "PUBLISH_FAIL",
        gm.MotionStatus.COMM_DISCONNECTED: "COMM_DISCONNECTED",
    }
    return labels.get(status, "UNKNOWN")


def print_vector(values):
    print("[", end="")
    for index, value in enumerate(values):
        if index > 0:
            print(", ", end="")
        print(value, end="")
    print("]", end="")


def print_robot_states(robot_states):
    if robot_states is None:
        print("None (use current complete robot state)")
        return

    whole_body_joint = list(getattr(robot_states, "whole_body_joint", []))
    base_state = list(getattr(robot_states, "base_state", []))
    print("RobotStates")
    print(f"    whole_body_joint[{len(whole_body_joint)}]: ", end="")
    print_vector(whole_body_joint)
    print()
    print(f"    base_state[{len(base_state)}]: ", end="")
    print_vector(base_state)
    print()


def print_get_jacobian_by_state_params(
    chain_name,
    target_frame,
    reference_frame,
    reference_robot_states,
):
    print("get_jacobian_by_state parameters:")
    print(f"  chain_name: {chain_name}")
    print(f"  target_frame: {target_frame}")
    print(f"  reference_frame: {reference_frame}")
    print("  reference_robot_states: ", end="")
    print_robot_states(reference_robot_states)


def print_jacobian(label, result):
    status, matrix = result
    print(f"[{label}] Status: {print_status(status)}")
    if status != gm.MotionStatus.SUCCESS or not matrix:
        print("Jacobian computation failed or returned an empty matrix.")
        return

    rows = len(matrix)
    cols = len(matrix[0])
    print(f"Jacobian matrix ({rows}x{cols}):")
    for row_index, row in enumerate(matrix):
        row_str = f"  row {row_index}:"
        for value in row:
            row_str += f" {value:10.5f}"
        print(row_str)


def make_fixed_whole_body_joint(dof):
    fixed_values = [
        0.3,
        0.8,
        0.5,
        0.0,
        0.0,
        0.1,
        -0.2,
        1.2,
        -0.8,
        0.4,
        -1.0,
        0.2,
        -0.6,
        0.0,
        -1.2,
        0.8,
        -0.4,
        1.0,
        -0.2,
        0.6,
        0.0,
    ]
    return [fixed_values[index % len(fixed_values)] for index in range(dof)]


def choose_chain_name(motion):
    support_chains = set(motion.get_supported_chains())
    if "left_arm" in support_chains:
        return "left_arm"
    if support_chains:
        return sorted(support_chains)[0]
    return "left_arm"


def run_example():
    motion = GalbotMotion()
    robot = GalbotRobot()
    robot_initialized = False

    if not motion.init():
        print("GalbotMotion initialization failed")
        return 1
    print("GalbotMotion initialized successfully")

    if not robot.init():
        print("GalbotRobot initialization failed")
        return 1
    robot_initialized = True
    print("GalbotRobot initialized successfully")

    try:
        time.sleep(3)

        chain_name = choose_chain_name(motion)
        target_frame = "EndEffector"
        reference_frame = "base_link"

        whole_body_dof = 21
        try:
            current_robot_state = motion.get_robot_states()
            if getattr(current_robot_state, "whole_body_joint", []):
                whole_body_dof = len(current_robot_state.whole_body_joint)
        except Exception as e:
            print(f"get_robot_states exception: {e}")

        reference_robot_states = gm.RobotStates()
        reference_robot_states.whole_body_joint = make_fixed_whole_body_joint(
            whole_body_dof
        )
        reference_robot_states.base_state = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]

        try:
            print("=== get_jacobian_by_state with explicit RobotStates ===")
            print_get_jacobian_by_state_params(
                chain_name,
                target_frame,
                reference_frame,
                reference_robot_states,
            )
            result = motion.get_jacobian_by_state(
                chain_name,
                target_frame,
                reference_frame,
                reference_robot_states,
            )
            print_jacobian("explicit RobotStates", result)
        except Exception as e:
            print(f"explicit RobotStates exception: {e}")

        try:
            print("=== get_jacobian_by_state with None RobotStates ===")
            print_get_jacobian_by_state_params(
                chain_name,
                target_frame,
                reference_frame,
                None,
            )
            result = motion.get_jacobian_by_state(
                chain_name,
                target_frame,
                reference_frame,
                None,
            )
            print_jacobian("None RobotStates", result)
        except Exception as e:
            print(f"None RobotStates exception: {e}")

        return 0
    finally:
        if robot_initialized:
            robot.request_shutdown()
            robot.wait_for_shutdown()
            robot.destroy()


if __name__ == "__main__":
    raise SystemExit(run_example())
