
# C++ Examples

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
4. To avoid hard-coded mistakes, call `get_joint_group_names()` and `get_joint_names(true, groups)` first.

### Typical Group Scenarios (G1)

| Joint Group | Typical Scenario |
|-------------|------------------|
| `head` | Head orientation / camera aiming |
| `left_arm` / `right_arm` | Arm reaching and manipulation |
| `leg` | Lower-body posture adjustment |
| `left_gripper` / `right_gripper` | Grasp width control |
| `left_suction_cup` / `right_suction_cup` | Vacuum pick and place |

## Sensor Types and Frames

**For sensor data access** (`get_rgb_data`, `get_depth_data`, `get_imu_data`, `get_lidar_data`), use the `SensorType` enum to specify which sensor to query. Available SensorType enums are documented in: **[C++ API Reference > SensorType](api_cpp_reference.md#galbot-sdk-sensortype-enum)**.

**For sensor extrinsic calibration**, there are two methods:
- **[get_sensor_extrinsic()](api_cpp_reference.md#galbotrobot-get_sensor_extrinsic-function)**: SDK internally maps frame IDs, pass SensorType directly
- **[get_transform()](api_cpp_reference.md#galbotrobot-get_transform-function)**: Requires explicit frame names. The second column below lists frame IDs for each sensor.

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

> **Note**: Call **[get_frame_names()](api_cpp_reference.md#galbotrobot-get_frame_names-function)** to get all available coordinate frames.

## Class: GalbotRobot

Tips: If you get data immediately after program startup, the data may not be ready right away. You may sleep for a few seconds as appropriate.

### Get Instance and Initialize (get_instance && init)

**Applicable Scenarios**: During program startup, get the robot singleton and complete SDK initialization. Must be called before using other APIs.

```cpp title="examples/cpp/galbot_robot/src/get_instance_init_example.cpp"
#include <iostream>
#include <vector>
#include <array>
#include <memory>
#include <thread>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

int main() {
    // Get object instance
    auto& robot = GalbotRobot::get_instance(MachineType::G1);
    
    // Initialize singleton instance
    if (robot.init()) {
        std::cout << "System initialized successfully!" << std::endl;
    } else {
        std::cerr << "System initialization failed!" << std::endl;
        return -1;
    }

    // Check whether it is in the running state
    while (robot.is_running()) {
        // do something
        std::cout << "System is running." << std::endl;
        break;
    }

    // Register an exit callback (optional; automatically triggered when an exit signal is received)
    robot.register_exit_callback([]() {
        std::cout << "System is exiting..." << std::endl;
    });
    std::cout << "System exit callback registered successfully" << std::endl;

    // Send exit signal
    robot.request_shutdown();
    // Wait until entering shutdown state
    robot.wait_for_shutdown();
    // Release SDK related resources
    robot.destroy();
    std::cout << "Program finished" << std::endl;

    return 0;
}
```

### Release SDK Resources and Exit Program

**Applicable Scenarios**: Release all resources occupied by the SDK before program exit, normally shut down the system.

```cpp title="examples/cpp/galbot_robot/src/stop_base_example.cpp"
#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <string>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

int main() {
    // Get object instance
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize system
    if (robot.init()) {
        std::cout << "System initialized successfully!" << std::endl;
    } else {
        std::cerr << "System initialization failed!" << std::endl;
        return -1;
    }

    // Program started, waiting for data
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));

    // Stop chassis motion
    while (true) {
        ControlStatus status = robot.stop_base();
        if (status == ControlStatus::SUCCESS) {
            std::cout << "Chassis motion has been stopped successfully!" << std::endl;
            break;
        } else {
            std::cerr << "Chassis stop motion failed, retrying..." << std::endl;
        }
    }

    // Exit system and release SDK resources
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### Log interface

**Applicable Scenarios**: Output logs using the SDK's built-in logging system, unifying log levels and formats.

```cpp title="examples/cpp/galbot_robot/src/logger_example.cpp"
#include <iostream>

#include "galbot_robot.hpp"
#include "galbot_sdk_logger.hpp"

using namespace galbot::sdk;

int main() {
  // Get and initialize the GalbotRobot singleton
  auto& robot = GalbotRobot::get_instance(MachineType::G1);
  robot.init();
  // ==============================
  // 1. Initialize SDK logging
  // ==============================
  LoggerConfig logger_config;
  // Log generation path; if not filled, defaults to ~/galbot_sdk_log/user_log
  logger_config.path = "";
  // Log file name; if not filled, defaults to <process_name>_<current_time>_<pid>_<thread_id>.log
  logger_config.file_name = "";
  // Maximum bytes per single log file
  logger_config.file_max_size = 1024 * 1024 * 10; // 10MB
  // Maximum number of rotating log files; creates new file when full, retaining up to file_max_num files
  logger_config.file_max_num = 5;
  // Minimum log output level
  logger_config.level = LogLevel::DEBUG;
  // Whether to output to terminal; default is false
  logger_config.console_output = false;

  if (!init_galbot_sdk_logger(logger_config)) {
    std::cerr << "failed to init galbot sdk logger" << std::endl;
    return -1;
  } else {
    std::cout << "galbot sdk logger initialized successfully" << std::endl;
  }

  // ==============================
  // 2. Print logs at different levels
  // ==============================
  GALBOT_SDK_LOG_TRACE << "this is trace log";
  GALBOT_SDK_LOG_DEBUG << "this is debug log";
  GALBOT_SDK_LOG_INFO << "this is info log";
  GALBOT_SDK_LOG_WARN << "this is warning log";
  GALBOT_SDK_LOG_ERROR << "this is error log";
  GALBOT_SDK_LOG_CRITICAL << "this is critical log";

  // ==============================
  // 3. Supports chained << style
  // ==============================
  int robot_id = 3;
  GALBOT_SDK_LOG_INFO << "robot_id = " << robot_id;

  GALBOT_SDK_LOG_INFO << "example program finished";

  // Exit the system and release SDK and logger resources
  robot.request_shutdown();
  robot.wait_for_shutdown();
  robot.destroy();
  return 0;
}
```

### Set Joint Positions (set_joint_positions)

**Applicable Scenarios**: Single-point movement, low-frequency position control tasks. This interface performs velocity-limited trajectory interpolation internally, making it suitable for one-time movement to target joint angles.

> **WARNING**: This interface is **NOT suitable** for high-frequency joint control scenarios with model inference output! Each call to this interface produces a new trajectory interpolation, continuous calls will result in discontinuous motion and delay.
>
> If you are working on a **model inference** scenario, please use [`set_joint_commands`](#set_joint_commands) or [`set_joint_commands_batch`](#set_joint_commands_batch) to issue joint commands directly.

```cpp title="examples/cpp/galbot_robot/src/set_joint_positions_example.cpp"
#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <string>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

int main() {
    // Get object instance
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize system
    if (robot.init()) {
        std::cout << "System initialized successfully!" << std::endl;
    } else {
        std::cerr << "System initialization failed!" << std::endl;
        return -1;
    }

    // Program started, waiting for data
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));

    // Get specified joint names; joint groups include ["leg", "head", "left_arm", "right_arm"]
    std::vector<std::string> joint_groups = {"head"};
    bool only_active_joint = true;  // Get active joints
    auto head_joint_names_vec =
        robot.get_joint_names(only_active_joint, joint_groups);
    std::cout << "Head joint names:" << std::endl;
    for (size_t i = 0; i < head_joint_names_vec.size(); ++i) {
        std::cout << i << ": " << head_joint_names_vec[i] << std::endl;
    }
    // Passing an empty array returns all joint group information by default
    std::vector<std::string> null_vec = {};
    auto all_joint_names_vec =
        robot.get_joint_names(only_active_joint, null_vec);
    std::cout << "All joint names:" << std::endl;
    for (size_t i = 0; i < all_joint_names_vec.size(); ++i) {
        std::cout << i << ": " << all_joint_names_vec[i] << std::endl;
    }

    // Joint groups to control; passing an empty array controls leg, head, left_arm, and right_arm by default
    joint_groups = {"head"};
    // Specific joints to control; if provided, this overrides the joint_groups parameter
    std::vector<std::string> joint_names = {};
    // Joint positions; head joint group contains two joints
    std::vector<double> joint_pos = {0.2, 0.2};
    // Whether to block and wait for joint angles to reach position or timeout
    bool is_block = true;
    // Maximum joint speed (rad/s)
    double speed_rad_s = 0.1;
    // Maximum wait time (seconds)
    double timeout_s = 10.0;

    // Set joint positions
    ControlStatus joint_execution_status =
        robot.set_joint_positions(joint_pos, joint_groups,joint_names, 
            is_block, speed_rad_s,timeout_s);

    if (joint_execution_status == ControlStatus::SUCCESS) {
        std::cout << "Joint command set successfully!" << std::endl;
    } else {
        std::cerr << "Failed to set joint command!" << std::endl;
    }

    // Query joint positions by group; empty array defaults to leg, head, dual-arm groups. Second parameter specifies joint names, which overrides joint_groups if provided.
    auto ret_positions = robot.get_joint_positions(joint_groups, {});
    for (auto position : ret_positions) {
        std::cout << "joint positions is " << position << std::endl;
    }

    // Use specific joint names for control; this parameter overrides joint_groups
    joint_names = {"head_joint1", "head_joint2"};
    joint_pos = {0.0, 0.0};

    // Set joint positions
    joint_execution_status = robot.set_joint_positions(joint_pos, joint_groups,joint_names, 
            is_block, speed_rad_s,timeout_s);

    if (joint_execution_status == ControlStatus::SUCCESS) {
        std::cout << "Joint command set successfully!" << std::endl;
    } else {
        std::cerr << "Failed to set joint command!" << std::endl;
    }

    // Query joint positions by group; empty array defaults to leg, head, dual-arm groups. Second parameter specifies joint names, which overrides joint_groups if provided.
    ret_positions = robot.get_joint_positions(joint_groups, {});
    for (auto position : ret_positions) {
        std::cout << "joint positions is " << position << std::endl;
    }

    // Exit system and release SDK resources
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### Set Gripper Command (set_gripper_command)

**Applicable Scenarios**: Control gripper opening and closing. Supports both position control and torque control modes.

```cpp title="examples/cpp/galbot_robot/src/set_gripper_command_example.cpp"
#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <string>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

void print_gripper_state(std::shared_ptr<GripperState> gripper_state) {
    std::cout << "Timestamp (ns): " << gripper_state->timestamp_ns << std::endl;

    std::cout << " width "  << gripper_state->width << " velocity " << gripper_state->velocity
                << " effort " << gripper_state->effort << " is moving "
                << gripper_state->is_moving << std::endl;
}

int main() {
    // Get object instance
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize system
    if (robot.init()) {
        std::cout << "System initialized successfully!" << std::endl;
    } else {
        std::cerr << "System initialization failed!" << std::endl;
        return -1;
    }

    // Program started, waiting for data
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));

    // Gripper width (m)
    double width_m = 0.02;
    // Gripper speed (m/s)
    double velocity_mps = 0.05;
    // Gripper torque (N·m)
    double effort = 10;
    // Whether to block until execution completes
    bool is_blocking = false;
    // Set left gripper width to 0.02m, speed 0.05m/s, torque 10, block until execution completes
    ControlStatus gripper_execution_status =
        robot.set_gripper_command("left_gripper", width_m, velocity_mps,
                                        effort, is_blocking);

    if (gripper_execution_status == ControlStatus::SUCCESS) {
        std::cout << "Gripper command set successfully!" << std::endl;
    } else {
        std::cerr << "Failed to set gripper command!" << std::endl;
    }

    // Get gripper state
    JointStateMessage joint_state;
    auto gripper_state_ptr = robot.get_gripper_state("left_gripper");

    if (gripper_state_ptr == nullptr) {
        std::cerr << "get gripper state error" << std::endl;
    } else {
        print_gripper_state(gripper_state_ptr);
    }

    // Gripper width (m)
    width_m = 0.1;
    // Gripper speed (m/s)
    velocity_mps = 0.05;
    // Gripper torque (N·m)
    effort = 10;
    // Whether to block until execution completes
    is_blocking = false;
    // Set left gripper width to 0.1m, speed 0.05m/s, torque 10, block until execution completes
    gripper_execution_status =
        robot.set_gripper_command("left_gripper", width_m, velocity_mps,
                                        effort, is_blocking);

    if (gripper_execution_status == ControlStatus::SUCCESS) {
        std::cout << "Gripper command set successfully!" << std::endl;
    } else {
        std::cerr << "Failed to set gripper command!" << std::endl;
    }

    // Exit system and release SDK resources
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### Set Suction Cup Command (set_suction_cup_command)

**Applicable Scenarios**: Control suction cup to suck/release objects, get current suction cup status.

```cpp title="examples/cpp/galbot_robot/src/set_suction_cup_command_example.cpp"
#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <string>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

int main() {
    // Get object instance
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize system
    if (robot.init()) {
        std::cout << "System initialized successfully!" << std::endl;
    } else {
        std::cerr << "System initialization failed!" << std::endl;
        return -1;
    }

    // Program started, waiting for data
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));

    // Activate suction cup
    if (robot.set_suction_cup_command("right_suction_cup", true) == ControlStatus::SUCCESS) {
        std::cout << "Suction cup activation command sent successfully" << std::endl;
        
    } else {
        std::cerr << "Suction cup activation command failed to send!" << std::endl;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(1000));
    // Deactivate suction cup
    if (robot.set_suction_cup_command("right_suction_cup", false) == ControlStatus::SUCCESS) {
        std::cout << "Suction cup deactivation command sent successfully" << std::endl;
        
    } else {
        std::cerr << "Suction cup deactivation command failed to send" << std::endl;
    }

    // Exit system and release SDK resources
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### Stop Trajectory Execution (stop_trajectory_execution)

**Applicable Scenarios**: Stop currently executing joint trajectory and interrupt ongoing motion.

```cpp title="examples/cpp/galbot_robot/src/stop_trajectory_execution_example.cpp"
#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <string>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

int main() {
    // Get object instance
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize system
    if (robot.init()) {
        std::cout << "System initialized successfully!" << std::endl;
    } else {
        std::cerr << "System initialization failed!" << std::endl;
        return -1;
    }

    // Program started, waiting for data
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));

    // Stop trajectory execution
    while(true) {
        ControlStatus joint_execution_status =
            robot.stop_trajectory_execution();
        
        // Check execution results
        if (joint_execution_status == ControlStatus::SUCCESS) {
            std::cout << "Trajectory stop command sent successfully" << std::endl;
            break;
        } else {
            std::cerr << "Failed to send trajectory stop command, retrying..." << std::endl;
        }
    }

    // Exit system and release SDK resources
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### Set Trajectory (execute_joint_trajectory)

**Applicable Scenarios**: Execute a predefined joint-space trajectory with multiple waypoints. The SDK executes the entire trajectory according to time nodes.

```cpp title="examples/cpp/galbot_robot/src/execute_joint_trajectory_example.cpp"
#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <string>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

double g_target_time = 10;
double g_start_time = 10;

std::string trajectory_status_to_string(TrajectoryControlStatus status) {
  switch (status) {
  case TrajectoryControlStatus::INVALID_INPUT:
    return "INVALID_INPUT";
  case TrajectoryControlStatus::RUNNING:
    return "RUNNING";
  case TrajectoryControlStatus::COMPLETED:
    return "COMPLETED";
  case TrajectoryControlStatus::STOPPED_UNREACHED:
    return "STOPPED_UNREACHED";
  case TrajectoryControlStatus::ERROR:
    return "ERROR";
  case TrajectoryControlStatus::DATA_FETCH_FAILED:
    return "DATA_FETCH_FAILED";
  case TrajectoryControlStatus::STATUS_NUM:
    return "STATUS_NUM";
  default:
    return "UNKNOWN_STATUS";
  }
}

void wait_for_traj_reached(const std::vector<std::string> &joint_groups) {
    std::vector<TrajectoryControlStatus> traj_exec_states;
    int count = 0;
    bool all_reached = false;
    while (count++ < 150) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        all_reached = true;
        traj_exec_states = GalbotRobot::get_instance(MachineType::G1)
                            .check_trajectory_execution_status(joint_groups);
        if (traj_exec_states.size() != joint_groups.size()) {
        std::cout << "traj_exec_states size != joint_groups size" << std::endl;
        }
        for (int i = 0; i < joint_groups.size(); ++i) {
        std::cout << joint_groups[i] << " exec state is "
                    << trajectory_status_to_string(traj_exec_states[i])
                    << std::endl;
        if (traj_exec_states[i] != TrajectoryControlStatus::COMPLETED) {
            all_reached = false;
        }
        }

        if (all_reached) {
            std::cout << "all reached" << std::endl;
            break;
        }
    }
    for (const auto &status : traj_exec_states) {
        std::cout << "done reached state is " << trajectory_status_to_string(status)
                << std::endl;
    }
}

std::vector<TrajectoryPoint>
generate_target_trajectory(int32_t joint_size, double ampl = 0.2,
                           double cycle = 10) {
  double amplitude = -ampl;
  double frequency = 1.0 / cycle;
  double phase = -M_PI / 2;
  double offset = amplitude;
  double dt = 0.004;
  int step = g_target_time / dt;

  std::vector<TrajectoryPoint> trajectory_data_vec;
  trajectory_data_vec.resize(step + 1);
  // Create a RobotCommand trajectory
  for (int i = 0; i <= step; ++i) {
    double t = i * dt;
    trajectory_data_vec[i].time_from_start_second = g_start_time + t;
    trajectory_data_vec[i].joint_command_vec.resize(joint_size);
    // Joint command
    for (int j = 0; j < joint_size; ++j) {
      trajectory_data_vec[i].joint_command_vec[j].position =
          offset + amplitude * std::sin(2 * M_PI * frequency * t + phase);
      trajectory_data_vec[i].joint_command_vec[j].velocity =
          amplitude * 2 * M_PI * frequency *
          std::cos(2 * M_PI * frequency * t + phase);
    }
  }

  return trajectory_data_vec;
}

int main() {
    // Get object instance
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize system
    if (robot.init()) {
        std::cout << "System initialized successfully!" << std::endl;
    } else {
        std::cerr << "System initialization failed!" << std::endl;
        return -1;
    }

    // Program started, waiting for data
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));

    // Execute joint trajectory
    Trajectory trajectory;
    // Enter joint group name to control, including ["leg", "head", "left_arm", "right_arm", "left_gripper", "right_gripper"]
    trajectory.joint_groups = {"head"};
    // Fill this field to control specific joint angles, which will override joint_groups if provided
    trajectory.joint_names = {};
    // Generate trajectory
    trajectory.points = generate_target_trajectory(2);
    // Whether to block until trajectory execution completes; when false, you can use
    bool is_traj_block = false;

    // Wait for trajectory execution to complete; this function wraps check_trajectory_execution_status to check trajectory execution status
    wait_for_traj_reached(trajectory.joint_groups);

    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### Set Joint Commands (set_joint_commands) {#set_joint_commands}

**Applicable Scenarios**: High-frequency joint control, such as **model inference output** (each inference step outputs one frame of joint commands), custom trajectory tracking. Issues joint commands directly to the low-level controller without extra interpolation.

