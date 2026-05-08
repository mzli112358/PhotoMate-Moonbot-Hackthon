import time
from galbot_sdk.g1 import GalbotRobot, G1JointGroup, DexHandType


def print_sharpa_dexhand_state(hand_name, dexhand_state):
    """
    hand_name: str, e.g. "Left" or "Right"
    dexhand_state: DexhandState with timestamp_ns, joint_state, force_sensor_map
    """
    print(f"{hand_name} Sharpa dexhand full state:")
    print(f"Timestamp (ns): {dexhand_state.timestamp_ns}")

    joint_state = dexhand_state.joint_state
    print(f"  Joint states ({len(joint_state.joint_state_vec)} joints):")
    for i, js in enumerate(joint_state.joint_state_vec):
        print(
            f"    joint{i+1}: position={js.position:.4f}, velocity={js.velocity:.4f}, "
            f"effort={js.effort:.4f}, current={js.current:.4f}"
        )

    force_map = dexhand_state.force_sensor_map
    if not force_map:
        print("  (no force sensor data)")
    else:
        print(f"  Force sensors ({len(force_map)} sensors):")
        for sensor_name, effort in force_map.items():
            print(
                f"    {sensor_name} @ {effort.timestamp_ns}: "
                f"Fx={effort.force.x:.4f}, Fy={effort.force.y:.4f}, Fz={effort.force.z:.4f}, "
                f"Mx={effort.torque.x:.4f}, My={effort.torque.y:.4f}, Mz={effort.torque.z:.4f}"
            )


# Get and initialize the GalbotRobot singleton
robot = GalbotRobot()
robot.init()

# Program started, waiting for data
time.sleep(1)
print("Initialization succeeded")

# Get left Sharpa dexhand state
left_state = robot.get_dexhand_state(G1JointGroup.left_dexhand, DexHandType.SHARPA)
if left_state is None:
    print("get left Sharpa dexhand state error")
else:
    print_sharpa_dexhand_state("Left", left_state)

# Get right Sharpa dexhand state
right_state = robot.get_dexhand_state(G1JointGroup.right_dexhand, DexHandType.SHARPA)
if right_state is None:
    print("get right Sharpa dexhand state error")
else:
    print_sharpa_dexhand_state("Right", right_state)

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')
