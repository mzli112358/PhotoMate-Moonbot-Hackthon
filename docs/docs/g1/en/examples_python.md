
# Python Examples

This file provides brief examples for the publicly available functions and types in the API, demonstrating how to use these interfaces.

## Robot Joint Names (G1 2.2)

### Joint Group List

Robot joint group names include: `["head", "left_arm", "right_arm", "leg", "left_gripper", "right_gripper", "left_suction_cup", "right_suction_cup"]`

### Detailed Information for Each Joint Group

| Joint Group | English Name | Number of Joints | Joint Name List |
|-------------|--------------|------------------|-----------------|
| Head | head | 2 | `head_joint1`, `head_joint2` |
| Legs | leg | 5 | `leg_joint1`, `leg_joint2`, `leg_joint3`, `leg_joint4`, `leg_joint5` |
| Left Arm | left_arm | 7 | `left_arm_joint1`, `left_arm_joint2`, `left_arm_joint3`, `left_arm_joint4`, `left_arm_joint5`, `left_arm_joint6`, `left_arm_joint7` |
| Right Arm | right_arm | 7 | `right_arm_joint1`, `right_arm_joint2`, `right_arm_joint3`, `right_arm_joint4`, `right_arm_joint5`, `right_arm_joint6`, `right_arm_joint7` |
| Left Gripper | left_gripper | 1 | `left_gripper_joint1` |
| Right Gripper | right_gripper | 1 | `right_gripper_joint1` |
| Left Suction Cup | left_suction_cup | 1 | `left_suction_cup_joint1` |
| Right Suction Cup | right_suction_cup | 1 | `right_suction_cup_joint1` |


### How To Use `joint_groups` Correctly

A "joint group" is the SDK control unit instead of a single joint. This grouping is used to ensure:

- Kinematic-chain consistency: arm/head/leg joints are validated and controlled as one chain.
- Deterministic command ordering: `joint_groups` are expanded to concrete joints in group order.
- Group-level validation: active/passive group constraints are checked before execution.

Usage rules:

1. Prefer `joint_groups` when controlling full chains (head/arm/leg/gripper/suction cup).
2. If `joint_names` is provided, it takes precedence over `joint_groups`.
3. If both `joint_groups` and `joint_names` are empty, SDK defaults to all active body joint groups.
4. To avoid hard-coded mistakes, call `get_joint_group_names()` and `get_joint_names(True, groups)` first.

### Typical Group Scenarios (G1)

| Joint Group | Typical Scenario |
|-------------|------------------|
| `head` | Head orientation / camera aiming |
| `left_arm` / `right_arm` | Arm reaching and manipulation |
| `leg` | Lower-body posture adjustment |
| `left_gripper` / `right_gripper` | Grasp width control |
| `left_suction_cup` / `right_suction_cup` | Vacuum pick and place |

## Sensor Types and Frames