```cpp title="examples/cpp/galbot_robot/src/set_joint_command_example.cpp"
#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <string>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

void print_joint_positions(const std::vector<double>& positions) {
    std::cout << "Current joint positions:" << std::endl;
    for (size_t i = 0; i < positions.size(); ++i) {
        std::cout << "  joint " << i << ": " << positions[i] << " rad" << std::endl;
    }
    std::cout << std::endl;
}

std::string execution_status_to_string(ControlStatus status) {
    switch (status) {
        case ControlStatus::SUCCESS:
            return "SUCCESS";
        case ControlStatus::TIMEOUT:
            return "TIMEOUT";
        case ControlStatus::FAULT:
            return "FAULT";
        case ControlStatus::INVALID_INPUT:
            return "INVALID_INPUT";
        case ControlStatus::INIT_FAILED:
            return "INIT_FAILED";
        case ControlStatus::IN_PROGRESS:
            return "IN_PROGRESS";
        case ControlStatus::STOPPED_UNREACHED:
            return "STOPPED_UNREACHED";
        case ControlStatus::DATA_FETCH_FAILED:
            return "DATA_FETCH_FAILED";
        case ControlStatus::PUBLISH_FAIL:
            return "PUBLISH_FAIL";
        case ControlStatus::COMM_DISCONNECTED:
            return "COMM_DISCONNECTED";
        default:
            return "UNKNOWN_STATUS";
    }
}

int main() {
    // Get object instance
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize system
    if (robot.init()) {
        std::cout << "System initialized successfully!" << std::endl;
    } else {
        std::cerr << "System initialization failed!" << std::endl;
        return -1;
    }

    // data
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));

    std::vector<std::string> joint_groups = {"head"};
    std::vector<std::string> joint_names = {};

    std::vector<JointCommand> joint_commands(2);
    joint_commands[0].position = 0.2;
    joint_commands[1].position = 0.2;
    // Set head joint angles to 0.3 0.3
    ControlStatus execution_status =
        robot.set_joint_commands(joint_commands, joint_groups, joint_names);
    if (execution_status != ControlStatus::SUCCESS) {
        std::cout << "Joint angle command sending failed" << std::endl;
    } else {
        std::cout << "Joint angle command sent successfully" << std::endl;
    }

    // , waitexecute
    std::this_thread::sleep_for(std::chrono::milliseconds(10000));

    // Query joint positions
    auto ret_positions = robot.get_joint_positions(joint_groups, {});
    print_joint_positions(ret_positions);

    // Step 2: Return to initial position —— set both head joints to 0.0 rad
    joint_commands[0].position = 0.0;
    joint_commands[1].position = 0.0;

    // Set joint commands by joint names; setting joint_names overrides joint_groups
    joint_groups = {""};
    joint_names = {"head_joint1", "head_joint2"};
    execution_status =
        robot.set_joint_commands(joint_commands, joint_groups, joint_names);
    if (execution_status != ControlStatus::SUCCESS) {
        std::cout << "Joint angle command sending failed" << std::endl;
    } else {
        std::cout << "Joint angle command sent successfully" << std::endl;
    }

    // Exit system and release SDK resources
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    std::cout << "\nProgram exited" << std::endl;
    return 0;
}
```

### Set Joint Commands in Batch Mode (set_joint_commands_batch) {#set_joint_commands_batch}

**Applicable Scenarios**: Batch issue multiple future frames of joint commands, suitable for scenarios where motion prediction models output multiple steps at once, improving control frequency and continuity.

```cpp title="examples/cpp/galbot_robot/src/set_joint_commands_batch_example.cpp"
#include <chrono>
#include <cmath>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

std::string control_status_to_string(ControlStatus status) {
  switch (status) {
    case ControlStatus::SUCCESS:
      return "SUCCESS";
    case ControlStatus::INVALID_INPUT:
      return "INVALID_INPUT";
    case ControlStatus::INIT_FAILED:
      return "INIT_FAILED";
    case ControlStatus::COMM_DISCONNECTED:
      return "COMM_DISCONNECTED";
    case ControlStatus::FAULT:
      return "FAULT";
    case ControlStatus::PUBLISH_FAIL:
      return "PUBLISH_FAIL";
    default:
      return "UNKNOWN_STATUS";
  }
}

std::vector<TrajectoryPoint> generate_batch_trajectory(int32_t joint_size, double ampl = 0.2, double cycle = 10,
                                                       int num_points = 10) {
  double amplitude = -ampl;
  double frequency = 1.0 / cycle;
  double phase = -M_PI / 2;
  double offset = amplitude;
  double dt = cycle / num_points;

  std::vector<TrajectoryPoint> trajectory_data_vec;
  trajectory_data_vec.resize(num_points);
  // Create batch trajectory points
  for (int i = 0; i < num_points; ++i) {
    double t = i * dt;
    trajectory_data_vec[i].time_from_start_second = t;
    trajectory_data_vec[i].joint_command_vec.resize(joint_size);
    // Joint command
    for (int j = 0; j < joint_size; ++j) {
      trajectory_data_vec[i].joint_command_vec[j].position =
          offset + amplitude * std::sin(2 * M_PI * frequency * t + phase);
      trajectory_data_vec[i].joint_command_vec[j].velocity =
          amplitude * 2 * M_PI * frequency * std::cos(2 * M_PI * frequency * t + phase);
      // trajectory_data_vec[i].joint_command_vec[j].acceleration = 0.0;
      // trajectory_data_vec[i].joint_command_vec[j].effort = 0.0;
    }
  }

  return trajectory_data_vec;
}

int main() {
  // Get object instance
  auto& robot = GalbotRobot::get_instance(MachineType::G1);

  // Initialize system
  if (robot.init()) {
    std::cout << "System initialized successfully!" << std::endl;
  } else {
    std::cerr << "System initialization failed!" << std::endl;
    return -1;
  }

  // Program started, waiting for data
  std::this_thread::sleep_for(std::chrono::milliseconds(2000));

  // Batch set joint commands
  Trajectory trajectory;
  // Enter joint group names to control, including ["leg", "head", "left_arm", "right_arm", "left_gripper", "right_gripper"]
  trajectory.joint_groups = {"head"};
  // Fill this field to control specific joint angles, which will override joint_groups if provided
  trajectory.joint_names = {};
  // Generate batched trajectory points (joint commands at multiple time points)
  trajectory.points = generate_batch_trajectory(2, 0.2, 10.0, 10);

  // Batch set joint commands (non-blocking, returns immediately)
  ControlStatus status = robot.set_joint_commands_batch(trajectory);
  std::cout << "Batch joint command status: " << control_status_to_string(status) << std::endl;

  if (status == ControlStatus::SUCCESS) {
    std::cout << "Batch commands submitted, executing in background (non-blocking)" << std::endl;
  } else {
    std::cerr << "Failed to submit batch commands!" << std::endl;
  }

  // Wait for a while to let the command execute
  std::this_thread::sleep_for(std::chrono::milliseconds(1000));

  // Exit system and release SDK resources
  robot.request_shutdown();
  robot.wait_for_shutdown();
  robot.destroy();

  return 0;
}
```

### Publish Raw Target Directly (PublishTarget)

**Applicable Scenarios**: Advanced users construct a `SingoriXTarget` directly and publish it through the WBCS publish channel. Suitable for high-frequency raw target streaming and one-shot dispatch of mixed joint/task targets.

```cpp title="examples/cpp/galbot_robot/src/publish_target_example.cpp"
/**
 * @file publish_target_example.cpp
 * @brief G1 PublishTarget menu example for SDK mirror SingoriXTarget.
 *
 * This example shows how to construct `SingoriXTarget` directly at the SDK layer
 * and send it to the low-level WBCS through `PublishTarget()`.
 *
 * 1. Joint-space commands are written into `target_group_trajectory_map`
 *    - Typical for head / arm style joint-space control
 *    - Each group corresponds to one `TargetGroupTrajectory`
 *    - Each trajectory point is described by `GroupCommand + JointCommand`
 *
 * 2. Chassis pose / twist style task-space commands are written into
 *    `target_task_trajectory_map`
 *    - Typical for chassis pose / chassis twist control
 *    - Each task corresponds to one `TargetTaskTrajectory`
 *    - Each trajectory point is described by `TaskCommand + FrameTriad`
 *
 * 3. One `SingoriXTarget` can contain both joint trajectory and task trajectory
 *    - This supports one-shot dispatch for whole-body / mixed control
 *
 * 4. The current SDK does not automatically switch the chassis controller when
 *    calling `PublishTarget()` / `RequestTarget()`
 *    - Therefore this example explicitly calls
 *      `switch_controller(G1ControllerName::CHASSIS_POSE_CTRL)` or
 *      `switch_controller(G1ControllerName::CHASSIS_TWIST_CTRL)` before
 *      chassis pose / twist / mixed scenes
 *
 * 5. For the base twist scene, this example automatically sends a zero-twist
 *    target after the configured duration to stop the chassis.
 */

#include <chrono>
#include <cstdint>
#include <iostream>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

namespace {

constexpr const char* kChassisTaskName = "chassis";
constexpr const char* kChassisSubtaskPose = "chassis_pose";
constexpr const char* kChassisSubtaskTwist = "chassis_twist";

int64_t now_ns() {
  return std::chrono::duration_cast<std::chrono::nanoseconds>(
             std::chrono::system_clock::now().time_since_epoch())
      .count();
}

const char* to_string(ControlStatus status) {
  switch (status) {
    case ControlStatus::SUCCESS:
      return "SUCCESS";
    case ControlStatus::TIMEOUT:
      return "TIMEOUT";
    case ControlStatus::FAULT:
      return "FAULT";
    case ControlStatus::INVALID_INPUT:
      return "INVALID_INPUT";
    case ControlStatus::INIT_FAILED:
      return "INIT_FAILED";
    case ControlStatus::IN_PROGRESS:
      return "IN_PROGRESS";
    case ControlStatus::STOPPED_UNREACHED:
      return "STOPPED_UNREACHED";
    case ControlStatus::DATA_FETCH_FAILED:
      return "DATA_FETCH_FAILED";
    case ControlStatus::PUBLISH_FAIL:
      return "PUBLISH_FAIL";
    case ControlStatus::COMM_DISCONNECTED:
      return "COMM_DISCONNECTED";
    default:
      return "UNKNOWN_STATUS";
  }
}

Quaternion yaw_to_quaternion(double yaw) {
  Quaternion q;
  q.z = std::sin(yaw * 0.5);
  q.w = std::cos(yaw * 0.5);
  return q;
}

SingoriXTarget make_empty_target() {
  SingoriXTarget target;
  target.header.timestamp_ns = now_ns();
  target.header.frame_id = "base_link";
  return target;
}

TargetConfig make_group_target_config() {
  TargetConfig config;
  config.target_data = TARGET_DATA_DEFAULT;
  config.target_type = TARGET_TYPE_PROVERRIDE;
  config.target_sampling = TargetSampling::TARGET_SAMPLING_DEFAULT;
  config.target_priority = 1;
  return config;
}

TargetConfig make_pose_target_config() {
  TargetConfig config;
  config.target_data = TARGET_DATA_FRAME_POSE;
  config.target_type = TARGET_TYPE_PROVERRIDE;
  config.target_sampling = TargetSampling::TARGET_SAMPLING_LINEAR_INTERPOLATE;
  config.target_priority = 1;
  return config;
}

TargetConfig make_twist_target_config() {
  TargetConfig config;
  config.target_data = TARGET_DATA_FRAME_TWIST;
  config.target_type = TARGET_TYPE_OVERRIDE;
  config.target_sampling = TargetSampling::TARGET_SAMPLING_DIRECT_PASS;
  config.target_priority = 1;
  return config;
}

SingoriXTarget build_joint_target(const std::string& group_name,
                                  const std::vector<std::string>& joint_names,
                                  const std::vector<double>& positions,
                                  double time_from_start_s) {
  SingoriXTarget target = make_empty_target();
  auto& group_traj = target.target_group_trajectory_map[group_name];
  group_traj.target_config = make_group_target_config();
  group_traj.joint_names = joint_names;

  GroupCommand command;
  command.time_from_start_s = time_from_start_s;
  command.joint_commands.resize(joint_names.size());
  for (size_t i = 0; i < joint_names.size(); ++i) {
    command.joint_commands[i].position = positions[i];
    command.joint_commands[i].velocity = 0.0;
    command.joint_commands[i].acceleration = 0.0;
    command.joint_commands[i].effort = 0.0;
  }
  group_traj.group_commands.push_back(command);
  return target;
}

SingoriXTarget build_chassis_pose_target(double x,
                                         double y,
                                         double yaw,
                                         double time_from_start_s,
                                         const std::string& frame_id = "odom",
                                         const std::string& reference_frame_id = "odom") {
  SingoriXTarget target = make_empty_target();
  auto& task_traj = target.target_task_trajectory_map[kChassisTaskName];
  task_traj.target_config = make_pose_target_config();
  task_traj.group_names = {G1JointGroup::CHASSIS};
  task_traj.subtask_names = {kChassisSubtaskPose};

  TaskCommand command;
  command.time_from_start_s = time_from_start_s;

  FrameTriad triad;
  triad.header.timestamp_ns = now_ns();
  triad.header.frame_id = frame_id;
  triad.body_frame_id = "base_link";
  triad.reference_frame_id = reference_frame_id;
  triad.pose = Pose();
  triad.pose->position.x = x;
  triad.pose->position.y = y;
  triad.pose->position.z = 0.0;
  triad.pose->orientation = yaw_to_quaternion(yaw);
  command.subtask_commands.push_back(triad);

  task_traj.task_commands.push_back(command);
  return target;
}

SingoriXTarget build_chassis_twist_target(double vx,
                                          double vy,
                                          double wz,
                                          double time_from_start_s) {
  SingoriXTarget target = make_empty_target();
  auto& task_traj = target.target_task_trajectory_map[kChassisTaskName];
  task_traj.target_config = make_twist_target_config();
  task_traj.group_names = {G1JointGroup::CHASSIS};
  task_traj.subtask_names = {kChassisSubtaskTwist};

  TaskCommand command;
  command.time_from_start_s = time_from_start_s;

  FrameTriad triad;
  triad.header.timestamp_ns = now_ns();
  triad.header.frame_id = "base_link";
  triad.body_frame_id = "base_link";
  triad.reference_frame_id = "base_link";
  triad.twist = Twist();
  triad.twist->linear = Vector3{vx, vy, 0.0};
  triad.twist->angular = Vector3{0.0, 0.0, wz};
  command.subtask_commands.push_back(triad);

  task_traj.task_commands.push_back(command);
  return target;
}

SingoriXTarget build_stop_twist_target() {
  return build_chassis_twist_target(0.0, 0.0, 0.0, 0.1);
}

SingoriXTarget merge_targets(const std::vector<SingoriXTarget>& targets) {
  SingoriXTarget merged = make_empty_target();
  for (const auto& target : targets) {
    for (const auto& [group_name, group_traj] : target.target_group_trajectory_map) {
      merged.target_group_trajectory_map[group_name] = group_traj;
    }
    for (const auto& [task_name, task_traj] : target.target_task_trajectory_map) {
      merged.target_task_trajectory_map[task_name] = task_traj;
    }
  }
  return merged;
}

void print_menu() {
  std::cout << "\nAvailable commands:\n"
            << "  joint        - publish a joint-only head target\n"
            << "  base_pose    - publish a chassis pose target\n"
            << "  base_twist   - publish a chassis twist target with auto stop\n"
            << "  mixed_pose   - publish head + left_arm + chassis pose in one target\n"
            << "  mixed_twist  - publish head + left_arm + chassis twist in one target\n"
            << "  quit         - exit example\n"
            << std::endl;
}

ControlStatus ensure_controller(GalbotRobot& robot, const std::string& controller_name) {
  const auto status = robot.switch_controller(controller_name);
  std::cout << "switch_controller(" << controller_name << "): " << to_string(status) << std::endl;
  return status;
}

void print_result(const std::string& scene_name, ControlStatus status) {
  std::cout << scene_name << " PublishTarget status: " << to_string(status) << std::endl;
}

ControlStatus run_twist_scene(GalbotRobot& robot,
                              const std::string& scene_name,
                              const SingoriXTarget& target,
                              double twist_duration_s) {
  std::cout << scene_name << ": start moving for " << twist_duration_s << " seconds" << std::endl;
  const auto motion_status = robot.PublishTarget(target);
  print_result(scene_name, motion_status);
  if (motion_status != ControlStatus::SUCCESS) {
    return motion_status;
  }

  std::this_thread::sleep_for(std::chrono::duration<double>(twist_duration_s));
  std::cout << scene_name << ": send stop twist target" << std::endl;
  const auto stop_status = robot.PublishTarget(build_stop_twist_target());
  std::cout << scene_name << " stop status: " << to_string(stop_status) << std::endl;
  return stop_status;
}

}  // namespace

int main() {
  auto& robot = GalbotRobot::get_instance(MachineType::G1);
  if (!robot.init()) {
    std::cerr << "robot init failed" << std::endl;
    return -1;
  }

  std::this_thread::sleep_for(std::chrono::seconds(2));

  const auto head_joint_names = robot.get_joint_names(true, {G1JointGroup::HEAD});
  const auto left_arm_joint_names = robot.get_joint_names(true, {G1JointGroup::LEFT_ARM});
  if (head_joint_names.empty() || left_arm_joint_names.empty()) {
    std::cerr << "failed to fetch active head/left_arm joints" << std::endl;
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();
    return -1;
  }

  const std::vector<std::string> head_single_joint = {head_joint_names.front()};
  const std::vector<std::string> arm_single_joint = {left_arm_joint_names.front()};
  constexpr double kJointTimeS = 3.0;
  constexpr double kPoseTimeS = 4.0;
  constexpr double kTwistCommandTimeS = 0.2;
  constexpr double kTwistDurationS = 2.0;

  print_menu();

  std::string command;
  while (true) {
    std::cout << "Enter command: ";
    if (!(std::cin >> command)) {
      break;
    }
    if (command == "quit") {
      break;
    }

    if (command == "joint") {
      const auto target = build_joint_target(G1JointGroup::HEAD, head_single_joint, {0.2}, kJointTimeS);
      print_result("joint", robot.PublishTarget(target));
      continue;
    }

    if (command == "base_pose") {
      if (ensure_controller(robot, G1ControllerName::CHASSIS_POSE_CTRL) != ControlStatus::SUCCESS) {
        continue;
      }
      const auto target = build_chassis_pose_target(0.2, 0.0, 0.0, kPoseTimeS);
      print_result("base_pose", robot.PublishTarget(target));
      continue;
    }

    if (command == "base_twist") {
      if (ensure_controller(robot, G1ControllerName::CHASSIS_TWIST_CTRL) != ControlStatus::SUCCESS) {
        continue;
      }
      const auto target = build_chassis_twist_target(0.05, 0.0, 0.0, kTwistCommandTimeS);
      run_twist_scene(robot, "base_twist", target, kTwistDurationS);
      continue;
    }

    if (command == "mixed_pose") {
      if (ensure_controller(robot, G1ControllerName::CHASSIS_POSE_CTRL) != ControlStatus::SUCCESS) {
        continue;
      }
      const auto target = merge_targets({
          build_joint_target(G1JointGroup::HEAD, head_single_joint, {0.15}, kJointTimeS),
          build_chassis_pose_target(0.1, 0.0, 0.0, kPoseTimeS),
      });
      print_result("mixed_pose", robot.PublishTarget(target));
      continue;
    }

    if (command == "mixed_twist") {
      if (ensure_controller(robot, G1ControllerName::CHASSIS_TWIST_CTRL) != ControlStatus::SUCCESS) {
        continue;
      }
      const auto target = merge_targets({
          build_joint_target(G1JointGroup::HEAD, head_single_joint, {-0.15}, kJointTimeS),
          build_chassis_twist_target(0.05, 0.0, 0.0, kTwistCommandTimeS),
      });
      run_twist_scene(robot, "mixed_twist", target, kTwistDurationS);
      continue;
    }

    std::cout << "Unknown command: " << command << std::endl;
    print_menu();
  }

  robot.request_shutdown();
  robot.wait_for_shutdown();
  robot.destroy();
  return 0;
}
```

### Request Raw Target Directly (RequestTarget)

**Applicable Scenarios**: Advanced users construct a `SingoriXTarget` directly and send it through the WBCS request channel. Suitable when the caller needs the service-side error response for a raw target dispatch.

