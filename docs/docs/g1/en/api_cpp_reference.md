# CPP API Reference - G1 Machine

- **[GalbotRobot](#module-galbotrobot)**: Core robot control module. Use this for robot connection, lifecycle management, joint control, sensor data queries, and hardware state monitoring.
- **[GalbotMotion](#module-galbotmotion)**: Motion planning and execution module. Use this for Cartesian/joint space movements, trajectory planning, inverse kinematics, and whole-body control.
- **[GalbotNavigation](#module-galbotnavigation)**: Mobile navigation module. Use this for mobile base localization, mapping, path planning, and autonomous movement.
- **[GalbotPerception](#module-galbotperception)**: On-device perception (G1 only). Load vision models, run inference, and read structured results such as stereo depth; use together with GalbotRobot sensor APIs.
- **[Types & Enums](#module-types-enums)**: Data structures, enums, and status types. Use this section to look up type definitions, sensor types, error codes, and state structures used by other modules.

---

<a id="module-galbotrobot"></a>

## GalbotRobot {#galbotrobot-class}

<small>Main robot control interface for Galbot humanoid robot.

This class provides a singleton interface for controlling the Galbot robot. It supports: Joint position and trajectory control End-effector control (grippers and suction cups) Mobile base velocity control Sensor data acquisition (IMU, cameras, LiDAR, ultrasonic) Coordinate frame transformations System lifecycle management Use [GalbotRobot](#galbotrobot-class)::get_instance([MachineType](#galbot-sdk-machinetype-enum)) to obtain a reference for a specific platform (G1/S1). All angles are in radians unless otherwise specified. All linear distances are in meters unless otherwise specified. All timestamps are in nanoseconds unless otherwise specified.</small>

### ~GalbotRobot {#galbotrobot-galbotrobot-function}

```cpp
virtual galbot::sdk::GalbotRobot::~GalbotRobot()=default
```

### init {#galbotrobot-init-function}

```cpp
virtual bool galbot::sdk::GalbotRobot::init(const std::unordered_set< SensorType > &enable_sensor_set={})=0
```

<small>Initialize the robot control system.

Initializes the robot hardware communication, middleware, and sensor interfaces. To optimize resource usage, only sensors specified in the enable_sensor_set will be initialized and available for data reading.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `enable_sensor_set` | const std::unordered_set< [SensorType](#galbot-sdk-sensortype-enum) > & | Set of sensors to enable. If empty, a default set of sensors will be enabled. Specify only required sensors to reduce computational overhead and memory consumption. |

**Returns**

| Type | Description |
| --- | --- |
| bool | true if initialization succeeded |

### PublishTarget {#galbotrobot-publishtarget-function}

```cpp
virtual ControlStatus galbot::sdk::GalbotRobot::PublishTarget(const SingoriXTarget &target)=0
```

<small>Publish a raw target without waiting for a service response.

This is the lightweight high-frequency path for advanced users who want to construct a [SingoriXTarget](#singorixtarget-struct) directly and send it through the WBC publish channel. The SDK performs only basic structural validation before publishing.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `target` | const [SingoriXTarget](#singorixtarget-struct) & | SDK mirror of singorix target data |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#galbot-sdk-controlstatus-enum) | [ControlStatus](#galbot-sdk-controlstatus-enum) indicating local validation / publish result |

### RequestTarget {#galbotrobot-requesttarget-function}

```cpp
virtual std::shared_ptr<ErrorInfo> galbot::sdk::GalbotRobot::RequestTarget(const SingoriXTarget &target)=0
```

<small>Request execution of a raw target and receive the service response.

This is the request/service path for advanced users who want direct target control with request-side error screening and a returned error payload. The SDK uses the middleware default timeout configured by the underlying client.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `target` | const [SingoriXTarget](#singorixtarget-struct) & | SDK mirror of singorix target data |

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [ErrorInfo](#errorinfo-struct) > | Shared pointer to on local pre-check failure or service response. Returns nullptr when the client is unavailable, disconnected, times out, or returns an empty response. |

### set_joint_commands {#galbotrobot-set_joint_commands-function}

```cpp
virtual ControlStatus galbot::sdk::GalbotRobot::set_joint_commands(
    const std::vector< JointCommand > &joint_commands,
    const std::vector< std::string > &joint_groups={},
    const std::vector< std::string > &joint_names={},
    const double time_from_start_s=10
) =0
```

<small>Set low-level joint commands for high-frequency streaming control.

Suitable for high-frequency command streaming (for example, per-frame model inference output).

This API does not interpolate from the current/start position to the first target. The controller drives joints toward each commanded target as quickly as possible to satisfy time_from_start_s (expected arrival time).

For standard joints (head, legs, arms), only [JointCommand](#jointcommand-struct)::position is effective in current versions; velocity, acceleration, and effort are currently ignored.

For gripper joints, the position field represents gripper width and both velocity and effort fields are supported and effective. Gripper motion uses whichever is slower between the specified velocity and time_from_start_s. Therefore, when setting the gripper velocity, time_from_start_s can be set to 0 (fastest arrival), and the gripper will be controlled directly by the specified velocity.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `joint_commands` | const std::vector< [JointCommand](#jointcommand-struct) > & | Vector of low-level joint commands. |
| `joint_groups` | const std::vector< std::string > & | Joint groups to control. Supported groups: legs, head, left_arm, right_arm, gripper, suction_cup. Empty vector defaults to all body joints (legs, head, left_arm, right_arm). |
| `joint_names` | const std::vector< std::string > & | Specific joint names to control. This parameter takes precedence over joint_groups. When provided, joint_groups is ignored. |
| `time_from_start_s` | const double | Expected arrival time (seconds) for the target command. |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#galbot-sdk-controlstatus-enum) | [ControlStatus](#galbot-sdk-controlstatus-enum) indicating success or failure of command transmission. |

!!! warning
    Especially on the first command, avoid a large gap between current and target joint angles. Large jumps may cause excessively fast motion and safety risk.

### set_joint_positions {#galbotrobot-set_joint_positions-function}

```cpp
virtual ControlStatus galbot::sdk::GalbotRobot::set_joint_positions(
    const std::vector< double > &joint_positions,
    const std::vector< std::string > &joint_groups={},
    const std::vector< std::string > &joint_names={},
    const bool is_blocking=true,
    const double speed_rad_s=0.2,
    const double timeout_s=15
) =0
```

<small>Set target joint positions for specified joint groups by name (for low-frequency keyframe/posture transitions)

Commands the robot to move specified joints to target positions. The motion is executed as a smooth trajectory with configurable speed limits.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `joint_positions` | const std::vector< double > & | Vector of target joint angles in radians. The order must match the joint ordering returned by get_joint_names() for the specified joint_groups or joint_names. |
| `joint_groups` | const std::vector< std::string > & | Joint group names to control. Supported groups: "legs", "head", "left_arm", "right_arm". Empty vector defaults to all body joints (legs, head, left_arm, right_arm). |
| `joint_names` | const std::vector< std::string > & | Specific joint names to control. This parameter takes precedence over joint_groups. When provided, joint_groups is ignored. |
| `is_blocking` | const bool | If true, blocks until motion completes or timeout occurs. If false, returns immediately after command is sent. |
| `speed_rad_s` | const double | Maximum joint angular velocity in radians per second (rad/s). Default: 0.2 rad/s. |
| `timeout_s` | const double | Maximum blocking wait time in seconds. Returns immediately upon timeout regardless of execution completion. Default: 15 seconds. |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#galbot-sdk-controlstatus-enum) | [ControlStatus](#galbot-sdk-controlstatus-enum) indicating success or failure of the motion command |

!!! warning
    This API is not suitable for high-frequency frame-by-frame model inference control. Each call creates a new interpolation goal, and continuous calls can cause lag or discontinuous motion. If your task is model-inference command streaming, use set_joint_commands or set_joint_commands_batch instead.

### check_trajectory_execution_status {#galbotrobot-check_trajectory_execution_status-function}

```cpp
virtual std::vector<TrajectoryControlStatus> galbot::sdk::GalbotRobot::check_trajectory_execution_status(
    std::vector< std::string > joint_groups
) =0
```

<small>Get trajectory execution status for specified joint groups.

Queries the current execution status of trajectories for the specified joint groups. This is useful for monitoring trajectory progress in non-blocking execution mode.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `joint_groups` | std::vector< std::string > | Vector of joint group names to query |

**Returns**

| Type | Description |
| --- | --- |
| std::vector< [TrajectoryControlStatus](#galbot-sdk-trajectorycontrolstatus-enum) > | Vector of [TrajectoryControlStatus](#galbot-sdk-trajectorycontrolstatus-enum) indicating execution state for each group |

### execute_joint_trajectory {#galbotrobot-execute_joint_trajectory-function}

```cpp
virtual ControlStatus galbot::sdk::GalbotRobot::execute_joint_trajectory(
    Trajectory trajectory,
    bool is_blocking=true
) =0
```

<small>Execute a pre-planned joint trajectory.

Executes a trajectory consisting of waypoints with associated joint positions, velocities, and timing information. The trajectory controller interpolates between waypoints to generate smooth motion.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `trajectory` | [Trajectory](#trajectory-struct) | [Trajectory](#trajectory-struct) data structure containing waypoints and timing |
| `is_blocking` | bool | If true, blocks until trajectory execution completes. If false, returns immediately after trajectory is submitted. |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#galbot-sdk-controlstatus-enum) | [ControlStatus](#galbot-sdk-controlstatus-enum) indicating success or failure of trajectory execution/submission |

!!! warning
    For per-frame model inference output, prefer command streaming interfaces (set_joint_commands / set_joint_commands_batch) rather than repeatedly re-submitting full trajectories.

### set_joint_commands_batch {#galbotrobot-set_joint_commands_batch-function}

```cpp
virtual ControlStatus galbot::sdk::GalbotRobot::set_joint_commands_batch(const Trajectory &trajectory)=0
```

<small>Set joint commands in batch mode (non-blocking)

Sets multiple joint command trajectory points in real-time control mode, supporting one-time submission of trajectory control commands for multiple time points. Provides a non-blocking high-frequency trajectory execution interface. Similar to set_joint_commands but supports batch trajectory control, suitable for scenarios such as VLA inference batch output.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `trajectory` | const [Trajectory](#trajectory-struct) & | [Trajectory](#trajectory-struct) data structure containing waypoints with joint commands. Each [TrajectoryPoint](#trajectorypoint-struct) contains time_from_start and a list of [JointCommand](#jointcommand-struct). [JointCommand](#jointcommand-struct) includes position (rad), velocity (rad/s), acceleration (rad/s²), effort (N·m), Kp (position gain), and Kd (velocity gain). |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#galbot-sdk-controlstatus-enum) | [ControlStatus](#galbot-sdk-controlstatus-enum) indicating success or failure of command submission. Returns immediately without waiting for execution completion (non-blocking). |

### set_suction_cup_command {#galbotrobot-set_suction_cup_command-function}

```cpp
virtual ControlStatus galbot::sdk::GalbotRobot::set_suction_cup_command(
    const std::string &end_effector,
    bool activate
) =0
```

<small>Control suction cup activation state.

Activates or deactivates the specified suction cup end-effector.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `end_effector` | const std::string & | Joint group name specifying which suction cup to control (e.g., "left_suction_cup", "right_suction_cup") |
| `activate` | bool | If true, activates vacuum suction. If false, releases suction. |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#galbot-sdk-controlstatus-enum) | [ControlStatus](#galbot-sdk-controlstatus-enum) indicating success or failure of command transmission  |

**Supported:** G1

### set_gripper_command {#galbotrobot-set_gripper_command-function}

```cpp
virtual ControlStatus galbot::sdk::GalbotRobot::set_gripper_command(
    const std::string &end_effector,
    double width_m,
    double velocity_mps=0.03,
    double effort=30,
    bool is_blocking=true
) =0
```

<small>Control gripper opening width and force.

Commands the gripper to move to a specified opening width with controlled velocity and maximum gripping force.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `end_effector` | const std::string & | Joint group name specifying which gripper to control (e.g., "left_gripper", "right_gripper") |
| `width_m` | double | Target gripper opening width in meters (m), measured between the inner surfaces of the gripper fingers. |
| `velocity_mps` | double | Gripper closing/opening velocity in meters per second (m/s). Default: 0.03 m/s. |
| `effort` | double | Maximum gripping force in Newton-meters (N·m). This limits the torque applied to prevent damage to grasped objects. Default: 30 N·m. |
| `is_blocking` | bool | If true, blocks until gripper reaches target position or times out. If false, returns immediately after command is sent. |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#galbot-sdk-controlstatus-enum) | [ControlStatus](#galbot-sdk-controlstatus-enum) indicating success or failure of gripper command |

### get_gripper_state {#galbotrobot-get_gripper_state-function}

```cpp
virtual std::shared_ptr<GripperState> galbot::sdk::GalbotRobot::get_gripper_state(
    const std::string &end_effector
) =0
```

<small>Get current gripper state.

Retrieves the current state of the specified gripper, including position, velocity, force, and motion-state estimation.

[GripperState](#gripperstate-struct)::is_moving is window-based: if no effective width change is detected within the internal time window, is_moving becomes false.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `end_effector` | const std::string & | Joint group name specifying which gripper to query (e.g., "left_gripper", "right_gripper") |

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [GripperState](#gripperstate-struct) > | Shared pointer to , or nullptr if retrieval fails |

### get_suction_cup_state {#galbotrobot-get_suction_cup_state-function}

```cpp
virtual std::shared_ptr<SuctionCupState> galbot::sdk::GalbotRobot::get_suction_cup_state(
    const std::string &end_effector
) =0
```

<small>Get current suction cup state.

Retrieves the current state of the specified suction cup, including activation status and vacuum pressure measurements.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `end_effector` | const std::string & | Joint group name specifying which suction cup to query (e.g., "left_suction_cup", "right_suction_cup") |

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [SuctionCupState](#suctioncupstate-struct) > | Shared pointer to , or nullptr if retrieval fails  |

**Supported:** G1

### get_dexterous_hand_state {#galbotrobot-get_dexterous_hand_state-function}

```cpp
virtual ControlStatus galbot::sdk::GalbotRobot::get_dexterous_hand_state(
    const std::string &end_effector,
    JointStateMessage &joint_state
) =0
```

<small>Get current dexterous hand (dexhand) state.

Retrieves the current joint state of the specified dexterous hand.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `end_effector` | const std::string & | Joint group name specifying which dexhand to query (e.g., "left_dexhand", "right_dexhand") |
| `joint_state` | [JointStateMessage](#jointstatemessage-struct) & | Output: current joint state (position, velocity, effort, etc.) |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#galbot-sdk-controlstatus-enum) | [ControlStatus](#galbot-sdk-controlstatus-enum) indicating success or failure |

### set_dexhand_command {#galbotrobot-set_dexhand_command-function}

```cpp
virtual ControlStatus galbot::sdk::GalbotRobot::set_dexhand_command(
    const std::string &end_effector,
    const std::vector< JointCommand > &dexhand_command,
    bool is_blocking=true
) =0
```

<small>Control dexhand with joint commands.

Commands the dexhand with a vector of joint commands (position, velocity, effort, etc.).</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `end_effector` | const std::string & | Joint group name specifying which dexhand to control (e.g., "left_dexhand", "right_dexhand") |
| `dexhand_command` | const std::vector< [JointCommand](#jointcommand-struct) > & | Vector of joint commands for each dexhand joint inspire: [position, velocity, acceleration, effort] range [0-1000, 0-1000, , 0-1000] brainco: [position, velocity, acceleration, effort] range [0-100, -100-100, , ] |
| `is_blocking` | bool | If true, blocks until command completes or times out |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#galbot-sdk-controlstatus-enum) | [ControlStatus](#galbot-sdk-controlstatus-enum) indicating success or failure |

### get_joint_positions {#galbotrobot-get_joint_positions-function}

```cpp
virtual std::vector<double> galbot::sdk::GalbotRobot::get_joint_positions(
    const std::vector< std::string > &joint_groups,
    const std::vector< std::string > &joint_names
) =0
```

<small>Get current joint positions by group name.

Retrieves the current angular positions of joints in the specified groups. The returned vector order matches the joint ordering from get_joint_names().</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `joint_groups` | const std::vector< std::string > & | Joint group names to query. Empty vector retrieves all body joints. |
| `joint_names` | const std::vector< std::string > & | Specific joint names to query. This parameter takes precedence over joint_groups. When provided, joint_groups is ignored. |

**Returns**

| Type | Description |
| --- | --- |
| std::vector< double > | Vector of current joint angles in radians |

### get_joint_group_names {#galbotrobot-get_joint_group_names-function}

```cpp
virtual std::vector<std::string> galbot::sdk::GalbotRobot::get_joint_group_names()=0
```

<small>Get available joint group names for the robot.

Retrieves all joint group names defined in the robot's kinematic configuration. This is useful for discovering available control groups at runtime.</small>

**Returns**

| Type | Description |
| --- | --- |
| std::vector< std::string > | Vector of joint group names, or empty vector if retrieval fails |

### get_joint_names {#galbotrobot-get_joint_names-function}

```cpp
virtual std::vector<std::string> galbot::sdk::GalbotRobot::get_joint_names(
    bool only_active_joint=true,
    const std::vector< std::string > &joint_groups={}
) =0
```

<small>Get robot joint names by group name.

Retrieves the names of joints belonging to specified joint groups. This is useful for determining the correct ordering when setting joint positions.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `only_active_joint` | bool | If true, returns only actuated joints (excludes passive/fixed joints). If false, returns all joints including passive ones. |
| `joint_groups` | const std::vector< std::string > & | Joint group names to query. Empty vector retrieves joints from all groups. |

**Returns**

| Type | Description |
| --- | --- |
| std::vector< std::string > | Vector of joint names in kinematic chain order |

### get_joint_states {#galbotrobot-get_joint_states-function}

```cpp
virtual std::vector<JointState> galbot::sdk::GalbotRobot::get_joint_states(
    const std::vector< std::string > &joint_group_vec,
    const std::vector< std::string > &joint_names_vec={}
) =0
```

<small>Get real-time joint states by group name.

Retrieves comprehensive state information for specified joints, including position, velocity, acceleration, effort (torque), and other feedback data.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `joint_group_vec` | const std::vector< std::string > & | Joint group names to query. Empty vector defaults to all body joints. |
| `joint_names_vec` | const std::vector< std::string > & | Specific joint names to query. This parameter takes precedence over joint_group_vec. When provided, joint_group_vec is ignored. |

**Returns**

| Type | Description |
| --- | --- |
| std::vector< [JointState](#jointstate-struct) > | Vector of structures containing current state for each joint |

### set_base_velocity {#galbotrobot-set_base_velocity-function}

```cpp
virtual ControlStatus galbot::sdk::GalbotRobot::set_base_velocity(
    const std::array< double, 3 > &linear_velocity,
    const std::array< double, 3 > &angular_velocity,
    double duration_s=0.0
) =0
```

<small>Set mobile base velocity command.

Commands the robot's mobile base to move with specified linear and angular velocities. Velocities are expressed in the robot's base frame coordinate system.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `linear_velocity` | const std::array< double, 3 > & | Linear velocity in meters per second (m/s), expressed in base frame. Order: {vx, vy, vz} where: vx: forward/backward velocity (positive forward) vy: left/right velocity (positive left) vz: up/down velocity (typically 0 for ground robots) |
| `angular_velocity` | const std::array< double, 3 > & | Angular velocity in radians per second (rad/s), expressed in base frame. Order: {wx, wy, wz} where: wx: roll rate (rotation about x-axis) wy: pitch rate (rotation about y-axis) wz: yaw rate (rotation about z-axis, positive counter-clockwise) |
| `duration_s` | double | Duration in seconds to maintain the velocity command before auto-stop. If <= 0, the command behaves as legacy mode (no automatic stop). |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#galbot-sdk-controlstatus-enum) | [ControlStatus](#galbot-sdk-controlstatus-enum) indicating success or failure of command transmission |

### set_base_pose {#galbotrobot-set_base_pose-function}

```cpp
virtual ControlStatus galbot::sdk::GalbotRobot::set_base_pose(
    const Pose &base_pose,
    bool is_blocking=true,
    double timeout_s=15.0
) =0
```

<small>Set mobile base pose command.

Commands the robot's mobile base to move to a specified pose in its reference frame. This uses the chassis pose controller (CHASSIS_POSE_CTRL). Use this overload when a full 3D pose (position + quaternion orientation) is already available.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `base_pose` | const [Pose](#pose-struct) & | Target base pose [x, y, z, qx, qy, qz, qw] |
| `is_blocking` | bool | If true, waits for controller response; if false, returns immediately after request |
| `timeout_s` | double | Timeout for blocking request (seconds) |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#galbot-sdk-controlstatus-enum) | [ControlStatus](#galbot-sdk-controlstatus-enum) indicating success or failure of command transmission |

### set_base_pose {#galbotrobot-set_base_pose-function}

```cpp
virtual ControlStatus galbot::sdk::GalbotRobot::set_base_pose(
    double x,
    double y,
    double yaw,
    const std::string &frame_id="odom",
    const std::string &reference_frame_id="odom",
    bool is_blocking=true,
    double timeout_s=15.0
) =0
```

<small>Set mobile base pose (x, y, yaw) with selectable frames.

Use this overload for planar 2D goal commands defined by x/y/yaw in the selected frame.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `x` | double | Target x position (meters) |
| `y` | double | Target y position (meters) |
| `yaw` | double | Target yaw (radians) |
| `frame_id` | const std::string & | Frame id of target. Options: "base_link" / "odom" / "map". Default: "odom" |
| `reference_frame_id` | const std::string & | Reference frame id. Options: "odom" / "map" |
| `is_blocking` | bool | If true, waits for controller response; if false, returns immediately after request |
| `timeout_s` | double | Timeout for blocking request (seconds) |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#galbot-sdk-controlstatus-enum) | [ControlStatus](#galbot-sdk-controlstatus-enum) indicating success or failure of command transmission |

### set_base_pose {#galbotrobot-set_base_pose-function}

```cpp
virtual ControlStatus galbot::sdk::GalbotRobot::set_base_pose(
    double x,
    double y,
    double yaw,
    const std::string &frame_id,
    const std::string &reference_frame_id,
    double time_from_start_s,
    bool is_blocking=true,
    double timeout_s=15.0
) =0
```

<small>Set mobile base pose (x, y, yaw) with explicit interpolation time.

Use this overload when arrival timing must be coordinated through time_from_start_s.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `x` | double | Target x position (meters) |
| `y` | double | Target y position (meters) |
| `yaw` | double | Target yaw (radians) |
| `frame_id` | const std::string & | Frame id of target. Options: "base_link" / "odom" / "map". |
| `reference_frame_id` | const std::string & | Reference frame id. Options: "odom" / "map" |
| `time_from_start_s` | double | Chassis pose interpolation time (seconds) |
| `is_blocking` | bool | If true, waits for controller response; if false, returns immediately after request |
| `timeout_s` | double | Request timeout (seconds) |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#galbot-sdk-controlstatus-enum) | [ControlStatus](#galbot-sdk-controlstatus-enum) indicating success or failure of command transmission |

### stop_base {#galbotrobot-stop_base-function}

```cpp
virtual ControlStatus galbot::sdk::GalbotRobot::stop_base()=0
```

<small>Emergency stop mobile base movement.

Immediately commands the mobile base to stop all motion. This is a safety function that should be used when immediate cessation of base motion is required.</small>

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#galbot-sdk-controlstatus-enum) | [ControlStatus](#galbot-sdk-controlstatus-enum) indicating success or failure of command transmission |

### zero_whole_body_and_base {#galbotrobot-zero_whole_body_and_base-function}

```cpp
virtual std::pair<MotionStatus, ControlStatus> galbot::sdk::GalbotRobot::zero_whole_body_and_base(
    const Pose &base_zero_pose,
    bool is_blocking=true,
    double leg_head_speed_rad_s=0.2,
    double leg_head_timeout_s=15.0,
    std::shared_ptr< Parameter > params=nullptr
) =0
```

<small>One-key zero: move whole-body joints to zero and base to zero pose.

This calls move_whole_body_joint_zero for joint zeroing, and commands the base pose to zero. If params is nullptr, default_param is used.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `base_zero_pose` | const [Pose](#pose-struct) & | Target base zero pose [x, y, z, qx, qy, qz, qw] |
| `is_blocking` | bool | Whether to block on joint zeroing |
| `leg_head_speed_rad_s` | double | Max joint speed for leg/head direct control (rad/s) |
| `leg_head_timeout_s` | double | Timeout for leg/head direct control (seconds) |
| `params` | std::shared_ptr< [Parameter](#parameter-class) > | Motion planning parameters (nullptr uses default_param) |

**Returns**

| Type | Description |
| --- | --- |
| std::pair< [MotionStatus](#galbot-sdk-motionstatus-enum), [ControlStatus](#galbot-sdk-controlstatus-enum) > | Pair of ([MotionStatus](#galbot-sdk-motionstatus-enum) for joints, [ControlStatus](#galbot-sdk-controlstatus-enum) for base) |

### zero_whole_body_and_base {#galbotrobot-zero_whole_body_and_base-function}

```cpp
virtual std::pair<MotionStatus, ControlStatus> galbot::sdk::GalbotRobot::zero_whole_body_and_base(
    const std::string &frame_id="odom",
    const std::string &reference_frame_id="odom",
    bool is_blocking=true,
    double leg_head_speed_rad_s=0.2,
    double leg_head_timeout_s=15.0,
    std::shared_ptr< Parameter > params=nullptr
) =0
```

<small>One-key zero: move whole-body joints to zero and base (x,y,yaw) to zero with selectable frames.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `frame_id` | const std::string & | Frame id of target. Options: "base_link" / "odom" / "map". Default "odom". |
| `reference_frame_id` | const std::string & | Reference frame id. Options: "odom" / "map" |
| `is_blocking` | bool | Whether to block on joint zeroing |
| `leg_head_speed_rad_s` | double | Max joint speed for leg/head direct control (rad/s) |
| `leg_head_timeout_s` | double | Timeout for leg/head direct control (seconds) |
| `params` | std::shared_ptr< [Parameter](#parameter-class) > | Motion planning parameters (nullptr uses default_param) |

**Returns**

| Type | Description |
| --- | --- |
| std::pair< [MotionStatus](#galbot-sdk-motionstatus-enum), [ControlStatus](#galbot-sdk-controlstatus-enum) > | Pair of ([MotionStatus](#galbot-sdk-motionstatus-enum) for joints, [ControlStatus](#galbot-sdk-controlstatus-enum) for base) |

### stop_trajectory_execution {#galbotrobot-stop_trajectory_execution-function}

```cpp
virtual ControlStatus galbot::sdk::GalbotRobot::stop_trajectory_execution()=0
```

<small>Stop all currently executing joint trajectories.

Immediately halts execution of all active joint trajectories across all joint groups. Joints will maintain their current positions after stopping.</small>

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#galbot-sdk-controlstatus-enum) | [ControlStatus](#galbot-sdk-controlstatus-enum) indicating success or failure of command transmission |

### reload_controller {#galbotrobot-reload_controller-function}

```cpp
virtual ControlStatus galbot::sdk::GalbotRobot::reload_controller(const std::string &group_name="all")=0
```

<small>Reload a controller.

Reinitializes the controller. Equivalent to a full restart cycle: stop -> reset -> start. Useful for error recovery or applying configuration changes.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `group_name` | const std::string & | Name of the joint group to reload. Supported groups: chassis, legs, head, left_arm, right_arm, gripper, or "all" to reload all controllers (default). |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#galbot-sdk-controlstatus-enum) | [ControlStatus](#galbot-sdk-controlstatus-enum) indicating success or failure of the reload operation |

### switch_controller {#galbotrobot-switch_controller-function}

```cpp
virtual ControlStatus galbot::sdk::GalbotRobot::switch_controller(const std::string &controller_name)=0
```

<small>Switch active controller strategy.

Transitions hardware control to a new strategy. Operation sequence: stop(old) -> release(old) -> acquire(new) -> start(new).</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `controller_name` | const std::string & | Controller name string, for example "CHASSIS_POSE_CTRL". |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#galbot-sdk-controlstatus-enum) | [ControlStatus](#galbot-sdk-controlstatus-enum) indicating success or failure of the switch operation. |

### get_active_controller {#galbotrobot-get_active_controller-function}

```cpp
virtual std::string galbot::sdk::GalbotRobot::get_active_controller(const std::string &group_name)=0
```

<small>Get active controller name for specified joint group.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `group_name` | const std::string & | Name of the joint group to query. |

**Returns**

| Type | Description |
| --- | --- |
| std::string | std::string Name of the active controller. |

### acquire_controller {#galbotrobot-acquire_controller-function}

```cpp
virtual ControlStatus galbot::sdk::GalbotRobot::acquire_controller(const std::string &controller_name)=0
```

<small>Acquire hardware authority.

Designates the controller to take ownership of the hardware. Opposite of release_controller. Controller must still be started to begin execution.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `controller_name` | const std::string & | Controller name string, for example "LEFT_ARM_PVT_CTRL". |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#galbot-sdk-controlstatus-enum) | [ControlStatus](#galbot-sdk-controlstatus-enum) indicating success or failure of the acquire operation. |

### release_controller {#galbotrobot-release_controller-function}

```cpp
virtual ControlStatus galbot::sdk::GalbotRobot::release_controller(const std::string &group_name="all")=0
```

<small>Release hardware authority.

Yields control of the hardware, freeing the joints. Opposite of acquire_controller. Implicitly stops execution if running.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `group_name` | const std::string & | Name of the joint group to release. Supported groups: chassis, legs, head, left_arm, right_arm, gripper, or "all" to release all controllers (default). |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#galbot-sdk-controlstatus-enum) | [ControlStatus](#galbot-sdk-controlstatus-enum) indicating success or failure of the release operation |

### start_controller {#galbotrobot-start_controller-function}

```cpp
virtual ControlStatus galbot::sdk::GalbotRobot::start_controller(const std::string &group_name="all")=0
```

<small>Start controller execution.

Activates the controller to begin sending commands. Opposite of stop_controller. Requires prior hardware authority (acquire).</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `group_name` | const std::string & | Name of the joint group to start. Supported groups: chassis, legs, head, left_arm, right_arm, gripper, or "all" to start all controllers (default). |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#galbot-sdk-controlstatus-enum) | [ControlStatus](#galbot-sdk-controlstatus-enum) indicating success or failure of the start operation |

### stop_controller {#galbotrobot-stop_controller-function}

```cpp
virtual ControlStatus galbot::sdk::GalbotRobot::stop_controller(const std::string &group_name="all")=0
```

<small>Stop controller execution.

Halts command execution but retains hardware authority. Opposite of start_controller.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `group_name` | const std::string & | Name of the joint group to stop. Supported groups: chassis, legs, head, left_arm, right_arm, gripper, or "all" to stop all controllers (default). |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#galbot-sdk-controlstatus-enum) | [ControlStatus](#galbot-sdk-controlstatus-enum) indicating success or failure of the stop operation |

### get_imu_data {#galbotrobot-get_imu_data-function}

```cpp
virtual std::shared_ptr<ImuData> galbot::sdk::GalbotRobot::get_imu_data(SensorType imu_type)=0
```

<small>Get IMU (Inertial Measurement Unit) sensor data.

Retrieves the latest IMU measurements including linear acceleration, angular velocity, and orientation estimation.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `imu_type` | [SensorType](#galbot-sdk-sensortype-enum) | [SensorType](#galbot-sdk-sensortype-enum) enumeration specifying which IMU to query |

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [ImuData](#imudata-struct) > | Shared pointer to structure, or nullptr if sensor is not enabled or data retrieval fails |

!!! note
    The IMU sensor must be enabled during initialization via enable_sensor_set

!!! note
    Acceleration is in meters per second squared (m/s²)

!!! note
    Angular velocity is in radians per second (rad/s)

### get_odom {#galbotrobot-get_odom-function}

```cpp
virtual std::shared_ptr<OdomData> galbot::sdk::GalbotRobot::get_odom()=0
```

<small>Get robot odometry information.

Retrieves the robot's current pose and velocity estimates from the odometry system. Odometry typically fuses wheel encoders, IMU, and other proprioceptive sensors.</small>

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [OdomData](#odomdata-struct) > | Shared pointer to containing:<br>- Position in meters (m) relative to odometry frame origin<br>- Orientation as quaternion<br>- Linear velocity in meters per second (m/s)<br>- Angular velocity in radians per second (rad/s)<br>- [Timestamp](#timestamp-struct) in nanoseconds Returns nullptr if odometry is unavailable. |

### get_device_information {#galbotrobot-get_device_information-function}

```cpp
virtual std::shared_ptr<DeviceInfo> galbot::sdk::GalbotRobot::get_device_information()=0
```

<small>Get device information.

Retrieves basic device information including device model, serial number, firmware version, hardware version, and manufacturer. This information is used for device management, version control, system diagnostics, and device identification.</small>

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [DeviceInfo](#deviceinfo-struct) > | Shared pointer to structure containing:<br>- model: Device model name or identifier<br>- serial_number: Unique serial number for device identification<br>- firmware_version: System firmware version string<br>- hardware_version: Hardware version or revision number<br>- manufacturer: Manufacturer name or company identifier Returns nullptr if device information retrieval fails. |

### get_rgb_data {#galbotrobot-get_rgb_data-function}

```cpp
virtual std::shared_ptr<RgbData> galbot::sdk::GalbotRobot::get_rgb_data(const SensorType rgb_camera)=0
```

<small>Get latest RGB image from specified camera.

Retrieves the most recent color image captured by the specified RGB camera.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `rgb_camera` | const [SensorType](#galbot-sdk-sensortype-enum) | [SensorType](#galbot-sdk-sensortype-enum) enumeration specifying which RGB camera to query |

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [RgbData](#rgbdata-struct) > | Shared pointer to containing image buffer, dimensions, encoding, and timestamp. Returns nullptr if camera is not enabled or data retrieval fails. |

!!! note
    The camera sensor must be enabled during initialization via enable_sensor_set

### get_depth_data {#galbotrobot-get_depth_data-function}

```cpp
virtual std::shared_ptr<DepthData> galbot::sdk::GalbotRobot::get_depth_data(const SensorType depth_camera)=0
```

<small>Get latest depth image from specified camera.

Retrieves the most recent depth image captured by the specified depth camera. Depth values typically represent distance from the camera sensor.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `depth_camera` | const [SensorType](#galbot-sdk-sensortype-enum) | [SensorType](#galbot-sdk-sensortype-enum) enumeration specifying which depth camera to query |

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [DepthData](#depthdata-struct) > | Shared pointer to containing depth image buffer, dimensions, encoding, and timestamp. Returns nullptr if camera is not enabled or data retrieval fails. |

!!! note
    The camera sensor must be enabled during initialization via enable_sensor_set

!!! note
    Depth values are typically in millimeters (mm) or meters (m) depending on sensor

### get_lidar_data {#galbotrobot-get_lidar_data-function}

```cpp
virtual std::shared_ptr<LidarData> galbot::sdk::GalbotRobot::get_lidar_data(const SensorType lidar)=0
```

<small>Get latest LiDAR point cloud data.

Retrieves the most recent 3D point cloud captured by the specified LiDAR sensor. Each point typically contains (x, y, z) coordinates and optional intensity values.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `lidar` | const [SensorType](#galbot-sdk-sensortype-enum) | [SensorType](#galbot-sdk-sensortype-enum) enumeration specifying which LiDAR to query |

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [LidarData](#lidardata-struct) > | Shared pointer to (PointCloud2 format) containing point cloud with coordinates in meters (m) relative to the LiDAR frame. Returns nullptr if LiDAR is not enabled or data retrieval fails. |

!!! note
    The LiDAR sensor must be enabled during initialization via enable_sensor_set

### get_ultrasonic_data {#galbotrobot-get_ultrasonic_data-function}

```cpp
virtual std::shared_ptr<UltrasonicData> galbot::sdk::GalbotRobot::get_ultrasonic_data(
    const UltrasonicType ultrasonic_type
) =0
```

<small>Get distance measurement from specified ultrasonic sensor.

Retrieves the latest distance measurement from one of the ultrasonic range sensors. The robot typically has multiple ultrasonic sensors arranged around its perimeter.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `ultrasonic_type` | const [UltrasonicType](#galbot-sdk-ultrasonictype-enum) | [UltrasonicType](#galbot-sdk-ultrasonictype-enum) enumeration specifying which ultrasonic sensor to query (one of 8 directional sensors) |

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [UltrasonicData](#ultrasonicdata-struct) > | Shared pointer to containing distance in meters (m), or nullptr if sensor is not enabled or data retrieval fails |

!!! note
    The ultrasonic sensor must be enabled during initialization via enable_sensor_set

**Supported:** G1

### get_camera_intrinsic {#galbotrobot-get_camera_intrinsic-function}

```cpp
virtual std::shared_ptr<CameraInfo> galbot::sdk::GalbotRobot::get_camera_intrinsic(const SensorType camera)=0
```

<small>Get camera intrinsic parameters.

Retrieves the intrinsic parameters of the specified camera, including focal lengths, principal points, and distortion coefficients, etc.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `camera` | const [SensorType](#galbot-sdk-sensortype-enum) | [SensorType](#galbot-sdk-sensortype-enum) enumeration specifying which camera to query |

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [CameraInfo](#camerainfo-struct) > | Shared pointer to containing:<br>- focal_length_x, focal_length_y: Focal lengths in pixels<br>- principal_point_x, principal_point_y: Principal point coordinates in pixels<br>- distortion_coeffs: Vector of distortion coefficients (e.g., k1, k2, p1, p2, k3)<br>- more camera-specific parameters as needed Returns nullptr if camera is not enabled or data retrieval fails. |

!!! note
    The camera sensor must be enabled during initialization via enable_sensor_set

### get_transform {#galbotrobot-get_transform-function}

```cpp
virtual std::pair<std::vector<double>, int64_t> galbot::sdk::GalbotRobot::get_transform(
    const std::string &target_frame,
    const std::string &source_frame,
    int64_t timestamp_ns=0,
    int64_t timeout_ms=100
) =0
```

<small>Query coordinate frame transformation (TF)

Queries the transformation between two coordinate frames in the robot's TF tree. This is used for converting poses and positions between different reference frames (e.g., from camera frame to base frame, from end-effector to world frame).</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `target_frame` | const std::string & | Name of the target coordinate frame (frame to transform into) |
| `source_frame` | const std::string & | Name of the source coordinate frame (frame to transform from) |
| `timestamp_ns` | int64_t | Desired transform timestamp in nanoseconds. Pass 0 to get the most recent available transformation. |
| `timeout_ms` | int64_t | Maximum time to wait for the transform in milliseconds. Default: 100 milliseconds. |

**Returns**

| Type | Description |
| --- | --- |
| std::pair< std::vector< double >, int64_t > | Pair containing:<br>- Vector of 7 doubles representing the transform [x, y, z, qx, qy, qz, qw] where (x, y, z) is translation in meters and (qx, qy, qz, qw) is orientation quaternion<br>- [Timestamp](#timestamp-struct) in nanoseconds when the transform was valid Returns empty vector and timestamp 0 if retrieval fails or times out. |

### get_frame_names {#galbotrobot-get_frame_names-function}

```cpp
virtual std::vector<std::string> galbot::sdk::GalbotRobot::get_frame_names()=0
```

<small>Get all available coordinate frame names in the TF tree.</small>

**Returns**

| Type | Description |
| --- | --- |
| std::vector< std::string > | std::vector<std::string> All frame names |

### get_sensor_extrinsic {#galbotrobot-get_sensor_extrinsic-function}

```cpp
virtual std::pair<std::vector<double>, int64_t> galbot::sdk::GalbotRobot::get_sensor_extrinsic(
    const SensorType sensor_id,
    const std::string &reference_frame="base_link"
) =0
```

<small>Get sensor extrinsic parameters.

Retrieves the extrinsic parameters of the specified sensor, including rotation and translation vectors relative to the robot's base frame.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `sensor_id` | const [SensorType](#galbot-sdk-sensortype-enum) | [SensorType](#galbot-sdk-sensortype-enum) enumeration specifying which sensor to query |
| `reference_frame` | const std::string & | Name of the reference coordinate frame (frame to transform from). Default is "base_link". |

**Returns**

| Type | Description |
| --- | --- |
| std::pair< std::vector< double >, int64_t > | Pair containing:<br>- Vector of 7 doubles representing the transform [x, y, z, qx, qy, qz, qw] where (x, y, z) is translation in meters and (qx, qy, qz, qw) is orientation quaternion<br>- [Timestamp](#timestamp-struct) in nanoseconds when the transform was valid Returns empty vector and timestamp 0 if retrieval fails. |

!!! note
    The sensor must be enabled during initialization via enable_sensor_set

### get_force_sensor_data {#galbotrobot-get_force_sensor_data-function}

```cpp
virtual std::shared_ptr<ForceData> galbot::sdk::GalbotRobot::get_force_sensor_data(
    const GalbotOneFoxtrotSensor sensor_type
) =0
```

<small>Get force/torque sensor data.

Retrieves the latest measurements from the specified force/torque sensor. These sensors are typically mounted at wrists or end-effectors for contact force monitoring and compliance control.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `sensor_type` | const [GalbotOneFoxtrotSensor](#galbot-sdk-galbotonefoxtrotsensor-enum) | [GalbotOneFoxtrotSensor](#galbot-sdk-galbotonefoxtrotsensor-enum) enumeration specifying which force sensor to query |

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [ForceData](#forcedata-struct) > | Shared pointer to containing:<br>- Force vector in Newtons (N): [fx, fy, fz]<br>- Torque vector in Newton-meters (N·m): [tx, ty, tz]<br>- [Timestamp](#timestamp-struct) in nanoseconds Returns nullptr if sensor is not enabled or data retrieval fails. |

!!! note
    The force sensor must be enabled during initialization via enable_sensor_set

**Supported:** G1

### start_microphone_stream_input {#galbotrobot-start_microphone_stream_input-function}

```cpp
virtual std::string galbot::sdk::GalbotRobot::start_microphone_stream_input(
    std::function< void(const std::shared_ptr< AudioData >)> callback,
    int chunk_size=2560,
    bool use_raw_audio=false
) =0
```

<small>Start microphone streaming audio input.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `callback` | std::function< void(const std::shared_ptr< [AudioData](#audiodata-struct) >)> | Audio data callback function with signature: void(const std::shared_ptr<[AudioData](#audiodata-struct)>) |
| `chunk_size` | int | Audio data chunk size in bytes, default value 2560. Dynamic configuration not supported yet |
| `use_raw_audio` | bool | Whether to use raw audio, default false. Dynamic configuration not supported yet. true means output raw audio directly, false means output processed audio |

**Returns**

| Type | Description |
| --- | --- |
| std::string | std::string Stream ID used to identify this audio input stream  |

**Supported:** G1

### stop_microphone_stream_input {#galbotrobot-stop_microphone_stream_input-function}

```cpp
virtual void galbot::sdk::GalbotRobot::stop_microphone_stream_input(const std::string &stream_id="")=0
```

<small>Stop the specified microphone streaming audio input.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `stream_id` | const std::string & | Audio input stream ID to stop. If empty string, stops all active streams |

**Supported:** G1

### write_audio_stream_output {#galbotrobot-write_audio_stream_output-function}

```cpp
virtual bool galbot::sdk::GalbotRobot::write_audio_stream_output(
    const std::string &audio_chunk,
    const std::string &stream_id=""
) =0
```

<small>Write PCM format audio data chunk to audio output stream for real-time playback.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `audio_chunk` | const std::string & | Audio data chunk in PCM format (16000 Hz, 16-bit little-endian), single channel |
| `stream_id` | const std::string & | Audio stream ID to distinguish different audio sources. Empty string means use default stream |

**Returns**

| Type | Description |
| --- | --- |
| bool | bool Returns operation result. True means audio data has been successfully written and playback task issued, False means write failed  |

**Supported:** G1

### stop_audio_stream_output {#galbotrobot-stop_audio_stream_output-function}

```cpp
virtual void galbot::sdk::GalbotRobot::stop_audio_stream_output(const std::string &stream_id="")=0
```

<small>Stop the specified audio output stream or all active audio output streams playback.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `stream_id` | const std::string & | Audio output stream ID to stop. Empty string means stop all active audio output streams |

**Supported:** G1

### get_volume {#galbotrobot-get_volume-function}

```cpp
virtual float galbot::sdk::GalbotRobot::get_volume()=0
```

<small>Get current system global volume value.</small>

**Returns**

| Type | Description |
| --- | --- |
| float | float Returns current volume value, range 0.0 to 100.0  |

**Supported:** G1

### set_volume {#galbotrobot-set_volume-function}

```cpp
virtual bool galbot::sdk::GalbotRobot::set_volume(float volume)=0
```

<small>Set system global volume value.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `volume` | float | Target volume value, range 0.0 to 100.0 |

**Returns**

| Type | Description |
| --- | --- |
| bool | bool Returns the volume setting result. True indicates the volume was set successfully, False indicates the volume setting failed.  |

**Supported:** G1

### is_running {#galbotrobot-is_running-function}

```cpp
virtual bool galbot::sdk::GalbotRobot::is_running()=0
```

<small>Check if the robot control system is running.

Queries whether the robot control system is still active or if a shutdown signal (e.g., SIGINT, SIGTERM) has been received.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | true if system is running normally |

### request_shutdown {#galbotrobot-request_shutdown-function}

```cpp
virtual void galbot::sdk::GalbotRobot::request_shutdown()=0
```

<small>Request system shutdown.

Programmatically sends a shutdown signal (SIGINT) to initiate graceful system shutdown. This triggers registered exit callbacks and begins resource cleanup.</small>

### wait_for_shutdown {#galbotrobot-wait_for_shutdown-function}

```cpp
virtual void galbot::sdk::GalbotRobot::wait_for_shutdown()=0
```

<small>Block until shutdown signal is received.

Blocks the calling thread indefinitely until a shutdown signal (SIGINT, SIGTERM) is received. This is useful for keeping the main thread alive while background threads handle robot control.</small>

!!! note
    This function will return when is_running() becomes false

### destroy {#galbotrobot-destroy-function}

```cpp
virtual void galbot::sdk::GalbotRobot::destroy()=0
```

<small>Clean up system resources.

Performs cleanup of robot control system resources including middleware connections, sensor interfaces, and communication channels. Should be called before program exit to ensure graceful shutdown.</small>

!!! note
    This function should be called after request_shutdown() or when is_running() returns false

### register_exit_callback {#galbotrobot-register_exit_callback-function}

```cpp
virtual void galbot::sdk::GalbotRobot::register_exit_callback(std::function< void()> exit_function)=0
```

<small>Register callback function for shutdown event.

Registers a user-defined callback function that will be invoked when a shutdown signal is received. Multiple callbacks can be registered and will be executed in registration order.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `exit_function` | std::function< void()> | Callback function with signature void() to be executed during shutdown. Use this to perform application-specific cleanup (e.g., saving data, stopping threads). |

!!! note
    Callbacks should complete quickly to avoid delaying shutdown

### get_bms_information {#galbotrobot-get_bms_information-function}

```cpp
virtual std::shared_ptr<BmsInfo> galbot::sdk::GalbotRobot::get_bms_information()=0
```

<small>Get BMS (Battery Management System) information.</small>

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [BmsInfo](#bmsinfo-struct) > | Shared pointer to containing battery information  |

**Supported:** G1

### get_log_information {#galbotrobot-get_log_information-function}

```cpp
virtual std::shared_ptr<LogInfo> galbot::sdk::GalbotRobot::get_log_information(
    uint64 timewindow_s,
    LogLevel log_level
) =0
```

<small>Get log information.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `timewindow_s` | uint64 |  |
| `log_level` | [LogLevel](#galbot-sdk-loglevel-enum) |  |

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [LogInfo](#loginfo-struct) > | Shared pointer to containing log information |

### get_instance {#galbotrobot-get_instance-function}

```cpp
static GalbotRobot& galbot::sdk::GalbotRobot::get_instance(MachineType m)
```

<small>Runtime factory for selecting a concrete robot singleton.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `m` | [MachineType](#galbot-sdk-machinetype-enum) | Machine type identifier (e.g. [MachineType](#galbot-sdk-machinetype-enum)::G1, [MachineType](#galbot-sdk-machinetype-enum)::S1). |

**Returns**

| Type | Description |
| --- | --- |
| [GalbotRobot](#galbotrobot-class) & | Reference to the singleton robot interface for the specified machine type. |


---

<a id="module-galbotmotion"></a>

## GalbotMotion {#galbotmotion-class}

<small>Unified motion planning and control interface for Galbot robots.

This interface provides a comprehensive API for robot motion control, including: Forward and inverse kinematics computation Single-chain and multi-chain trajectory planning Collision detection (self-collision and environment) Tool and obstacle management Whole-body coordinated motion planning Use [GalbotMotion](#galbotmotion-class)::get_instance([MachineType](#galbot-sdk-machinetype-enum)) to obtain a reference for a specific platform (G1/S1). All angular units are radians, linear units are meters (SI standard). Quaternions must be unit-normalized: sqrt(x² + y² + z² + w²) = 1.</small>

### ~GalbotMotion {#galbotmotion-galbotmotion-function}

```cpp
virtual galbot::sdk::GalbotMotion::~GalbotMotion()=default
```

### init {#galbotmotion-init-function}

```cpp
virtual bool galbot::sdk::GalbotMotion::init()=0
```

<small>Initialize motion planning system and communication interfaces.

Must be called before any other API functions. Initializes internal communication middleware, loads robot kinematic models, and establishes connections to control services.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | true if initialization succeeds |

!!! note
    Safe to call multiple times; subsequent calls after successful init are no-ops.

!!! warning
    All other API calls will fail if init() returns false.

### is_valid {#galbotmotion-is_valid-function}

```cpp
virtual bool galbot::sdk::GalbotMotion::is_valid()=0
```

<small>Check if the motion interface is properly initialized and operational.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | true if object is valid and ready for use |

!!! note
    Should be checked before critical operations if init status is uncertain.

### forward_kinematics {#galbotmotion-forward_kinematics-function}

```cpp
virtual std::tuple<MotionStatus, std::vector<double> > galbot::sdk::GalbotMotion::forward_kinematics(
    const std::string &target_frame,
    const std::string &reference_frame="base_link",
    const std::unordered_map< std::string, std::vector< double >> &joint_state={},
    std::shared_ptr< Parameter > params=default_param
) =0
```

<small>Compute forward kinematics for a target link.

Calculates the Cartesian pose of a specified link given joint configurations. Useful for determining end-effector positions, validating configurations, or computing intermediate link poses.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `target_frame` | const std::string & | Name of the link whose pose is to be computed (e.g., "left_ee_link", "camera_link") |
| `reference_frame` | const std::string & | Coordinate frame for pose expression (default: "base_link") |
| `joint_state` | const std::unordered_map< std::string, std::vector< double >> & | Joint configurations by chain: {chain_name -> joint_angles}. Empty map uses current robot joint state. |
| `params` | std::shared_ptr< [Parameter](#parameter-class) > | Planning parameters (collision checking, timeout, etc.) |

**Returns**

| Type | Description |
| --- | --- |
| std::tuple< [MotionStatus](#galbot-sdk-motionstatus-enum), std::vector< double > > | Tuple of (status, pose_vector):<br>- status: [MotionStatus](#galbot-sdk-motionstatus-enum)::SUCCESS on success, error code otherwise<br>- pose_vector: [x, y, z, qx, qy, qz, qw] (meters, quaternion) or empty on failure |

!!! note
    Joint angles in radians, output pose in meters with unit quaternion.

!!! warning
    target_frame must be a valid link in the URDF model.

### forward_kinematics_by_state {#galbotmotion-forward_kinematics_by_state-function}

```cpp
virtual std::tuple<MotionStatus, std::vector<double> > galbot::sdk::GalbotMotion::forward_kinematics_by_state(
    const std::string &target_frame,
    const std::shared_ptr< RobotStates > &reference_robot_states=nullptr,
    const std::string &reference_frame="base_link",
    std::shared_ptr< Parameter > params=default_param
) =0
```

<small>Compute forward kinematics using complete robot state.

Similar to forward_kinematics(), but accepts a [RobotStates](#robotstates-class) object for specifying the complete robot configuration (whole-body joints + base pose).</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `target_frame` | const std::string & | Link name for pose computation |
| `reference_robot_states` | const std::shared_ptr< [RobotStates](#robotstates-class) > & | Complete robot state; nullptr uses current robot state |
| `reference_frame` | const std::string & | Coordinate frame for pose expression (default: "base_link") |
| `params` | std::shared_ptr< [Parameter](#parameter-class) > | Planning parameters |

**Returns**

| Type | Description |
| --- | --- |
| std::tuple< [MotionStatus](#galbot-sdk-motionstatus-enum), std::vector< double > > | Tuple of (status, pose_vector):<br>- status: [MotionStatus](#galbot-sdk-motionstatus-enum)::SUCCESS on success, error code otherwise<br>- pose_vector: [x, y, z, qx, qy, qz, qw] (meters, quaternion) or empty on failure |

!!! note
    Useful when computing FK for hypothetical states without modifying current robot state.

### inverse_kinematics {#galbotmotion-inverse_kinematics-function}

```cpp
virtual std::tuple<MotionStatus, std::unordered_map<std::string, std::vector<double> > > galbot::sdk::GalbotMotion::inverse_kinematics(
    const std::vector< double > &target_pose,
    const std::vector< std::string > &chain_names,
    const std::string &target_frame="EndEffector",
    const std::string &reference_frame="base_link",
    const std::unordered_map< std::string, std::vector< double >> &initial_joint_positions={},
    const bool &enable_collision_check=true,
    std::shared_ptr< Parameter > params=default_param
) =0
```

<small>Compute inverse kinematics for target Cartesian pose.

Solves for joint configurations that achieve the specified end-effector pose. Supports single-chain IK (arm only) or coordinated multi-chain IK (arm + torso/legs).</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `target_pose` | const std::vector< double > & | Target Cartesian pose: [x, y, z, qx, qy, qz, qw] (meters, quaternion) |
| `chain_names` | const std::vector< std::string > & | Kinematic chains to coordinate (e.g., {"left_arm"}, {"right_arm", "torso"}) |
| `target_frame` | const std::string & | Frame on chain for pose target (e.g., "EndEffector", "Tool") |
| `reference_frame` | const std::string & | Coordinate frame for pose specification (default: "base_link") |
| `initial_joint_positions` | const std::unordered_map< std::string, std::vector< double >> & | Seed configurations by chain: {chain_name -> joint_angles}. Empty map uses current robot state as seed. |
| `enable_collision_check` | const bool & | If true, only returns collision-free solutions |
| `params` | std::shared_ptr< [Parameter](#parameter-class) > | Planning parameters (timeout, actuation type, etc.) |

**Returns**

| Type | Description |
| --- | --- |
| std::tuple< [MotionStatus](#galbot-sdk-motionstatus-enum), std::unordered_map< std::string, std::vector< double > > > | Tuple of (status, solution_map):<br>- status: [MotionStatus](#galbot-sdk-motionstatus-enum)::SUCCESS if solvable, error code otherwise<br>- solution_map: {chain_name -> joint_angles} (radians) for each chain, empty on failure |

!!! note
    IK may have multiple solutions; returns first valid solution found.

!!! note
    Seed configuration affects convergence speed and which solution is returned.

!!! warning
    No solution guaranteed if target is outside workspace or in singular configuration.

### inverse_kinematics_by_state {#galbotmotion-inverse_kinematics_by_state-function}

```cpp
virtual std::tuple<MotionStatus, std::unordered_map<std::string, std::vector<double> > > galbot::sdk::GalbotMotion::inverse_kinematics_by_state(
    const std::vector< double > &target_pose,
    const std::vector< std::string > &chain_names,
    const std::string &target_frame="EndEffector",
    const std::string &reference_frame="base_link",
    const std::shared_ptr< RobotStates > &reference_robot_states=nullptr,
    const bool &enable_collision_check=true,
    std::shared_ptr< Parameter > params=default_param
) =0
```

<small>Compute inverse kinematics using complete robot state as seed.

Similar to inverse_kinematics(), but accepts [RobotStates](#robotstates-class) for specifying the seed configuration, allowing precise control over the entire robot state.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `target_pose` | const std::vector< double > & | Target Cartesian pose: [x, y, z, qx, qy, qz, qw] (meters, quaternion) |
| `chain_names` | const std::vector< std::string > & | Kinematic chains to coordinate |
| `target_frame` | const std::string & | Frame on chain for pose target (e.g., "EndEffector", "Tool") |
| `reference_frame` | const std::string & | Coordinate frame for pose specification (default: "base_link") |
| `reference_robot_states` | const std::shared_ptr< [RobotStates](#robotstates-class) > & | Complete robot state as IK seed; nullptr uses current state |
| `enable_collision_check` | const bool & | If true, only returns collision-free solutions |
| `params` | std::shared_ptr< [Parameter](#parameter-class) > | Planning parameters |

**Returns**

| Type | Description |
| --- | --- |
| std::tuple< [MotionStatus](#galbot-sdk-motionstatus-enum), std::unordered_map< std::string, std::vector< double > > > | Tuple of (status, solution_map):<br>- status: [MotionStatus](#galbot-sdk-motionstatus-enum)::SUCCESS if solvable, error code otherwise<br>- solution_map: {chain_name -> joint_angles} (radians), empty on failure |

!!! note
    Useful for offline planning with hypothetical robot states.

### get_end_effector_pose {#galbotmotion-get_end_effector_pose-function}

```cpp
virtual std::tuple<MotionStatus, std::vector<double> > galbot::sdk::GalbotMotion::get_end_effector_pose(
    const std::string &end_effector_frame,
    const std::string &reference_frame="base_link"
) =0
```

<small>Get current end-effector pose from robot state.

Queries the TF (Transform) tree to retrieve the current Cartesian pose of a specified end-effector link. Requires the link to be defined in the robot's URDF model.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `end_effector_frame` | const std::string & | Name of end-effector link (must exist in URDF, e.g., "left_ee_link") |
| `reference_frame` | const std::string & | Coordinate frame for pose expression (default: "base_link") |

**Returns**

| Type | Description |
| --- | --- |
| std::tuple< [MotionStatus](#galbot-sdk-motionstatus-enum), std::vector< double > > | Tuple of (status, pose_vector):<br>- status: [MotionStatus](#galbot-sdk-motionstatus-enum)::SUCCESS on success, error codes: DATA_FETCH_FAILED: TF lookup failed INVALID_INPUT: Invalid frame names<br>- pose_vector: [x, y, z, qx, qy, qz, qw] (meters, quaternion) or empty on failure<br>- DATA_FETCH_FAILED: TF lookup failed<br>- INVALID_INPUT: Invalid frame names |

!!! note
    Reflects the current actual robot state (not planned state).

!!! warning
    Requires TF tree to be properly published and up-to-date.

### get_end_effector_pose_on_chain {#galbotmotion-get_end_effector_pose_on_chain-function}

```cpp
virtual std::tuple<MotionStatus, std::vector<double> > galbot::sdk::GalbotMotion::get_end_effector_pose_on_chain(
    const std::string &chain_name,
    const std::string frame_id="EndEffector",
    const std::string &reference_frame="base_link"
) =0
```

<small>Get current end-effector pose for a specific kinematic chain.

Convenience method for retrieving end-effector pose by chain name and frame type, without needing to know the exact link name in URDF.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `chain_name` | const std::string & | Kinematic chain identifier (e.g., "left_arm", "right_arm") |
| `frame_id` | const std::string | End-effector frame type: "EndEffector" (flange), "Camera", etc. |
| `reference_frame` | const std::string & | Coordinate frame for pose expression (default: "base_link") |

**Returns**

| Type | Description |
| --- | --- |
| std::tuple< [MotionStatus](#galbot-sdk-motionstatus-enum), std::vector< double > > | Tuple of (status, pose_vector):<br>- status: [MotionStatus](#galbot-sdk-motionstatus-enum)::SUCCESS on success, error code otherwise<br>- pose_vector: [x, y, z, qx, qy, qz, qw] (meters, quaternion) or empty on failure |

!!! note
    Internally maps chain_name + frame_id to actual URDF link name.

### set_end_effector_pose {#galbotmotion-set_end_effector_pose-function}

```cpp
virtual MotionStatus galbot::sdk::GalbotMotion::set_end_effector_pose(
    const std::vector< double > &target_pose,
    const std::string &end_effector_frame,
    const std::string &reference_frame="base_link",
    std::shared_ptr< RobotStates > reference_robot_states=nullptr,
    const bool &enable_collision_check=true,
    const bool &is_blocking=true,
    const double &timeout=-1.0,
    std::shared_ptr< Parameter > params=default_param
) =0
```

<small>Command end-effector to move to target Cartesian pose.

High-level interface for Cartesian motion commands. Internally performs IK, plans trajectory, and optionally executes the motion. Supports both blocking (wait for completion) and non-blocking (return immediately) modes.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `target_pose` | const std::vector< double > & | Target Cartesian pose: [x, y, z, qx, qy, qz, qw] (meters, quaternion) |
| `end_effector_frame` | const std::string & | Kinematic chain identifier (e.g., "left_arm", "right_arm") |
| `reference_frame` | const std::string & | Coordinate frame for pose specification (default: "base_link") |
| `reference_robot_states` | std::shared_ptr< [RobotStates](#robotstates-class) > | Planning seed state; nullptr uses current state. Warning: For direct execution, typically leave as nullptr to avoid conflicts between seed and actual robot state. |
| `enable_collision_check` | const bool & | If true, only executes collision-free trajectories |
| `is_blocking` | const bool & | If true, blocks until motion completes or times out; if false, returns immediately |
| `timeout` | const double & | Blocking timeout (seconds). If < 0 and is_blocking=true, uses params->timeout_second |
| `params` | std::shared_ptr< [Parameter](#parameter-class) > | Motion planning parameters (linear motion, actuation type, etc.) |

**Returns**

| Type | Description |
| --- | --- |
| [MotionStatus](#galbot-sdk-motionstatus-enum) | [MotionStatus](#galbot-sdk-motionstatus-enum):<br>- SUCCESS: Motion completed successfully (blocking) or command sent (non-blocking)<br>- TIMEOUT: Motion exceeded timeout duration<br>- INVALID_INPUT: Invalid pose or parameters<br>- FAULT: Planning or execution failure |

!!! note
    Motion type (linear/joint-space) controlled by params->move_line flag.

!!! note
    For direct execution (params->is_direct_execute=true), avoid passing reference_robot_states.

!!! warning
    Blocking calls will halt execution until motion completes; use with caution in real-time contexts.

### motion_plan {#galbotmotion-motion_plan-function}

```cpp
virtual std::tuple<MotionStatus, std::unordered_map<std::string, std::vector<std::vector<double> > > > galbot::sdk::GalbotMotion::motion_plan(
    std::shared_ptr< RobotStates > target,
    std::shared_ptr< RobotStates > start=nullptr,
    std::shared_ptr< RobotStates > reference_robot_states=nullptr,
    bool enable_collision_check=true,
    std::shared_ptr< Parameter > params=default_param
) =0
```

<small>Plan trajectory for a single kinematic chain.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `target` | std::shared_ptr< [RobotStates](#robotstates-class) > | Target state (must be [PoseState](#posestate-class) or [JointStates](#jointstates-class), not base [RobotStates](#robotstates-class)). Specifies the goal configuration for planning. |
| `start` | std::shared_ptr< [RobotStates](#robotstates-class) > | Optional start state (typically [JointStates](#jointstates-class)). nullptr uses current robot state as start. Warning: For direct execution, leave as nullptr to avoid conflicts. |
| `reference_robot_states` | std::shared_ptr< [RobotStates](#robotstates-class) > | Whole-body reference state for planning context. nullptr uses current robot state. If start is provided, its joint values overwrite the corresponding chain in reference_robot_states. Warning: For direct execution, leave as nullptr. |
| `enable_collision_check` | bool | If true, only returns collision-free trajectories |
| `params` | std::shared_ptr< [Parameter](#parameter-class) > | Planning parameters (timeout, actuation type, linear motion, etc.) |

**Returns**

| Type | Description |
| --- | --- |
| std::tuple< [MotionStatus](#galbot-sdk-motionstatus-enum), std::unordered_map< std::string, std::vector< std::vector< double > > > > | Tuple of (status, trajectory_map):<br>- status: [MotionStatus](#galbot-sdk-motionstatus-enum)::SUCCESS if planning succeeds, error code otherwise<br>- trajectory_map: {chain_name -> waypoint_list}, where waypoint_list is a sequence of joint configurations (radians) along the trajectory. Empty on failure. |

!!! note
    Collision semantics: galbotMotion does not have real-time obstacle perception. When enable_collision_check=true, collision checking is evaluated against self-collision and the Motion-side environment objects that the user loads manually via add_obstacle() / attach_target_object().

!!! note
    Trajectory is time-parameterized with velocity/acceleration limits respected.

!!! note
    For direct execution (params->is_direct_execute=true), trajectory is automatically sent to robot.

!!! warning
    target must be PoseState or JointStates; passing base RobotStates will cause INVALID_INPUT error.

### motion_plan_multi_waypoints {#galbotmotion-motion_plan_multi_waypoints-function}

```cpp
virtual std::tuple<MotionStatus, std::unordered_map<std::string, std::vector<std::vector<double> > > > galbot::sdk::GalbotMotion::motion_plan_multi_waypoints(
    std::shared_ptr< RobotStates > target,
    std::vector< std::vector< double >> targets,
    std::shared_ptr< RobotStates > start=nullptr,
    std::shared_ptr< RobotStates > reference_robot_states=nullptr,
    bool enable_collision_check=true,
    std::shared_ptr< Parameter > params=default_param
) =0
```

<small>Plan trajectory through multiple waypoints for a single chain.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `target` | std::shared_ptr< [RobotStates](#robotstates-class) > | Template state defining waypoint type ([PoseState](#posestate-class) or [JointStates](#jointstates-class)) and specifying chain_name. The state values in target are not used; only the type and chain_name are referenced. |
| `targets` | std::vector< std::vector< double >> | Sequence of waypoint values. Format depends on target type: [PoseState](#posestate-class): each waypoint is [x, y, z, qx, qy, qz, qw] (meters, quaternion) [JointStates](#jointstates-class): each waypoint is joint configuration (radians) |
| `start` | std::shared_ptr< [RobotStates](#robotstates-class) > | Optional start state ([JointStates](#jointstates-class)). nullptr uses current robot state. Warning: For direct execution, leave as nullptr. |
| `reference_robot_states` | std::shared_ptr< [RobotStates](#robotstates-class) > | Whole-body reference state for planning context. nullptr uses current state. Warning: For direct execution, leave as nullptr. |
| `enable_collision_check` | bool | If true, only returns collision-free trajectories |
| `params` | std::shared_ptr< [Parameter](#parameter-class) > | Planning parameters |

**Returns**

| Type | Description |
| --- | --- |
| std::tuple< [MotionStatus](#galbot-sdk-motionstatus-enum), std::unordered_map< std::string, std::vector< std::vector< double > > > > | Tuple of (status, trajectory_map):<br>- status: [MotionStatus](#galbot-sdk-motionstatus-enum)::SUCCESS if planning succeeds, error code otherwise<br>- trajectory_map: {chain_name -> waypoint_list}, smooth trajectory through all waypoints |

!!! note
    Collision semantics: same as motion_plan(). The collision world for Motion planning is built from user-loaded objects and is not updated by real-time perception automatically.

!!! note
    Planner ensures C1 continuity (continuous velocity) at waypoints.

!!! note
    Intermediate waypoints may not be exactly reached (blending); use multiple plans for exact passing.

### motion_plan_multi_waypoints {#galbotmotion-motion_plan_multi_waypoints-function}

```cpp
virtual std::tuple<MotionStatus, std::unordered_map<std::string, std::vector<std::vector<double> > > > galbot::sdk::GalbotMotion::motion_plan_multi_waypoints(
    std::unordered_map< std::shared_ptr< RobotStates >, std::vector< std::vector< double >>> targets,
    std::vector< std::shared_ptr< RobotStates >> start={},
    std::shared_ptr< RobotStates > reference_robot_states=nullptr,
    bool enable_collision_check=true,
    std::shared_ptr< Parameter > params=default_param
) =0
```

<small>Plan coordinated trajectories through waypoints for multiple chains.

Enables coordinated multi-arm or whole-body motion through waypoint sequences. Each chain can have its own waypoint sequence, executed in synchronized fashion.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `targets` | std::unordered_map< std::shared_ptr< [RobotStates](#robotstates-class) >, std::vector< std::vector< double >>> | Map of {state_template -> waypoint_list} for each chain. Keys are [RobotStates](#robotstates-class) (with chain_name set) defining waypoint type; values are waypoint sequences in same format as single-chain version. |
| `start` | std::vector< std::shared_ptr< [RobotStates](#robotstates-class) >> | Optional start states ([JointStates](#jointstates-class)) for each chain. Empty uses current state. Warning: For direct execution, leave empty. |
| `reference_robot_states` | std::shared_ptr< [RobotStates](#robotstates-class) > | Whole-body reference state for planning context. nullptr uses current state. Warning: For direct execution, leave as nullptr. |
| `enable_collision_check` | bool | If true, only returns collision-free trajectories |
| `params` | std::shared_ptr< [Parameter](#parameter-class) > | Planning parameters |

**Returns**

| Type | Description |
| --- | --- |
| std::tuple< [MotionStatus](#galbot-sdk-motionstatus-enum), std::unordered_map< std::string, std::vector< std::vector< double > > > > | Tuple of (status, trajectory_map):<br>- status: [MotionStatus](#galbot-sdk-motionstatus-enum)::SUCCESS if planning succeeds, error code otherwise<br>- trajectory_map: {chain_name -> waypoint_list} for all chains |

!!! note
    All chain trajectories are time-synchronized for coordinated execution.

!!! note
    Useful for bimanual manipulation or mobile manipulation tasks.

### move_whole_body_joint_zero {#galbotmotion-move_whole_body_joint_zero-function}

```cpp
virtual MotionStatus galbot::sdk::GalbotMotion::move_whole_body_joint_zero(
    bool is_blocking=true,
    double leg_head_speed_rad_s=0.2,
    double leg_head_timeout_s=15.0,
    std::shared_ptr< Parameter > params=default_param
) =0
```

<small>Move the whole-body joints to the predefined zero (home) configuration.

The leg and head joints are commanded via [GalbotRobot](#galbotrobot-class) (direct joint control), while the left/right arms are planned via the motion planner with collision checking enabled.

Joint order of the zero configuration follows the SDK convention: leg(5) + head(2) + left_arm(7) + right_arm(7).</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `is_blocking` | bool | Whether to block on leg/head execution and arm planning/execution. |
| `leg_head_speed_rad_s` | double | Max joint speed for leg/head direct control (rad/s). |
| `leg_head_timeout_s` | double | Timeout for leg/head direct control (seconds). |
| `params` | std::shared_ptr< [Parameter](#parameter-class) > | Motion planning parameters for arm planning (collision is forced enabled). |

**Returns**

| Type | Description |
| --- | --- |
| [MotionStatus](#galbot-sdk-motionstatus-enum) | [MotionStatus](#galbot-sdk-motionstatus-enum) Overall execution status. |

### check_collision {#galbotmotion-check_collision-function}

```cpp
virtual std::tuple<MotionStatus, std::vector<bool> > galbot::sdk::GalbotMotion::check_collision(
    const std::vector< std::shared_ptr< RobotStates >> &start,
    bool enable_collision_check=true,
    std::shared_ptr< Parameter > params=default_param
) =0
```

<small>Check robot states for collisions.

Therefore, if you need Motion to consider environmental obstacles (including point clouds), you must load the obstacle map/objects explicitly (e.g., obstacle_type = point_cloud with a file path in key).

Note: integrating real-time perception (navigation-style obstacle updates / point-cloud map) into galbotMotion is a planned future feature and has limited internal validation at the moment. Validates whether given robot configurations are collision-free. Checks both self-collisions (robot links with each other) and environment collisions (robot with scene obstacles). Batch processing supported for efficiency.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `start` | const std::vector< std::shared_ptr< [RobotStates](#robotstates-class) >> & | Vector of robot states to check. Each state can be: [RobotStates](#robotstates-class): complete whole-body configuration [JointStates](#jointstates-class): single-chain configuration (other joints use current state) |
| `enable_collision_check` | bool | If true, checks both self and environment collisions; if false, only checks self-collisions |
| `params` | std::shared_ptr< [Parameter](#parameter-class) > | Optional parameters |

**Returns**

| Type | Description |
| --- | --- |
| std::tuple< [MotionStatus](#galbot-sdk-motionstatus-enum), std::vector< bool > > | Tuple of (status, collision_results):<br>- status: [MotionStatus](#galbot-sdk-motionstatus-enum)::SUCCESS if check completes, error code otherwise<br>- collision_results: Boolean vector (same size as start): true = collision detected, false = collision-free |

!!! note
    [Obstacle perception & point-cloud usage: galbotNav vs galbotMotion]

!!! note
    Useful for validating planned trajectories or sampling-based planners.

!!! note
    Respects safe_margin settings in previously added obstacles.

### attach_tool {#galbotmotion-attach_tool-function}

```cpp
virtual MotionStatus galbot::sdk::GalbotMotion::attach_tool(
    const std::string &chain,
    const std::string &tool
) =0
```

<small>Attach a tool to an end-effector.

Loads a tool (gripper, camera, custom end-effector) onto a kinematic chain. Updates the kinematic model and collision geometry to include the tool.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `chain` | const std::string & | Kinematic chain for tool attachment (e.g., "left_arm", "right_arm") |
| `tool` | const std::string & | Tool identifier (must be predefined in tool library, see get_support_tool_list()) |

**Returns**

| Type | Description |
| --- | --- |
| [MotionStatus](#galbot-sdk-motionstatus-enum) | [MotionStatus](#galbot-sdk-motionstatus-enum):<br>- SUCCESS: Tool attached successfully<br>- INVALID_INPUT: Invalid chain or tool name<br>- FAULT: Tool attachment failed |

!!! note
    Tool transform and collision geometry must be pre-configured in robot description.

!!! note
    Attaching a new tool automatically detaches any previously attached tool on that chain.

!!! warning
    Kinematics and collision checking will reflect the attached tool; update plans accordingly.

### detach_tool {#galbotmotion-detach_tool-function}

```cpp
virtual MotionStatus galbot::sdk::GalbotMotion::detach_tool(const std::string &chain)=0
```

<small>Detach the current tool from an end-effector.

Removes the attached tool from a kinematic chain, reverting to the base end-effector. Updates kinematic model and collision geometry accordingly.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `chain` | const std::string & | Kinematic chain to detach tool from (e.g., "left_arm", "right_arm") |

**Returns**

| Type | Description |
| --- | --- |
| [MotionStatus](#galbot-sdk-motionstatus-enum) | [MotionStatus](#galbot-sdk-motionstatus-enum):<br>- SUCCESS: Tool detached successfully<br>- INVALID_INPUT: Invalid chain name or no tool attached<br>- FAULT: Tool detachment failed |

!!! note
    If no tool is attached, operation succeeds as a no-op.

### add_obstacle {#galbotmotion-add_obstacle-function}

```cpp
virtual MotionStatus galbot::sdk::GalbotMotion::add_obstacle(
    const std::string &obstacle_id,
    const std::string &obstacle_type,
    const std::vector< double > &pose,
    const std::array< double, 3 > &scale={},
    const std::string &key="",
    const std::string &target_frame="world",
    const std::string &ee_frame="ee_base",
    const std::vector< double > &reference_joint_positions={},
    const std::vector< double > &reference_base_pose={},
    const std::vector< std::string > &ignore_collision_link_names={},
    const double &safe_margin=0,
    const double &resolution=0.01
) =0
```

<small>Load collision object into environment.

Inserts a geometric or mesh-based obstacle into the environment for collision avoidance. Obstacles can be static (world-fixed) or robot-relative. Supports primitive shapes, meshes, point clouds, and depth images.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `obstacle_id` | const std::string & | Unique obstacle identifier (must not exist in scene). Used for later removal/updates. |
| `obstacle_type` | const std::string & | Obstacle geometry type (e.g., "box", "sphere", "cylinder", "mesh", "point_cloud", "depth_image"). See get_support_obstacle_type() for valid types. |
| `pose` | const std::vector< double > & | Obstacle pose: [x, y, z, qx, qy, qz, qw] (meters, quaternion) relative to target_frame. |
| `scale` | const std::array< double, 3 > & | Geometry dimensions (meters): box: [length, width, height] sphere: [radius, -, -] cylinder: [radius, height, -] mesh/point_cloud: scaling factors [sx, sy, sz] |
| `key` | const std::string & | [Type](#galbot-sdk-robotstates-type-enum)-specific data: mesh/point_cloud: file path (e.g., "/path/to/model.stl") depth_image: camera source ("front_head", "left_arm", "right_arm") primitives: unused, leave empty |
| `target_frame` | const std::string & | Reference frame for pose (default: "world"). Can be "world", "base_link", or chain name (e.g., "left_arm"). |
| `ee_frame` | const std::string & | If target_frame is a chain, specifies frame on chain: "ee_base" (end-effector), "camera_base", "camera_object". |
| `reference_joint_positions` | const std::vector< double > & | Robot joint state for computing frame transforms (radians). Empty uses current robot state. |
| `reference_base_pose` | const std::vector< double > & | Robot base pose in map frame: [x, y, z, qx, qy, qz, qw]. Empty uses current localization. |
| `ignore_collision_link_names` | const std::vector< std::string > & | Robot links to exclude from collision with this obstacle. Useful for carried objects or mounting surfaces. |
| `safe_margin` | const double & | Safety distance buffer (meters). Collision reported if distance < safe_margin. Default: 0 (contact-based). |
| `resolution` | const double & | Discretization resolution (meters) for complex geometries (mesh, point cloud, depth image). Default: 0.01m. |

**Returns**

| Type | Description |
| --- | --- |
| [MotionStatus](#galbot-sdk-motionstatus-enum) | [MotionStatus](#galbot-sdk-motionstatus-enum):<br>- SUCCESS: Obstacle added successfully<br>- INVALID_INPUT: Invalid obstacle_id (duplicate), type, or parameters<br>- FAULT: Failed to process geometry or add to scene |

!!! note
    Point-cloud note: point_cloud here refers to a point-cloud obstacle explicitly loaded via this API (typically from a file/offline data). It is NOT the same as a navigation-maintained point-cloud map. galbotMotion does not automatically subscribe to or synchronize with galbotNav's point-cloud map for collision.

!!! note
    Obstacles persist until explicitly removed or cleared.

!!! note
    For moving obstacles, remove and re-add at new poses (no update method currently).

!!! warning
    Large safe_margin values may over-constrain planning; use conservatively.

### remove_obstacle {#galbotmotion-remove_obstacle-function}

```cpp
virtual MotionStatus galbot::sdk::GalbotMotion::remove_obstacle(const std::string &obstacle_id)=0
```

<small>Remove a collision obstacle from the planning scene.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `obstacle_id` | const std::string & | Unique identifier of obstacle to remove (must exist in scene) |

**Returns**

| Type | Description |
| --- | --- |
| [MotionStatus](#galbot-sdk-motionstatus-enum) | [MotionStatus](#galbot-sdk-motionstatus-enum): SUCCESS, INVALID_INPUT (obstacle_id not found), or FAULT |

!!! note
    Removing a non-existent obstacle returns INVALID_INPUT (not silently ignored).

### clear_obstacle {#galbotmotion-clear_obstacle-function}

```cpp
virtual MotionStatus galbot::sdk::GalbotMotion::clear_obstacle()=0
```

<small>Remove all collision obstacles from the planning scene.

Clears the entire obstacle set, resetting the planning scene to empty (except robot geometry).</small>

**Returns**

| Type | Description |
| --- | --- |
| [MotionStatus](#galbot-sdk-motionstatus-enum) | [MotionStatus](#galbot-sdk-motionstatus-enum): SUCCESS or FAULT |

!!! note
    Attached objects (see attach_target_object) are not affected.

!!! note
    Safe to call even if scene is already empty.

### attach_target_object {#galbotmotion-attach_target_object-function}

```cpp
virtual MotionStatus galbot::sdk::GalbotMotion::attach_target_object(
    const std::string &obstacle_id,
    const std::string &obstacle_type,
    const std::vector< double > &pose,
    const std::array< double, 3 > &scale={},
    const std::string &key="",
    const std::string &target_frame="world",
    const std::string &ee_frame="ee_base",
    const std::vector< double > &reference_joint_positions={},
    const std::vector< double > &reference_base_pose={},
    const std::vector< std::string > &ignore_collision_link_names={},
    const double &safe_margin=0,
    const double &resolution=0.01
) =0
```

<small>Attach a collision object to the robot (e.g., grasped object).

Similar to add_obstacle(), but the object moves with the robot (attached to a link/chain). Used for representing grasped objects, sensors, or payloads. The object's pose is maintained relative to the attachment frame during motion.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `obstacle_id` | const std::string & | Unique object identifier (must not exist in scene). |
| `obstacle_type` | const std::string & | Object geometry type (e.g., "box", "sphere", "mesh"). See get_support_obstacle_type() for valid types. |
| `pose` | const std::vector< double > & | Object pose: [x, y, z, qx, qy, qz, qw] (meters, quaternion) relative to target_frame at attachment time. |
| `scale` | const std::array< double, 3 > & | Geometry dimensions (meters): box: [length, width, height] sphere: [radius, -, -] cylinder: [radius, height, -] |
| `key` | const std::string & | [Type](#galbot-sdk-robotstates-type-enum)-specific data (e.g., mesh file path for "mesh" type). |
| `target_frame` | const std::string & | Attachment frame (default: "world"). Typically a chain name (e.g., "left_arm") for grasped objects. |
| `ee_frame` | const std::string & | If target_frame is a chain, specifies frame on chain ("ee_base", "camera_base", etc.). |
| `reference_joint_positions` | const std::vector< double > & | Robot joint state for computing attachment transform (radians). Empty uses current robot state. |
| `reference_base_pose` | const std::vector< double > & | Robot base pose in map: [x, y, z, qx, qy, qz, qw]. Empty uses current localization. |
| `ignore_collision_link_names` | const std::vector< std::string > & | Robot links to exclude from collision with this object. Typically includes the grasping end-effector links. |
| `safe_margin` | const double & | Safety distance buffer (meters). Default: 0. |
| `resolution` | const double & | Discretization resolution for complex geometries (meters). Default: 0.01m. |

**Returns**

| Type | Description |
| --- | --- |
| [MotionStatus](#galbot-sdk-motionstatus-enum) | [MotionStatus](#galbot-sdk-motionstatus-enum): SUCCESS, INVALID_INPUT, or FAULT |

!!! note
    Point-cloud note: same as add_obstacle(). point_cloud here is an explicitly loaded point-cloud object and will not be automatically synchronized with any navigation-side point-cloud map.

!!! note
    Attached objects move with the robot; their collision geometry is updated automatically.

!!! note
    Typically used in pick-and-place: attach_target_object after grasp, detach after release.

!!! warning
    Ensure ignore_collision_link_names includes grasping links to avoid false collisions.

### detach_target_object {#galbotmotion-detach_target_object-function}

```cpp
virtual MotionStatus galbot::sdk::GalbotMotion::detach_target_object(const std::string &obstacle_id)=0
```

<small>Detach an object from the robot (e.g., after release).

Removes an attached object from the robot. Typically called after releasing a grasped object. The object is removed from the planning scene entirely (not converted to a static obstacle).</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `obstacle_id` | const std::string & | Unique identifier of attached object to remove |

**Returns**

| Type | Description |
| --- | --- |
| [MotionStatus](#galbot-sdk-motionstatus-enum) | [MotionStatus](#galbot-sdk-motionstatus-enum): SUCCESS, INVALID_INPUT (obstacle_id not found), or FAULT |

!!! note
    To keep the object in the scene as a static obstacle after release, call detach_target_object() then add_obstacle() with the object's final pose.

### set_motion_plan_config {#galbotmotion-set_motion_plan_config-function}

```cpp
virtual MotionStatus galbot::sdk::GalbotMotion::set_motion_plan_config(
    std::shared_ptr< MotionPlanConfig > config
) =0
```

<small>Set global motion planning configuration.

Updates planner settings such as velocity/acceleration limits, planning algorithm parameters, and optimization objectives. Affects all subsequent planning operations.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `config` | std::shared_ptr< [MotionPlanConfig](#motionplanconfig-class) > | Shared pointer to [MotionPlanConfig](#motionplanconfig-class) with desired settings |

**Returns**

| Type | Description |
| --- | --- |
| [MotionStatus](#galbot-sdk-motionstatus-enum) | [MotionStatus](#galbot-sdk-motionstatus-enum):<br>- SUCCESS: Configuration applied successfully<br>- INVALID_INPUT: Invalid configuration parameters<br>- FAULT: Configuration update failed |

!!! note
    Changes persist until explicitly reset or process restart.

!!! note
    See MotionPlanConfig documentation for available parameters.

### get_motion_plan_config {#galbotmotion-get_motion_plan_config-function}

```cpp
virtual std::tuple<MotionStatus, MotionPlanConfig> galbot::sdk::GalbotMotion::get_motion_plan_config()=0
```

<small>Get current motion planning configuration.

Retrieves the active planner configuration, including velocity/acceleration limits and planning algorithm parameters.</small>

**Returns**

| Type | Description |
| --- | --- |
| std::tuple< [MotionStatus](#galbot-sdk-motionstatus-enum), [MotionPlanConfig](#motionplanconfig-class) > | Tuple of (status, config):<br>- status: [MotionStatus](#galbot-sdk-motionstatus-enum)::SUCCESS on success, error code otherwise<br>- config: Current [MotionPlanConfig](#motionplanconfig-class) object (default-constructed on failure) |

!!! note
    Useful for inspecting current limits or saving/restoring configurations.

### get_link_names {#galbotmotion-get_link_names-function}

```cpp
virtual std::vector<std::string> galbot::sdk::GalbotMotion::get_link_names(bool only_end_effector=false)=0
```

<small>Get robot link names from kinematic model.

Retrieves the list of link names defined in the robot's URDF model. Can filter to only end-effector links or return all links.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `only_end_effector` | bool | If true, returns only end-effector/tool links; if false, returns all links including base, intermediate, and end-effector links. Default: false (all links). |

**Returns**

| Type | Description |
| --- | --- |
| std::vector< std::string > | Vector of link name strings (empty if retrieval fails) |

!!! note
    End-effector detection based on link having no child links in kinematic tree.

!!! note
    Useful for forward kinematics queries or TF frame validation.

### get_support_links {#galbotmotion-get_support_links-function}

```cpp
virtual const std::set<std::string>& galbot::sdk::GalbotMotion::get_support_links()=0
```

<small>Get set of valid link names in robot model.

Returns all link names defined in the loaded URDF kinematic model. Useful for validating forward kinematics queries or TF lookups.</small>

**Returns**

| Type | Description |
| --- | --- |
| const std::set< std::string > & | Const reference to set of supported link name strings |

!!! note
    Set is populated during initialization from robot URDF.

### get_support_chains {#galbotmotion-get_support_chains-function}

```cpp
virtual const std::set<std::string>& galbot::sdk::GalbotMotion::get_support_chains()=0
```

<small>Get set of valid kinematic chain names.

Returns the names of all predefined kinematic chains (e.g., "left_arm", "right_arm", "torso", "left_leg", "right_leg"). Chains are groups of joints treated as a unit for planning and control.</small>

**Returns**

| Type | Description |
| --- | --- |
| const std::set< std::string > & | Const reference to set of supported chain name strings |

!!! note
    Chain definitions are specified in robot configuration files.

### get_support_frame {#galbotmotion-get_support_frame-function}

```cpp
virtual const std::set<std::string>& galbot::sdk::GalbotMotion::get_support_frame()=0
```

<small>Get set of valid reference frame names.

Returns standard reference frames supported for pose specifications (e.g., "base_link", "world", "odom").</small>

**Returns**

| Type | Description |
| --- | --- |
| const std::set< std::string > & | Const reference to set of supported reference frame name strings |

!!! note
    These are global/base frames; individual link frames accessed via TF.

### get_support_ee_frame {#galbotmotion-get_support_ee_frame-function}

```cpp
virtual const std::set<std::string>& galbot::sdk::GalbotMotion::get_support_ee_frame()=0
```

<small>Get set of valid end-effector frame types.

Returns frame identifiers that can be specified for end-effector poses (e.g., "EndEffector", "Camera", "TCP"). These are frame types, not specific link names.</small>

**Returns**

| Type | Description |
| --- | --- |
| const std::set< std::string > & | Const reference to set of supported end-effector frame type strings |

!!! note
    Actual link names derived by combining chain name + frame type.

### get_support_tool_list {#galbotmotion-get_support_tool_list-function}

```cpp
virtual const std::set<std::string>& galbot::sdk::GalbotMotion::get_support_tool_list()=0
```

<small>Get list of available tools that can be attached.

Returns names of predefined tools (grippers, sensors, custom end-effectors) that can be attached via attach_tool().</small>

**Returns**

| Type | Description |
| --- | --- |
| const std::set< std::string > & | Const reference to set of tool name strings |

!!! note
    Tools must be pre-configured with geometry and kinematic offsets.

### get_support_obstacle_type {#galbotmotion-get_support_obstacle_type-function}

```cpp
virtual std::set<std::string> galbot::sdk::GalbotMotion::get_support_obstacle_type()=0
```

<small>Get list of supported collision obstacle geometry types.

Returns geometry types supported by add_obstacle() and attach_target_object() (e.g., "box", "sphere", "cylinder", "mesh", "point_cloud", "depth_image").</small>

**Returns**

| Type | Description |
| --- | --- |
| std::set< std::string > | Set of supported obstacle type strings |

!!! note
    Different types require different scale/key parameter formats.

### get_built_object_list {#galbotmotion-get_built_object_list-function}

```cpp
virtual std::vector<std::string> galbot::sdk::GalbotMotion::get_built_object_list()=0
```

<small>Get list of currently added obstacles in planning scene.

Returns the obstacle IDs of all obstacles currently present in the scene (both static obstacles and attached objects).</small>

**Returns**

| Type | Description |
| --- | --- |
| std::vector< std::string > | Vector of obstacle ID strings (empty if no obstacles) |

!!! note
    Useful for debugging scene state or preventing duplicate IDs.

### get_attached_object_list {#galbotmotion-get_attached_object_list-function}

```cpp
virtual std::vector<std::string> galbot::sdk::GalbotMotion::get_attached_object_list()=0
```

<small>Get list of currently attached objects on the robot.

Returns the obstacle IDs of all objects currently attached to the robot (via attach_target_object()).</small>

**Returns**

| Type | Description |
| --- | --- |
| std::vector< std::string > | Vector of attached object ID strings (empty if none attached) |

!!! note
    Useful for tracking grasped objects or payloads.

### is_link_name_valid {#galbotmotion-is_link_name_valid-function}

```cpp
virtual bool galbot::sdk::GalbotMotion::is_link_name_valid(
    const std::string &value,
    bool throw_exception=false
) =0
```

<small>Validate link name against robot model.

Checks if the provided link name exists in the loaded URDF model.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | const std::string & | Link name to validate |
| `throw_exception` | bool | If true, throws std::invalid_argument on validation failure; if false, returns false silently. Default: false. |

**Returns**

| Type | Description |
| --- | --- |
| bool | true if link name is valid, false otherwise |

!!! note
    Use get_support_links() to retrieve valid link names.

### is_chain_name_valid {#galbotmotion-is_chain_name_valid-function}

```cpp
virtual bool galbot::sdk::GalbotMotion::is_chain_name_valid(
    const std::string &value,
    bool throw_exception=false
) =0
```

<small>Validate kinematic chain name.

Checks if the provided chain name is defined in robot configuration.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | const std::string & | Chain name to validate (e.g., "left_arm", "right_arm") |
| `throw_exception` | bool | If true, throws exception on failure. Default: false. |

**Returns**

| Type | Description |
| --- | --- |
| bool | true if chain name is valid, false otherwise |

!!! note
    Use get_support_chains() to retrieve valid chain names.

### is_frame_name_valid {#galbotmotion-is_frame_name_valid-function}

```cpp
virtual bool galbot::sdk::GalbotMotion::is_frame_name_valid(
    const std::string &value,
    bool throw_exception=false
) =0
```

<small>Validate reference frame name.

Checks if the provided frame name is a valid reference frame for pose specifications.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | const std::string & | Frame name to validate (e.g., "base_link", "world") |
| `throw_exception` | bool | If true, throws exception on failure. Default: false. |

**Returns**

| Type | Description |
| --- | --- |
| bool | true if frame name is valid, false otherwise |

!!! note
    Use get_support_frame() to retrieve valid frame names.

### is_ee_frame_valid {#galbotmotion-is_ee_frame_valid-function}

```cpp
virtual bool galbot::sdk::GalbotMotion::is_ee_frame_valid(
    const std::string &value,
    bool throw_exception=false
) =0
```

<small>Validate end-effector frame type.

Checks if the provided frame type is valid for end-effector specifications.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | const std::string & | Frame type to validate (e.g., "EndEffector", "Camera", "TCP") |
| `throw_exception` | bool | If true, throws exception on failure. Default: false. |

**Returns**

| Type | Description |
| --- | --- |
| bool | true if frame type is valid, false otherwise |

!!! note
    Use get_support_ee_frame() to retrieve valid frame types.

### is_tool_name_valid {#galbotmotion-is_tool_name_valid-function}

```cpp
virtual bool galbot::sdk::GalbotMotion::is_tool_name_valid(
    const std::string &value,
    bool throw_exception=false
) =0
```

<small>Validate tool name.

Checks if the provided tool name is available for attachment.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | const std::string & | Tool name to validate |
| `throw_exception` | bool | If true, throws exception on failure. Default: false. |

**Returns**

| Type | Description |
| --- | --- |
| bool | true if tool name is valid, false otherwise |

!!! note
    Use get_support_tool_list() to retrieve available tools.

### is_obstacle_type_valid {#galbotmotion-is_obstacle_type_valid-function}

```cpp
virtual bool galbot::sdk::GalbotMotion::is_obstacle_type_valid(
    const std::string &value,
    bool throw_exception=false
) =0
```

<small>Validate obstacle geometry type.

Checks if the provided type is supported for obstacle creation.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | const std::string & | Obstacle type to validate (e.g., "box", "sphere", "mesh") |
| `throw_exception` | bool | If true, throws exception on failure. Default: false. |

**Returns**

| Type | Description |
| --- | --- |
| bool | true if obstacle type is valid, false otherwise |

!!! note
    Use get_support_obstacle_type() to retrieve supported types.

### is_whole_body_state_valid {#galbotmotion-is_whole_body_state_valid-function}

```cpp
virtual bool galbot::sdk::GalbotMotion::is_whole_body_state_valid(
    const std::vector< double > &value,
    bool throw_exception=false
) =0
```

<small>Validate whole-body joint configuration vector.

Checks if the provided vector has the correct size (robot DOF) for whole-body state.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | const std::vector< double > & | Joint configuration vector (radians) to validate |
| `throw_exception` | bool | If true, throws exception on failure. Default: false. |

**Returns**

| Type | Description |
| --- | --- |
| bool | true if vector size matches robot DOF, false otherwise |

!!! note
    Expected size: get_robot_dof() elements.

!!! note
    Does not validate joint limit compliance, only vector dimensionality.

### is_pose_7d_valid {#galbotmotion-is_pose_7d_valid-function}

```cpp
virtual bool galbot::sdk::GalbotMotion::is_pose_7d_valid(
    const std::vector< double > &value,
    bool throw_exception=false
) =0
```

<small>Validate 7D pose vector (position + quaternion).

Checks if the provided pose vector has exactly 7 elements: [x, y, z, qx, qy, qz, qw].</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | const std::vector< double > & | [Pose](#pose-struct) vector to validate |
| `throw_exception` | bool | If true, throws exception on failure. Default: false. |

**Returns**

| Type | Description |
| --- | --- |
| bool | true if vector size is 7, false otherwise |

!!! note
    Does not enforce quaternion normalization; only checks dimensionality.

!!! warning
    Using non-normalized quaternions will cause undefined behavior in kinematics.

### is_chain_joint_state_valid {#galbotmotion-is_chain_joint_state_valid-function}

```cpp
virtual bool galbot::sdk::GalbotMotion::is_chain_joint_state_valid(
    const std::unordered_map< std::string, std::vector< double >> &value,
    bool throw_exception=false
) =0
```

<small>Validate chain-indexed joint configuration map.

Checks if chain names are valid and joint vectors have correct dimensions for each chain.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | const std::unordered_map< std::string, std::vector< double >> & | Map of {chain_name -> joint_configuration} to validate |
| `throw_exception` | bool | If true, throws exception on failure. Default: false. |

**Returns**

| Type | Description |
| --- | --- |
| bool | true if all chain names and vector sizes are valid, false otherwise |

!!! note
    Validates both chain name existence and joint vector dimensionality per chain.

### get_robot_dof {#galbotmotion-get_robot_dof-function}

```cpp
virtual int galbot::sdk::GalbotMotion::get_robot_dof()=0
```

<small>Get robot total degrees of freedom (DOF).

Returns the number of actuated joints in the complete robot (whole-body). Used for validating joint state vector dimensions.</small>

**Returns**

| Type | Description |
| --- | --- |
| int | Number of robot DOF (actuated joints) |

!!! note
    Typical humanoid/mobile manipulator: 15-30 DOF.

### get_robot_states {#galbotmotion-get_robot_states-function}

```cpp
virtual RobotStates galbot::sdk::GalbotMotion::get_robot_states()=0
```

<small>Get current complete robot state.

Retrieves the current whole-body joint configuration and mobile base pose. Represents the full kinematic state of the robot.</small>

**Returns**

| Type | Description |
| --- | --- |
| [RobotStates](#robotstates-class) | object containing:<br>- whole_body_joint: complete joint configuration (radians)<br>- base_state: mobile base pose [x, y, z, qx, qy, qz, qw] (meters, quaternion) |

!!! note
    Reflects actual robot state (from sensor feedback/state estimation).

!!! note
    Useful as seed/reference for planning operations.

### get_whole_body_state {#galbotmotion-get_whole_body_state-function}

```cpp
virtual std::vector<double> galbot::sdk::GalbotMotion::get_whole_body_state()=0
```

<small>Get current whole-body joint configuration.

Retrieves joint angles for all actuated joints in the robot.</small>

**Returns**

| Type | Description |
| --- | --- |
| std::vector< double > | Vector of joint angles (radians), size = |

!!! note
    Joint ordering defined by robot URDF/configuration.

### get_chassis_state {#galbotmotion-get_chassis_state-function}

```cpp
virtual std::vector<double> galbot::sdk::GalbotMotion::get_chassis_state()=0
```

<small>Get current mobile base pose.

Retrieves the position and orientation of the robot's mobile base in the map frame.</small>

**Returns**

| Type | Description |
| --- | --- |
| std::vector< double > | Base pose vector: [x, y, z, qx, qy, qz, qw] (meters, unit quaternion) |

!!! note
    For non-mobile robots, typically returns identity pose.

!!! note
    Pose obtained from localization/odometry system.

### get_chain_joint_state {#galbotmotion-get_chain_joint_state-function}

```cpp
virtual std::unordered_map<std::string, std::vector<double> > galbot::sdk::GalbotMotion::get_chain_joint_state() =0
```

<small>Get current joint configurations for all kinematic chains.

Retrieves per-chain joint states, decomposing the whole-body configuration into individual chain contributions.</small>

**Returns**

| Type | Description |
| --- | --- |
| std::unordered_map< std::string, std::vector< double > > | Map of {chain_name -> joint_configuration} (radians) for each chain (e.g., {"left_arm" -> [7 joint angles], "right_arm" -> [7 joint angles]}) |

!!! note
    Joint vector sizes vary by chain DOF.

### get_chain_pose_state {#galbotmotion-get_chain_pose_state-function}

```cpp
virtual std::unordered_map<std::string, std::vector<double> > galbot::sdk::GalbotMotion::get_chain_pose_state(
    const std::string &frame="base_link"
) =0
```

<small>Get current Cartesian poses for all kinematic chains.

Computes forward kinematics for all chain end-effectors, returning their poses in the specified reference frame.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `frame` | const std::string & | Reference frame for pose expression (default: "base_link") |

**Returns**

| Type | Description |
| --- | --- |
| std::unordered_map< std::string, std::vector< double > > | Map of {chain_name -> pose_vector}, where pose_vector is [x, y, z, qx, qy, qz, qw] (meters, quaternion) for each chain's end-effector |

!!! note
    Computationally more expensive than get_chain_joint_state() (requires FK computation).

### replace_joint_state {#galbotmotion-replace_joint_state-function}

```cpp
virtual bool galbot::sdk::GalbotMotion::replace_joint_state(
    const std::string &chain_name,
    const std::vector< double > &chain_joint,
    std::vector< double > &whole_body_joint
) =0
```

<small>Update a specific chain's joints in a whole-body configuration.

Utility function for modifying a chain's joint values within a complete whole-body joint vector, while preserving other chains' states.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `chain_name` | const std::string & | Chain identifier whose joints to replace |
| `chain_joint` | const std::vector< double > & | New joint configuration for the chain (radians) |
| `whole_body_joint` | std::vector< double > & | Whole-body joint vector to modify (in/out parameter) |

**Returns**

| Type | Description |
| --- | --- |
| bool | true if replacement succeeds, false if chain_name invalid or size mismatch |

!!! note
    whole_body_joint is modified in-place; ensure it has correct size (get_robot_dof()).

!!! note
    Useful for offline state manipulation or custom planning seeds.

### status_to_string {#galbotmotion-status_to_string-function}

```cpp
virtual std::string galbot::sdk::GalbotMotion::status_to_string(MotionStatus status)=0
```

<small>Convert [MotionStatus](#galbot-sdk-motionstatus-enum) enum to human-readable string.

Maps status codes to descriptive strings for logging, error reporting, or UI display.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `status` | [MotionStatus](#galbot-sdk-motionstatus-enum) | [MotionStatus](#galbot-sdk-motionstatus-enum) enumeration value |

**Returns**

| Type | Description |
| --- | --- |
| std::string | Descriptive status string (e.g., "SUCCESS: Execution succeeded", "TIMEOUT: Execution timeout") |

!!! note
    Uses status_string_map_ for lookup; returns "UNKNOWN" if status not found.

### get_instance {#galbotmotion-get_instance-function}

```cpp
static GalbotMotion& galbot::sdk::GalbotMotion::get_instance(MachineType m)
```

<small>Runtime factory for selecting a concrete motion planning singleton.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `m` | [MachineType](#galbot-sdk-machinetype-enum) | Machine type identifier (e.g. [MachineType](#galbot-sdk-machinetype-enum)::G1, [MachineType](#galbot-sdk-machinetype-enum)::S1). |

**Returns**

| Type | Description |
| --- | --- |
| [GalbotMotion](#galbotmotion-class) & | Reference to the singleton motion interface for the specified machine type. |


---

<a id="module-galbotnavigation"></a>

## GalbotNavigation {#galbotnavigation-class}

<small>Navigation interface for mobile robot chassis motion planning and localization.

This class provides a thread-safe singleton interface for controlling the mobile base navigation system. It supports 2D pose estimation, relocalization, goal-directed navigation with dynamic obstacle avoidance, and path planning capabilities. The navigation system operates in a global map frame and provides both blocking and non-blocking navigation modes. It supports both differential drive and omnidirectional motion planning strategies. This class uses the singleton pattern with thread-safe initialization. All pose coordinates are specified in the map frame unless explicitly stated otherwise. Typical usage: auto&nav=[GalbotNavigation](#galbotnavigation-class)::get_instance([MachineType](#galbot-sdk-machinetype-enum)::G1); if(nav.init()){ Posegoal; goal.x=1.0;//meters goal.y=2.0;//meters goal.orientation.w=1.0;//identityquaternion(x,y,zdefault0) nav.navigate_to_goal(goal,true,false,30.0,true); }</small>

### ~GalbotNavigation {#galbotnavigation-galbotnavigation-function}

```cpp
virtual galbot::sdk::GalbotNavigation::~GalbotNavigation()=default
```

### init {#galbotnavigation-init-function}

```cpp
virtual bool galbot::sdk::GalbotNavigation::init()=0
```

<small>Initialize the navigation subsystem and its dependencies.

This method must be called before using any other navigation functions. It initializes communication channels, loads the map, starts the localization module, and prepares the path planner.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | true if initialization succeeded, false otherwise. |

!!! note
    This method should only be called once after obtaining the singleton instance.

!!! note
    Subsequent calls will return the result of the first initialization attempt.

!!! warning
    Calling navigation methods before successful initialization will result in undefined behavior.

### relocalize {#galbotnavigation-relocalize-function}

```cpp
virtual NavigationStatus galbot::sdk::GalbotNavigation::relocalize(const Pose &init_pose)=0
```

<small>Perform relocalization to re-estimate the robot's pose in the map frame.

This method resets the localization filter and provides an initial pose estimate to help the robot re-establish its position in the known map. This is useful when the robot has lost localization or when manually placing the robot at a known position.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `init_pose` | const [Pose](#pose-struct) & | Initial pose estimate in the map frame: position (x, y, z) in meters and orientation as unit quaternion (x, y, z, w). Serves as the starting point for the relocalization algorithm. |

**Returns**

| Type | Description |
| --- | --- |
| [NavigationStatus](#galbot-sdk-navigationstatus-enum) | [NavigationStatus](#galbot-sdk-navigationstatus-enum) indicating the result of the relocalization request. See [NavigationStatus](#galbot-sdk-navigationstatus-enum) enumeration for possible values. |

!!! note
    The robot should be stationary during relocalization for best results.

!!! note
    After calling this method, use is_localized() to verify successful relocalization before proceeding with navigation tasks.

### is_localized {#galbotnavigation-is_localized-function}

```cpp
virtual bool galbot::sdk::GalbotNavigation::is_localized()=0
```

<small>Check whether the robot is currently localized in the map.

This method queries the localization system to determine if the robot has a valid pose estimate with sufficient confidence. A robot that is not localized should not perform navigation tasks.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | true if the robot is localized with acceptable confidence, false if localization is lost or uncertain. |

!!! note
    It is recommended to check localization status before issuing navigation commands.

!!! note
    If this returns false, consider calling relocalize() with a known pose estimate.

### get_current_pose {#galbotnavigation-get_current_pose-function}

```cpp
virtual Pose galbot::sdk::GalbotNavigation::get_current_pose()=0
```

<small>Get the current estimated pose of the robot chassis in the map frame.

This method returns the most recent pose estimate from the localization system. The pose represents the position and orientation of the robot's base_link frame relative to the map frame origin.</small>

**Returns**

| Type | Description |
| --- | --- |
| [Pose](#pose-struct) | : position (x, y, z) in meters and orientation as unit quaternion (x, y, z, w) in the map frame. |

!!! note
    The returned pose is only valid if is_localized() returns true.

!!! note
    The pose represents the center of the robot's base footprint.

### navigate_to_goal {#galbotnavigation-navigate_to_goal-function}

```cpp
virtual NavigationStatus galbot::sdk::GalbotNavigation::navigate_to_goal(
    const Pose &goal_pose,
    bool enable_collision_check=true,
    bool is_blocking=false,
    float timeout=8,
    bool omni_plan=true
) =0
```

<small>Navigate the robot to a target goal pose in the map frame.

This method commands the mobile base to navigate to a specified goal pose using the global path planner and local trajectory controller. The planner will compute a collision-free path from the current pose to the goal, considering both static map obstacles and dynamic obstacles if collision checking is enabled.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `goal_pose` | const [Pose](#pose-struct) & | Target goal pose in the map frame: position (x, y, z) in meters and target orientation as unit quaternion (x, y, z, w). |
| `enable_collision_check` | bool | If true, enables dynamic obstacle detection and avoidance during navigation. If false, only static map obstacles are considered. Default: true. |
| `is_blocking` | bool | Execution mode flag. Default: false. false (non-blocking): Returns immediately after sending the navigation command. The return status indicates whether the command was successfully sent, not whether the goal was reached. true (blocking): Blocks until the goal is reached, navigation fails, or timeout occurs. The return status reflects the final navigation outcome. |
| `timeout` | float | Maximum wait time in seconds for blocking mode. Default: 8.0 seconds. Only relevant when is_blocking is true. If the goal is not reached within this time, the method returns with a timeout status. |
| `omni_plan` | bool | Motion planning mode flag. Default: true. true: Enables omnidirectional motion planning (holonomic drive), allowing the robot to move in any direction and rotate independently. false: Uses differential drive planning with kinematic constraints. |

**Returns**

| Type | Description |
| --- | --- |
| [NavigationStatus](#galbot-sdk-navigationstatus-enum) | [NavigationStatus](#galbot-sdk-navigationstatus-enum) indicating the result:<br>- In non-blocking mode: Command acceptance status<br>- In blocking mode: Final navigation outcome (success, failure, timeout) |

!!! note
    The robot must be localized (is_localized() returns true) before calling this method.

!!! note
    For blocking mode, the calling thread will be blocked until completion or timeout.

!!! note
    The actual navigation time may exceed the timeout value in blocking mode before the method returns.

!!! warning
    In non-blocking mode, monitor navigation progress separately to detect completion or failures.

### move_straight_to {#galbotnavigation-move_straight_to-function}

```cpp
virtual NavigationStatus galbot::sdk::GalbotNavigation::move_straight_to(
    const Pose &goal_pose,
    bool is_blocking=true,
    float timeout=8
) =0
```

<small>Move the robot to a relative target pose in the odometry frame.

This method commands the robot to move to a pose specified relative to its current position in the odometry (odom) frame. This is useful for short, precise movements where map-based planning is not needed. Unlike navigate_to_goal(), this method does NOT perform dynamic obstacle detection or global path planning. It uses omnidirectional motion planning for direct movement to the target.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `goal_pose` | const [Pose](#pose-struct) & | Target pose relative to the current base_link frame: position (x, y, z) in meters (typically x forward, y left, z up) and relative orientation as unit quaternion (x, y, z, w). |
| `is_blocking` | bool | Execution mode flag. Default: true. true (blocking): Blocks until the motion is complete, fails, or timeout occurs. The return status reflects the final outcome. false (non-blocking): Returns immediately after sending the motion command. The return status indicates command acceptance. |
| `timeout` | float | Maximum wait time in seconds for blocking mode. Default: 8.0 seconds. Only relevant when is_blocking is true. |

**Returns**

| Type | Description |
| --- | --- |
| [NavigationStatus](#galbot-sdk-navigationstatus-enum) | [NavigationStatus](#galbot-sdk-navigationstatus-enum) indicating the result:<br>- In non-blocking mode: Command acceptance status<br>- In blocking mode: Final motion outcome (success, failure, timeout) |

!!! note
    This method does NOT check for obstacles or collisions. Use only when the path is known to be clear.

!!! note
    This method uses the odometry frame and does NOT require map localization.

!!! note
    Suitable for small, precise adjustments such as final approach positioning or docking maneuvers.

!!! warning
    Since collision checking is disabled, ensure the path is obstacle-free before calling this method to avoid collisions.

!!! warning
    Odometry drift may affect accuracy over longer distances. For accurate long-distance navigation, use navigate_to_goal() instead.

### stop_navigation {#galbotnavigation-stop_navigation-function}

```cpp
virtual NavigationStatus galbot::sdk::GalbotNavigation::stop_navigation()=0
```

<small>Stop the current navigation task and bring the robot to a halt.

This method immediately cancels any ongoing navigation command (from either navigate_to_goal() or move_straight_to()) and commands the robot to stop. The robot will decelerate according to its kinematic constraints and come to a safe stop.</small>

**Returns**

| Type | Description |
| --- | --- |
| [NavigationStatus](#galbot-sdk-navigationstatus-enum) | [NavigationStatus](#galbot-sdk-navigationstatus-enum) indicating whether the stop command was successfully sent to the navigation system. |

!!! note
    This method can be called at any time during navigation, including when using non-blocking navigation modes.

!!! note
    After stopping, the robot's position may not match the original goal.

!!! note
    The robot will attempt to stop smoothly following its acceleration limits.

### check_path_reachability {#galbotnavigation-check_path_reachability-function}

```cpp
virtual bool galbot::sdk::GalbotNavigation::check_path_reachability(
    const Pose &goal_pose,
    const Pose &start_pose
) =0
```

<small>Check if a collision-free path exists from start to goal in the map.

This method queries the global path planner to determine if a valid, collision-free path exists between the specified start and goal poses. This is useful for validating goal poses before attempting navigation, or for multi-goal path planning.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `goal_pose` | const [Pose](#pose-struct) & | Goal pose in the map frame: position (x, y, z) in meters and orientation quaternion (x, y, z, w). |
| `start_pose` | const [Pose](#pose-struct) & | Start pose in the map frame: position (x, y, z) in meters and orientation quaternion (x, y, z, w). |

**Returns**

| Type | Description |
| --- | --- |
| bool | true if a collision-free path exists from start to goal, false if no valid path can be found. |

!!! note
    This method only checks for static obstacles based on the map data. Dynamic obstacles are not considered.

!!! note
    The path computation may take some time depending on distance and map complexity.

!!! note
    A return value of true does not guarantee successful navigation, as dynamic obstacles or localization errors may still cause failures.

### check_goal_arrival {#galbotnavigation-check_goal_arrival-function}

```cpp
virtual bool galbot::sdk::GalbotNavigation::check_goal_arrival()=0
```

<small>Check if the robot has successfully reached the current goal.

This method queries the navigation system to determine if the robot has arrived at the goal pose within acceptable position and orientation tolerances. This is particularly useful when using non-blocking navigation mode to poll for completion.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | true if the robot has reached the goal within tolerance thresholds, false if still navigating, no active goal, or goal not yet reached. |

!!! note
    This method is most useful in non-blocking navigation scenarios where the application needs to monitor progress.

!!! note
    The tolerance thresholds for "arrival" are defined by the navigation system's internal parameters (typically a few centimeters in position and a few degrees in orientation).

!!! note
    If no navigation command is active, this method returns false.

### get_navigation_status {#galbotnavigation-get_navigation_status-function}

```cpp
virtual NavigationTaskStatus galbot::sdk::GalbotNavigation::get_navigation_status()=0
```

<small>Get the current navigation task state.

Returns the most recent task state reported by the navigation system (UNKNOWN, RUNNING, SUCCESS, or FAILED). Use this when running non-blocking navigation to poll for state and exit error logic in time on FAILED or timeout, avoiding deadlock or indefinite wait.</small>

**Returns**

| Type | Description |
| --- | --- |
| [NavigationTaskStatus](#galbot-sdk-navigationtaskstatus-enum) | [NavigationTaskStatus](#galbot-sdk-navigationtaskstatus-enum) Current task state. UNKNOWN if no status yet; RUNNING while navigating; SUCCESS or FAILED when task has finished. |

!!! note
    Useful in non-blocking navigation: loop on get_navigation_status() and break on SUCCESS, FAILED, or after a timeout.

### get_instance {#galbotnavigation-get_instance-function}

```cpp
static GalbotNavigation& galbot::sdk::GalbotNavigation::get_instance(MachineType m)
```

<small>Runtime factory for selecting a concrete navigation singleton.

This static factory method allows runtime selection of the navigation implementation based on the robot machine type. The method declaration resides in the interface header for compile-time availability, while the actual implementation logic (including platform-specific includes and switch statements) is contained in the corresponding .cpp file. This design keeps the interface clean while enabling platform-specific instantiation without exposing implementation details.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `m` | [MachineType](#galbot-sdk-machinetype-enum) | Machine type identifier specifying which robot platform to use. |

**Returns**

| Type | Description |
| --- | --- |
| [GalbotNavigation](#galbotnavigation-class) & | Reference to the singleton navigation interface instance for the specified machine type. |

!!! note
    Adding support for a new machine type requires updating the MachineType enumeration and the factory implementation in the .cpp file.


---

<a id="module-galbotperception"></a>

## GalbotPerception {#galbotperception-class}

<small>Perception module interface; obtain the singleton via get_instance([MachineType](#galbot-sdk-machinetype-enum)).

Implemented for G1 only: get_instance([MachineType](#galbot-sdk-machinetype-enum)::S1) throws std::runtime_error.</small>

### ~GalbotPerception {#galbotperception-galbotperception-function}

```cpp
virtual galbot::sdk::GalbotPerception::~GalbotPerception()=default
```

### init {#galbotperception-init-function}

```cpp
virtual bool galbot::sdk::GalbotPerception::init(const std::set< PerceptionModule > &enabled_modules)=0
```

<small>Initialize perception and load models for the selected modules.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `enabled_modules` | const std::set< [PerceptionModule](#galbot_perception_types-hpp-perceptionmodule-enum) > & | Set of perception modules to enable. |

**Returns**

| Type | Description |
| --- | --- |
| bool | True if every requested module loaded successfully. |

### run_once {#galbotperception-run_once-function}

```cpp
virtual bool galbot::sdk::GalbotPerception::run_once(PerceptionModule module)=0
```

<small>Run a single inference for the given module.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `module` | [PerceptionModule](#galbot_perception_types-hpp-perceptionmodule-enum) | Perception module to run. |

!!! note
    After init, wait ~10s for models to be ready before calling run_once.

### wait_for_new_result {#galbotperception-wait_for_new_result-function}

```cpp
virtual bool galbot::sdk::GalbotPerception::wait_for_new_result(
    PerceptionModule module,
    double timeout_s=5.0
) =0
```

<small>Block until the module produces a new result, or timeout. Use with run_once to fetch the latest output.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `module` | [PerceptionModule](#galbot_perception_types-hpp-perceptionmodule-enum) | Perception module. |
| `timeout_s` | double | Timeout in seconds. |

### get_latest_result {#galbotperception-get_latest_result-function}

```cpp
virtual bool galbot::sdk::GalbotPerception::get_latest_result(
    PerceptionModule module,
    DetectionResult &result
) =0
```

<small>Return the latest cached result for the module without blocking.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `module` | [PerceptionModule](#galbot_perception_types-hpp-perceptionmodule-enum) | Perception module. |
| `result` | [DetectionResult](#detectionresult-struct) & | Output detection result. |

**Returns**

| Type | Description |
| --- | --- |
| bool | True if a result is available, false if none. |

### get_instance {#galbotperception-get_instance-function}

```cpp
static GalbotPerception& galbot::sdk::GalbotPerception::get_instance(MachineType m)
```

<small>Get the singleton instance of [GalbotPerception](#galbotperception-class).</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `m` | [MachineType](#galbot-sdk-machinetype-enum) | Machine type (e.g. [MachineType](#galbot-sdk-machinetype-enum)::G1). [MachineType](#galbot-sdk-machinetype-enum)::S1 is not supported and throws. |

**Returns**

| Type | Description |
| --- | --- |
| [GalbotPerception](#galbotperception-class) & | Reference to the singleton instance for the given machine type. |


---

<a id="module-types-enums"></a>

## Types & Enums

### ActuateType {#galbot-sdk-actuatetype-enum}

<small>Specifies which kinematic chains should be actuated during motion planning and execution. This controls whether the robot uses only the target arm, or also involves torso or leg motion.</small>

| Enum Value | Description |
| --- | --- |
| `ACTUATE_WITH_CHAIN_ONLY` | Actuate only the target joint chain (e.g., arm only), base remains fixed |
| `ACTUATE_WITH_TORSO` | Actuate target joint chain and torso for extended workspace |
| `ACTUATE_WITH_LEG` | Actuate target joint chain and legs for mobile manipulation |
| `ACTUATE_TYPE_NUM` | Total number of actuation types (for boundary checking or array sizing) |


---

### AudioData {#audiodata-struct}

<small>Audio data structure used to encapsulate audio data.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `header` | [Header](#header-struct) | Message header. |
| `type` | std::string | Audio data type identifier, possible values include: "waken_up": Wake-up event, format is json, data is json string "denoise_chunk": Denoised audio data, format is pcm, data is pcm data "vad_begin": Voice Activity Detection start marker (data is empty) "vad_chunk": Audio data during voice activity detection, format is pcm, data is pcm data "vad_end": Voice Activity Detection end marker (data is empty) |
| `format` | std::string | Audio data format description, for example: "pcm": Sample rate 16000Hz, bit depth 16bit, mono "json": UTF-8 encoded json text |
| `data` | std::vector< uint8_t > | Binary data packet, the specific format is specified by the format field. For pcm format, the data size for each 80ms is 2560 bytes. For json format, the data size may be the length of json text or empty. |


---

### BBox {#bbox-struct}

<small>Axis-aligned 2D bounding box with class id and score helpers.</small>

#### x1 {#bbox-x1-function}

```cpp
int BBox::x1() const
```

#### y1 {#bbox-y1-function}

```cpp
int BBox::y1() const
```

#### x2 {#bbox-x2-function}

```cpp
int BBox::x2() const
```

#### y2 {#bbox-y2-function}

```cpp
int BBox::y2() const
```

#### area {#bbox-area-function}

```cpp
float BBox::area() const
```

#### center {#bbox-center-function}

```cpp
cv::Point2f BBox::center() const
```

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `rect` | cv::Rect |  |
| `cls` | std::pair< int, float > |  |


---

### BmsInfo {#bmsinfo-struct}

<small>Bms information.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `voltage` | float | Voltage (V) |
| `current` | float | Current (A) |
| `battery_level` | float | Battery level (0-100%) |
| `temperature` | float | Temperature (℃) |
| `charging_status` | bool | Charging status：False: not charging, True: charging |
| `health_status` | bool | Health status：False: good, True: bad |
| `capacity` | float | Remaining capacity (Ah) |


---

### CameraInfo {#camerainfo-struct}

<small>Complete camera calibration data including intrinsic parameters, distortion coefficients, rectification, and projection matrices. Compatible with ROS 2 sensor_msgs/[CameraInfo](#camerainfo-struct).</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `header` | [Header](#header-struct) | Contains timestamp and camera coordinate frame ID (e.g., "camera_optical_frame"). |
| `height` | uint32_t | Vertical resolution of images produced by this camera at calibration time. |
| `width` | uint32_t | Horizontal resolution of images produced by this camera at calibration time. |
| `distortion_model` | std::string | Specifies the lens distortion model used. Common values: "plumb_bob": Brown-Conrady model with radial (k1,k2,k3) and tangential (p1,p2) distortion "rational_polynomial": Extended model with additional parameters "equidistant": Fisheye lens model |
| `d` | std::vector< double > | Vector of distortion parameters, size and interpretation depend on distortion_model. For "plumb_bob": [k1, k2, p1, p2, k3] (5 parameters) k1, k2, k3: Radial distortion coefficients p1, p2: Tangential distortion coefficients |
| `k` | std::array< double, 9 > | 3×3 matrix in row-major order, maps 3D points in camera frame to 2D pixel coordinates: [fx0cx] [0fycy] [001] fx, fy: Focal lengths in pixel units cx, cy: Principal point (optical center) in pixels |
| `r` | std::array< double, 9 > | 3×3 rotation matrix in row-major order. For stereo cameras: rotates left/right camera image planes to be coplanar and row-aligned. For monocular cameras: typically identity matrix (no rectification needed). |
| `p` | std::array< double, 12 > | 3×4 matrix in row-major order, projects 3D points to rectified image coordinates: [fx'0cx'Tx] [0fy'cy'Ty] [0010] fx', fy': Rectified focal lengths cx', cy': Rectified principal point Tx, Ty: Stereo baseline (Tx = -fx' × baseline for right camera) |
| `binning_x` | uint32_t | Number of camera pixels combined horizontally for each output pixel. Values: 0 or 1 = no binning, 2 = 2×1 binning, etc. |
| `binning_y` | uint32_t | Number of camera pixels combined vertically for each output pixel. Values: 0 or 1 = no binning, 2 = 1×2 binning, etc. |
| `roi` | [RegionOfInterest](#regionofinterest-struct) | Specifies a sub-window within the full sensor resolution. |
| `camera_type` | std::string | Optional field specifying camera type or model. Examples: "monocular", "stereo_left", "stereo_right", "depth" |
| `T` | std::vector< double > | Optional transformation matrix for vendor-specific or extended calibration data. Size and interpretation depend on implementation. |


---

### ChainType {#galbot-sdk-chaintype-enum}

<small>Identifies different kinematic chains in the robot structure for forward/inverse kinematics calculations and motion planning.</small>

| Enum Value | Description |
| --- | --- |
| `HEAD` | Head kinematic chain, from base/torso to head end-effector |
| `LEFT_ARM` | Left arm kinematic chain, from base/torso to left end-effector |
| `RIGHT_ARM` | Right arm kinematic chain, from base/torso to right end-effector |
| `LEG` | Leg kinematic chain, for legged locomotion |
| `TORSO` | Torso kinematic chain, connects base to upper body |
| `CHAIN_NUM` | Total number of kinematic chains (for boundary checking or array sizing) |


---

### CollisionCheckOption {#collisioncheckoption-struct}

<small>Collision detection enable/disable configuration.

This structure provides fine-grained control over collision checking during motion planning and execution. It supports independent toggling of self-collision detection (robot links colliding with each other) and environment collision detection (robot colliding with obstacles or workspace boundaries). Disabling collision checks improves computational performance but may result in unsafe trajectories. Use with caution in controlled environments.</small>

#### set_disable_self_collision_check {#collisioncheckoption-set_disable_self_collision_check-function}

```cpp
void galbot::sdk::CollisionCheckOption::set_disable_self_collision_check(bool disable)
```

<small>Enable or disable self-collision detection.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `disable` | bool | true to disable self-collision checking, false to enable |

!!! warning
    Disabling self-collision checks may result in physically infeasible configurations

#### set_disable_env_collision_check {#collisioncheckoption-set_disable_env_collision_check-function}

```cpp
void galbot::sdk::CollisionCheckOption::set_disable_env_collision_check(bool disable)
```

<small>Enable or disable environment collision detection.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `disable` | bool | true to disable environment collision checking, false to enable |

!!! warning
    Disabling environment checks may result in collisions with obstacles

#### get_disable_self_collision_check {#collisioncheckoption-get_disable_self_collision_check-function}

```cpp
bool galbot::sdk::CollisionCheckOption::get_disable_self_collision_check() const
```

<small>Check if self-collision detection is disabled.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | true if self-collision detection is currently disabled, false if enabled |

#### get_disable_env_collision_check {#collisioncheckoption-get_disable_env_collision_check-function}

```cpp
bool galbot::sdk::CollisionCheckOption::get_disable_env_collision_check() const
```

<small>Check if environment collision detection is disabled.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | true if environment collision detection is currently disabled, false if enabled |

#### print {#collisioncheckoption-print-function}

```cpp
void galbot::sdk::CollisionCheckOption::print() const
```

<small>Print collision detection configuration to standard output.

Outputs enabled/disabled status for each collision check type.</small>


---

### ControlStatus {#galbot-sdk-controlstatus-enum}

<small>Control command execution status enumeration.

Represents the execution status of robot control commands, including joint control, end-effector control, and other motion control operations.</small>

| Enum Value | Description |
| --- | --- |
| `SUCCESS` | Execution succeeded, command completed with valid result |
| `TIMEOUT` | Execution timeout, task not completed within specified time limit |
| `FAULT` | Fault occurred, system detected anomaly and aborted execution |
| `INVALID_INPUT` | Input parameters invalid or not meeting interface requirements |
| `INIT_FAILED` | Initialization failed, internal communication or dependent component creation failed |
| `IN_PROGRESS` | Command is executing but has not reached target state |
| `STOPPED_UNREACHED` | Stopped during execution without reaching target position or state |
| `DATA_FETCH_FAILED` | Data retrieval failed during operation, unable to read required state |
| `PUBLISH_FAIL` | Control or state data publication failed, command may not be transmitted |
| `COMM_DISCONNECTED` | Communication connection lost, cannot continue execution |
| `STATUS_NUM` | Total number of status enumerations (for boundary checking or array sizing) |


---

### DepthData {#depthdata-struct}

<small>Contains compressed depth image data from depth cameras or RGB-D sensors. Compatible with ROS 2 sensor_msgs/CompressedImage format with depth extensions.</small>

#### convert_to_cv2_mat {#depthdata-convert_to_cv2_mat-function}

```cpp
std::shared_ptr<cv::Mat> galbot::sdk::DepthData::convert_to_cv2_mat()
```

<small>Convert depth data to OpenCV Mat.

Decodes and converts depth data to cv::Mat format for processing.</small>

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< cv::Mat > | std::shared_ptr<cv::Mat> Smart pointer to decoded depth image on success, nullptr on failure |

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `header` | [Header](#header-struct) | Contains acquisition timestamp and camera coordinate frame ID. |
| `height` | uint32_t | Number of rows in the depth image. |
| `width` | uint32_t | Number of columns in the depth image. |
| `format` | std::string | Specifies depth encoding and compression format. Example: "16UC1; compressedDepth png" (16-bit unsigned, 1 channel, PNG compressed) |
| `data` | std::vector< uint8_t > | Binary blob containing raw or compressed depth image data. |
| `depth_scale` | uint32_t | Quantization factor for converting pixel values to metric depth. True depth (meters) = pixel_value / depth_scale Example: depth_scale = 1000 means pixel values are in millimeters |


---

### DetectionAndSegmentationResult {#detectionandsegmentationresult-struct}

<small>Single-object detection or instance segmentation record (2D box, class, optional mask/keypoints).</small>

#### SENSORDATA_POINTER_TYPEDEFS {#detectionandsegmentationresult-sensordata_pointer_typedefs-function}

```cpp
DetectionAndSegmentationResult::SENSORDATA_POINTER_TYPEDEFS(DetectionAndSegmentationResult)
```

#### DetectionAndSegmentationResult {#detectionandsegmentationresult-detectionandsegmentationresult-function}

```cpp
DetectionAndSegmentationResult::DetectionAndSegmentationResult()
```

#### DetectionAndSegmentationResult {#detectionandsegmentationresult-detectionandsegmentationresult-function}

```cpp
DetectionAndSegmentationResult::DetectionAndSegmentationResult(
    const cv::Rect &box,
    const std::string &name,
    const int index,
    const float conf,
    const std::vector< cv::Point2f > &kps=std::vector< cv::Point2f >(),
    const std::vector< cv::Point > &poly=std::vector< cv::Point >()
)
```

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `box` | const cv::Rect & |  |
| `name` | const std::string & |  |
| `index` | const int |  |
| `conf` | const float |  |
| `kps` | const std::vector< cv::Point2f > & |  |
| `poly` | const std::vector< cv::[Point](#point-struct) > & |  |

#### printInfo {#detectionandsegmentationresult-printinfo-function}

```cpp
void DetectionAndSegmentationResult::printInfo(std::ostream &os, bool showPolygon=false) const
```

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `os` | std::ostream & |  |
| `showPolygon` | bool |  |

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `bbox` | cv::Rect |  |
| `className` | std::string |  |
| `classIndex` | int |  |
| `confidence` | float |  |
| `keypoints` | std::vector< cv::Point2f > |  |
| `polygon` | std::vector< cv::[Point](#point-struct) > |  |


---

### DetectionResult {#detectionresult-struct}

<small>Aggregated perception output for one module tick (images, masks, poses, point clouds, etc.).</small>

#### SENSORDATA_POINTER_TYPEDEFS {#detectionresult-sensordata_pointer_typedefs-function}

```cpp
DetectionResult::SENSORDATA_POINTER_TYPEDEFS(DetectionResult)
```

#### addResult {#detectionresult-addresult-function}

```cpp
void DetectionResult::addResult(
    const cv::Rect &box,
    const std::string &className,
    int classIndex,
    float confidence
)
```

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `box` | const cv::Rect & |  |
| `className` | const std::string & |  |
| `classIndex` | int |  |
| `confidence` | float |  |

#### addResult {#detectionresult-addresult-function}

```cpp
void DetectionResult::addResult(
    const cv::Rect &box,
    const std::vector< cv::Point2f > &kps,
    const std::string &className,
    int classIndex,
    float confidence
)
```

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `box` | const cv::Rect & |  |
| `kps` | const std::vector< cv::Point2f > & |  |
| `className` | const std::string & |  |
| `classIndex` | int |  |
| `confidence` | float |  |

#### addPose {#detectionresult-addpose-function}

```cpp
void DetectionResult::addPose(const Eigen::Matrix4f &pose)
```

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `pose` | const Eigen::Matrix4f & |  |

#### addKeypoints {#detectionresult-addkeypoints-function}

```cpp
void DetectionResult::addKeypoints(const std::vector< cv::Point2f > &kps)
```

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `kps` | const std::vector< cv::Point2f > & |  |

#### addPointCloud {#detectionresult-addpointcloud-function}

```cpp
void DetectionResult::addPointCloud(const PointCloudPtr &cloud)
```

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `cloud` | const PointCloudPtr & |  |

#### setRunningInfo {#detectionresult-setrunninginfo-function}

```cpp
void DetectionResult::setRunningInfo(const std::string &info)
```

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `info` | const std::string & |  |

#### addClassMask {#detectionresult-addclassmask-function}

```cpp
void DetectionResult::addClassMask(const cv::Mat &mask)
```

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `mask` | const cv::Mat & |  |

#### addInstanceMask {#detectionresult-addinstancemask-function}

```cpp
void DetectionResult::addInstanceMask(const cv::Mat &mask)
```

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `mask` | const cv::Mat & |  |

#### clear {#detectionresult-clear-function}

```cpp
void DetectionResult::clear()
```

#### getResultInfo {#detectionresult-getresultinfo-function}

```cpp
std::string DetectionResult::getResultInfo()
```

#### copyFrom {#detectionresult-copyfrom-function}

```cpp
void DetectionResult::copyFrom(const DetectionResult &other)
```

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `other` | const [DetectionResult](#detectionresult-struct) & |  |

#### DetectionResult {#detectionresult-detectionresult-function}

```cpp
DetectionResult::DetectionResult()
```

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `timestamp_ns` | EIGEN_MAKE_ALIGNED_OPERATOR_NEW int64_t |  |
| `sensorName` | std::string |  |
| `resultImage` | cv::Mat |  |
| `resultPointCloud` | std::vector< PointCloudPtr > |  |
| `detectionAndSegmentationResults` | std::vector< [DetectionAndSegmentationResult](#detectionandsegmentationresult-struct) > |  |
| `boundingBoxes` | std::vector< cv::Rect > |  |
| `classNames` | std::vector< std::string > |  |
| `classIndices` | std::vector< int > |  |
| `confidences` | std::vector< float > |  |
| `ocrString` | std::vector< std::string > |  |
| `targetPoses` | std::vector< Eigen::Matrix4f > |  |
| `keypoints` | std::vector< std::vector< cv::Point2f > > |  |
| `runningInfo` | std::string |  |
| `classMask` | cv::Mat |  |
| `instanceMask` | cv::Mat |  |
| `garbage_result` | [GarbageResult](#garbageresult-struct)::Ptr |  |
| `object6DPoses` | std::map< std::string, std::vector< Eigen::Matrix4f > > |  |
| `grasp_pose_result` | std::vector< std::vector< float > > |  |
| `targetPointPoses` | std::vector< Eigen::Matrix4f > |  |
| `preTargetPointPoses` | std::vector< Eigen::Matrix4f > |  |
| `ocrPointPoses` | std::vector< Eigen::Matrix4f > |  |
| `ocrLabelImage` | std::map< std::string, std::vector< cv::Mat > > |  |
| `ocrResults` | std::map< std::string, Eigen::Matrix4f > |  |


---

### DeviceInfo {#deviceinfo-struct}

<small>Describes basic information about the robot or module, used for device management, logging, diagnostics, and maintenance tracking.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `model` | std::string | Device model name or identifier |
| `serial_number` | std::string | Unique serial number for device identification |
| `firmware_version` | std::string | System firmware version string (e.g., "1.2.3") |
| `hardware_version` | std::string | Hardware version or revision number |
| `manufacturer` | std::string | Manufacturer name or company identifier |


---

### EffortInfo {#effortinfo-struct}

<small>Represents a 6-DOF wrench (force and torque) typically measured by a force/torque sensor. Also known as a spatial force or generalized force.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `timestamp_ns` | int64_t | Measurement timestamp (nanoseconds since epoch) |
| `force` | [Vector3](#vector3-struct) | Force vector (Newtons): [fx, fy, fz] |
| `torque` | [Vector3](#vector3-struct) | Torque vector (Newton-meters): [tx, ty, tz] |


---

### Error {#error-struct}

<small>Describes an error from a single module or component, including error code and human-readable description for debugging and diagnostics.</small>

#### Error {#error-error-function}

```cpp
galbot::sdk::Error::Error(std::string commpent_input, int error_code_input, std::string description_input)
```

<small>Constructor.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `commpent_input` | std::string | Fault module or component name |
| `error_code_input` | int | Numerical error code |
| `description_input` | std::string | Human-readable error description |

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `commpent` | std::string | Fault module or component name (note: field name contains typo but preserved for API compatibility) |
| `error_code` | uint64_t | Numerical error code for programmatic error handling |
| `description` | std::string | Human-readable error description |


---

### ErrorInfo {#errorinfo-struct}

<small>Contains a timestamped collection of error messages from multiple modules or components.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `timestamp_ns` | int64_t | [Timestamp](#timestamp-struct) when errors were collected (nanoseconds since epoch) |
| `error_vec` | std::vector< [Error](#error-struct) > | Vector of error messages from various system components |


---

### ForceData {#forcedata-struct}

<small>Contains timestamped force and torque measurements from a 6-axis force/torque sensor, typically mounted at robot wrists or tool interfaces.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `timestamp_ns` | int64_t | Measurement timestamp (nanoseconds since epoch) |
| `force` | [Vector3](#vector3-struct) | Force vector (Newtons): [fx, fy, fz] |
| `torque` | [Vector3](#vector3-struct) | Torque vector (Newton-meters): [tx, ty, tz] |


---

### FrameTriad {#frametriad-struct}

<small>Task-space command for a body frame relative to a reference frame.

Mirrors galbot.spatial_proto.[FrameTriad](#frametriad-struct) at the SDK type layer.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `header` | [Header](#header-struct) |  |
| `body_frame_id` | std::string |  |
| `reference_frame_id` | std::string |  |
| `pose` | std::optional< [Pose](#pose-struct) > |  |
| `twist` | std::optional< [Twist](#twist-struct) > |  |
| `wrench` | std::optional< [Wrench](#wrench-struct) > |  |


---

### G1ControllerName {#g1controllername-struct}

<small>String constants for G1 controller names.

Defines the controller names supported by the G1 robot model.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `CHASSIS_POSE_CTRL` | constexpr Name | Chassis pose controller |
| `CHASSIS_TWIST_CTRL` | constexpr Name | Chassis twist controller |
| `LEG_PVT_BYPASS_CTRL` | constexpr Name | Leg PVT bypass controller |
| `LEG_PVT_CTRL` | constexpr Name | Leg PVT controller |
| `HEAD_PVT_BYPASS_CTRL` | constexpr Name | Head PVT bypass controller |
| `HEAD_PVT_CTRL` | constexpr Name | Head PVT controller |
| `LEFT_ARM_PVT_BYPASS_CTRL` | constexpr Name | Left arm PVT bypass controller |
| `LEFT_ARM_PVT_CTRL` | constexpr Name | Left arm PVT controller |
| `RIGHT_ARM_PVT_BYPASS_CTRL` | constexpr Name | Right arm PVT bypass controller |
| `RIGHT_ARM_PVT_CTRL` | constexpr Name | Right arm PVT controller |
| `LEFT_GRIPPER_CTRL` | constexpr Name | Left gripper controller |
| `RIGHT_GRIPPER_CTRL` | constexpr Name | Right gripper controller |
| `LEFT_DEXHAND_CTRL` | constexpr Name | Left dexhand controller |
| `RIGHT_DEXHAND_CTRL` | constexpr Name | Right dexhand controller |
| `CONTROLLER_NAME_NUM` | constexpr Name | Sentinel value for invalid controller name |


---

### G1JointGroup {#g1jointgroup-struct}

<small>A "joint group" is the SDK's primary control/planning unit, not a single joint: Kinematic-consistent control: commands are validated and executed per chain/end-effector group. Deterministic command ordering: joint_groups are expanded to concrete joint_names in group order. Group-level behavior: each group has its own active/passive attribute and execution tolerance. Recommended usage: Use constants in this struct when filling API parameters such as joint_groups. If exact joint names are needed, query them at runtime via get_joint_names(true, {group_name}) instead of hard-coding. In APIs that accept both joint_groups and joint_names, joint_names takes precedence.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `HEAD` | constexpr Name | Head chain. Default joints: head_joint1, head_joint2. Typical use: gaze/camera orientation. |
| `LEFT_ARM` | constexpr Name | Left 7-DoF arm chain. Default joints: left_arm_joint1 ... left_arm_joint7. Typical use: left-arm reaching/manipulation. |
| `RIGHT_ARM` | constexpr Name | Right 7-DoF arm chain. Default joints: right_arm_joint1 ... right_arm_joint7. Typical use: right-arm reaching/manipulation. |
| `LEFT_GRIPPER` | constexpr Name | Left gripper chain. Default joint: left_gripper_joint1. Typical use: left gripper open/close and grasp width. |
| `RIGHT_GRIPPER` | constexpr Name | Right gripper chain. Default joint: right_gripper_joint1. Typical use: right gripper open/close and grasp width. |
| `LEG` | constexpr Name | Leg chain. Default joints: leg_joint1 ... leg_joint5. Typical use: lower-body posture/locomotion-related body control. |
| `CHASSIS` | constexpr Name | Chassis mechanism group (passive in joint-position control). Default joints: chassis_joint1 ... chassis_joint4. Typical use: chassis state grouping; base motion should use base APIs. |
| `LEFT_SUCTION_CUP` | constexpr Name | Left suction-cup end-effector group. Default joint: left_suction_cup_joint1. Typical use: vacuum pick/place on left arm. |
| `RIGHT_SUCTION_CUP` | constexpr Name | Right suction-cup end-effector group. Default joint: right_suction_cup_joint1. Typical use: vacuum pick/place on right arm. |
| `LEFT_DEXHAND` | constexpr Name | Left dexterous hand group. Default joints: left_dexhand_joint1 ... left_dexhand_joint6. Typical use: multi-finger dexterous manipulation (left). |
| `RIGHT_DEXHAND` | constexpr Name | Right dexterous hand group. Default joints: right_dexhand_joint1 ... right_dexhand_joint6. Typical use: multi-finger dexterous manipulation (right). |


---

### GalbotOneFoxtrotSensor {#galbot-sdk-galbotonefoxtrotsensor-enum}

<small>Force sensor enumeration describing robot wrist force sensors.

Identifies force/torque sensors mounted at the robot's wrist joints for force-controlled manipulation and contact detection.</small>

| Enum Value | Description |
| --- | --- |
| `LEFT_WRIST_FORCE` | Left wrist force/torque sensor, typically 6-axis (3 forces + 3 torques) |
| `RIGHT_WRIST_FORCE` | Right wrist force/torque sensor, typically 6-axis (3 forces + 3 torques) |
| `FORCE_NUM` | Total number of force sensor enumerations (for boundary checking or array sizing) |


---

### GalbotSdkLogStream {#galbotsdklogstream-class}

#### GalbotSdkLogStream {#galbotsdklogstream-galbotsdklogstream-function}

```cpp
galbot::sdk::GalbotSdkLogStream::GalbotSdkLogStream(
    LogLevel level,
    const char *file,
    const char *func,
    int line
)
```

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `level` | [LogLevel](#galbot-sdk-loglevel-enum) |  |
| `file` | const char * |  |
| `func` | const char * |  |
| `line` | int |  |

#### operator<< {#galbotsdklogstream-operator--function}

```cpp
GalbotSdkLogStream& galbot::sdk::GalbotSdkLogStream::operator<<(const T &v)
```

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `v` | const T & |  |

#### operator<< {#galbotsdklogstream-operator--function}

```cpp
GalbotSdkLogStream& galbot::sdk::GalbotSdkLogStream::operator<<(std::ostream &(*manip)(std::ostream &))
```

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `manip` | std::ostream &(*)(std::ostream &) |  |

#### ~GalbotSdkLogStream {#galbotsdklogstream-galbotsdklogstream-function}

```cpp
galbot::sdk::GalbotSdkLogStream::~GalbotSdkLogStream() noexcept
```


---

### GarbageResult {#garbageresult-struct}

<small>Structured garbage / bin-like detection output (3D boxes and optional clouds).</small>

#### SENSORDATA_POINTER_TYPEDEFS {#garbageresult-sensordata_pointer_typedefs-function}

```cpp
GarbageResult::SENSORDATA_POINTER_TYPEDEFS(GarbageResult)
```

#### addResult {#garbageresult-addresult-function}

```cpp
void GarbageResult::addResult(
    const std::string &uuid,
    Eigen::Vector3f box_shape,
    const Eigen::Vector3f &box_center_pos,
    const cv::Rect &box
)
```

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `uuid` | const std::string & |  |
| `box_shape` | Eigen::Vector3f |  |
| `box_center_pos` | const Eigen::Vector3f & |  |
| `box` | const cv::Rect & |  |

#### addPointCloud {#garbageresult-addpointcloud-function}

```cpp
void GarbageResult::addPointCloud(const std::string &uuid, const PointCloudPtr &bbox_pointcloud)
```

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `uuid` | const std::string & |  |
| `bbox_pointcloud` | const PointCloudPtr & |  |

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `boxes_shape` | EIGEN_MAKE_ALIGNED_OPERATOR_NEW std::map< std::string, Eigen::Vector3f > |  |
| `boxes_center_pos` | std::map< std::string, Eigen::Vector3f > |  |
| `bboxes` | std::map< std::string, cv::Rect > |  |
| `bboxes_pointcloud` | std::map< std::string, PointCloudPtr > |  |


---

### GripperState {#gripperstate-struct}

<small>Represents the current state of a parallel-jaw gripper, including opening width, motion status, and grasping force.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `timestamp_ns` | int64_t | State timestamp (nanoseconds since epoch) |
| `width` | double | Gripper opening width (meters), distance between fingers |
| `velocity` | double | Gripper closing/opening velocity (meters/second), positive = opening |
| `effort` | double | Gripper grasping force (Newtons), force applied by fingers |
| `is_moving` | bool | Motion flag from a movement window: false if no effective movement is observed within the configured time window |
| `joint_positions` | std::vector< double > | Gripper joint positions (radians), typically 1-2 joints for finger actuators |


---

### GroupCommand {#groupcommand-struct}

<small>Group-space command at a specific time point.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `time_from_start_s` | double |  |
| `joint_commands` | std::vector< [JointCommand](#jointcommand-struct) > |  |


---

### Header {#header-struct}

<small>Standard message header containing timestamp and coordinate frame information. [Timestamp](#timestamp-struct) is stored as nanoseconds since epoch (unified with other sensor types).</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `timestamp_ns` | int64_t | [Timestamp](#timestamp-struct) of data acquisition (nanoseconds since epoch)<br><br>Records when the data was captured or generated. |
| `frame_id` | std::string | Identifies the coordinate frame in which the data is expressed. Examples: "base_link", "world", "camera_optical_frame", "lidar_link", "map" |


---

### IKSolverConfig {#iksolverconfig-struct}

<small>Inverse kinematics (IK) solver configuration parameters.

This structure configures the numerical inverse kinematics solver used to compute joint configurations that achieve desired end-effector poses. It supports collision-aware IK with configurable seed strategies, convergence tolerances, joint limit handling, and timeout parameters. IK solving is an iterative numerical optimization process that may benefit from multiple random initializations to find feasible collision-free solutions.</small>

#### set_col_aware_ik_timeout {#iksolverconfig-set_col_aware_ik_timeout-function}

```cpp
void galbot::sdk::IKSolverConfig::set_col_aware_ik_timeout(double timeout)
```

<small>Set timeout for collision-aware IK solver.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `timeout` | double | Maximum solver iteration time (units: ms) |

!!! note
    Longer timeouts allow more seed attempts but delay planning

#### set_seed_type {#iksolverconfig-set_seed_type-function}

```cpp
void galbot::sdk::IKSolverConfig::set_seed_type(SeedType type)
```

<small>Set initial configuration seed generation strategy.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `type` | [SeedType](#galbot-sdk-seedtype-enum) | Seed generation method for IK optimization initialization |

#### set_col_aware_ik_joint_limit_bias {#iksolverconfig-set_col_aware_ik_joint_limit_bias-function}

```cpp
void galbot::sdk::IKSolverConfig::set_col_aware_ik_joint_limit_bias(double bias)
```

<small>Set safety margin from joint position limits.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `bias` | double | Distance from joint limits to treat as forbidden region (units: rad) |

!!! note
    Prevents IK solver from proposing configurations near singularities or mechanical limits

#### set_translation_eps {#iksolverconfig-set_translation_eps-function}

```cpp
void galbot::sdk::IKSolverConfig::set_translation_eps(const std::array< double, 3 > &eps)
```

<small>Set Cartesian position error tolerance for IK convergence.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `eps` | const std::array< double, 3 > & | Per-axis position error tolerance {x, y, z} (units: m) |

!!! note
    IK solution is accepted when position error is within this threshold

#### set_rotation_eps {#iksolverconfig-set_rotation_eps-function}

```cpp
void galbot::sdk::IKSolverConfig::set_rotation_eps(const std::array< double, 3 > &eps)
```

<small>Set orientation error tolerance for IK convergence.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `eps` | const std::array< double, 3 > & | Per-axis orientation error tolerance {roll, pitch, yaw} (units: rad) |

!!! note
    IK solution is accepted when orientation error is within this threshold

#### set_enable_collision_check_log {#iksolverconfig-set_enable_collision_check_log-function}

```cpp
void galbot::sdk::IKSolverConfig::set_enable_collision_check_log(bool enable)
```

<small>Enable or disable detailed collision checking diagnostic logs.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `enable` | bool | true to output collision detection logs, false to suppress |

!!! note
    Useful for debugging IK failures due to collision constraints

#### get_col_aware_ik_timeout {#iksolverconfig-get_col_aware_ik_timeout-function}

```cpp
double galbot::sdk::IKSolverConfig::get_col_aware_ik_timeout() const
```

<small>Get collision-aware IK solver timeout.</small>

**Returns**

| Type | Description |
| --- | --- |
| double | Timeout duration (units: ms) |

#### get_seed_type {#iksolverconfig-get_seed_type-function}

```cpp
SeedType galbot::sdk::IKSolverConfig::get_seed_type() const
```

<small>Get IK solver seed generation strategy.</small>

**Returns**

| Type | Description |
| --- | --- |
| [SeedType](#galbot-sdk-seedtype-enum) | Current seed type |

#### get_col_aware_ik_joint_limit_bias {#iksolverconfig-get_col_aware_ik_joint_limit_bias-function}

```cpp
double galbot::sdk::IKSolverConfig::get_col_aware_ik_joint_limit_bias() const
```

<small>Get joint limit safety margin.</small>

**Returns**

| Type | Description |
| --- | --- |
| double | Joint limit bias distance (units: rad) |

#### get_translation_eps {#iksolverconfig-get_translation_eps-function}

```cpp
const std::array<double, 3>& galbot::sdk::IKSolverConfig::get_translation_eps() const
```

<small>Get Cartesian position error tolerance.</small>

**Returns**

| Type | Description |
| --- | --- |
| const std::array< double, 3 > & | Per-axis position tolerance {x, y, z} (units: m) |

#### get_rotation_eps {#iksolverconfig-get_rotation_eps-function}

```cpp
const std::array<double, 3>& galbot::sdk::IKSolverConfig::get_rotation_eps() const
```

<small>Get orientation error tolerance.</small>

**Returns**

| Type | Description |
| --- | --- |
| const std::array< double, 3 > & | Per-axis orientation tolerance {roll, pitch, yaw} (units: rad) |

#### get_enable_collision_check_log {#iksolverconfig-get_enable_collision_check_log-function}

```cpp
bool galbot::sdk::IKSolverConfig::get_enable_collision_check_log() const
```

<small>Check if collision check logging is enabled.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | true if logging is enabled, false otherwise |

#### print {#iksolverconfig-print-function}

```cpp
void galbot::sdk::IKSolverConfig::print() const
```

<small>Print IK solver configuration to standard output.

Outputs all configuration parameters for debugging and verification.</small>

**Nested Enums**

##### SeedType {#galbot-sdk-iksolverconfig-seedtype-enum}

Initial guess generation strategy for IK optimization.

| Enum Value | Description |
| --- | --- |
| `RANDOM_SEED` | Uniformly random joint configurations within limits |
| `RANDOM_PROGRESSIVE_SEED` | Progressive random sampling with increasing coverage |
| `USER_DEFINED_SEED` | User-provided initial joint configurations |


---

### ImuData {#imudata-struct}

<small>Contains timestamped data from an Inertial Measurement Unit (IMU), including accelerometer, gyroscope, and magnetometer measurements.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `timestamp_ns` | int64_t | Measurement timestamp (nanoseconds since epoch) |
| `accel` | [Vector3](#vector3-struct) | Linear acceleration (meters/second²): [ax, ay, az] |
| `gyro` | [Vector3](#vector3-struct) | Angular velocity (radians/second): [ωx, ωy, ωz] |
| `magnet` | [Vector3](#vector3-struct) | Magnetic field strength (micro-Tesla): [mx, my, mz] |


---

### JointCommand {#jointcommand-struct}

<small>Specifies desired motion parameters for a single robot joint in a trajectory or control command.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `position` | double | Desired joint position (radians) |
| `velocity` | double | Desired joint velocity (radians/second) |
| `acceleration` | double | Desired joint acceleration (radians/second²) |
| `effort` | double | Desired joint torque/effort (Newton-meters) |


---

### JointState {#jointstate-struct}

<small>Represents the complete real-time state of a single robot joint, including kinematic quantities (position, velocity, acceleration) and dynamic quantities (torque/effort and motor current).</small>

#### JointState {#jointstate-jointstate-function}

```cpp
galbot::sdk::JointState::JointState()=default
```

<small>Default constructor.

Initializes all state variables to zero.</small>

#### JointState {#jointstate-jointstate-function}

```cpp
galbot::sdk::JointState::JointState(
    double position_input,
    double velocity_input,
    double acceleration_input,
    double effort_input,
    double current_input
)
```

<small>Parameterized constructor.

Initializes joint state with specified values.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `position_input` | double | Joint angular position (radians) |
| `velocity_input` | double | Joint angular velocity (radians/second) |
| `acceleration_input` | double | Joint angular acceleration (radians/second²) |
| `effort_input` | double | Joint torque/effort (Newton-meters) |
| `current_input` | double | Motor current (amperes) |

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `position` | double | Joint angular position (radians) |
| `velocity` | double | Joint angular velocity (radians/second) |
| `acceleration` | double | Joint angular acceleration (radians/second²) |
| `effort` | double | Joint torque/effort (Newton-meters) |
| `current` | double | Motor current (amperes) |


---

### JointStateMessage {#jointstatemessage-struct}

<small>Timestamped collection of joint states for multiple joints, typically representing a snapshot of the robot's complete joint configuration at one instant.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `timestamp_ns` | int64_t | Acquisition timestamp (nanoseconds since epoch) |
| `joint_state_vec` | std::vector< [JointState](#jointstate-struct) > | Vector of individual joint states |


---

### JointStates {#jointstates-class}

<small>Represents target joint configuration for a kinematic chain. Extends [RobotStates](#robotstates-class) to specify joint-based motion goals. Used in joint trajectory planning and forward kinematics computation. All joint angles must be in radians. Vector size must match the DOF of the specified kinematic chain.</small>

#### get_type {#jointstates-get_type-function}

```cpp
Type galbot::sdk::JointStates::get_type() const override
```

<small>Get runtime type identifier.</small>

**Returns**

| Type | Description |
| --- | --- |
| [Type](#galbot-sdk-robotstates-type-enum) | , indicating this is a joint-space target |

#### set_joint_positions {#jointstates-set_joint_positions-function}

```cpp
void galbot::sdk::JointStates::set_joint_positions(const std::vector< double > &joints)
```

<small>Set complete joint configuration for the kinematic chain.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `joints` | const std::vector< double > & | Vector of joint angles (radians), must match chain DOF |

!!! note
    Vector size should equal the number of actuated joints in the specified chain.

#### set_joint {#jointstates-set_joint-function}

```cpp
void galbot::sdk::JointStates::set_joint(int index, int val)
```

<small>Set individual joint angle by index.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `index` | int | Zero-based joint index within the chain |
| `val` | int | Joint angle value (radians) |

!!! note
    Function performs bounds checking; invalid indices are silently ignored.

!!! warning
    No error is returned for out-of-bounds access; ensure index validity externally.

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `joint_positions` | std::vector< double > | Target joint configuration for the chain (radians), ordered by joint index. |


---

### KinematicsBoundary {#kinematicsboundary-struct}

<small>Kinematic boundary parameters for robot kinematic chain joints.

This structure defines the kinematic constraints for a robot kinematic chain (e.g., manipulator arms, mobile base, or leg chains). It specifies position, velocity, acceleration, and jerk limits for each joint in the chain. These boundaries are critical for ensuring safe and physically feasible motion during trajectory planning and execution. Each vector should contain one value per joint in the kinematic chain. All joint space quantities are specified in radians or radians per unit time.</small>

#### set_chain_name {#kinematicsboundary-set_chain_name-function}

```cpp
void galbot::sdk::KinematicsBoundary::set_chain_name(const std::string &name)
```

<small>Set the name identifier for this kinematic chain.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `name` | const std::string & | Chain name identifier, e.g., "left_arm", "right_arm", "mobile_base" |

#### set_lower_limit {#kinematicsboundary-set_lower_limit-function}

```cpp
void galbot::sdk::KinematicsBoundary::set_lower_limit(const std::vector< double > &limits)
```

<small>Set joint position lower bounds.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `limits` | const std::vector< double > & | Vector of lower position limits for each joint (units: rad) |

!!! note
    Vector size must equal the number of joints in the chain

#### set_upper_limit {#kinematicsboundary-set_upper_limit-function}

```cpp
void galbot::sdk::KinematicsBoundary::set_upper_limit(const std::vector< double > &limits)
```

<small>Set joint position upper bounds.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `limits` | const std::vector< double > & | Vector of upper position limits for each joint (units: rad) |

!!! note
    Vector size must equal the number of joints in the chain

#### set_vel_lower_limit {#kinematicsboundary-set_vel_lower_limit-function}

```cpp
void galbot::sdk::KinematicsBoundary::set_vel_lower_limit(const std::vector< double > &limits)
```

<small>Set joint velocity lower bounds.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `limits` | const std::vector< double > & | Vector of lower velocity limits for each joint (units: rad/s) |

!!! note
    Typically negative values for bidirectional joints

#### set_vel_upper_limit {#kinematicsboundary-set_vel_upper_limit-function}

```cpp
void galbot::sdk::KinematicsBoundary::set_vel_upper_limit(const std::vector< double > &limits)
```

<small>Set joint velocity upper bounds.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `limits` | const std::vector< double > & | Vector of upper velocity limits for each joint (units: rad/s) |

!!! note
    Typically positive values for bidirectional joints

#### set_acc_lower_limit {#kinematicsboundary-set_acc_lower_limit-function}

```cpp
void galbot::sdk::KinematicsBoundary::set_acc_lower_limit(const std::vector< double > &limits)
```

<small>Set joint acceleration lower bounds.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `limits` | const std::vector< double > & | Vector of lower acceleration limits for each joint (units: rad/s²) |

!!! note
    Used for trajectory optimization and smoothness constraints

#### set_acc_upper_limit {#kinematicsboundary-set_acc_upper_limit-function}

```cpp
void galbot::sdk::KinematicsBoundary::set_acc_upper_limit(const std::vector< double > &limits)
```

<small>Set joint acceleration upper bounds.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `limits` | const std::vector< double > & | Vector of upper acceleration limits for each joint (units: rad/s²) |

!!! note
    Used for trajectory optimization and smoothness constraints

#### set_jerk_lower_limit {#kinematicsboundary-set_jerk_lower_limit-function}

```cpp
void galbot::sdk::KinematicsBoundary::set_jerk_lower_limit(const std::vector< double > &limits)
```

<small>Set joint jerk lower bounds.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `limits` | const std::vector< double > & | Vector of lower jerk limits for each joint (units: rad/s³) |

!!! note
    Jerk constraints improve motion smoothness and reduce mechanical wear

#### set_jerk_upper_limit {#kinematicsboundary-set_jerk_upper_limit-function}

```cpp
void galbot::sdk::KinematicsBoundary::set_jerk_upper_limit(const std::vector< double > &limits)
```

<small>Set joint jerk upper bounds.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `limits` | const std::vector< double > & | Vector of upper jerk limits for each joint (units: rad/s³) |

!!! note
    Jerk constraints improve motion smoothness and reduce mechanical wear

#### get_chain_name {#kinematicsboundary-get_chain_name-function}

```cpp
const std::string& galbot::sdk::KinematicsBoundary::get_chain_name() const
```

<small>Get the kinematic chain name identifier.</small>

**Returns**

| Type | Description |
| --- | --- |
| const std::string & | Const reference to chain name string |

#### get_lower_limit {#kinematicsboundary-get_lower_limit-function}

```cpp
const std::vector<double>& galbot::sdk::KinematicsBoundary::get_lower_limit() const
```

<small>Get joint position lower bounds.</small>

**Returns**

| Type | Description |
| --- | --- |
| const std::vector< double > & | Const reference to vector of lower position limits (units: rad) |

#### get_upper_limit {#kinematicsboundary-get_upper_limit-function}

```cpp
const std::vector<double>& galbot::sdk::KinematicsBoundary::get_upper_limit() const
```

<small>Get joint position upper bounds.</small>

**Returns**

| Type | Description |
| --- | --- |
| const std::vector< double > & | Const reference to vector of upper position limits (units: rad) |

#### get_vel_lower_limit {#kinematicsboundary-get_vel_lower_limit-function}

```cpp
const std::vector<double>& galbot::sdk::KinematicsBoundary::get_vel_lower_limit() const
```

<small>Get joint velocity lower bounds.</small>

**Returns**

| Type | Description |
| --- | --- |
| const std::vector< double > & | Const reference to vector of lower velocity limits (units: rad/s) |

#### get_vel_upper_limit {#kinematicsboundary-get_vel_upper_limit-function}

```cpp
const std::vector<double>& galbot::sdk::KinematicsBoundary::get_vel_upper_limit() const
```

<small>Get joint velocity upper bounds.</small>

**Returns**

| Type | Description |
| --- | --- |
| const std::vector< double > & | Const reference to vector of upper velocity limits (units: rad/s) |

#### get_acc_lower_limit {#kinematicsboundary-get_acc_lower_limit-function}

```cpp
const std::vector<double>& galbot::sdk::KinematicsBoundary::get_acc_lower_limit() const
```

<small>Get joint acceleration lower bounds.</small>

**Returns**

| Type | Description |
| --- | --- |
| const std::vector< double > & | Const reference to vector of lower acceleration limits (units: rad/s²) |

#### get_acc_upper_limit {#kinematicsboundary-get_acc_upper_limit-function}

```cpp
const std::vector<double>& galbot::sdk::KinematicsBoundary::get_acc_upper_limit() const
```

<small>Get joint acceleration upper bounds.</small>

**Returns**

| Type | Description |
| --- | --- |
| const std::vector< double > & | Const reference to vector of upper acceleration limits (units: rad/s²) |

#### get_jerk_lower_limit {#kinematicsboundary-get_jerk_lower_limit-function}

```cpp
const std::vector<double>& galbot::sdk::KinematicsBoundary::get_jerk_lower_limit() const
```

<small>Get joint jerk lower bounds.</small>

**Returns**

| Type | Description |
| --- | --- |
| const std::vector< double > & | Const reference to vector of lower jerk limits (units: rad/s³) |

#### get_jerk_upper_limit {#kinematicsboundary-get_jerk_upper_limit-function}

```cpp
const std::vector<double>& galbot::sdk::KinematicsBoundary::get_jerk_upper_limit() const
```

<small>Get joint jerk upper bounds.</small>

**Returns**

| Type | Description |
| --- | --- |
| const std::vector< double > & | Const reference to vector of upper jerk limits (units: rad/s³) |

#### print {#kinematicsboundary-print-function}

```cpp
void galbot::sdk::KinematicsBoundary::print() const
```

<small>Print kinematic boundary information to standard output.

Outputs all boundary parameters for debugging and visualization purposes.</small>


---

### LidarData {#lidardata-struct}

<small>Generic N-dimensional point cloud structure compatible with ROS 2 sensor_msgs/PointCloud2. Stores point data as a binary blob with field descriptors defining the data layout. Supports both ordered (structured) and unordered (unstructured) point clouds.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `header` | [Header](#header-struct) | Contains acquisition timestamp and coordinate frame for temporal and spatial reference. |
| `height` | uint32_t | Unordered point cloud: height = 1 (single row) Ordered point cloud: height = number of rows (e.g., from spinning lidar or depth camera) |
| `width` | uint32_t | Unordered point cloud: width = total number of points Ordered point cloud: width = number of points per row (columns) Total points = height × width |
| `fields` | std::vector< [PointField](#pointfield-struct) > | Describes the data channels (x, y, z, intensity, rgb, etc.) present in each point and their binary layout (offset, type, count). |
| `is_bigendian` | bool | true: Data is Big Endian byte order false: Data is Little Endian byte order (typical for x86/ARM systems) |
| `point_step` | uint32_t | Total byte size of a single point structure, including all fields and padding. Must be ≥ sum of all field sizes, may include alignment padding. |
| `row_step` | uint32_t | Total byte size of one row of points. Formula: row_step = point_step × width |
| `data` | std::vector< uint8_t > | Binary blob containing all point data in row-major order. Size should equal: row_step × height bytes Each point occupies point_step bytes, laid out according to fields descriptors. |
| `is_dense` | bool | true: All points are valid, no NaN or Inf values present false: Cloud may contain invalid points (NaN/Inf coordinates or fields) |


---

### LineTrajCheckPrimitive {#linetrajcheckprimitive-struct}

<small>Geometric primitive configuration for Cartesian linear trajectory validation.

This structure configures the collision detection geometric representation for linear end-effector trajectories in Cartesian space. It supports two primitive types: infinitesimally thin lines and swept-volume cylinders. Choosing the appropriate primitive affects collision detection conservativeness and computational cost. Cylinder primitives model the robot's actual swept volume more accurately but require more expensive geometric queries.</small>

#### set_line_check_primitive_type {#linetrajcheckprimitive-set_line_check_primitive_type-function}

```cpp
void galbot::sdk::LineTrajCheckPrimitive::set_line_check_primitive_type(PrimitiveType type)
```

<small>Set geometric primitive type for linear trajectory validation.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `type` | [PrimitiveType](#galbot-sdk-linetrajcheckprimitive-primitivetype-enum) | Primitive representation (LINE or CYLINDER) |

!!! note
    CYLINDER is recommended for safety-critical applications

#### set_cylinder_prim_radius {#linetrajcheckprimitive-set_cylinder_prim_radius-function}

```cpp
void galbot::sdk::LineTrajCheckPrimitive::set_cylinder_prim_radius(double radius)
```

<small>Set swept-volume cylinder radius for trajectory collision checking.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `radius` | double | Cylinder radius representing robot swept volume (units: m) |

!!! note
    Larger radii increase safety margins but may be overly conservative

!!! note
    Only applies when primitive type is CYLINDER

#### set_line_prim_curvature {#linetrajcheckprimitive-set_line_prim_curvature-function}

```cpp
void galbot::sdk::LineTrajCheckPrimitive::set_line_prim_curvature(double curvature)
```

<small>Set curvature approximation tolerance for line primitive.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `curvature` | double | Maximum deviation tolerance for piecewise-linear approximation (units: m) |

!!! note
    Controls how finely curved paths are discretized into line segments

!!! note
    Lower values improve accuracy but increase computational cost

#### get_line_check_primitive_type {#linetrajcheckprimitive-get_line_check_primitive_type-function}

```cpp
PrimitiveType galbot::sdk::LineTrajCheckPrimitive::get_line_check_primitive_type() const
```

<small>Get the geometric primitive type for trajectory checking.</small>

**Returns**

| Type | Description |
| --- | --- |
| [PrimitiveType](#galbot-sdk-linetrajcheckprimitive-primitivetype-enum) | Current primitive type (LINE or CYLINDER) |

#### get_cylinder_prim_radius {#linetrajcheckprimitive-get_cylinder_prim_radius-function}

```cpp
double galbot::sdk::LineTrajCheckPrimitive::get_cylinder_prim_radius() const
```

<small>Get the cylinder primitive swept-volume radius.</small>

**Returns**

| Type | Description |
| --- | --- |
| double | Cylinder radius (units: m) |

#### get_line_prim_curvature {#linetrajcheckprimitive-get_line_prim_curvature-function}

```cpp
double galbot::sdk::LineTrajCheckPrimitive::get_line_prim_curvature() const
```

<small>Get the line primitive curvature approximation tolerance.</small>

**Returns**

| Type | Description |
| --- | --- |
| double | Curvature tolerance (units: m) |

#### print {#linetrajcheckprimitive-print-function}

```cpp
void galbot::sdk::LineTrajCheckPrimitive::print() const
```

<small>Print line trajectory check primitive configuration to standard output.

Outputs selected primitive type and associated parameters for debugging.</small>

**Nested Enums**

##### PrimitiveType {#galbot-sdk-linetrajcheckprimitive-primitivetype-enum}

Geometric representation for linear trajectory collision checking.

| Enum Value | Description |
| --- | --- |
| `LINE` | Zero-thickness line segment (fast but less conservative) |
| `CYLINDER` | Swept-volume cylinder with configurable radius (accurate but slower) |


---

### LoggerConfig {#loggerconfig-struct}

<small>Defines the configuration parameters for the logging system, including file settings, log levels, and output options.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `path` | std::string | Directory path for log files. Default: ~/galbot_sdk_log/user_log |
| `file_name` | std::string | Log file name. Default: <process_name>_<current_time>_<pid>_<thread_id>.log |
| `file_max_size` | uint64_t | Maximum size of a single log file (bytes) |
| `file_max_num` | uint64_t | Number of log files to retain in rotation |
| `level` | [LogLevel](#galbot-sdk-loglevel-enum) | Minimum log level to record |
| `console_output` | bool | Flag to enable or disable console output |


---

### LogInfo {#loginfo-struct}

<small>Log information.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `level` | std::string |  |
| `message` | std::string | "error" "warning" |


---

### LogLevel {#galbot-sdk-loglevel-enum}

<small>Represents the severity level of log messages.</small>

| Enum Value | Description |
| --- | --- |
| `TRACE` | Trace level, detailed information for debugging |
| `DEBUG` | Debug level, diagnostic information for developers |
| `INFO` | Info level, general operational messages |
| `WARN` | Warn level, potentially harmful situations |
| `ERROR` | [Error](#error-struct) level, error events that might still allow the application to continue running |
| `CRITICAL` | Critical level, severe error events that lead to application termination |


---

### MachineType {#galbot-sdk-machinetype-enum}

<small>This enumeration defines the different robot platforms or machine types supported by the Galbot SDK. Clients can use these values to specify which robot model they are working with, particularly for factory methods that return platform-specific implementations. Keeping the enumeration in the common type definitions ensures consistency across the SDK while hiding implementation details in the respective modules.</small>

| Enum Value | Description |
| --- | --- |
| `G1` | Galbot G1 humanoid robot platform |


---

### MotionPlanConfig {#motionplanconfig-class}

<small>Comprehensive motion planning configuration management.

[MotionPlanConfig](#motionplanconfig-class) serves as a centralized configuration container for all motion planning subsystems. It aggregates sampling strategies, trajectory generation parameters, inverse kinematics solver settings, collision detection options, feasibility validation criteria, and kinematic constraint boundaries. This class provides a unified interface for configuring complex motion planning pipelines, supporting both simple manipulator planning and whole-body humanoid motion generation with multiple kinematic chains. Configuration objects are lazily initialized and managed through shared pointers to optimize memory usage and support optional feature configuration.</small>

#### MotionPlanConfig {#motionplanconfig-motionplanconfig-function}

```cpp
galbot::sdk::MotionPlanConfig::MotionPlanConfig()=default
```

<small>Default constructor.

Initializes an empty configuration with all sub-configurations set to nullptr. Sub-configurations are created on-demand via create_* or get_*_ref methods.</small>

#### set_update_time {#motionplanconfig-set_update_time-function}

```cpp
void galbot::sdk::MotionPlanConfig::set_update_time(int64_t t)
```

<small>Set configuration update timestamp.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `t` | int64_t | [Timestamp](#timestamp-struct) of last configuration modification (units: ns, typically CLOCK_MONOTONIC) |

!!! note
    Used for configuration versioning and cache invalidation

#### get_update_time {#motionplanconfig-get_update_time-function}

```cpp
int64_t galbot::sdk::MotionPlanConfig::get_update_time()
```

<small>Get configuration update timestamp.</small>

**Returns**

| Type | Description |
| --- | --- |
| int64_t | of last configuration modification (units: ns) |

#### create_sampler_config {#motionplanconfig-create_sampler_config-function}

```cpp
std::shared_ptr<SamplerConfig> galbot::sdk::MotionPlanConfig::create_sampler_config()
```

<small>Create or retrieve sampler configuration.

Lazily initializes the sampler configuration if it does not exist. Safe to call multiple times; returns the same instance after first creation.</small>

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [SamplerConfig](#samplerconfig-struct) > | Shared pointer to sampler configuration with default settings |

#### create_trajectory_plan_config {#motionplanconfig-create_trajectory_plan_config-function}

```cpp
std::shared_ptr<TrajectoryPlanConfig> galbot::sdk::MotionPlanConfig::create_trajectory_plan_config()
```

<small>Create or retrieve trajectory planning configuration.

Lazily initializes the trajectory planning configuration if it does not exist.</small>

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [TrajectoryPlanConfig](#trajectoryplanconfig-struct) > | Shared pointer to trajectory planning configuration with default settings |

#### create_ik_solver_config {#motionplanconfig-create_ik_solver_config-function}

```cpp
std::shared_ptr<IKSolverConfig> galbot::sdk::MotionPlanConfig::create_ik_solver_config()
```

<small>Create or retrieve inverse kinematics solver configuration.

Lazily initializes the IK solver configuration if it does not exist.</small>

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [IKSolverConfig](#iksolverconfig-struct) > | Shared pointer to IK solver configuration with default settings |

#### create_collision_check_option {#motionplanconfig-create_collision_check_option-function}

```cpp
std::shared_ptr<CollisionCheckOption> galbot::sdk::MotionPlanConfig::create_collision_check_option()
```

<small>Create or retrieve collision check option configuration.

Lazily initializes the collision check options if they do not exist.</small>

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [CollisionCheckOption](#collisioncheckoption-struct) > | Shared pointer to collision check options with default settings |

#### create_trajectory_feasibility_check_option {#motionplanconfig-create_trajectory_feasibility_check_option-function}

```cpp
std::shared_ptr<TrajectoryFeasibilityCheckOption> galbot::sdk::MotionPlanConfig::create_trajectory_feasibility_check_option()
```

<small>Create or retrieve trajectory feasibility check option configuration.

Lazily initializes the trajectory feasibility check options if they do not exist.</small>

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [TrajectoryFeasibilityCheckOption](#trajectoryfeasibilitycheckoption-struct) > | Shared pointer to trajectory feasibility check options with default settings |

#### create_line_traj_check_primitive {#motionplanconfig-create_line_traj_check_primitive-function}

```cpp
std::shared_ptr<LineTrajCheckPrimitive> galbot::sdk::MotionPlanConfig::create_line_traj_check_primitive()
```

<small>Create or retrieve line trajectory check primitive configuration.

Lazily initializes the line trajectory check primitive configuration if it does not exist.</small>

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [LineTrajCheckPrimitive](#linetrajcheckprimitive-struct) > | Shared pointer to line trajectory check primitive with default settings |

#### set_sampler_config {#motionplanconfig-set_sampler_config-function}

```cpp
void galbot::sdk::MotionPlanConfig::set_sampler_config(const std::shared_ptr< SamplerConfig > &config)
```

<small>Set or replace sampler configuration.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `config` | const std::shared_ptr< [SamplerConfig](#samplerconfig-struct) > & | Shared pointer to sampler configuration; nullptr clears the configuration |

#### set_trajectory_plan_config {#motionplanconfig-set_trajectory_plan_config-function}

```cpp
void galbot::sdk::MotionPlanConfig::set_trajectory_plan_config(
    const std::shared_ptr< TrajectoryPlanConfig > &config
)
```

<small>Set or replace trajectory planning configuration.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `config` | const std::shared_ptr< [TrajectoryPlanConfig](#trajectoryplanconfig-struct) > & | Shared pointer to trajectory planning configuration; nullptr clears the configuration |

#### set_ik_solver_config {#motionplanconfig-set_ik_solver_config-function}

```cpp
void galbot::sdk::MotionPlanConfig::set_ik_solver_config(const std::shared_ptr< IKSolverConfig > &config)
```

<small>Set or replace inverse kinematics solver configuration.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `config` | const std::shared_ptr< [IKSolverConfig](#iksolverconfig-struct) > & | Shared pointer to IK solver configuration; nullptr clears the configuration |

#### set_collision_check_option {#motionplanconfig-set_collision_check_option-function}

```cpp
void galbot::sdk::MotionPlanConfig::set_collision_check_option(
    const std::shared_ptr< CollisionCheckOption > &option
)
```

<small>Set or replace collision check option configuration.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `option` | const std::shared_ptr< [CollisionCheckOption](#collisioncheckoption-struct) > & | Shared pointer to collision check options; nullptr clears the configuration |

#### set_trajectory_feasibility_check_option {#motionplanconfig-set_trajectory_feasibility_check_option-function}

```cpp
void galbot::sdk::MotionPlanConfig::set_trajectory_feasibility_check_option(
    const std::shared_ptr< TrajectoryFeasibilityCheckOption > &option
)
```

<small>Set or replace trajectory feasibility check option configuration.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `option` | const std::shared_ptr< [TrajectoryFeasibilityCheckOption](#trajectoryfeasibilitycheckoption-struct) > & | Shared pointer to trajectory feasibility check options; nullptr clears the configuration |

#### set_feasibility_boundary {#motionplanconfig-set_feasibility_boundary-function}

```cpp
void galbot::sdk::MotionPlanConfig::set_feasibility_boundary(
    const std::vector< KinematicsBoundary > &boundary
)
```

<small>Set kinematic feasibility boundaries for all chains.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `boundary` | const std::vector< [KinematicsBoundary](#kinematicsboundary-struct) > & | Vector of kinematic boundaries, one per chain |

!!! note
    These boundaries are used for general trajectory feasibility validation

#### set_line_traj_check_primitive {#motionplanconfig-set_line_traj_check_primitive-function}

```cpp
void galbot::sdk::MotionPlanConfig::set_line_traj_check_primitive(
    const std::shared_ptr< LineTrajCheckPrimitive > &primitive
)
```

<small>Set or replace line trajectory check primitive configuration.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `primitive` | const std::shared_ptr< [LineTrajCheckPrimitive](#linetrajcheckprimitive-struct) > & | Shared pointer to line trajectory check primitive; nullptr clears the configuration |

#### set_ik_joint_limit {#motionplanconfig-set_ik_joint_limit-function}

```cpp
void galbot::sdk::MotionPlanConfig::set_ik_joint_limit(const std::vector< KinematicsBoundary > &boundary)
```

<small>Set joint limits used during IK solving phase.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `boundary` | const std::vector< [KinematicsBoundary](#kinematicsboundary-struct) > & | Vector of kinematic boundaries for IK solver joint constraints |

!!! note
    IK limits may be tighter than hard limits to improve convergence and avoid singularities

#### set_sampler_joint_limit {#motionplanconfig-set_sampler_joint_limit-function}

```cpp
void galbot::sdk::MotionPlanConfig::set_sampler_joint_limit(const std::vector< KinematicsBoundary > &boundary)
```

<small>Set joint limits used during sampling-based planning phase.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `boundary` | const std::vector< [KinematicsBoundary](#kinematicsboundary-struct) > & | Vector of kinematic boundaries for sampling algorithms |

!!! note
    Sampling limits define the valid configuration space for exploration

#### set_hard_joint_limit {#motionplanconfig-set_hard_joint_limit-function}

```cpp
void galbot::sdk::MotionPlanConfig::set_hard_joint_limit(const std::vector< KinematicsBoundary > &boundary)
```

<small>Set absolute hard joint limits (safety-critical boundaries)</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `boundary` | const std::vector< [KinematicsBoundary](#kinematicsboundary-struct) > & | Vector of kinematic boundaries representing mechanical/safety limits |

!!! note
    Hard limits must never be violated; typically correspond to physical joint stops

#### set_revert_ik_joint_limit {#motionplanconfig-set_revert_ik_joint_limit-function}

```cpp
void galbot::sdk::MotionPlanConfig::set_revert_ik_joint_limit(bool flag)
```

<small>Enable or disable IK joint limit reversion to hard limits.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `flag` | bool | true to revert IK joint limits to hard limits, false to use configured IK limits |

!!! note
    Useful for recovering from constrained configurations by temporarily relaxing IK limits

#### set_revert_ik_joint_limit_chains {#motionplanconfig-set_revert_ik_joint_limit_chains-function}

```cpp
void galbot::sdk::MotionPlanConfig::set_revert_ik_joint_limit_chains(const std::vector< std::string > &chains)
```

<small>Set specific kinematic chains for IK joint limit reversion.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `chains` | const std::vector< std::string > & | Vector of chain names to apply IK limit reversion (e.g., {"left_arm", "torso"}) |

!!! note
    If non-empty, automatically enables revert_ik_joint_limit flag

!!! note
    Empty vector disables selective reversion (applies to all chains if flag is set)

#### get_sampler_config {#motionplanconfig-get_sampler_config-function}

```cpp
std::shared_ptr<SamplerConfig> galbot::sdk::MotionPlanConfig::get_sampler_config() const
```

<small>Get sampler configuration (may be nullptr if not initialized)</small>

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [SamplerConfig](#samplerconfig-struct) > | Shared pointer to sampler configuration, or nullptr if not set |

!!! note
    Use create_sampler_config() to ensure a valid configuration exists

#### get_trajectory_plan_config {#motionplanconfig-get_trajectory_plan_config-function}

```cpp
std::shared_ptr<TrajectoryPlanConfig> galbot::sdk::MotionPlanConfig::get_trajectory_plan_config() const
```

<small>Get trajectory planning configuration (may be nullptr if not initialized)</small>

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [TrajectoryPlanConfig](#trajectoryplanconfig-struct) > | Shared pointer to trajectory planning configuration, or nullptr if not set |

!!! note
    Use create_trajectory_plan_config() to ensure a valid configuration exists

#### get_ik_solver_config {#motionplanconfig-get_ik_solver_config-function}

```cpp
std::shared_ptr<IKSolverConfig> galbot::sdk::MotionPlanConfig::get_ik_solver_config() const
```

<small>Get inverse kinematics solver configuration (may be nullptr if not initialized)</small>

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [IKSolverConfig](#iksolverconfig-struct) > | Shared pointer to IK solver configuration, or nullptr if not set |

!!! note
    Use create_ik_solver_config() to ensure a valid configuration exists

#### get_collision_check_option {#motionplanconfig-get_collision_check_option-function}

```cpp
std::shared_ptr<CollisionCheckOption> galbot::sdk::MotionPlanConfig::get_collision_check_option() const
```

<small>Get collision check option configuration (may be nullptr if not initialized)</small>

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [CollisionCheckOption](#collisioncheckoption-struct) > | Shared pointer to collision check options, or nullptr if not set |

!!! note
    Use create_collision_check_option() to ensure a valid configuration exists

#### get_trajectory_feasibility_check_option {#motionplanconfig-get_trajectory_feasibility_check_option-function}

```cpp
std::shared_ptr<TrajectoryFeasibilityCheckOption> galbot::sdk::MotionPlanConfig::get_trajectory_feasibility_check_option() const
```

<small>Get trajectory feasibility check option configuration (may be nullptr if not initialized)</small>

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [TrajectoryFeasibilityCheckOption](#trajectoryfeasibilitycheckoption-struct) > | Shared pointer to trajectory feasibility check options, or nullptr if not set |

!!! note
    Use create_trajectory_feasibility_check_option() to ensure a valid configuration exists

#### get_line_traj_check_primitive {#motionplanconfig-get_line_traj_check_primitive-function}

```cpp
std::shared_ptr<LineTrajCheckPrimitive> galbot::sdk::MotionPlanConfig::get_line_traj_check_primitive() const
```

<small>Get line trajectory check primitive configuration (may be nullptr if not initialized)</small>

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< [LineTrajCheckPrimitive](#linetrajcheckprimitive-struct) > | Shared pointer to line trajectory check primitive, or nullptr if not set |

!!! note
    Use create_line_traj_check_primitive() to ensure a valid configuration exists

#### get_sampler_config_ref {#motionplanconfig-get_sampler_config_ref-function}

```cpp
SamplerConfig& galbot::sdk::MotionPlanConfig::get_sampler_config_ref()
```

<small>Get mutable reference to sampler configuration.

Lazily creates a new sampler configuration with default values if not already initialized. Useful for in-place modification of configuration parameters.</small>

**Returns**

| Type | Description |
| --- | --- |
| [SamplerConfig](#samplerconfig-struct) & | Mutable reference to sampler configuration (guaranteed non-null) |

#### get_trajectory_plan_config_ref {#motionplanconfig-get_trajectory_plan_config_ref-function}

```cpp
TrajectoryPlanConfig& galbot::sdk::MotionPlanConfig::get_trajectory_plan_config_ref()
```

<small>Get mutable reference to trajectory planning configuration.

Lazily creates a new trajectory planning configuration with default values if not already initialized.</small>

**Returns**

| Type | Description |
| --- | --- |
| [TrajectoryPlanConfig](#trajectoryplanconfig-struct) & | Mutable reference to trajectory planning configuration (guaranteed non-null) |

#### get_ik_solver_config_ref {#motionplanconfig-get_ik_solver_config_ref-function}

```cpp
IKSolverConfig& galbot::sdk::MotionPlanConfig::get_ik_solver_config_ref()
```

<small>Get mutable reference to inverse kinematics solver configuration.

Lazily creates a new IK solver configuration with default values if not already initialized.</small>

**Returns**

| Type | Description |
| --- | --- |
| [IKSolverConfig](#iksolverconfig-struct) & | Mutable reference to IK solver configuration (guaranteed non-null) |

#### get_collision_check_option_ref {#motionplanconfig-get_collision_check_option_ref-function}

```cpp
CollisionCheckOption& galbot::sdk::MotionPlanConfig::get_collision_check_option_ref()
```

<small>Get mutable reference to collision check option configuration.

Lazily creates a new collision check option with default values if not already initialized.</small>

**Returns**

| Type | Description |
| --- | --- |
| [CollisionCheckOption](#collisioncheckoption-struct) & | Mutable reference to collision check options (guaranteed non-null) |

#### get_trajectory_feasibility_check_option_ref {#motionplanconfig-get_trajectory_feasibility_check_option_ref-function}

```cpp
TrajectoryFeasibilityCheckOption& galbot::sdk::MotionPlanConfig::get_trajectory_feasibility_check_option_ref()
```

<small>Get mutable reference to trajectory feasibility check option configuration.

Lazily creates a new trajectory feasibility check option with default values if not already initialized.</small>

**Returns**

| Type | Description |
| --- | --- |
| [TrajectoryFeasibilityCheckOption](#trajectoryfeasibilitycheckoption-struct) & | Mutable reference to trajectory feasibility check options (guaranteed non-null) |

#### get_line_traj_check_primitive_ref {#motionplanconfig-get_line_traj_check_primitive_ref-function}

```cpp
LineTrajCheckPrimitive& galbot::sdk::MotionPlanConfig::get_line_traj_check_primitive_ref()
```

<small>Get mutable reference to line trajectory check primitive configuration.

Lazily creates a new line trajectory check primitive with default values if not already initialized.</small>

**Returns**

| Type | Description |
| --- | --- |
| [LineTrajCheckPrimitive](#linetrajcheckprimitive-struct) & | Mutable reference to line trajectory check primitive (guaranteed non-null) |

#### get_feasibility_boundary {#motionplanconfig-get_feasibility_boundary-function}

```cpp
const std::vector<KinematicsBoundary>& galbot::sdk::MotionPlanConfig::get_feasibility_boundary() const
```

<small>Get kinematic feasibility boundaries for all chains (read-only)

Returns immutable access to the feasibility boundary configuration.</small>

**Returns**

| Type | Description |
| --- | --- |
| const std::vector< [KinematicsBoundary](#kinematicsboundary-struct) > & | Const reference to vector of kinematic feasibility boundaries |

#### get_feasibility_boundary {#motionplanconfig-get_feasibility_boundary-function}

```cpp
std::vector<KinematicsBoundary>& galbot::sdk::MotionPlanConfig::get_feasibility_boundary()
```

<small>Get kinematic feasibility boundaries for all chains (mutable)

Returns mutable access to the feasibility boundary configuration for in-place modification.</small>

**Returns**

| Type | Description |
| --- | --- |
| std::vector< [KinematicsBoundary](#kinematicsboundary-struct) > & | Mutable reference to vector of kinematic feasibility boundaries |

#### get_ik_joint_limit {#motionplanconfig-get_ik_joint_limit-function}

```cpp
const std::vector<KinematicsBoundary>& galbot::sdk::MotionPlanConfig::get_ik_joint_limit() const
```

<small>Get IK phase joint limits (read-only)</small>

**Returns**

| Type | Description |
| --- | --- |
| const std::vector< [KinematicsBoundary](#kinematicsboundary-struct) > & | Const reference to vector of IK joint limit boundaries |

#### get_ik_joint_limit {#motionplanconfig-get_ik_joint_limit-function}

```cpp
std::vector<KinematicsBoundary>& galbot::sdk::MotionPlanConfig::get_ik_joint_limit()
```

<small>Get IK phase joint limits (mutable)</small>

**Returns**

| Type | Description |
| --- | --- |
| std::vector< [KinematicsBoundary](#kinematicsboundary-struct) > & | Mutable reference to vector of IK joint limit boundaries |

#### get_sampler_joint_limit {#motionplanconfig-get_sampler_joint_limit-function}

```cpp
const std::vector<KinematicsBoundary>& galbot::sdk::MotionPlanConfig::get_sampler_joint_limit() const
```

<small>Get sampling phase joint limits (read-only)</small>

**Returns**

| Type | Description |
| --- | --- |
| const std::vector< [KinematicsBoundary](#kinematicsboundary-struct) > & | Const reference to vector of sampling joint limit boundaries |

#### get_sampler_joint_limit {#motionplanconfig-get_sampler_joint_limit-function}

```cpp
std::vector<KinematicsBoundary>& galbot::sdk::MotionPlanConfig::get_sampler_joint_limit()
```

<small>Get sampling phase joint limits (mutable)</small>

**Returns**

| Type | Description |
| --- | --- |
| std::vector< [KinematicsBoundary](#kinematicsboundary-struct) > & | Mutable reference to vector of sampling joint limit boundaries |

#### get_hard_joint_limit {#motionplanconfig-get_hard_joint_limit-function}

```cpp
const std::vector<KinematicsBoundary>& galbot::sdk::MotionPlanConfig::get_hard_joint_limit() const
```

<small>Get hard joint limits (read-only)</small>

**Returns**

| Type | Description |
| --- | --- |
| const std::vector< [KinematicsBoundary](#kinematicsboundary-struct) > & | Const reference to vector of hard joint limit boundaries |

!!! note
    Hard limits represent absolute mechanical/safety constraints

#### get_hard_joint_limit {#motionplanconfig-get_hard_joint_limit-function}

```cpp
std::vector<KinematicsBoundary>& galbot::sdk::MotionPlanConfig::get_hard_joint_limit()
```

<small>Get hard joint limits (mutable)</small>

**Returns**

| Type | Description |
| --- | --- |
| std::vector< [KinematicsBoundary](#kinematicsboundary-struct) > & | Mutable reference to vector of hard joint limit boundaries |

#### get_revert_ik_joint_limit_chains {#motionplanconfig-get_revert_ik_joint_limit_chains-function}

```cpp
const std::vector<std::string>& galbot::sdk::MotionPlanConfig::get_revert_ik_joint_limit_chains() const
```

<small>Get kinematic chains for selective IK joint limit reversion (read-only)</small>

**Returns**

| Type | Description |
| --- | --- |
| const std::vector< std::string > & | Const reference to vector of chain names for IK limit reversion |

!!! note
    Empty vector means reversion applies to all chains (if reversion is enabled)

#### get_revert_ik_joint_limit_chains {#motionplanconfig-get_revert_ik_joint_limit_chains-function}

```cpp
std::vector<std::string>& galbot::sdk::MotionPlanConfig::get_revert_ik_joint_limit_chains()
```

<small>Get kinematic chains for selective IK joint limit reversion (mutable)</small>

**Returns**

| Type | Description |
| --- | --- |
| std::vector< std::string > & | Mutable reference to vector of chain names for IK limit reversion |

#### get_revert_ik_joint_limit {#motionplanconfig-get_revert_ik_joint_limit-function}

```cpp
bool galbot::sdk::MotionPlanConfig::get_revert_ik_joint_limit()
```

<small>Check if IK joint limit reversion is enabled.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | true if IK limits should revert to hard limits, false otherwise |

#### print {#motionplanconfig-print-function}

```cpp
void galbot::sdk::MotionPlanConfig::print() const
```

<small>Print comprehensive motion planning configuration to standard output.

Outputs all sub-configuration parameters and kinematic boundaries in human-readable format. Useful for debugging, logging, and verification of configuration state.</small>


---

### MotionStatus {#galbot-sdk-motionstatus-enum}

<small>Robot motion execution status enumeration.

Represents the execution status of robot motion commands, including trajectory following, pose reaching, and other motion planning operations.</small>

| Enum Value | Description |
| --- | --- |
| `SUCCESS` | Execution succeeded, motion reached expected target position/pose |
| `TIMEOUT` | Execution timeout, motion not completed within specified time limit |
| `FAULT` | Fault occurred, motion cannot continue due to hardware or safety issue |
| `INVALID_INPUT` | Input parameters invalid or not meeting interface requirements |
| `INIT_FAILED` | Internal initialization failed, communication component or resource creation failed |
| `IN_PROGRESS` | Motion in progress but has not reached target yet |
| `STOPPED_UNREACHED` | Stopped during motion without reaching target position/pose |
| `DATA_FETCH_FAILED` | Data retrieval failed, e.g., sensor or state reading failure |
| `PUBLISH_FAIL` | Data transmission or command delivery failed, motion command may not be executed |
| `COMM_DISCONNECTED` | Communication disconnected or control node unavailable |
| `STATUS_NUM` | Total number of status enumerations (for boundary checking or array sizing) |
| `UNSUPPORTED_FUNCRION` | Function not yet supported, called interface or operation not implemented (note: typo in enum name preserved for API compatibility) |


---

### NavigationStatus {#galbot-sdk-navigationstatus-enum}

<small>Navigation task execution status enumeration.

Defines the possible outcomes when executing navigation commands such as moving to a goal position or following a path.</small>

| Enum Value | Description |
| --- | --- |
| `SUCCESS` | Execution succeeded, navigation task completed as expected |
| `FAIL` | Execution failed due to unspecified error |
| `TIMEOUT` | Execution timeout, task did not complete within allowed time |
| `INVALID_INPUT` | Input parameters do not meet requirements or are out of valid range |
| `MODE_ERR` | Current mode does not support this operation |
| `COMM_ERR` | Communication error occurred during execution |
| `WAIT_INITIALIZED` | Waiting for system initialization, navigation system not ready |


---

### NavigationTaskStatus {#galbot-sdk-navigationtaskstatus-enum}

<small>Navigation task current state enumeration.

Represents the current state of an active or completed navigation task, as reported by the navigation system. Used for polling during non-blocking navigation to detect RUNNING, SUCCESS, or FAILED and exit error logic in time.</small>

| Enum Value | Description |
| --- | --- |
| `UNKNOWN` | Task state unknown or not yet reported |
| `RUNNING` | Navigation task is in progress |
| `SUCCESS` | Navigation task completed successfully |
| `FAILED` | Navigation task failed |


---

### OdomData {#odomdata-struct}

<small>Contains robot pose and velocity estimates from odometry sources (wheel encoders, IMU fusion, etc.). Used for robot localization and navigation.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `timestamp_ns` | int64_t | Odometry timestamp (nanoseconds since epoch) |
| `position` | std::array< double, 3 > | Position [x, y, z] (meters) |
| `orientation` | std::array< double, 4 > | Orientation as quaternion [qx, qy, qz, qw] |
| `linear_velocity` | std::array< double, 3 > | Linear velocity vx, vy, vz |
| `angular_velocity` | std::array< double, 3 > | Angular velocity ωx, ωy, ωz |


---

### Parameter {#parameter-class}

<small>Motion planning parameter configuration class.

This class extends [PlannerConfig](#plannerconfig-struct) to provide comprehensive configuration options for whole-body motion planning and execution. It encapsulates execution mode, actuation type, tool frame handling, collision checking, and coordinate frame specifications. All angular parameters are expected in radians, linear parameters in meters (SI units).</small>

#### Parameter {#parameter-parameter-function}

```cpp
galbot::sdk::Parameter::Parameter()=default
```

<small>Default constructor.

Initializes [Parameter](#parameter-class) with default values inherited from [PlannerConfig](#plannerconfig-struct).</small>

#### Parameter {#parameter-parameter-function}

```cpp
galbot::sdk::Parameter::Parameter(
    bool direct_execute,
    bool blocking,
    double timeout,
    std::string actuate,
    bool tool_pose,
    bool check_collision,
    const std::string &frame="base_link"
)
```

<small>Parameterized constructor for whole-body motion planning configuration.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `direct_execute` | bool | If true, immediately executes the planned motion; if false, only computes the plan |
| `blocking` | bool | If true, blocks until motion completes or times out; if false, returns immediately |
| `timeout` | double | Maximum allowed time for motion execution (in seconds) |
| `actuate` | std::string | Actuation type string key (see g_actuate_type_map): "with_chain_only", "with_torso", or "with_leg" |
| `tool_pose` | bool | If true, target pose is relative to tool frame; if false, relative to end-effector flange |
| `check_collision` | bool | If true, enables collision checking during planning; if false, skips collision detection |
| `frame` | const std::string & | Reference frame for pose specifications, defaults to "base_link" (robot base frame) |

!!! note
    timeout is only relevant when blocking is true.

!!! note
    Invalid actuate strings will cause undefined behavior; ensure key exists in g_actuate_type_map.

#### set_direct_execute {#parameter-set_direct_execute-function}

```cpp
void galbot::sdk::Parameter::set_direct_execute(bool direct_execute)
```

<small>Set direct execution mode.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `direct_execute` | bool | If true, planned motion is immediately executed on the robot; if false, only computes the trajectory without execution |

#### set_blocking {#parameter-set_blocking-function}

```cpp
void galbot::sdk::Parameter::set_blocking(bool blocking)
```

<small>Set blocking execution mode.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `blocking` | bool | If true, function blocks until motion completes or times out; if false, returns immediately after sending motion command |

#### set_timeout {#parameter-set_timeout-function}

```cpp
void galbot::sdk::Parameter::set_timeout(double timeout)
```

<small>Set motion execution timeout.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `timeout` | double | Maximum allowed time for motion execution (in seconds, must be positive) |

!!! note
    Only applies when blocking mode is enabled.

#### set_actuate {#parameter-set_actuate-function}

```cpp
void galbot::sdk::Parameter::set_actuate(const std::string &actuate)
```

<small>Set actuation type for whole-body coordination.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `actuate` | const std::string & | Actuation type string key: "with_chain_only" (arms only), "with_torso" (arms + torso), or "with_leg" (arms + legs) |

!!! warning
    Must be a valid key in g_actuate_type_map, otherwise behavior is undefined.

#### set_tool_pose {#parameter-set_tool_pose-function}

```cpp
void galbot::sdk::Parameter::set_tool_pose(bool tool_pose)
```

<small>Set tool coordinate frame usage.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `tool_pose` | bool | If true, target poses are interpreted relative to the tool frame (TCP); if false, relative to the end-effector flange frame |

#### set_check_collision {#parameter-set_check_collision-function}

```cpp
void galbot::sdk::Parameter::set_check_collision(bool check_collision)
```

<small>Enable or disable collision checking.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `check_collision` | bool | If true, planner performs collision detection against self-collisions and environment obstacles; if false, skips collision checking |

!!! warning
    Disabling collision checking may result in unsafe trajectories.

#### set_reference_frame {#parameter-set_reference_frame-function}

```cpp
void galbot::sdk::Parameter::set_reference_frame(const std::string &frame)
```

<small>Set the reference frame for pose specifications.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `frame` | const std::string & | Reference frame name (e.g., "base_link", "world", "odom") |

!!! note
    Must be a valid frame in the robot's TF tree.

#### set_move_line {#parameter-set_move_line-function}

```cpp
void galbot::sdk::Parameter::set_move_line(bool flag)
```

<small>Set Cartesian linear motion mode.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `flag` | bool | If true, uses linear (straight-line) Cartesian motion; if false, uses joint-space interpolation (may result in curved end-effector paths) |

!!! note
    Linear motion provides predictable Cartesian paths but may have joint velocity discontinuities.

#### get_direct_execute {#parameter-get_direct_execute-function}

```cpp
bool galbot::sdk::Parameter::get_direct_execute() const
```

<small>Get direct execution mode status.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | true if direct execution is enabled, false otherwise |

#### get_blocking {#parameter-get_blocking-function}

```cpp
bool galbot::sdk::Parameter::get_blocking() const
```

<small>Get blocking execution mode status.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | true if blocking mode is enabled, false otherwise |

#### get_timeout {#parameter-get_timeout-function}

```cpp
double galbot::sdk::Parameter::get_timeout() const
```

<small>Get motion execution timeout value.</small>

**Returns**

| Type | Description |
| --- | --- |
| double | Timeout duration in seconds (positive value) |

#### get_actuate_type {#parameter-get_actuate_type-function}

```cpp
std::string galbot::sdk::Parameter::get_actuate_type() const
```

<small>Get actuation type as string.

Performs reverse lookup in g_actuate_type_map to convert enum to string key.</small>

**Returns**

| Type | Description |
| --- | --- |
| std::string | Actuation type string ("with_chain_only", "with_torso", "with_leg", or "unknown" if not found) |

#### get_tool_pose {#parameter-get_tool_pose-function}

```cpp
bool galbot::sdk::Parameter::get_tool_pose() const
```

<small>Get tool coordinate frame usage status.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | true if using tool frame (TCP), false if using end-effector flange frame |

#### get_check_collision {#parameter-get_check_collision-function}

```cpp
bool galbot::sdk::Parameter::get_check_collision() const
```

<small>Get collision checking status.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | true if collision checking is enabled, false otherwise |

#### get_reference_frame {#parameter-get_reference_frame-function}

```cpp
std::string galbot::sdk::Parameter::get_reference_frame() const
```

<small>Get reference frame name.</small>

**Returns**

| Type | Description |
| --- | --- |
| std::string | Reference frame identifier string (e.g., "base_link", "world") |

#### is_move_line {#parameter-is_move_line-function}

```cpp
bool galbot::sdk::Parameter::is_move_line()
```

<small>Check if Cartesian linear motion mode is enabled.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | true if using linear Cartesian interpolation, false if using joint-space interpolation |


---

### PerceptionModule {#galbot_perception_types-hpp-perceptionmodule-enum}

<small>Enabled perception pipelines (model sets loaded at init).</small>

| Enum Value | Description |
| --- | --- |
| `FOUNDATION_STEREO` |  |
| `LIGHT_STEREO` |  |
| `STATUS_NUM` |  |


---

### PlannerConfig {#plannerconfig-struct}

<small>Motion planning configuration structure.

Comprehensive configuration for robot motion planning and execution, controlling behavior such as planning mode, collision checking, reference frames, and execution parameters.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `is_direct_execute` | bool | Whether to execute trajectory immediately after planning.<br><br>true: Plan and execute the trajectory in one operation false: Only plan the trajectory without executing (for preview or validation) |
| `is_blocking` | bool | Whether to wait synchronously for operation completion.<br><br>true: Block until planning/execution completes or timeout occurs false: Return immediately after initiating operation (asynchronous mode) |
| `timeout_second` | double | Timeout duration for blocking operations (seconds)<br><br>Maximum time to wait for planning or execution completion when is_blocking = true. Default: 20 seconds |
| `actuate_type` | [ActuateType](#galbot-sdk-actuatetype-enum) | Actuation mode specifying which kinematic chains to use.<br><br>Determines whether to use only the target arm, or also involve torso/leg motion for extended workspace or mobile manipulation. |
| `is_tool_pose` | bool | Whether target is specified as tool center point (TCP) pose.<br><br>true: Target is end-effector TCP pose (Cartesian space) false: Target is joint space configuration |
| `is_relative_pose` | bool | Whether target pose is relative to current pose.<br><br>true: Target pose is relative displacement from current end-effector pose false: Target pose is absolute in the specified reference frame |
| `is_check_collision` | bool | Whether to enable collision checking during planning.<br><br>true: Check collisions with obstacles and self-collisions false: Disable collision checking (use with caution) |
| `reference_frame` | std::string | Reference coordinate frame for target pose.<br><br>Specifies the coordinate frame in which target poses are expressed. Common values: "base_link", "world", "odom" |
| `joint_state` | std::unordered_map< std::string, std::vector< double > > | Specifies starting joint configuration for planning. If empty, uses current robot state. Key: Joint group identifier Value: Vector of joint angles (radians) for that group |
| `move_line` | bool | true: Plan straight-line motion in Cartesian space (end-effector moves in straight line) false: Plan standard joint-space or task-space trajectory (may not be Cartesian linear) |


---

### PlanTaskResult {#plantaskresult-struct}

<small>Contains the complete result of a motion planning operation, including success status, generated trajectory, kinematics solutions, and collision information.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `task_id` | std::string | Used to track and distinguish different planning tasks, especially in asynchronous operations. |
| `success` | bool | true: Planning completed successfully false: Planning failed (check error_code and error_message for details) |
| `error_code` | int | Used for programmatic error handling. Zero typically indicates success, non-zero values indicate specific error conditions. |
| `error_message` | std::string | Provides detailed description of failure reason or exception information when success = false. |
| `trajectory` | struct [[galbot::sdk::[PlanTaskResult](#plantaskresult-struct)](#plantaskresult-struct)::[Trajectory](#trajectory-struct)](#trajectory-struct) | Contains the complete planned trajectory with joint positions and timing information. |
| `ik_result` | std::unordered_map< std::string, std::vector< double > > | Maps kinematic chain name to solved joint configuration (radians). Key: Joint chain name (e.g., "left_arm", "right_arm") Value: Vector of joint angles (radians) |
| `fk_result` | std::unordered_map< std::string, [Pose](#pose-struct) > | Maps link or end-effector name to computed pose. Key: Link or end-effector name (e.g., "left_gripper", "right_hand") Value: Computed pose (position + orientation) |
| `collision_result` | std::vector< double > | Optional field containing collision distances or penetration depths. Empty vector typically means no collision check was performed. Non-empty values may represent minimum distances to obstacles or collision severity. |


---

### Point {#point-struct}

<small>Represents a position in three-dimensional Cartesian space.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `x` | double | X coordinate (meters) |
| `y` | double | Y coordinate (meters) |
| `z` | double | Z coordinate (meters) |


---

### PointField {#pointfield-struct}

<small>Describes one data field in a PointCloud2 point structure, defining its name, type, offset, and count. Compatible with ROS 2 sensor_msgs/[PointField](#pointfield-struct).</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `name` | std::string | Identifier for this data channel. Standard field names include: "x", "y", "z": 3D Cartesian coordinates (meters) "intensity": Reflection intensity (unitless or sensor-specific) "rgb" or "rgba": Color information (packed RGB or RGBA) "ring": Lidar ring/laser index (integer) "timestamp": Per-point timestamp (seconds or nanoseconds) |
| `offset` | uint32_t | Byte offset of this field from the beginning of a point's data structure. Example: For point layout {x:float32, y:float32, z:float32}, offsets are: x=0, y=4, z=8 |
| `datatype` | [DataType](#galbot-sdk-pointfield-datatype-enum) | Specifies the primitive data type using the [DataType](#galbot-sdk-pointfield-datatype-enum) enumeration. |
| `count` | uint32_t | Array length for this field. Typically 1 for scalar fields (x, y, z, intensity). May be > 1 for array fields (e.g., count=3 for a 3-element vector). |

**Nested Enums**

##### DataType {#galbot-sdk-pointfield-datatype-enum}

Defines primitive data types for point cloud fields, determining byte size and interpretation method for each field value.

| Enum Value | Description |
| --- | --- |
| `UNKNOWN` | Unknown or unspecified type |
| `INT8` | 8-bit signed integer (1 byte) |
| `UINT8` | 8-bit unsigned integer (1 byte) |
| `INT16` | 16-bit signed integer (2 bytes) |
| `UINT16` | 16-bit unsigned integer (2 bytes) |
| `INT32` | 32-bit signed integer (4 bytes) |
| `UINT32` | 32-bit unsigned integer (4 bytes) |
| `FLOAT32` | 32-bit IEEE 754 floating point (4 bytes) |
| `FLOAT64` | 64-bit IEEE 754 floating point (8 bytes) |


---

### Pose {#pose-struct}

<small>[Pose](#pose-struct) (position + orientation) structure.

Represents a full 6-DOF (Degrees of Freedom) pose in 3D space, combining position (translation) and orientation (rotation) information. Commonly used for robot end-effector poses, object poses, and coordinate frame transforms.</small>

#### Pose {#pose-pose-function}

```cpp
galbot::sdk::Pose::Pose()=default
```

<small>Default constructor.

Initializes pose at origin (0,0,0) with identity rotation.</small>

#### Pose {#pose-pose-function}

```cpp
galbot::sdk::Pose::Pose(const T &pos, const T &quat)
```

<small>Initialize [Pose](#pose-struct) using separate position and quaternion containers.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `pos` | const T & | 3D position vector [x, y, z] in meters, must have size 3 |
| `quat` | const T & | [Quaternion](#quaternion-struct) vector [x, y, z, w], must have size 4 |

#### Pose {#pose-pose-function}

```cpp
galbot::sdk::Pose::Pose(const T &vec)
```

<small>Initialize [Pose](#pose-struct) using a single 7-dimensional vector.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `vec` | const T & | 7D vector: [x, y, z, qx, qy, qz, qw] where first 3 elements are position (meters) and last 4 elements are quaternion |

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `position` | [Point](#point-struct) | Position in 3D space (x, y, z) in meters |
| `orientation` | [Quaternion](#quaternion-struct) | Orientation as unit quaternion (x, y, z, w) |


---

### PoseState {#posestate-class}

<small>Represents a target end-effector pose in Cartesian space (SE(3)). Extends [RobotStates](#robotstates-class) to specify pose-based motion goals for kinematic chains. Used in inverse kinematics and Cartesian trajectory planning. [Pose](#pose-struct) values: position in meters, orientation as unit quaternion. Coordinate frames must exist in the robot's TF tree.</small>

#### get_type {#posestate-get_type-function}

```cpp
Type galbot::sdk::PoseState::get_type() const override
```

<small>Get runtime type identifier.</small>

**Returns**

| Type | Description |
| --- | --- |
| [Type](#galbot-sdk-robotstates-type-enum) | , indicating this is a Cartesian pose target |

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `frame_id` | std::string | Target frame on the kinematic chain (e.g., "EndEffector", "Camera", "TCP") |
| `reference_frame` | std::string | Reference coordinate frame (e.g., "base_link", "world", "odom") |
| `pose` | [Pose](#pose-struct) | Target Cartesian pose: position (meters) + orientation (unit quaternion) |


---

### Quaternion {#quaternion-struct}

<small>Represents a 3D rotation using quaternion representation (x, y, z, w). A unit quaternion has magnitude 1 and represents a valid rotation.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `x` | double | X component of the quaternion vector part |
| `y` | double | Y component of the quaternion vector part |
| `z` | double | Z component of the quaternion vector part |
| `w` | double | W component, scalar part (for identity rotation, w=1 and x=y=z=0) |


---

### ReferenceFrame {#galbot-sdk-referenceframe-enum}

<small>Specifies the coordinate frame in which poses, positions, or trajectories are expressed. Note: This is a plain enum (not enum class) for C-style compatibility.</small>

| Enum Value | Description |
| --- | --- |
| `FRAME_WORLD` | World/global coordinate frame, fixed reference frame |
| `FRAME_BASE` | Robot base coordinate frame, attached to mobile base |


---

### RegionOfInterest {#regionofinterest-struct}

<small>Defines a rectangular sub-region within an image for selective processing. Compatible with ROS 2 sensor_msgs/[RegionOfInterest](#regionofinterest-struct).</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `x_offset` | uint32_t | Horizontal pixel coordinate of the ROI's left edge. 0 means ROI starts at the image's left edge. |
| `y_offset` | uint32_t | Vertical pixel coordinate of the ROI's top edge. 0 means ROI starts at the image's top edge. |
| `height` | uint32_t | Number of pixel rows in the region of interest. |
| `width` | uint32_t | Number of pixel columns in the region of interest. |
| `do_rectify` | bool | true: Apply camera rectification to this ROI before processing false: Use raw image data without rectification, or capture full resolution |


---

### RgbData {#rgbdata-struct}

<small>Contains compressed color image data from RGB cameras. Compatible with ROS 2 sensor_msgs/CompressedImage format.</small>

#### convert_to_cv2_mat {#rgbdata-convert_to_cv2_mat-function}

```cpp
std::shared_ptr<cv::Mat> galbot::sdk::RgbData::convert_to_cv2_mat()
```

<small>Decode compressed image data to OpenCV Mat.

Decodes the internally stored compressed binary data using cv::imdecode.</small>

**Returns**

| Type | Description |
| --- | --- |
| std::shared_ptr< cv::Mat > | std::shared_ptr<cv::Mat> Smart pointer to decoded image on success, nullptr on failure |

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `header` | [Header](#header-struct) | Contains acquisition timestamp and camera coordinate frame ID. |
| `format` | std::string | Specifies compression format and encoding. Examples: "jpeg", "png", "bgr8; jpeg compressed bgr8" |
| `data` | std::vector< uint8_t > | Binary blob containing the compressed image (JPEG, PNG, etc.). |


---

### RobotStates {#robotstates-class}

<small>Encapsulates the complete kinematic state of the robot, including whole-body joint configuration and mobile base pose. This class serves as a base for more specialized state representations ([PoseState](#posestate-class), [JointStates](#jointstates-class)) and is used throughout the planning and control pipeline for state specification and feedback. All angular values are in radians, linear values in meters (SI units). Base pose uses quaternion representation for orientation (x, y, z, qx, qy, qz, qw).</small>

#### get_type {#robotstates-get_type-function}

```cpp
virtual Type galbot::sdk::RobotStates::get_type() const
```

<small>Get the runtime type of this state object.</small>

**Returns**

| Type | Description |
| --- | --- |
| [Type](#galbot-sdk-robotstates-type-enum) | [Type](#galbot-sdk-robotstates-type-enum) enumeration value, ROBOT_STATES for base class |

#### RobotStates {#robotstates-robotstates-function}

```cpp
galbot::sdk::RobotStates::RobotStates()=default
```

<small>Default constructor.

Creates an empty [RobotStates](#robotstates-class) object with uninitialized joint and base states.</small>

#### set_whole_body_joint {#robotstates-set_whole_body_joint-function}

```cpp
void galbot::sdk::RobotStates::set_whole_body_joint(const std::vector< double > &joint_positions)
```

<small>Set complete whole-body joint configuration.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `joint_positions` | const std::vector< double > & | Vector of joint angles (in radians), must match robot DOF |

!!! note
    Vector size should equal the total number of actuated joints in the robot.

#### set_base_state {#robotstates-set_base_state-function}

```cpp
void galbot::sdk::RobotStates::set_base_state(const Pose &base_pose)
```

<small>Set mobile base pose.

Converts [Pose](#pose-struct) structure to internal base_state vector representation.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `base_pose` | const [Pose](#pose-struct) & | Base pose in SE(3): position (meters) and orientation (quaternion) |

!!! note
    Quaternion must be unit-normalized (x^2 + y^2 + z^2 + w^2 = 1).

#### RobotStates {#robotstates-robotstates-function}

```cpp
galbot::sdk::RobotStates::RobotStates(
    const std::string &chain,
    const std::vector< double > &whole_joint,
    const Pose &base_pose
)
```

<small>Parameterized constructor for complete robot state initialization.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `chain` | const std::string & | Kinematic chain name (e.g., "left_arm", "right_arm") |
| `whole_joint` | const std::vector< double > & | Complete joint configuration vector (radians) |
| `base_pose` | const [Pose](#pose-struct) & | Mobile base pose: position (meters) + orientation (unit quaternion) |

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `chain_name` | std::string | Kinematic chain identifier (e.g., "left_arm", "right_arm") |
| `whole_body_joint` | std::vector< double > | Complete robot joint configuration (radians), ordered by joint index. |
| `base_state` | std::vector< double > | Mobile base pose: [x, y, z, qx, qy, qz, qw] (meters, quaternion) |

**Nested Enums**

##### Type {#galbot-sdk-robotstates-type-enum}

Enumeration for distinguishing derived state types.

Used for runtime type identification of [RobotStates](#robotstates-class)-derived classes.

| Enum Value | Description |
| --- | --- |
| `POSE` | [PoseState](#posestate-class): Cartesian pose target. |
| `JOINT` | [JointStates](#jointstates-class): Joint space target. |
| `ROBOT_STATES` | [RobotStates](#robotstates-class): Generic whole-body state. |


---

### SamplerConfig {#samplerconfig-struct}

<small>Configuration parameters for sampling-based motion planners.

This structure configures sampling-based planning algorithms (e.g., RRT, RRT*). It controls state space sampling resolution, interpolation settings, path simplification, and planning termination conditions. Sampling-based planners explore the configuration space by randomly sampling states and connecting them to build a motion plan graph.</small>

#### set_state_check_type {#samplerconfig-set_state_check_type-function}

```cpp
void galbot::sdk::SamplerConfig::set_state_check_type(StateCheckType type)
```

<small>Set the distance metric for state comparison.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `type` | [StateCheckType](#galbot-sdk-samplerconfig-statechecktype-enum) | Distance metric type for evaluating state similarity |

#### set_state_check_resolution {#samplerconfig-set_state_check_resolution-function}

```cpp
void galbot::sdk::SamplerConfig::set_state_check_resolution(double resolution)
```

<small>Set state comparison resolution threshold.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `resolution` | double | Minimum distance threshold to consider two states as distinct (units: rad or dimensionless) |

!!! note
    Lower values increase planning precision but may slow down computation

#### set_interpolate {#samplerconfig-set_interpolate-function}

```cpp
void galbot::sdk::SamplerConfig::set_interpolate(bool enable)
```

<small>Enable or disable path interpolation between sampled states.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `enable` | bool | true to enable interpolation, false to use only sampled waypoints |

!!! note
    Interpolation improves trajectory smoothness and collision checking accuracy

#### set_interpolation_cnt {#samplerconfig-set_interpolation_cnt-function}

```cpp
void galbot::sdk::SamplerConfig::set_interpolation_cnt(int cnt)
```

<small>Set the number of interpolation waypoints between consecutive samples.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `cnt` | int | Number of intermediate waypoints to insert (0 = use automatic calculation) |

!!! note
    Higher counts improve collision detection but increase computational cost

#### set_simplify {#samplerconfig-set_simplify-function}

```cpp
void galbot::sdk::SamplerConfig::set_simplify(bool enable)
```

<small>Enable or disable path simplification post-processing.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `enable` | bool | true to enable path shortcutting and smoothing, false to use raw planned path |

!!! note
    Simplification reduces waypoints and improves trajectory efficiency

#### set_max_simplification_time {#samplerconfig-set_max_simplification_time-function}

```cpp
void galbot::sdk::SamplerConfig::set_max_simplification_time(double time)
```

<small>Set maximum time budget for path simplification.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `time` | double | Maximum simplification duration (units: s); negative values indicate no time limit |

!!! note
    Longer simplification time may yield shorter, smoother paths

#### set_termination_condition_type {#samplerconfig-set_termination_condition_type-function}

```cpp
void galbot::sdk::SamplerConfig::set_termination_condition_type(TerminationConditionType type)
```

<small>Set planning termination condition.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `type` | [TerminationConditionType](#galbot-sdk-samplerconfig-terminationconditiontype-enum) | Termination criterion (timeout only vs. timeout or exact solution) |

#### set_max_planning_time {#samplerconfig-set_max_planning_time-function}

```cpp
void galbot::sdk::SamplerConfig::set_max_planning_time(double time)
```

<small>Set maximum time budget for motion planning.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `time` | double | Maximum planning duration (units: s) |

!!! note
    Planning may terminate earlier if exact solution is found (depends on termination condition)

#### get_state_check_type {#samplerconfig-get_state_check_type-function}

```cpp
StateCheckType galbot::sdk::SamplerConfig::get_state_check_type() const
```

<small>Get the configured distance metric for state comparison.</small>

**Returns**

| Type | Description |
| --- | --- |
| [StateCheckType](#galbot-sdk-samplerconfig-statechecktype-enum) | Current state check type |

#### get_state_check_resolution {#samplerconfig-get_state_check_resolution-function}

```cpp
double galbot::sdk::SamplerConfig::get_state_check_resolution() const
```

<small>Get state comparison resolution threshold.</small>

**Returns**

| Type | Description |
| --- | --- |
| double | Resolution value (units: rad or dimensionless, depending on state check type) |

#### get_interpolate {#samplerconfig-get_interpolate-function}

```cpp
bool galbot::sdk::SamplerConfig::get_interpolate() const
```

<small>Check if path interpolation is enabled.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | true if interpolation is enabled, false otherwise |

#### get_interpolation_cnt {#samplerconfig-get_interpolation_cnt-function}

```cpp
int galbot::sdk::SamplerConfig::get_interpolation_cnt() const
```

<small>Get the number of interpolation waypoints.</small>

**Returns**

| Type | Description |
| --- | --- |
| int | Number of intermediate waypoints between samples |

#### get_simplify {#samplerconfig-get_simplify-function}

```cpp
bool galbot::sdk::SamplerConfig::get_simplify() const
```

<small>Check if path simplification is enabled.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | true if path simplification is enabled, false otherwise |

#### get_max_simplification_time {#samplerconfig-get_max_simplification_time-function}

```cpp
double galbot::sdk::SamplerConfig::get_max_simplification_time() const
```

<small>Get maximum path simplification time budget.</small>

**Returns**

| Type | Description |
| --- | --- |
| double | Maximum simplification time (units: s); negative values indicate no limit |

#### get_termination_condition_type {#samplerconfig-get_termination_condition_type-function}

```cpp
TerminationConditionType galbot::sdk::SamplerConfig::get_termination_condition_type() const
```

<small>Get planning termination condition.</small>

**Returns**

| Type | Description |
| --- | --- |
| [TerminationConditionType](#galbot-sdk-samplerconfig-terminationconditiontype-enum) | Current termination condition type |

#### get_max_planning_time {#samplerconfig-get_max_planning_time-function}

```cpp
double galbot::sdk::SamplerConfig::get_max_planning_time() const
```

<small>Get maximum planning time budget.</small>

**Returns**

| Type | Description |
| --- | --- |
| double | Maximum planning time (units: s) |

#### print {#samplerconfig-print-function}

```cpp
void galbot::sdk::SamplerConfig::print() const
```

<small>Print sampler configuration to standard output.

Outputs all configuration parameters for debugging and verification.</small>

**Nested Enums**

##### StateCheckType {#galbot-sdk-samplerconfig-statechecktype-enum}

Distance metric for comparing states in configuration space.

| Enum Value | Description |
| --- | --- |
| `EUCLIDEAN_DISTANCE` | Cartesian Euclidean distance in joint space (treats joint angles as Cartesian coordinates) |
| `RADIAN_DISTANCE` | Angular distance metric accounting for joint angle wraparound and weighting |

##### TerminationConditionType {#galbot-sdk-samplerconfig-terminationconditiontype-enum}

Planning termination criteria.

| Enum Value | Description |
| --- | --- |
| `TIMEOUT` | Terminate only when maximum planning time is exceeded |
| `TIMEOUT_AND_EXACT_SOLUTION` | Terminate when timeout occurs OR exact goal solution is found |


---

### SeedType {#galbot-sdk-seedtype-enum}

<small>Specifies the initialization strategy for inverse kinematics (IK) solvers. Different seed types affect convergence speed and solution quality.</small>

| Enum Value | Description |
| --- | --- |
| `RANDOM_SEED` | Random seed, generates random initial joint configurations |
| `RANDOM_PROGRESSIVE_SEED` | Random progressive seed, tries multiple random seeds iteratively (recommended for robustness) |
| `USER_DEFINED_SEED` | User-defined seed, uses explicitly provided initial joint configuration |
| `SEED_TYPE_NUM` | Total number of seed types (for boundary checking or array sizing) |


---

### SensorStatus {#galbot-sdk-sensorstatus-enum}

<small>Represents the status of sensor data acquisition and processing operations, applicable to cameras, lidar, IMU, force sensors, and other sensor types.</small>

| Enum Value | Description |
| --- | --- |
| `SUCCESS` | Execution succeeded, sensor data valid and operation completed |
| `TIMEOUT` | Execution timeout, data acquisition or operation not completed within specified time limit |
| `FAULT` | Fault occurred, sensor detected anomaly and cannot continue normal operation |
| `INVALID_INPUT` | Input parameters invalid or not meeting interface requirements |
| `INIT_FAILED` | Initialization failed, internal communication or dependent component creation failed |
| `IN_PROGRESS` | Operation in progress but not yet completed |
| `STOPPED_UNREACHED` | Stopped during execution without completing expected operation |
| `DATA_FETCH_FAILED` | Data acquisition or reading failed, sensor may be disconnected or malfunctioning |
| `PUBLISH_FAIL` | Data transmission or reporting failed, unable to publish sensor data |
| `COMM_DISCONNECTED` | Sensor communication connection lost, no data available |
| `STATUS_NUM` | Total number of status enumerations (for boundary checking or array sizing) |


---

### SensorType {#galbot-sdk-sensortype-enum}

<small>Sensor type enumeration describing various sensors on the robot.

Identifies different sensor types available on the robot for perception, localization, and manipulation tasks.</small>

| Enum Value | Description |
| --- | --- |
| `HEAD_LEFT_CAMERA` | Head left camera, typically RGB camera for stereo vision . |
| `HEAD_RIGHT_CAMERA` | Head right camera, typically RGB camera for stereo vision . |
| `LEFT_ARM_CAMERA` | Left arm camera, mounted on left manipulator for visual servoing . |
| `RIGHT_ARM_CAMERA` | Right arm camera, mounted on right manipulator for visual servoing . |
| `LEFT_ARM_DEPTH_CAMERA` | Left arm depth camera, provides RGB-D data for left arm workspace . |
| `RIGHT_ARM_DEPTH_CAMERA` | Right arm depth camera, provides RGB-D data for right arm workspace . |
| `BASE_LIDAR` | G1 Base LiDAR . |
| `TORSO_IMU` | G1 Torso IMU (Inertial Measurement Unit), measures acceleration and angular velocity . |
| `BASE_ULTRASONIC` | Base ultrasonic sensor array, for proximity detection and collision avoidance . |
| `LEFT_FRONT_SURROUND_CAMERA` | G1 left-front surround color camera . |
| `RIGHT_FRONT_SURROUND_CAMERA` | G1 right-front surround color camera . |
| `LEFT_REAR_SURROUND_CAMERA` | G1 left-rear surround color camera . |
| `RIGHT_REAR_SURROUND_CAMERA` | G1 right-rear surround color camera . |
| `SENSOR_NUM` | Total number of sensor enumerations (for boundary checking or array sizing) . |


---

### SingoriXTarget {#singorixtarget-struct}

<small>SDK mirror of galbot.singorix_proto.[SingoriXTarget](#singorixtarget-struct).</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `header` | [Header](#header-struct) |  |
| `target_group_trajectory_map` | std::unordered_map< std::string, [TargetGroupTrajectory](#targetgrouptrajectory-struct) > |  |
| `target_task_trajectory_map` | std::unordered_map< std::string, [TargetTaskTrajectory](#targettasktrajectory-struct) > |  |


---

### SUCTION_ACTION_STATE {#galbot-sdk-suction_action_state-enum}

<small>Represents the operational state of a vacuum suction cup end-effector, tracking the suction process from idle to success or failure.</small>

| Enum Value | Description |
| --- | --- |
| `suction_action_idle` | Idle state, vacuum not activated |
| `suction_action_sucking` | Suction in progress, attempting to grasp object |
| `suction_action_success` | Suction successful, pressure decreased indicating secure grasp |
| `suction_action_failed` | Suction failed, pressure did not decrease (no object or seal failure) |


---

### SuctionCupState {#suctioncupstate-struct}

<small>Contains the current state of a vacuum suction cup gripper, including activation status, pressure reading, and action state.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `timestamp_ns` | int64_t | State timestamp (nanoseconds since epoch) |
| `activation` | bool | Activation flag: true if vacuum is on, false if off |
| `pressure` | double | Current vacuum pressure (Pascals), typically negative for suction |
| `action_state` | [SUCTION_ACTION_STATE](#galbot-sdk-suction_action_state-enum) | Current suction action state |


---

### TargetConfig {#targetconfig-struct}

<small>Common target configuration shared by group and task trajectories.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `target_data` | int32_t |  |
| `target_type` | int32_t |  |
| `target_sampling` | [TargetSampling](#galbot-sdk-targetsampling-enum) |  |
| `target_priority` | int32_t |  |
| `target_id` | std::string |  |
| `target_ts` | [Timestamp](#timestamp-struct) |  |


---

### TargetDataBits {#galbot-sdk-targetdatabits-enum}

<small>Bitmask describing which fields in a target are meaningful.

Mirrors galbot.singorix_proto.TargetData while remaining in the SDK type layer.</small>

| Enum Value | Description |
| --- | --- |
| `TARGET_DATA_NONE` |  |
| `TARGET_DATA_JOINT_POS` |  |
| `TARGET_DATA_JOINT_VEL` |  |
| `TARGET_DATA_JOINT_ACC` |  |
| `TARGET_DATA_JOINT_EFF` |  |
| `TARGET_DATA_FRAME_POSE` |  |
| `TARGET_DATA_FRAME_TWIST` |  |
| `TARGET_DATA_FRAME_WRENCH` |  |
| `TARGET_DATA_DEFAULT` |  |


---

### TargetGroupTrajectory {#targetgrouptrajectory-struct}

<small>Target trajectory for a group of joints.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `target_config` | [TargetConfig](#targetconfig-struct) |  |
| `joint_names` | std::vector< std::string > |  |
| `group_commands` | std::vector< [GroupCommand](#groupcommand-struct) > |  |


---

### TargetSampling {#galbot-sdk-targetsampling-enum}

<small>Sampling strategy for a target trajectory.

Mirrors galbot.singorix_proto.[TargetSampling](#galbot-sdk-targetsampling-enum) while remaining in the SDK type layer.</small>

| Enum Value | Description |
| --- | --- |
| `TARGET_SAMPLING_DEFAULT` |  |
| `TARGET_SAMPLING_DIRECT_PASS` |  |
| `TARGET_SAMPLING_LINEAR_INTERPOLATE` |  |
| `TARGET_SAMPLING_TRAPEZOIDAL_PROFILE` |  |
| `TARGET_SAMPLING_S_CURVE_PROFILE` |  |
| `TARGET_SAMPLING_CUBIC_SPLINES` |  |
| `TARGET_SAMPLING_QUINTIC_SPLINES` |  |
| `TARGET_SAMPLING_B_SPLINES` |  |
| `TARGET_SAMPLING_CUSTOM` |  |


---

### TargetTaskTrajectory {#targettasktrajectory-struct}

<small>Target trajectory for task-space control.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `target_config` | [TargetConfig](#targetconfig-struct) |  |
| `group_names` | std::vector< std::string > |  |
| `joint_names` | std::vector< std::string > |  |
| `subtask_names` | std::vector< std::string > |  |
| `task_commands` | std::vector< [TaskCommand](#taskcommand-struct) > |  |


---

### TargetTypeBits {#galbot-sdk-targettypebits-enum}

<small>Bitmask describing how a target should be applied.

Mirrors galbot.singorix_proto.TargetType while remaining in the SDK type layer.</small>

| Enum Value | Description |
| --- | --- |
| `TARGET_TYPE_NONE` |  |
| `TARGET_TYPE_TOUCH` |  |
| `TARGET_TYPE_CLEAR` |  |
| `TARGET_TYPE_PREPENDNOW` |  |
| `TARGET_TYPE_APPEND` |  |
| `TARGET_TYPE_OVERRIDE` |  |
| `TARGET_TYPE_PROVERRIDE` |  |
| `TARGET_TYPE_DEFAULT` |  |


---

### TaskCommand {#taskcommand-struct}

<small>Task-space command at a specific time point.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `time_from_start_s` | double |  |
| `subtask_commands` | std::vector< [FrameTriad](#frametriad-struct) > |  |


---

### Timestamp {#timestamp-struct}

<small>Represents high-precision time points with second and nanosecond components. Compatible with ROS 2 builtin_interfaces/Time and std_msgs/[Header](#header-struct) timestamp format.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `sec` | int64_t | Number of seconds since UNIX Epoch (1970-01-01 00:00:00 UTC). |
| `nanosec` | uint32_t | Nanosecond portion within the current second. Valid range: [0, 999,999,999] (< 1 second) |


---

### Trajectory {#trajectory-struct}

<small>Contains the complete planned trajectory with joint positions and timing information.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `joint_positions` | std::vector< std::vector< double > > | Each element is a vector of joint angles (radians) representing robot configuration at one waypoint. Inner vector size = number of joints, outer vector size = number of waypoints. |
| `timestamps` | std::vector< double > | Cumulative time from trajectory start. Size must match joint_positions size. |


---

### Trajectory {#trajectory-struct}

<small>Represents a complete robot trajectory consisting of multiple waypoints over time.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `points` | std::vector< [TrajectoryPoint](#trajectorypoint-struct) > | Ordered list of trajectory waypoints |
| `joint_groups` | std::vector< std::string > | Joint-group names used to expand target joints in-order. Example: {"head","left_arm"} maps to head_joint1, head_joint2, left_arm_joint1 ... left_arm_joint7. If empty (and joint_names is also empty), SDK defaults to all active body joint groups. |
| `joint_names` | std::vector< std::string > | Explicit joint names. When non-empty, this takes precedence over joint_groups and is validated as active joints only. |


---

### TrajectoryControlStatus {#galbot-sdk-trajectorycontrolstatus-enum}

<small>Robot trajectory execution status enumeration.

Represents the real-time execution status when the robot follows a pre-planned trajectory consisting of multiple waypoints.</small>

| Enum Value | Description |
| --- | --- |
| `INVALID_INPUT` | Input parameters do not meet requirements, trajectory cannot be executed |
| `RUNNING` | [Trajectory](#trajectory-struct) is currently executing, not yet completed |
| `COMPLETED` | [Trajectory](#trajectory-struct) execution completed successfully, reached final target point |
| `STOPPED_UNREACHED` | Stopped during trajectory execution without reaching endpoint |
| `ERROR` | [Error](#error-struct) occurred, trajectory execution cannot continue |
| `DATA_FETCH_FAILED` | Execution data retrieval failed, e.g., joint state or sensor feedback unavailable |
| `STATUS_NUM` | Total number of status enumerations (for boundary checking or array sizing) |


---

### TrajectoryFeasibilityCheckOption {#trajectoryfeasibilitycheckoption-struct}

<small>[Trajectory](#trajectory-struct) validation and feasibility checking configuration.

This structure provides fine-grained control over which feasibility constraints are enforced during trajectory validation. It supports independent toggling of collision detection, joint limit compliance, and velocity profile feasibility. Selectively disabling checks can improve computational performance for debugging, simulation, or scenarios where certain constraints are guaranteed to be satisfied. Disabling feasibility checks may produce trajectories that are unsafe or physically unrealizable. Use with caution and only when constraints are verified through other means.</small>

#### set_disable_collision_check {#trajectoryfeasibilitycheckoption-set_disable_collision_check-function}

```cpp
void galbot::sdk::TrajectoryFeasibilityCheckOption::set_disable_collision_check(bool disable)
```

<small>Enable or disable collision detection during trajectory validation.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `disable` | bool | true to skip collision checking, false to enforce collision-free trajectories |

!!! warning
    Disabling collision checks may result in unsafe motion plans

#### set_disable_joint_limit_check {#trajectoryfeasibilitycheckoption-set_disable_joint_limit_check-function}

```cpp
void galbot::sdk::TrajectoryFeasibilityCheckOption::set_disable_joint_limit_check(bool disable)
```

<small>Enable or disable joint limit compliance checking.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `disable` | bool | true to skip joint limit validation, false to enforce position limits |

!!! warning
    Disabling joint limit checks may damage hardware or violate safety constraints

#### set_disable_velocity_feasibility_check {#trajectoryfeasibilitycheckoption-set_disable_velocity_feasibility_check-function}

```cpp
void galbot::sdk::TrajectoryFeasibilityCheckOption::set_disable_velocity_feasibility_check(bool disable)
```

<small>Enable or disable velocity profile feasibility checking.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `disable` | bool | true to skip velocity limit validation, false to enforce velocity constraints |

!!! note
    Velocity feasibility ensures the trajectory can be executed within actuator speed limits

#### get_disable_collision_check {#trajectoryfeasibilitycheckoption-get_disable_collision_check-function}

```cpp
bool galbot::sdk::TrajectoryFeasibilityCheckOption::get_disable_collision_check() const
```

<small>Check if collision detection is disabled.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | true if collision checking is currently disabled, false if enabled |

#### get_disable_joint_limit_check {#trajectoryfeasibilitycheckoption-get_disable_joint_limit_check-function}

```cpp
bool galbot::sdk::TrajectoryFeasibilityCheckOption::get_disable_joint_limit_check() const
```

<small>Check if joint limit checking is disabled.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | true if joint limit validation is currently disabled, false if enabled |

#### get_disable_velocity_feasibility_check {#trajectoryfeasibilitycheckoption-get_disable_velocity_feasibility_check-function}

```cpp
bool galbot::sdk::TrajectoryFeasibilityCheckOption::get_disable_velocity_feasibility_check() const
```

<small>Check if velocity feasibility checking is disabled.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | true if velocity validation is currently disabled, false if enabled |

#### print {#trajectoryfeasibilitycheckoption-print-function}

```cpp
void galbot::sdk::TrajectoryFeasibilityCheckOption::print() const
```

<small>Print trajectory feasibility check configuration to standard output.

Outputs enabled/disabled status for each feasibility check type.</small>


---

### TrajectoryPlanConfig {#trajectoryplanconfig-struct}

<small>[Trajectory](#trajectory-struct) planning and parameterization configuration.

This structure configures trajectory generation parameters for converting discrete motion plans into smooth, time-parameterized trajectories. It supports both single-segment and multi-waypoint trajectory planning. [Trajectory](#trajectory-struct) planning involves computing velocity and acceleration profiles along a geometric path while respecting kinematic constraints.</small>

#### set_min_move_time {#trajectoryplanconfig-set_min_move_time-function}

```cpp
void galbot::sdk::TrajectoryPlanConfig::set_min_move_time(double time)
```

<small>Set minimum duration for any motion segment.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `time` | double | Minimum trajectory execution time (units: s) |

!!! note
    Non-zero values prevent excessively fast motions; 0.0 allows maximum speed within kinematic limits

#### set_move_line_intermediate_point {#trajectoryplanconfig-set_move_line_intermediate_point-function}

```cpp
void galbot::sdk::TrajectoryPlanConfig::set_move_line_intermediate_point(double value)
```

<small>Set waypoint density for Cartesian linear motion interpolation.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | double | Number of intermediate waypoints for linear path segments (dimensionless) |

!!! note
    Higher values improve Cartesian path accuracy but increase computational cost

#### set_way_point_plan_expected_time {#trajectoryplanconfig-set_way_point_plan_expected_time-function}

```cpp
void galbot::sdk::TrajectoryPlanConfig::set_way_point_plan_expected_time(double time)
```

<small>Set expected total duration for multi-waypoint trajectory planning.</small>

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `time` | double | Expected trajectory execution time for waypoint sequences (units: s) |

!!! note
    Used as a hint for time-optimal trajectory generation algorithms

#### get_min_move_time {#trajectoryplanconfig-get_min_move_time-function}

```cpp
double galbot::sdk::TrajectoryPlanConfig::get_min_move_time() const
```

<small>Get minimum motion segment duration.</small>

**Returns**

| Type | Description |
| --- | --- |
| double | Minimum movement time (units: s) |

#### get_move_line_intermediate_point {#trajectoryplanconfig-get_move_line_intermediate_point-function}

```cpp
double galbot::sdk::TrajectoryPlanConfig::get_move_line_intermediate_point() const
```

<small>Get waypoint density for linear motion interpolation.</small>

**Returns**

| Type | Description |
| --- | --- |
| double | Number of intermediate waypoints (dimensionless) |

#### get_way_point_plan_expected_time {#trajectoryplanconfig-get_way_point_plan_expected_time-function}

```cpp
double galbot::sdk::TrajectoryPlanConfig::get_way_point_plan_expected_time() const
```

<small>Get expected multi-waypoint trajectory duration.</small>

**Returns**

| Type | Description |
| --- | --- |
| double | Expected planning time (units: s) |

#### print {#trajectoryplanconfig-print-function}

```cpp
void galbot::sdk::TrajectoryPlanConfig::print() const
```

<small>Print trajectory planning configuration to standard output.

Outputs all configuration parameters for debugging and verification.</small>


---

### TrajectoryPoint {#trajectorypoint-struct}

<small>Represents a waypoint in a robot trajectory, specifying joint states at a particular time.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `time_from_start_second` | double | Time from trajectory start (seconds) |
| `joint_command_vec` | std::vector< [JointCommand](#jointcommand-struct) > | List of joint commands for all joints at this waypoint |


---

### TransformMessage {#transformmessage-struct}

<small>Represents a timestamped coordinate frame transformation, consisting of translation and rotation. Commonly used for TF (Transform) trees in robotics.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `timestamp_ns` | int64_t | Transform timestamp (nanoseconds since epoch) |
| `translation` | [Point](#point-struct) | Translation vector (meters) |
| `rotation` | [Quaternion](#quaternion-struct) | Rotation as unit quaternion (x, y, z, w) |


---

### Twist {#twist-struct}

<small>6D twist command (linear + angular velocity).</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `linear` | [Vector3](#vector3-struct) |  |
| `angular` | [Vector3](#vector3-struct) |  |


---

### UltrasonicData {#ultrasonicdata-struct}

<small>Contains a single ultrasonic distance measurement with timestamp.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `timestamp_ns` | int64_t | Measurement timestamp in nanoseconds since epoch |
| `distance` | double | Measured distance to nearest obstacle (meters) |


---

### UltrasonicType {#galbot-sdk-ultrasonictype-enum}

<small>Chassis ultrasonic sensor probe enumeration (8 directions)

Identifies individual ultrasonic sensors arranged around the mobile base chassis for omnidirectional obstacle detection and proximity sensing.</small>

| Enum Value | Description |
| --- | --- |
| `FRONT_LEFT` | Front left ultrasonic sensor |
| `FRONT_RIGHT` | Front right ultrasonic sensor |
| `RIGHT_LEFT` | Right side front ultrasonic sensor |
| `RIGHT_RIGHT` | Right side rear ultrasonic sensor |
| `BACK_LEFT` | Back left ultrasonic sensor |
| `BACK_RIGHT` | Back right ultrasonic sensor |
| `LEFT_LEFT` | Left side front ultrasonic sensor |
| `LEFT_RIGHT` | Left side rear ultrasonic sensor |
| `ULTRASONIC_NUM` | Total number of ultrasonic sensors (for boundary checking or array sizing) |


---

### Vector3 {#vector3-struct}

<small>Represents a three-dimensional vector, used for forces, torques, velocities, accelerations, and other vectorial quantities.</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `x` | double | X component |
| `y` | double | Y component |
| `z` | double | Z component |


---

### Wrench {#wrench-struct}

<small>6D wrench command (force + torque).</small>

**Member Variables**

| Name | Type | Description |
| --- | --- | --- |
| `force` | [Vector3](#vector3-struct) |  |
| `torque` | [Vector3](#vector3-struct) |  |


---