**For sensor data access** (`get_rgb_data`, `get_depth_data`, `get_imu_data`, `get_lidar_data`), use the `SensorType` enum to specify which sensor to query. Available SensorType enums are documented in: **[Python API Reference > SensorType](api_python_reference.md#sensortype-enum)**.

**For sensor extrinsic calibration**, there are two methods:
- **[get_sensor_extrinsic()](api_python_reference.md#galbotrobot-get_sensor_extrinsic-function)**: SDK internally maps frame IDs, pass SensorType directly
- **[get_transform()](api_python_reference.md#galbotrobot-get_transform-function)**: Requires explicit frame names. The second column below lists frame IDs for each sensor.

| SensorType | Frame ID |
|------------|----------|
| `HEAD_LEFT_CAMERA` | `head_left_camera_color_optical_frame` |
| `HEAD_RIGHT_CAMERA` | `head_right_camera_color_optical_frame` |
| `LEFT_ARM_CAMERA` | `left_arm_camera_color_optical_frame` |
| `LEFT_ARM_DEPTH_CAMERA` | `left_arm_camera_color_optical_frame` |
| `RIGHT_ARM_CAMERA` | `right_arm_camera_color_optical_frame` |
| `RIGHT_ARM_DEPTH_CAMERA` | `right_arm_camera_color_optical_frame` |
| `BASE_LIDAR` | `lidar_base_link` |
| `TORSO_IMU` | `imu_base_link` |
| `BASE_ULTRASONIC` | — (no TF frame) |
| `LEFT_FRONT_SURROUND_CAMERA` | `left_front_surround_color_optical_frame` |
| `RIGHT_FRONT_SURROUND_CAMERA` | `right_front_surround_color_optical_frame` |
| `LEFT_REAR_SURROUND_CAMERA` | `left_rear_surround_color_optical_frame` |
| `RIGHT_REAR_SURROUND_CAMERA` | `right_rear_surround_color_optical_frame` |

> **Note**: Call **[get_frame_names()](api_python_reference.md#galbotrobot-get_frame_names-function)** to get all available coordinate frames.

## Class: GalbotRobot

Tips: If you get data immediately after program startup, the data may not be ready right away. You may sleep for a few seconds as appropriate.

### Get Instance and Initialize (get_instance && init)

**Applicable Scenarios**: During program startup, get the robot singleton and complete SDK initialization. Must be called before using other APIs.

```python title="examples/python/galbot_robot/get_instance.py"
from galbot_sdk.g1 import GalbotRobot
import time

# Get GalbotRobot
robot = GalbotRobot()

state = robot.init()
if not state:
    print("Initialization failed")
else:
    print("Initialization succeeded")

while robot.is_running():
    # business logic
    time.sleep(1)
    break

# Send exit signal to exit the program
robot.request_shutdown()
# Wait for exit state
robot.wait_for_shutdown()
# Release SDK-related resources
robot.destroy()
```

### Log interface

**Applicable Scenarios**: Output logs using the SDK's built-in logging system, unifying log levels and formats.

```python title="examples/python/galbot_robot/logger_example.py"
import galbot_sdk

cfg = {
    # Log storage directory; if empty, defaults to ~/galbot_sdk_log/user_log
    "path": "",

    # Log file name; if empty, defaults to <process_name>_<current_time>_<pid>_<thread_id>.log
    "file_name": "",

    # log bytes, log size,
    "file_max_size": 10 * 1024 * 1024,  # 10MB

    # Maximum rotating log files; oldest file is overwritten when limit exceeded
    "file_max_num": 5,

    # Whether to output logs to console; default is False
    "console_output": True,

    # Log output level, available values: debug, info, warning, error, critical
    "level": "info",
}

galbot_sdk.init_logger(cfg)

# Write log
galbot_sdk.debug("Debug example")
galbot_sdk.info("Info example")
galbot_sdk.warning("Warning example")
galbot_sdk.error("Error example")
galbot_sdk.critical("Critical example")
```

### Set Joint Positions (set_joint_positions)

**Applicable Scenarios**: Single-point movement, low-frequency position control tasks. This interface performs velocity-limited trajectory interpolation internally, making it suitable for one-time movement to target joint angles.

> **WARNING**: This interface is **NOT suitable** for high-frequency joint control scenarios with model inference output! Each call to this interface produces a new trajectory interpolation, continuous calls will result in discontinuous motion and delay.
>
> If you are working on a **model inference** scenario, please use [`set_joint_commands`](#set_joint_commands) or [`set_joint_commands_batch`](#set_joint_commands_batch) to issue joint commands directly.

```python title="examples/python/galbot_robot/set_joint_positions.py"
import time
from galbot_sdk.g1 import GalbotRobot
from galbot_sdk.g1 import ControlStatus

# Get and initialize the GalbotRobot singleton
robot = GalbotRobot()
robot.init()
print('Initialization succeeded')

# Program started, waiting for data
time.sleep(2)

# Set head joints to 0.2, 0.2, block and wait for motion to complete, max timeout 10s
joint_pos = [0.2, 0.2]
# Set head joint group; if empty, defaults to whole body joints ["leg", "head", "left_arm", "right_arm"]
joint_groups = ["head"]
# Whether to block until joints reach target
is_blocking = True
# Limit joint max speed to 0.1rad/s
max_speed = 0.1
# Maximum blocking wait time
timeout_s = 10

status = robot.set_joint_positions(
    joint_pos, joint_groups, [], is_blocking, max_speed, timeout_s
)

if status != ControlStatus.SUCCESS:
    print("Joint angle setting failed")
else:
    print('Joint angle setting succeeded')

time.sleep(1)

# Use specific joint names for control; this parameter overrides joint_groups
joint_names = ["head_joint1", "head_joint2"]
joint_pos = [0.0, 0.0]

status = robot.set_joint_positions(
    joint_pos, [], joint_names, is_blocking, max_speed, timeout_s
)

if status != ControlStatus.SUCCESS:
    print("Joint angle setting failed")
else:
    print('Joint angle setting succeeded')

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')
```

### Set Gripper Command (set_gripper_command)

**Applicable Scenarios**: Control gripper opening and closing. Supports both position control and torque control modes.

```python title="examples/python/galbot_robot/set_gripper_command.py"
import time
from galbot_sdk.g1 import GalbotRobot, G1JointGroup, ControlStatus

# Get and initialize the GalbotRobot singleton
robot = GalbotRobot()
robot.init()
print('Initialization succeeded')
# Program started, waiting for data
time.sleep(2)

# Set left gripper width to 0.02m, speed 0.05m, torque 10N, block until gripper reaches position
status = robot.set_gripper_command(
    G1JointGroup.left_gripper, 0.02, 0.05, 10, False
)
if status != ControlStatus.SUCCESS:
    print("Set gripper failed")
else:
    print('Set gripper success')

# Set left gripper width to 0.1m, speed 0.05m, torque 10N, block until gripper reaches position
status = robot.set_gripper_command(
    G1JointGroup.left_gripper, 0.1, 0.05, 10, False
)

if status != ControlStatus.SUCCESS:
    print("Set gripper failed")
else:
    print('Set gripper success')

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')
```

### Set Suction Cup Command (set_suction_cup_command)

**Applicable Scenarios**: Control suction cup to suck/release objects, get current suction cup status.

```python title="examples/python/galbot_robot/set_suction_cup_command.py"
from galbot_sdk.g1 import GalbotRobot
from galbot_sdk.g1 import G1JointGroup, ControlStatus
import time

# Get and initialize the GalbotRobot singleton
robot = GalbotRobot()
robot.init()
time.sleep(1)
print('Initialization succeeded')

# Set suction cup joint group (right suction cup)
joint_group = G1JointGroup.right_suction_cup

# Whether to activate suction cup
activate = True  # True: activate suction cup, False: deactivate suction cup

# Send suction cup control command
status = robot.set_suction_cup_command(
    joint_group,
    activate
)

# Check execution results
if status != ControlStatus.SUCCESS:
    print("Set suction cup failed")
else:
    print("Set suction cup succeeded")

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')
```

### Stop Trajectory Execution (stop_trajectory_execution)

**Applicable Scenarios**: Stop currently executing joint trajectory and interrupt ongoing motion.

```python title="examples/python/galbot_robot/stop_trajectory_execution.py"
from galbot_sdk.g1 import GalbotRobot
from galbot_sdk.g1 import ControlStatus
import time

# Get and initialize the GalbotRobot singleton
robot = GalbotRobot()
robot.init()
time.sleep(2)
print("Initialization succeeded")

# Stop trajectory execution
while True:
    status = robot.stop_trajectory_execution()

    # Check execution results
    if status == ControlStatus.SUCCESS:
        print('Stop trajectory execution succeeded')
        break

    print("Trajectory stop failed, retrying...")

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')
```

### Execute Joint Trajectory (execute_joint_trajectory)

**Applicable Scenarios**: Execute a predefined joint-space trajectory with multiple waypoints. The SDK executes the entire trajectory according to time nodes.

```python title="examples/python/galbot_robot/execute_joint_trajectory.py"
from galbot_sdk.g1 import GalbotRobot
from galbot_sdk.g1 import G1JointGroup, ControlStatus, Trajectory, TrajectoryPoint, JointCommand
import time
import numpy as np
from typing import List

# Generate trajectory point with position and time info
def generate_target_point(q: List[float], target_time: float = 10):
    """Generate target for joints"""
    joint_position = TrajectoryPoint()
    joint_position.time_from_start_second = target_time
    joint_command_vec = []
    for joint in q:
        joint_cmd = JointCommand()
        joint_cmd.position = joint
        joint_command_vec.append(joint_cmd)
    joint_position.joint_command_vec = joint_command_vec
    return joint_position

def generate_target_trajectory(trajectory, joint_groups=[], joint_names=[], dt=0.008):
    """Generate trajectory for joints"""
    if trajectory is None or np.ndim(trajectory) != 2 or len(trajectory) == 0:
        return None

    # Create Trajectory
    traj = Trajectory()
    traj.joint_groups = joint_groups
    traj.joint_names = joint_names

    time = 0.0
    points = []
    for state in trajectory:
        time += dt
        # Create single trajectory point
        traj_point = generate_target_point(state, time)
        points.append(traj_point)

    traj.points = points
    return traj

# Trajectory execution function
def traj_exec():
    # Get GalbotRobot singleton and initialize; only needs to be initialized once
    robot = GalbotRobot()
    robot.init()
    time.sleep(1)
    print("Initialization succeeded")

    head_traj = np.linspace(
        [0.0, 0.0],
        [0.5, 0.0],
        num=200,
    )
    # Whether to block and wait for trajectory execution to complete
    is_block = True
    # Specify which joint group trajectory to execute
    joint_groups = ["head"]
    # Execute specified joint trajectory; if provided, overrides joint_groups parameters
    joint_names = []
    status = robot.execute_joint_trajectory(generate_target_trajectory(head_traj.tolist(), joint_groups, joint_names), is_block)

    # Check execution results
    if status != ControlStatus.SUCCESS:
        print("Trajectory execution failed")
    else:
        print("Trajectory execution succeeded")

    # send SIGINT shutdown signal
    robot.request_shutdown()
    # Wait until entering shutdown state
    robot.wait_for_shutdown()
    # Perform SDK resource release
    robot.destroy()
    print('Resources released successfully')

traj_exec()
```

### Set Joint Commands (set_joint_commands) {#set_joint_commands}

**Applicable Scenarios**: High-frequency joint control, such as **model inference output** (each inference step outputs one frame of joint commands), custom trajectory tracking. Issues joint commands directly to the low-level controller without extra interpolation.

```python title="examples/python/galbot_robot/set_joint_commands_example.py"
import time
from galbot_sdk.g1 import GalbotRobot
from galbot_sdk.g1 import JointCommand

def head_high_frequency_control():
    """
    Head high-frequency control example
    """

    control_frequency = 100.0  # Hz
    dt = 1.0 / control_frequency
    duration = 4.0  # Control for 4 seconds

    amplitude = 0.3  # Maximum oscillation amplitude (rad)
    frequency = 0.5  # Sine frequency (Hz)
    # Joint group name to control
    joint_groups = ["head"]
    # Fill this field to control specific joints, which will override joint_groups. If empty, controls all joints in joint_groups by default
    joint_names = []

    print("Start high-frequency head control")

    joint_commands = [JointCommand(), JointCommand()]

    start_time = time.time()

    while True:
        current_time = time.time() - start_time
        if current_time > duration:
            break

        # Generate sine trajectory
        target_position = amplitude * math.sin(
            2 * math.pi * frequency * current_time
        )

        # Set head joint angles
        joint_commands[0].position = target_position
        joint_commands[1].position = target_position
        print(f"current: {current_time:.2f}s, target: {target_position:.3f} rad")

        # Expected arrival time
        time_from_start_sec = 0.0

        execution_status = GalbotRobot().set_joint_commands(
            joint_commands,
            joint_groups,
            joint_names,
            time_from_start_sec
        )

        # Sleep at a fixed interval
        time.sleep(dt)

    print("end")

def main():
    # Get and initialize the GalbotRobot singleton
    robot = GalbotRobot()

    if robot.init():
        print("System initialized successfully!")
    else:
        print("System initialization failed!")
        return

    # Program started, waiting for data
    time.sleep(2)
    
    head_high_frequency_control()

    # Exit system and release SDK resources
    robot.request_shutdown()
    robot.wait_for_shutdown()
    robot.destroy()
    print("Program exited")


if __name__ == "__main__":
    main()
```

### Set Joint Commands in Batch Mode (set_joint_commands_batch) {#set_joint_commands_batch}

**Applicable Scenarios**: Batch issue multiple future frames of joint commands, suitable for scenarios where motion prediction models output multiple steps at once, improving control frequency and continuity.

```python title="examples/python/galbot_robot/set_joint_commands_batch.py"
from galbot_sdk.g1 import GalbotRobot, G1JointGroup, ControlStatus, Trajectory, TrajectoryPoint, JointCommand
import time
import numpy as np
from typing import List

# Generate trajectory point with position and time info
def generate_target_point(q: List[float], target_time: float = 10):
    """Generate target for joints"""
    joint_position = TrajectoryPoint()
    joint_position.time_from_start_second = target_time
    joint_command_vec = []
    for joint in q:
        joint_cmd = JointCommand()
        joint_cmd.position = joint
        joint_cmd.velocity = 0.0
        joint_cmd.acceleration = 0.0
        joint_cmd.effort = 0.0
        # joint_cmd.Kp = 0.0
        # joint_cmd.Kd = 0.0
        joint_command_vec.append(joint_cmd)
    joint_position.joint_command_vec = joint_command_vec
    return joint_position

def generate_batch_trajectory(trajectory, joint_groups=[], joint_names=[], dt=0.008):
    """Generate batch trajectory for joints"""
    if trajectory is None or np.ndim(trajectory) != 2 or len(trajectory) == 0:
        return None

    # Create Trajectory
    traj = Trajectory()
    traj.joint_groups = joint_groups
    traj.joint_names = joint_names

    time = 0.0
    points = []
    for state in trajectory:
        time += dt
        # Create single trajectory point
        traj_point = generate_target_point(state, time)
        points.append(traj_point)

    traj.points = points
    return traj

# Batch set-joint-command function
def batch_commands_exec():
    # Get GalbotRobot singleton and initialize; only needs to be initialized once
    robot = GalbotRobot()
    robot.init()
    time.sleep(1)
    print("Initialization succeeded")

    # Generate batched trajectory data (joint commands at multiple time points)
    head_traj = np.linspace(
        [0.0, 0.0],
        [0.5, 0.0],
        num=10,  # Number of batch trajectory points
    )
    # Specify which joint group trajectory to execute
    joint_groups = ["head"]
    # Execute specified joint trajectory; if provided, overrides joint_groups parameters
    joint_names = []
    
    # Batch set joint commands (non-blocking, returns immediately)
    status = robot.set_joint_commands_batch(generate_batch_trajectory(head_traj.tolist(), joint_groups, joint_names))

    # Check execution results
    if status != ControlStatus.SUCCESS:
        print("Batch command submission failed")
    else:
        print("Batch commands submitted, executing in background (non-blocking)")

    # Wait for a while to let the command execute
    time.sleep(1)

    # send SIGINT shutdown signal
    robot.request_shutdown()
    # Wait until entering shutdown state
    robot.wait_for_shutdown()
    # Perform SDK resource release
    robot.destroy()
    print('Resources released successfully')

batch_commands_exec()
```

### Publish Raw Target Directly (publish_target)

**Applicable Scenarios**: Advanced users construct a `SingoriXTarget` directly and publish it through the WBCS publish channel. Suitable for high-frequency raw target streaming and one-shot dispatch of mixed joint/task targets.

```python title="examples/python/galbot_robot/publish_target_example.py"
"""
G1 PublishTarget menu example for SDK mirror SingoriXTarget.

This example shows how to construct `SingoriXTarget` directly at the Python SDK
layer and send it to the low-level WBCS through `publish_target()`.

1. Joint-space commands are written into `target_group_trajectory_map`
2. Chassis pose / twist style task-space commands are written into `target_task_trajectory_map`
3. One `SingoriXTarget` can contain both joint trajectory and task trajectory
4. The current SDK does not automatically switch the chassis controller, so
   pose / twist / mixed scenes explicitly call `switch_controller(...)`
5. The base twist scene automatically sends a zero-twist target after the
   configured duration to stop the chassis
"""

import math
import time

from galbot_sdk.g1 import (
    ControlStatus,
    G1ControllerName,
    G1JointGroup,
    GalbotRobot,
    GroupCommand,
    JointCommand,
    Pose,
    SingoriXTarget,
    TargetConfig,
    TargetGroupTrajectory,
    TargetSampling,
    TargetTaskTrajectory,
    TaskCommand,
    Twist,
    Vector3,
    FrameTriad,
    TARGET_DATA_DEFAULT,
    TARGET_DATA_FRAME_POSE,
    TARGET_DATA_FRAME_TWIST,
    TARGET_TYPE_DEFAULT,
    TARGET_TYPE_OVERRIDE,
    TARGET_TYPE_PROVERRIDE,
)


CHASSIS_TASK_NAME = "chassis"
CHASSIS_SUBTASK_POSE = "chassis_pose"
CHASSIS_SUBTASK_TWIST = "chassis_twist"


def now_ns():
    return time.time_ns()


def status_to_string(status):
    return getattr(status, "name", str(status))


def yaw_to_quaternion(yaw):
    return [0.0, 0.0, math.sin(yaw * 0.5), math.cos(yaw * 0.5)]


def make_empty_target():
    target = SingoriXTarget()
    target.header.timestamp_ns = now_ns()
    target.header.frame_id = "base_link"
    return target


def make_group_target_config():
    config = TargetConfig()
    config.target_data = TARGET_DATA_DEFAULT
    config.target_type = TARGET_TYPE_PROVERRIDE
    config.target_sampling = TargetSampling.TARGET_SAMPLING_DEFAULT
    config.target_priority = 1
    return config


def make_pose_target_config():
    config = TargetConfig()
    config.target_data = TARGET_DATA_FRAME_POSE
    config.target_type = TARGET_TYPE_PROVERRIDE
    config.target_sampling = TargetSampling.TARGET_SAMPLING_LINEAR_INTERPOLATE
    config.target_priority = 1
    return config


def make_twist_target_config():
    config = TargetConfig()
    config.target_data = TARGET_DATA_FRAME_TWIST
    config.target_type = TARGET_TYPE_OVERRIDE
    config.target_sampling = TargetSampling.TARGET_SAMPLING_DIRECT_PASS
    config.target_priority = 1
    return config


def make_joint_command(position):
    command = JointCommand()
    command.position = position
    command.velocity = 0.0
    command.acceleration = 0.0
    command.effort = 0.0
    return command


def make_vector3(x, y, z):
    vec = Vector3()
    vec.x = x
    vec.y = y
    vec.z = z
    return vec


def build_joint_target(group_name, joint_names, positions, time_from_start_s):
    target = make_empty_target()

    group_traj = TargetGroupTrajectory()
    group_traj.target_config = make_group_target_config()
    group_traj.joint_names = list(joint_names)

    command = GroupCommand()
    command.time_from_start_s = time_from_start_s
    command.joint_commands = [make_joint_command(position) for position in positions]
    group_traj.group_commands = [command]

    target.target_group_trajectory_map = {group_name: group_traj}
    return target


def build_chassis_pose_target(x, y, yaw, time_from_start_s, frame_id="odom", reference_frame_id="odom"):
    target = make_empty_target()

    task_traj = TargetTaskTrajectory()
    task_traj.target_config = make_pose_target_config()
    task_traj.group_names = [G1JointGroup.chassis]
    task_traj.subtask_names = [CHASSIS_SUBTASK_POSE]

    triad = FrameTriad()
    triad.header.timestamp_ns = now_ns()
    triad.header.frame_id = frame_id
    triad.body_frame_id = "base_link"
    triad.reference_frame_id = reference_frame_id
    triad.pose = Pose([x, y, 0.0], yaw_to_quaternion(yaw))

    command = TaskCommand()
    command.time_from_start_s = time_from_start_s
    command.subtask_commands = [triad]
    task_traj.task_commands = [command]

    target.target_task_trajectory_map = {CHASSIS_TASK_NAME: task_traj}
    return target


def build_chassis_twist_target(vx, vy, wz, time_from_start_s):
    target = make_empty_target()

    task_traj = TargetTaskTrajectory()
    task_traj.target_config = make_twist_target_config()
    task_traj.group_names = [G1JointGroup.chassis]
    task_traj.subtask_names = [CHASSIS_SUBTASK_TWIST]

    twist = Twist()
    twist.linear = make_vector3(vx, vy, 0.0)
    twist.angular = make_vector3(0.0, 0.0, wz)

    triad = FrameTriad()
    triad.header.timestamp_ns = now_ns()
    triad.header.frame_id = "base_link"
    triad.body_frame_id = "base_link"
    triad.reference_frame_id = "base_link"
    triad.twist = twist

    command = TaskCommand()
    command.time_from_start_s = time_from_start_s
    command.subtask_commands = [triad]
    task_traj.task_commands = [command]

    target.target_task_trajectory_map = {CHASSIS_TASK_NAME: task_traj}
    return target


def build_stop_twist_target():
    return build_chassis_twist_target(0.0, 0.0, 0.0, 0.1)


def merge_targets(targets):
    merged = make_empty_target()
    group_map = {}
    task_map = {}
    for target in targets:
        group_map.update(target.target_group_trajectory_map)
        task_map.update(target.target_task_trajectory_map)
    merged.target_group_trajectory_map = group_map
    merged.target_task_trajectory_map = task_map
    return merged


def ensure_controller(robot, controller_name):
    status = robot.switch_controller(controller_name)
    print(f"switch_controller({controller_name}): {status_to_string(status)}")
    return status


def run_twist_scene(robot, scene_name, target, twist_duration_s):
    print(f"{scene_name}: start moving for {twist_duration_s} seconds")
    motion_status = robot.publish_target(target)
    print(f"{scene_name} publish_target status: {status_to_string(motion_status)}")
    if motion_status != ControlStatus.SUCCESS:
        return motion_status

    time.sleep(twist_duration_s)
    print(f"{scene_name}: send stop twist target")
    stop_status = robot.publish_target(build_stop_twist_target())
    print(f"{scene_name} stop status: {status_to_string(stop_status)}")
    return stop_status


def print_menu():
    print(
        "\nAvailable commands:\n"
        "  joint        - publish a joint-only head target\n"
        "  base_pose    - publish a chassis pose target\n"
        "  base_twist   - publish a chassis twist target with auto stop\n"
        "  mixed_pose   - publish head + left_arm + chassis pose in one target\n"
        "  mixed_twist  - publish head + left_arm + chassis twist in one target\n"
        "  quit         - exit example\n"
    )


def main():
    robot = GalbotRobot()
    if not robot.init():
        print("robot init failed")
        return

    time.sleep(2)

    head_joint_names = robot.get_joint_names(True, [G1JointGroup.head])
    left_arm_joint_names = robot.get_joint_names(True, [G1JointGroup.left_arm])
    if not head_joint_names or not left_arm_joint_names:
        print("failed to fetch active head/left_arm joints")
        robot.request_shutdown()
        robot.wait_for_shutdown()
        robot.destroy()
        return

    head_single_joint = [head_joint_names[0]]
    arm_single_joint = [left_arm_joint_names[0]]
    joint_time_s = 3.0
    pose_time_s = 4.0
    twist_command_time_s = 0.2
    twist_duration_s = 2.0

    print_menu()

    while True:
        command = input("Enter command: ").strip()
        if command == "quit":
            break

        if command == "joint":
            target = build_joint_target(G1JointGroup.head, head_single_joint, [0.2], joint_time_s)
            status = robot.publish_target(target)
            print(f"joint publish_target status: {status_to_string(status)}")
            continue

        if command == "base_pose":
            if ensure_controller(robot, G1ControllerName.CHASSIS_POSE_CTRL) != ControlStatus.SUCCESS:
                continue
            target = build_chassis_pose_target(0.2, 0.0, 0.0, pose_time_s)
            status = robot.publish_target(target)
            print(f"base_pose publish_target status: {status_to_string(status)}")
            continue

        if command == "base_twist":
            if ensure_controller(robot, G1ControllerName.CHASSIS_TWIST_CTRL) != ControlStatus.SUCCESS:
                continue
            target = build_chassis_twist_target(0.05, 0.0, 0.0, twist_command_time_s)
            run_twist_scene(robot, "base_twist", target, twist_duration_s)
            continue

        if command == "mixed_pose":
            if ensure_controller(robot, G1ControllerName.CHASSIS_POSE_CTRL) != ControlStatus.SUCCESS:
                continue
            target = merge_targets(
                [
                    build_joint_target(G1JointGroup.head, head_single_joint, [0.2], joint_time_s),
                    build_joint_target(G1JointGroup.left_arm, arm_single_joint, [0.1], joint_time_s),
                    build_chassis_pose_target(0.1, 0.0, 0.0, pose_time_s),
                ]
            )
            status = robot.publish_target(target)
            print(f"mixed_pose publish_target status: {status_to_string(status)}")
            continue

        if command == "mixed_twist":
            if ensure_controller(robot, G1ControllerName.CHASSIS_TWIST_CTRL) != ControlStatus.SUCCESS:
                continue
            target = merge_targets(
                [
                    build_joint_target(G1JointGroup.head, head_single_joint, [-0.2], joint_time_s),
                    build_joint_target(G1JointGroup.left_arm, arm_single_joint, [-0.1], joint_time_s),
                    build_chassis_twist_target(0.05, 0.0, 0.0, twist_command_time_s),
                ]
            )
            run_twist_scene(robot, "mixed_twist", target, twist_duration_s)
            continue

        print(f"Unknown command: {command}")
        print_menu()

    robot.request_shutdown()
    robot.wait_for_shutdown()
    robot.destroy()


if __name__ == "__main__":
    main()
```

### Request Raw Target Directly (request_target)

**Applicable Scenarios**: Advanced users construct a `SingoriXTarget` directly and send it through the WBCS request channel. Suitable when the caller needs the service-side error response for a raw target dispatch.

```python title="examples/python/galbot_robot/request_target_example.py"
"""
G1 RequestTarget menu example for SDK mirror SingoriXTarget.

This example shows how to construct `SingoriXTarget` directly at the Python SDK
layer and send it to the low-level WBCS through `request_target()`.

1. Joint-space commands are written into `target_group_trajectory_map`
2. Chassis pose / twist style task-space commands are written into `target_task_trajectory_map`
3. One `SingoriXTarget` can contain both joint trajectory and task trajectory
4. The current SDK does not automatically switch the chassis controller, so
   pose / twist / mixed scenes explicitly call `switch_controller(...)`
5. The base twist scene automatically sends a zero-twist target after the
   configured duration to stop the chassis
"""

import math
import time

from galbot_sdk.g1 import (
    ControlStatus,
    ErrorInfo,
    G1ControllerName,
    G1JointGroup,
    GalbotRobot,
    GroupCommand,
    JointCommand,
    Pose,
    SingoriXTarget,
    TargetConfig,
    TargetGroupTrajectory,
    TargetSampling,
    TargetTaskTrajectory,
    TaskCommand,
    Twist,
    Vector3,
    FrameTriad,
    TARGET_DATA_DEFAULT,
    TARGET_DATA_FRAME_POSE,
    TARGET_DATA_FRAME_TWIST,
    TARGET_TYPE_DEFAULT,
    TARGET_TYPE_OVERRIDE,
    TARGET_TYPE_PROVERRIDE,
)


CHASSIS_TASK_NAME = "chassis"
CHASSIS_SUBTASK_POSE = "chassis_pose"
CHASSIS_SUBTASK_TWIST = "chassis_twist"


def now_ns():
    return time.time_ns()


def yaw_to_quaternion(yaw):
    return [0.0, 0.0, math.sin(yaw * 0.5), math.cos(yaw * 0.5)]


def make_empty_target():
    target = SingoriXTarget()
    target.header.timestamp_ns = now_ns()
    target.header.frame_id = "base_link"
    return target


def make_group_target_config():
    config = TargetConfig()
    config.target_data = TARGET_DATA_DEFAULT
    config.target_type = TARGET_TYPE_PROVERRIDE
    config.target_sampling = TargetSampling.TARGET_SAMPLING_DEFAULT
    config.target_priority = 1
    return config


def make_pose_target_config():
    config = TargetConfig()
    config.target_data = TARGET_DATA_FRAME_POSE
    config.target_type = TARGET_TYPE_PROVERRIDE
    config.target_sampling = TargetSampling.TARGET_SAMPLING_LINEAR_INTERPOLATE
    config.target_priority = 1
    return config


def make_twist_target_config():
    config = TargetConfig()
    config.target_data = TARGET_DATA_FRAME_TWIST
    config.target_type = TARGET_TYPE_OVERRIDE
    config.target_sampling = TargetSampling.TARGET_SAMPLING_DIRECT_PASS
    config.target_priority = 1
    return config


def make_joint_command(position):
    command = JointCommand()
    command.position = position
    command.velocity = 0.0
    command.acceleration = 0.0
    command.effort = 0.0
    return command


def make_vector3(x, y, z):
    vec = Vector3()
    vec.x = x
    vec.y = y
    vec.z = z
    return vec


def build_joint_target(group_name, joint_names, positions, time_from_start_s):
    target = make_empty_target()

    group_traj = TargetGroupTrajectory()
    group_traj.target_config = make_group_target_config()
    group_traj.joint_names = list(joint_names)

    command = GroupCommand()
    command.time_from_start_s = time_from_start_s
    command.joint_commands = [make_joint_command(position) for position in positions]
    group_traj.group_commands = [command]

    target.target_group_trajectory_map = {group_name: group_traj}
    return target


def build_chassis_pose_target(x, y, yaw, time_from_start_s, frame_id="odom", reference_frame_id="odom"):
    target = make_empty_target()

    task_traj = TargetTaskTrajectory()
    task_traj.target_config = make_pose_target_config()
    task_traj.group_names = [G1JointGroup.chassis]
    task_traj.subtask_names = [CHASSIS_SUBTASK_POSE]

    triad = FrameTriad()
    triad.header.timestamp_ns = now_ns()
    triad.header.frame_id = frame_id
    triad.body_frame_id = "base_link"
    triad.reference_frame_id = reference_frame_id
    triad.pose = Pose([x, y, 0.0], yaw_to_quaternion(yaw))

    command = TaskCommand()
    command.time_from_start_s = time_from_start_s
    command.subtask_commands = [triad]
    task_traj.task_commands = [command]

    target.target_task_trajectory_map = {CHASSIS_TASK_NAME: task_traj}
    return target


def build_chassis_twist_target(vx, vy, wz, time_from_start_s):
    target = make_empty_target()

    task_traj = TargetTaskTrajectory()
    task_traj.target_config = make_twist_target_config()
    task_traj.group_names = [G1JointGroup.chassis]
    task_traj.subtask_names = [CHASSIS_SUBTASK_TWIST]

    twist = Twist()
    twist.linear = make_vector3(vx, vy, 0.0)
    twist.angular = make_vector3(0.0, 0.0, wz)

    triad = FrameTriad()
    triad.header.timestamp_ns = now_ns()
    triad.header.frame_id = "base_link"
    triad.body_frame_id = "base_link"
    triad.reference_frame_id = "base_link"
    triad.twist = twist

    command = TaskCommand()
    command.time_from_start_s = time_from_start_s
    command.subtask_commands = [triad]
    task_traj.task_commands = [command]

    target.target_task_trajectory_map = {CHASSIS_TASK_NAME: task_traj}
    return target


def build_stop_twist_target():
    return build_chassis_twist_target(0.0, 0.0, 0.0, 0.1)


def merge_targets(targets):
    merged = make_empty_target()
    group_map = {}
    task_map = {}
    for target in targets:
        group_map.update(target.target_group_trajectory_map)
        task_map.update(target.target_task_trajectory_map)
    merged.target_group_trajectory_map = group_map
    merged.target_task_trajectory_map = task_map
    return merged


def print_error_info(scene_name, error_info):
    if error_info is None:
        print(f"{scene_name}: request_target returned None")
        return
    if not isinstance(error_info, ErrorInfo):
        print(f"{scene_name}: unexpected response type {type(error_info)}")
        return
    if not error_info.error_vec:
        print(f"{scene_name}: request_target success, service returned no errors")
        return

    print(f"{scene_name}: request_target returned {len(error_info.error_vec)} error entries:")
    for error in error_info.error_vec:
        print(
            f"  component={error.commpent}, code={error.error_code}, description={error.description}"
        )


def ensure_controller(robot, controller_name):
    status = robot.switch_controller(controller_name)
    print(f"switch_controller({controller_name}): {getattr(status, 'name', status)}")
    return status


def run_twist_scene(robot, scene_name, target, twist_duration_s):
    print(f"{scene_name}: start moving for {twist_duration_s} seconds")
    print_error_info(scene_name, robot.request_target(target))
    time.sleep(twist_duration_s)
    print(f"{scene_name}: send stop twist target")
    print_error_info(f"{scene_name}_stop", robot.request_target(build_stop_twist_target()))


def print_menu():
    print(
        "\nAvailable commands:\n"
        "  joint        - request a joint-only head target\n"
        "  base_pose    - request a chassis pose target\n"
        "  base_twist   - request a chassis twist target with auto stop\n"
        "  mixed_pose   - request head + left_arm + chassis pose in one target\n"
        "  mixed_twist  - request head + left_arm + chassis twist in one target\n"
        "  quit         - exit example\n"
    )


def main():
    robot = GalbotRobot()
    if not robot.init():
        print("robot init failed")
        return

    time.sleep(2)

    head_joint_names = robot.get_joint_names(True, [G1JointGroup.head])
    if not head_joint_names:
        print("failed to fetch active head joints")
        robot.request_shutdown()
        robot.wait_for_shutdown()
        robot.destroy()
        return

    head_single_joint = [head_joint_names[0]]
    joint_time_s = 3.0
    pose_time_s = 4.0
    twist_command_time_s = 0.2
    twist_duration_s = 2.0

    print_menu()

    while True:
        command = input("Enter command: ").strip()
        if command == "quit":
            break

        if command == "joint":
            target = build_joint_target(G1JointGroup.head, head_single_joint, [0.2], joint_time_s)
            print_error_info("joint", robot.request_target(target))
            continue

        if command == "base_pose":
            if ensure_controller(robot, G1ControllerName.CHASSIS_POSE_CTRL) != ControlStatus.SUCCESS:
                continue
            target = build_chassis_pose_target(0.2, 0.0, 0.0, pose_time_s)
            print_error_info("base_pose", robot.request_target(target))
            continue

        if command == "base_twist":
            if ensure_controller(robot, G1ControllerName.CHASSIS_TWIST_CTRL) != ControlStatus.SUCCESS:
                continue
            target = build_chassis_twist_target(0.05, 0.0, 0.0, twist_command_time_s)
            run_twist_scene(robot, "base_twist", target, twist_duration_s)
            continue

        if command == "mixed_pose":
            if ensure_controller(robot, G1ControllerName.CHASSIS_POSE_CTRL) != ControlStatus.SUCCESS:
                continue
            target = merge_targets(
                [
                    build_joint_target(G1JointGroup.head, head_single_joint, [0.2], joint_time_s),
                    build_chassis_pose_target(0.1, 0.0, 0.0, pose_time_s),
                ]
            )
            print_error_info("mixed_pose", robot.request_target(target))
            continue

        if command == "mixed_twist":
            if ensure_controller(robot, G1ControllerName.CHASSIS_TWIST_CTRL) != ControlStatus.SUCCESS:
                continue
            target = merge_targets(
                [
                    build_joint_target(G1JointGroup.head, head_single_joint, [-0.2], joint_time_s),
                    build_chassis_twist_target(0.05, 0.0, 0.0, twist_command_time_s),
                ]
            )
            run_twist_scene(robot, "mixed_twist", target, twist_duration_s)
            continue

        print(f"Unknown command: {command}")
        print_menu()

    robot.request_shutdown()
    robot.wait_for_shutdown()
    robot.destroy()


if __name__ == "__main__":
    main()
```

### Set Base Velocity (set_base_velocity)

**Applicable Scenarios**: Control linear and angular velocity of the mobile base, used for navigation or remote control.

```python title="examples/python/galbot_robot/set_base_velocity.py"
from galbot_sdk.g1 import GalbotRobot, ControlStatus
import time

# Get GalbotRobot
robot = GalbotRobot()
robot.init()
time.sleep(1)
print("Initialization succeeded")

# Set chassis speed
linear_velocity = [0.05, 0.0, 0.0]  # 0.5 m/s
angular_velocity = [0.0, 0.0, 0.1]  # 0.1 rad/s

duration_s = 2.0  # Automatically stop after 2 seconds
status = robot.set_base_velocity(linear_velocity, angular_velocity, duration_s)

if status == ControlStatus.SUCCESS:
    print(f"Chassis speed set successfully; will auto-stop after {duration_s} seconds.")
else:
    print("Set chassis speed failed.")

time.sleep(duration_s + 0.5)

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')
```

### Get Joint States (get_joint_states)

**Applicable Scenarios**: Get complete state information of all joints, including position, velocity, current, etc. Suitable for algorithms requiring full joint information (such as dynamics calculation, state estimation).

```python title="examples/python/galbot_robot/get_joint_states.py"
import time
from galbot_sdk.g1 import GalbotRobot

def print_joint_states(joint_states):
    """
    joint_state_vec: List of JointState; each object has position, velocity, acceleration, effort, current
    """
    for js in joint_states:
        print(f" : position = {js.position} , velocity = {js.velocity} "
            f", acceleration = {js.acceleration} , effort = {js.effort} , current = {js.current}")

# Get and initialize the GalbotRobot singleton
robot = GalbotRobot()
robot.init()
# Program started, waiting for data
time.sleep(1)
print("Initialization succeeded")
# Get joint states by joint group names; returns all joints if empty
joint_group_names = ["left_arm"]
ret = robot.get_joint_states(joint_group_names, [])
print_joint_states(ret)

# Get specified joint states; if provided, overrides joint group input
joint_names = ["left_arm_joint1", "left_arm_joint2"]
state_ret = robot.get_joint_states([], joint_names)
print_joint_states(state_ret)

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')
```

### Get Joint Positions (get_joint_positions)

**Applicable Scenarios**: Only get current joint positions. Use this interface when you only need joint position information, it's more lightweight than `get_joint_states`.

```python title="examples/python/galbot_robot/get_joint_positions.py"
import time
from galbot_sdk.g1 import GalbotRobot

def print_joint_positions(joint_positions):
    print(f"pos count is {len(joint_positions)}")
    for pos in joint_positions:
        print(pos)

# Get and initialize the GalbotRobot singleton
robot = GalbotRobot()
robot.init()
# Program started, waiting for data
time.sleep(1)
print("Initialization succeeded")

# Get joint positions by joint group names; returns all joints if empty
joint_group_names = ["left_arm"]
ret = robot.get_joint_positions(joint_group_names, [])
print("Left arm joint positions:")
print_joint_positions(ret)
# Get specified joint positions; if provided, overrides joint group input
joint_names = ["left_arm_joint1", "left_arm_joint2"]
state_ret = robot.get_joint_positions([], joint_names)
print("Left arm joints 1 and 2 positions:")
print_joint_positions(state_ret)

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')
```

### Get Joint Names (get_joint_names)

**Applicable Scenarios**: Get a list of all joint names of the robot, used for iterating through joints or generating configuration files.

```python title="examples/python/galbot_robot/get_joint_names.py"
import time
from galbot_sdk.g1 import GalbotRobot

# Get and initialize the GalbotRobot singleton
robot = GalbotRobot()
robot.init()
# Program started, waiting for data
time.sleep(1)
print("Initialization succeeded")

# Get joint positions by joint group names; returns all joints if empty
joint_group_names = ["left_arm"]
# get joint
only_active_joint = True
ret = robot.get_joint_names(only_active_joint, joint_group_names)
print("Left joint names:")
for i, name in enumerate(ret):
    print(f"{i + 1}: {name}")

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')
```

### Get Gripper State (get_gripper_state)

**Applicable Scenarios**: Get current gripper position and status, determine if gripper is open or closed.

```python title="examples/python/galbot_robot/get_gripper_state.py"
import time
from galbot_sdk.g1 import GalbotRobot, G1JointGroup

def print_gripper_state(joint_group, gripper_state):
    """
    joint_group: G1JointGroup enum value
    gripper_state: object including timestamp_ns, width, velocity, effort, is_moving
    """
    print(f"Timestamp (ns): {gripper_state.timestamp_ns}")
    print(
        f"width {gripper_state.width} "
        f"velocity {gripper_state.velocity} "
        f"effort {gripper_state.effort} "
        f"is moving {gripper_state.is_moving}"
    )

# Get and initialize the GalbotRobot singleton
robot = GalbotRobot()
robot.init()

# Program started, waiting for data
time.sleep(1)
print("Initialization succeeded")

# Set gripper joint group (left gripper)
joint_group = G1JointGroup.left_gripper

# Get gripper state
gripper_state = robot.get_gripper_state(joint_group)

if gripper_state is None:
    print("get gripper state error")
else:
    print("Left gripper state is as follows:")
    print_gripper_state(joint_group, gripper_state)

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')
```

### Get Suction Cup State (get_suction_cup_state)

**Applicable Scenarios**: Get whether the suction cup is currently suctioned and whether it successfully detected an object.

```python title="examples/python/galbot_robot/get_suction_cup_state.py"
import time
from galbot_sdk.g1 import GalbotRobot, G1JointGroup

def print_suction_cup_state(suction_cup_state):
    """
    suction_cup_state: object including timestamp_ns, pressure, activation, action_state
    """
    group_name = joint_group.name
    print(f"Timestamp (ns): {suction_cup_state.timestamp_ns}")
    print(
        f"pressure {suction_cup_state.pressure} "
        f"activation {suction_cup_state.activation} "
        f"action state {int(suction_cup_state.action_state)}"
    )

# Get and initialize the GalbotRobot singleton
robot = GalbotRobot()
robot.init()

# Program started, waiting for data
time.sleep(1)
print("Initialization succeeded")

# Set suction cup joint group (right suction cup)
joint_group = G1JointGroup.right_suction_cup

# Get suction cup state
suction_cup_state = robot.get_suction_cup_state(joint_group)

if suction_cup_state is None:
    print("get suction cup error")
else:
    print("Right suction cup status:")
    print_suction_cup_state(suction_cup_state)

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')
```

### Get Transform (get_transform)

**Applicable Scenarios**: Get the transformation (pose) between two coordinate frames, used in robotic arm grasping, visual localization and other scenarios.

```python title="examples/python/galbot_robot/get_transform.py"
import time
from galbot_sdk.g1 import GalbotRobot

def print_pose(pose_vec):
    """
    pose_vec: list of floats
    """
    print("pose_vec = [" + ", ".join(str(p) for p in pose_vec) + "]")

# Get and initialize the GalbotRobot singleton
robot = GalbotRobot()
robot.init()

# Program started, waiting for data
time.sleep(1)
print("Initialization succeeded")

# Set target frame and source frame
target_frame = "base_link"
source_frame = "left_arm_link1"
timestamp_ns = 0    # 0 means fetch the latest TF transform value

# Get coordinate transform
ret_val = robot.get_transform(target_frame, source_frame)

if not ret_val[0]:
    print("get_transform error")
else:
    print("tf_timestamp_ns:", ret_val[1])
    print_pose(ret_val[0])

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')
```

### Get IMU Data (get_imu_data)

**Applicable Scenarios**: Get acceleration, angular velocity and pose information from the base IMU, used for state estimation and motion analysis.

```python title="examples/python/galbot_robot/get_imu_data.py"
import time
from galbot_sdk.g1 import GalbotRobot, SensorType
from typing import Dict

def print_imu_data(imu_data: dict):
    """
    imu_data: dict, includes:
        - 'timestamp_ns'
        - 'accel'   : {'x', 'y', 'z'}
        - 'gyro'    : {'x', 'y', 'z'}
        - 'magnet'  : {'x', 'y', 'z'}
    """
    if not imu_data:
        print("IMU data is empty")
        return

    print(f"Timestamp (ns): {imu_data.get('timestamp_ns')}")

    accel = imu_data.get("accel", {})
    gyro = imu_data.get("gyro", {})
    magnet = imu_data.get("magnet", {})

    print(
        f"Accelerometer: x={accel.get('x')}, "
        f"y={accel.get('y')}, "
        f"z={accel.get('z')}"
    )
    print(
        f"Gyroscope:     x={gyro.get('x')}, "
        f"y={gyro.get('y')}, "
        f"z={gyro.get('z')}"
    )
    print(
        f"Magnetometer:  x={magnet.get('x')}, "
        f"y={magnet.get('y')}, "
        f"z={magnet.get('z')}"
    )

# Get and initialize the GalbotRobot singleton
robot = GalbotRobot()
robot.init({SensorType.TORSO_IMU})

# Program started, waiting for data
time.sleep(1)
print("Initialization succeeded")

imu_data = robot.get_imu_data(SensorType.TORSO_IMU)
if not imu_data:
    print("No imu data!")
else:
    print("IMU data:")
    print_imu_data(imu_data)

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')
```
### Get Battery Information (get_bms_information)

**Applicable Scenarios**: Get battery voltage, charge level and other information, used for low battery detection and status monitoring.

```python title="examples/python/galbot_robot/get_bms_information.py"
import time
from galbot_sdk.g1 import GalbotRobot


def print_bms_information(bms_info: dict):
    """
    bms_info: dict, includes:
        - 'voltage'            : float (V)
        - 'current'            : float (A)
        - 'battery_level'      : float (0-100)
        - 'temperature'        : float (°C)
        - 'charging_status'    : str or int
        - 'health_status'      : str or int
        - 'capacity'           : float (Ah)
    """
    if not bms_info:
        print("BMS information is empty")
        return

    print(f"Voltage (V): {bms_info.get('voltage')}")
    print(f"Current (A): {bms_info.get('current')}")
    print(f"Battery level (%): {bms_info.get('battery_level')}")
    print(f"Temperature (C): {bms_info.get('temperature')}")
    print(f"Charging status: {bms_info.get('charging_status')}")
    print(f"Health status: {bms_info.get('health_status')}")
    print(f"Capacity (Ah): {bms_info.get('capacity')}")


# Get and initialize the GalbotRobot singleton
robot = GalbotRobot()
robot.init()

# Program started, waiting for data
time.sleep(3)
print("Initialization succeeded")

bms_info = robot.get_bms_information()
print_bms_information(bms_info)

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print("Resources released successfully")
```

### Get Device Information (get_device_information)

**Applicable Scenarios**: Get device information such as hardware version and firmware version, used for debugging and compatibility checking.

```python title="examples/python/galbot_robot/get_device_information.py"
import time
from galbot_sdk.g1 import GalbotRobot
from typing import Dict

def print_device_info(device_info: dict):
    """
    device_info: dict, including the following fields:
        - 'model': Device model (str)
        - 'serial_number': Serial number (str)
        - 'firmware_version': Firmware version (str)
        - 'hardware_version': Hardware version (str)
        - 'manufacturer': Manufacturer (str)
    """
    if not device_info:
        print("Device information is empty")
        return

    print("Device information:")
    print(f"  Model: {device_info.get('model', 'N/A')}")
    print(f"  Serial number: {device_info.get('serial_number', 'N/A')}")
    print(f"  Firmware version: {device_info.get('firmware_version', 'N/A')}")
    print(f"  Hardware version: {device_info.get('hardware_version', 'N/A')}")
    print(f"  : {device_info.get('manufacturer', 'N/A')}")

# Get and initialize the GalbotRobot singleton
robot = GalbotRobot()
robot.init()

# Program started, waiting for data
time.sleep(1)
print("Initialization succeeded")

device_info = robot.get_device_information()
if not device_info:
    print("Failed to get device information!")
else:
    print("Device information retrieved successfully!")
    print_device_info(device_info)

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')
```

### Get Camera Image Data (get_rgb_data && get_depth_data)

**Applicable Scenarios**: Get RGB image and depth image data, used for visual perception, object detection, SLAM and other tasks.

```python title="examples/python/galbot_robot/get_camera_data.py"
try:
    from galbot_sdk.g1 import GalbotRobot, SensorType
except ImportError:
    print("import galbot_sdk failed, please install it first or check if it is in the PYTHONPATH")
    exit(1)

import os

try:
    import cv2
except ImportError:
    os.system("pip install opencv-python")
    import cv2

try:
    import numpy as np
except ImportError:
    os.system("pip install numpy")
    import numpy as np

import time
from typing import Dict

def decode_compressed_image(compressed_image):
    """
    decode CompressedImage image

    Parameters:
        compressed_image (dict): image dict, keys:[header, format, data, "depth_scale"]

    Returns:
        numpy.ndarray: decoded image
    """
    image_data = compressed_image["data"]
    if compressed_image["format"] == "rgb8":
        return decode_rgb_image(image_data)
    elif compressed_image["format"] == "16UC1":
        return decode_depth_image(compressed_image)
    else:
        raise ValueError(f"Unsupport data format: {compressed_image['format']}")

def decode_rgb_image(image_data):
    """decode rgb image"""
    nparr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Fail to Decode RGB Image")
    return img

def decode_depth_image(image_data):
    """decode depth image"""
    depth_img = np.frombuffer(image_data["data"], dtype=np.uint16).copy()

    # Check whether height and width exist
    if "height" not in image_data or "width" not in image_data:
        raise ValueError("Missing 'height' or 'width' in depth image metadata.")
    if image_data["height"] == 0 or image_data["width"] == 0:
        raise ValueError(f"Invalid 'height' ({image_data['height']}) or 'width' ({image_data['width']}) in depth image metadata.")

    # Parse depth image
    depth_img = depth_img.reshape((image_data["height"], image_data["width"]))
    depth_img = depth_img.astype(np.float32) / image_data["depth_scale"]

    return depth_img

def main():
    SHOW_IMAGE = False
    robot = GalbotRobot()

    # Get left arm RGB and depth images, right arm depth image, chassis lidar data, torso IMU data
    enable_sensor_set = {SensorType.LEFT_ARM_CAMERA, # Left arm depth camera
                        SensorType.LEFT_ARM_DEPTH_CAMERA,} # Left arm RGB camera
    robot.init(enable_sensor_set)
    print("Initialization succeeded")
    # Program started, waiting for data
    time.sleep(5)
    # Get left arm RGB image
    rgb_image_data = robot.get_rgb_data(SensorType.LEFT_ARM_CAMERA)
    if not rgb_image_data:
        print("No rgb image data!")
    else:
        print("get rgb image suceess")
        print(rgb_image_data['header'])
        img = decode_compressed_image(rgb_image_data)
        
        # Save RGB image
        cv2.imwrite("rgb_image_data.jpg", img)
        # 可视化RGB图像
        if SHOW_IMAGE:
            cv2.namedWindow("rgb image", cv2.WINDOW_NORMAL)
            cv2.imshow("rgb image", img)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

    # Get left arm depth image
    depth_data = robot.get_depth_data(SensorType.LEFT_ARM_DEPTH_CAMERA)
    if not depth_data or "data" not in depth_data:
        print("Depth camera not ready")
    else:
        print("get depth data suceess")
        print(depth_data['header'])
        depth_img_raw = decode_compressed_image(depth_data)
        depth_img = cv2.normalize(depth_img_raw, None, 0, 255, cv2.NORM_MINMAX) # Normalize depth values to 0-1 range
        depth_img = depth_img.astype(np.uint8)

        # Save depth image
        cv2.imwrite("depth_data.jpg", depth_img)
        # 可视化深度图
        if SHOW_IMAGE:
            cv2.namedWindow("depth image", cv2.WINDOW_NORMAL)
            cv2.imshow("depth image", depth_img)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

    # send SIGINT shutdown signal
    robot.request_shutdown()
    # Wait until entering shutdown state
    robot.wait_for_shutdown()
    # Perform SDK resource release
    robot.destroy()
    print('Resources released successfully')
    
if __name__=="__main__":
    main()
```

### Get Sensor Parameters (get_camera_intrinsic && get_sensor_extrinsic)

**Applicable Scenarios**: Get camera intrinsics and sensor extrinsics relative to the robot base, used for computer vision calculations and 3D reconstruction.

```python title="examples/python/galbot_robot/get_camera_params.py"
try:
    from galbot_sdk.g1 import GalbotRobot, SensorType
except ImportError:
    print("import galbot_sdk failed, please install it first or check if it is in the PYTHONPATH")
    exit(1)

import os

try:
    import cv2
except ImportError:
    os.system("pip install opencv-python")
    import cv2

try:
    import numpy as np
except ImportError:
    os.system("pip install numpy")
    import numpy as np

import time
from typing import Dict

def decode_compressed_image(compressed_image):
    """
    decode CompressedImage image

    Parameters:
        compressed_image (dict): image dict, keys:[header, format, data, "depth_scale"]

    Returns:
        numpy.ndarray: decoded image
    """
    image_data = compressed_image["data"]
    if compressed_image["format"] == "rgb8":
        return decode_rgb_image(image_data)
    elif compressed_image["format"] == "16UC1":
        return decode_depth_image(compressed_image)
    else:
        raise ValueError(f"Unsupport data format: {compressed_image['format']}")

def decode_rgb_image(image_data):
    """decode rgb image"""
    nparr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Fail to Decode RGB Image")
    return img

def decode_depth_image(image_data):
    """decode depth image"""
    depth_img = np.frombuffer(image_data["data"], dtype=np.uint16).copy()

    # Check whether height and width exist
    if "height" not in image_data or "width" not in image_data:
        raise ValueError("Missing 'height' or 'width' in depth image metadata.")
    if image_data["height"] == 0 or image_data["width"] == 0:
        raise ValueError(f"Invalid 'height' ({image_data['height']}) or 'width' ({image_data['width']}) in depth image metadata.")

    # Parse depth image
    depth_img = depth_img.reshape((image_data["height"], image_data["width"]))
    depth_img = depth_img.astype(np.float32) / image_data["depth_scale"]

    return depth_img

def main():
    robot = GalbotRobot()

    # Get left arm RGB and depth images, right arm depth image, chassis lidar data, torso IMU data
    enable_sensor_set = {SensorType.LEFT_ARM_CAMERA, # Left arm depth camera
                        SensorType.LEFT_ARM_DEPTH_CAMERA,} # Left arm RGB camera
    robot.init(enable_sensor_set)
    print("Initialization succeeded")
    
    # Program started, waiting for data
    time.sleep(5)
    
    # Get left arm RGB image
    rgb_image_data = robot.get_rgb_data(SensorType.LEFT_ARM_CAMERA)
    if not rgb_image_data:
        print("No rgb image data!")
    else:
        print("get rgb image suceess")
        print(rgb_image_data['header'])
        img = decode_compressed_image(rgb_image_data)
        
        # Save RGB image
        cv2.imwrite("rgb_image_data.jpg", img)

    # Get left arm camera intrinsics
    camera_intrinsics = robot.get_camera_intrinsic(SensorType.LEFT_ARM_CAMERA)
    if not camera_intrinsics:
        print("No camera intrinsics data!")
    else:
        print("get camera intrinsics suceess")
        print(camera_intrinsics)

    # Get left arm depth image
    depth_data = robot.get_depth_data(SensorType.LEFT_ARM_DEPTH_CAMERA)
    if not depth_data or "data" not in depth_data:
        print("Depth camera not ready")
    else:
        print("get depth data suceess")
        print(depth_data['header'])
        depth_img_raw = decode_compressed_image(depth_data)
        depth_img = cv2.normalize(depth_img_raw, None, 0, 255, cv2.NORM_MINMAX) # Normalize depth values to 0-1 range
        depth_img = depth_img.astype(np.uint8)

        # Save depth image
        cv2.imwrite("depth_data.jpg", depth_img)

    # Get left-arm depth camera intrinsics
    camera_intrinsics = robot.get_camera_intrinsic(SensorType.LEFT_ARM_DEPTH_CAMERA)
    if not camera_intrinsics:
        print("No camera intrinsics data!")
    else:
        print("get camera intrinsics suceess")
        print(camera_intrinsics)

    # Extrinsics
    time.sleep(2)
    camera_extrinsics, timestamp_ns = robot.get_sensor_extrinsic(SensorType.LEFT_ARM_DEPTH_CAMERA)
    if not camera_extrinsics:
        print("No camera extrinsics data!")
    else:
        print("get camera extrinsics suceess")
        print(camera_extrinsics)

    # send SIGINT shutdown signal
    robot.request_shutdown()
    # Wait until entering shutdown state
    robot.wait_for_shutdown()
    # Perform SDK resource release
    robot.destroy()
    print('Resources released successfully')
    
if __name__=="__main__":
    main()
```

### Get Lidar Data (get_lidar_data)

**Applicable Scenarios**: Get LiDAR point cloud data, used for navigation, obstacle avoidance, and environment modeling.

```python title="examples/python/galbot_robot/get_lidar_data.py"
from galbot_sdk.g1 import GalbotRobot, SensorType
from typing import Dict
import time
import numpy as np

def convert_pointcloud(cloud):
    """
    Convert cloud dict to NumPy array dictionary

    Args:
        pointcloud_msg: PointCloud2 protobuf message object

    Returns:
        Dictionary: {field_name: NumPy array}
        - Single-element fields: shape (N,)
        - Multi-element fields: shape (N, count) or (N,)
        - N = width * height (total number of points)
    """

    if not cloud:
        return {}

    num_points = cloud["height"] * cloud["width"]
    if num_points == 0:
        return {}

    DTYPE_MAP = {
        1: np.int8,
        2: np.uint8,
        3: np.int16,
        4: np.uint16,
        5: np.int32,
        6: np.uint32,
        7: np.float32,
        8: np.float64
    }
    dtype_list = []
    for field in cloud["fields"]:
        # Get base data type
        np_dtype_class = DTYPE_MAP.get(field["datatype"])
        if np_dtype_class is None:
            raise ValueError(f"Unsupported data type: {field['datatype']}")

        dtype_inst = np.dtype(np_dtype_class)

        # Handle byte order (endianness)
        if dtype_inst.itemsize > 1:
            byteorder = '>' if cloud["is_bigendian"] else '<'
            dtype_inst = dtype_inst.newbyteorder(byteorder)

        # Add to dtype list
        if field["count"] == 1:
            dtype_list.append((field["name"], dtype_inst))
        else:
            # Multi-element fields (e.g., rgb)
            dtype_list.append((field["name"], dtype_inst, field["count"]))

    # Create structured dtype
    dtype = np.dtype(dtype_list)

    # Data integrity check
    expected_size = num_points * cloud["point_step"]
    if len(cloud["data"]) < expected_size:
        raise ValueError(
            f"Insufficient data length: expected {expected_size} bytes, "
            f"actual {len(cloud['data'])} bytes"
        )

    # Create NumPy structured array from binary data
    # count parameter ensures only expected number of points are read
    arr = np.frombuffer(cloud["data"], dtype=dtype, count=num_points)

    # Convert to regular dictionary (copy data to avoid modifying original)
    result = {}
    for field in cloud["fields"]:
        field_data = arr[field["name"]]

        # Handle shape of multi-element fields
        if field["count"] == 1:
            result[field["name"]] = field_data.copy()
        else:
            # Keep original shape or flatten, choose according to needs
            result[field["name"]] = field_data.copy()

    return result


def get_xyz_array(pointcloud_dict: Dict[str, np.ndarray], 
                remove_nan: bool = False) -> np.ndarray:
    """
    Extract XYZ coordinate array from converted point cloud dictionary

    Args:
        pointcloud_dict: Dictionary returned by pointcloud2_to_numpy()
        remove_nan: Whether to remove points containing NaN (for FLOAT32/FLOAT64 types)

    Returns:
        Nx3 point coordinate array
    """
    required = ['x', 'y', 'z']
    if not all(k in pointcloud_dict for k in required):
        raise ValueError("Point cloud data missing required xyz fields")

    points = np.stack([pointcloud_dict['x'], 
                    pointcloud_dict['y'], 
                    pointcloud_dict['z']], axis=1)

    if remove_nan:
        mask = ~np.isnan(points).any(axis=1)
        points = points[mask]

    return points

def save_xyz_to_pcd(xyz_array: np.ndarray, filename: str, binary: bool = False) -> None:
    """
    Save XYZ coordinates to PCD file format (simplest option for coordinate-only data)

    Args:
        xyz_array: Nx3 array of XYZ coordinates
        filename: Output PCD file path
        binary: If True, saves in binary format; otherwise ASCII
    """
    if xyz_array.ndim != 2 or xyz_array.shape[1] != 3:
        raise ValueError(f"xyz_array must have shape (N, 3), got {xyz_array.shape}")

    num_points = xyz_array.shape[0]
    header = [
        "# .PCD v0.7 - Point Cloud Data file format",
        "VERSION 0.7",
        "FIELDS x y z",
        "SIZE 4 4 4",
        "TYPE F F F",  # F = float32
        "COUNT 1 1 1",
        f"WIDTH {num_points}",
        "HEIGHT 1",
        "VIEWPOINT 0 0 0 1 0 0 0",
        f"POINTS {num_points}",
        f"DATA {'binary' if binary else 'ascii'}"
    ]

    if binary:
        with open(filename, 'wb') as f:
            f.write(('\n'.join(header) + '\n').encode('ascii'))
            f.write(xyz_array.astype(np.float32).tobytes())
    else:
        with open(filename, 'w') as f:
            f.write('\n'.join(header) + '\n')
            np.savetxt(f, xyz_array, fmt='%f')

# Get and initialize the GalbotRobot singleton
robot = GalbotRobot()
enable_sensor_set = {SensorType.BASE_LIDAR}
# To save resource overhead, only cameras and LiDAR sensors passed during initialization can retrieve data
robot.init(enable_sensor_set)
print("Initialization succeeded")
# Program started, waiting for data
time.sleep(4)

cloud = robot.get_lidar_data(SensorType.BASE_LIDAR)
if not cloud:
    print("No lidar data!")
else:
    pointcloud_dict = convert_pointcloud(cloud)
    xyz_points = get_xyz_array(pointcloud_dict)
    save_xyz_to_pcd(xyz_points, "output_xyz.pcd")
    print(pointcloud_dict)
    print("get lidar data success")

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')
```

### One-Click Reset to Zero – Odometry Frame (whole_body_reset_zero_odom)

**Applicable Scenarios**: Quickly move all joints to zero position (initial pose) based on odometry frame. Typically used for initialization after program startup.

```python title="examples/python/galbot_robot/whole_body_reset_zero_odom_example.py"
from galbot_sdk.g1 import GalbotRobot
from galbot_sdk.g1 import GalbotMotion
import time


def main():
    robot = GalbotRobot()
    motion = GalbotMotion()

    if not robot.init():
        print("GalbotRobot init failed.")
        return
    if not motion.init():
        print("GalbotMotion init failed.")
        return

    time.sleep(2)

    # Whole-body joints: leg(5) + head(2) + left_arm(7) + right_arm(7)
    whole_body_joint_1 = [
        0.25, 1.1, 0.85, 0.0, 0.0,       # leg
        0.5, 0.5,                        # head
        2.0, -1.55, -0.55, -1.7, -0.0, -0.8, 0.2,   # left_arm
        -2.0, 1.55, 0.55, 1.7, 0.0, 0.8, 0.2        # right_arm
    ]

    # Base pose command odom(x, y, yaw)
    base_x_1 = 0.2
    base_y_1 = 0.0
    base_yaw_1 = 0.0

    # Optional frames (frame_id: base_link/odom/map, reference_frame_id: odom/map)
    frame_id = "base_link"
    reference_frame_id = "odom"

    # Chassis pose interpolation time (seconds), used to generate a smooth chassis trajectory
    base_time_s = 15.0

    time.sleep(1)

    # reset to zero
    result = robot.zero_whole_body_and_base(
        frame_id,
        reference_frame_id,
        True,
        0.2,
        15.0,
    )
    print("Zero joint status:", result[0])
    print("Zero base status:", result[1])

    robot.request_shutdown()
    robot.wait_for_shutdown()
    robot.destroy()


if __name__ == "__main__":
    main()
```

### One-Click Reset to Zero – Map Frame (whole_body_reset_zero_map)

**Applicable Scenarios**: Quickly move all joints to zero position (initial pose) based on map frame.

```python title="examples/python/galbot_robot/whole_body_reset_zero_map_example.py"
from galbot_sdk.g1 import GalbotRobot
from galbot_sdk.g1 import GalbotMotion
import time


def main():
    robot = GalbotRobot()
    motion = GalbotMotion()

    if not robot.init():
        print("GalbotRobot init failed.")
        return
    if not motion.init():
        print("GalbotMotion init failed.")
        return

    time.sleep(2)

    # Whole-body joints: leg(5) + head(2) + left_arm(7) + right_arm(7)
    whole_body_joint_1 = [
        0.25, 1.1, 0.85, 0.0, 0.0,       # leg
        0.5, 0.5,                        # head
        2.0, -1.55, -0.55, -1.7, -0.0, -0.8, 0.2,   # left_arm
        -2.0, 1.55, 0.55, 1.7, 0.0, 0.8, 0.2        # right_arm
    ]

    # Base pose command map(x, y, yaw) Note: adjust based on the robot's actual localization in the map frame
    base_x_1 = -0.4
    base_y_1 = 0.226593
    base_yaw_1 = 0.0

    # Optional frames (frame_id: base_link/odom/map, reference_frame_id: odom/map)
    frame_id = "base_link"
    reference_frame_id = "map"

    # Chassis pose interpolation time (seconds), used to generate a smooth chassis trajectory
    base_time_s = 15.0

    time.sleep(1)

    # reset to zero
    result = robot.zero_whole_body_and_base(
        frame_id,
        reference_frame_id,
        True,
        0.2,
        15.0,
    )
    print("Zero joint status:", result[0])
    print("Zero base status:", result[1])

    robot.request_shutdown()
    robot.wait_for_shutdown()
    robot.destroy()


if __name__ == "__main__":
    main()
```

## Class: GalbotMotion

### Get Instance and Initialize

**Applicable Scenarios**: Get the motion planning module singleton and initialize. Must be called before using motion planning functions.

```python title="examples/python/galbot_motion/get_instance.py"
from galbot_sdk.g1 import GalbotMotion
from galbot_sdk.g1 import GalbotRobot

# Get and initialize the GalbotMotion singleton
motion = GalbotMotion()
robot = GalbotRobot()

if motion.init():
    print("GalbotMotion initialized successfully")
else:
    print("GalbotMotion initialization failed")

if robot.init():
    print("GalbotRobot initialized successfully")
else:
    print("GalbotRobot initialization failed")

# You can still manage the robot lifecycle through GalbotRobot
robot.request_shutdown()
robot.wait_for_shutdown()
robot.destroy()
```

### Forward Kinematics (Using Current State or Specified RobotStates)

**Applicable Scenarios**: Calculate end effector pose based on given joint angles. Used for robotic arm task verification and state analysis.

```python title="examples/python/galbot_motion/fk.py"
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
time.sleep(1)

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
reference_frame = "base_link"
target_frame = "EndEffector"
target_chain = "left_arm"
one_chain = [target_chain]
chain_with_torso = [target_chain, "torso"]
error_chains = [target_chain, "torso", "head"]
# Scenario 1: Single-chain inverse kinematics
try:
    status, joint_map = motion.inverse_kinematics(
        target_pose=chain_pose_baselink[target_chain],
        chain_names=one_chain,
        target_frame=target_frame,
        reference_frame=reference_frame,
        enable_collision_check=False  # Disable collision checking for accelerated testing
    )
    printStatus(status)
    assert status == gm.MotionStatus.SUCCESS, "Inverse kinematics calculation failed"
    print(f"✅ Basic version forward kinematics successful: joint angles={joint_map}")
    time.sleep(0.8)
except Exception as e:
    print(f"❌ Basic version forward kinematics exception: {e}")

# Scenario 2: Arm chain + torso inverse kinematics
try:
    status, joint_map = motion.inverse_kinematics(
        target_pose=chain_pose_baselink[target_chain],
        chain_names=chain_with_torso,
        target_frame=target_frame,
        reference_frame=reference_frame,
        enable_collision_check=False  # Disable collision checking for accelerated testing
    )
    printStatus(status)
    assert status == gm.MotionStatus.SUCCESS, "Inverse kinematics calculation failed"
    print(f"✅ Custom initial joint forward kinematics successful: joint angles={joint_map}")
    time.sleep(0.8)
except Exception as e:
    print(f"❌ Custom initial joint forward kinematics exception: {e}")

# Scenario 3: invalid chain combination
try:
    status, joint_map = motion.inverse_kinematics(
        target_pose=chain_pose_baselink[target_chain],
        chain_names=error_chains,
        target_frame=target_frame,
        reference_frame=reference_frame,
        enable_collision_check=False  # Disable collision checking for accelerated testing
    )
    printStatus(status)
    assert status == gm.MotionStatus.INVALID_INPUT, "Inverse kinematics calculation failed"
    print(f"✅ Invalid chain-combination input check passed")
    time.sleep(0.8)
except Exception as e:
    print(f"❌ Custom initial joint forward kinematics exception: {e}")

# Scenario 4: Use reference joints
try:
    # initial_joint_positions can specify chain joints as IK reference, unspecified chain joints use whole-body joints
    status, joint_map = motion.inverse_kinematics(
        target_pose=chain_pose_baselink[target_chain],
        chain_names=one_chain,
        target_frame=target_frame,
        reference_frame=reference_frame,
        initial_joint_positions=chain_joints,
        enable_collision_check=False  # Disable collision checking for accelerated testing
    )
    printStatus(status)
    assert status == gm.MotionStatus.SUCCESS, "Inverse kinematics calculation failed"
    print(f"✅ Custom initial joint forward kinematics successful: joint angles={joint_map}")
    time.sleep(0.8)
except Exception as e:
    print(f"❌ Custom initial joint forward kinematics exception: {e}")

# Scenario 5: Use RobotStates
try:
    ref_robot_state = gm.RobotStates()
    ref_robot_state.chain_name = target_chain
    ref_robot_state.whole_body_joint = whole_body_joint
    ref_robot_state.base_state = base_state
    target_frame = "EndEffector"
    reference_frame = "base_link"
    status, joint_map = motion.inverse_kinematics_by_state(
        target_pose=chain_pose_baselink[target_chain],
        chain_names=one_chain,
        target_frame=target_frame,
        reference_frame=reference_frame,
        reference_robot_states=ref_robot_state
    )
    printStatus(status)
    assert status == gm.MotionStatus.SUCCESS, "Inverse kinematics calculation failed"
    print(f"✅ Based on RobotStates forward kinematics successful: joint angles={joint_map}")
except Exception as e:
    print(f"❌ Based on RobotStatesforward kinematics exception: {e}")

robot.request_shutdown()
robot.wait_for_shutdown()
robot.destroy()
```

### Inverse Kinematics (Basic and RobotStates-based)

**Applicable Scenarios**: Solve for the required joint angles based on the desired end effector pose. This is a core step for operations like robotic arm grasping.

```python title="examples/python/galbot_motion/ik.py"
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
time.sleep(1)

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
reference_frame = "base_link"
target_frame = "EndEffector"
target_chain = "left_arm"
one_chain = [target_chain]
chain_with_torso = [target_chain, "torso"]
error_chains = [target_chain, "torso", "head"]
# Scenario 1: Single-chain inverse kinematics
try:
    status, joint_map = motion.inverse_kinematics(
        target_pose=chain_pose_baselink[target_chain],
        chain_names=one_chain,
        target_frame=target_frame,
        reference_frame=reference_frame,
        enable_collision_check=False  # Disable collision checking for accelerated testing
    )
    printStatus(status)
    assert status == gm.MotionStatus.SUCCESS, "Inverse kinematics calculation failed"
    print(f"✅ Basic IK succeeded: joint angles={joint_map}")
    time.sleep(0.8)
except Exception as e:
    print(f"❌ Basic IK exception: {e}")

# Scenario 2: Arm chain + torso inverse kinematics
try:
    status, joint_map = motion.inverse_kinematics(
        target_pose=chain_pose_baselink[target_chain],
        chain_names=chain_with_torso,
        target_frame=target_frame,
        reference_frame=reference_frame,
        enable_collision_check=False  # Disable collision checking for accelerated testing
    )
    printStatus(status)
    assert status == gm.MotionStatus.SUCCESS, "Inverse kinematics calculation failed"
    print(f"✅ IK with custom initial joints succeeded: joint angles={joint_map}")
    time.sleep(0.8)
except Exception as e:
    print(f"❌ IK with custom initial joints exception: {e}")

# Scenario 3: invalid chain combination
try:
    status, joint_map = motion.inverse_kinematics(
        target_pose=chain_pose_baselink[target_chain],
        chain_names=error_chains,
        target_frame=target_frame,
        reference_frame=reference_frame,
        enable_collision_check=False  # Disable collision checking for accelerated testing
    )
    printStatus(status)
    assert status == gm.MotionStatus.INVALID_INPUT, "Inverse kinematics calculation failed"
    print(f"✅ Invalid chain-combination input check passed")
    time.sleep(0.8)
except Exception as e:
    print(f"❌ IK with custom initial joints exception: {e}")

# Scenario 4: Use reference joints
try:
    # initial_joint_positions can specify chain joints as IK reference; unspecified chain joints are filled from whole-body joints
    status, joint_map = motion.inverse_kinematics(
        target_pose=chain_pose_baselink[target_chain],
        chain_names=one_chain,
        target_frame=target_frame,
        reference_frame=reference_frame,
        initial_joint_positions=chain_joints,
        enable_collision_check=False  # Disable collision checking for accelerated testing
    )
    printStatus(status)
    assert status == gm.MotionStatus.SUCCESS, "Inverse kinematics calculation failed"
    print(f"✅ IK with custom initial joints succeeded: joint angles={joint_map}")
    time.sleep(0.8)
except Exception as e:
    print(f"❌ IK with custom initial joints exception: {e}")

# Scenario 5: Use RobotStates
try:
    ref_robot_state = gm.RobotStates()
    ref_robot_state.chain_name = target_chain
    ref_robot_state.whole_body_joint = whole_body_joint
    ref_robot_state.base_state = base_state
    target_frame = "EndEffector"
    reference_frame = "base_link"
    status, joint_map = motion.inverse_kinematics_by_state(
        target_pose=chain_pose_baselink[target_chain],
        chain_names=one_chain,
        target_frame=target_frame,
        reference_frame=reference_frame,
        reference_robot_states=ref_robot_state
    )
    printStatus(status)
    assert status == gm.MotionStatus.SUCCESS, "Inverse kinematics calculation failed"
    print(f"✅ RobotStates-based IK succeeded: joint angles={joint_map}")
except Exception as e:
    print(f"❌ RobotStates-based IK exception: {e}")

robot.request_shutdown()
robot.wait_for_shutdown()
robot.destroy()
```

### Get and Set End Effector Pose

**Applicable Scenarios**: Directly get current end effector pose, or move the end effector to a specified pose. Integrates inverse kinematics calculation and execution.

```python title="examples/python/galbot_motion/get_set_end_effector_pose.py"
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
time.sleep(1)

chain_pose_baselink = {
    "leg": [0.0596,-0.0000,1.0327,0.5000,0.5003,0.4997,0.5000],
    "head": [0.0599,0.0002,1.4098,-0.7072,0.0037,0.0037,0.7069],
    "left_arm": [0.1267,0.2342,0.7356,0.0220,0.0127,0.0343,0.9991],
    "right_arm": [0.1267,-0.2345,0.7358,-0.0225,0.0126,-0.0343,0.9991]
}
custom_param = gm.Parameter()
target_frame = "EndEffector"
reference_frame = "base_link"
target_chain = "left_arm"
# Scenario 1: Basic version
try:
    end_ee_link = "left_arm_end_effector_mount_link"
    status, pose = motion.get_end_effector_pose(
        end_effector_frame=end_ee_link,
        reference_frame=reference_frame
    )
    printStatus(status)
    assert status == gm.MotionStatus.SUCCESS, "Failed to get end-effector pose"
    print(f"✅ Basic end-effector pose retrieval succeeded: {pose}")
    time.sleep(0.8)
except Exception as e:
    print(f"❌ Basic end-effector pose retrieval exception: {e}")

# Scenario 2: Specify chain name + custom frame
try:
    status, pose = motion.get_end_effector_pose_on_chain(
        chain_name=target_chain,
        frame_id=target_frame,
        reference_frame=reference_frame
    )
    printStatus(status)
    assert status == gm.MotionStatus.SUCCESS, "Failed to get end-effector pose"
    print(f"✅ End-effector pose retrieval by specified chain succeeded: {pose}")
    time.sleep(0.8)
except Exception as e:
    print(f"❌ End-effector pose retrieval by specified chain exception: {e}")

end_effector_frame="left_arm"
reference_frame = "base_link"
try:
    status = motion.set_end_effector_pose(
        target_pose=chain_pose_baselink[end_effector_frame],
        end_effector_frame=end_effector_frame,
        reference_frame=reference_frame,
        enable_collision_check=False,
        is_blocking=False,
        timeout=5.0,
        params=custom_param
    )
    printStatus(status)
    assert status == gm.MotionStatus.SUCCESS, "Set end-effector pose failed"
    print(f"✅ End-effector pose set succeeded: status={status}")
except Exception as e:
    print(f"❌ End-effector pose setting exception: {e}")

robot.request_shutdown()
robot.wait_for_shutdown()
robot.destroy()
```

### Single Point Motion Planning (Joint Space and Cartesian Space)

**Applicable Scenarios**: Plan a collision-free motion trajectory from the current pose to a single target pose. Suitable for single-point target arrival tasks.

```python title="examples/python/galbot_motion/motion_plan.py"
import time

import galbot_sdk.g1 as gm
from galbot_sdk.g1 import GalbotMotion, GalbotRobot

# NOTE:
# - GalbotMotion currently does NOT provide real-time obstacle perception / automatic environment updates.
# - Motion collision checking uses self-collision + a collision world built from objects you load manually via
#   add_obstacle()/attach_target_object() (including point clouds if you load them explicitly).

motion = GalbotMotion()
robot = GalbotRobot()

def printStatus(status):
        if(status == gm.MotionStatus.SUCCESS):
            print("Result: SUCCESS")
        elif(status == gm.MotionStatus.TIMEOUT):
            print("Result: TIMEOUT")
        elif(status == gm.MotionStatus.FAULT):
            print("Result: FAULT")
        elif(status == gm.MotionStatus.INVALID_INPUT):
            print("Result: INVALID_INPUT")
        elif(status == gm.MotionStatus.INIT_FAILED):
            print("Result: INIT_FAILED")
        elif(status == gm.MotionStatus.IN_PROGRESS):
            print("Result: IN_PROGRESS")
        elif(status == gm.MotionStatus.STOPPED_UNREACHED):
            print("Result: STOPPED_UNREACHED")
        elif(status == gm.MotionStatus.DATA_FETCH_FAILED):
            print("Result: DATA_FETCH_FAILED")
        elif(status == gm.MotionStatus.PUBLISH_FAIL):
            print("Result: PUBLISH_FAIL")
        elif(status == gm.MotionStatus.COMM_DISCONNECTED):
            print("Result: COMM_DISCONNECTED")

if motion.init():
    print("GalbotMotion init OK")
else:
    print("GalbotMotion init FAILED")
if robot.init():
    print("GalbotRobot init OK")
else:
    print("GalbotRobot init FAILED")

# Wait for data to be ready.
time.sleep(1)

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

# Scenario 1: joint-space planning, target type = joint state
try:
    # Construct target joint state

    target_joint = gm.JointStates()
    target_joint.chain_name = "left_arm"
    target_joint.joint_positions = chain_joints[target_joint.chain_name]

    status, traj = motion.motion_plan(
        target=target_joint,
        # When enable_collision_check=True, collision is checked against Motion-side explicitly loaded obstacles
        # (add_obstacle/attach_target_object) and self-collision.
        enable_collision_check=False,
        params=custom_param
    )
    printStatus(status)
    assert status == gm.MotionStatus.SUCCESS, "Planning failed"
    if traj != {}:
        print(f"✅ Joint-space planning + joint-target single-chain single-point planning succeeded: trajectory points={len(traj[target_joint.chain_name])}")
        time.sleep(0.8)
    else:
        print(f"⚠️ Return status is SUCCESS, but trajectory is empty; possibly already reached, check whether the target matches current state or is within tolerance")

except Exception as e:
    print(f"ERROR: joint-space single-point planning exception: {e}")

# Scenario 2: joint-space planning, target type = end-effector pose (Cartesian)
try:
    # Construct target pose state
    target_pose_state = gm.PoseState()
    target_pose_state.chain_name = "left_arm"
    target_pose_state.frame_id = "EndEffector"
    target_pose_state.reference_frame = "base_link"
    target_pose_state.pose = gm.Pose(chain_pose_baselink[target_pose_state.chain_name])
    # target_pose_state.pose.position.x += 0.2

    status, traj = motion.motion_plan(
        target=target_pose_state,
        enable_collision_check=False
    )
    printStatus(status)
    assert status == gm.MotionStatus.SUCCESS, "Planning failed"
    if traj != {}:
        print(f"✅ Joint-space planning + end-effector-pose-target single-chain single-point planning succeeded: trajectory length={len(traj[target_pose_state.chain_name])}")
        time.sleep(0.8)
    else:
        print(f"⚠️ Return status is SUCCESS, but trajectory is empty; possibly already reached, check whether the target matches current state or is within tolerance")

except Exception as e:
    print(f"ERROR: Cartesian single-point planning exception: {e}")

# Scenario 3: joint-space planning with an explicit start state
try:
    # Construct target joint state

    target_joint = gm.JointStates()
    target_joint.chain_name = "left_arm"
    target_joint.joint_positions = chain_joints[target_joint.chain_name]

    start_joint = gm.JointStates()
    start_joint.chain_name = "left_arm"
    start_joint.joint_positions = [0] * 7

    status, traj = motion.motion_plan(
        target=target_joint,
        start=start_joint,
        enable_collision_check=False,
        params=custom_param
    )
    printStatus(status)
    assert status == gm.MotionStatus.SUCCESS, "Planning failed"
    if traj != {}:
        print(f"✅ Joint-space planning + joint-target single-chain single-point planning succeeded: trajectory points={len(traj[target_joint.chain_name])}")
    else:
        print(f"⚠️ Return status is SUCCESS, but trajectory is empty; possibly already reached, check whether the target matches current state or is within tolerance")

except Exception as e:
    print(f"ERROR: joint-space single-point planning exception: {e}")

robot.request_shutdown()
robot.wait_for_shutdown()
robot.destroy()
```

### Multi-Waypoint Trajectory Planning

**Applicable Scenarios**: Plan a continuous motion trajectory through multiple waypoints, suitable for complex motions that need to pass through multiple intermediate points.

```python title="examples/python/galbot_motion/motion_plan_multi_waypoints.py"
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
```

### Collision Detection

**Applicable Scenarios**: Check whether a given joint configuration will cause self-collision or collision with environmental obstacles. Used for feasibility checking before motion planning.

```python title="examples/python/galbot_motion/check_collision.py"
import galbot_sdk.g1 as gm
from galbot_sdk.g1 import GalbotMotion, GalbotRobot, GalbotNavigation   
import time

# NOTE:
# - GalbotMotion currently does NOT provide real-time obstacle perception / automatic environment updates.
# - Collision checking uses self-collision + the collision world built from objects you load manually via
#   add_obstacle()/attach_target_object() (including point clouds if you load them explicitly).

motion = GalbotMotion()
robot = GalbotRobot()
nav = GalbotNavigation()

def printStatus(status):
        if(status == gm.MotionStatus.SUCCESS):
            print("Result: SUCCESS")
        elif(status == gm.MotionStatus.TIMEOUT):
            print("Result: TIMEOUT")
        elif(status == gm.MotionStatus.FAULT):
            print("Result: FAULT")
        elif(status == gm.MotionStatus.INVALID_INPUT):
            print("Result: INVALID_INPUT")
        elif(status == gm.MotionStatus.INIT_FAILED):
            print("Result: INIT_FAILED")
        elif(status == gm.MotionStatus.IN_PROGRESS):
            print("Result: IN_PROGRESS")
        elif(status == gm.MotionStatus.STOPPED_UNREACHED):
            print("Result: STOPPED_UNREACHED")
        elif(status == gm.MotionStatus.DATA_FETCH_FAILED):
            print("Result: DATA_FETCH_FAILED")
        elif(status == gm.MotionStatus.PUBLISH_FAIL):
            print("Result: PUBLISH_FAIL")
        elif(status == gm.MotionStatus.COMM_DISCONNECTED):
            print("Result: COMM_DISCONNECTED")

if motion.init():
    print("GalbotMotion init OK")
else:
    print("GalbotMotion init FAILED")
if robot.init():
    print("GalbotRobot init OK")
else:
    print("GalbotRobot init FAILED")
if nav.init():
    print("GalbotNavigation init OK")
else:
    print("GalbotNavigation init FAILED")

# Wait for data to be ready.
time.sleep(3)

chain_joints = {
    "leg": [0.4992,1.4991,1.0005,0.0000,-0.0004],
    "head": [0.0000,0.0],
    "left_arm": [1.9999,-1.6000,-0.5999,-1.6999,0.0000,-0.7999,0.0000],
    "right_arm": [-2.0000,1.6001,0.6001,1.7000,0.0000,0.8000,0.0000]
}

whole_body_joint = [
    num for key in ["leg", "head", "left_arm", "right_arm"] 
    for num in chain_joints[key]
]
base_state = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]
custom_param = gm.Parameter()

try:
    # Build RobotStates list to check.
    check_states = [gm.RobotStates() for _ in range(2)]
    check_states[0].whole_body_joint = whole_body_joint
    check_states[0].base_state = base_state

    bad_left_arm_joint = [1.99995,-1.60004,0.599905,-1.69994,0,-0.799924,0]

    check_left_arm = gm.JointStates()
    check_left_arm.chain_name = "left_arm"
    check_left_arm.joint_positions = bad_left_arm_joint
    check_states[1] = check_left_arm

    status, collision_res = motion.check_collision(
        start=check_states,
        enable_collision_check=True
    )
    printStatus(status)
    assert status == gm.MotionStatus.SUCCESS, "Collision check failed"
    assert len(collision_res) == len(check_states), "Result size mismatch"
    print(f"OK: collision check finished: {collision_res} (False=no collision)")
except Exception as e:
    print(f"ERROR: collision check exception: {e}")

robot.request_shutdown()
robot.wait_for_shutdown()
robot.destroy()
```

### Attach Tool

**Applicable Scenarios**: Attach a tool (such as a gripper, suction cup, etc. to the robot end effector, updating the motion planning model to account for tool mass and collision volume.

```python title="examples/python/galbot_motion/attach_tool.py"
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

try:
    chain_name = "left_arm"
    tool_name = "suction_cup"
    status = motion.attach_tool(
        chain=chain_name,
        tool=tool_name
    )
    printStatus(status)
    assert status == gm.MotionStatus.SUCCESS, "load failed"
    print(f"✅ Tool attached successfully")
except Exception as e:
    print(f"❌ Tool attachment exception: {e}")

robot.request_shutdown()
robot.wait_for_shutdown()
robot.destroy()
```

### Detach Tool

**Applicable Scenarios**: Remove an attached tool from the robot end effector, restoring the original robot model.

```python title="examples/python/galbot_motion/detach_tool.py"
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

# 1. Detach tool
try:
    chain_name = "left_arm"
    status = motion.detach_tool(
        chain=chain_name
    )
    printStatus(status)
    assert status == gm.MotionStatus.SUCCESS, "detach failed"
    print(f"✅ Tool detached successfully")
except Exception as e:
    print(f"❌ Tool detachment exception: {e}") 

robot.request_shutdown()
robot.wait_for_shutdown()
robot.destroy()
```

### Get Link Names List

**Applicable Scenarios**: Get a list of names of all links in the robot model, used for collision detection and motion planning debugging.

```python title="examples/python/galbot_motion/get_link_names.py"
import time
import galbot_sdk.g1 as gm
from galbot_sdk.g1 import GalbotMotion, GalbotRobot

# Get and initialize the GalbotMotion singleton
motion = GalbotMotion()
robot = GalbotRobot()

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

try:
    # Get all link names
    all_link_names = motion.get_link_names(only_end_effector=False)
    print(f"\nAll link names (total {len(all_link_names)}):")
    for i, link_name in enumerate(all_link_names, 1):
        print(f"  {i}. {link_name}")

    # getend effectorexecute link
    ee_link_names = motion.get_link_names(only_end_effector=True)
    print(f"\nEnd-effector link names (total {len(ee_link_names)}):")
    for i, link_name in enumerate(ee_link_names, 1):
        print(f"  {i}. {link_name}")

    # example: link kinematics
    if ee_link_names:
        print(f"\nRun forward kinematics using end-effector link '{ee_link_names[0]}'...")
        success, fk_result = motion.forward_kinematics(ee_link_names[0])
        if success == gm.MotionStatus.SUCCESS:
            print(f"Forward-kinematics result: {fk_result}")
        else:
            print(f"Forward-kinematics computation failed: {success}")
except Exception as e:
    print(f"❌ Link-name retrieval exception: {e}")

robot.request_shutdown()
robot.wait_for_shutdown()
robot.destroy()
```

### Add/Remove Environment Collision Objects

**Applicable Scenarios**: Add obstacles to the motion planning environment or remove added obstacles, enabling motion planning to account for environmental obstacles.

```python title="examples/python/galbot_motion/add_obstacle.py"
import time

import galbot_sdk.g1 as gm
from galbot_sdk.g1 import GalbotMotion, GalbotRobot

# NOTE:
# - GalbotMotion currently does NOT provide real-time obstacle perception / automatic environment updates.
# - If you want Motion collision checking to consider obstacles (including point clouds), you must load them
#   manually via add_obstacle()/attach_target_object().

motion = GalbotMotion()
robot = GalbotRobot()

def printStatus(status):
        if(status == gm.MotionStatus.SUCCESS):
            print("Result: SUCCESS")
        elif(status == gm.MotionStatus.TIMEOUT):
            print("Result: TIMEOUT")
        elif(status == gm.MotionStatus.FAULT):
            print("Result: FAULT")
        elif(status == gm.MotionStatus.INVALID_INPUT):
            print("Result: INVALID_INPUT")
        elif(status == gm.MotionStatus.INIT_FAILED):
            print("Result: INIT_FAILED")
        elif(status == gm.MotionStatus.IN_PROGRESS):
            print("Result: IN_PROGRESS")
        elif(status == gm.MotionStatus.STOPPED_UNREACHED):
            print("Result: STOPPED_UNREACHED")
        elif(status == gm.MotionStatus.DATA_FETCH_FAILED):
            print("Result: DATA_FETCH_FAILED")
        elif(status == gm.MotionStatus.PUBLISH_FAIL):
            print("Result: PUBLISH_FAIL")
        elif(status == gm.MotionStatus.COMM_DISCONNECTED):
            print("Result: COMM_DISCONNECTED")

if motion.init():
    print("GalbotMotion init OK")
else:
    print("GalbotMotion init FAILED")
if robot.init():
    print("GalbotRobot init OK")
else:
    print("GalbotRobot init FAILED")

# Wait for data to be ready.
time.sleep(2)

# 1) Add a box collision object into Motion environment.
#    This affects Motion-side collision checking (e.g., motion_plan/check_collision).
try:
    obstacle_id = "box_test_1"
    obj_type = "box"
    obj_pose = [1.0, 0.0, 1.0, 0,0,0,1]
    obj_size = [1.0, 1.0, 1.0]
    target_frame = "world"
    status = motion.add_obstacle(
        obstacle_id=obstacle_id,
        obstacle_type=obj_type,
        pose=obj_pose,
        scale=obj_size,
        target_frame=target_frame
    )
    printStatus(status)
    motion.clear_obstacle()
    assert status == gm.MotionStatus.SUCCESS, "Failed to add obstacle"
    print(f"OK: added obstacle: {obstacle_id}")
except Exception as e:
    print(f"ERROR: add obstacle exception: {e}")

# 2) Add a duplicate ID (expected to fail).
try:
    obstacle_id = "box_test_1"
    obj_type = "box"
    obj_pose = [1.0, 0.0, 1.0, 0,0,0,1]
    obj_size = [1.0, 1.0, 1.0]
    target_frame = "world"
    status = motion.add_obstacle(
        obstacle_id=obstacle_id,
        obstacle_type=obj_type,
        pose=obj_pose,
        scale=obj_size,
        target_frame=target_frame
    )
    status = motion.add_obstacle(
        obstacle_id=obstacle_id,
        obstacle_type=obj_type,
        pose=obj_pose,
        scale=obj_size,
        target_frame=target_frame
    )
    printStatus(status)
    motion.clear_obstacle()
    assert status == gm.MotionStatus.FAULT, "Expected duplicate obstacle ID to fail"
    print("OK: duplicate obstacle ID is rejected")
except Exception as e:
    print(f"ERROR: duplicate obstacle exception: {e}")

robot.request_shutdown()
robot.wait_for_shutdown()
robot.destroy()
```

## Class: GalbotNavigation

### Get Instance / Initialize

**Applicable Scenarios**: Get the navigation module singleton and initialize. Must be called before using navigation functions.

```python title="examples/python/galbot_navigation/get_instance.py"
from galbot_sdk.g1 import GalbotNavigation
from galbot_sdk.g1 import GalbotRobot
import numpy as np

# Initialize system and navigation module
robot = GalbotRobot()
robot.init()

nav = GalbotNavigation()
nav.init()

print("GalbotNavigation has been initialized:", nav is not None)

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')
```

### Relocalize / Is Localized / Get Current Pose

**Applicable Scenarios**: Trigger relocalization, check if the robot is successfully localized, and get the robot's current pose in the map.

```python title="examples/python/galbot_navigation/relocalized.py"
from galbot_sdk.g1 import GalbotNavigation
from galbot_sdk.g1 import GalbotRobot
import numpy as np
import time

nav = GalbotNavigation()
nav.init()
robot = GalbotRobot()
robot.init()

init_pose = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0])

# success
while not nav.is_localized():
    nav.relocalize(init_pose)
    time.sleep(0.5)

print("Current pose:", nav.get_current_pose())

nav.stop_navigation()
# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print('Resources released successfully')
```

### Check Path Reachability and Blocking Navigation to Goal

**Applicable Scenarios**: Check if the target point is reachable, and if reachable, block and wait for navigation to complete reaching the target. Convenient for simple scenarios.

```python title="examples/python/galbot_navigation/check_path_reachability.py"
from galbot_sdk.g1 import GalbotNavigation
from galbot_sdk.g1 import GalbotRobot
from galbot_sdk.g1 import ControlStatus, G1ControllerName
import numpy as np
import sys

nav = GalbotNavigation()
nav.init()
robot = GalbotRobot()
robot.init()

start = nav.get_current_pose()
goal = np.array([1.0, 1.0, 0.0, 0, 0, 0.4794255, 0.8775826])

res = robot.switch_controller(G1ControllerName.CHASSIS_POSE_CTRL)
if res != ControlStatus.SUCCESS:
    print("Failed to switch controller!")
    sys.exit(1)
else:
    print("Controller switched successfully!")

if nav.check_path_reachability(goal, start):
    status = nav.navigate_to_goal(
        goal, enable_collision_check=True, is_blocking=True, timeout=30
    )
    print("navigate_to_goal returned status:", status)
    print("Reached or not:", nav.check_goal_arrival())
else:
    print("Path unreachable or unsafe")

nav.stop_navigation()
# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print("Resources released successfully")
```

### Non-blocking Navigation + Polling for Arrival

**Applicable Scenarios**: Start navigation without blocking the current thread, allowing other processing during navigation, and need to poll to determine if the target has been reached. Suitable for scenarios requiring asynchronous processing.

```python title="examples/python/galbot_navigation/navigate_to_goal.py"
from galbot_sdk.g1 import GalbotNavigation
from galbot_sdk.g1 import GalbotRobot
from galbot_sdk.g1 import ControlStatus, G1ControllerName
import numpy as np
import time
import sys

nav = GalbotNavigation()
nav.init()
robot = GalbotRobot()
robot.init()

goal = np.array([0.5, 0.0, 0.0, 0, 0, 0.0, 1.0])

res = robot.switch_controller(G1ControllerName.CHASSIS_POSE_CTRL)
if res != ControlStatus.SUCCESS:
    print("Failed to switch controller!")
    sys.exit(1)
else:
    print("Controller switched successfully!")

nav.navigate_to_goal(goal, enable_collision_check=True, is_blocking=False, timeout=20)

start_time = time.time()
reached = False

while True:
    if nav.check_goal_arrival():
        reached = True
        break
    if time.time() - start_time > 20:
        print("Navigation timed out; target not reached within 20s")
        break
    print("Navigating...")
    time.sleep(0.5)

if reached:
    print("Target reached")

nav.stop_navigation()
# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print("Resources released successfully")
```

### Move Straight to Goal / Stop Navigation

**Applicable Scenarios**: Move the robot in a straight line to the target point, or stop the currently ongoing navigation task.

```python title="examples/python/galbot_navigation/move_straight_to.py"
from galbot_sdk.g1 import GalbotNavigation
from galbot_sdk.g1 import GalbotRobot
from galbot_sdk.g1 import ControlStatus, G1ControllerName
import numpy as np
import time
import sys

nav = GalbotNavigation()
nav.init()
robot = GalbotRobot()
robot.init()

target = np.array([0.2, 0.0, 0.0, 0, 0, 0.0, 1.0])

res = robot.switch_controller(G1ControllerName.CHASSIS_POSE_CTRL)
if res != ControlStatus.SUCCESS:
    print("Failed to switch controller!")
    sys.exit(1)
else:
    print("Controller switched successfully!")

nav.move_straight_to(target, is_blocking=False, timeout=10)
time.sleep(1.0)
nav.stop_navigation()

# send SIGINT shutdown signal
robot.request_shutdown()
# Wait until entering shutdown state
robot.wait_for_shutdown()
# Perform SDK resource release
robot.destroy()
print("Resources released successfully")
```

### Get Navigation Status + Polling for SUCCESS/FAILED or Timeout

**Applicable Scenarios**: Get the execution status of the current navigation task, used for polling in non-blocking navigation.

```python title="examples/python/galbot_navigation/get_navigation_status.py"
"""
example: navigation get_navigation_status, SUCCESS/FAILED timeout exit,
Avoid deadlock and execute error logic.
"""

from galbot_sdk.g1 import GalbotNavigation
from galbot_sdk.g1 import GalbotRobot
from galbot_sdk.g1 import NavigationTaskStatus, ControlStatus, G1ControllerName
import numpy as np
import time
import sys

nav = GalbotNavigation()
nav.init()
robot = GalbotRobot()
robot.init()

goal = np.array([0.5, 0.0, 0.0, 0, 0, 0.0, 1.0])
timeout_s = 20.0
poll_interval_s = 0.5

res = robot.switch_controller(G1ControllerName.CHASSIS_POSE_CTRL)
if res != ControlStatus.SUCCESS:
    print("Failed to switch controller!")
    sys.exit(1)
else:
    print("Controller switched successfully!")
# Non-blocking navigation
nav.navigate_to_goal(
    goal, enable_collision_check=True, is_blocking=False, timeout=timeout_s
)
start = time.time()

while True:
    status = nav.get_navigation_status()
    elapsed = time.time() - start

    if status == NavigationTaskStatus.SUCCESS:
        print("Target reached")
        break
    if status == NavigationTaskStatus.FAILED:
        print("Navigation failed; exit error-handling logic promptly")
        break
    if elapsed >= timeout_s:
        print("navigationtimeout, exit")
        break

    if status == NavigationTaskStatus.RUNNING:
        print(f"Navigating... Status: {status.name}, elapsed: {elapsed:.1f}s")
    else:
        print(f"Status: {status.name}, elapsed: {elapsed:.1f}s")

    time.sleep(poll_interval_s)

nav.stop_navigation()
robot.request_shutdown()
robot.wait_for_shutdown()
robot.destroy()
print("Resources released successfully")
```

### Complete Running Example (Simple Workflow)

**Applicable Scenarios**: Demonstrates the complete usage workflow of navigation functionality, including initialization, relocalization, navigation to target and other steps for reference.

```python title="examples/python/galbot_navigation/complete_example.py"
from galbot_sdk.g1 import GalbotRobot, GalbotNavigation
from galbot_sdk.g1 import ControlStatus, G1ControllerName
import numpy as np
import time
import sys

robot = GalbotRobot()
robot.init()
nav = GalbotNavigation()
nav.init()

init_pose = np.array([0.0, 0.0, 0.0, 0, 0, 0.0, 1.0])
goal_pose = np.array([1.0, 0.0, 0.0, 0, 0, 0.0, 1.0])

res = robot.switch_controller(G1ControllerName.CHASSIS_POSE_CTRL)
if res != ControlStatus.SUCCESS:
    print("Failed to switch controller!")
    sys.exit(1)
else:
    print("Controller switched successfully!")

while not nav.is_localized():
    nav.relocalize(init_pose)
    time.sleep(0.5)

if nav.check_path_reachability(goal_pose, nav.get_current_pose()):
    nav.navigate_to_goal(
        goal_pose, enable_collision_check=True, is_blocking=True, timeout=30
    )
    print("Whether reached:", nav.check_goal_arrival())

nav.stop_navigation()
# Shutdown system
robot.request_shutdown()
robot.wait_for_shutdown()
robot.destroy()
```

## Class: GalbotPerception

### Foundation Stereo: single run_once and save a colorized depth image

**Applicable scenarios**: Trigger a single stereo depth estimation inference and retrieve the result.

```python title="examples/python/galbot_perception/foundation_stereo_example.py"
"""Foundation stereo depth example (G1): single run_once, save a pseudo-color depth image."""

import time

import cv2
import numpy as np

try:
    from galbot_sdk import (
        GalbotPerception,
        GalbotRobot,
        MachineType,
        PerceptionModule,
    )
except ImportError:
    print("Failed to import galbot_sdk, please install it first or check if it is in PYTHONPATH")
    raise

OUTPUT_IMAGE_PATH = "foundation_stereo_depth.png"


def main():
    robot = GalbotRobot.get_instance(MachineType.G1)
    if not robot.init():
        print("Robot init failed")
        return
    print("Robot init OK")

    perception = GalbotPerception.get_instance(MachineType.G1)
    if not perception.init({PerceptionModule.FOUNDATION_STEREO, PerceptionModule.LIGHT_STEREO}):
        print("Perception init failed")
        return
    print("Perception init OK")

    time.sleep(12)  # Wait for perception models to load
    print("Triggering single inference...")

    if not perception.run_once(PerceptionModule.FOUNDATION_STEREO):
        print("run_once failed to send command")
        return

    print("Waiting for inference result...")
    if not perception.wait_for_new_result(
        PerceptionModule.FOUNDATION_STEREO, timeout_s=6.0
    ):
        print("Timed out waiting for inference result")
        return

    ok, result = perception.get_latest_result(PerceptionModule.FOUNDATION_STEREO)
    if not ok:
        print("get_latest_result failed")
        return

    print(result.get_result_info())

    depth_map = result.instance_mask
    if depth_map is None:
        print("No depth map (instance_mask is empty)")
        return

    print(f"Depth map shape: {depth_map.shape}, dtype: {depth_map.dtype}")
    print(f"Depth value range: [{np.nanmin(depth_map)}, {np.nanmax(depth_map)}]")

    depth_f = depth_map.astype(np.float32)
    valid = depth_f[depth_f > 0]
    if valid.size > 0:
        vmin, vmax = np.percentile(valid, [1, 99])
        normalized = np.clip((depth_f - vmin) / (vmax - vmin + 1e-6), 0, 1)
    else:
        normalized = np.zeros_like(depth_f)
    colored = cv2.applyColorMap(
        (normalized * 255).astype(np.uint8), cv2.COLORMAP_TURBO
    )

    if cv2.imwrite(OUTPUT_IMAGE_PATH, colored):
        print(f"Saved: {OUTPUT_IMAGE_PATH}")
    else:
        print(f"Failed to save: {OUTPUT_IMAGE_PATH}")


if __name__ == "__main__":
    main()
    GalbotRobot.get_instance(MachineType.G1).request_shutdown()
    GalbotRobot.get_instance(MachineType.G1).wait_for_shutdown()
    GalbotRobot.get_instance(MachineType.G1).destroy()
```

## Class: Parameter

**Applicable Scenarios**: Create a motion planning parameter object used to configure various parameters for motion planning such as velocity limits, acceleration limits, planning time, etc.

```python title="examples/python/galbot_motion/create_parameter.py"
from galbot_sdk.g1 import Parameter, create_parameter, G1JointGroup

# Create Parameter via constructor and set options
p = Parameter()
p.set_blocking(True)
p.set_check_collision(False)
p.set_timeout(5.0)
p.set_actuate('with_chain_only')
p.set_tool_pose(False)
p.set_reference_frame('base_link')

p.joint_state = {
    G1JointGroup.left_arm: [0.0] * 7,
    # Can add others if needed:
    # G1JointGroup.right_arm: [0.0] * 7,
    # G1JointGroup.LEG: [0.0] * 4,
}

print('blocking:', p.get_blocking())
print('collision check:', p.get_check_collision())
print('timeout:', p.get_timeout())

# Or use factory function to quickly create Parameter
p2 = create_parameter(direct_execute=False, blocking=True, timeout=3.0, actuate='with_chain_only', tool_pose=False, check_collision=True)
print('Factory-created timeout:', p2.get_timeout())
```

## Utility Functions

### check_motion_status

**Applicable Scenarios**: Check motion planning execution result status, determine if planning succeeded, and print error messages.

```python title="examples/python/galbot_motion/check_motion_status.py"
from galbot_sdk.g1 import MotionStatus, check_motion_status

status_str = check_motion_status(MotionStatus.SUCCESS)
print('MotionStatus string:', status_str)
```

### create_joint_state / create_pose_state

**Applicable Scenarios**: Quickly create joint state and pose state objects, facilitating motion planning interface calls.

```python title="examples/python/galbot_motion/create_pose_state.py"
from galbot_sdk.g1 import create_joint_state, create_pose_state, JointStates, PoseState, Pose

# Create helper objects using the factory function
js = create_joint_state()
ps = create_pose_state()

# Fill example fields
js.chain_name = 'left_arm'
js.joint_positions = [0.0] * 7

ps.chain_name = 'left_arm'
# 7D vector: x, y, z, qx, qy, qz, qw
ps.pose = Pose([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0])

print(type(js), js.chain_name)
print(type(ps), ps.chain_name)
```