```cpp title="examples/cpp/galbot_robot/src/request_target_example.cpp"
/**
 * @file request_target_example.cpp
 * @brief G1 RequestTarget menu example for SDK mirror SingoriXTarget.
 *
 * This example shows how to construct `SingoriXTarget` directly at the SDK layer
 * and send it to the low-level WBCS through `RequestTarget()`.
 *
 * 1. Joint-space commands are written into `target_group_trajectory_map`
 *    - Typical for head / arm style joint-space control
 *    - Each group corresponds to one `TargetGroupTrajectory`
 *    - Each trajectory point is described by `GroupCommand + JointCommand`
 *
 * 2. Chassis pose / twist style task-space commands are written into
 *    `target_task_trajectory_map`
 *    - Typical for chassis pose / chassis twist control
 *    - Each task corresponds to one `TargetTaskTrajectory`
 *    - Each trajectory point is described by `TaskCommand + FrameTriad`
 *
 * 3. One `SingoriXTarget` can contain both joint trajectory and task trajectory
 *    - This supports one-shot dispatch for whole-body / mixed control
 *
 * 4. The current SDK does not automatically switch the chassis controller when
 *    calling `PublishTarget()` / `RequestTarget()`
 *    - Therefore this example explicitly calls
 *      `switch_controller(G1ControllerName::CHASSIS_POSE_CTRL)` or
 *      `switch_controller(G1ControllerName::CHASSIS_TWIST_CTRL)` before
 *      chassis pose / twist / mixed scenes
 *
 * 5. For the base twist scene, this example automatically sends a zero-twist
 *    target after the configured duration to stop the chassis.
 */

#include <chrono>
#include <cstdint>
#include <iostream>
#include <memory>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

namespace {

constexpr const char* kChassisTaskName = "chassis";
constexpr const char* kChassisSubtaskPose = "chassis_pose";
constexpr const char* kChassisSubtaskTwist = "chassis_twist";

int64_t now_ns() {
  return std::chrono::duration_cast<std::chrono::nanoseconds>(
             std::chrono::system_clock::now().time_since_epoch())
      .count();
}

Quaternion yaw_to_quaternion(double yaw) {
  Quaternion q;
  q.z = std::sin(yaw * 0.5);
  q.w = std::cos(yaw * 0.5);
  return q;
}

SingoriXTarget make_empty_target() {
  SingoriXTarget target;
  target.header.timestamp_ns = now_ns();
  target.header.frame_id = "base_link";
  return target;
}

TargetConfig make_group_target_config() {
  TargetConfig config;
  config.target_data = TARGET_DATA_DEFAULT;
  config.target_type = TARGET_TYPE_PROVERRIDE;
  config.target_sampling = TargetSampling::TARGET_SAMPLING_DEFAULT;
  config.target_priority = 1;
  return config;
}

TargetConfig make_pose_target_config() {
  TargetConfig config;
  config.target_data = TARGET_DATA_FRAME_POSE;
  config.target_type = TARGET_TYPE_PROVERRIDE;
  config.target_sampling = TargetSampling::TARGET_SAMPLING_LINEAR_INTERPOLATE;
  config.target_priority = 1;
  return config;
}

TargetConfig make_twist_target_config() {
  TargetConfig config;
  config.target_data = TARGET_DATA_FRAME_TWIST;
  config.target_type = TARGET_TYPE_OVERRIDE;
  config.target_sampling = TargetSampling::TARGET_SAMPLING_DIRECT_PASS;
  config.target_priority = 1;
  return config;
}

SingoriXTarget build_joint_target(const std::string& group_name,
                                  const std::vector<std::string>& joint_names,
                                  const std::vector<double>& positions,
                                  double time_from_start_s) {
  SingoriXTarget target = make_empty_target();
  auto& group_traj = target.target_group_trajectory_map[group_name];
  group_traj.target_config = make_group_target_config();
  group_traj.joint_names = joint_names;

  GroupCommand command;
  command.time_from_start_s = time_from_start_s;
  command.joint_commands.resize(joint_names.size());
  for (size_t i = 0; i < joint_names.size(); ++i) {
    command.joint_commands[i].position = positions[i];
    command.joint_commands[i].velocity = 0.0;
    command.joint_commands[i].acceleration = 0.0;
    command.joint_commands[i].effort = 0.0;
  }
  group_traj.group_commands.push_back(command);
  return target;
}

SingoriXTarget build_chassis_pose_target(double x,
                                         double y,
                                         double yaw,
                                         double time_from_start_s,
                                         const std::string& frame_id = "odom",
                                         const std::string& reference_frame_id = "odom") {
  SingoriXTarget target = make_empty_target();
  auto& task_traj = target.target_task_trajectory_map[kChassisTaskName];
  task_traj.target_config = make_pose_target_config();
  task_traj.group_names = {G1JointGroup::CHASSIS};
  task_traj.subtask_names = {kChassisSubtaskPose};

  TaskCommand command;
  command.time_from_start_s = time_from_start_s;

  FrameTriad triad;
  triad.header.timestamp_ns = now_ns();
  triad.header.frame_id = frame_id;
  triad.body_frame_id = "base_link";
  triad.reference_frame_id = reference_frame_id;
  triad.pose = Pose();
  triad.pose->position.x = x;
  triad.pose->position.y = y;
  triad.pose->position.z = 0.0;
  triad.pose->orientation = yaw_to_quaternion(yaw);
  command.subtask_commands.push_back(triad);

  task_traj.task_commands.push_back(command);
  return target;
}

SingoriXTarget build_chassis_twist_target(double vx,
                                          double vy,
                                          double wz,
                                          double time_from_start_s) {
  SingoriXTarget target = make_empty_target();
  auto& task_traj = target.target_task_trajectory_map[kChassisTaskName];
  task_traj.target_config = make_twist_target_config();
  task_traj.group_names = {G1JointGroup::CHASSIS};
  task_traj.subtask_names = {kChassisSubtaskTwist};

  TaskCommand command;
  command.time_from_start_s = time_from_start_s;

  FrameTriad triad;
  triad.header.timestamp_ns = now_ns();
  triad.header.frame_id = "base_link";
  triad.body_frame_id = "base_link";
  triad.reference_frame_id = "base_link";
  triad.twist = Twist();
  triad.twist->linear = Vector3{vx, vy, 0.0};
  triad.twist->angular = Vector3{0.0, 0.0, wz};
  command.subtask_commands.push_back(triad);

  task_traj.task_commands.push_back(command);
  return target;
}

SingoriXTarget build_stop_twist_target() {
  return build_chassis_twist_target(0.0, 0.0, 0.0, 0.1);
}

SingoriXTarget merge_targets(const std::vector<SingoriXTarget>& targets) {
  SingoriXTarget merged = make_empty_target();
  for (const auto& target : targets) {
    for (const auto& [group_name, group_traj] : target.target_group_trajectory_map) {
      merged.target_group_trajectory_map[group_name] = group_traj;
    }
    for (const auto& [task_name, task_traj] : target.target_task_trajectory_map) {
      merged.target_task_trajectory_map[task_name] = task_traj;
    }
  }
  return merged;
}

void print_menu() {
  std::cout << "\nAvailable commands:\n"
            << "  joint        - request a joint-only head target\n"
            << "  base_pose    - request a chassis pose target\n"
            << "  base_twist   - request a chassis twist target with auto stop\n"
            << "  mixed_pose   - request head + left_arm + chassis pose in one target\n"
            << "  mixed_twist  - request head + left_arm + chassis twist in one target\n"
            << "  quit         - exit example\n"
            << std::endl;
}

void print_error_info(const std::string& scene_name, const std::shared_ptr<ErrorInfo>& error_info) {
  if (error_info == nullptr) {
    std::cout << scene_name << ": RequestTarget returned nullptr" << std::endl;
    return;
  }
  if (error_info->error_vec.empty()) {
    std::cout << scene_name << ": RequestTarget success, service returned no errors" << std::endl;
    return;
  }

  std::cout << scene_name << ": RequestTarget returned " << error_info->error_vec.size() << " error entries:"
            << std::endl;
  for (const auto& error : error_info->error_vec) {
    std::cout << "  component=" << error.commpent << ", code=" << error.error_code
              << ", description=" << error.description << std::endl;
  }
}

ControlStatus ensure_controller(GalbotRobot& robot, const std::string& controller_name) {
  const auto status = robot.switch_controller(controller_name);
  std::cout << "switch_controller(" << controller_name << "): ";
  std::cout << (status == ControlStatus::SUCCESS ? "SUCCESS" : "FAILED") << std::endl;
  return status;
}

void run_twist_scene(GalbotRobot& robot,
                     const std::string& scene_name,
                     const SingoriXTarget& target,
                     double twist_duration_s) {
  std::cout << scene_name << ": start moving for " << twist_duration_s << " seconds" << std::endl;
  print_error_info(scene_name, robot.RequestTarget(target));
  std::this_thread::sleep_for(std::chrono::duration<double>(twist_duration_s));
  std::cout << scene_name << ": send stop twist target" << std::endl;
  print_error_info(scene_name + "_stop", robot.RequestTarget(build_stop_twist_target()));
}

}  // namespace

int main() {
  auto& robot = GalbotRobot::get_instance(MachineType::G1);
  if (!robot.init()) {
    std::cerr << "robot init failed" << std::endl;
    return -1;
  }

  std::this_thread::sleep_for(std::chrono::seconds(2));

  const auto head_joint_names = robot.get_joint_names(true, {G1JointGroup::HEAD});
  if (head_joint_names.empty()) {
    std::cerr << "failed to fetch active head joints" << std::endl;
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();
    return -1;
  }

  const std::vector<std::string> head_single_joint = {head_joint_names.front()};
  constexpr double kJointTimeS = 3.0;
  constexpr double kPoseTimeS = 4.0;
  constexpr double kTwistCommandTimeS = 0.2;
  constexpr double kTwistDurationS = 2.0;

  print_menu();

  std::string command;
  while (true) {
    std::cout << "Enter command: ";
    if (!(std::cin >> command)) {
      break;
    }
    if (command == "quit") {
      break;
    }

    if (command == "joint") {
      const auto target = build_joint_target(G1JointGroup::HEAD, head_single_joint, {0.2}, kJointTimeS);
      print_error_info("joint", robot.RequestTarget(target));
      continue;
    }

    if (command == "base_pose") {
      if (ensure_controller(robot, G1ControllerName::CHASSIS_POSE_CTRL) != ControlStatus::SUCCESS) {
        continue;
      }
      const auto target = build_chassis_pose_target(0.2, 0.0, 0.0, kPoseTimeS);
      print_error_info("base_pose", robot.RequestTarget(target));
      continue;
    }

    if (command == "base_twist") {
      if (ensure_controller(robot, G1ControllerName::CHASSIS_TWIST_CTRL) != ControlStatus::SUCCESS) {
        continue;
      }
      const auto target = build_chassis_twist_target(0.05, 0.0, 0.0, kTwistCommandTimeS);
      run_twist_scene(robot, "base_twist", target, kTwistDurationS);
      continue;
    }

    if (command == "mixed_pose") {
      if (ensure_controller(robot, G1ControllerName::CHASSIS_POSE_CTRL) != ControlStatus::SUCCESS) {
        continue;
      }
      const auto target = merge_targets({
          build_joint_target(G1JointGroup::HEAD, head_single_joint, {0.15}, kJointTimeS),
          build_chassis_pose_target(0.1, 0.0, 0.0, kPoseTimeS),
      });
      print_error_info("mixed_pose", robot.RequestTarget(target));
      continue;
    }

    if (command == "mixed_twist") {
      if (ensure_controller(robot, G1ControllerName::CHASSIS_TWIST_CTRL) != ControlStatus::SUCCESS) {
        continue;
      }
      const auto target = merge_targets({
          build_joint_target(G1JointGroup::HEAD, head_single_joint, {-0.15}, kJointTimeS),
          build_chassis_twist_target(0.05, 0.0, 0.0, kTwistCommandTimeS),
      });
      run_twist_scene(robot, "mixed_twist", target, kTwistDurationS);
      continue;
    }

    std::cout << "Unknown command: " << command << std::endl;
    print_menu();
  }

  robot.request_shutdown();
  robot.wait_for_shutdown();
  robot.destroy();
  return 0;
}
```

### Stop Base Motion (stop_base)

**Applicable Scenarios**: Immediately stop all motion of the base, used for emergency stop.

```cpp title="examples/cpp/galbot_robot/src/stop_base_example.cpp"
#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <string>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

int main() {
    // Get object instance
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize system
    if (robot.init()) {
        std::cout << "System initialized successfully!" << std::endl;
    } else {
        std::cerr << "System initialization failed!" << std::endl;
        return -1;
    }

    // Program started, waiting for data
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));

    // Stop chassis motion
    while (true) {
        ControlStatus status = robot.stop_base();
        if (status == ControlStatus::SUCCESS) {
            std::cout << "Chassis motion has been stopped successfully!" << std::endl;
            break;
        } else {
            std::cerr << "Chassis stop motion failed, retrying..." << std::endl;
        }
    }

    // Exit system and release SDK resources
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### Set Base Velocity (set_base_velocity)

**Applicable Scenarios**: Control linear and angular velocity of the mobile base, used for navigation or remote control.

```cpp title="examples/cpp/galbot_robot/src/set_base_velocity_example.cpp"
#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <string>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

int main() {
    // Get object instance
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize system
    if (robot.init()) {
        std::cout << "System initialized successfully!" << std::endl;
    } else {
        std::cerr << "System initialization failed!" << std::endl;
        return -1;
    }

    // Program started, waiting for data
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));

    // Please confirm the surrounding environment before chassis testing
    // Set chassis speed, linear_velocity first two fields are x and y velocities, angular_velocity third field is z rotation speed
    std::array<double, 3> linear_velocity = {0.05, 0.0, 0.0};    // 0.05 m/s
    std::array<double, 3> angular_velocity = {0.0, 0.0, 0.1};    // 0.1 rad/s
    double duration_s = 2.0;  // Automatically stop after 2 seconds

    if (robot.set_base_velocity(linear_velocity, angular_velocity, duration_s) == ControlStatus::SUCCESS) {
        std::cout << "Chassis speed set successfully; will stop in " << duration_s << " seconds then auto-stop." << std::endl;
    } else {
        std::cerr << "Set chassis speed failed." << std::endl;
    }

    // Wait for auto-stop to complete (with small buffer time)
    std::this_thread::sleep_for(std::chrono::duration<double>(duration_s + 0.5));

    // Exit system and release SDK resources
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### Get Joint States (get_joint_states)

**Applicable Scenarios**: Get complete state information of all joints, including position, velocity, current, etc. Suitable for algorithms requiring full joint information (such as dynamics calculation, state estimation).

```cpp title="examples/cpp/galbot_robot/src/get_joint_states_example.cpp"
#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <string>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

void print_joint_states(const std::vector<JointState>& joint_states) {
    for (const auto& states : joint_states) {
        std::cout << "--- Joint State ---" << std::endl;
        std::cout << "Position:     " << states.position     << " rad" << std::endl;
        std::cout << "Velocity:     " << states.velocity     << " rad/s" << std::endl;
        std::cout << "Acceleration: " << states.acceleration << " rad/s^2" << std::endl;
        std::cout << "Effort:       " << states.effort       << " Nm" << std::endl;
        std::cout << "Current:      " << states.current      << " A" << std::endl;
        std::cout << "------------------" << std::endl;
    }
}

int main() {
    // Get object instance
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize system
    if (robot.init()) {
        std::cout << "System initialized successfully!" << std::endl;
    } else {
        std::cerr << "System initialization failed!" << std::endl;
        return -1;
    }

    // Program started, waiting for data
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));

    // Get joint states by joint group names; returns all joints if empty
    std::vector<std::string> joint_groups = {"left_arm"};
    auto ret_states = robot.get_joint_states(joint_groups, {});
    print_joint_states(ret_states);

    // Get specified joint states; if provided, overrides joint group input
    std::vector<std::string> joint_names = {"left_arm_joint1", "left_arm_joint2"};
    ret_states = robot.get_joint_states(joint_groups, joint_names);
    print_joint_states(ret_states);

    // Exit system and release SDK resources
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### Get Joint Positions (get_joint_positions)

**Applicable Scenarios**: Only get current joint positions. Use this interface when you only need joint position information, it's more lightweight than `get_joint_states`.

```cpp title="examples/cpp/galbot_robot/src/get_joint_positions_example.cpp"
#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <string>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

void print_joint_positions(const std::vector<double>& positions) {
    for (const auto& pos : positions) {
        std::cout << "joint positions is " << pos << std::endl;
    }
    std::cout << std::endl;
}

int main() {
    // Get object instance
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize system
    if (robot.init()) {
        std::cout << "System initialized successfully!" << std::endl;
    } else {
        std::cerr << "System initialization failed!" << std::endl;
        return -1;
    }

    // Program started, waiting for data
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));

    // Get joint positions by joint group names; returns all joints if empty
    std::vector<std::string> joint_groups = {"left_arm"};
    auto ret_positions = robot.get_joint_positions(joint_groups, {});
    std::cout << "Left arm joint positions:" << std::endl;
    print_joint_positions(ret_positions);

    // Get specified joint positions; if provided, overrides joint group input
    std::vector<std::string> joint_names = {"left_arm_joint1", "left_arm_joint2"};
    ret_positions = robot.get_joint_positions({joint_groups}, joint_names);
    std::cout << "Positions of left arm joint1 and joint2:" << std::endl;
    print_joint_positions(ret_positions);

    // Exit system and release SDK resources
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### Get Joint Names (get_joint_names)

**Applicable Scenarios**: Get a list of all joint names of the robot, used for iterating through joints or generating configuration files.

```cpp title="examples/cpp/galbot_robot/src/get_joint_names_example.cpp"
#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <string>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

int main() {
    // Get object instance
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize system
    if (robot.init()) {
        std::cout << "System initialized successfully!" << std::endl;
    } else {
        std::cerr << "System initialization failed!" << std::endl;
        return -1;
    }

    // Program started, waiting for data
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));

    // Get specified joint names; joint groups include ["leg", "head", "left_arm", "right_arm"]
    std::vector<std::string> joint_groups = {"head"};
    bool only_active_joint = true;  // Get active joints
    auto head_joint_names_vec =
        robot.get_joint_names(only_active_joint, joint_groups);
    std::cout << "Head joint names:" << std::endl;
    for (size_t i = 0; i < head_joint_names_vec.size(); ++i) {
        std::cout << i << ": " << head_joint_names_vec[i] << std::endl;
    }

    // Passing an empty array returns all joint group information by default
    std::vector<std::string> null_vec = {};
    auto all_joint_names_vec =
        robot.get_joint_names(only_active_joint, null_vec);
    std::cout << "All joint names:" << std::endl;
    for (size_t i = 0; i < all_joint_names_vec.size(); ++i) {
        std::cout << i << ": " << all_joint_names_vec[i] << std::endl;
    }

    // Exit system and release SDK resources
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### Get Gripper State (get_gripper_state)

**Applicable Scenarios**: Get current gripper position and status, determine if gripper is open or closed.

```cpp title="examples/cpp/galbot_robot/src/get_gripper_state_example.cpp"
#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <string>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

void print_gripper_state(std::shared_ptr<GripperState> gripper_state) {
    std::cout << "Timestamp (ns): " << gripper_state->timestamp_ns << std::endl;

    std::cout << " width "  << gripper_state->width << " velocity " << gripper_state->velocity
                << " effort " << gripper_state->effort << " is moving "
                << gripper_state->is_moving << std::endl;
}

int main() {
    // Get object instance
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize system
    if (robot.init()) {
        std::cout << "System initialized successfully!" << std::endl;
    } else {
        std::cerr << "System initialization failed!" << std::endl;
        return -1;
    }

    // Program started, waiting for data
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));

    // Get gripper state
    auto gripper_state_ptr = robot.get_gripper_state("left_gripper");

    if (gripper_state_ptr == nullptr) {
        std::cerr << "get gripper state error" << std::endl;
    } else {
        std::cout << "Left gripper state:" << std::endl;
        print_gripper_state(gripper_state_ptr);
    }

    // Exit system and release SDK resources
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### Get Suction Cup State (get_suction_cup_state)

