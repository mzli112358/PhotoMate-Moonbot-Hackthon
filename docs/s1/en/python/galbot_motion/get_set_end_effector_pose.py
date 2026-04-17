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

time.sleep(3)

reference_frame = "base_link"
target_frame = "EndEffector"
target_chain = "right_arm"
end_ee_link = "right_arm_end_effector_mount_link"
custom_param = gm.Parameter()

# Scenario 1: Get end-effector pose (basic version)
try:
    print(">> Scenario 1: Getting the basic end-effector pose...")
    status, pose = motion.get_end_effector_pose(
        end_effector_frame=end_ee_link,
        reference_frame=reference_frame
    )
    printStatus(status)
    assert status == gm.MotionStatus.SUCCESS, "Failed to get end-effector pose"
    print(f"✅ Basic end-effector pose retrieval succeeded: {pose}")
    time.sleep(0.8)
except Exception as e:
    print(f"❌ Scenario 1 exception: {e}")

# Scenario 2: specify chain name + custom frame to get end-effector pose
current_pose = None
try:
    print(">> Scenario 2: Getting pose by specified chain name...")
    status, current_pose = motion.get_end_effector_pose_on_chain(
        chain_name=target_chain,
        frame_id=target_frame,
        reference_frame=reference_frame
    )
    printStatus(status)
    assert status == gm.MotionStatus.SUCCESS, "Failed to get end-effector pose"
    print(f"✅ End-effector pose retrieval by specified chain succeeded: {current_pose}")
    time.sleep(0.8)
except Exception as e:
    print(f"❌ Scenario 2 exception: {e}")

# Scenario 3: Set end-effector pose (small offset from current pose)
try:
    print(">> Scenario 3: Setting end-effector pose...")
    if current_pose is None or len(current_pose) != 7:
        print("❌ Unable to get current pose; skipping Scenario 3")
    else:
        target_pose = list(current_pose)
        target_pose[2] -= 0.05  # Move downward 5 cm in z direction
        print(f"  Target pose: {target_pose}")

        status = motion.set_end_effector_pose(
            target_pose=target_pose,
            end_effector_frame=target_chain,
            reference_frame=reference_frame,
            enable_collision_check=False,
            is_blocking=True,
            timeout=5.0,
            params=custom_param
        )
        printStatus(status)
        if status == gm.MotionStatus.SUCCESS:
            print(f"✅ Motion execution completed")
except Exception as e:
    print(f"❌ Scenario 3 exception: {e}")

# Scenario 4: Get end-effector pose after execution to verify result
try:
    print(">> Scenario 4: Getting end-effector pose after motion...")
    status, pose = motion.get_end_effector_pose(
        end_effector_frame=end_ee_link,
        reference_frame=reference_frame
    )
    printStatus(status)
    if status == gm.MotionStatus.SUCCESS:
        print(f"✅ End-effector pose after motion: {pose}")
    time.sleep(0.8)
except Exception as e:
    print(f"❌ Scenario 4 exception: {e}")

robot.request_shutdown()
robot.wait_for_shutdown()
robot.destroy()
