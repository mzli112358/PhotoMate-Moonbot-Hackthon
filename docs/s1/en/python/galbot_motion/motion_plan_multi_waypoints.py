import time
import galbot_sdk.s1 as gm
from galbot_sdk.s1 import GalbotMotion, GalbotRobot

motion = GalbotMotion()
robot = GalbotRobot()

def printStatus(status):
        if(status == gm.MotionStatus.SUCCESS):
            print("Execution result: SUCCESS, execution successful")
        elif(status == gm.MotionStatus.TIMEOUT):
            print("Execution result: TIMEOUT, execution timed out")
        elif(status == gm.MotionStatus.FAULT):
            print("Execution result: FAULT, a fault occurred and execution cannot continue")
        elif(status == gm.MotionStatus.INVALID_INPUT):
            print("Execution result: INVALID_INPUT, input parameters do not meet requirements")
        elif(status == gm.MotionStatus.INIT_FAILED):
            print("Execution result: INIT_FAILED, failed to create internal communication components")
        elif(status == gm.MotionStatus.IN_PROGRESS):
            print("Execution result: IN_PROGRESS, in motion but not yet in position")
        elif(status == gm.MotionStatus.STOPPED_UNREACHED):
            print("Execution result: STOPPED_UNREACHED, stopped but target not reached")
        elif(status == gm.MotionStatus.DATA_FETCH_FAILED):
            print("Execution result: DATA_FETCH_FAILED, failed to fetch data")
        elif(status == gm.MotionStatus.PUBLISH_FAIL):
            print("Execution result: PUBLISH_FAIL, data transmission failed")
        elif(status == gm.MotionStatus.COMM_DISCONNECTED):
            print("Execution result: COMM_DISCONNECTED, connection failed")

if motion.init():
    print("GalbotMotion initialized successfully")
else:
    print("GalbotMotion initialization failed")
if robot.init():
    print("GalbotRobot initialized successfully")
else:
    print("GalbotRobot initialization failed")

time.sleep(2)

custom_param = gm.Parameter()
target_chain = "left_arm"

# Scenario 1: Multi-waypoint planning in Cartesian space (PoseState target)
try:
    print(">> Running Scenario 1: Multi-waypoint planning in Cartesian space...")

    target_pose_state = gm.PoseState()
    target_pose_state.chain_name = target_chain

    waypoint_poses = [
        [0.1267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991],
        [0.2267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991],
        [0.3267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991],
        [0.4267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991],
    ]

    status, traj = motion.motion_plan_multi_waypoints(
        target=target_pose_state,
        waypoint_poses=waypoint_poses,
        enable_collision_check=False,
        params=custom_param
    )
    printStatus(status)
    if status == gm.MotionStatus.SUCCESS and traj != {}:
        print(f"✅ Cartesian multi-point planning succeeded: trajectory points={len(traj[target_chain])}")
        time.sleep(0.8)
    elif status == gm.MotionStatus.SUCCESS:
        print(f"⚠️ Return status is SUCCESS, but trajectory is empty")
    else:
        print(f"❌ Cartesian multi-point planning failed")
except Exception as e:
    print(f"❌ Scenario 1 exception: {e}")

# Scenario 2: Multi-waypoint planning in joint space (JointStates target)
try:
    print(">> Running Scenario 2: Multi-waypoint planning in joint space...")

    target_joint = gm.JointStates()
    target_joint.chain_name = target_chain

    waypoints = [
        [0.1267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991],
        [0.2267, 0.4342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991],
        [0.3267, 0.6342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991],
        [0.4267, 0.8342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991]
    ]

    status, traj = motion.motion_plan_multi_waypoints(
        target=target_joint,
        waypoint_poses=waypoints,
        enable_collision_check=False,
        params=custom_param
    )
    printStatus(status)
    if status == gm.MotionStatus.SUCCESS and traj != {}:
        print(f"✅ Joint-space multi-point planning succeeded: trajectory points={len(traj[target_chain])}")
    elif status == gm.MotionStatus.SUCCESS:
        print(f"⚠️ Return status is SUCCESS, but trajectory is empty")
    else:
        print(f"❌ Joint-space multi-point planning failed")
except Exception as e:
    print(f"❌ Scenario 2 exception: {e}")

robot.request_shutdown()
robot.wait_for_shutdown()
robot.destroy()