**Applicable Scenarios**: Get whether the suction cup is currently suctioned and whether it successfully detected an object.

```cpp title="examples/cpp/galbot_robot/src/get_suction_cup_state_example.cpp"
#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <string>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

void print_suction_cup_state(std::shared_ptr<SuctionCupState> suction_cup_state) {
    std::cout << "Timestamp (ns): " << suction_cup_state->timestamp_ns << std::endl;
    std::cout << "Activation: " << suction_cup_state->activation << std::endl;
    std::cout << "Pressure: " << suction_cup_state->pressure << " Pa" << std::endl;
    std::cout << "Action State: " << int(suction_cup_state->action_state) << std::endl;
}

int main() {
    // Get object instance
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize system
    if (robot.init()) {
        std::cout << "System initialized successfully!" << std::endl;
    } else {
        std::cerr << "System initialization failed!" << std::endl;
        return -1;
    }

    // Program started, waiting for data
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));

    // Get suction cup state
    auto suction_cup_state_ptr = robot.get_suction_cup_state("right_suction_cup");

    if (suction_cup_state_ptr == nullptr) {
        std::cerr << "get suction cup state error" << std::endl;
    } else {
        std::cout << "Right suction cup status:" << std::endl;
        print_suction_cup_state(suction_cup_state_ptr);
    }

    // Exit system and release SDK resources
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### Get Transform (get_transform)

**Applicable Scenarios**: Get the transformation (pose) between two coordinate frames, used in robotic arm grasping, visual localization and other scenarios.

```cpp title="examples/cpp/galbot_robot/src/get_transform_example.cpp"
#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <string>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

void print_pose_vec(const std::vector<double> &pose_vec) {
    // Output pose_vec
    std::cout << "pose_vec = [";
    for (size_t i = 0; i < pose_vec.size(); ++i) {
        std::cout << pose_vec[i];
        if (i + 1 < pose_vec.size())
        std::cout << ", ";
    }
    std::cout << "]" << std::endl;
}

int main() {
    // Get object instance
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize system
    if (robot.init()) {
        std::cout << "System initialized successfully!" << std::endl;
    } else {
        std::cerr << "System initialization failed!" << std::endl;
        return -1;
    }

    // Program started, waiting for data
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));

    // Get coordinate transform
    std::pair<std::vector<double>, int64_t> tf_ret = robot.get_transform("left_arm_link1", "left_arm_link7", 0);

    if (tf_ret.first.empty()) {
        std::cout << "get_transform error" << std::endl;
    } else {
        std::cout << "tf_timestamp_ns: " << tf_ret.second << std::endl;
        print_pose_vec(tf_ret.first);
    }

    // Exit system and release SDK resources
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### Get IMU Data (get_imu_data)

**Applicable Scenarios**: Get acceleration, angular velocity and pose information from the base IMU, used for state estimation and motion analysis.

```cpp title="examples/cpp/galbot_robot/src/get_imu_data_example.cpp"
#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <string>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

void print_imu_data(const std::shared_ptr<ImuData>& imu_data) {
    if (!imu_data) {
        std::cerr << "IMU data is empty" << std::endl;
        return;
    }

    std::cout << "Timestamp (ns): " << imu_data->timestamp_ns << std::endl;

    std::cout << "Accelerometer: "
              << "x=" << imu_data->accel.x << ", "
              << "y=" << imu_data->accel.y << ", "
              << "z=" << imu_data->accel.z << std::endl;

    std::cout << "Gyroscope: "
              << "x=" << imu_data->gyro.x << ", "
              << "y=" << imu_data->gyro.y << ", "
              << "z=" << imu_data->gyro.z << std::endl;

    std::cout << "Magnetometer: "
              << "x=" << imu_data->magnet.x << ", "
              << "y=" << imu_data->magnet.y << ", "
              << "z=" << imu_data->magnet.z << std::endl;
}

int main() {
    // Get object instance
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize system
    if (robot.init()) {
        std::cout << "System initialized successfully!" << std::endl;
    } else {
        std::cerr << "System initialization failed!" << std::endl;
        return -1;
    }

    // Program started, waiting for data
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));

    // Get IMU data
    std::shared_ptr<ImuData> imu_data = robot.get_imu_data(SensorType::TORSO_IMU);
    if (imu_data) {
        std::cout << "IMU data retrieved successfully!" << std::endl;
        print_imu_data(imu_data);
    } else {
        std::cerr << "Failed to get IMU data!" << std::endl;
    }

    // Exit system and release SDK resources
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```
### Get Battery Information (get_bms_information)

**Applicable Scenarios**: Get battery voltage, charge level and other information, used for low battery detection and status monitoring.

```cpp title="examples/cpp/galbot_robot/src/get_bms_information_example.cpp"
#include <iostream>
#include <chrono>
#include <thread>
#include <string>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

void print_bms_information(const std::shared_ptr<BmsInfo>& bms_info) {
    if (!bms_info) {
        std::cerr << "BMS info is empty" << std::endl;
        return;
    }

    std::cout << "Voltage (V): " << bms_info->voltage << std::endl;
    std::cout << "Current (A): " << bms_info->current << std::endl;
    std::cout << "Battery level (%): " << bms_info->battery_level << std::endl;
    std::cout << "Temperature (C): " << bms_info->temperature << std::endl;
    std::cout << "Charging status: " << std::boolalpha << bms_info->charging_status
              << std::noboolalpha << std::endl;
    std::cout << "Health status: " << std::boolalpha << bms_info->health_status
              << std::noboolalpha << std::endl;
    std::cout << "Capacity (Ah): " << bms_info->capacity << std::endl;
}

int main() {
    // Get object instance
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize system
    if (robot.init()) {
        std::cout << "System initialized successfully!" << std::endl;
    } else {
        std::cerr << "System initialization failed!" << std::endl;
        return -1;
    }

    // Program started, waiting for data
    std::this_thread::sleep_for(std::chrono::milliseconds(3000));

    // Get BMS information
    auto bms_info = robot.get_bms_information();
    if (bms_info) {
        std::cout << "BMS info retrieved successfully!" << std::endl;
        print_bms_information(bms_info);
    } else {
        std::cerr << "Failed to get BMS info!" << std::endl;
    }

    // Exit system and release SDK resources
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### Get Device Information (get_device_information)

**Applicable Scenarios**: Get device information such as hardware version and firmware version, used for debugging and compatibility checking.

```cpp title="examples/cpp/galbot_robot/src/get_device_information_example.cpp"
#include <chrono>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

void print_device_info(const std::shared_ptr<DeviceInfo>& device_info) {
  if (!device_info) {
    std::cerr << "Device information is empty" << std::endl;
    return;
  }

  std::cout << "Device information:" << std::endl;
  std::cout << "  Model: " << (device_info->model.empty() ? "N/A" : device_info->model) << std::endl;
  std::cout << "  Serial number: " << (device_info->serial_number.empty() ? "N/A" : device_info->serial_number) << std::endl;
  std::cout << "  Firmware version: " << (device_info->firmware_version.empty() ? "N/A" : device_info->firmware_version)
            << std::endl;
  std::cout << "  Hardware version: " << (device_info->hardware_version.empty() ? "N/A" : device_info->hardware_version)
            << std::endl;
  std::cout << "  : " << (device_info->manufacturer.empty() ? "N/A" : device_info->manufacturer) << std::endl;
}

int main() {
  // Get object instance
  auto& robot = GalbotRobot::get_instance(MachineType::G1);

  // Initialize system
  if (robot.init()) {
    std::cout << "System initialized successfully!" << std::endl;
  } else {
    std::cerr << "System initialization failed!" << std::endl;
    return -1;
  }

  // Program started, waiting for data
  std::this_thread::sleep_for(std::chrono::milliseconds(1000));

  // Get device information
  std::shared_ptr<DeviceInfo> device_info = robot.get_device_information();
  if (device_info) {
    std::cout << "Device information retrieved successfully!" << std::endl;
    print_device_info(device_info);
  } else {
    std::cerr << "Failed to get device information!" << std::endl;
  }

  // Exit system and release SDK resources
  robot.request_shutdown();
  robot.wait_for_shutdown();
  robot.destroy();

  return 0;
}
```

### Get Camera Image Data (get_rgb_data && get_depth_data) (get_camera_data)

**Applicable Scenarios**: Get RGB image and depth image data, used for visual perception, object detection, SLAM and other tasks.

```cpp title="examples/cpp/galbot_robot/src/get_camera_data_example.cpp"
#include <iostream>
#include <vector>
#include <memory>
#include <unordered_set>
#include <chrono>
#include <thread>

#include "galbot_robot.hpp"
#include "opencv2/opencv.hpp"

using namespace galbot::sdk;

void print_rgb_data(const std::shared_ptr<RgbData> &rgb_data) {
  if (rgb_data == nullptr) {
    std::cout << "rgb_data is nullptr" << std::endl;
    return;
  }

  std::cout << "Camera image timestamp: "
            << rgb_data->header.timestamp_ns
            << std::endl;
  std::cout << "format is " << rgb_data->format << std::endl;
  std::cout << "frame_id is " << rgb_data->header.frame_id << std::endl;
  std::cout << "data size is " << rgb_data->data.size() << std::endl;

  std::cout << "show image:";

  std::shared_ptr<cv::Mat> img = rgb_data->convert_to_cv2_mat();

  cv::imwrite("result_image.jpg", *img);

  std::cout << "Image saved to result_image.jpg" << std::endl;
}

void print_depth_data(const std::shared_ptr<DepthData> depth_data_ptr) {
  if (depth_data_ptr == nullptr) {
    std::cout << "depth_data_ptr is nullptr" << std::endl;
    return;
  }

  std::cout << "Camera image timestamp: "
            << depth_data_ptr->header.timestamp_ns
            << std::endl;
  std::cout << "format is " << depth_data_ptr->format << std::endl;
  std::cout << "frame_id is " << depth_data_ptr->header.frame_id << std::endl;
  std::cout << "data size is " << depth_data_ptr->data.size() << std::endl;

  std::shared_ptr<cv::Mat> img = depth_data_ptr->convert_to_cv2_mat();

  if (img && !img->empty()) {
    cv::Mat img_vis;

    // Image information normalization
    cv::normalize(*img, img_vis, 0, 255, cv::NORM_MINMAX, CV_8UC1);

    // Pseudo-color enhancement
    cv::Mat img_color;
    cv::applyColorMap(img_vis, img_color, cv::COLORMAP_JET);

    // save
    cv::imwrite("check_raw_data.png", *img); 
    cv::imwrite("check_visual_view.jpg", img_color); 

    std::cout << "Image saved: \n"
              << "1. check_raw_data.png -> A fully black image containing real physical depth\n"
              << "2. check_visual_view.jpg -> A colorized image where object contours are visible" << std::endl;
    }
}

int main() {
    // Get object instance
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize sensors; only cameras and LiDAR sensors passed during initialization can retrieve data
    std::unordered_set<SensorType> sensor_types =  {
        SensorType::HEAD_LEFT_CAMERA,       // Head left camera
        SensorType::LEFT_ARM_DEPTH_CAMERA,  // Left arm depth camera
    };

    // Initialize system
    if (robot.init(sensor_types)) {
        std::cout << "System initialized successfully!" << std::endl;
    } else {
        std::cerr << "System initialization failed!" << std::endl;
        return -1;
    }
    // Wait for camera data ready
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));

    // Get RGB image data
    std::shared_ptr<RgbData> rgb_data = robot.get_rgb_data(SensorType::HEAD_LEFT_CAMERA);
    if (rgb_data) {
        std::cout << "RGB image data retrieved successfully!" << std::endl;
        print_rgb_data(rgb_data);
    } else {
        std::cerr << "Failed to get RGB image data!" << std::endl;
    }

    // Get depth image data
    std::shared_ptr<DepthData> depth_data = robot.get_depth_data(SensorType::LEFT_ARM_DEPTH_CAMERA);
    if (depth_data) {
        std::cout << "Depth image data retrieved successfully!" << std::endl;
        print_depth_data(depth_data);
    } else {
        std::cerr << "Failed to get depth image data!" << std::endl;
    }

    // Exit system and release SDK resources
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### Get Sensor Parameters (get_camera_intrinsic && get_sensor_extrinsic)

**Applicable Scenarios**: Get camera intrinsics and sensor extrinsics relative to the robot base, used for computer vision calculations and 3D reconstruction.

```cpp title="examples/cpp/galbot_robot/src/get_camera_params.cpp"
#include <iostream>
#include <vector>
#include <memory>
#include <unordered_set>
#include <chrono>
#include <thread>

#include "galbot_robot.hpp"
#include "opencv2/opencv.hpp"

using namespace galbot::sdk;

void print_rgb_data(
  const std::shared_ptr<RgbData> &rgb_data) {
  if (rgb_data == nullptr) {
    std::cout << "rgb_data is nullptr" << std::endl;
    return;
  }

  std::cout << "Camera image timestamp: "
            << rgb_data->header.timestamp_ns
            << std::endl;
  std::cout << "format is " << rgb_data->format << std::endl;
  std::cout << "frame_id is " << rgb_data->header.frame_id << std::endl;
  std::cout << "data size is " << rgb_data->data.size() << std::endl;

  std::cout << "show image:";

  std::shared_ptr<cv::Mat> img = rgb_data->convert_to_cv2_mat();

  cv::imwrite("result_image.jpg", *img);

  std::cout << "Image saved to result_image.jpg" << std::endl;
}

void print_depth_data(
    const std::shared_ptr<DepthData>
        depth_data_ptr) {
  if (depth_data_ptr == nullptr) {
    std::cout << "depth_data_ptr is nullptr" << std::endl;
    return;
  }

  std::cout << "Camera image timestamp: "
            << depth_data_ptr->header.timestamp_ns
            << std::endl;
  std::cout << "format is " << depth_data_ptr->format << std::endl;
  std::cout << "frame_id is " << depth_data_ptr->header.frame_id << std::endl;
  std::cout << "data size is " << depth_data_ptr->data.size() << std::endl;

  std::shared_ptr<cv::Mat> img = depth_data_ptr->convert_to_cv2_mat();

  if (img && !img->empty()) {
    cv::Mat img_vis;

    // Image information normalization
    cv::normalize(*img, img_vis, 0, 255, cv::NORM_MINMAX, CV_8UC1);

    // Pseudo-color enhancement
    cv::Mat img_color;
    cv::applyColorMap(img_vis, img_color, cv::COLORMAP_JET);

    // save
    cv::imwrite("check_raw_data.png", *img); 
    cv::imwrite("check_visual_view.jpg", img_color); 

    std::cout << "Image saved: \n"
              << "1. check_raw_data.png -> A fully black image containing real physical depth\n"
              << "2. check_visual_view.jpg -> A colorized image where object contours are visible" << std::endl;
    }
}

void print_camera_info(const std::shared_ptr<CameraInfo>& camerainfo){
    if (camerainfo == nullptr) {
        std::cout << "camerainfo is nullptr" << std::endl;
        return;
    }

    std::cout << "camera info:" << std::endl;
    std::cout << "header {" << std::endl;
    std::cout << "  timestamp_ns: " << camerainfo->header.timestamp_ns << std::endl;
    std::cout << "  frame_id: " << camerainfo->header.frame_id << std::endl;
    std::cout << "}" << std::endl;
    std::cout << "width: " << camerainfo->width << std::endl;
    std::cout << "height: " << camerainfo->height << std::endl;
    std::cout << "distortion_model: " << camerainfo->distortion_model << std::endl;
    std::cout << "d: ";
    for (auto& d_i : camerainfo->d) {
        std::cout << d_i << " ";
    }
    std::cout << std::endl;
    std::cout << "k: ";
    for (auto& k_i : camerainfo->k) {
        std::cout << k_i << " ";
    }
    std::cout << std::endl;
    std::cout << "r: ";
    for (auto& r_i : camerainfo->r) {
        std::cout << r_i << " ";
    }
    std::cout << std::endl;
    std::cout << "p: ";
    for (auto& p_i : camerainfo->p) {
        std::cout << p_i << " ";
    }
    std::cout << std::endl;
    std::cout << "T: ";
    for (auto& t_i : camerainfo->T) {
        std::cout << t_i << " ";
    }
    std::cout << std::endl;
    std::cout << "roi {" << std::endl;
    std::cout << "  width: " << camerainfo->roi.width << std::endl;
    std::cout << "  height: " << camerainfo->roi.height << std::endl;
    std::cout << "}" << std::endl;
    std::cout << "camera_type: " << camerainfo->camera_type << std::endl;
}

int main() {
    // Get object instance
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize sensors; only cameras and LiDAR sensors passed during initialization can retrieve data
    std::unordered_set<SensorType> sensor_types =  {
        SensorType::HEAD_LEFT_CAMERA,       // Head left camera
        SensorType::LEFT_ARM_DEPTH_CAMERA,  // Left arm depth camera
    };

    // Initialize system
    if (robot.init(sensor_types)) {
        std::cout << "System initialized successfully!" << std::endl;
    } else {
        std::cerr << "System initialization failed!" << std::endl;
        return -1;
    }
    // Wait for camera data ready
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));

    // Get RGB image data
    std::shared_ptr<RgbData> rgb_data = robot.get_rgb_data(SensorType::HEAD_LEFT_CAMERA);
    if (rgb_data) {
        std::cout << "RGB image data retrieved successfully!" << std::endl;
        print_rgb_data(rgb_data);
    } else {
        std::cerr << "Failed to get RGB image data!" << std::endl;
    }

    // Get camera parameters
    std::shared_ptr<CameraInfo> rgb_camerainfo = robot.get_camera_intrinsic(SensorType::LEFT_ARM_DEPTH_CAMERA);
    if (rgb_camerainfo) {
        std::cout << "Camera parameters retrieved successfully!" << std::endl;
        print_camera_info(rgb_camerainfo);
    } else {
        std::cerr << "Failed to get camera parameters!" << std::endl;
    }

    // Get depth image data
    std::shared_ptr<DepthData> depth_data = robot.get_depth_data(SensorType::LEFT_ARM_DEPTH_CAMERA);
    if (depth_data) {
        std::cout << "Depth image data retrieved successfully!" << std::endl;
        print_depth_data(depth_data);
    } else {
        std::cerr << "Failed to get depth image data!" << std::endl;
    }

    // Get sensor extrinsics
    std::pair<std::vector<double>, int64_t> sensor_extrinsic = robot.get_sensor_extrinsic(SensorType::LEFT_ARM_DEPTH_CAMERA);
    if (!sensor_extrinsic.first.empty()) {
        std::cout << "Sensor extrinsics retrieved successfully!" << std::endl;
        std::cout << "transform: ";
        for (auto& t_i : sensor_extrinsic.first) {
            std::cout << t_i << " ";
        }
        std::cout << std::endl;
        std::cout << "timestamp: " << sensor_extrinsic.second << std::endl;
    } else {
        std::cerr << "Failed to get sensor extrinsics!" << std::endl;
    }

    // Exit system and release SDK resources
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### Get Lidar Data (get_lidar_data)

**Applicable Scenarios**: Get LiDAR point cloud data, used for navigation, obstacle avoidance, and environment modeling.

```cpp title="examples/cpp/galbot_robot/src/get_lidar_data_example.cpp"
#include <iostream>
#include <vector>
#include <string>
#include <fstream>
#include <cmath>
#include <chrono>
#include <thread>
#include <memory>
#include <unordered_set>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

// Define point structure
struct Point3D {
    float x, y, z;
};

/**
 * Directly extract the XYZ array from LidarData via pointer operations
 */
