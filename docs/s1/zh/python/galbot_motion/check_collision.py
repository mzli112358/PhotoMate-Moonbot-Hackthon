import sys

import galbot_sdk.s1 as gm
from galbot_sdk.s1 import GalbotMotion, GalbotRobot, GalbotNavigation

# NOTE:
# - GalbotNavigation (galbotNav) may use real-time obstacle perception/avoidance during navigation (deployment dependent).
# - GalbotMotion does NOT provide real-time obstacle perception today; Motion collision uses self-collision +
#   manually loaded obstacles (add_obstacle/attach_target_object).

motion = GalbotMotion()
robot = GalbotRobot()
navigation = GalbotNavigation()

if not motion.init():
    print("GalbotMotion init FAILED", file=sys.stderr)
    sys.exit(1)
if not robot.init():
    print("GalbotRobot init FAILED", file=sys.stderr)
    sys.exit(1)
if not navigation.init():
    print("GalbotNavigation init FAILED", file=sys.stderr)
    sys.exit(1)

chain_joints = {
    "torso": [1.1],
    "head": [0.0000, -0.26],
    "left_arm": [-0.47, -0.94, -0.54, -1.92, 0.2, 0.0, 0.0],
    "right_arm": [0.47, 0.94, 0.54, 1.92, -0.2, 0.0, 0.0],
}

whole_body_joint = [
    num for key in ["torso", "head", "left_arm", "right_arm"] for num in chain_joints[key]
]
base_state = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]
bad_left_arm_joint = [1.99995, -1.60004, 0.599905, -1.69994, 0, -0.799924, 0]
custom_param = gm.Parameter()

try:
    print(">> Running collision check...")

    # Construct a RobotStates list for collision checking
    check_states = []

    # status 0: RobotStates
    state0 = gm.RobotStates()
    state0.whole_body_joint = whole_body_joint
    state0.base_state = base_state
    check_states.append(state0)

    # status 1: JointStates
    state1 = gm.JointStates()
    state1.chain_name = "left_arm"
    state1.joint_positions = bad_left_arm_joint
    check_states.append(state1)

    status, collision_results = motion.check_collision(
        start=check_states,
        enable_collision_check=True,
        params=custom_param,
    )

    print(f"Status: {motion.status_to_string(status)}")

    if status == gm.MotionStatus.SUCCESS:
        print("OK: collision check finished (false=no collision, true=collision):")
        for i, collided in enumerate(collision_results):
            label = "COLLISION" if collided else "NO COLLISION"
            print(f"  - status [{i}]: {label}")
    else:
        print("ERROR: collision check returned failure.", file=sys.stderr)

except Exception as e:
    print(f"ERROR: collision check exception: {e}", file=sys.stderr)

robot.request_shutdown()
robot.wait_for_shutdown()
robot.destroy()
