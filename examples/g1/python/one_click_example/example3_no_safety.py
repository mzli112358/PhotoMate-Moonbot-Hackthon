"""
Note: When running this example, please confirm that the robot's navigation function `/data/galbot/bin/service_navigation_plan` has been loaded;
"""
try:
    from galbot_sdk.g1 import GalbotNavigation
    from galbot_sdk.g1 import GalbotRobot
except ImportError:
    print("Failed to import galbot_sdk, please install it first or check if it's in PYTHONPATH")
    exit(1)

import os

try:
    import numpy as np
except ImportError:
    os.system("pip install numpy")
    import numpy as np

try:
    from scipy.spatial.transform import Rotation as R
except ImportError:
    os.system("pip install scipy")
    from scipy.spatial.transform import Rotation as R

import time
from typing import Sequence, Dict

INIT_POSE_FILE = "/userdata/init_pose.txt"


def quat_normalize(q: np.ndarray) -> np.ndarray:
    q = np.array(q, dtype=np.float64)
    return q / np.linalg.norm(q)


def quat_conjugate(q: np.ndarray) -> np.ndarray:
    qx, qy, qz, qw = q
    return np.array([-qx, -qy, -qz, qw])


def quat_multiply(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return np.array([
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
    ])


def orientation_error_angle(A: np.ndarray, B: np.ndarray) -> float:
    qA = quat_normalize(A[3:7])
    qB = quat_normalize(B[3:7])
    q_err = quat_multiply(qB, quat_conjugate(qA))
    q_err = quat_normalize(q_err)
    qw = np.clip(q_err[3], -1.0, 1.0)
    return 2 * np.arccos(qw)


def calculate_error(pose1: Sequence[float], pose2: Sequence[float]) -> Dict[str, float]:
    A, B = np.array(pose1), np.array(pose2)
    pos_err = np.linalg.norm(A[:3] - B[:3])
    rot_err = orientation_error_angle(A, B)
    return {
        "position_error_norm": pos_err,
        "orientation_error_rad": rot_err,
        "orientation_error_deg": np.degrees(rot_err)
    }


def local_pose_to_global(start_pose: Sequence[float], local_pose: Sequence[float]):
    start_mat = np.eye(4)
    start_mat[:3, :3] = R.from_quat([start_pose[3], start_pose[4], start_pose[5], start_pose[6]]).as_matrix()
    start_mat[:3, 3] = [start_pose[0], start_pose[1], start_pose[2]]

    local_mat = np.eye(4)
    local_mat[:3, :3] = R.from_quat([local_pose[3], local_pose[4], local_pose[5], local_pose[6]]).as_matrix()
    local_mat[:3, 3] = [local_pose[0], local_pose[1], local_pose[2]]

    global_mat = start_mat @ local_mat
    return global_mat[:3, 3].tolist() + R.from_matrix(global_mat[:3, :3]).as_quat().tolist()


def demo_square_move(robot: GalbotRobot, nav: GalbotNavigation):
    try:
        start_pose = nav.get_current_pose()
    except Exception as e:
        print(f"Failed to get current pose: {e}")
        return

    local_pose = [0.5, 0.0, 0.0, 0.0, 0.0, 0.707, 0.707]
    try:
        for _ in range(4):
            cur_pose = nav.get_current_pose()
            goal_pose = local_pose_to_global(cur_pose, local_pose)
            if nav.check_path_reachability(goal_pose, cur_pose):
                retry_cnt = 3
                while True:
                    status = nav.navigate_to_goal(goal_pose, enable_collision_check=True, is_blocking=True, timeout=30)
                    time.sleep(0.5)
                    retry_cnt -= 1
                    if nav.check_goal_arrival() or retry_cnt < 0:
                        break
                    else:
                        print(f"Navigation failed, retrying...{retry_cnt}")
                print("navigate_to_goal return status:", status)
                print("Has arrived:", nav.check_goal_arrival())
            else:
                print("Path unreachable or unsafe")

        cur_pose = nav.get_current_pose()
        print(f"Current pose: {cur_pose}, Error from start pose: {calculate_error(cur_pose, start_pose)}")
    except Exception as e:
        print(f"Exception occurred during navigation: {e}")


def move_to_original(robot: GalbotRobot, nav: GalbotNavigation, init_pose: Sequence[float]):
    cur_pose = nav.get_current_pose()
    goal_pose = list(init_pose)

    try:
        if nav.check_path_reachability(goal_pose, cur_pose):
            retry_cnt = 3
            while True:
                status = nav.navigate_to_goal(goal_pose, enable_collision_check=True, is_blocking=True, timeout=30)
                time.sleep(0.5)
                retry_cnt -= 1
                if nav.check_goal_arrival() or retry_cnt < 0:
                    break
                else:
                    print(f"Navigation failed, retrying...{retry_cnt}")
            print("navigate_to_goal return status:", status)
            print("Has arrived:", nav.check_goal_arrival())
        else:
            print("Path unreachable or unsafe")
    except Exception as e:
        print(f"Exception occurred during navigation: {e}")


def load_init_pose_from_file(file_path: str) -> Sequence[float]:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if not content:
        raise ValueError(f"Init pose file is empty: {file_path}")
    # Support formats like:
    # [x, y, z, qx, qy, qz, qw]
    # x y z qx qy qz qw
    # x,y,z,qx,qy,qz,qw
    content = content.replace("[", " ").replace("]", " ").replace(",", " ")
    vals = [float(v) for v in content.split()]
    if len(vals) != 7:
        raise ValueError(f"Init pose must contain 7 values, got {len(vals)}")
    return vals


def main():
    try:
        robot = GalbotRobot()
        nav = GalbotNavigation()

        if robot.init():
            print("Robot initialization successful")
        else:
            print("Robot initialization failed")
        if nav.init():
            print("Navigation initialization successful")
        else:
            print("Navigation initialization failed")

        time.sleep(1)

        try:
            init_pose = load_init_pose_from_file(INIT_POSE_FILE)
            print(f"Loaded init pose from {INIT_POSE_FILE}: {init_pose}")
        except Exception as e:
            print(f"Failed to load init pose from file, fallback to origin pose: {e}")
            init_pose = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]

        is_localized = nav.is_localized()
        if not is_localized:
            print("Localization failed, attempting to re-localize with init pose from file...")
        time.sleep(3)
        while not is_localized:
            nav.relocalize(init_pose)
            time.sleep(0.5)
            is_localized = nav.is_localized()

        demo_square_move(robot, nav)
        move_to_original(robot, nav, init_pose)

    except Exception as e:
        print(f"Exception occurred: {e}")
    finally:
        robot.request_shutdown()
        robot.wait_for_shutdown()
        robot.destroy()


if __name__ == "__main__":
    main()