std::vector<Point3D> get_xyz_points(const std::shared_ptr<LidarData>& cloud, bool remove_nan = false) {
    std::vector<Point3D> points;
    if (!cloud || cloud->data.empty()) return points;

    // 1. Find the offsets of x, y, z fields (offset)
    // In the Python version, fields are indexed by field name; here we precompute offsets for better performance
    int32_t off_x = -1, off_y = -1, off_z = -1;
    for (const auto& f : cloud->fields) {
        if (f.name == "x") off_x = f.offset;
        else if (f.name == "y") off_y = f.offset;
        else if (f.name == "z") off_z = f.offset;
    }

    if (off_x == -1 || off_y == -1 || off_z == -1) {
        std::cerr << "Error: point cloud data is missing required xyz fields" << std::endl;
        return points;
    }

    uint32_t num_points = cloud->width * cloud->height;
    points.reserve(num_points);

    const uint8_t* raw_data = cloud->data.data();
    uint32_t point_step = cloud->point_step;

    // 2. Read directly via pointer (core zero-copy logic)
    for (uint32_t i = 0; i < num_points; ++i) {
        // Calculate starting pointer for current point
        const uint8_t* pt_ptr = raw_data + (i * point_step);

        // Use reinterpret_cast to directly cast pointer types and read memory
        // Assume LiDAR data is float32 (F), which is the most common format
        float x = *reinterpret_cast<const float*>(pt_ptr + off_x);
        float y = *reinterpret_cast<const float*>(pt_ptr + off_y);
        float z = *reinterpret_cast<const float*>(pt_ptr + off_z);

        // Handle NaN values (corresponds to Python remove_nan logic)
        if (remove_nan) {
            if (std::isnan(x) || std::isnan(y) || std::isnan(z)) {
                continue;
            }
        }

        points.push_back({x, y, z});
    }

    return points;
}

/**
 * Save to a PCD file
 */
void save_xyz_to_pcd(const std::vector<Point3D>& points, const std::string& filename) {
    std::ofstream fs(filename);
    if (!fs.is_open()) {
        std::cerr << "Unable to open file for writing: " << filename << std::endl;
        return;
    }

    // PCD 0.7 Header
    fs << "# .PCD v0.7 - Point Cloud Data file format\n"
       << "VERSION 0.7\n"
       << "FIELDS x y z\n"
       << "SIZE 4 4 4\n"
       << "TYPE F F F\n"
       << "COUNT 1 1 1\n"
       << "WIDTH " << points.size() << "\n"
       << "HEIGHT 1\n"
       << "VIEWPOINT 0 0 0 1 0 0 0\n"
       << "POINTS " << points.size() << "\n"
       << "DATA ascii\n";

    // Data
    for (const auto& p : points) {
        fs << p.x << " " << p.y << " " << p.z << "\n";
    }

    fs.close();
    std::cout << "Saved " << points.size() << " points to " << filename << std::endl;
}

int main() {
    // Get object instance
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize sensors; only cameras and LiDAR sensors passed during initialization can retrieve data
    std::unordered_set<SensorType> sensor_types =  {
        SensorType::BASE_LIDAR              // Chassis lidar
    };

    // Initialize system
    if (robot.init(sensor_types)) {
        std::cout << "System initialized successfully!" << std::endl;
    } else {
        std::cerr << "System initialization failed!" << std::endl;
        return -1;
    }

    // Program started, waiting for data
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));

    // Get LiDAR data
    std::shared_ptr<LidarData> lidar_data = robot.get_lidar_data(SensorType::BASE_LIDAR);
    if (lidar_data) {
        std::cout << "Lidar data retrieved successfully!" << std::endl;
        std::vector<Point3D> xyz_points = get_xyz_points(lidar_data, false);
        if (!xyz_points.empty()) {
            save_xyz_to_pcd(xyz_points, "output_xyz.pcd");
        }
    } else {
        std::cerr << "Failed to get lidar data!" << std::endl;
    }

    // Exit system and release SDK resources
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### One-Click Reset to Zero – Odometry Frame (whole_body_reset_zero_odom)

**Applicable Scenarios**: Quickly move all joints to zero position (initial pose) based on odometry frame. Typically used for initialization after program startup.

```cpp title="examples/cpp/galbot_robot/src/whole_body_reset_zero_odom_example.cpp"
#include <iostream>

#include "galbot_motion.hpp"
#include "galbot_robot.hpp"

using namespace galbot::sdk;

namespace {
const char* control_status_to_string(ControlStatus status) {
    switch (status) {
        case ControlStatus::SUCCESS:
            return "SUCCESS";
        case ControlStatus::TIMEOUT:
            return "TIMEOUT";
        case ControlStatus::FAULT:
            return "FAULT";
        case ControlStatus::INVALID_INPUT:
            return "INVALID_INPUT";
        case ControlStatus::INIT_FAILED:
            return "INIT_FAILED";
        case ControlStatus::IN_PROGRESS:
            return "IN_PROGRESS";
        case ControlStatus::STOPPED_UNREACHED:
            return "STOPPED_UNREACHED";
        case ControlStatus::DATA_FETCH_FAILED:
            return "DATA_FETCH_FAILED";
        case ControlStatus::PUBLISH_FAIL:
            return "PUBLISH_FAIL";
        case ControlStatus::COMM_DISCONNECTED:
            return "COMM_DISCONNECTED";
        default:
            return "UNKNOWN_STATUS";
    }
}
}  // namespace

int main() {
    auto& robot = GalbotRobot::get_instance(MachineType::G1);
    auto& motion = GalbotMotion::get_instance(MachineType::G1);

    if (!robot.init()) {
        std::cerr << "GalbotRobot init failed." << std::endl;
        return -1;
    }
    if (!motion.init()) {
        std::cerr << "GalbotMotion init failed." << std::endl;
        return -1;
    }

    // Optional frames (frame_id: base_link/odom/map, reference_frame_id: odom/map)
    const std::string frame_id = "base_link";
    const std::string reference_frame_id = "odom";

    // reset to zero
    auto result = robot.zero_whole_body_and_base(
        frame_id,
        reference_frame_id,
        /*is_blocking=*/true,
        /*leg_head_speed_rad_s=*/0.2,
        /*leg_head_timeout_s=*/15.0,
        /*params=*/default_param);
    
    std::cout << "Zero joint status: " << motion.status_to_string(result.first) << std::endl;
    std::cout << "Zero base status: " << control_status_to_string(result.second) << std::endl;

    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### One-Click Reset to Zero – Map Frame (whole_body_reset_zero_map)

**Applicable Scenarios**: Quickly move all joints to zero position (initial pose) based on map frame.

```cpp title="examples/cpp/galbot_robot/src/whole_body_reset_zero_map_example.cpp"
#include <iostream>

#include "galbot_motion.hpp"
#include "galbot_robot.hpp"

using namespace galbot::sdk;

namespace {
const char* control_status_to_string(ControlStatus status) {
    switch (status) {
        case ControlStatus::SUCCESS:
            return "SUCCESS";
        case ControlStatus::TIMEOUT:
            return "TIMEOUT";
        case ControlStatus::FAULT:
            return "FAULT";
        case ControlStatus::INVALID_INPUT:
            return "INVALID_INPUT";
        case ControlStatus::INIT_FAILED:
            return "INIT_FAILED";
        case ControlStatus::IN_PROGRESS:
            return "IN_PROGRESS";
        case ControlStatus::STOPPED_UNREACHED:
            return "STOPPED_UNREACHED";
        case ControlStatus::DATA_FETCH_FAILED:
            return "DATA_FETCH_FAILED";
        case ControlStatus::PUBLISH_FAIL:
            return "PUBLISH_FAIL";
        case ControlStatus::COMM_DISCONNECTED:
            return "COMM_DISCONNECTED";
        default:
            return "UNKNOWN_STATUS";
    }
}
}  // namespace

int main() {
    auto& robot = GalbotRobot::get_instance(MachineType::G1);
    auto& motion = GalbotMotion::get_instance(MachineType::G1);

    if (!robot.init()) {
        std::cerr << "GalbotRobot init failed." << std::endl;
        return -1;
    }
    if (!motion.init()) {
        std::cerr << "GalbotMotion init failed." << std::endl;
        return -1;
    }

    // Optional frames (frame_id: base_link/odom/map, reference_frame_id: odom/map)
    const std::string frame_id = "base_link";
    const std::string reference_frame_id = "map";

    // reset to zero
    auto result = robot.zero_whole_body_and_base(
        frame_id,
        reference_frame_id,
        /*is_blocking=*/true,
        /*leg_head_speed_rad_s=*/0.2,
        /*leg_head_timeout_s=*/15.0,
        /*params=*/default_param);
    
    std::cout << "Zero joint status: " << motion.status_to_string(result.first) << std::endl;
    std::cout << "Zero base status: " << control_status_to_string(result.second) << std::endl;

    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

## Class: GalbotMotion

### Get Instance and Initialize (get_instance && init)

**Applicable Scenarios**: Get the motion planning module singleton and initialize. Must be called before using motion planning functions.

```cpp title="examples/cpp/galbot_motion/src/get_instance_init_example.cpp"
#include <iostream>
#include <set>
#include <string>

#include "galbot_motion.hpp"
#include "galbot_robot.hpp"

using namespace galbot::sdk;

int main() {

    auto& planner = GalbotMotion::get_instance(MachineType::G1);
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    if (planner.init()) {
        std::cout << "Planner initialized successfully!" << std::endl;
    } else {
        std::cerr << "Planner initialization failed!" << std::endl;
        return -1;
    }
    
    if (robot.init()) {
        std::cout << "System initialized successfully!" << std::endl;
    } else {
        std::cerr << "System initialization failed!" << std::endl;
        return -1;
    }

    // You can still manage the robot lifecycle through GalbotRobot
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### Forward Kinematics (Using Current State or Specified RobotStates) (forward_kinematics)

**Applicable Scenarios**: Calculate end effector pose based on given joint angles. Used for robotic arm task verification and state analysis.

```cpp title="examples/cpp/galbot_motion/src/forward_kinematics_example.cpp"
#include <algorithm>
#include <chrono>
#include <iostream>
#include <map>
#include <string>
#include <thread>
#include <tuple>
#include <vector>

#include "galbot_motion.hpp"
#include "galbot_robot.hpp"

using namespace galbot::sdk;

// Helper print function
void print_pose(const std::string& label, const std::tuple<MotionStatus, std::vector<double>>& res,
                GalbotMotion& planner) {
  std::cout << "[" << label << "] Status: " << planner.status_to_string(std::get<0>(res)) << std::endl;

  if (std::get<0>(res) == MotionStatus::SUCCESS) {
    std::cout << "End-effector pose: ";
    for (double v : std::get<1>(res)) {
      std::cout << v << " ";
    }
    std::cout << "\n" << std::endl;
  } else {
    std::cout << "Calculation failed!" << std::endl;
  }
}

int main() {
  auto& planner = GalbotMotion::get_instance(MachineType::G1);
  auto& robot = GalbotRobot::get_instance(MachineType::G1);

  if (planner.init()) {
    std::cout << "Planner initialized successfully!" << std::endl;
  } else {
    std::cerr << "Planner initialization failed!" << std::endl;
    return -1;
  }

  if (robot.init()) {
    std::cout << "System initialized successfully!" << std::endl;
  } else {
    std::cerr << "System initialization failed!" << std::endl;
    return -1;
  }

  // Program started, waiting for data
  std::this_thread::sleep_for(std::chrono::milliseconds(3000));

  std::map<std::string, std::vector<double>> chain_joints = {
      {"leg", {0.4992, 1.4991, 1.0005, 0.0000}},
      {"head", {0.0000, 0.0}},
      {"left_arm", {1.9999, -1.6000, -0.5999, -1.6999, 0.0000, -0.7999, 0.0000}},
      {"right_arm", {-2.0000, 1.6001, 0.6001, 1.7000, 0.0000, 0.8000, 0.0000}}};

  std::vector<double> whole_body_joint;
  std::vector<std::string> keys = {"leg", "head", "left_arm", "right_arm"};
  for (const auto& key : keys) {
    whole_body_joint.insert(whole_body_joint.end(), chain_joints[key].begin(), chain_joints[key].end());
  }

  std::vector<double> base_state = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0};
  std::string end_link = "left_arm_end_effector_mount_link";
  std::string reference_frame = "base_link";

  // --- test 1: defaultparameters (current status) ---
  try {
    std::cout << ">> Executing: Basic forward kinematics..." << std::endl;
    auto res1 = planner.forward_kinematics(end_link, reference_frame);
    print_pose("Basic version", res1, planner);
  } catch (const std::exception& e) {
    std::cerr << "❌ Basic version exception: " << e.what() << std::endl;
  }

  // --- test 2: jointstatus + parameters ---
  try {
    std::cout << ">> Executing: Forward kinematics with custom joints..." << std::endl;

    std::unordered_map<std::string, std::vector<double>> custom_joint_state = {{"left_arm", chain_joints["left_arm"]}};
    auto custom_param_ptr = std::make_shared<Parameter>();
    auto res2 = planner.forward_kinematics(end_link, reference_frame, custom_joint_state, custom_param_ptr);

    print_pose("Custom parameters", res2, planner);
  } catch (const std::exception& e) {
    std::cerr << "❌ Custom-parameter exception: " << e.what() << std::endl;
  }

  // --- test 3: RobotStates forward kinematics(current status, planning)---
  try {
    std::cout << ">> Executing: Forward kinematics based on RobotStates..." << std::endl;

    RobotStates current_state = planner.get_robot_states();
    if (current_state.whole_body_joint.empty()) {
      std::cerr << "❌ RobotStates-based: Unable to get current body joint states; ensure WBC/sensors are ready." << std::endl;
    } else {
      auto ref_robot_state_ptr = std::make_shared<RobotStates>(std::move(current_state));
      auto res3 = planner.forward_kinematics_by_state(end_link, ref_robot_state_ptr, reference_frame,
                                                      std::make_shared<Parameter>());
      print_pose("Based on RobotStates", res3, planner);
    }
  } catch (const std::exception& e) {
    std::cerr << "❌ RobotStates-based exception: " << e.what() << std::endl;
  }

  robot.request_shutdown();
  robot.wait_for_shutdown();
  robot.destroy();

  return 0;
}
```

### Get Link Names (get_link_names)

**Applicable Scenarios**: Get a list of names of all links in the robot model, used for collision detection and motion planning debugging.

```cpp title="examples/cpp/galbot_motion/src/get_link_names_example.cpp"
#include <chrono>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

#include "galbot_motion.hpp"
#include "galbot_robot.hpp"

using namespace galbot::sdk;

void print_link_names(const std::vector<std::string>& link_names, const std::string& title) {
  std::cout << title << " (total " << link_names.size() << " items):" << std::endl;
  for (size_t i = 0; i < link_names.size(); ++i) {
    std::cout << "  " << (i + 1) << ". " << link_names[i] << std::endl;
  }
}

int main() {
  // Get object instance
  auto& motion = GalbotMotion::get_instance(MachineType::G1);
  auto& robot = GalbotRobot::get_instance(MachineType::G1);

  // Initialize system
  if (!motion.init()) {
    std::cerr << "GalbotMotion initialization failed!" << std::endl;
    return -1;
  }
  if (!robot.init()) {
    std::cerr << "GalbotRobot initialization failed!" << std::endl;
    return -1;
  }

  std::cout << "System initialized successfully!" << std::endl;

  // Program started, waiting for data
  std::this_thread::sleep_for(std::chrono::milliseconds(2000));

  try {
    // Get all link names
    std::vector<std::string> all_link_names = motion.get_link_names(false);
    print_link_names(all_link_names, "\nAll link names");

    // getend effectorexecute link
    std::vector<std::string> ee_link_names = motion.get_link_names(true);
    print_link_names(ee_link_names, "\nEnd-effector link names");
  } catch (const std::exception& e) {
    std::cerr << "Get link name exception: " << e.what() << std::endl;
  }

  // Exit system and release SDK resources
  robot.request_shutdown();
  robot.wait_for_shutdown();
  robot.destroy();

  return 0;
}
```

### Inverse Kinematics (Basic and RobotStates-based) (inverse_kinematics)

**Applicable Scenarios**: Solve for the required joint angles based on the desired end effector pose. This is a core step for operations like robotic arm grasping.

```cpp title="examples/cpp/galbot_motion/src/inverse_kinematics_example.cpp"
#include <algorithm>
#include <chrono>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <thread>
#include <tuple>
#include <unordered_map>
#include <vector>

#include "galbot_motion.hpp"
#include "galbot_robot.hpp"

using namespace galbot::sdk;

// Helper function: print inverse kinematics result
void print_ik_result(const std::string& label,
                     const std::tuple<MotionStatus, std::unordered_map<std::string, std::vector<double>>>& res,
                     GalbotMotion& planner) {
  auto status = std::get<0>(res);
  auto joint_map = std::get<1>(res);

  std::cout << "[" << label << "] Status feedback: " << planner.status_to_string(status) << std::endl;

  if (status == MotionStatus::SUCCESS) {
    std::cout << "✅ IK computation succeeded! Joint angles obtained:" << std::endl;
    for (const auto& [name, joints] : joint_map) {
      std::cout << "  - Chain [" << name << "]: ";
      for (double v : joints)
        std::cout << v << " ";
      std::cout << std::endl;
    }
  } else {
    std::cout << "❌ inverse kinematics failed, checkinput targetpose." << std::endl;
  }
  std::cout << "---------------------------------------------------" << std::endl;
}

