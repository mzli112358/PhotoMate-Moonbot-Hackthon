import time
import galbot_sdk.g1 as gm
from galbot_sdk.g1 import GalbotMotion, GalbotRobot

# Get and initialize the GalbotMotion singleton
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

# Program started, waiting for data
time.sleep(2)

chain_joints = {
    "leg": [0.4992,1.4991,1.0005,0.0000,-0.0004],
    "head": [0.0000,0.0],
    "left_arm": [1.9999,-1.6000,-0.5999,-1.6999,0.0000,-0.7999,0.0000],
    "right_arm": [-2.0000,1.6001,0.6001,1.7000,0.0000,0.8000,0.0000]
}
chain_pose_baselink = {
    "leg": [0.0596,-0.0000,1.0327,0.5000,0.5003,0.4997,0.5000],
    "head": [0.0599,0.0002,1.4098,-0.7072,0.0037,0.0037,0.7069],
    "left_arm": [0.1267,0.2342,0.7356,0.0220,0.0127,0.0343,0.9991],
    "right_arm": [0.1267,-0.2345,0.7358,-0.0225,0.0126,-0.0343,0.9991]
}
whole_body_joint = [
    num for key in ["leg", "head", "left_arm", "right_arm"]
    for num in chain_joints[key]
]
base_state = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]
custom_param = gm.Parameter()

# Scenario 1: Multi-waypoint planning in Cartesian space (PoseState target)
try:
    # Construct target pose
    target_pose_state = gm.PoseState()
    target_pose_state.chain_name = "left_arm"

    # Construct waypoints (3 intermediate poses)
    waypoint_poses = [
        [0.1267,0.2342,0.7356,0.0220,0.0127,0.0343,0.9991],
        [0.2267,0.2342,0.7356,0.0220,0.0127,0.0343,0.9991],
        [0.3267,0.2342,0.7356,0.0220,0.0127,0.0343,0.9991],
        [0.4267,0.2342,0.7356,0.0220,0.0127,0.0343,0.9991],
    ]

    status, traj = motion.motion_plan_multi_waypoints(
        target=target_pose_state,
        waypoint_poses=waypoint_poses,
        enable_collision_check=False,
        params=custom_param
    )
    printStatus(status)
    assert status == gm.MotionStatus.SUCCESS, "Cartesian multi-waypoint single-chain planning failed"
    if traj != {}:
        print(f"✅ Cartesian waypoint single-chain planning succeeded: trajectory points={len(traj[target_pose_state.chain_name])}")
        time.sleep(0.8)
    else:
        print(f"⚠️ Return status is SUCCESS, but trajectory is empty; possibly already reached, check whether the target matches current state or is within tolerance")
except Exception as e:
    print(f"❌ Cartesian multi-point motion planning exception: {e}")

# Scenario 2: Multi-waypoint planning in joint space (JointStates target)
try:
    # Construct target pose
    target_joint = gm.JointStates()
    target_joint.chain_name = "left_arm"

    # Construct waypoints (3 intermediate poses)
    waypoints = [
        [0.1267,0.2342,0.7356,0.0220,0.0127,0.0343,0.9991],
        [0.2267,0.4342,0.7356,0.0220,0.0127,0.0343,0.9991],
        [0.3267,0.6342,0.7356,0.0220,0.0127,0.0343,0.9991],
        [0.4267,0.8342,0.7356,0.0220,0.0127,0.0343,0.9991]
    ]

    status, traj = motion.motion_plan_multi_waypoints(
        target=target_joint,
        waypoint_poses=waypoints,
        enable_collision_check=False,
        params=custom_param
    )
    printStatus(status)
    assert status == gm.MotionStatus.SUCCESS, "Cartesian multi-waypoint single-chain planning failed"
    if traj != {}:
        print(f"✅ Joint-waypoint single-chain planning succeeded: trajectory points={len(traj[target_pose_state.chain_name])}")
    else:
        print(f"⚠️ Return status is SUCCESS, but trajectory is empty; possibly already reached, check whether the target matches current state or is within tolerance")
except Exception as e:
    print(f"❌ Joint-space multi-point motion planning exception: {e}")

robot.request_shutdown()
robot.wait_for_shutdown()
robot.destroy()