import time
from galbot_sdk.g1 import GalbotRobot, G1JointGroup, DexHandType


def print_dexhand_state(hand_name, dexhand_state):
    """
    hand_name: str, e.g. "Left" or "Right"
    dexhand_state: DexhandState with timestamp_ns and joint_state.joint_state_vec
    """
    print(f"{hand_name} dexterous hand state:")
    print(f"Timestamp (ns): {dexhand_state.timestamp_ns}")
    for i, js in enumerate(dexhand_state.joint_state.joint_state_vec):
        print(
            f"  {hand_name.lower()}_dexhand_joint{i+1}: "
            f"position={js.position:.4f}, velocity={js.velocity:.4f}, "
            f"acceleration={js.acceleration:.4f}, "
            f"effort={js.effort:.4f}, current={js.current:.4f}"
        )


# Get and initialize the GalbotRobot singleton
robot = GalbotRobot()
robot.init()

# Program started, waiting for data
time.sleep(1)
print("Initialization succeeded")

# Get left dexhand state
left_state = robot.get_dexhand_state(G1JointGroup.left_dexhand, DexHandType.INSPIRE)
if left_state is None:
    print("get left dexterous hand state error")
else:
    print_dexhand_state("Left", left_state)

# Get right dexhand state
right_state = robot.get_dexhand_state(G1JointGroup.right_dexhand, DexHandType.INSPIRE)
if right_state is None:
    print("get right dexterous hand state error")
else:
    print_dexhand_state("Right", right_state)

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')