int main() {
  auto& planner = GalbotMotion::get_instance(MachineType::G1);
  auto& robot = GalbotRobot::get_instance(MachineType::G1);

  if (planner.init()) {
    std::cout << "Planner initialized successfully!" << std::endl;
  } else {
    std::cerr << "Planner initialization failed!" << std::endl;
    return -1;
  }

  if (robot.init()) {
    std::cout << "System initialized successfully!" << std::endl;
  } else {
    std::cerr << "System initialization failed!" << std::endl;
    return -1;
  }

  std::this_thread::sleep_for(std::chrono::milliseconds(1000));

  // Joint state definition
  std::unordered_map<std::string, std::vector<double>> chain_joints = {
      {"leg", {0.4992, 1.4991, 1.0005, 0.0000, -0.0004}},
      {"head", {0.0000, 0.0}},
      {"left_arm", {1.9999, -1.6000, -0.5999, -1.6999, 0.0000, -0.7999, 0.0000}},
      {"right_arm", {-2.0000, 1.6001, 0.6001, 1.7000, 0.0000, 0.8000, 0.0000}}};

  // Target pose definition (x, y, z, qx, qy, qz, qw)
  std::unordered_map<std::string, std::vector<double>> chain_pose_baselink = {
      {"left_arm", {0.1267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991}},
      {"right_arm", {0.1267, -0.2345, 0.7358, -0.0225, 0.0126, -0.0343, 0.9991}}};

  // Whole-body joint vector concatenation (Leg -> Head -> Left Arm -> Right Arm)
  std::vector<double> whole_body_joint;
  std::vector<std::string> key_order = {"leg", "head", "left_arm", "right_arm"};
  for (const auto& key : key_order) {
    whole_body_joint.insert(whole_body_joint.end(), chain_joints[key].begin(), chain_joints[key].end());
  }

  // General configuration
  std::string reference_frame = "base_link";
  std::string target_frame = "EndEffector";
  std::string target_chain = "left_arm";
  auto params = std::make_shared<Parameter>();

  // Scenario 1: Single-chain inverse kinematics
  try {
    std::cout << ">> Running Scenario 1: Single-chain IK test..." << std::endl;
    std::vector<std::string> one_chain = {target_chain};

    auto res = planner.inverse_kinematics(chain_pose_baselink[target_chain],  // 1. target_pose
                                          one_chain                           // 2. chain_names
                                          // target_frame,                      // 3. target_frame
                                          // reference_frame,                   // 4. reference_frame
                                          // {},                                // 5. initial_joint_positions (empty)
                                          // false,                             // 6. enable_collision_check (bool)
                                          // params                             // 7. params (shared_ptr)
    );
    print_ik_result("Single-chain inverse kinematics", res, planner);
    std::this_thread::sleep_for(std::chrono::milliseconds(800));
  } catch (const std::exception& e) {
    std::cerr << "Scenario 1 exception: " << e.what() << std::endl;
  }

  // Scenario 2: Arm chain + torso inverse kinematics
  try {
    std::cout << ">> Running Scenario 2: Arm chain + torso IK test..." << std::endl;
    std::vector<std::string> chain_with_torso = {target_chain, "torso"};

    auto res = planner.inverse_kinematics(chain_pose_baselink[target_chain], chain_with_torso, target_frame,
                                          reference_frame, {}, false, params);
    print_ik_result("Arm + torso inverse kinematics", res, planner);
    std::this_thread::sleep_for(std::chrono::milliseconds(800));
  } catch (const std::exception& e) {
    std::cerr << "Scenario 2 exception: " << e.what() << std::endl;
  }

  // Scenario 3: invalid chain combination
  try {
    std::cout << ">> Running Scenario 3: Invalid chain-combination test..." << std::endl;
    std::vector<std::string> error_chains = {target_chain, "torso", "head"};

    auto res = planner.inverse_kinematics(chain_pose_baselink[target_chain], error_chains, target_frame,
                                          reference_frame, {}, false, params);
    print_ik_result("Invalid chain combination detection", res, planner);
  } catch (const std::exception& e) {
    std::cerr << "Scenario 3 exception: " << e.what() << std::endl;
  }

  // Scenario 4: use reference joints (initial_joint_positions can specify chain joints as IK references; unspecified chain joints are filled with whole-body joints)
  try {
    std::cout << ">> Running Scenario 4: IK test with initial reference values..." << std::endl;
    std::vector<std::string> one_chain = {target_chain};

    auto res = planner.inverse_kinematics(chain_pose_baselink[target_chain], one_chain, target_frame, reference_frame,
                                          chain_joints, false, params);
    print_ik_result("Inverse kinematics with reference values", res, planner);
    std::this_thread::sleep_for(std::chrono::milliseconds(800));
  } catch (const std::exception& e) {
    std::cerr << "Scenario 4 exception: " << e.what() << std::endl;
  }

  // scenario 5: RobotStates inverse kinematics
  try {
    std::cout << ">> Running Scenario 5: IK test based on RobotStates..." << std::endl;

    // Construct RobotStates smart pointer
    auto ref_state = std::make_shared<RobotStates>();
    ref_state->chain_name = target_chain;
    ref_state->whole_body_joint = whole_body_joint;
    ref_state->base_state = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0};

    std::vector<std::string> one_chain = {target_chain};

    auto res = planner.inverse_kinematics_by_state(chain_pose_baselink[target_chain],  // 1. target_pose
                                                   one_chain,                          // 2. chain_names
                                                   target_frame,                       // 3. target_frame
                                                   reference_frame,                    // 4. reference_frame
                                                   ref_state,  // 5. reference_robot_states (shared_ptr)
                                                   false,      // 6. enable_collision_check (bool)
                                                   params      // 7. params (shared_ptr)
    );
    print_ik_result("RobotStates inverse kinematics", res, planner);
  } catch (const std::exception& e) {
    std::cerr << "Scenario 5 exception: " << e.what() << std::endl;
  }

  robot.request_shutdown();
  robot.wait_for_shutdown();
  robot.destroy();
  std::cout << "Resources released." << std::endl;

  return 0;
}
```

### Get and Set End Effector Pose (get_set_end_effort_pos)

**Applicable Scenarios**: Directly get current end effector pose, or move the end effector to a specified pose. Integrates inverse kinematics calculation and execution.

```cpp title="examples/cpp/galbot_motion/src/get_set_end_effort_pos_example.cpp"
#include <iostream>
#include <vector>
#include <string>
#include <unordered_map>
#include <thread>
#include <chrono>
#include <tuple>
#include <memory>
#include <stdexcept>

#include "galbot_motion.hpp"
#include "galbot_robot.hpp"

using namespace galbot::sdk;

// Helper function: print pose information
void print_pose_info(const std::string& label, const std::vector<double>& pose) {
    if (pose.size() == 7) {
        std::cout << "[" << label << "] Pose: "
                  << "pos(" << pose[0] << ", " << pose[1] << ", " << pose[2] << "), "
                  << "ori(" << pose[3] << ", " << pose[4] << ", " << pose[5] << ", " << pose[6] << ")" 
                  << std::endl;
    }
}

