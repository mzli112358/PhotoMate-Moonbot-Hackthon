import sys
import time

import galbot_sdk.s1 as gm
from galbot_sdk.s1 import GalbotMotion, GalbotRobot

motion = GalbotMotion()
robot = GalbotRobot()


def print_ik_result(label, status, joint_map, planner):
    print(f"[{label}] Status feedback: {planner.status_to_string(status)}")
    if status == gm.MotionStatus.SUCCESS:
        print("✅ IK computation succeeded! Joint angles obtained:")
        for name, joints in joint_map.items():
            print(f"  - Chain [{name}]: " + " ".join(str(v) for v in joints))
    else:
        print("❌ inverse kinematics failed, checkinput targetpose.")
    print("---------------------------------------------------")


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

    time.sleep(1)

    reference_frame = "base_link"
    target_frame = "EndEffector"
    target_chain = "left_arm"
    params = gm.Parameter()

    # Get current end-effector pose from robot as target for subsequent IK scenarios
    status, target_pose = motion.get_end_effector_pose_on_chain(
        target_chain, target_frame, reference_frame
    )
    if status != gm.MotionStatus.SUCCESS or len(target_pose) != 7:
        print("Failed to get current end-effector pose, cannot continue test.", file=sys.stderr)
        return -1

    print(f"Current {target_chain} End-effector pose: " + " ".join(str(v) for v in target_pose))
    print("---------------------------------------------------")

    one_chain = [target_chain]
    chain_with_torso = [target_chain, "torso"]
    error_chains = [target_chain, "torso", "head"]

    # Scenario 1: Single-chain inverse kinematics (using default parameters)
    try:
        print(">> Running Scenario 1: Single-chain IK test...")
        res = motion.inverse_kinematics(target_pose, one_chain)
        print_ik_result("Single-chain inverse kinematics", res[0], res[1], motion)
        time.sleep(0.8)
    except Exception as e:
        print(f"Scenario 1 exception: {e}", file=sys.stderr)

    # Scenario 2: Arm chain + torso inverse kinematics
    try:
        print(">> Running Scenario 2: Arm chain + torso IK test...")
        res = motion.inverse_kinematics(
            target_pose,
            chain_with_torso,
            target_frame,
            reference_frame,
            {},
            False,
            params,
        )
        print_ik_result("Arm + torso inverse kinematics", res[0], res[1], motion)
        time.sleep(0.8)
    except Exception as e:
        print(f"Scenario 2 exception: {e}", file=sys.stderr)

    # Scenario 3: invalid chain combination (expected to return INVALID_INPUT)
    try:
        print(">> Running Scenario 3: Invalid chain-combination test...")
        res = motion.inverse_kinematics(
            target_pose,
            error_chains,
            target_frame,
            reference_frame,
            {},
            False,
            params,
        )
        print_ik_result("Invalid chain combination detection", res[0], res[1], motion)
    except Exception as e:
        print(f"Scenario 3 exception: {e}", file=sys.stderr)

    # Scenario 4: Inverse kinematics with initial reference joint values (using current robot state)
    try:
        print(">> Running Scenario 4: IK test with initial reference values...")
        current_chain_joints = motion.get_chain_joint_state()
        print("  Current joint states:")
        for name, joints in current_chain_joints.items():
            print(f"    [{name}]: " + " ".join(str(v) for v in joints))

        res = motion.inverse_kinematics(
            target_pose,
            one_chain,
            target_frame,
            reference_frame,
            current_chain_joints,
            False,
            params,
        )
        print_ik_result("Inverse kinematics with reference values", res[0], res[1], motion)
        time.sleep(0.8)
    except Exception as e:
        print(f"Scenario 4 exception: {e}", file=sys.stderr)

    # Scenario 5: Inverse kinematics based on RobotStates (get full state from robot)
    try:
        print(">> Running Scenario 5: IK test based on RobotStates...")
        robot_states = motion.get_robot_states()
        ref_state = gm.RobotStates()
        ref_state.whole_body_joint = list(robot_states.whole_body_joint)
        ref_state.base_state = list(robot_states.base_state)
        ref_state.chain_name = target_chain

        print(f"  Number of whole-body joints: {len(ref_state.whole_body_joint)}")
        print(f"  Number of chassis states: {len(ref_state.base_state)}")

        res = motion.inverse_kinematics_by_state(
            target_pose,
            one_chain,
            target_frame,
            reference_frame,
            ref_state,
            False,
            params,
        )
        print_ik_result("RobotStates inverse kinematics", res[0], res[1], motion)
    except Exception as e:
        print(f"Scenario 5 exception: {e}", file=sys.stderr)

    robot.request_shutdown()
    robot.wait_for_shutdown()
    robot.destroy()
    print("Resources released.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
