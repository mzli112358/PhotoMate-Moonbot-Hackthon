import argparse
import time
from galbot_sdk.g1 import GalbotRobot, G1JointGroup, ControlStatus, JointCommand, DexHandType

DEXHAND_TYPE_MAP = {
    "inspire": DexHandType.INSPIRE,
    "brainco": DexHandType.BRAINCO,
    "sharpa": DexHandType.SHARPA,
}


def parse_dexhand_type(type_name: str) -> DexHandType:
    key = type_name.lower()
    if key not in DEXHAND_TYPE_MAP:
        raise ValueError(f"Unknown dexhand type '{type_name}', choose from: inspire, brainco, sharpa")
    return DEXHAND_TYPE_MAP[key]


def dexhand_joint_count(dexhand_type: DexHandType) -> int:
    return 22 if dexhand_type == DexHandType.SHARPA else 6


def make_dexhand_command(joint_count: int, position: float) -> list:
    commands = [JointCommand() for _ in range(joint_count)]
    for cmd in commands:
        cmd.position = position
    return commands


def default_positions(dexhand_type: DexHandType) -> tuple[float, float]:
    """Return (left_position, right_position) for the given dexhand model."""
    if dexhand_type == DexHandType.SHARPA:
        return 0.0, 0.0
    if dexhand_type == DexHandType.BRAINCO:
        return 50.0, 80.0
    return 500.0, 800.0


def main():
    parser = argparse.ArgumentParser(description="Set dexhand joint commands for left and right hands.")
    parser.add_argument(
        "--type",
        default="inspire",
        choices=DEXHAND_TYPE_MAP.keys(),
        help="Dexhand model: inspire (6 joints, 0-1000), brainco (6 joints, 0-100), sharpa (22 joints)",
    )
    args = parser.parse_args()
    dexhand_type = parse_dexhand_type(args.type)
    type_label = args.type.lower()

    robot = GalbotRobot()
    robot.init()
    print("Initialization succeeded")

    time.sleep(2)

    joint_count = dexhand_joint_count(dexhand_type)
    left_pos, right_pos = default_positions(dexhand_type)

    left_command = make_dexhand_command(joint_count, left_pos)
    status = robot.set_dexhand_command(
        G1JointGroup.left_dexhand, left_command, dexhand_type, False
    )
    if status != ControlStatus.SUCCESS:
        print(f"Set left {type_label} dexhand failed")
    else:
        print(f"Set left {type_label} dexhand success ({joint_count} joints, position={left_pos})")

    time.sleep(1 if dexhand_type == DexHandType.SHARPA else 2)

    right_command = make_dexhand_command(joint_count, right_pos)
    status = robot.set_dexhand_command(
        G1JointGroup.right_dexhand, right_command, dexhand_type, False
    )
    if status != ControlStatus.SUCCESS:
        print(f"Set right {type_label} dexhand failed")
    else:
        print(f"Set right {type_label} dexhand success ({joint_count} joints, position={right_pos})")

    robot.request_shutdown()
    robot.wait_for_shutdown()
    robot.destroy()
    print("Resources released successfully")


if __name__ == "__main__":
    main()