int main() {

    auto& planner = GalbotMotion::get_instance(MachineType::G1);
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    if (!planner.init()) {
        std::cerr << "GalbotMotion initialization failed" << std::endl;
        return -1;
    }
    if (!robot.init()) {
        std::cerr << "GalbotRobot initialization failed" << std::endl;
        return -1;
    }

    std::this_thread::sleep_for(std::chrono::milliseconds(1000));

    std::unordered_map<std::string, std::vector<double>> chain_pose_baselink = {
        {"leg",       {0.0596, -0.0000, 1.0327, 0.5000, 0.5003, 0.4997, 0.5000}},
        {"head",      {0.0599, 0.0002, 1.4098, -0.7072, 0.0037, 0.0037, 0.7069}},
        {"left_arm",  {0.1267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991}},
        {"right_arm", {0.097768, -0.226021, 0.8, -0.0117403, -0.0098713, 0.0157502, 0.999758}}
    };

    std::string reference_frame = "base_link";
    std::string target_frame = "EndEffector";
    std::string target_chain = "right_arm";
    auto custom_param = std::make_shared<Parameter>();

    // --- Scenario 1: Get end-effector pose (basic version) ---
    try {
        std::cout << ">> Scenario 1: Getting the basic end-effector pose..." << std::endl;
        std::string end_ee_link = "right_arm_end_effector_mount_link";

        auto res = planner.get_end_effector_pose(end_ee_link, reference_frame);
        
        MotionStatus status = std::get<0>(res);
        std::vector<double> pose = std::get<1>(res);

        std::cout << "Execution status: " << planner.status_to_string(status) << std::endl;
        if (status == MotionStatus::SUCCESS) {
            print_pose_info("Basic version", pose);
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(800));
    } catch (const std::exception& e) {
        std::cerr << "❌ Scenario 1 exception: " << e.what() << std::endl;
    }

    // --- Scenario 2: Get end-effector pose by specified chain name + custom frame ---
    try {
        std::cout << ">> Scenario 2: Getting pose by specified chain name..." << std::endl;

        auto res = planner.get_end_effector_pose_on_chain(target_chain, target_frame, reference_frame);
        
        MotionStatus status = std::get<0>(res);
        std::vector<double> pose = std::get<1>(res);

        std::cout << "Execution status: " << planner.status_to_string(status) << std::endl;
        if (status == MotionStatus::SUCCESS) {
            print_pose_info("Specified chain name version", pose);
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(800));
    } catch (const std::exception& e) {
        std::cerr << "❌ Scenario 2 exception: " << e.what() << std::endl;
    }

    // --- Scenario 3: Set end-effector pose ---
    try {
        std::cout << ">> Scenario 3: Setting end-effector pose..." << std::endl;
        
        std::string ee_frame = "right_arm"; 
        std::vector<double> target_pose = chain_pose_baselink[ee_frame];

        MotionStatus status = planner.set_end_effector_pose(
            target_pose,        // 1
            ee_frame,           // 2
            reference_frame,    // 3
            nullptr,            // 4. Important: pass nullptr if no specific reference state is used
            false,              // 5. enable_collision_check
            true,               // 6. is_blocking
            5.0,                // 7. timeout
            custom_param        // 8. params
        );

        std::cout << "Set status: " << planner.status_to_string(status) << std::endl;
        if (status == MotionStatus::SUCCESS) {
            std::cout << "✅ Command sent successfully (blocking wait mode)" << std::endl;
        }
    } catch (const std::exception& e) {
        std::cerr << "❌ Pose-setting exception: " << e.what() << std::endl;
    }

    // --- Scenario 4: Get end-effector pose again after execution ---
    try {
        std::cout << ">> Scenario 4: Getting the basic end-effector pose..." << std::endl;
        std::string end_ee_link = "right_arm_end_effector_mount_link";

        auto res = planner.get_end_effector_pose(end_ee_link, reference_frame);
        
        MotionStatus status = std::get<0>(res);
        std::vector<double> pose = std::get<1>(res);

        std::cout << "Execution status: " << planner.status_to_string(status) << std::endl;
        if (status == MotionStatus::SUCCESS) {
            print_pose_info("Basic version", pose);
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(800));
    } catch (const std::exception& e) {
        std::cerr << "❌ Scenario 4 exception: " << e.what() << std::endl;
    }

    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### Single Point Motion Planning (Joint Space and Cartesian Space) (single_point_planning)

**Applicable Scenarios**: Plan a collision-free motion trajectory from the current pose to a single target pose. Suitable for single-point target arrival tasks.

```cpp title="examples/cpp/galbot_motion/src/single_point_planning_example.cpp"
#include <iostream>
#include <vector>
#include <string>
#include <unordered_map>
#include <thread>
#include <chrono>
#include <tuple>
#include <memory>
#include <stdexcept>

#include "galbot_motion.hpp"
#include "galbot_robot.hpp"

using namespace galbot::sdk;

// Define a trajectory return type to simplify the code
using TrajResult = std::tuple<MotionStatus, std::unordered_map<std::string, std::vector<std::vector<double>>>>;

/**
 * Helper function: print planning result
 */
void print_plan_info(const std::string& label, const TrajResult& res, const std::string& chain_name, GalbotMotion& planner) {
    auto status = std::get<0>(res);
    auto traj_map = std::get<1>(res);

    std::cout << "[" << label << "] Status: " << planner.status_to_string(status) << std::endl;
    if (status == MotionStatus::SUCCESS) {
        if (traj_map.count(chain_name) && !traj_map[chain_name].empty()) {
            std::cout << "✅ Planning succeeded: trajectory points = " << traj_map[chain_name].size() << std::endl;
        } else {
            std::cout << "⚠️ Status is SUCCESS but trajectory is empty (possibly already at target)" << std::endl;
        }
    } else {
        std::cout << "❌ Planning failed" << std::endl;
    }
    std::cout << "---------------------------------------" << std::endl;
}

int main() {

    auto& planner = GalbotMotion::get_instance(MachineType::G1);
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    if (!planner.init()) {
        std::cerr << "GalbotMotion init FAILED" << std::endl;
        return -1;
    }
    if (!robot.init()) {
        std::cerr << "GalbotRobot init FAILED" << std::endl;
        return -1;
    }
    
    std::this_thread::sleep_for(std::chrono::milliseconds(1000));

    std::unordered_map<std::string, std::vector<double>> chain_joints = {
        {"leg",       {0.4992, 1.4991, 1.0005, 0.0000, -0.0004}},
        {"head",      {0.0000, 0.0}},
        {"left_arm",  {1.9999, -1.6000, -0.5999, -1.6999, 0.0000, -0.7999, 0.0000}},
        {"right_arm", {-2.0000, 1.6001, 0.6001, 1.7000, 0.0000, 0.8000, 0.0000}}
    };

    std::unordered_map<std::string, std::vector<double>> chain_pose_baselink = {
        {"leg",       {0.0596, -0.0000, 1.0327, 0.5000, 0.5003, 0.4997, 0.5000}},
        {"head",      {0.0599, 0.0002, 1.4098, -0.7072, 0.0037, 0.0037, 0.7069}},
        {"left_arm",  {0.1267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991}},
        {"right_arm", {0.1267, -0.2345, 0.7358, -0.0225, 0.0126, -0.0343, 0.9991}}
    };

    auto params = std::make_shared<Parameter>();
    std::string target_chain = "left_arm";

    // NOTE:
    // - GalbotMotion does NOT provide real-time obstacle perception / automatic environment updates today.
    // - When enable_collision_check=true, collision checking uses self-collision + objects you load manually via
    //   add_obstacle/attach_target_object (including point clouds if you load them explicitly).

    // Scenario 1: joint-space planning, target type = joint state
    try {
        std::cout << ">> Scenario 1: joint-space planning (joint target)..." << std::endl;

        // Construct target joint state
        auto target_joint = std::make_shared<JointStates>();
        target_joint->chain_name = target_chain;
        target_joint->joint_positions = chain_joints[target_chain];

        auto res = planner.motion_plan(
            target_joint,   // 1. target
            nullptr,        // 2. start (nullptr means start from current state)
            nullptr,        // 3. reference_robot_states
            false,          // 4. enable_collision_check
            params          // 5. params
        );

        print_plan_info("Joint-space planning (joint target)", res, target_chain, planner);
    } catch (const std::exception& e) { std::cerr << e.what() << std::endl; }

    // Scenario 2: joint-space planning, target type = end-effector pose (Cartesian)
    try {
        std::cout << ">> Scenario 2: joint-space planning (pose target)..." << std::endl;

        // Construct target pose state
        auto target_pose = std::make_shared<PoseState>();
        target_pose->chain_name = target_chain;
        target_pose->frame_id = "EndEffector";
        target_pose->reference_frame = "base_link";
        target_pose->pose = chain_pose_baselink[target_chain];

        auto res = planner.motion_plan(
            target_pose,    // 1. target
            nullptr,        // 2. start
            nullptr,        // 3. reference_robot_states
            false,          // 4. enable_collision_check
            params          // 5. params
        );

        print_plan_info("Joint-space planning (pose target)", res, target_chain, planner);
        std::this_thread::sleep_for(std::chrono::milliseconds(800));
    } catch (const std::exception& e) { std::cerr << e.what() << std::endl; }

    // Scenario 3: joint-space planning with an explicit start state
    try {
        std::cout << ">> Scenario 3: joint-space planning (explicit start)..." << std::endl;

        auto target_joint = std::make_shared<JointStates>();
        target_joint->chain_name = target_chain;
        target_joint->joint_positions = chain_joints[target_chain];

        auto start_joint = std::make_shared<JointStates>();
        start_joint->chain_name = target_chain;
        start_joint->joint_positions = std::vector<double>(7, 0.0); // Use seven zeros as the starting point

        auto res = planner.motion_plan(
            target_joint, 
            start_joint,    // 2. Specify the start point
            nullptr, 
            false, 
            params
        );

        print_plan_info("Joint-space planning (explicit start)", res, target_chain, planner);
    } catch (const std::exception& e) { std::cerr << e.what() << std::endl; }

    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();
    return 0;
}
```

### Multi-Waypoint Trajectory Planning (multi_point_planning)

**Applicable Scenarios**: Plan a continuous motion trajectory through multiple waypoints, suitable for complex motions that need to pass through multiple intermediate points.

```cpp title="examples/cpp/galbot_motion/src/multi_point_planning_example.cpp"
#include <iostream>
#include <vector>
#include <string>
#include <unordered_map>
#include <thread>
#include <chrono>
#include <tuple>
#include <memory>
#include <stdexcept>
#include <algorithm>

#include "galbot_motion.hpp"
#include "galbot_robot.hpp"

using namespace galbot::sdk;

// Trajectory return type definition
using TrajResult = std::tuple<MotionStatus, std::unordered_map<std::string, std::vector<std::vector<double>>>>;

/**
 * Helper function: print planning result
 */
void print_multi_plan_result(const std::string& label, const TrajResult& res, const std::string& chain_name, GalbotMotion& planner) {
    auto status = std::get<0>(res);
    auto traj_map = std::get<1>(res);

    std::cout << "[" << label << "] Status feedback: " << planner.status_to_string(status) << std::endl;
    if (status == MotionStatus::SUCCESS) {
        if (traj_map.count(chain_name) && !traj_map[chain_name].empty()) {
            std::cout << "✅ Multi-point planning succeeded: total trajectory points = " << traj_map[chain_name].size() << std::endl;
        } else {
            std::cout << "⚠️ Status is SUCCESS but trajectory is empty; target may overlap current pose." << std::endl;
        }
    } else {
        std::cout << "❌ Multi-point planning failed." << std::endl;
    }
    std::cout << "---------------------------------------------------" << std::endl;
}

int main() {
    auto& planner = GalbotMotion::get_instance(MachineType::G1);
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    if (!planner.init()) {
        std::cerr << "GalbotMotion initialization failed" << std::endl;
        return -1;
    }
    if (!robot.init()) {
        std::cerr << "GalbotRobot initialization failed" << std::endl;
        return -1;
    }
    
    std::this_thread::sleep_for(std::chrono::seconds(2));

    std::unordered_map<std::string, std::vector<double>> chain_joints = {
        {"leg",       {0.4992, 1.4991, 1.0005, 0.0000, -0.0004}},
        {"head",      {0.0000, 0.0}},
        {"left_arm",  {1.9999, -1.6000, -0.5999, -1.6999, 0.0000, -0.7999, 0.0000}},
        {"right_arm", {-2.0000, 1.6001, 0.6001, 1.7000, 0.0000, 0.8000, 0.0000}}
    };

    std::vector<double> whole_body_joint;
    std::vector<std::string> keys = {"leg", "head", "left_arm", "right_arm"};
    for (const auto& key : keys) {
        whole_body_joint.insert(whole_body_joint.end(), chain_joints[key].begin(), chain_joints[key].end());
    }

    auto params = std::make_shared<Parameter>();
    std::string target_chain = "left_arm";

    // --- Scenario 1: Multi-waypoint planning in Cartesian space (PoseState target) ---
    try {
        std::cout << ">> Running Scenario 1: Multi-waypoint planning in Cartesian space..." << std::endl;

        auto target_pose_state = std::make_shared<PoseState>();
        target_pose_state->chain_name = target_chain;

        // Construct waypoints (3 intermediate poses)
        std::vector<std::vector<double>> waypoint_poses = {
            {0.1267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991},
            {0.2267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991},
            {0.3267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991},
            {0.4267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991}
        };

        auto res = planner.motion_plan_multi_waypoints(
            target_pose_state,
            waypoint_poses,
            nullptr,  // start
            nullptr,  // reference_robot_states
            false,    // enable_collision_check
            params    // params
        );

        print_multi_plan_result("Cartesian multi-waypoint single-chain planning", res, target_chain, planner);
        std::this_thread::sleep_for(std::chrono::milliseconds(800));
    } catch (const std::exception& e) { std::cerr << "Scenario 1 exception: " << e.what() << std::endl; }

    // --- Scenario 2: Multi-waypoint planning in joint space (JointStates target) ---
    try {
        std::cout << ">> Running Scenario 2: Multi-waypoint planning in joint space..." << std::endl;

        auto target_joint = std::make_shared<JointStates>();
        target_joint->chain_name = target_chain;

        // Construct waypoints (3 intermediate poses)
        std::vector<std::vector<double>> waypoints = {
            {0.1267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991},
            {0.2267, 0.4342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991},
            {0.3267, 0.6342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991},
            {0.4267, 0.8342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991}
        };

        auto res = planner.motion_plan_multi_waypoints(
            target_joint,
            waypoints,
            nullptr,
            nullptr,
            false,
            params
        );

        print_multi_plan_result("Joint-space multi-waypoint", res, target_chain, planner);
    } catch (const std::exception& e) { std::cerr << "Scenario 2 exception: " << e.what() << std::endl; }

    // 4. Clean up resources
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();
    return 0;
}
```

### Collision Detection (collision_detection)

**Applicable Scenarios**: Check whether a given joint configuration will cause self-collision or collision with environmental obstacles. Used for feasibility checking before motion planning.

```cpp title="examples/cpp/galbot_motion/src/collision_detection_example.cpp"
#include <iostream>
#include <vector>
#include <string>
#include <unordered_map>
#include <thread>
#include <chrono>
#include <tuple>
#include <memory>
#include <stdexcept>
#include <algorithm>

#include "galbot_motion.hpp"
#include "galbot_robot.hpp"
#include "galbot_navigation.hpp"

using namespace galbot::sdk;

int main() {

    auto& planner = GalbotMotion::get_instance(MachineType::G1);
    auto& robot = GalbotRobot::get_instance(MachineType::G1);
    auto& navigation = GalbotNavigation::get_instance(MachineType::G1);

    // NOTE:
    // - GalbotNavigation (galbotNav) may use real-time obstacle perception/avoidance during navigation (deployment dependent).
    // - GalbotMotion does NOT provide real-time obstacle perception today; Motion collision uses self-collision +
    //   manually loaded obstacles (add_obstacle/attach_target_object).

    if (!planner.init()) {
        std::cerr << "GalbotMotion init FAILED" << std::endl;
        return -1;
    }
    if (!robot.init()) {
        std::cerr << "GalbotRobot init FAILED" << std::endl;
        return -1;
    }
    if (!navigation.init()) {
        std::cerr << "GalbotNavigation init FAILED" << std::endl;
        return -1;
    }

    std::unordered_map<std::string, std::vector<double>> chain_joints = {
        {"leg",       {0.4992, 1.4991, 1.0005, 0.0000, -0.0004}},
        {"head",      {0.0000, 0.0}},
        {"left_arm",  {1.9999, -1.6000, -0.5999, -1.6999, 0.0000, -0.7999, 0.0000}},
        {"right_arm", {-2.0000, 1.6001, 0.6001, 1.7000, 0.0000, 0.8000, 0.0000}}
    };

    std::vector<double> whole_body_joint;
    std::vector<std::string> keys = {"leg", "head", "left_arm", "right_arm"};
    for (const auto& key : keys) {
        whole_body_joint.insert(whole_body_joint.end(), chain_joints[key].begin(), chain_joints[key].end());
    }

    std::vector<double> base_state = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0};
    std::vector<double> bad_left_arm_joint = {1.99995, -1.60004, 0.599905, -1.69994, 0, -0.799924, 0};
    auto custom_param = std::make_shared<Parameter>();

    try {
        std::cout << ">> Running collision check..." << std::endl;

        // Construct a RobotStates list for collision checking
        std::vector<std::shared_ptr<RobotStates>> check_states;

        // status 0: status (RobotStates)
        auto state0 = std::make_shared<RobotStates>();
        state0->whole_body_joint = whole_body_joint;
        state0->base_state = base_state;
        check_states.push_back(state0);

        // status 1: status (JointStates RobotStates)
        auto state1 = std::make_shared<JointStates>();
        state1->chain_name = "left_arm";
        state1->joint_positions = bad_left_arm_joint;
        check_states.push_back(state1);

        // Call collision detection interface
        auto res = planner.check_collision(check_states, true, custom_param);

        MotionStatus status = std::get<0>(res);
        std::vector<bool> collision_results = std::get<1>(res);

        std::cout << "Status: " << planner.status_to_string(status) << std::endl;

        if (status == MotionStatus::SUCCESS) {
            std::cout << "OK: collision check finished (false=no collision, true=collision):" << std::endl;
            for (size_t i = 0; i < collision_results.size(); ++i) {
                std::cout << "  - status [" << i << "]: " 
                          << (collision_results[i] ? "COLLISION" : "NO COLLISION") 
                          << std::endl;
            }
        } else {
            std::cerr << "ERROR: collision check returned failure." << std::endl;
        }

    } catch (const std::exception& e) {
        std::cerr << "ERROR: collision check exception: " << e.what() << std::endl;
    }

    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### Attach Tool (attach_tool)

**Applicable Scenarios**: Attach a tool (such as a gripper, suction cup, etc.) to the robot end effector, updating the motion planning model to account for tool mass and collision volume.

```cpp title="examples/cpp/galbot_motion/src/attach_tool_example.cpp"
#include <iostream>
#include <string>
#include <thread>
#include <chrono>
#include <stdexcept>

#include "galbot_motion.hpp"
#include "galbot_robot.hpp"

using namespace galbot::sdk;

int main() {

    auto& planner = GalbotMotion::get_instance(MachineType::G1);
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    if (!planner.init()) {
        std::cerr << "GalbotMotion initialization failed" << std::endl;
        return -1;
    }
    if (!robot.init()) {
        std::cerr << "GalbotRobot initialization failed" << std::endl;
        return -1;
    }

    // Program started, waiting for data
    std::this_thread::sleep_for(std::chrono::seconds(2));

    // --- Execute tool-attach operation ---
    try {
        std::string chain_name = "left_arm";
        std::string tool_name = "suction_cup";

        MotionStatus status = planner.attach_tool(chain_name, tool_name);

        std::cout << "Execution status feedback: " << planner.status_to_string(status) << std::endl;

        if (status == MotionStatus::SUCCESS) {
            std::cout << "✅ Tool attached successfully: " << tool_name << std::endl;
        } else {
            std::cerr << "❌ Tool attachment failed. Please check whether the tool name is defined in the configuration file." << std::endl;
        }

    } catch (const std::exception& e) {
        std::cerr << "❌ Exception occurred during runtime: " << e.what() << std::endl;
    }

    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();
    return 0;
}
```

### Detach Tool (detach_tool)

**Applicable Scenarios**: Remove an attached tool from the robot end effector, restoring the original robot model.

```cpp title="examples/cpp/galbot_motion/src/detach_tool_example.cpp"
#include <iostream>
#include <string>
#include <thread>
#include <chrono>
#include <stdexcept>

#include "galbot_motion.hpp"
#include "galbot_robot.hpp"

using namespace galbot::sdk;

int main() {

    auto& planner = GalbotMotion::get_instance(MachineType::G1);
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    if (!planner.init()) {
        std::cerr << "GalbotMotion initialization failed" << std::endl;
        return -1;
    }
    if (!robot.init()) {
        std::cerr << "GalbotRobot initialization failed" << std::endl;
        return -1;
    }

    // Program started, waiting for data
    std::this_thread::sleep_for(std::chrono::seconds(2));

    // --- Execute tool-detach operation ---
    try {
        std::string chain_name = "left_arm";
        MotionStatus status = planner.detach_tool(chain_name);

        std::cout << "Execution status feedback: " << planner.status_to_string(status) << std::endl;

        if (status == MotionStatus::SUCCESS) {
            std::cout << "✅ Tool detached successfully." << std::endl;
        } else {
            std::cerr << "❌ Tool detachment failed." << std::endl;
        }

    } catch (const std::exception& e) {
        std::cerr << "❌ Exception occurred during runtime: " << e.what() << std::endl;
    }

    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();
    return 0;
}
```

### Add/Remove Environment Collision Objects (env_collider_operation)

**Applicable Scenarios**: Add obstacles to the motion planning environment or remove added obstacles, enabling motion planning to account for environmental obstacles.

```cpp title="examples/cpp/galbot_motion/src/env_collider_operation_example.cpp"
#include <iostream>
#include <vector>
#include <string>
#include <array>
#include <thread>
#include <chrono>
#include <memory>
#include <stdexcept>

#include "galbot_motion.hpp"
#include "galbot_robot.hpp"

using namespace galbot::sdk;

/*
    NOTE:
    - GalbotMotion does NOT provide real-time obstacle perception / automatic environment updates today.
    - To make Motion collision checking consider environmental obstacles, you must load them manually
        (e.g., box/mesh/point_cloud via add_obstacle/attach_target_object).
    - Real-time perception / navigation-style obstacle updates in Motion is a planned future feature.
*/

int main() {
    auto& planner = GalbotMotion::get_instance(MachineType::G1);
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    if (!planner.init()) {
        std::cerr << "GalbotMotion init FAILED" << std::endl;
        return -1;
    }
    if (!robot.init()) {
        std::cerr << "GalbotRobot init FAILED" << std::endl;
        return -1;
    }
    
    std::this_thread::sleep_for(std::chrono::seconds(2));

    // Scenario 1: add a Box collision object into Motion environment.
    try {
        std::cout << ">> Scenario 1: add obstacle..." << std::endl;

        std::string obstacle_id = "box_test_1";
        std::string obj_type = "box";
        std::vector<double> obj_pose = {1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0};
        std::array<double, 3> obj_scale = {1.0, 1.0, 1.0};
        std::string target_frame = "world";

        MotionStatus status = planner.add_obstacle(
            obstacle_id,      // 1. ID
            obj_type,         // 2. Type
            obj_pose,         // 3. Pose
            obj_scale,        // 4. Scale (array)
            "",               // 5. key
            target_frame,     // 6. target_frame
            "",               // 7. ee_frame
            {},               // 8. ref_joints
            {},               // 9. ref_base
            {},               // 10. ignore_links
            0.0,              // 11. safe_margin
            0.0               // 12. resolution
        );

        std::cout << "Status: " << planner.status_to_string(status) << std::endl;
        
        planner.clear_obstacle();
        
        if (status == MotionStatus::SUCCESS) {
            std::cout << "OK: obstacle added" << std::endl;
        }
    } catch (const std::exception& e) { std::cerr << e.what() << std::endl; }

    // Scenario 2: add a duplicate ID (expected to fail).
    try {
        std::cout << "\n>> Scenario 2: test duplicate ID..." << std::endl;

        std::string obstacle_id = "box_test_2";
        std::string obj_type = "box";
        std::vector<double> obj_pose = {1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0};
        std::array<double, 3> obj_scale = {1.0, 1.0, 1.0};
        std::string target_frame = "world";

        // First addition
        planner.add_obstacle(obstacle_id, obj_type, obj_pose, obj_scale, "", target_frame, "", {}, {}, {}, 0.0, 0.0);

        // Second addition with same ID
        MotionStatus status = planner.add_obstacle(obstacle_id, obj_type, obj_pose, obj_scale, "", target_frame, "", {}, {}, {}, 0.0, 0.0);

        std::cout << "Status: " << planner.status_to_string(status) << std::endl;
        
        planner.clear_obstacle();

        if (status == MotionStatus::FAULT) {
            std::cout << "OK: duplicate ID rejected (expected)" << std::endl;
        }
    } catch (const std::exception& e) { std::cerr << e.what() << std::endl; }

    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();
    return 0;
}
```

## Class: GalbotNavigation

### Get Instance / Initialize (get_instance_init)

**Applicable Scenarios**: Get the navigation module singleton and initialize. Must be called before using navigation functions.

```cpp title="examples/cpp/galbot_navigation/src/get_instance_init_example.cpp"
#include "galbot_navigation.hpp"
#include "galbot_robot.hpp"

#include <iostream>
#include <string>
#include <vector>
#include <thread>
#include <thread>

using namespace galbot::sdk;

int main() {
    auto& navigation = GalbotNavigation::get_instance(MachineType::G1);
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize system
    if (!robot.init()) {
        std::cerr << "Base instance initialization failed!" << std::endl;
        return -1;
    }
    if (!navigation.init()) {
        std::cerr << "Navigation instance initialization failed!" << std::endl;
        return -1;
    }

    std::cout << "Initialization successful!" << std::endl;

    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### Relocalize / Is Localized / Get Current Pose (relocation)

**Applicable Scenarios**: Trigger relocalization, check if the robot is successfully localized, and get the robot's current pose in the map.

```cpp title="examples/cpp/galbot_navigation/src/relocation_example.cpp"
#include "galbot_navigation.hpp"
#include "galbot_robot.hpp"

#include <iostream>
#include <string>
#include <vector>
#include <thread>
#include <thread>

using namespace galbot::sdk;

int main() {
    auto& navigation = GalbotNavigation::get_instance(MachineType::G1);
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize system
    if (robot.init()) {
        std::cout << "Base instance initialized successfully!" << std::endl;
    } else {
        std::cerr << "Base instance initialization failed!" << std::endl;
        return -1;
    }
    if (navigation.init()) {
        std::cout << "Navigation instance initialized successfully!" << std::endl;
    } else {
        std::cerr << "Navigation instance initialization failed!" << std::endl;
        return -1;
    }

    Pose init_pose(std::vector<double>{0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0});

    // checkrelocalize success
    int count_relocalize = 0;
    while (!navigation.is_localized() && count_relocalize < 20) {
        navigation.relocalize(init_pose);
        std::this_thread::sleep_for(std::chrono::milliseconds(500));
        std::cout << "is relocalizing" << std::endl;
        count_relocalize++;
    }

    if (navigation.is_localized()) {
        std::cout << "relocalization success." << std::endl;

        // Get current pose
        Pose current_pose = navigation.get_current_pose();
        std::cout << "Current pose: Position(" << current_pose.position.x << ", "
                  << current_pose.position.y << ", " << current_pose.position.z
                  << "), orientation(" << current_pose.orientation.x << ", "
                  << current_pose.orientation.y << ", " << current_pose.orientation.z
                  << ", " << current_pose.orientation.w << ")" << std::endl;

        robot.request_shutdown();
        robot.wait_for_shutdown();
    } else {
        std::cout << "relocalization failed, cannot proceed with navigation." << std::endl;
    }

    robot.destroy();

    return 0;
}
```

### Check Path Reachability and Blocking Navigation to Goal (blocked_navigation)

**Applicable Scenarios**: Check if the target point is reachable, and if reachable, block and wait for navigation to complete reaching the target. Convenient for simple scenarios.

```cpp title="examples/cpp/galbot_navigation/src/blocked_navigation_example.cpp"
#include "galbot_navigation.hpp"
#include "galbot_robot.hpp"

#include <iostream>
#include <string>
#include <vector>
#include <thread>
#include <thread>

using namespace galbot::sdk;

int main() {
    auto& navigation = GalbotNavigation::get_instance(MachineType::G1);
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize system
    if (robot.init()) {
        std::cout << "Base instance initialized successfully!" << std::endl;
    } else {
        std::cerr << "Base instance initialization failed!" << std::endl;
        return -1;
    }
    if (navigation.init()) {
        std::cout << "Navigation instance initialized successfully!" << std::endl;
    } else {
        std::cerr << "Navigation instance initialization failed!" << std::endl;
        return -1;
    }
    auto res = robot.switch_controller(G1ControllerName::CHASSIS_POSE_CTRL);
    if (res != ControlStatus::SUCCESS) {
        std::cerr << "Failed to switch controller!" << std::endl;
        return -1;
    }
    Pose init_pose(std::vector<double>{0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0});
    Pose goal_pose(std::vector<double>{0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0});

    // checkrelocalize success
    int count_relocalize = 0;
    while (!navigation.is_localized() && count_relocalize < 20) {
        navigation.relocalize(init_pose);
        std::this_thread::sleep_for(std::chrono::milliseconds(500));
        std::cout << "is relocalizing" << std::endl;
        count_relocalize++;
    }

    if (navigation.is_localized()) {
        std::cout << "relocalization success." << std::endl;

        // Get current pose
        Pose current_pose = navigation.get_current_pose();
        std::cout << "Current pose: Position(" << current_pose.position.x << ", "
                << current_pose.position.y << ", " << current_pose.position.z
                << "), orientation(" << current_pose.orientation.x << ", "
                << current_pose.orientation.y << ", " << current_pose.orientation.z
                << ", " << current_pose.orientation.w << ")" << std::endl;

        std::this_thread::sleep_for(std::chrono::milliseconds(2000));

        // Whether to enable obstacle checking (can be set to true in open environments)
        bool enable_collision_check = false;
        // Whether to block and wait for arrival
        bool is_blocking = true;
        // Maximum wait time to reach position
        float timeout_s = 20;

        // Navigate 3 times in loop
        int count = 0;
        while (count++ < 3) {
            std::cout << "No. " << count << " navigation(s)" << std::endl;
            // checkpath navigation target
            if (navigation.check_path_reachability(goal_pose, init_pose)) {
                std::cout << "Path reachable, navigating to target point" << std::endl;
                NavigationStatus status = navigation.navigate_to_goal(
                    goal_pose, enable_collision_check, is_blocking, timeout_s);
                if (status == NavigationStatus::SUCCESS) {
                    std::cout << "Target point reached" << std::endl;
                } else {
                    std::cout << "navigationfailed, status: " << static_cast<int>(status) << std::endl;
                }
            } else {
                std::cout << "Path unreachable, cannot navigate to target point" << std::endl;
            }
            // Check path reachability and return to start point
            if (navigation.check_path_reachability(init_pose, goal_pose)) {
                std::cout << "Path reachable, navigating to start point" << std::endl;
                NavigationStatus status = navigation.navigate_to_goal(
                    init_pose, enable_collision_check, is_blocking, timeout_s);
                if (status == NavigationStatus::SUCCESS) {
                    std::cout << "Returned to start point" << std::endl;
                } else {
                    std::cout << "navigationfailed, status: " << static_cast<int>(status) << std::endl;
                }
            } else {
                std::cout << "Path unreachable, cannot navigate to start point" << std::endl;
            }
        }

        // Stop navigation
        navigation.stop_navigation();

        // Get current pose again
        current_pose = navigation.get_current_pose();
        std::cout << "Current pose: Position(" << current_pose.position.x << ", "
                << current_pose.position.y << ", " << current_pose.position.z
                << "), orientation(" << current_pose.orientation.x << ", "
                << current_pose.orientation.y << ", " << current_pose.orientation.z
                << ", " << current_pose.orientation.w << ")" << std::endl;

    } else {
        std::cout << "relocalization failed." << std::endl;
    }


    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### Non-blocking Navigation + Polling for Arrival (non_blocking_navigation)

**Applicable Scenarios**: Start navigation without blocking the current thread, allowing other processing during navigation, and need to poll to determine if the target has been reached. Suitable for scenarios requiring asynchronous processing.

```cpp title="examples/cpp/galbot_navigation/src/non_blocking_navigation_example.cpp"
#include "galbot_navigation.hpp"
#include "galbot_robot.hpp"

#include <iostream>
#include <string>
#include <vector>
#include <thread>
#include <thread>

using namespace galbot::sdk;

int main() {
    auto& navigation = GalbotNavigation::get_instance(MachineType::G1);
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize system
    if (robot.init()) {
        std::cout << "Base instance initialized successfully!" << std::endl;
    } else {
        std::cerr << "Base instance initialization failed!" << std::endl;
        return -1;
    }
    if (navigation.init()) {
        std::cout << "Navigation instance initialized successfully!" << std::endl;
    } else {
        std::cerr << "Navigation instance initialization failed!" << std::endl;
        return -1;
    }

    auto res = robot.switch_controller(G1ControllerName::CHASSIS_POSE_CTRL);
    if (res != ControlStatus::SUCCESS) {
        std::cerr << "Failed to switch controller!" << std::endl;
        return -1;
    }

    Pose init_pose(std::vector<double>{0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0});
    Pose goal_pose(std::vector<double>{0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0});

    // checkrelocalize success
    int count_relocalize = 0;
    while (!navigation.is_localized() && count_relocalize < 20) {
        navigation.relocalize(init_pose);
        std::this_thread::sleep_for(std::chrono::milliseconds(5000));
        std::cout << "is relocalizing" << std::endl;
        count_relocalize++;
    }
    if (navigation.is_localized()) {
        std::cout << "relocalization success." << std::endl;

        // Get current pose
        Pose current_pose = navigation.get_current_pose();
        std::cout << "Current pose: Position(" << current_pose.position.x << ", "
                << current_pose.position.y << ", " << current_pose.position.z
                << "), orientation(" << current_pose.orientation.x << ", "
                << current_pose.orientation.y << ", " << current_pose.orientation.z
                << ", " << current_pose.orientation.w << ")" << std::endl;

        std::this_thread::sleep_for(std::chrono::milliseconds(2000));

        // Whether to enable obstacle checking (can be set to true in open environments)
        bool enable_collision_check = false;
        // Whether to block and wait for arrival
        bool is_blocking = false;

        // Navigate 2 times in loop, non-blocking wait for arrival
        int count = 0;
        while (count++ < 2) {
            std::cout << "No. " << count << " navigation(s)" << std::endl;
            // checkpath navigation target
            if (navigation.check_path_reachability(goal_pose, init_pose)) {
                std::cout << "Path reachable, navigating to target point" << std::endl;
                NavigationStatus status = navigation.navigate_to_goal(
                    goal_pose, enable_collision_check, is_blocking);
                // wait
                int count_arrival = 0;
                while (!navigation.check_goal_arrival()) {
                    std::cout << "navigate has not arrived" << std::endl;
                    std::this_thread::sleep_for(std::chrono::milliseconds(500));
                    if (++count_arrival > 10) {
                        break;
                    }
                }
                if (navigation.check_goal_arrival()) {
                    std::cout << "Target point reached" << std::endl;
                } else {
                    std::cout << "Navigation failed; target point not reached" << std::endl;
                }
            } else {
                std::cout << "Path unreachable, cannot navigate to target point" << std::endl;
            }
            // Check path reachability and return to start point
            if (navigation.check_path_reachability(init_pose, goal_pose)) {
                std::cout << "Path reachable, navigating to start point" << std::endl;
                NavigationStatus status = navigation.navigate_to_goal(
                    init_pose, enable_collision_check, is_blocking);
                // wait
                int count_arrival = 0;
                while (!navigation.check_goal_arrival()) {
                    std::cout << "navigate has not arrived" << std::endl;
                    std::this_thread::sleep_for(std::chrono::milliseconds(1000));
                    if (++count_arrival > 10) {
                        break;
                    }
                }
                if (navigation.check_goal_arrival()) {
                    std::cout << "Target point reached" << std::endl;
                } else {
                    std::cout << "Navigation failed; target point not reached" << std::endl;
                }
            } else {
                std::cout << "Path unreachable, cannot navigate to start point" << std::endl;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(1000));
        }

        // Stop navigation
        navigation.stop_navigation();

        // Get current pose
        current_pose = navigation.get_current_pose();
        std::cout << "Current pose: Position(" << current_pose.position.x << ", "
                << current_pose.position.y << ", " << current_pose.position.z
                << "), orientation(" << current_pose.orientation.x << ", "
                << current_pose.orientation.y << ", " << current_pose.orientation.z
                << ", " << current_pose.orientation.w << ")" << std::endl;
    } else {
        std::cout << "relocalization failed, cannot proceed with navigation." << std::endl;
    }
    
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

### Get Navigation Status + Polling for SUCCESS/FAILED or Timeout (get_navigation_status_example)

**Applicable Scenarios**: Get the execution status of the current navigation task, used for polling in non-blocking navigation.

```cpp title="examples/cpp/galbot_navigation/src/get_navigation_status_example.cpp"
/**
 * example: navigation get_navigation_status, SUCCESS/FAILED timeout exit,
 * Avoid deadlock and execute error logic.
 */
#include "galbot_navigation.hpp"
#include "galbot_robot.hpp"

#include <chrono>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

using namespace galbot::sdk;

int main() {
    auto& navigation = GalbotNavigation::get_instance(MachineType::G1);
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    if (!robot.init()) {
        std::cerr << "Base instance initialization failed!" << std::endl;
        return -1;
    }
    if (!navigation.init()) {
        std::cerr << "Navigation instance initialization failed!" << std::endl;
        return -1;
    }
    auto res = robot.switch_controller(G1ControllerName::CHASSIS_POSE_CTRL);
    if (res != ControlStatus::SUCCESS) {
        std::cerr << "Failed to switch controller!" << std::endl;
        return -1;
    }
    Pose goal_pose(std::vector<double>{0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0});
    const double timeout_s = 20.0;
    const double poll_interval_s = 0.5;

    // Non-blocking navigation
    navigation.navigate_to_goal(goal_pose, true, false, static_cast<float>(timeout_s));
    auto start = std::chrono::steady_clock::now();

    while (true) {
        NavigationTaskStatus status = navigation.get_navigation_status();
        auto elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();

        if (status == NavigationTaskStatus::SUCCESS) {
            std::cout << "Target reached" << std::endl;
            break;
        }
        if (status == NavigationTaskStatus::FAILED) {
            std::cout << "Navigation failed; exit error-handling logic promptly" << std::endl;
            break;
        }
        if (elapsed >= timeout_s) {
            std::cout << "navigationtimeout, exit" << std::endl;
            break;
        }

        if (status == NavigationTaskStatus::RUNNING) {
            std::cout << "Navigating... Status: RUNNING, elapsed: " << elapsed << "s" << std::endl;
        } else {
            std::cout << "Status: UNKNOWN, : " << elapsed << "s" << std::endl;
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(static_cast<int>(poll_interval_s * 1000)));
    }

    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();
    std::cout << "Resources released successfully" << std::endl;
    return 0;
}
```

### Move Straight to Goal / Stop Navigation (linear_movement)

**Applicable Scenarios**: Move the robot in a straight line to the target point, or stop the currently ongoing navigation task.

```cpp title="examples/cpp/galbot_navigation/src/linear_movement_example.cpp"
#include "galbot_navigation.hpp"
#include "galbot_robot.hpp"

#include <iostream>
#include <string>
#include <vector>
#include <thread>
#include <chrono>
#include <iomanip>
#include <sstream>

using namespace galbot::sdk;

// Helper function: get current time string [HH:MM:SS.ms]
std::string get_timestamp() {
    auto now = std::chrono::system_clock::now();
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()) % 1000;
    std::time_t t = std::chrono::system_clock::to_time_t(now);
    std::tm tm = *std::localtime(&t);

    std::stringstream ss;
    ss << "[" << std::put_time(&tm, "%H:%M:%S") << "." 
       << std::setfill('0') << std::setw(3) << ms.count() << "] ";
    return ss.str();
}

int main() {
    auto& navigation = GalbotNavigation::get_instance(MachineType::G1);
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize system
    std::cout << get_timestamp() << "Starting call to robot.init()..." << std::endl;
    if (robot.init()) {
        std::cout << get_timestamp() << "Base instance initialized successfully!" << std::endl;
    } else {
        std::cerr << get_timestamp() << "Base instance initialization failed!" << std::endl;
        return -1;
    }

    std::cout << get_timestamp() << "Starting call to navigation.init()..." << std::endl;
    if (navigation.init()) {
        std::cout << get_timestamp() << "Navigation instance initialized successfully!" << std::endl;
    } else {
        std::cerr << get_timestamp() << "Navigation instance initialization failed!" << std::endl;
        return -1;
    }

    auto res = robot.switch_controller(G1ControllerName::CHASSIS_POSE_CTRL);
    if (res != ControlStatus::SUCCESS) {
        std::cerr << "Failed to switch controller!" << std::endl;
        return -1;
    }
    Pose init_pose(std::vector<double>{0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0});
    Pose goal_pose(std::vector<double>{0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0});

    // checkrelocalize success
    std::cout << get_timestamp() << "Enter relocalization check loop..." << std::endl;
    int count_relocalize = 0;
    while (!navigation.is_localized() && count_relocalize < 20) {
        std::cout << get_timestamp() << "Calling navigation.relocalize()..." << std::endl;
        navigation.relocalize(init_pose);
        std::this_thread::sleep_for(std::chrono::milliseconds(500));
        std::cout << get_timestamp() << "is relocalizing" << std::endl;
        count_relocalize++;
    }

    if (navigation.is_localized()) {
        std::cout << get_timestamp() << "relocalization success." << std::endl;

        // Get current pose
        std::cout << get_timestamp() << "Calling navigation.get_current_pose()..." << std::endl;
        Pose current_pose = navigation.get_current_pose();
        std::cout << get_timestamp() << "Current pose: Position(" << current_pose.position.x << ", "
                << current_pose.position.y << ", " << current_pose.position.z
                << "), orientation(" << current_pose.orientation.x << ", "
                << current_pose.orientation.y << ", " << current_pose.orientation.z
                << ", " << current_pose.orientation.w << ")" << std::endl;

        // Whether to block and wait for arrival
        bool is_blocking = true;
        // Maximum wait time to reach position
        float timeout_s = 20;

        // --- ---
        std::cout << "--------------------------------------------------" << std::endl;
        std::cout << get_timestamp() << "Preparing to execute move_straight_to (linear movement)..." << std::endl;
        
        // Record start time
        auto start_move = std::chrono::system_clock::now();
        
        // Execute move
        NavigationStatus status = navigation.move_straight_to(goal_pose, is_blocking, timeout_s);
        
        // Record end time and calculate elapsed time
        auto end_move = std::chrono::system_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_move - start_move).count();

        if (status == NavigationStatus::SUCCESS) {
            std::cout << get_timestamp() << "Target point reached (elapsed: " << duration << "ms)" << std::endl;
        } else {
            std::cout << get_timestamp() << "navigationfailed, status: " << static_cast<int>(status) 
                    << " (elapsed: " << duration << "ms)" << std::endl;
        }
        std::cout << "--------------------------------------------------" << std::endl;

        // Stop navigation
        std::cout << get_timestamp() << "Calling navigation.stop_navigation()..." << std::endl;
        navigation.stop_navigation();

        // Get current pose again
        std::cout << get_timestamp() << "Calling navigation.get_current_pose()..." << std::endl;
        current_pose = navigation.get_current_pose();
        std::cout << get_timestamp() << "Current pose: Position(" << current_pose.position.x << ", "
                << current_pose.position.y << ", " << current_pose.position.z
                << "), orientation(" << current_pose.orientation.x << ", "
                << current_pose.orientation.y << ", " << current_pose.orientation.z
                << ", " << current_pose.orientation.w << ")" << std::endl;
    } else {
        std::cout << get_timestamp() << "Relocalization failed, cannot continue navigation." << std::endl;
    }
    
    std::cout << get_timestamp() << "Executing shutdown..." << std::endl;
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();
    std::cout << get_timestamp() << "Program finished." << std::endl;

    return 0;
}
```

### Complete Running Example (Simple Workflow) (complete_running_example)

**Applicable Scenarios**: Demonstrates the complete usage workflow of navigation functionality, including initialization, relocalization, navigation to target and other steps for reference.

```cpp title="examples/cpp/galbot_navigation/src/complete_running_example.cpp"
#include "galbot_navigation.hpp"
#include "galbot_robot.hpp"

#include <iostream>
#include <string>
#include <vector>
#include <thread>
#include <thread>

using namespace galbot::sdk;

int main() {
    auto& navigation = GalbotNavigation::get_instance(MachineType::G1);
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize system
    if (!robot.init()) {
        std::cerr << "Base instance initialization failed!" << std::endl;
        return -1;
    }
    if (!navigation.init()) {
        std::cerr << "Navigation instance initialization failed!" << std::endl;
        return -1;
    }

    auto res = robot.switch_controller(G1ControllerName::CHASSIS_POSE_CTRL);
    if (res != ControlStatus::SUCCESS) {
        std::cerr << "Failed to switch controller!" << std::endl;
        return -1;
    }
    Pose init_pose(std::vector<double>{0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0});
    Pose goal_pose(std::vector<double>{0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0});

    // checkrelocalize success
    int count_relocalize = 0;
    while (!navigation.is_localized() && count_relocalize < 20) {
        navigation.relocalize(init_pose);
        std::this_thread::sleep_for(std::chrono::milliseconds(500));
        std::cout << "is relocalizing" << std::endl;
        count_relocalize++;
    }

    if (navigation.is_localized()) {
        std::cout << "Relocalization successful!" << std::endl;

        // Get current pose
        Pose current_pose = navigation.get_current_pose();
        std::cout << "Current pose: Position(" << current_pose.position.x << ", "
                << current_pose.position.y << ", " << current_pose.position.z
                << "), orientation(" << current_pose.orientation.x << ", "
                << current_pose.orientation.y << ", " << current_pose.orientation.z
                << ", " << current_pose.orientation.w << ")" << std::endl;

        // Whether to enable obstacle checking (can be set to true in open environments)
        bool enable_collision_check = false;
        // Whether to block and wait for arrival
        bool is_blocking = true;
        // Maximum wait time to reach position
        float timeout_s = 20;

        // checkpath navigation target
        if (navigation.check_path_reachability(goal_pose, init_pose)) {
            std::cout << "Path reachable, navigating to target point" << std::endl;
            // navigation, obstaclecheck, wait, wait 20
            NavigationStatus status = navigation.navigate_to_goal(
                goal_pose, enable_collision_check, is_blocking, timeout_s);
            if (status == NavigationStatus::SUCCESS) {
                std::cout << "Target point reached" << std::endl;
            } else {
                std::cout << "navigationfailed, status: " << static_cast<int>(status) << std::endl;
            }
        } else {
            std::cout << "Path unreachable, cannot navigate to target point" << std::endl;
        }

        // Check path reachability and return to start point
        if (navigation.check_path_reachability(init_pose, goal_pose)) {
            std::cout << "Path reachable, navigating to start point" << std::endl;
            // Navigate to the target waypoint with obstacle checking disabled and non-blocking wait for arrival
            is_blocking = false;
            NavigationStatus status = navigation.navigate_to_goal(
                init_pose, enable_collision_check, is_blocking);
            // wait
            int count_arrival = 0;
            while (!navigation.check_goal_arrival()) {
                std::cout << "navigate has not arrived" << std::endl;
                std::this_thread::sleep_for(std::chrono::milliseconds(1000));
                if (++count_arrival > 10) {
                    break;
                }
            }
            if (navigation.check_goal_arrival()) {
                std::cout << "Target point reached" << std::endl;
            } else {
                std::cout << "Navigation failed; target point not reached" << std::endl;
            }
        } else {
            std::cout << "Path unreachable, cannot navigate to start point" << std::endl;
        }

        // checkpath navigation target
        if (navigation.check_path_reachability(goal_pose, init_pose)) {
            std::cout << "Path reachable, navigating to target point" << std::endl;
            // target, wait, wait 10
            is_blocking = true;
            NavigationStatus status = navigation.move_straight_to(
                goal_pose, is_blocking, timeout_s);

            if (status == NavigationStatus::SUCCESS) {
                std::cout << "Target point reached" << std::endl;
            } else {
                std::cout << "navigationfailed, status: " << static_cast<int>(status) << std::endl;
            }
        } else {
            std::cout << "Path unreachable, cannot navigate to target point" << std::endl;
        }

        // Stop navigation
        navigation.stop_navigation();

    } else {
        std::cout << "Relocalization failed!" << std::endl;
    }


    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

## Class: GalbotPerception

### Foundation Stereo: single run_once and save a colorized depth image

**Applicable scenarios**: Trigger a single stereo depth estimation inference and retrieve the result.

```cpp title="examples/cpp/galbot_perception/src/foundation_stereo_run_once_example.cpp"
/**
 * Foundation stereo depth example: single run_once + wait_for_new_result to fetch one inference result.
 */

#include <iostream>
#include <thread>
#include <chrono>

#include "galbot_robot.hpp"
#include "galbot_perception.hpp"
#include "galbot_sdk_type.hpp"
#include "opencv2/opencv.hpp"

using namespace galbot::sdk;

bool run_foundation_stereo_once(GalbotPerception& perception) {
    if (!perception.run_once(PerceptionModule::FOUNDATION_STEREO)) {
        std::cerr << "run_once failed to send command" << std::endl;
        return false;
    }

    std::cout << "Waiting for inference result..." << std::endl;
    if (!perception.wait_for_new_result(PerceptionModule::FOUNDATION_STEREO, 5.0)) {
        std::cerr << "Timed out waiting for inference result" << std::endl;
        return false;
    }

    DetectionResult result;
    if (!perception.get_latest_result(PerceptionModule::FOUNDATION_STEREO, result)) {
        std::cerr << "get_latest_result failed" << std::endl;
        return false;
    }

    if (!result.instanceMask.empty()) {
        cv::Mat depth_map = result.instanceMask;
        std::cout << "Depth map size: " << depth_map.cols << "x" << depth_map.rows
                << ", type: " << depth_map.type() << std::endl;

        double min_val, max_val;
        cv::minMaxLoc(depth_map, &min_val, &max_val);
        std::cout << "Depth value range: [" << min_val << ", " << max_val << "]" << std::endl;

        cv::Mat depth_f;
        depth_map.convertTo(depth_f, CV_32F);
        cv::Mat mask = (depth_f > 0);

        cv::Mat normalized;
        cv::normalize(depth_f, normalized, 0, 255, cv::NORM_MINMAX, CV_8UC1, mask);

        cv::Mat colored;
        cv::applyColorMap(normalized, colored, cv::COLORMAP_TURBO);

        cv::imwrite("foundation_stereo_depth.jpg", colored);
        std::cout << "Depth map saved to foundation_stereo_depth.jpg" << std::endl;
    } else {
        std::cout << "No depth map (instanceMask is empty)" << std::endl;
    }

    return true;
}

int main() {
    auto& robot = GalbotRobot::get_instance(MachineType::G1);
    robot.init();

    auto& perception = GalbotPerception::get_instance(MachineType::G1);
    perception.init({PerceptionModule::FOUNDATION_STEREO});

    // Wait for perception models to load
    std::this_thread::sleep_for(std::chrono::seconds(12));
    std::cout << "Init OK, sending single inference request..." << std::endl;

    run_foundation_stereo_once(perception);

    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
```

## Class: Parameter

### Create and Use `Parameter` (parameter_use)

**Applicable Scenarios**: Create a motion planning parameter object used to configure various parameters for motion planning such as velocity limits, acceleration limits, planning time, etc.

```cpp title="examples/cpp/galbot_motion/src/parameter_use_example.cpp"
#include <iostream>
#include <vector>
#include <string>
#include <memory>

#include "galbot_motion.hpp"

using namespace galbot::sdk;

int main() {
    // Create Parameter via constructor and set options
    auto p = std::make_shared<Parameter>();

    p->set_blocking(true);            // Set whether to block execution
    p->set_check_collision(false);     // Disable collision detection
    p->set_timeout(5.0);              // Set timeout (seconds)
    p->set_actuate("with_chain_only");// Set drive mode
    p->set_tool_pose(false);           // Whether to consider tool pose
    p->set_reference_frame("base_link");

    std::cout << "--- Parameter p ---" << std::endl;
    std::cout << "blocking: " << (p->get_blocking() ? "True" : "False") << std::endl;
    std::cout << "collision check: " << (p->get_check_collision() ? "True" : "False") << std::endl;
    std::cout << "timeout: " << p->get_timeout() << "s" << std::endl;

    return 0;
}
```

## Utility Functions

### status_to_string / JointStates / PoseState (auxi_fun_use)

**Applicable Scenarios**: Demonstrates how to use utility functions to convert status to strings, create joint state and pose state objects.

```cpp title="examples/cpp/galbot_motion/src/function_use_example.cpp"
#include <iostream>
#include <string>

#include "galbot_motion.hpp"

using namespace galbot::sdk;

int main() {

    auto& planner = GalbotMotion::get_instance(MachineType::G1);

    MotionStatus status = MotionStatus::SUCCESS;
    std::string status_str = planner.status_to_string(status);
    
    std::cout << "MotionStatus string: " << status_str << std::endl;

    auto js = std::make_shared<JointStates>();
    auto ps = std::make_shared<PoseState>();

    js->chain_name = "left_arm";
    js->joint_positions = std::vector<double>(7, 0.0); 

    ps->chain_name = "left_arm";
    ps->pose = Pose(std::vector<double>{1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0});
    ps->reference_frame = "base_link"; 
    ps->frame_id = "EndEffector";

    std::cout << "--- JointStates ---" << std::endl;
    std::cout << "Type: " << typeid(*js).name() << std::endl; // Print class name
    std::cout << "Chain Name: " << js->chain_name << std::endl;
    std::cout << "Joints size: " << js->joint_positions.size() << std::endl;

    std::cout << "\n--- PoseState ---" << std::endl;
    std::cout << "Type: " << typeid(*ps).name() << std::endl;
    std::cout << "Chain Name: " << ps->chain_name << std::endl;
    std::cout << "Pose Z: " << ps->pose.position.z << std::endl;

    return 0;
}
```
