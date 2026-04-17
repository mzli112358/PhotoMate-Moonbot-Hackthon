# Python API Reference - G1 Machine

- **[GalbotRobot](#module-galbotrobot)**: Core robot control module. Use this for robot connection, lifecycle management, joint control, sensor data queries, and hardware state monitoring.
- **[GalbotMotion](#module-galbotmotion)**: Motion planning and execution module. Use this for Cartesian/joint space movements, trajectory planning, inverse kinematics, and whole-body control.
- **[GalbotNavigation](#module-galbotnavigation)**: Mobile navigation module. Use this for mobile base localization, mapping, path planning, and autonomous movement.
- **[GalbotPerception](#module-galbotperception)**: On-device perception (G1 only). Load vision models, run inference, and read structured results such as stereo depth; use together with GalbotRobot sensor APIs.
- **[Types & Enums](#module-types-enums)**: Data structures, enums, and status types. Use this section to look up type definitions, sensor types, error codes, and state structures used by other modules.

---

<a id="module-galbotrobot"></a>

## GalbotRobot {#galbotrobot-class}

<small>Main robot control interface for Galbot humanoid robot.

This class provides a singleton interface for controlling the Galbot robot. It supports: Joint position and trajectory control End-effector control (grippers and suction cups) Mobile base velocity control Sensor data acquisition (IMU, cameras, LiDAR, ultrasonic) Coordinate frame transformations System lifecycle management Use GalbotRobot::get_instance(MachineType) to obtain a reference for a specific platform (G1/S1). All angles are in radians unless otherwise specified. All linear distances are in meters unless otherwise specified. All timestamps are in nanoseconds unless otherwise specified.</small>

### get_instance {#galbotrobot-get_instance-function}

```python
@staticmethod
def get_instance(machine_type: MachineType) -> GalbotRobot
```

<small>Runtime factory for selecting a concrete robot singleton.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `machine_type` | [MachineType](#machinetype-enum) | required | - |

**Returns**

| Type | Description |
| --- | --- |
| [GalbotRobot](#galbotrobot-class) | - |

### acquire_controller {#galbotrobot-acquire_controller-function}

```python
def acquire_controller(controller_name: str) -> ControlStatus
```

<small>Acquire hardware authority.

Designates the controller to take ownership of the hardware. Opposite of release_controller. Controller must still be started to begin execution.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `controller_name` | str | required | Controller name, for example "LEFT_ARM_PVT_CTRL". |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#controlstatus-enum) | ControlStatus: Result of the operation. |

### check_trajectory_execution_status {#galbotrobot-check_trajectory_execution_status-function}

```python
def check_trajectory_execution_status(
    joint_groups: Sequence[str] = []
) -> list[TrajectoryControlStatus]
```

<small>Get trajectory execution status for specified joint groups.

Queries the current execution status of trajectories for the specified joint groups. This is useful for monitoring trajectory progress in non-blocking execution mode.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `joint_groups` | Sequence[str] | `[]` | Joint groups to query (optional). |

**Returns**

| Type | Description |
| --- | --- |
| list[[TrajectoryControlStatus](#trajectorycontrolstatus-enum)] | List[TrajectoryControlStatus]: List of trajectory execution statuses. |

### destroy {#galbotrobot-destroy-function}

```python
def destroy() -> None
```

<small>Clean up system resources.

Performs cleanup of robot control system resources including middleware connections, sensor interfaces, and communication channels. Should be called before program exit to ensure graceful shutdown.</small>

!!! note
    This function should be called after request_shutdown() or when is_running() returns false

### execute_joint_trajectory {#galbotrobot-execute_joint_trajectory-function}

```python
def execute_joint_trajectory(trajectory: Trajectory, is_blocking: bool = True) -> ControlStatus
```

<small>Execute a pre-planned joint trajectory.

Executes a trajectory consisting of waypoints with associated joint positions, velocities, and timing information. The trajectory controller interpolates between waypoints to generate smooth motion.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `trajectory` | [Trajectory](#trajectory-class) | required | Trajectory data to execute. |
| `is_blocking` | bool | `True` | Whether to block until trajectory execution completes (optional, default: True). |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#controlstatus-enum) | ControlStatus: Trajectory execution/sending result. |

!!! warning
    For per-frame model inference output, prefer command streaming interfaces (set_joint_commands / set_joint_commands_batch) rather than repeatedly re-submitting full trajectories.

### get_active_controller {#galbotrobot-get_active_controller-function}

```python
def get_active_controller(group_name: str) -> str
```

<small>Get active controller name for specified joint group.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `group_name` | str | required | The joint group name to query. |

**Returns**

| Type | Description |
| --- | --- |
| str | str: Active controller name for the group. |

### get_bms_information {#galbotrobot-get_bms_information-function}

```python
def get_bms_information() -> dict
```

<small>Get BMS (Battery Management System) information.</small>

**Returns**

| Type | Description |
| --- | --- |
| dict | dict: Dictionary containing the following keys:<br>- 'voltage': Battery voltage in V<br>- 'current': Battery current in A<br>- 'battery_level': Battery level in %<br>- 'temperature': Battery temperature in C<br>- 'charging_status': Charging status (bool)<br>- 'health_status': Health status (bool)<br>- 'capacity': Remaining capacity in Ah<br>Returns empty dictionary on failure. |

### get_camera_intrinsic {#galbotrobot-get_camera_intrinsic-function}

```python
def get_camera_intrinsic(camera_id: SensorType) -> dict
```

<small>Get camera intrinsic parameters.

Retrieves the intrinsic parameters of the specified camera, including focal lengths, principal points, and distortion coefficients, etc.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `camera_id` | [SensorType](#sensortype-enum) | required | Camera sensor ID to query. |

**Returns**

| Type | Description |
| --- | --- |
| dict | dict: Dictionary containing camera intrinsic parameters.<br>- header: Message header with timestamp and frame information<br>- height: Image height in pixels<br>- width: Image width in pixels<br>- distortion_model: Distortion model, e.g., 'plumb_bob'<br>- D: Distortion coefficients (list of float)<br>- K: Camera intrinsic matrix (list of 9 float)<br>- binning_x: Horizontal binning factor<br>- binning_y: Vertical binning factor<br>- roi: Region of interest (list of int)<br>- camera_type: camera type<br>Returns empty dictionary on failure. |

!!! note
    The camera sensor must be enabled during initialization via enable_sensor_set

### get_depth_data {#galbotrobot-get_depth_data-function}

```python
def get_depth_data(camera_id: SensorType) -> dict
```

<small>Get latest depth image from specified camera.

Retrieves the most recent depth image captured by the specified depth camera. Depth values typically represent distance from the camera sensor.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `camera_id` | [SensorType](#sensortype-enum) | required | Depth camera sensor ID to query. |

**Returns**

| Type | Description |
| --- | --- |
| dict | dict: Dictionary containing the following keys:<br>- 'header': Message header with timestamp and frame information<br>- 'format': Image format, e.g., 'depth16' or other<br>- 'depth_scale': Depth scaling factor<br>- 'height': Image height in pixels<br>- 'width': Image width in pixels<br>- 'data': Compressed depth image binary data (bytes).<br>Returns empty dictionary on failure. |

!!! note
    The camera sensor must be enabled during initialization via enable_sensor_set

!!! note
    Depth values are typically in millimeters (mm) or meters (m) depending on sensor

### get_device_information {#galbotrobot-get_device_information-function}

```python
def get_device_information() -> dict
```

<small>Get device information.

Retrieves basic device information including device model, serial number, firmware version, hardware version, and manufacturer. This information is used for device management, version control, system diagnostics, and device identification.</small>

**Returns**

| Type | Description |
| --- | --- |
| dict | dict: Dictionary containing the following keys:<br>- 'model': Device model name or identifier (str)<br>- 'serial_number': Unique serial number for device identification (str)<br>- 'firmware_version': System firmware version string (str)<br>- 'hardware_version': Hardware version or revision number (str)<br>- 'manufacturer': Manufacturer name or company identifier (str)<br>Returns empty dictionary on failure. |

### get_dexterous_hand_state {#galbotrobot-get_dexterous_hand_state-function}

```python
def get_dexterous_hand_state(end_effector: str) -> tuple
```

<small>Get current dexterous hand (dexhand) state.

Retrieves the current joint state of the specified dexterous hand.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `end_effector` | str | required | Dexhand name, e.g. "left_dexhand" or "right_dexhand". |

**Returns**

| Type | Description |
| --- | --- |
| tuple | Tuple[ControlStatus, JointStateMessage]: Query result and current dexhand joint states. |

### get_force_sensor_data {#galbotrobot-get_force_sensor_data-function}

```python
def get_force_sensor_data(sensor_type: GalbotOneFoxtrotSensor) -> dict
```

<small>Get force/torque sensor data.

Retrieves the latest measurements from the specified force/torque sensor. These sensors are typically mounted at wrists or end-effectors for contact force monitoring and compliance control.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `sensor_type` | [GalbotOneFoxtrotSensor](#galbotonefoxtrotsensor-enum) | required | Force sensor enum to query. |

**Returns**

| Type | Description |
| --- | --- |
| dict | dict: Dictionary containing the following keys:<br>- 'timestamp_ns': Timestamp in nanoseconds<br>- 'force': Force vector dictionary with 'x', 'y', 'z' keys<br>- 'torque': Torque vector dictionary with 'x', 'y', 'z' keys<br>Returns empty dictionary on failure. |

!!! note
    The force sensor must be enabled during initialization via enable_sensor_set

### get_frame_names {#galbotrobot-get_frame_names-function}

```python
def get_frame_names() -> list[str]
```

<small>Get all available coordinate frame names in the TF tree.</small>

**Returns**

| Type | Description |
| --- | --- |
| list[str] | list(str): List of all frame names. |

### get_gripper_state {#galbotrobot-get_gripper_state-function}

```python
def get_gripper_state(end_effector: str) -> GripperState
```

<small>Get current gripper state.

Retrieves the current state of the specified gripper, including position, velocity, force, and motion-state estimation.

GripperState::is_moving is window-based: if no effective width change is detected within the internal time window, is_moving becomes false.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `end_effector` | str | required | Gripper name, e.g. "left_gripper" or "right_gripper". |

**Returns**

| Type | Description |
| --- | --- |
| [GripperState](#gripperstate-class) | GripperState: Gripper state information. |

### get_imu_data {#galbotrobot-get_imu_data-function}

```python
def get_imu_data(sensor_id: SensorType) -> dict
```

<small>Get IMU (Inertial Measurement Unit) sensor data.

Retrieves the latest IMU measurements including linear acceleration, angular velocity, and orientation estimation.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `sensor_id` | [SensorType](#sensortype-enum) | required | IMU sensor enum to query. |

**Returns**

| Type | Description |
| --- | --- |
| dict | dict: Dictionary containing the following keys:<br>- 'timestamp_ns': Timestamp in nanoseconds<br>- 'accel': Acceleration Vector3 {'x': float, 'y': float, 'z': float}<br>- 'gyro': Gyroscope Vector3 {'x': float, 'y': float, 'z': float}<br>- 'magnet': Magnetometer Vector3 {'x': float, 'y': float, 'z': float}<br>Returns empty dictionary on failure. |

!!! note
    The IMU sensor must be enabled during initialization via enable_sensor_set

!!! note
    Acceleration is in meters per second squared (m/s²)

!!! note
    Angular velocity is in radians per second (rad/s)

### get_joint_group_names {#galbotrobot-get_joint_group_names-function}

```python
def get_joint_group_names() -> list[str]
```

<small>Get available joint group names for the robot.

Retrieves all joint group names defined in the robot's kinematic configuration. This is useful for discovering available control groups at runtime.</small>

**Returns**

| Type | Description |
| --- | --- |
| list[str] | List[str]: Array of available joint group names, returns empty list on failure. |

### get_joint_names {#galbotrobot-get_joint_names-function}

```python
def get_joint_names(only_active_joint: bool = True, joint_groups: Sequence[str] = []) -> list[str]
```

<small>Get robot joint names by group name.

Retrieves the names of joints belonging to specified joint groups. This is useful for determining the correct ordering when setting joint positions.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `only_active_joint` | bool | `True` | Whether to only get active joints (optional, default: True). |
| `joint_groups` | Sequence[str] | `[]` | Joint groups (optional). |

**Returns**

| Type | Description |
| --- | --- |
| list[str] | List[str]: Array of corresponding joint names. |

### get_joint_positions {#galbotrobot-get_joint_positions-function}

```python
def get_joint_positions(joint_groups: Sequence[str], joint_names: Sequence[str] = []) -> list[float]
```

<small>Get current joint positions by group name.

Retrieves the current angular positions of joints in the specified groups. The returned vector order matches the joint ordering from get_joint_names().</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `joint_groups` | Sequence[str] | required | Joint groups to query. |
| `joint_names` | Sequence[str] | `[]` | Specific joint names, takes priority over joint_groups (optional). |

**Returns**

| Type | Description |
| --- | --- |
| list[float] | List[float]: Array of corresponding joint angles in radians. |

### get_joint_states {#galbotrobot-get_joint_states-function}

```python
def get_joint_states(
    joint_group_vec: Sequence[str],
    joint_names_vec: Sequence[str] = []
) -> list[JointState]
```

<small>Get real-time joint states by group name.

Retrieves comprehensive state information for specified joints, including position, velocity, acceleration, effort (torque), and other feedback data.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `joint_group_vec` | Sequence[str] | required | Joint groups to query (optional). |
| `joint_names_vec` | Sequence[str] | `[]` | Specific joint names, takes priority over joint_group_vec (optional). |

**Returns**

| Type | Description |
| --- | --- |
| list[[JointState](#jointstate-class)] | List[JointState]: Real-time state data for corresponding joints. |

### get_lidar_data {#galbotrobot-get_lidar_data-function}

```python
def get_lidar_data(sensor_id: SensorType) -> dict
```

<small>Get latest LiDAR point cloud data.

Retrieves the most recent 3D point cloud captured by the specified LiDAR sensor. Each point typically contains (x, y, z) coordinates and optional intensity values.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `sensor_id` | [SensorType](#sensortype-enum) | required | LiDAR sensor enum to query. |

**Returns**

| Type | Description |
| --- | --- |
| dict | dict: Dictionary containing point cloud data fields and binary point data.<br>Returns empty dictionary on failure. |

!!! note
    The LiDAR sensor must be enabled during initialization via enable_sensor_set

### get_log_information {#galbotrobot-get_log_information-function}

```python
def get_log_information(timewindow_s: SupportsInt, log_level: LogLevel) -> dict
```

<small>Get log information.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `timewindow_s` | SupportsInt | required | Time window in seconds. |
| `log_level` | [LogLevel](#loglevel-enum) | required | Log level. |

**Returns**

| Type | Description |
| --- | --- |
| dict | dict: Dictionary containing the following keys:<br>- 'level': Log level<br>- 'message': Log message<br>Returns empty dictionary on failure. |

### get_odom {#galbotrobot-get_odom-function}

```python
def get_odom() -> dict
```

<small>Get robot odometry information.

Retrieves the robot's current pose and velocity estimates from the odometry system. Odometry typically fuses wheel encoders, IMU, and other proprioceptive sensors.</small>

**Returns**

| Type | Description |
| --- | --- |
| dict | dict: Dictionary containing the following keys:<br>- 'timestamp_ns': Timestamp in nanoseconds<br>- 'position': Position array [x, y, z] in meters<br>- 'orientation': Quaternion array [x, y, z, w]<br>Returns empty dictionary on failure. |

### get_rgb_data {#galbotrobot-get_rgb_data-function}

```python
def get_rgb_data(camera_id: SensorType) -> dict
```

<small>Get latest RGB image from specified camera.

Retrieves the most recent color image captured by the specified RGB camera.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `camera_id` | [SensorType](#sensortype-enum) | required | Camera sensor ID to query. |

**Returns**

| Type | Description |
| --- | --- |
| dict | dict: Dictionary containing the following keys:<br>- 'header': Message header with timestamp and frame information<br>- 'format': Image format, e.g., 'jpeg' or 'png'<br>- 'data': Compressed image binary data (bytes)<br>Returns empty dictionary on failure. |

!!! note
    The camera sensor must be enabled during initialization via enable_sensor_set

### get_sensor_extrinsic {#galbotrobot-get_sensor_extrinsic-function}

```python
def get_sensor_extrinsic(sensor_id: SensorType, reference_frame: str = 'base_link') -> tuple
```

<small>Get sensor extrinsic parameters.

Retrieves the extrinsic parameters of the specified sensor, including rotation and translation vectors relative to the robot's base frame.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `sensor_id` | [SensorType](#sensortype-enum) | required | Sensor enum to query. |
| `reference_frame` | str | `'base_link'` | Name of the reference coordinate frame (frame to transform from). Default is "base_link". |

**Returns**

| Type | Description |
| --- | --- |
| tuple | tuple(List[float], int): Transform [x, y, z, qx, qy, qz, qw] and timestamp. Returns empty list on failure. |

!!! note
    The sensor must be enabled during initialization via enable_sensor_set

### get_suction_cup_state {#galbotrobot-get_suction_cup_state-function}

```python
def get_suction_cup_state(end_effector: str) -> SuctionCupState
```

<small>Get current suction cup state.

Retrieves the current state of the specified suction cup, including activation status and vacuum pressure measurements.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `end_effector` | str | required | Suction cup name, e.g. "left_suction_cup" or "right_suction_cup". |

**Returns**

| Type | Description |
| --- | --- |
| [SuctionCupState](#suctioncupstate-class) | SuctionCupState: Suction cup state information. |

### get_transform {#galbotrobot-get_transform-function}

```python
def get_transform(
    target_frame: str,
    source_frame: str,
    timestamp_ns: SupportsInt = 0,
    timeout_ms: SupportsInt = 100
) -> tuple
```

<small>Query coordinate frame transformation (TF)

Queries the transformation between two coordinate frames in the robot's TF tree. This is used for converting poses and positions between different reference frames (e.g., from camera frame to base frame, from end-effector to world frame).</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `target_frame` | str | required | Target coordinate frame (e.g., map, base_link, imu_base_link; actual list is from get_frame_names()). |
| `source_frame` | str | required | Source coordinate frame (e.g., map, base_link, imu_base_link; actual list is from get_frame_names()). |
| `timestamp_ns` | SupportsInt | `0` | Desired transform timestamp in nanoseconds, 0 for latest (optional, default: 0). |
| `timeout_ms` | SupportsInt | `100` | Query timeout in milliseconds (optional, default: 100). |

**Returns**

| Type | Description |
| --- | --- |
| tuple | tuple(List[float], int): Transform matrix list and timestamp. Returns empty list on failure. |

### get_ultrasonic_data {#galbotrobot-get_ultrasonic_data-function}

```python
def get_ultrasonic_data(ultrasonic_type: UltrasonicType) -> dict
```

<small>Get distance measurement from specified ultrasonic sensor.

Retrieves the latest distance measurement from one of the ultrasonic range sensors. The robot typically has multiple ultrasonic sensors arranged around its perimeter.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `ultrasonic_type` | [UltrasonicType](#ultrasonictype-enum) | required | Ultrasonic sensor enum to query. |

**Returns**

| Type | Description |
| --- | --- |
| dict | dict: Dictionary containing the following keys:<br>- 'timestamp_ns': Timestamp in nanoseconds<br>- 'distance': Distance value in meters<br>Returns empty dictionary on failure. |

!!! note
    The ultrasonic sensor must be enabled during initialization via enable_sensor_set

### get_volume {#galbotrobot-get_volume-function}

```python
def get_volume() -> float
```

<small>Get current system global volume value.</small>

**Returns**

| Type | Description |
| --- | --- |
| float | float: Current volume value, range 0.0 to 100.0. |

### init {#galbotrobot-init-function}

```python
def init(enable_sensor_set: Set[SensorType] = ...) -> bool
```

<small>Initialize the robot control system.

Initializes the robot hardware communication, middleware, and sensor interfaces. To optimize resource usage, only sensors specified in the enable_sensor_set will be initialized and available for data reading.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `enable_sensor_set` | Set[[SensorType](#sensortype-enum)] | `...` | Set of sensors to enable. Empty set uses default sensors. |

**Returns**

| Type | Description |
| --- | --- |
| bool | bool: True if initialization succeeded; False otherwise. |

### is_running {#galbotrobot-is_running-function}

```python
def is_running() -> bool
```

<small>Check if the robot control system is running.

Queries whether the robot control system is still active or if a shutdown signal (e.g., SIGINT, SIGTERM) has been received.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | bool: True if system is running, False if shutdown signal captured and preparing to shutdown. |

### publish_target {#galbotrobot-publish_target-function}

```python
def publish_target(target: SingoriXTarget) -> ControlStatus
```

<small>Publish a raw SingoriXTarget through the WBC publish channel. This is the advanced high-frequency path. Construct a SingoriXTarget directly, then call this interface to send it to the low-level controller without waiting for a service response. The SDK performs only basic structural validation.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `target` | [SingoriXTarget](#singorixtarget-class) | required | SDK mirror target containing group-space and/or task-space trajectories. |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#controlstatus-enum) | ControlStatus: Local validation / publish result. |

### release_controller {#galbotrobot-release_controller-function}

```python
def release_controller(group_name: str = 'all') -> ControlStatus
```

<small>Release hardware authority.

Yields control of the hardware, freeing the joints. Opposite of acquire_controller. Implicitly stops execution if running.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `group_name` | str | `'all'` | Name of the joint group (default: "all"). |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#controlstatus-enum) | ControlStatus: Result of the operation. |

### reload_controller {#galbotrobot-reload_controller-function}

```python
def reload_controller(group_name: str = 'all') -> ControlStatus
```

<small>Reload a controller.

Reinitializes the controller. Equivalent to a full restart cycle: stop -> reset -> start. Useful for error recovery or applying configuration changes.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `group_name` | str | `'all'` | Name of the joint group (default: "all"). |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#controlstatus-enum) | ControlStatus: Result of the operation. |

### request_shutdown {#galbotrobot-request_shutdown-function}

```python
def request_shutdown() -> None
```

<small>Request system shutdown.

Programmatically sends a shutdown signal (SIGINT) to initiate graceful system shutdown. This triggers registered exit callbacks and begins resource cleanup.</small>

### request_target {#galbotrobot-request_target-function}

```python
def request_target(target: SingoriXTarget) -> ErrorInfo
```

<small>Request execution of a raw SingoriXTarget through the WBC service channel. This is the advanced request path. The SDK performs request-side runtime error screening, sends the target through the middleware client, and returns the ErrorInfo service payload. A return value of None means the client was unavailable, disconnected, timed out, or returned an empty response.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `target` | [SingoriXTarget](#singorixtarget-class) | required | SDK mirror target containing group-space and/or task-space trajectories. |

**Returns**

| Type | Description |
| --- | --- |
| [ErrorInfo](#errorinfo-class) | ErrorInfo \| None: Error response payload or None when no valid response was received. |

### set_base_pose {#galbotrobot-set_base_pose-function}

```python
def set_base_pose(
    base_pose: Pose,
    is_blocking: bool = True,
    timeout_s: SupportsFloat = 15.0
) -> ControlStatus
```

<small>Set mobile base pose (x, y, yaw) with explicit interpolation time.

Use this overload when arrival timing must be coordinated through time_from_start_s.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `base_pose` | [Pose](#pose-class) | required | Target base pose. |
| `is_blocking` | bool | `True` | Whether to block until command execution completes (optional, default: True). |
| `timeout_s` | SupportsFloat | `15.0` | Blocking timeout in seconds (optional, default: 15.0). |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#controlstatus-enum) | ControlStatus: Command sending result. |

### set_base_pose {#galbotrobot-set_base_pose-function}

```python
def set_base_pose(
    x: SupportsFloat,
    y: SupportsFloat,
    yaw: SupportsFloat,
    frame_id: str = 'odom',
    reference_frame_id: str = 'odom',
    is_blocking: bool = True,
    timeout_s: SupportsFloat = 15.0
) -> ControlStatus
```

<small>Set mobile base pose (x, y, yaw) with explicit interpolation time.

Use this overload when arrival timing must be coordinated through time_from_start_s.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `x` | SupportsFloat | required | Target x position. |
| `y` | SupportsFloat | required | Target y position. |
| `yaw` | SupportsFloat | required | Target yaw (rad). |
| `frame_id` | str | `'odom'` | Frame id ("base_link"/"odom"/"map"). Default "odom". |
| `reference_frame_id` | str | `'odom'` | Reference frame id ("odom"/"map"). Default "odom". |
| `is_blocking` | bool | `True` | Whether to block until command execution completes (optional, default: True). |
| `timeout_s` | SupportsFloat | `15.0` | Blocking timeout in seconds (optional, default: 15.0). |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#controlstatus-enum) | ControlStatus: Command sending result. |

### set_base_pose {#galbotrobot-set_base_pose-function}

```python
def set_base_pose(
    x: SupportsFloat,
    y: SupportsFloat,
    yaw: SupportsFloat,
    frame_id: str,
    reference_frame_id: str,
    time_from_start_s: SupportsFloat,
    is_blocking: bool = True,
    timeout_s: SupportsFloat = 15.0
) -> ControlStatus
```

<small>Set mobile base pose (x, y, yaw) with explicit interpolation time.

Use this overload when arrival timing must be coordinated through time_from_start_s.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `x` | SupportsFloat | required | Target x position (meters). |
| `y` | SupportsFloat | required | Target y position (meters). |
| `yaw` | SupportsFloat | required | Target yaw (radians). |
| `frame_id` | str | required | Frame id of target ("base_link"/"odom"/"map"). |
| `reference_frame_id` | str | required | Reference frame id ("odom"/"map"). |
| `time_from_start_s` | SupportsFloat | required | Chassis pose interpolation time (seconds). |
| `is_blocking` | bool | `True` | Whether to block until command execution completes (optional, default: True). |
| `timeout_s` | SupportsFloat | `15.0` | Request timeout in seconds (optional, default: 15.0). |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#controlstatus-enum) | ControlStatus: Command sending result. |

### set_base_velocity {#galbotrobot-set_base_velocity-function}

```python
def set_base_velocity(
    linear_velocity: list[float],
    angular_velocity: list[float],
    duration_s: SupportsFloat = 0.0
) -> ControlStatus
```

<small>Set mobile base velocity command.

Commands the robot's mobile base to move with specified linear and angular velocities. Velocities are expressed in the robot's base frame coordinate system.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `linear_velocity` | list[float] | required | Linear velocity command [vx, vy, vz] in m/s. |
| `angular_velocity` | list[float] | required | Angular velocity command [wx, wy, wz] in rad/s. |
| `duration_s` | SupportsFloat | `0.0` | Duration in seconds before auto-stop (optional, default: 0.0). If <= 0.0, no automatic stop is performed. |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#controlstatus-enum) | ControlStatus: Command sending result. |

### set_dexhand_command {#galbotrobot-set_dexhand_command-function}

```python
def set_dexhand_command(
    end_effector: str,
    dexhand_command: Sequence[JointCommand],
    is_blocking: bool = True
) -> ControlStatus
```

<small>Control dexhand with joint commands.

Commands the dexhand with a vector of joint commands (position, velocity, effort, etc.).</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `end_effector` | str | required | Dexhand name, e.g. "left_dexhand" or "right_dexhand". |
| `dexhand_command` | Sequence[[JointCommand](#jointcommand-class)] | required | Joint commands for the dexhand. |
| `is_blocking` | bool | `True` | Whether to block until action completes (optional, default: True). |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#controlstatus-enum) | ControlStatus: Command execution/sending result. |

### set_gripper_command {#galbotrobot-set_gripper_command-function}

```python
def set_gripper_command(
    end_effector: str,
    width_m: SupportsFloat,
    velocity_mps: SupportsFloat = 0.03,
    effort: SupportsFloat = 30,
    is_blocking: bool = True
) -> ControlStatus
```

<small>Control gripper opening width and force.

Commands the gripper to move to a specified opening width with controlled velocity and maximum gripping force.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `end_effector` | str | required | Gripper name, e.g. "left_gripper" or "right_gripper". |
| `width_m` | SupportsFloat | required | Target gripper width in meters. |
| `velocity_mps` | SupportsFloat | `0.03` | Gripper motion speed in m/s (optional, default: 0.03). |
| `effort` | SupportsFloat | `30` | Gripper effort in Nm (optional, default: 30). |
| `is_blocking` | bool | `True` | Whether to block until action completes (optional, default: True). |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#controlstatus-enum) | ControlStatus: Command execution/sending result. |

### set_joint_commands {#galbotrobot-set_joint_commands-function}

```python
def set_joint_commands(
    joint_commands: Sequence[JointCommand],
    joint_groups: Sequence[str] = [],
    joint_names: Sequence[str] = [],
    time_from_start_s: SupportsFloat = 10.0
) -> ControlStatus
```

<small>Set low-level joint commands for high-frequency streaming control.

Suitable for high-frequency command streaming (for example, per-frame model inference output).

This API does not interpolate from the current/start position to the first target. The controller drives joints toward each commanded target as quickly as possible to satisfy time_from_start_s (expected arrival time).

For standard joints (head, legs, arms), only JointCommand::position is effective in current versions; velocity, acceleration, and effort are currently ignored.

For gripper joints, the position field represents gripper width and both velocity and effort fields are supported and effective. Gripper motion uses whichever is slower between the specified velocity and time_from_start_s. Therefore, when setting the gripper velocity, time_from_start_s can be set to 0 (fastest arrival), and the gripper will be controlled directly by the specified velocity.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `joint_commands` | Sequence[[JointCommand](#jointcommand-class)] | required | List of joint commands to control. |
| `joint_groups` | Sequence[str] | `[]` | Joint groups to control (optional). |
| `joint_names` | Sequence[str] | `[]` | Specific joint names, takes priority over joint_groups (optional). |
| `time_from_start_s` | SupportsFloat | `10.0` | Time in seconds from the start of the motion to execute the command (optional, default: 10.0). |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#controlstatus-enum) | ControlStatus: Result of command execution. |

!!! warning
    Especially on the first command, avoid a large gap between current and target joint angles. Large jumps may cause excessively fast motion and safety risk.

### set_joint_commands_batch {#galbotrobot-set_joint_commands_batch-function}

```python
def set_joint_commands_batch(trajectory: Trajectory) -> ControlStatus
```

<small>Set joint commands in batch mode (non-blocking)

Sets multiple joint command trajectory points in real-time control mode, supporting one-time submission of trajectory control commands for multiple time points. Provides a non-blocking high-frequency trajectory execution interface. Similar to set_joint_commands but supports batch trajectory control, suitable for scenarios such as VLA inference batch output.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `trajectory` | [Trajectory](#trajectory-class) | required | Trajectory data structure containing waypoints with joint commands. Each TrajectoryPoint contains time_from_start and a list of JointCommand. JointCommand includes position (rad), velocity (rad/s), acceleration (rad/s²), effort (N·m), Kp (position gain), and Kd (velocity gain). |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#controlstatus-enum) | ControlStatus: Command submission result. Returns immediately without waiting for execution completion (non-blocking). |

### set_joint_positions {#galbotrobot-set_joint_positions-function}

```python
def set_joint_positions(
    joint_positions: list[float],
    joint_groups: Sequence[str] = [],
    joint_names: Sequence[str] = [],
    is_blocking: bool = True,
    speed_rad_s: SupportsFloat = 0.2,
    timeout_s: SupportsFloat = 15.0
) -> ControlStatus
```

<small>Set target joint positions for specified joint groups by name (for low-frequency keyframe/posture transitions)

Commands the robot to move specified joints to target positions. The motion is executed as a smooth trajectory with configurable speed limits.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `joint_positions` | list[float] | required | Array of joint angles in radians. |
| `joint_groups` | Sequence[str] | `[]` | Joint groups to control (optional). |
| `joint_names` | Sequence[str] | `[]` | Specific joint names, takes priority over joint_groups (optional). |
| `is_blocking` | bool | `True` | Whether to block until command execution completes (optional, default: True). |
| `speed_rad_s` | SupportsFloat | `0.2` | Maximum joint speed in rad/s (optional, default: 0.2). |
| `timeout_s` | SupportsFloat | `15.0` | Maximum blocking wait time in seconds (optional, default: 15.0). |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#controlstatus-enum) | ControlStatus: Execution result status. |

!!! warning
    This API is not suitable for high-frequency frame-by-frame model inference control. Each call creates a new interpolation goal, and continuous calls can cause lag or discontinuous motion. If your task is model-inference command streaming, use set_joint_commands or set_joint_commands_batch instead.

### set_suction_cup_command {#galbotrobot-set_suction_cup_command-function}

```python
def set_suction_cup_command(end_effector: str, activate: bool) -> ControlStatus
```

<small>Control suction cup activation state.

Activates or deactivates the specified suction cup end-effector.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `end_effector` | str | required | Suction cup name, e.g. "left_suction_cup" or "right_suction_cup". |
| `activate` | bool | required | Whether to activate the suction cup. |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#controlstatus-enum) | ControlStatus: Command sending result. |

### set_volume {#galbotrobot-set_volume-function}

```python
def set_volume(volume: SupportsFloat) -> bool
```

<small>Set system global volume value.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `volume` | SupportsFloat | required | Target volume value, range 0.0 to 100.0. |

**Returns**

| Type | Description |
| --- | --- |
| bool | bool: Returns the volume setting result. True indicates the volume was set successfully, False indicates the volume setting failed. |

### start_controller {#galbotrobot-start_controller-function}

```python
def start_controller(group_name: str = 'all') -> ControlStatus
```

<small>Start controller execution.

Activates the controller to begin sending commands. Opposite of stop_controller. Requires prior hardware authority (acquire).</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `group_name` | str | `'all'` | Name of the joint group (default: "all"). |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#controlstatus-enum) | ControlStatus: Result of the operation. |

### start_microphone_stream_input {#galbotrobot-start_microphone_stream_input-function}

```python
def start_microphone_stream_input(
    callback: Callable,
    chunk_size: SupportsInt = 2560,
    use_raw_audio: bool = False
) -> str
```

<small>Start microphone streaming audio input.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `callback` | Callable | required | Audio data callback function with signature: void(dict audio_data). The audio_data dict contains: - 'header': Message header with timestamp and frame information - 'type': Audio data type ('waken_up', 'denoise_chunk', 'vad_begin', 'vad_chunk', 'vad_end') - 'format': Audio format ('pcm', 'json') - 'data': Audio binary data (bytes) |
| `chunk_size` | SupportsInt | `2560` | Audio data chunk size in bytes, default value 2560. Dynamic configuration not supported yet |
| `use_raw_audio` | bool | `False` | Whether to use raw audio, default false. Dynamic configuration not supported yet. |

**Returns**

| Type | Description |
| --- | --- |
| str | str: Stream ID used to identify the audio input stream. |

### stop_audio_stream_output {#galbotrobot-stop_audio_stream_output-function}

```python
def stop_audio_stream_output(stream_id: str = '') -> None
```

<small>Stop the specified audio output stream or all active audio output streams playback.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `stream_id` | str | `''` | Audio output stream ID to stop. Empty string means stop all active audio output streams (optional, default: ""). |

### stop_base {#galbotrobot-stop_base-function}

```python
def stop_base() -> ControlStatus
```

<small>Emergency stop mobile base movement.

Immediately commands the mobile base to stop all motion. This is a safety function that should be used when immediate cessation of base motion is required.</small>

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#controlstatus-enum) | ControlStatus: Command sending result. |

### stop_controller {#galbotrobot-stop_controller-function}

```python
def stop_controller(group_name: str = 'all') -> ControlStatus
```

<small>Stop controller execution.

Halts command execution but retains hardware authority. Opposite of start_controller.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `group_name` | str | `'all'` | Name of the joint group (default: "all"). |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#controlstatus-enum) | ControlStatus: Result of the operation. |

### stop_microphone_stream_input {#galbotrobot-stop_microphone_stream_input-function}

```python
def stop_microphone_stream_input(stream_id: str = '') -> None
```

<small>Stop the specified microphone streaming audio input.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `stream_id` | str | `''` | Audio input stream ID to stop. Empty string stops all active streams (optional, default: ""). |

### stop_trajectory_execution {#galbotrobot-stop_trajectory_execution-function}

```python
def stop_trajectory_execution() -> ControlStatus
```

<small>Stop all currently executing joint trajectories.

Immediately halts execution of all active joint trajectories across all joint groups. Joints will maintain their current positions after stopping.</small>

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#controlstatus-enum) | ControlStatus: Command sending result. |

### switch_controller {#galbotrobot-switch_controller-function}

```python
def switch_controller(controller_name: str) -> ControlStatus
```

<small>Switch active controller strategy.

Transitions hardware control to a new strategy. Operation sequence: stop(old) -> release(old) -> acquire(new) -> start(new).</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `controller_name` | str | required | Controller name, for example "CHASSIS_POSE_CTRL". |

**Returns**

| Type | Description |
| --- | --- |
| [ControlStatus](#controlstatus-enum) | ControlStatus: Result of the operation. |

### wait_for_shutdown {#galbotrobot-wait_for_shutdown-function}

```python
def wait_for_shutdown() -> None
```

<small>Block until shutdown signal is received.

Blocks the calling thread indefinitely until a shutdown signal (SIGINT, SIGTERM) is received. This is useful for keeping the main thread alive while background threads handle robot control.</small>

!!! note
    This function will return when is_running() becomes false

### write_audio_stream_output {#galbotrobot-write_audio_stream_output-function}

```python
def write_audio_stream_output(audio_chunk: str, stream_id: str = '') -> bool
```

<small>Write PCM format audio data chunk to audio output stream for real-time playback.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `audio_chunk` | str | required | Audio data chunk in PCM format (16000 Hz, 16-bit little-endian), single channel. |
| `stream_id` | str | `''` | Audio stream ID to distinguish different audio sources. Empty string means use default stream (optional, default: ""). |

**Returns**

| Type | Description |
| --- | --- |
| bool | bool: True if audio data has been successfully written and playback task issued, False if write failed. |

### zero_whole_body_and_base {#galbotrobot-zero_whole_body_and_base-function}

```python
def zero_whole_body_and_base(
    base_zero_pose: Pose,
    is_blocking: bool = True,
    leg_head_speed_rad_s: SupportsFloat = 0.2,
    leg_head_timeout_s: SupportsFloat = 15.0,
    params: Parameter = None
) -> tuple[MotionStatus, ControlStatus]
```

<small>One-key zero: move whole-body joints to zero and base (x,y,yaw) to zero with selectable frames.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `base_zero_pose` | [Pose](#pose-class) | required | - |
| `is_blocking` | bool | `True` | - |
| `leg_head_speed_rad_s` | SupportsFloat | `0.2` | - |
| `leg_head_timeout_s` | SupportsFloat | `15.0` | - |
| `params` | [Parameter](#parameter-class) | `None` | - |

**Returns**

| Type | Description |
| --- | --- |
| tuple[[MotionStatus](#motionstatus-enum), [ControlStatus](#controlstatus-enum)] | - |

### zero_whole_body_and_base {#galbotrobot-zero_whole_body_and_base-function}

```python
def zero_whole_body_and_base(
    frame_id: str = 'odom',
    reference_frame_id: str = 'odom',
    is_blocking: bool = True,
    leg_head_speed_rad_s: SupportsFloat = 0.2,
    leg_head_timeout_s: SupportsFloat = 15.0,
    params: Parameter = None
) -> tuple[MotionStatus, ControlStatus]
```

<small>One-key zero: move whole-body joints to zero and base (x,y,yaw) to zero with selectable frames.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `frame_id` | str | `'odom'` | Frame id ("base_link"/"odom"/"map"). Default "odom". |
| `reference_frame_id` | str | `'odom'` | Reference frame id ("odom"/"map"). Default "odom". |
| `is_blocking` | bool | `True` | Whether to block on joint zeroing (optional, default: True). |
| `leg_head_speed_rad_s` | SupportsFloat | `0.2` | Leg/head joint speed limit in rad/s (optional, default: 0.2). |
| `leg_head_timeout_s` | SupportsFloat | `15.0` | Leg/head blocking timeout in seconds (optional, default: 15.0). |
| `params` | [Parameter](#parameter-class) | `None` | Motion planning parameters (optional, default: None). |

**Returns**

| Type | Description |
| --- | --- |
| tuple[[MotionStatus](#motionstatus-enum), [ControlStatus](#controlstatus-enum)] | - |


---

<a id="module-galbotmotion"></a>

## GalbotMotion {#galbotmotion-class}

<small>Unified motion planning and control interface for Galbot robots.

This interface provides a comprehensive API for robot motion control, including: Forward and inverse kinematics computation Single-chain and multi-chain trajectory planning Collision detection (self-collision and environment) Tool and obstacle management Whole-body coordinated motion planning Use GalbotMotion::get_instance(MachineType) to obtain a reference for a specific platform (G1/S1). All angular units are radians, linear units are meters (SI standard). Quaternions must be unit-normalized: sqrt(x² + y² + z² + w²) = 1.</small>

### get_instance {#galbotmotion-get_instance-function}

```python
@staticmethod
def get_instance(machine_type: ...) -> GalbotMotion
```

<small>Runtime factory for selecting a concrete motion planning singleton.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `machine_type` | ... | required | - |

**Returns**

| Type | Description |
| --- | --- |
| [GalbotMotion](#galbotmotion-class) | - |

### add_obstacle {#galbotmotion-add_obstacle-function}

```python
def add_obstacle(
    obstacle_id: str,
    obstacle_type: str,
    pose: list[float],
    scale: list[float] = [0.0, 0.0, 0.0],
    key: str = '',
    target_frame: str = 'world',
    ee_frame: str = 'ee_base',
    reference_joint_positions: list[float] = [],
    reference_base_pose: list[float] = [],
    ignore_collision_link_names: Sequence[str] = [],
    safe_margin: SupportsFloat = 0.0,
    resolution: SupportsFloat = 0.01
) -> MotionStatus
```

<small>Load collision object into environment.

Inserts a geometric or mesh-based obstacle into the environment for collision avoidance. Obstacles can be static (world-fixed) or robot-relative. Supports primitive shapes, meshes, point clouds, and depth images.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `obstacle_id` | str | required | Unique ID for the obstacle (cannot be duplicated) |
| `obstacle_type` | str | required | Obstacle type. Options: box / sphere / cylinder / mesh / point_cloud / depth_image |
| `pose` | list[float] | required | Position and orientation of the obstacle. Length 7: [x, y, z, qx, qy, qz, qw] |
| `scale` | list[float] | `[0.0, 0.0, 0.0]` | Geometric size of the obstacle `box: length / width / height (l / w / h)` / `sphere: radius / - / -` / `cylinder: radius / height / -` |
| `key` | str | `''` | key for the obstacle. `mesh / point_cloud: file path` / `depth_image: camera type (front_head / left_arm / right_arm)` |
| `target_frame` | str | `'world'` | Target coordinate frame. Options: world / base_link / motion chain name |
| `ee_frame` | str | `'ee_base'` | End-effector coordinate frame. Only effective when target_frame is a motion chain name |
| `reference_joint_positions` | list[float] | `[]` | Robot joint state when loading obstacle. If empty, current joint state is used |
| `reference_base_pose` | list[float] | `[]` | Robot base pose in map coordinate frame. If empty, current base pose is used |
| `ignore_collision_link_names` | Sequence[str] | `[]` | List of robot link names to ignore in collision detection |
| `safe_margin` | SupportsFloat | `0.0` | Safe distance to obstacle. Collision is detected when obstacle distance is less than this value |
| `resolution` | SupportsFloat | `0.01` | Loading precision for some obstacle types. Defaults to 0.01 |

**Returns**

| Type | Description |
| --- | --- |
| [MotionStatus](#motionstatus-enum) | MotionStatus: Result of adding the obstacle |

!!! note
    Point-cloud note: point_cloud here refers to a point-cloud obstacle explicitly loaded via this API (typically from a file/offline data). It is NOT the same as a navigation-maintained point-cloud map. galbotMotion does not automatically subscribe to or synchronize with galbotNav's point-cloud map for collision.

!!! note
    Obstacles persist until explicitly removed or cleared.

!!! note
    For moving obstacles, remove and re-add at new poses (no update method currently).

!!! warning
    Large safe_margin values may over-constrain planning; use conservatively.

### attach_target_object {#galbotmotion-attach_target_object-function}

```python
def attach_target_object(
    obstacle_id: str,
    obstacle_type: str,
    pose: list[float],
    scale: list[float] = [0.0, 0.0, 0.0],
    key: str = '',
    target_frame: str = 'world',
    ee_frame: str = 'ee_base',
    reference_joint_positions: list[float] = [],
    reference_base_pose: list[float] = [],
    ignore_collision_link_names: Sequence[str] = [],
    safe_margin: SupportsFloat = 0.0,
    resolution: SupportsFloat = 0.01
) -> MotionStatus
```

<small>Attach a collision object to the robot (e.g., grasped object).

Similar to add_obstacle(), but the object moves with the robot (attached to a link/chain). Used for representing grasped objects, sensors, or payloads. The object's pose is maintained relative to the attachment frame during motion.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `obstacle_id` | str | required | Unique ID for the obstacle (cannot repeat) |
| `obstacle_type` | str | required | Type of obstacle (box/sphere/cylinder/mesh/point_cloud/depth_image) |
| `pose` | list[float] | required | Position and orientation of the obstacle (length 7: xyz+quat) |
| `scale` | list[float] | `[0.0, 0.0, 0.0]` | Geometry size (box: l/w/h; sphere: r/-/-; cylinder: r/h/-) |
| `key` | str | `''` | File path (mesh/point_cloud) or camera type (depth_image: front_head/left_arm/right_arm) |
| `target_frame` | str | `'world'` | Target coordinate frame (world/base_link/chain name) |
| `ee_frame` | str | `'ee_base'` | End-effector frame (only valid if target_frame is a chain) |
| `reference_joint_positions` | list[float] | `[]` | Robot joint state when loading obstacle (current if empty) |
| `reference_base_pose` | list[float] | `[]` | Robot base pose in map frame (current if empty) |
| `ignore_collision_link_names` | Sequence[str] | `[]` | Links to ignore collision with |
| `safe_margin` | SupportsFloat | `0.0` | Safe distance (collision if < this value) |
| `resolution` | SupportsFloat | `0.01` | Loading precision for some obstacle types |

**Returns**

| Type | Description |
| --- | --- |
| [MotionStatus](#motionstatus-enum) | MotionStatus: Result of adding obstacle |

!!! note
    Point-cloud note: same as add_obstacle(). point_cloud here is an explicitly loaded point-cloud object and will not be automatically synchronized with any navigation-side point-cloud map.

!!! note
    Attached objects move with the robot; their collision geometry is updated automatically.

!!! note
    Typically used in pick-and-place: attach_target_object after grasp, detach after release.

!!! warning
    Ensure ignore_collision_link_names includes grasping links to avoid false collisions.

### attach_tool {#galbotmotion-attach_tool-function}

```python
def attach_tool(chain: str, tool: str) -> MotionStatus
```

<small>Attach a tool to an end-effector.

Loads a tool (gripper, camera, custom end-effector) onto a kinematic chain. Updates the kinematic model and collision geometry to include the tool.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `chain` | str | required | The robot motion chain. |
| `tool` | str | required | The tool to attach. |

**Returns**

| Type | Description |
| --- | --- |
| [MotionStatus](#motionstatus-enum) | bool: True if the tool attachment is successful, False otherwise. |

!!! note
    Tool transform and collision geometry must be pre-configured in robot description.

!!! note
    Attaching a new tool automatically detaches any previously attached tool on that chain.

!!! warning
    Kinematics and collision checking will reflect the attached tool; update plans accordingly.

### check_collision {#galbotmotion-check_collision-function}

```python
def check_collision(
    start: Sequence[RobotStates],
    enable_collision_check: bool = True,
    params: Parameter = ...
) -> tuple[MotionStatus, list[bool]]
```

<small>Check robot states for collisions.

Therefore, if you need Motion to consider environmental obstacles (including point clouds), you must load the obstacle map/objects explicitly (e.g., obstacle_type = point_cloud with a file path in key).

Note: integrating real-time perception (navigation-style obstacle updates / point-cloud map) into galbotMotion is a planned future feature and has limited internal validation at the moment. Validates whether given robot configurations are collision-free. Checks both self-collisions (robot links with each other) and environment collisions (robot with scene obstacles). Batch processing supported for efficiency.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `start` | Sequence[[RobotStates](#robotstates-class)] | required | The robot states. |
| `enable_collision_check` | bool | `True` | Whether to enable collision checking. Defaults to true. |
| `params` | [Parameter](#parameter-class) | `...` | Additional parameters for the collision checking. Defaults to default_param. |

**Returns**

| Type | Description |
| --- | --- |
| tuple[[MotionStatus](#motionstatus-enum), list[bool]] | bool: True if there is a collision, False otherwise. |

!!! note
    [Obstacle perception & point-cloud usage: galbotNav vs galbotMotion]

!!! note
    Useful for validating planned trajectories or sampling-based planners.

!!! note
    Respects safe_margin settings in previously added obstacles.

### clear_obstacle {#galbotmotion-clear_obstacle-function}

```python
def clear_obstacle() -> MotionStatus
```

<small>Remove all collision obstacles from the planning scene.

Clears the entire obstacle set, resetting the planning scene to empty (except robot geometry).</small>

**Returns**

| Type | Description |
| --- | --- |
| [MotionStatus](#motionstatus-enum) | - |

!!! note
    Attached objects (see attach_target_object) are not affected.

!!! note
    Safe to call even if scene is already empty.

### detach_target_object {#galbotmotion-detach_target_object-function}

```python
def detach_target_object(obstacle_id: str) -> MotionStatus
```

<small>Detach an object from the robot (e.g., after release).

Removes an attached object from the robot. Typically called after releasing a grasped object. The object is removed from the planning scene entirely (not converted to a static obstacle).</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `obstacle_id` | str | required | - |

**Returns**

| Type | Description |
| --- | --- |
| [MotionStatus](#motionstatus-enum) | - |

!!! note
    To keep the object in the scene as a static obstacle after release, call detach_target_object() then add_obstacle() with the object's final pose.

### detach_tool {#galbotmotion-detach_tool-function}

```python
def detach_tool(chain: str) -> MotionStatus
```

<small>Detach the current tool from an end-effector.

Removes the attached tool from a kinematic chain, reverting to the base end-effector. Updates kinematic model and collision geometry accordingly.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `chain` | str | required | The robot motion chain. |

**Returns**

| Type | Description |
| --- | --- |
| [MotionStatus](#motionstatus-enum) | bool: True if the tool detachment is successful, False otherwise. |

!!! note
    If no tool is attached, operation succeeds as a no-op.

### forward_kinematics {#galbotmotion-forward_kinematics-function}

```python
def forward_kinematics(
    target_frame: str,
    reference_frame: str = 'base_link',
    joint_state: dict] = {},
    params: Parameter = ...
) -> tuple[MotionStatus, list[float]]
```

<small>Compute forward kinematics for a target link.

Calculates the Cartesian pose of a specified link given joint configurations. Useful for determining end-effector positions, validating configurations, or computing intermediate link poses.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `target_frame` | str | required | The name of the target frame. |
| `reference_frame` | str | `'base_link'` | The name of the reference frame. Defaults to "base_link". |
| `joint_state` | dict] | `{}` | A dictionary mapping joint names to their positions. Defaults to an empty dictionary. |
| `params` | [Parameter](#parameter-class) | `...` | Additional parameters for the forward kinematics. Defaults to default_param. |

**Returns**

| Type | Description |
| --- | --- |
| tuple[[MotionStatus](#motionstatus-enum), list[float]] | Pose: The computed pose of the target frame. |

!!! note
    Joint angles in radians, output pose in meters with unit quaternion.

!!! warning
    target_frame must be a valid link in the URDF model.

### forward_kinematics_by_state {#galbotmotion-forward_kinematics_by_state-function}

```python
def forward_kinematics_by_state(
    target_frame: str,
    reference_robot_states: RobotStates = None,
    reference_frame: str = 'base_link',
    params: Parameter = ...
) -> tuple[MotionStatus, list[float]]
```

<small>Compute forward kinematics using complete robot state.

Similar to forward_kinematics(), but accepts a RobotStates object for specifying the complete robot configuration (whole-body joints + base pose).</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `target_frame` | str | required | The name of the target frame. |
| `reference_robot_states` | [RobotStates](#robotstates-class) | `None` | The reference robot states. Defaults to nullptr. |
| `reference_frame` | str | `'base_link'` | The name of the reference frame. Defaults to "base_link". |
| `params` | [Parameter](#parameter-class) | `...` | Additional parameters for the forward kinematics. Defaults to default_param. |

**Returns**

| Type | Description |
| --- | --- |
| tuple[[MotionStatus](#motionstatus-enum), list[float]] | Pose: The computed pose of the target frame. |

!!! note
    Useful when computing FK for hypothetical states without modifying current robot state.

### get_built_obstacles_list {#galbotmotion-get_built_obstacles_list-function}

```python
def get_built_obstacles_list() -> list[str]
```

<small>Get the list of currently loaded obstacle IDs.</small>

**Returns**

| Type | Description |
| --- | --- |
| list[str] | - |

### get_chain_joint_state {#galbotmotion-get_chain_joint_state-function}

```python
def get_chain_joint_state() -> dict[str, list[float]]
```

<small>Get current joint configurations for all kinematic chains.

Retrieves per-chain joint states, decomposing the whole-body configuration into individual chain contributions.</small>

**Returns**

| Type | Description |
| --- | --- |
| dict[str, list[float]] | - |

!!! note
    Joint vector sizes vary by chain DOF.

### get_end_effector_pose {#galbotmotion-get_end_effector_pose-function}

```python
def get_end_effector_pose(
    end_effector_frame: str,
    reference_frame: str = 'base_link'
) -> tuple[MotionStatus, list[float]]
```

<small>Get current end-effector pose from robot state.

Queries the TF (Transform) tree to retrieve the current Cartesian pose of a specified end-effector link. Requires the link to be defined in the robot's URDF model.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `end_effector_frame` | str | required | The name of the end-effector frame. |
| `reference_frame` | str | `'base_link'` | The name of the reference frame. Defaults to "base_link". |

**Returns**

| Type | Description |
| --- | --- |
| tuple[[MotionStatus](#motionstatus-enum), list[float]] | Pose: The computed pose of the end-effector frame. |

!!! note
    Reflects the current actual robot state (not planned state).

!!! warning
    Requires TF tree to be properly published and up-to-date.

### get_end_effector_pose_on_chain {#galbotmotion-get_end_effector_pose_on_chain-function}

```python
def get_end_effector_pose_on_chain(
    chain_name: str,
    frame_id: str = 'EndEffector',
    reference_frame: str = 'base_link'
) -> tuple[MotionStatus, list[float]]
```

<small>Get current end-effector pose for a specific kinematic chain.

Convenience method for retrieving end-effector pose by chain name and frame type, without needing to know the exact link name in URDF.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `chain_name` | str | required | The name of the chain. |
| `frame_id` | str | `'EndEffector'` | The name of the end-effector frame. Defaults to "EndEffector". |
| `reference_frame` | str | `'base_link'` | The name of the reference frame. Defaults to "base_link". |

**Returns**

| Type | Description |
| --- | --- |
| tuple[[MotionStatus](#motionstatus-enum), list[float]] | Pose: The computed pose of the end-effector frame on the specified chain. |

!!! note
    Internally maps chain_name + frame_id to actual URDF link name.

### get_link_names {#galbotmotion-get_link_names-function}

```python
def get_link_names(only_end_effector: bool = False) -> list[str]
```

<small>Get robot link names from kinematic model.

Retrieves the list of link names defined in the robot's URDF model. Can filter to only end-effector links or return all links.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `only_end_effector` | bool | `False` | If true, returns only end-effector/tool links; if false, returns all links including base, intermediate, and end-effector links. |

**Returns**

| Type | Description |
| --- | --- |
| list[str] | list: Vector of link name strings (empty if retrieval fails) |

!!! note
    End-effector detection based on link having no child links in kinematic tree.

!!! note
    Useful for forward kinematics queries or TF frame validation.

### get_motion_plan_config {#galbotmotion-get_motion_plan_config-function}

```python
def get_motion_plan_config() -> tuple[MotionStatus, MotionPlanConfig]
```

<small>Get current motion planning configuration.

Retrieves the active planner configuration, including velocity/acceleration limits and planning algorithm parameters.</small>

**Returns**

| Type | Description |
| --- | --- |
| tuple[[MotionStatus](#motionstatus-enum), [MotionPlanConfig](#motionplanconfig-class)] | - |

!!! note
    Useful for inspecting current limits or saving/restoring configurations.

### get_robot_states {#galbotmotion-get_robot_states-function}

```python
def get_robot_states() -> RobotStates
```

<small>Get current complete robot state.

Retrieves the current whole-body joint configuration and mobile base pose. Represents the full kinematic state of the robot.</small>

**Returns**

| Type | Description |
| --- | --- |
| [RobotStates](#robotstates-class) | - |

!!! note
    Reflects actual robot state (from sensor feedback/state estimation).

!!! note
    Useful as seed/reference for planning operations.

### get_supported_chains {#galbotmotion-get_supported_chains-function}

```python
def get_supported_chains() -> set[str]
```

<small>Get the set of supported kinematic chain names (e.g. left_arm, right_arm).</small>

**Returns**

| Type | Description |
| --- | --- |
| set[str] | - |

### get_supported_ee_frames {#galbotmotion-get_supported_ee_frames-function}

```python
def get_supported_ee_frames() -> set[str]
```

<small>Get the set of supported end-effector frame identifiers.</small>

**Returns**

| Type | Description |
| --- | --- |
| set[str] | - |

### get_supported_frames {#galbotmotion-get_supported_frames-function}

```python
def get_supported_frames() -> set[str]
```

<small>Get the set of supported reference frame names.</small>

**Returns**

| Type | Description |
| --- | --- |
| set[str] | - |

### get_supported_links {#galbotmotion-get_supported_links-function}

```python
def get_supported_links() -> set[str]
```

<small>Get the set of supported link names (URDF link names for FK/IK).</small>

**Returns**

| Type | Description |
| --- | --- |
| set[str] | - |

### get_supported_obstacle_types {#galbotmotion-get_supported_obstacle_types-function}

```python
def get_supported_obstacle_types() -> set[str]
```

<small>Get the set of supported obstacle types (e.g. box, sphere, cylinder, mesh).</small>

**Returns**

| Type | Description |
| --- | --- |
| set[str] | - |

### get_supported_tool_list {#galbotmotion-get_supported_tool_list-function}

```python
def get_supported_tool_list() -> set[str]
```

<small>Get the list of supported tool names for attach_tool.</small>

**Returns**

| Type | Description |
| --- | --- |
| set[str] | - |

### init {#galbotmotion-init-function}

```python
def init() -> bool
```

<small>Initialize motion planning system and communication interfaces.

Must be called before any other API functions. Initializes internal communication middleware, loads robot kinematic models, and establishes connections to control services.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | - |

!!! note
    Safe to call multiple times; subsequent calls after successful init are no-ops.

!!! warning
    All other API calls will fail if init() returns false.

### inverse_kinematics {#galbotmotion-inverse_kinematics-function}

```python
def inverse_kinematics(
    target_pose: list[float],
    chain_names: Sequence[str],
    target_frame: str = 'EndEffector',
    reference_frame: str = 'base_link',
    initial_joint_positions: dict] = {},
    enable_collision_check: bool = True,
    params: Parameter = ...
) -> tuple[MotionStatus, dict[str, list[float]]]
```

<small>Compute inverse kinematics for target Cartesian pose.

Solves for joint configurations that achieve the specified end-effector pose. Supports single-chain IK (arm only) or coordinated multi-chain IK (arm + torso/legs).</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `target_pose` | list[float] | required | The target pose. |
| `chain_names` | Sequence[str] | required | The list of chain names to consider. |
| `target_frame` | str | `'EndEffector'` | The name of the target frame. Defaults to "EndEffector". |
| `reference_frame` | str | `'base_link'` | The name of the reference frame. Defaults to "base_link". |
| `initial_joint_positions` | dict] | `{}` | A dictionary mapping joint names to their initial positions. Defaults to an empty dictionary. |
| `enable_collision_check` | bool | `True` | Whether to enable collision checking. Defaults to true. |
| `params` | [Parameter](#parameter-class) | `...` | Additional parameters for the inverse kinematics. Defaults to default_param. |

**Returns**

| Type | Description |
| --- | --- |
| tuple[[MotionStatus](#motionstatus-enum), dict[str, list[float]]] | dict: A dictionary mapping joint names to their computed positions. |

!!! note
    IK may have multiple solutions; returns first valid solution found.

!!! note
    Seed configuration affects convergence speed and which solution is returned.

!!! warning
    No solution guaranteed if target is outside workspace or in singular configuration.

### inverse_kinematics_by_state {#galbotmotion-inverse_kinematics_by_state-function}

```python
def inverse_kinematics_by_state(
    target_pose: list[float],
    chain_names: Sequence[str],
    target_frame: str = 'EndEffector',
    reference_frame: str = 'base_link',
    reference_robot_states: RobotStates = None,
    enable_collision_check: bool = True,
    params: Parameter = ...
) -> tuple[MotionStatus, dict[str, list[float]]]
```

<small>Compute inverse kinematics using complete robot state as seed.

Similar to inverse_kinematics(), but accepts RobotStates for specifying the seed configuration, allowing precise control over the entire robot state.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `target_pose` | list[float] | required | The target pose. |
| `chain_names` | Sequence[str] | required | The list of chain names to consider. |
| `target_frame` | str | `'EndEffector'` | The name of the target frame. Defaults to "EndEffector". |
| `reference_frame` | str | `'base_link'` | The name of the reference frame. Defaults to "base_link". |
| `reference_robot_states` | [RobotStates](#robotstates-class) | `None` | The reference robot states. Defaults to nullptr. |
| `enable_collision_check` | bool | `True` | Whether to enable collision checking. Defaults to true. |
| `params` | [Parameter](#parameter-class) | `...` | Additional parameters for the inverse kinematics. Defaults to default_param. |

**Returns**

| Type | Description |
| --- | --- |
| tuple[[MotionStatus](#motionstatus-enum), dict[str, list[float]]] | dict: A dictionary mapping joint names to their computed positions. |

!!! note
    Useful for offline planning with hypothetical robot states.

### motion_plan {#galbotmotion-motion_plan-function}

```python
def motion_plan(
    target: RobotStates,
    start: RobotStates = None,
    reference_robot_states: RobotStates = None,
    enable_collision_check: bool = True,
    params: Parameter = ...
) -> tuple[MotionStatus, dict[str, list[list[float]]]]
```

<small>Plan trajectory for a single kinematic chain.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `target` | [RobotStates](#robotstates-class) | required | The target pose. |
| `start` | [RobotStates](#robotstates-class) | `None` | The initial robot states. Defaults to nullptr. |
| `reference_robot_states` | [RobotStates](#robotstates-class) | `None` | The reference robot states. Defaults to nullptr. |
| `enable_collision_check` | bool | `True` | Whether to enable collision checking. Defaults to true. |
| `params` | [Parameter](#parameter-class) | `...` | Additional parameters for the motion planning. Defaults to default_param. |

**Returns**

| Type | Description |
| --- | --- |
| tuple[[MotionStatus](#motionstatus-enum), dict[str, list[list[float]]]] | bool: True if the motion planning is successful, False otherwise. |

!!! note
    Collision semantics: galbotMotion does not have real-time obstacle perception. When enable_collision_check=true, collision checking is evaluated against self-collision and the Motion-side environment objects that the user loads manually via add_obstacle() / attach_target_object().

!!! note
    Trajectory is time-parameterized with velocity/acceleration limits respected.

!!! note
    For direct execution (params->is_direct_execute=true), trajectory is automatically sent to robot.

!!! warning
    target must be PoseState or JointStates; passing base RobotStates will cause INVALID_INPUT error.

### motion_plan_multi_waypoints {#galbotmotion-motion_plan_multi_waypoints-function}

```python
def motion_plan_multi_waypoints(
    target: RobotStates,
    waypoint_poses: Sequence[list[float]],
    start: RobotStates = None,
    reference_robot_states: RobotStates = None,
    enable_collision_check: bool = True,
    params: Parameter = ...
) -> tuple[MotionStatus, dict[str, list[list[float]]]]
```

<small>Plan coordinated trajectories through waypoints for multiple chains.

Enables coordinated multi-arm or whole-body motion through waypoint sequences. Each chain can have its own waypoint sequence, executed in synchronized fashion.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `target` | [RobotStates](#robotstates-class) | required | The target pose. |
| `waypoint_poses` | Sequence[list[float]] | required | The waypoint poses. |
| `start` | [RobotStates](#robotstates-class) | `None` | The initial robot states. Defaults to nullptr. |
| `reference_robot_states` | [RobotStates](#robotstates-class) | `None` | The reference robot states. Defaults to nullptr. |
| `enable_collision_check` | bool | `True` | Whether to enable collision checking. Defaults to true. |
| `params` | [Parameter](#parameter-class) | `...` | Additional parameters for the motion planning. Defaults to default_param. |

**Returns**

| Type | Description |
| --- | --- |
| tuple[[MotionStatus](#motionstatus-enum), dict[str, list[list[float]]]] | bool: True if the motion planning is successful, False otherwise. |

!!! note
    All chain trajectories are time-synchronized for coordinated execution.

!!! note
    Useful for bimanual manipulation or mobile manipulation tasks.

### motion_plan_multi_waypoints {#galbotmotion-motion_plan_multi_waypoints-function}

```python
def motion_plan_multi_waypoints(
    targets: dict]],
    start: Sequence[RobotStates] = [],
    reference_robot_states: RobotStates = None,
    enable_collision_check: bool = True,
    params: Parameter = ...
) -> tuple[MotionStatus, dict[str, list[list[float]]]]
```

<small>Plan coordinated trajectories through waypoints for multiple chains.

Enables coordinated multi-arm or whole-body motion through waypoint sequences. Each chain can have its own waypoint sequence, executed in synchronized fashion.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `targets` | dict]] | required | The target poses. |
| `start` | Sequence[[RobotStates](#robotstates-class)] | `[]` | The initial robot states. Defaults to nullptr. |
| `reference_robot_states` | [RobotStates](#robotstates-class) | `None` | The reference robot states. Defaults to nullptr. |
| `enable_collision_check` | bool | `True` | Whether to enable collision checking. Defaults to true. |
| `params` | [Parameter](#parameter-class) | `...` | Additional parameters for the motion planning. Defaults to default_param. |

**Returns**

| Type | Description |
| --- | --- |
| tuple[[MotionStatus](#motionstatus-enum), dict[str, list[list[float]]]] | bool: True if the motion planning is successful, False otherwise. |

!!! note
    All chain trajectories are time-synchronized for coordinated execution.

!!! note
    Useful for bimanual manipulation or mobile manipulation tasks.

### move_whole_body_joint_zero {#galbotmotion-move_whole_body_joint_zero-function}

```python
def move_whole_body_joint_zero(
    is_blocking: bool = True,
    leg_head_speed_rad_s: SupportsFloat = 0.2,
    leg_head_timeout_s: SupportsFloat = 15.0,
    params: Parameter = ...
) -> MotionStatus
```

<small>Move the whole-body joints to the predefined zero (home) configuration.

The leg and head joints are commanded via GalbotRobot (direct joint control), while the left/right arms are planned via the motion planner with collision checking enabled.

Joint order of the zero configuration follows the SDK convention: leg(5) + head(2) + left_arm(7) + right_arm(7).</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `is_blocking` | bool | `True` | - |
| `leg_head_speed_rad_s` | SupportsFloat | `0.2` | - |
| `leg_head_timeout_s` | SupportsFloat | `15.0` | - |
| `params` | [Parameter](#parameter-class) | `...` | - |

**Returns**

| Type | Description |
| --- | --- |
| [MotionStatus](#motionstatus-enum) | - |

### remove_obstacle {#galbotmotion-remove_obstacle-function}

```python
def remove_obstacle(obstacle_id: str) -> MotionStatus
```

<small>Remove a collision obstacle from the planning scene.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `obstacle_id` | str | required | - |

**Returns**

| Type | Description |
| --- | --- |
| [MotionStatus](#motionstatus-enum) | - |

!!! note
    Removing a non-existent obstacle returns INVALID_INPUT (not silently ignored).

### set_end_effector_pose {#galbotmotion-set_end_effector_pose-function}

```python
def set_end_effector_pose(
    target_pose: list[float],
    end_effector_frame: str,
    reference_frame: str = 'base_link',
    reference_robot_states: RobotStates = None,
    enable_collision_check: bool = True,
    is_blocking: bool = True,
    timeout: SupportsFloat = -1.0,
    params: Parameter = ...
) -> MotionStatus
```

<small>Command end-effector to move to target Cartesian pose.

High-level interface for Cartesian motion commands. Internally performs IK, plans trajectory, and optionally executes the motion. Supports both blocking (wait for completion) and non-blocking (return immediately) modes.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `target_pose` | list[float] | required | The target pose. |
| `end_effector_frame` | str | required | The name of the end-effector frame. |
| `reference_frame` | str | `'base_link'` | The name of the reference frame. Defaults to "base_link". |
| `reference_robot_states` | [RobotStates](#robotstates-class) | `None` | The reference robot states. Defaults to nullptr. |
| `enable_collision_check` | bool | `True` | Whether to enable collision checking. Defaults to true. |
| `is_blocking` | bool | `True` | Whether to block until the motion is completed. Defaults to true. |
| `timeout` | SupportsFloat | `-1.0` | The maximum time to wait for the motion to complete. Defaults to -1.0. |
| `params` | [Parameter](#parameter-class) | `...` | Additional parameters for the motion planning. Defaults to default_param. |

**Returns**

| Type | Description |
| --- | --- |
| [MotionStatus](#motionstatus-enum) | bool: True if the motion planning is successful, False otherwise. |

!!! note
    Motion type (linear/joint-space) controlled by params->move_line flag.

!!! note
    For direct execution (params->is_direct_execute=true), avoid passing reference_robot_states.

!!! warning
    Blocking calls will halt execution until motion completes; use with caution in real-time contexts.

### set_motion_plan_config {#galbotmotion-set_motion_plan_config-function}

```python
def set_motion_plan_config(config: MotionPlanConfig) -> MotionStatus
```

<small>Set global motion planning configuration.

Updates planner settings such as velocity/acceleration limits, planning algorithm parameters, and optimization objectives. Affects all subsequent planning operations.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `config` | [MotionPlanConfig](#motionplanconfig-class) | required | - |

**Returns**

| Type | Description |
| --- | --- |
| [MotionStatus](#motionstatus-enum) | - |

!!! note
    Changes persist until explicitly reset or process restart.

!!! note
    See MotionPlanConfig documentation for available parameters.

### status_to_string {#galbotmotion-status_to_string-function}

```python
def status_to_string(status: MotionStatus) -> str
```

<small>Convert MotionStatus enum to human-readable string.

Maps status codes to descriptive strings for logging, error reporting, or UI display.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `status` | [MotionStatus](#motionstatus-enum) | required | - |

**Returns**

| Type | Description |
| --- | --- |
| str | - |

!!! note
    Uses status_string_map_ for lookup; returns "UNKNOWN" if status not found.


---

<a id="module-galbotnavigation"></a>

## GalbotNavigation {#galbotnavigation-class}

<small>Navigation interface for mobile robot chassis motion planning and localization.

This class provides a thread-safe singleton interface for controlling the mobile base navigation system. It supports 2D pose estimation, relocalization, goal-directed navigation with dynamic obstacle avoidance, and path planning capabilities. The navigation system operates in a global map frame and provides both blocking and non-blocking navigation modes. It supports both differential drive and omnidirectional motion planning strategies. This class uses the singleton pattern with thread-safe initialization. All pose coordinates are specified in the map frame unless explicitly stated otherwise. Typical usage: auto&nav=GalbotNavigation::get_instance(MachineType::G1); if(nav.init()){ Posegoal; goal.x=1.0;//meters goal.y=2.0;//meters goal.orientation.w=1.0;//identityquaternion(x,y,zdefault0) nav.navigate_to_goal(goal,true,false,30.0,true); }</small>

### get_instance {#galbotnavigation-get_instance-function}

```python
@staticmethod
def get_instance(machine_type: MachineType) -> GalbotNavigation
```

<small>Runtime factory for selecting a concrete navigation singleton.

This static factory method allows runtime selection of the navigation implementation based on the robot machine type. The method declaration resides in the interface header for compile-time availability, while the actual implementation logic (including platform-specific includes and switch statements) is contained in the corresponding .cpp file. This design keeps the interface clean while enabling platform-specific instantiation without exposing implementation details.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `machine_type` | [MachineType](#machinetype-enum) | required | MachineType enum (e.g. MachineType.G1 / MachineType.S1) |

**Returns**

| Type | Description |
| --- | --- |
| [GalbotNavigation](#galbotnavigation-class) | GalbotNavigation: The navigation instance for that machine type. |

!!! note
    Adding support for a new machine type requires updating the MachineType enumeration and the factory implementation in the .cpp file.

### check_goal_arrival {#galbotnavigation-check_goal_arrival-function}

```python
def check_goal_arrival() -> bool
```

<small>Check if the robot has successfully reached the current goal.

This method queries the navigation system to determine if the robot has arrived at the goal pose within acceptable position and orientation tolerances. This is particularly useful when using non-blocking navigation mode to poll for completion.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | bool: True if the robot has reached the goal; False if still navigating or no active goal. |

!!! note
    This method is most useful in non-blocking navigation scenarios where the application needs to monitor progress.

!!! note
    The tolerance thresholds for "arrival" are defined by the navigation system's internal parameters (typically a few centimeters in position and a few degrees in orientation).

!!! note
    If no navigation command is active, this method returns false.

### check_path_reachability {#galbotnavigation-check_path_reachability-function}

```python
def check_path_reachability(goal_pose: numpy.ArrayLike, start_pose: numpy.ArrayLike) -> bool
```

<small>Check if a collision-free path exists from start to goal in the map.

This method queries the global path planner to determine if a valid, collision-free path exists between the specified start and goal poses. This is useful for validating goal poses before attempting navigation, or for multi-goal path planning.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `goal_pose` | numpy.ArrayLike | required | Goal pose [x, y, z, qx, qy, qz, qw], map frame. |
| `start_pose` | numpy.ArrayLike | required | Start pose [x, y, z, qx, qy, qz, qw], map frame. |

**Returns**

| Type | Description |
| --- | --- |
| bool | bool: True if a collision-free path exists from start to goal; False otherwise. |

!!! note
    This method only checks for static obstacles based on the map data. Dynamic obstacles are not considered.

!!! note
    The path computation may take some time depending on distance and map complexity.

!!! note
    A return value of true does not guarantee successful navigation, as dynamic obstacles or localization errors may still cause failures.

### get_current_pose {#galbotnavigation-get_current_pose-function}

```python
def get_current_pose() -> list[float]
```

<small>Get the current estimated pose of the robot chassis in the map frame.

This method returns the most recent pose estimate from the localization system. The pose represents the position and orientation of the robot's base_link frame relative to the map frame origin.</small>

**Returns**

| Type | Description |
| --- | --- |
| list[float] | array: [x, y, z, qx, qy, qz, qw], map frame (meters, unit quaternion). Valid only if is_localized() is True. |

!!! note
    The returned pose is only valid if is_localized() returns true.

!!! note
    The pose represents the center of the robot's base footprint.

### get_navigation_status {#galbotnavigation-get_navigation_status-function}

```python
def get_navigation_status() -> NavigationTaskStatus
```

<small>Get the current navigation task state.

Returns the most recent task state reported by the navigation system (UNKNOWN, RUNNING, SUCCESS, or FAILED). Use this when running non-blocking navigation to poll for state and exit error logic in time on FAILED or timeout, avoiding deadlock or indefinite wait.</small>

**Returns**

| Type | Description |
| --- | --- |
| [NavigationTaskStatus](#navigationtaskstatus-enum) | NavigationTaskStatus: Current task state for non-blocking navigation polling. |

!!! note
    Useful in non-blocking navigation: loop on get_navigation_status() and break on SUCCESS, FAILED, or after a timeout.

### init {#galbotnavigation-init-function}

```python
def init() -> bool
```

<small>Initialize the navigation subsystem and its dependencies.

This method must be called before using any other navigation functions. It initializes communication channels, loads the map, starts the localization module, and prepares the path planner.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | bool: True if initialization succeeded; False otherwise. |

!!! note
    This method should only be called once after obtaining the singleton instance.

!!! note
    Subsequent calls will return the result of the first initialization attempt.

!!! warning
    Calling navigation methods before successful initialization will result in undefined behavior.

### is_localized {#galbotnavigation-is_localized-function}

```python
def is_localized() -> bool
```

<small>Check whether the robot is currently localized in the map.

This method queries the localization system to determine if the robot has a valid pose estimate with sufficient confidence. A robot that is not localized should not perform navigation tasks.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | bool: True if localized; False if localization is lost or uncertain. |

!!! note
    It is recommended to check localization status before issuing navigation commands.

!!! note
    If this returns false, consider calling relocalize() with a known pose estimate.

### move_straight_to {#galbotnavigation-move_straight_to-function}

```python
def move_straight_to(
    goal_pose: numpy.ArrayLike,
    is_blocking: bool = True,
    timeout: SupportsFloat = 8
) -> tuple
```

<small>Move the robot to a relative target pose in the odometry frame.

This method commands the robot to move to a pose specified relative to its current position in the odometry (odom) frame. This is useful for short, precise movements where map-based planning is not needed. Unlike navigate_to_goal(), this method does NOT perform dynamic obstacle detection or global path planning. It uses omnidirectional motion planning for direct movement to the target.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `goal_pose` | numpy.ArrayLike | required | Target pose relative to current base_link [x, y, z, qx, qy, qz, qw], odom frame (meters). |
| `is_blocking` | bool | `True` | If True, blocks until motion is complete or timeout; default True. |
| `timeout` | SupportsFloat | `8` | Maximum wait time in seconds for blocking mode; default 8.0. |

**Returns**

| Type | Description |
| --- | --- |
| tuple | tuple: (success: bool, status_string: str)<br>- success: True if motion succeeded.<br>- status_string: Status string. |

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

### navigate_to_goal {#galbotnavigation-navigate_to_goal-function}

```python
def navigate_to_goal(
    goal_pose: numpy.ArrayLike,
    enable_collision_check: bool = True,
    is_blocking: bool = False,
    timeout: SupportsFloat = 8,
    omni_plan: bool = True
) -> tuple
```

<small>Navigate the robot to a target goal pose in the map frame.

This method commands the mobile base to navigate to a specified goal pose using the global path planner and local trajectory controller. The planner will compute a collision-free path from the current pose to the goal, considering both static map obstacles and dynamic obstacles if collision checking is enabled.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `goal_pose` | numpy.ArrayLike | required | Target goal pose [x, y, z, qx, qy, qz, qw], map frame (meters, quaternion). |
| `enable_collision_check` | bool | `True` | If True, enables dynamic obstacle detection and avoidance; default True. |
| `is_blocking` | bool | `False` | If True, blocks until goal is reached or timeout; default False. |
| `timeout` | SupportsFloat | `8` | Maximum wait time in seconds for blocking mode; default 8.0. |
| `omni_plan` | bool | `True` | If True, omnidirectional motion planning; if False, differential drive; default True. |

**Returns**

| Type | Description |
| --- | --- |
| tuple | tuple: (success: bool, status_string: str)<br>- success: True if navigation succeeded.<br>- status_string: Status string (SUCCESS, FAIL, TIMEOUT, etc.). |

!!! note
    The robot must be localized (is_localized() returns true) before calling this method.

!!! note
    For blocking mode, the calling thread will be blocked until completion or timeout.

!!! note
    The actual navigation time may exceed the timeout value in blocking mode before the method returns.

!!! warning
    In non-blocking mode, monitor navigation progress separately to detect completion or failures.

### relocalize {#galbotnavigation-relocalize-function}

```python
def relocalize(init_pose: numpy.ArrayLike) -> tuple
```

<small>Perform relocalization to re-estimate the robot's pose in the map frame.

This method resets the localization filter and provides an initial pose estimate to help the robot re-establish its position in the known map. This is useful when the robot has lost localization or when manually placing the robot at a known position.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `init_pose` | numpy.ArrayLike | required | Initial pose estimate [x, y, z, qx, qy, qz, qw], map frame (meters, quaternion). |

**Returns**

| Type | Description |
| --- | --- |
| tuple | tuple: (success: bool, status_string: str)<br>- success: True if relocalization succeeded.<br>- status_string: Status string (SUCCESS, FAIL, etc.). |

!!! note
    The robot should be stationary during relocalization for best results.

!!! note
    After calling this method, use is_localized() to verify successful relocalization before proceeding with navigation tasks.

### stop_navigation {#galbotnavigation-stop_navigation-function}

```python
def stop_navigation() -> tuple
```

<small>Stop the current navigation task and bring the robot to a halt.

This method immediately cancels any ongoing navigation command (from either navigate_to_goal() or move_straight_to()) and commands the robot to stop. The robot will decelerate according to its kinematic constraints and come to a safe stop.</small>

**Returns**

| Type | Description |
| --- | --- |
| tuple | tuple: (success: bool, status_string: str)<br>- success: True if stop command was successfully sent.<br>- status_string: Status string. |

!!! note
    This method can be called at any time during navigation, including when using non-blocking navigation modes.

!!! note
    After stopping, the robot's position may not match the original goal.

!!! note
    The robot will attempt to stop smoothly following its acceleration limits.


---

<a id="module-galbotperception"></a>

## GalbotPerception {#galbotperception-class}

<small>Perception module interface; obtain the singleton via get_instance(MachineType).

Implemented for G1 only: get_instance(MachineType::S1) throws std::runtime_error.</small>

### get_instance {#galbotperception-get_instance-function}

```python
@staticmethod
def get_instance(machine_type: MachineType) -> GalbotPerception
```

<small>Get the singleton instance of GalbotPerception.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `machine_type` | [MachineType](#machinetype-enum) | required | Platform selector, e.g. MachineType.G1. MachineType.S1 raises RuntimeError (not supported). |

**Returns**

| Type | Description |
| --- | --- |
| [GalbotPerception](#galbotperception-class) | GalbotPerception: Reference to the singleton instance for that machine type. |

### get_latest_result {#galbotperception-get_latest_result-function}

```python
def get_latest_result(module: PerceptionModule) -> tuple
```

<small>Return the latest cached result for the module without blocking.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `module` | [PerceptionModule](#perceptionmodule-enum) | required | Perception module. |

**Returns**

| Type | Description |
| --- | --- |
| tuple | tuple[bool, DetectionResult]: (success, result). success is True if a result is available, False if none. |

### init {#galbotperception-init-function}

```python
def init(enabled_modules: Set[PerceptionModule]) -> bool
```

<small>Initialize perception and load models for the selected modules.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `enabled_modules` | Set[[PerceptionModule](#perceptionmodule-enum)] | required | Set of perception modules to enable. |

**Returns**

| Type | Description |
| --- | --- |
| bool | bool: True if every requested module loaded successfully. |

### run_once {#galbotperception-run_once-function}

```python
def run_once(module: PerceptionModule) -> bool
```

<small>Run a single inference for the given module.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `module` | [PerceptionModule](#perceptionmodule-enum) | required | Perception module to run. |

**Returns**

| Type | Description |
| --- | --- |
| bool | bool: True if the command was sent successfully. |

!!! note
    After init, wait ~10s for models to be ready before calling run_once.

### wait_for_new_result {#galbotperception-wait_for_new_result-function}

```python
def wait_for_new_result(module: PerceptionModule, timeout_s: SupportsFloat = 5.0) -> bool
```

<small>Block until the module produces a new result, or timeout. Use with run_once to fetch the latest output.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `module` | [PerceptionModule](#perceptionmodule-enum) | required | Perception module. |
| `timeout_s` | SupportsFloat | `5.0` | Timeout in seconds (default 5.0). |

**Returns**

| Type | Description |
| --- | --- |
| bool | bool: True if new data arrived, False on timeout. |


---

<a id="module-types-enums"></a>

## Types & Enums

### AudioData {#audiodata-class}

<small>Audio data structure.

Audio data structure used to encapsulate audio data.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `data` | list[int] | Binary data packet - for pcm format: 2560 bytes per 80ms, for json: text length or empty |
| `format` | str | Audio format: 'pcm' (16000Hz 16-bit mono) or 'json' (UTF-8 text) |
| `header` | [Header](#header-class) | Message header with timestamp and frame ID |
| `type` | str | Audio type identifier: 'waken_up' (wake-up event), 'denoise_chunk' (denoised audio), 'vad_begin' (VAD start), 'vad_chunk' (VAD audio), 'vad_end' (VAD end) |


---

### CollisionCheckOption {#collisioncheckoption-class}

<small>Collision detection enable/disable configuration.

This structure provides fine-grained control over collision checking during motion planning and execution. It supports independent toggling of self-collision detection (robot links colliding with each other) and environment collision detection (robot colliding with obstacles or workspace boundaries). Disabling collision checks improves computational performance but may result in unsafe trajectories. Use with caution in controlled environments.</small>

#### get_disable_env_collision_check {#collisioncheckoption-get_disable_env_collision_check-function}

```python
def get_disable_env_collision_check() -> bool
```

<small>Check if environment collision detection is disabled.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | - |

#### get_disable_self_collision_check {#collisioncheckoption-get_disable_self_collision_check-function}

```python
def get_disable_self_collision_check() -> bool
```

<small>Check if self-collision detection is disabled.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | - |

#### print {#collisioncheckoption-print-function}

```python
def print() -> None
```

<small>Print collision detection configuration to standard output.

Outputs enabled/disabled status for each collision check type.</small>

#### set_disable_env_collision_check {#collisioncheckoption-set_disable_env_collision_check-function}

```python
def set_disable_env_collision_check(disable: bool) -> None
```

<small>Enable or disable environment collision detection.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `disable` | bool | required | - |

!!! warning
    Disabling environment checks may result in collisions with obstacles

#### set_disable_self_collision_check {#collisioncheckoption-set_disable_self_collision_check-function}

```python
def set_disable_self_collision_check(disable: bool) -> None
```

<small>Enable or disable self-collision detection.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `disable` | bool | required | - |

!!! warning
    Disabling self-collision checks may result in physically infeasible configurations


---

### ControlStatus {#controlstatus-enum}

<small>Control command execution status enumeration.

Represents the execution status of robot control commands, including joint control, end-effector control, and other motion control operations.</small>

| Enum Value | Description |
| --- | --- |
| `COMM_DISCONNECTED` | Communication connection lost, cannot continue execution |
| `DATA_FETCH_FAILED` | Data retrieval failed during operation, unable to read required state |
| `FAULT` | Fault occurred, system detected anomaly and aborted execution |
| `INIT_FAILED` | Initialization failed, internal communication or dependent component creation failed |
| `INVALID_INPUT` | Input parameters invalid or not meeting interface requirements |
| `IN_PROGRESS` | Command is executing but has not reached target state |
| `PUBLISH_FAIL` | Control or state data publication failed, command may not be transmitted |
| `STOPPED_UNREACHED` | Stopped during execution without reaching target position or state |
| `SUCCESS` | Execution succeeded, command completed with valid result |
| `TIMEOUT` | Execution timeout, task not completed within specified time limit |


---

### DepthData {#depthdata-class}

<small>Depth image data structure.

Contains compressed depth image data from depth cameras or RGB-D sensors. Compatible with ROS 2 sensor_msgs/CompressedImage format with depth extensions.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `data` | list[int] | Compressed depth data |
| `depth_scale` | int | Depth scale/quantization factor |
| `format` | str | Image format |
| `header` | [Header](#header-class) | Message header |
| `height` | int | Image height |
| `width` | int | Image width |


---

### DetectionAndSegmentationResult {#detectionandsegmentationresult-class}

<small>Single-object detection or instance segmentation record (2D box, class, optional mask/keypoints).</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `bbox` | tuple[int, int, int, int] | Bounding box as (x, y, width, height) |
| `class_index` | int | Class index |
| `class_name` | str | Class name |
| `confidence` | float | Confidence score |
| `keypoints` | list[tuple[float, float]] | Keypoints as list of (x, y) tuples |


---

### DetectionResult {#detectionresult-class}

<small>Aggregated perception output for one module tick (images, masks, poses, point clouds, etc.).</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `bounding_boxes` | list[tuple[int, int, int, int]] | Bounding boxes as list of (x, y, width, height) |
| `class_indices` | list[int] | List of class indices |
| `class_names` | list[str] | List of class names |
| `confidences` | list[float] | List of confidences |
| `detection_results` | list[[DetectionAndSegmentationResult](#detectionandsegmentationresult-class)] | List of DetectionAndSegmentationResult |
| `grasp_pose_result` | list[list[float]] | Grasp pose results |
| `instance_mask` | Any | Instance mask as numpy array (HxW or HxWxC), or None if empty |
| `ocr_string` | list[str] | OCR results |
| `point_clouds` | list | Point clouds as list of Nx3 numpy arrays |
| `running_info` | str | Running info string |
| `sensor_name` | str | Sensor name |
| `target_point_poses` | list[numpy.NDArray[numpy.float32]"]] | 4x4 poses from perception proto field target_point_poses (same buffer as target_poses here) |
| `target_poses` | list[numpy.NDArray[numpy.float32]"]] | List of 4x4 target pose matrices (C++ targetPoses; perception proto target_point_poses fills this) |
| `timestamp_ns` | int | Timestamp in nanoseconds |

#### clear {#detectionresult-clear-function}

```python
def clear() -> None
```

<small>Clear all result fields</small>

#### get_result_info {#detectionresult-get_result_info-function}

```python
def get_result_info() -> str
```

<small>Get result summary string</small>

**Returns**

| Type | Description |
| --- | --- |
| str | - |


---

### Error {#error-class}

<small>Error information.

Describes an error from a single module or component, including error code and human-readable description for debugging and diagnostics.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `commpent` | str | Fault component name |
| `description` | str | Human-readable error description |
| `error_code` | int | Numerical error code |


---

### ErrorInfo {#errorinfo-class}

<small>Error information collection.

Contains a timestamped collection of error messages from multiple modules or components.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `error_vec` | list[[Error](#error-class)] | List of error entries |
| `timestamp_ns` | int | Collection timestamp in nanoseconds |


---

### ForceData {#forcedata-class}

<small>Force sensor data.

Contains timestamped force and torque measurements from a 6-axis force/torque sensor, typically mounted at robot wrists or tool interfaces.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `force` | [Vector3](#vector3-class) | Force vector Vector3 |
| `timestamp_ns` | int | Timestamp (nanoseconds) |
| `torque` | [Vector3](#vector3-class) | Torque vector Vector3 |


---

### FrameTriad {#frametriad-class}

<small>Task-space command for a body frame relative to a reference frame.

Mirrors galbot.spatial_proto.FrameTriad at the SDK type layer.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `body_frame_id` | str | Body frame id |
| `header` | [Header](#header-class) | Message header |
| `pose` | [Pose](#pose-class) | None | Optional pose command |
| `reference_frame_id` | str | Reference frame id |
| `twist` | [Twist](#twist-class) | None | Optional twist command |
| `wrench` | [Wrench](#wrench-class) | None | Optional wrench command |


---

### G1ControllerName {#g1controllername-enum}

<small>String constants for G1 controller names.

Defines the controller names supported by the G1 robot model.</small>

| Enum Value | Description |
| --- | --- |
| `CHASSIS_POSE_CTRL` | Chassis pose controller |
| `CHASSIS_TWIST_CTRL` | Chassis twist controller |
| `CONTROLLER_NAME_NUM` | Sentinel value for invalid controller name |
| `HEAD_PVT_BYPASS_CTRL` | Head PVT bypass controller |
| `HEAD_PVT_CTRL` | Head PVT controller |
| `LEFT_ARM_PVT_BYPASS_CTRL` | Left arm PVT bypass controller |
| `LEFT_ARM_PVT_CTRL` | Left arm PVT controller |
| `LEFT_DEXHAND_CTRL` | Left dexhand controller |
| `LEFT_GRIPPER_CTRL` | Left gripper controller |
| `LEG_PVT_BYPASS_CTRL` | Leg PVT bypass controller |
| `LEG_PVT_CTRL` | Leg PVT controller |
| `RIGHT_ARM_PVT_BYPASS_CTRL` | Right arm PVT bypass controller |
| `RIGHT_ARM_PVT_CTRL` | Right arm PVT controller |
| `RIGHT_DEXHAND_CTRL` | Right dexhand controller |
| `RIGHT_GRIPPER_CTRL` | Right gripper controller |


---

### G1JointGroup {#g1jointgroup-enum}

<small>Galbot G1 joint-group names.

A "joint group" is the SDK's primary control/planning unit, not a single joint: Kinematic-consistent control: commands are validated and executed per chain/end-effector group. Deterministic command ordering: joint_groups are expanded to concrete joint_names in group order. Group-level behavior: each group has its own active/passive attribute and execution tolerance. Recommended usage: Use constants in this struct when filling API parameters such as joint_groups. If exact joint names are needed, query them at runtime via get_joint_names(true, {group_name}) instead of hard-coding. In APIs that accept both joint_groups and joint_names, joint_names takes precedence.</small>

| Enum Value | Description |
| --- | --- |
| `chassis` | Chassis mechanism group (passive in joint-position control). Default joints: chassis_joint1 ... chassis_joint4. Typical use: chassis state grouping; base motion should use base APIs. |
| `head` | Head chain. Default joints: head_joint1, head_joint2. Typical use: gaze/camera orientation. |
| `left_arm` | Left 7-DoF arm chain. Default joints: left_arm_joint1 ... left_arm_joint7. Typical use: left-arm reaching/manipulation. |
| `left_dexhand` | Left dexterous hand group. Default joints: left_dexhand_joint1 ... left_dexhand_joint6. Typical use: multi-finger dexterous manipulation (left). |
| `left_gripper` | Left gripper chain. Default joint: left_gripper_joint1. Typical use: left gripper open/close and grasp width. |
| `left_suction_cup` | Left suction-cup end-effector group. Default joint: left_suction_cup_joint1. Typical use: vacuum pick/place on left arm. |
| `leg` | Leg chain. Default joints: leg_joint1 ... leg_joint5. Typical use: lower-body posture/locomotion-related body control. |
| `right_arm` | Right 7-DoF arm chain. Default joints: right_arm_joint1 ... right_arm_joint7. Typical use: right-arm reaching/manipulation. |
| `right_dexhand` | Right dexterous hand group. Default joints: right_dexhand_joint1 ... right_dexhand_joint6. Typical use: multi-finger dexterous manipulation (right). |
| `right_gripper` | Right gripper chain. Default joint: right_gripper_joint1. Typical use: right gripper open/close and grasp width. |
| `right_suction_cup` | Right suction-cup end-effector group. Default joint: right_suction_cup_joint1. Typical use: vacuum pick/place on right arm. |


---

### GalbotOneFoxtrotSensor {#galbotonefoxtrotsensor-enum}

<small>Force sensor enumeration describing robot wrist force sensors.

Identifies force/torque sensors mounted at the robot's wrist joints for force-controlled manipulation and contact detection.</small>

| Enum Value | Description |
| --- | --- |
| `LEFT_WRIST_FORCE` | Left wrist force/torque sensor, typically 6-axis (3 forces + 3 torques) |
| `RIGHT_WRIST_FORCE` | Right wrist force/torque sensor, typically 6-axis (3 forces + 3 torques) |


---

### GripperState {#gripperstate-class}

<small>Gripper state.

Represents the current state of a parallel-jaw gripper, including opening width, motion status, and grasping force.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `effort` | float | Gripper torque (newton-meters) |
| `is_moving` | bool | Whether currently moving |
| `joint_positions` | list[float] | Joint positions array |
| `timestamp_ns` | int | Timestamp (nanoseconds) |
| `velocity` | float | Gripper velocity (meters/second) |
| `width` | float | Gripper width (meters) |


---

### GroupCommand {#groupcommand-class}

<small>Group-space command at a specific time point.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `joint_commands` | list[[JointCommand](#jointcommand-class)] | Joint commands at this point |
| `time_from_start_s` | float | Time from trajectory start in seconds |


---

### Header {#header-class}

<small>Message header structure.

Standard message header containing timestamp and coordinate frame information. Timestamp is stored as nanoseconds since epoch (unified with other sensor types).</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `frame_id` | str | Frame ID |
| `timestamp_ns` | int | Timestamp (nanoseconds since epoch) |


---

### IKSolverConfig {#iksolverconfig-class}

<small>Inverse kinematics (IK) solver configuration parameters.

This structure configures the numerical inverse kinematics solver used to compute joint configurations that achieve desired end-effector poses. It supports collision-aware IK with configurable seed strategies, convergence tolerances, joint limit handling, and timeout parameters. IK solving is an iterative numerical optimization process that may benefit from multiple random initializations to find feasible collision-free solutions.</small>

#### get_col_aware_ik_joint_limit_bias {#iksolverconfig-get_col_aware_ik_joint_limit_bias-function}

```python
def get_col_aware_ik_joint_limit_bias() -> float
```

<small>Get joint limit safety margin.</small>

**Returns**

| Type | Description |
| --- | --- |
| float | - |

#### get_col_aware_ik_timeout {#iksolverconfig-get_col_aware_ik_timeout-function}

```python
def get_col_aware_ik_timeout() -> float
```

<small>Get collision-aware IK solver timeout.</small>

**Returns**

| Type | Description |
| --- | --- |
| float | - |

#### get_enable_collision_check_log {#iksolverconfig-get_enable_collision_check_log-function}

```python
def get_enable_collision_check_log() -> bool
```

<small>Check if collision check logging is enabled.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | - |

#### get_rotation_eps {#iksolverconfig-get_rotation_eps-function}

```python
def get_rotation_eps() -> list[float]
```

<small>Get orientation error tolerance.</small>

**Returns**

| Type | Description |
| --- | --- |
| list[float] | - |

#### get_seed_type {#iksolverconfig-get_seed_type-function}

```python
def get_seed_type() -> SeedType
```

<small>Get IK solver seed generation strategy.</small>

**Returns**

| Type | Description |
| --- | --- |
| [SeedType](#seedtype-enum) | - |

#### get_translation_eps {#iksolverconfig-get_translation_eps-function}

```python
def get_translation_eps() -> list[float]
```

<small>Get Cartesian position error tolerance.</small>

**Returns**

| Type | Description |
| --- | --- |
| list[float] | - |

#### print {#iksolverconfig-print-function}

```python
def print() -> None
```

<small>Print IK solver configuration to standard output.

Outputs all configuration parameters for debugging and verification.</small>

#### set_col_aware_ik_joint_limit_bias {#iksolverconfig-set_col_aware_ik_joint_limit_bias-function}

```python
def set_col_aware_ik_joint_limit_bias(bias: SupportsFloat) -> None
```

<small>Set safety margin from joint position limits.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `bias` | SupportsFloat | required | - |

!!! note
    Prevents IK solver from proposing configurations near singularities or mechanical limits

#### set_col_aware_ik_timeout {#iksolverconfig-set_col_aware_ik_timeout-function}

```python
def set_col_aware_ik_timeout(timeout: SupportsFloat) -> None
```

<small>Set timeout for collision-aware IK solver.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `timeout` | SupportsFloat | required | - |

!!! note
    Longer timeouts allow more seed attempts but delay planning

#### set_enable_collision_check_log {#iksolverconfig-set_enable_collision_check_log-function}

```python
def set_enable_collision_check_log(enable: bool) -> None
```

<small>Enable or disable detailed collision checking diagnostic logs.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `enable` | bool | required | - |

!!! note
    Useful for debugging IK failures due to collision constraints

#### set_rotation_eps {#iksolverconfig-set_rotation_eps-function}

```python
def set_rotation_eps(eps: list[float]) -> None
```

<small>Set orientation error tolerance for IK convergence.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `eps` | list[float] | required | - |

!!! note
    IK solution is accepted when orientation error is within this threshold

#### set_seed_type {#iksolverconfig-set_seed_type-function}

```python
def set_seed_type(type: SeedType) -> None
```

<small>Set initial configuration seed generation strategy.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `type` | [SeedType](#seedtype-enum) | required | - |

#### set_translation_eps {#iksolverconfig-set_translation_eps-function}

```python
def set_translation_eps(eps: list[float]) -> None
```

<small>Set Cartesian position error tolerance for IK convergence.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `eps` | list[float] | required | - |

!!! note
    IK solution is accepted when position error is within this threshold


---

### ImuData {#imudata-class}

<small>IMU data structure.

Contains timestamped data from an Inertial Measurement Unit (IMU), including accelerometer, gyroscope, and magnetometer measurements.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `accel` | [Vector3](#vector3-class) | Acceleration Vector3 |
| `gyro` | [Vector3](#vector3-class) | Gyroscope Vector3 |
| `magnet` | [Vector3](#vector3-class) | Magnetometer Vector3 |
| `timestamp_ns` | int | Timestamp (nanoseconds) |


---

### JointCommand {#jointcommand-class}

<small>Single joint control command.

Specifies desired motion parameters for a single robot joint in a trajectory or control command.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `acceleration` | float | - `acceleration` (`float`): Joint acceleration |
| `effort` | float | - `effort` (`float`): Joint torque (N·m) |
| `position` | float | - `position` (`float`): Joint target position (radians) |
| `velocity` | float | - `velocity` (`float`): Joint velocity (radians/second) |


---

### JointState {#jointstate-class}

<small>Single joint state structure.

Represents the complete real-time state of a single robot joint, including kinematic quantities (position, velocity, acceleration) and dynamic quantities (torque/effort and motor current).</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `acceleration` | float | - |
| `current` | float | - |
| `effort` | float | - |
| `position` | float | - |
| `velocity` | float | - |


---

### JointStateMessage {#jointstatemessage-class}

<small>Joint state message structure.

Timestamped collection of joint states for multiple joints, typically representing a snapshot of the robot's complete joint configuration at one instant.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `joint_state_vec` | list[[JointState](#jointstate-class)] | Joint state list |
| `timestamp_ns` | int | Timestamp (nanoseconds) |


---

### JointStates {#jointstates-class}

<small>Joint-space target specification.

Represents target joint configuration for a kinematic chain. Extends RobotStates to specify joint-based motion goals. Used in joint trajectory planning and forward kinematics computation. All joint angles must be in radians. Vector size must match the DOF of the specified kinematic chain.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `joint_positions` | list[float] | - |

#### get_type {#jointstates-get_type-function}

```python
def get_type() -> RobotStatesType
```

<small>Get runtime type identifier.</small>

**Returns**

| Type | Description |
| --- | --- |
| [RobotStatesType](#robotstatestype-enum) | - |

#### set_joint {#jointstates-set_joint-function}

```python
def set_joint(index: SupportsInt, val: SupportsInt) -> None
```

<small>Set individual joint angle by index.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `index` | SupportsInt | required | - |
| `val` | SupportsInt | required | - |

!!! note
    Function performs bounds checking; invalid indices are silently ignored.

!!! warning
    No error is returned for out-of-bounds access; ensure index validity externally.

#### set_joint_positions {#jointstates-set_joint_positions-function}

```python
def set_joint_positions(joints: list[float]) -> None
```

<small>Set complete joint configuration for the kinematic chain.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `joints` | list[float] | required | - |

!!! note
    Vector size should equal the number of actuated joints in the specified chain.


---

### KinematicsBoundary {#kinematicsboundary-class}

<small>Kinematic boundary parameters for robot kinematic chain joints.

This structure defines the kinematic constraints for a robot kinematic chain (e.g., manipulator arms, mobile base, or leg chains). It specifies position, velocity, acceleration, and jerk limits for each joint in the chain. These boundaries are critical for ensuring safe and physically feasible motion during trajectory planning and execution. Each vector should contain one value per joint in the kinematic chain. All joint space quantities are specified in radians or radians per unit time.</small>

#### get_acc_lower_limit {#kinematicsboundary-get_acc_lower_limit-function}

```python
def get_acc_lower_limit() -> list[float]
```

<small>Get joint acceleration lower bounds.</small>

**Returns**

| Type | Description |
| --- | --- |
| list[float] | - |

#### get_acc_upper_limit {#kinematicsboundary-get_acc_upper_limit-function}

```python
def get_acc_upper_limit() -> list[float]
```

<small>Get joint acceleration upper bounds.</small>

**Returns**

| Type | Description |
| --- | --- |
| list[float] | - |

#### get_chain_name {#kinematicsboundary-get_chain_name-function}

```python
def get_chain_name() -> str
```

<small>Get the kinematic chain name identifier.</small>

**Returns**

| Type | Description |
| --- | --- |
| str | - |

#### get_jerk_lower_limit {#kinematicsboundary-get_jerk_lower_limit-function}

```python
def get_jerk_lower_limit() -> list[float]
```

<small>Get joint jerk lower bounds.</small>

**Returns**

| Type | Description |
| --- | --- |
| list[float] | - |

#### get_jerk_upper_limit {#kinematicsboundary-get_jerk_upper_limit-function}

```python
def get_jerk_upper_limit() -> list[float]
```

<small>Get joint jerk upper bounds.</small>

**Returns**

| Type | Description |
| --- | --- |
| list[float] | - |

#### get_lower_limit {#kinematicsboundary-get_lower_limit-function}

```python
def get_lower_limit() -> list[float]
```

<small>Get joint position lower bounds.</small>

**Returns**

| Type | Description |
| --- | --- |
| list[float] | - |

#### get_upper_limit {#kinematicsboundary-get_upper_limit-function}

```python
def get_upper_limit() -> list[float]
```

<small>Get joint position upper bounds.</small>

**Returns**

| Type | Description |
| --- | --- |
| list[float] | - |

#### get_vel_lower_limit {#kinematicsboundary-get_vel_lower_limit-function}

```python
def get_vel_lower_limit() -> list[float]
```

<small>Get joint velocity lower bounds.</small>

**Returns**

| Type | Description |
| --- | --- |
| list[float] | - |

#### get_vel_upper_limit {#kinematicsboundary-get_vel_upper_limit-function}

```python
def get_vel_upper_limit() -> list[float]
```

<small>Get joint velocity upper bounds.</small>

**Returns**

| Type | Description |
| --- | --- |
| list[float] | - |

#### print {#kinematicsboundary-print-function}

```python
def print() -> None
```

<small>Print kinematic boundary information to standard output.

Outputs all boundary parameters for debugging and visualization purposes.</small>

#### set_acc_lower_limit {#kinematicsboundary-set_acc_lower_limit-function}

```python
def set_acc_lower_limit(limits: list[float]) -> None
```

<small>Set joint acceleration lower bounds.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `limits` | list[float] | required | - |

!!! note
    Used for trajectory optimization and smoothness constraints

#### set_acc_upper_limit {#kinematicsboundary-set_acc_upper_limit-function}

```python
def set_acc_upper_limit(limits: list[float]) -> None
```

<small>Set joint acceleration upper bounds.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `limits` | list[float] | required | - |

!!! note
    Used for trajectory optimization and smoothness constraints

#### set_chain_name {#kinematicsboundary-set_chain_name-function}

```python
def set_chain_name(name: str) -> None
```

<small>Set the name identifier for this kinematic chain.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `name` | str | required | - |

#### set_jerk_lower_limit {#kinematicsboundary-set_jerk_lower_limit-function}

```python
def set_jerk_lower_limit(limits: list[float]) -> None
```

<small>Set joint jerk lower bounds.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `limits` | list[float] | required | - |

!!! note
    Jerk constraints improve motion smoothness and reduce mechanical wear

#### set_jerk_upper_limit {#kinematicsboundary-set_jerk_upper_limit-function}

```python
def set_jerk_upper_limit(limits: list[float]) -> None
```

<small>Set joint jerk upper bounds.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `limits` | list[float] | required | - |

!!! note
    Jerk constraints improve motion smoothness and reduce mechanical wear

#### set_lower_limit {#kinematicsboundary-set_lower_limit-function}

```python
def set_lower_limit(limits: list[float]) -> None
```

<small>Set joint position lower bounds.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `limits` | list[float] | required | - |

!!! note
    Vector size must equal the number of joints in the chain

#### set_upper_limit {#kinematicsboundary-set_upper_limit-function}

```python
def set_upper_limit(limits: list[float]) -> None
```

<small>Set joint position upper bounds.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `limits` | list[float] | required | - |

!!! note
    Vector size must equal the number of joints in the chain

#### set_vel_lower_limit {#kinematicsboundary-set_vel_lower_limit-function}

```python
def set_vel_lower_limit(limits: list[float]) -> None
```

<small>Set joint velocity lower bounds.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `limits` | list[float] | required | - |

!!! note
    Typically negative values for bidirectional joints

#### set_vel_upper_limit {#kinematicsboundary-set_vel_upper_limit-function}

```python
def set_vel_upper_limit(limits: list[float]) -> None
```

<small>Set joint velocity upper bounds.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `limits` | list[float] | required | - |

!!! note
    Typically positive values for bidirectional joints


---

### LidarData {#lidardata-class}

<small>Lidar data structure.

Generic N-dimensional point cloud structure compatible with ROS 2 sensor_msgs/PointCloud2. Stores point data as a binary blob with field descriptors defining the data layout. Supports both ordered (structured) and unordered (unstructured) point clouds.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `data` | list[int] | Point cloud binary data |
| `fields` | list[[PointField](#pointfield-class)] | Point field description list |
| `header` | [Header](#header-class) | Message header |
| `height` | int | Point cloud height |
| `is_bigendian` | bool | Whether big-endian |
| `is_dense` | bool | Whether dense |
| `point_step` | int | Bytes per point |
| `row_step` | int | Bytes per row |
| `width` | int | Point cloud width |


---

### LineTrajCheckPrimitive {#linetrajcheckprimitive-class}

<small>Geometric primitive configuration for Cartesian linear trajectory validation.

This structure configures the collision detection geometric representation for linear end-effector trajectories in Cartesian space. It supports two primitive types: infinitesimally thin lines and swept-volume cylinders. Choosing the appropriate primitive affects collision detection conservativeness and computational cost. Cylinder primitives model the robot's actual swept volume more accurately but require more expensive geometric queries.</small>

#### get_cylinder_prim_radius {#linetrajcheckprimitive-get_cylinder_prim_radius-function}

```python
def get_cylinder_prim_radius() -> float
```

<small>Get the cylinder primitive swept-volume radius.</small>

**Returns**

| Type | Description |
| --- | --- |
| float | - |

#### get_line_check_primitive_type {#linetrajcheckprimitive-get_line_check_primitive_type-function}

```python
def get_line_check_primitive_type() -> PrimitiveType
```

<small>Get the geometric primitive type for trajectory checking.</small>

**Returns**

| Type | Description |
| --- | --- |
| [PrimitiveType](#primitivetype-enum) | - |

#### get_line_prim_curvature {#linetrajcheckprimitive-get_line_prim_curvature-function}

```python
def get_line_prim_curvature() -> float
```

<small>Get the line primitive curvature approximation tolerance.</small>

**Returns**

| Type | Description |
| --- | --- |
| float | - |

#### print {#linetrajcheckprimitive-print-function}

```python
def print() -> None
```

<small>Print line trajectory check primitive configuration to standard output.

Outputs selected primitive type and associated parameters for debugging.</small>

#### set_cylinder_prim_radius {#linetrajcheckprimitive-set_cylinder_prim_radius-function}

```python
def set_cylinder_prim_radius(radius: SupportsFloat) -> None
```

<small>Set swept-volume cylinder radius for trajectory collision checking.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `radius` | SupportsFloat | required | - |

!!! note
    Larger radii increase safety margins but may be overly conservative

!!! note
    Only applies when primitive type is CYLINDER

#### set_line_check_primitive_type {#linetrajcheckprimitive-set_line_check_primitive_type-function}

```python
def set_line_check_primitive_type(type: PrimitiveType) -> None
```

<small>Set geometric primitive type for linear trajectory validation.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `type` | [PrimitiveType](#primitivetype-enum) | required | - |

!!! note
    CYLINDER is recommended for safety-critical applications

#### set_line_prim_curvature {#linetrajcheckprimitive-set_line_prim_curvature-function}

```python
def set_line_prim_curvature(curvature: SupportsFloat) -> None
```

<small>Set curvature approximation tolerance for line primitive.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `curvature` | SupportsFloat | required | - |

!!! note
    Controls how finely curved paths are discretized into line segments

!!! note
    Lower values improve accuracy but increase computational cost


---

### LogLevel {#loglevel-enum}

<small>Log level enumeration.

Represents the severity level of log messages.</small>

| Enum Value | Description |
| --- | --- |
| `CRITICAL` | Critical level, severe error events that lead to application termination |
| `DEBUG` | Debug level, diagnostic information for developers |
| `ERROR` | Error level, error events that might still allow the application to continue running |
| `INFO` | Info level, general operational messages |
| `TRACE` | Trace level, detailed information for debugging |
| `WARN` | Warn level, potentially harmful situations |


---

### MachineType {#machinetype-enum}

<small>Supported robot machine types.

This enumeration defines the different robot platforms or machine types supported by the Galbot SDK. Clients can use these values to specify which robot model they are working with, particularly for factory methods that return platform-specific implementations. Keeping the enumeration in the common type definitions ensures consistency across the SDK while hiding implementation details in the respective modules.</small>

| Enum Value | Description |
| --- | --- |
| `G1` | Galbot G1 humanoid robot platform |
| `S1` | Galbot S1 humanoid robot platform |


---

### MotionPlanConfig {#motionplanconfig-class}

<small>Comprehensive motion planning configuration management.

MotionPlanConfig serves as a centralized configuration container for all motion planning subsystems. It aggregates sampling strategies, trajectory generation parameters, inverse kinematics solver settings, collision detection options, feasibility validation criteria, and kinematic constraint boundaries. This class provides a unified interface for configuring complex motion planning pipelines, supporting both simple manipulator planning and whole-body humanoid motion generation with multiple kinematic chains. Configuration objects are lazily initialized and managed through shared pointers to optimize memory usage and support optional feature configuration.</small>

#### create_collision_check_option {#motionplanconfig-create_collision_check_option-function}

```python
def create_collision_check_option() -> CollisionCheckOption
```

<small>Create or retrieve collision check option configuration.

Lazily initializes the collision check options if they do not exist.</small>

**Returns**

| Type | Description |
| --- | --- |
| [CollisionCheckOption](#collisioncheckoption-class) | - |

#### create_ik_solver_config {#motionplanconfig-create_ik_solver_config-function}

```python
def create_ik_solver_config() -> IKSolverConfig
```

<small>Create or retrieve inverse kinematics solver configuration.

Lazily initializes the IK solver configuration if it does not exist.</small>

**Returns**

| Type | Description |
| --- | --- |
| [IKSolverConfig](#iksolverconfig-class) | - |

#### create_line_traj_check_primitive {#motionplanconfig-create_line_traj_check_primitive-function}

```python
def create_line_traj_check_primitive() -> LineTrajCheckPrimitive
```

<small>Create or retrieve line trajectory check primitive configuration.

Lazily initializes the line trajectory check primitive configuration if it does not exist.</small>

**Returns**

| Type | Description |
| --- | --- |
| [LineTrajCheckPrimitive](#linetrajcheckprimitive-class) | - |

#### create_sampler_config {#motionplanconfig-create_sampler_config-function}

```python
def create_sampler_config() -> SamplerConfig
```

<small>Create or retrieve sampler configuration.

Lazily initializes the sampler configuration if it does not exist. Safe to call multiple times; returns the same instance after first creation.</small>

**Returns**

| Type | Description |
| --- | --- |
| [SamplerConfig](#samplerconfig-class) | - |

#### create_trajectory_feasibility_check_option {#motionplanconfig-create_trajectory_feasibility_check_option-function}

```python
def create_trajectory_feasibility_check_option() -> TrajectoryFeasibilityCheckOption
```

<small>Create or retrieve trajectory feasibility check option configuration.

Lazily initializes the trajectory feasibility check options if they do not exist.</small>

**Returns**

| Type | Description |
| --- | --- |
| [TrajectoryFeasibilityCheckOption](#trajectoryfeasibilitycheckoption-class) | - |

#### create_trajectory_plan_config {#motionplanconfig-create_trajectory_plan_config-function}

```python
def create_trajectory_plan_config() -> TrajectoryPlanConfig
```

<small>Create or retrieve trajectory planning configuration.

Lazily initializes the trajectory planning configuration if it does not exist.</small>

**Returns**

| Type | Description |
| --- | --- |
| [TrajectoryPlanConfig](#trajectoryplanconfig-class) | - |

#### get_collision_check_option {#motionplanconfig-get_collision_check_option-function}

```python
def get_collision_check_option() -> CollisionCheckOption
```

<small>Get collision check option configuration (may be nullptr if not initialized)</small>

**Returns**

| Type | Description |
| --- | --- |
| [CollisionCheckOption](#collisioncheckoption-class) | - |

!!! note
    Use create_collision_check_option() to ensure a valid configuration exists

#### get_collision_check_option_ref {#motionplanconfig-get_collision_check_option_ref-function}

```python
def get_collision_check_option_ref() -> CollisionCheckOption
```

<small>Get mutable reference to collision check option configuration.

Lazily creates a new collision check option with default values if not already initialized.</small>

**Returns**

| Type | Description |
| --- | --- |
| [CollisionCheckOption](#collisioncheckoption-class) | - |

#### get_feasibility_boundary {#motionplanconfig-get_feasibility_boundary-function}

```python
def get_feasibility_boundary() -> list[KinematicsBoundary]
```

<small>Get kinematic feasibility boundaries for all chains (mutable)

Returns mutable access to the feasibility boundary configuration for in-place modification.</small>

**Returns**

| Type | Description |
| --- | --- |
| list[[KinematicsBoundary](#kinematicsboundary-class)] | - |

#### get_hard_joint_limit {#motionplanconfig-get_hard_joint_limit-function}

```python
def get_hard_joint_limit() -> list[KinematicsBoundary]
```

<small>Get hard joint limits (mutable)</small>

**Returns**

| Type | Description |
| --- | --- |
| list[[KinematicsBoundary](#kinematicsboundary-class)] | - |

#### get_ik_joint_limit {#motionplanconfig-get_ik_joint_limit-function}

```python
def get_ik_joint_limit() -> list[KinematicsBoundary]
```

<small>Get IK phase joint limits (mutable)</small>

**Returns**

| Type | Description |
| --- | --- |
| list[[KinematicsBoundary](#kinematicsboundary-class)] | - |

#### get_ik_solver_config {#motionplanconfig-get_ik_solver_config-function}

```python
def get_ik_solver_config() -> IKSolverConfig
```

<small>Get inverse kinematics solver configuration (may be nullptr if not initialized)</small>

**Returns**

| Type | Description |
| --- | --- |
| [IKSolverConfig](#iksolverconfig-class) | - |

!!! note
    Use create_ik_solver_config() to ensure a valid configuration exists

#### get_ik_solver_config_ref {#motionplanconfig-get_ik_solver_config_ref-function}

```python
def get_ik_solver_config_ref() -> IKSolverConfig
```

<small>Get mutable reference to inverse kinematics solver configuration.

Lazily creates a new IK solver configuration with default values if not already initialized.</small>

**Returns**

| Type | Description |
| --- | --- |
| [IKSolverConfig](#iksolverconfig-class) | - |

#### get_line_traj_check_primitive {#motionplanconfig-get_line_traj_check_primitive-function}

```python
def get_line_traj_check_primitive() -> LineTrajCheckPrimitive
```

<small>Get line trajectory check primitive configuration (may be nullptr if not initialized)</small>

**Returns**

| Type | Description |
| --- | --- |
| [LineTrajCheckPrimitive](#linetrajcheckprimitive-class) | - |

!!! note
    Use create_line_traj_check_primitive() to ensure a valid configuration exists

#### get_line_traj_check_primitive_ref {#motionplanconfig-get_line_traj_check_primitive_ref-function}

```python
def get_line_traj_check_primitive_ref() -> LineTrajCheckPrimitive
```

<small>Get mutable reference to line trajectory check primitive configuration.

Lazily creates a new line trajectory check primitive with default values if not already initialized.</small>

**Returns**

| Type | Description |
| --- | --- |
| [LineTrajCheckPrimitive](#linetrajcheckprimitive-class) | - |

#### get_revert_ik_joint_limit {#motionplanconfig-get_revert_ik_joint_limit-function}

```python
def get_revert_ik_joint_limit() -> bool
```

<small>Check if IK joint limit reversion is enabled.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | - |

#### get_revert_ik_joint_limit_chains {#motionplanconfig-get_revert_ik_joint_limit_chains-function}

```python
def get_revert_ik_joint_limit_chains() -> list[str]
```

<small>Get kinematic chains for selective IK joint limit reversion (mutable)</small>

**Returns**

| Type | Description |
| --- | --- |
| list[str] | - |

#### get_sampler_config {#motionplanconfig-get_sampler_config-function}

```python
def get_sampler_config() -> SamplerConfig
```

<small>Get sampler configuration (may be nullptr if not initialized)</small>

**Returns**

| Type | Description |
| --- | --- |
| [SamplerConfig](#samplerconfig-class) | - |

!!! note
    Use create_sampler_config() to ensure a valid configuration exists

#### get_sampler_config_ref {#motionplanconfig-get_sampler_config_ref-function}

```python
def get_sampler_config_ref() -> SamplerConfig
```

<small>Get mutable reference to sampler configuration.

Lazily creates a new sampler configuration with default values if not already initialized. Useful for in-place modification of configuration parameters.</small>

**Returns**

| Type | Description |
| --- | --- |
| [SamplerConfig](#samplerconfig-class) | - |

#### get_sampler_joint_limit {#motionplanconfig-get_sampler_joint_limit-function}

```python
def get_sampler_joint_limit() -> list[KinematicsBoundary]
```

<small>Get sampling phase joint limits (mutable)</small>

**Returns**

| Type | Description |
| --- | --- |
| list[[KinematicsBoundary](#kinematicsboundary-class)] | - |

#### get_trajectory_feasibility_check_option {#motionplanconfig-get_trajectory_feasibility_check_option-function}

```python
def get_trajectory_feasibility_check_option() -> TrajectoryFeasibilityCheckOption
```

<small>Get trajectory feasibility check option configuration (may be nullptr if not initialized)</small>

**Returns**

| Type | Description |
| --- | --- |
| [TrajectoryFeasibilityCheckOption](#trajectoryfeasibilitycheckoption-class) | - |

!!! note
    Use create_trajectory_feasibility_check_option() to ensure a valid configuration exists

#### get_trajectory_feasibility_check_option_ref {#motionplanconfig-get_trajectory_feasibility_check_option_ref-function}

```python
def get_trajectory_feasibility_check_option_ref() -> TrajectoryFeasibilityCheckOption
```

<small>Get mutable reference to trajectory feasibility check option configuration.

Lazily creates a new trajectory feasibility check option with default values if not already initialized.</small>

**Returns**

| Type | Description |
| --- | --- |
| [TrajectoryFeasibilityCheckOption](#trajectoryfeasibilitycheckoption-class) | - |

#### get_trajectory_plan_config {#motionplanconfig-get_trajectory_plan_config-function}

```python
def get_trajectory_plan_config() -> TrajectoryPlanConfig
```

<small>Get trajectory planning configuration (may be nullptr if not initialized)</small>

**Returns**

| Type | Description |
| --- | --- |
| [TrajectoryPlanConfig](#trajectoryplanconfig-class) | - |

!!! note
    Use create_trajectory_plan_config() to ensure a valid configuration exists

#### get_trajectory_plan_config_ref {#motionplanconfig-get_trajectory_plan_config_ref-function}

```python
def get_trajectory_plan_config_ref() -> TrajectoryPlanConfig
```

<small>Get mutable reference to trajectory planning configuration.

Lazily creates a new trajectory planning configuration with default values if not already initialized.</small>

**Returns**

| Type | Description |
| --- | --- |
| [TrajectoryPlanConfig](#trajectoryplanconfig-class) | - |

#### get_update_time {#motionplanconfig-get_update_time-function}

```python
def get_update_time() -> int
```

<small>Get configuration update timestamp.</small>

**Returns**

| Type | Description |
| --- | --- |
| int | - |

#### print {#motionplanconfig-print-function}

```python
def print() -> None
```

<small>Print comprehensive motion planning configuration to standard output.

Outputs all sub-configuration parameters and kinematic boundaries in human-readable format. Useful for debugging, logging, and verification of configuration state.</small>

#### set_collision_check_option {#motionplanconfig-set_collision_check_option-function}

```python
def set_collision_check_option(option: CollisionCheckOption) -> None
```

<small>Set or replace collision check option configuration.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `option` | [CollisionCheckOption](#collisioncheckoption-class) | required | - |

#### set_feasibility_boundary {#motionplanconfig-set_feasibility_boundary-function}

```python
def set_feasibility_boundary(boundary: Sequence[KinematicsBoundary]) -> None
```

<small>Set kinematic feasibility boundaries for all chains.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `boundary` | Sequence[[KinematicsBoundary](#kinematicsboundary-class)] | required | - |

!!! note
    These boundaries are used for general trajectory feasibility validation

#### set_hard_joint_limit {#motionplanconfig-set_hard_joint_limit-function}

```python
def set_hard_joint_limit(boundary: Sequence[KinematicsBoundary]) -> None
```

<small>Set absolute hard joint limits (safety-critical boundaries)</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `boundary` | Sequence[[KinematicsBoundary](#kinematicsboundary-class)] | required | - |

!!! note
    Hard limits must never be violated; typically correspond to physical joint stops

#### set_ik_joint_limit {#motionplanconfig-set_ik_joint_limit-function}

```python
def set_ik_joint_limit(boundary: Sequence[KinematicsBoundary]) -> None
```

<small>Set joint limits used during IK solving phase.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `boundary` | Sequence[[KinematicsBoundary](#kinematicsboundary-class)] | required | - |

!!! note
    IK limits may be tighter than hard limits to improve convergence and avoid singularities

#### set_ik_solver_config {#motionplanconfig-set_ik_solver_config-function}

```python
def set_ik_solver_config(config: IKSolverConfig) -> None
```

<small>Set or replace inverse kinematics solver configuration.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `config` | [IKSolverConfig](#iksolverconfig-class) | required | - |

#### set_line_traj_check_primitive {#motionplanconfig-set_line_traj_check_primitive-function}

```python
def set_line_traj_check_primitive(primitive: LineTrajCheckPrimitive) -> None
```

<small>Set or replace line trajectory check primitive configuration.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `primitive` | [LineTrajCheckPrimitive](#linetrajcheckprimitive-class) | required | - |

#### set_revert_ik_joint_limit {#motionplanconfig-set_revert_ik_joint_limit-function}

```python
def set_revert_ik_joint_limit(flag: bool) -> None
```

<small>Enable or disable IK joint limit reversion to hard limits.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `flag` | bool | required | - |

!!! note
    Useful for recovering from constrained configurations by temporarily relaxing IK limits

#### set_revert_ik_joint_limit_chains {#motionplanconfig-set_revert_ik_joint_limit_chains-function}

```python
def set_revert_ik_joint_limit_chains(chains: Sequence[str]) -> None
```

<small>Set specific kinematic chains for IK joint limit reversion.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `chains` | Sequence[str] | required | - |

!!! note
    If non-empty, automatically enables revert_ik_joint_limit flag

!!! note
    Empty vector disables selective reversion (applies to all chains if flag is set)

#### set_sampler_config {#motionplanconfig-set_sampler_config-function}

```python
def set_sampler_config(config: SamplerConfig) -> None
```

<small>Set or replace sampler configuration.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `config` | [SamplerConfig](#samplerconfig-class) | required | - |

#### set_sampler_joint_limit {#motionplanconfig-set_sampler_joint_limit-function}

```python
def set_sampler_joint_limit(boundary: Sequence[KinematicsBoundary]) -> None
```

<small>Set joint limits used during sampling-based planning phase.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `boundary` | Sequence[[KinematicsBoundary](#kinematicsboundary-class)] | required | - |

!!! note
    Sampling limits define the valid configuration space for exploration

#### set_trajectory_feasibility_check_option {#motionplanconfig-set_trajectory_feasibility_check_option-function}

```python
def set_trajectory_feasibility_check_option(option: TrajectoryFeasibilityCheckOption) -> None
```

<small>Set or replace trajectory feasibility check option configuration.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `option` | [TrajectoryFeasibilityCheckOption](#trajectoryfeasibilitycheckoption-class) | required | - |

#### set_trajectory_plan_config {#motionplanconfig-set_trajectory_plan_config-function}

```python
def set_trajectory_plan_config(config: TrajectoryPlanConfig) -> None
```

<small>Set or replace trajectory planning configuration.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `config` | [TrajectoryPlanConfig](#trajectoryplanconfig-class) | required | - |

#### set_update_time {#motionplanconfig-set_update_time-function}

```python
def set_update_time(t: SupportsInt) -> None
```

<small>Set configuration update timestamp.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `t` | SupportsInt | required | - |

!!! note
    Used for configuration versioning and cache invalidation


---

### MotionStatus {#motionstatus-enum}

<small>Robot motion execution status enumeration.

Represents the execution status of robot motion commands, including trajectory following, pose reaching, and other motion planning operations.</small>

| Enum Value | Description |
| --- | --- |
| `COMM_DISCONNECTED` | Communication disconnected or control node unavailable |
| `DATA_FETCH_FAILED` | Data retrieval failed, e.g., sensor or state reading failure |
| `FAULT` | Fault occurred, motion cannot continue due to hardware or safety issue |
| `INIT_FAILED` | Internal initialization failed, communication component or resource creation failed |
| `INVALID_INPUT` | Input parameters invalid or not meeting interface requirements |
| `IN_PROGRESS` | Motion in progress but has not reached target yet |
| `PUBLISH_FAIL` | Data transmission or command delivery failed, motion command may not be executed |
| `STATUS_NUM` | Total number of status enumerations (for boundary checking or array sizing) |
| `STOPPED_UNREACHED` | Stopped during motion without reaching target position/pose |
| `SUCCESS` | Execution succeeded, motion reached expected target position/pose |
| `TIMEOUT` | Execution timeout, motion not completed within specified time limit |
| `UNSUPPORTED_FUNCRION` | Function not yet supported, called interface or operation not implemented (note: typo in enum name preserved for API compatibility) |


---

### NavigationTaskStatus {#navigationtaskstatus-enum}

<small>Navigation task current state enumeration.

Represents the current state of an active or completed navigation task, as reported by the navigation system. Used for polling during non-blocking navigation to detect RUNNING, SUCCESS, or FAILED and exit error logic in time.</small>

| Enum Value | Description |
| --- | --- |
| `FAILED` | Navigation task failed |
| `RUNNING` | Navigation task is in progress |
| `SUCCESS` | Navigation task completed successfully |
| `UNKNOWN` | Task state unknown or not yet reported |


---

### OdomData {#odomdata-class}

<small>Odometry data.

Contains robot pose and velocity estimates from odometry sources (wheel encoders, IMU fusion, etc.). Used for robot localization and navigation.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `angular_velocity` | list[float] | Angular velocity [wx, wy, wz] (radians/second) |
| `linear_velocity` | list[float] | Linear velocity [vx, vy, vz] (meters/second) |
| `orientation` | list[float] | Orientation quaternion [x, y, z, w] |
| `position` | list[float] | Position [x, y, z] (meters) |
| `timestamp_ns` | int | Timestamp (nanoseconds) |


---

### Parameter {#parameter-class}

<small>Motion planning parameter configuration class.

This class extends PlannerConfig to provide comprehensive configuration options for whole-body motion planning and execution. It encapsulates execution mode, actuation type, tool frame handling, collision checking, and coordinate frame specifications. All angular parameters are expected in radians, linear parameters in meters (SI units).</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `joint_state` | dict[str, list[float]] | - |
| `timeout_second` | float | - |

#### get_actuate_type {#parameter-get_actuate_type-function}

```python
def get_actuate_type() -> str
```

<small>Get actuation type as string.

Performs reverse lookup in g_actuate_type_map to convert enum to string key.</small>

**Returns**

| Type | Description |
| --- | --- |
| str | - |

#### get_blocking {#parameter-get_blocking-function}

```python
def get_blocking() -> bool
```

<small>Get blocking execution mode status.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | - |

#### get_check_collision {#parameter-get_check_collision-function}

```python
def get_check_collision() -> bool
```

<small>Get collision checking status.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | - |

#### get_direct_execute {#parameter-get_direct_execute-function}

```python
def get_direct_execute() -> bool
```

<small>Get direct execution mode status.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | - |

#### get_reference_frame {#parameter-get_reference_frame-function}

```python
def get_reference_frame() -> str
```

<small>Get reference frame name.</small>

**Returns**

| Type | Description |
| --- | --- |
| str | - |

#### get_timeout {#parameter-get_timeout-function}

```python
def get_timeout() -> float
```

<small>Get motion execution timeout value.</small>

**Returns**

| Type | Description |
| --- | --- |
| float | - |

#### get_tool_pose {#parameter-get_tool_pose-function}

```python
def get_tool_pose() -> bool
```

<small>Get tool coordinate frame usage status.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | - |

#### set_actuate {#parameter-set_actuate-function}

```python
def set_actuate(actuate: str) -> None
```

<small>Set actuation type for whole-body coordination.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `actuate` | str | required | - |

!!! warning
    Must be a valid key in g_actuate_type_map, otherwise behavior is undefined.

#### set_blocking {#parameter-set_blocking-function}

```python
def set_blocking(blocking: bool) -> None
```

<small>Set blocking execution mode.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `blocking` | bool | required | - |

#### set_check_collision {#parameter-set_check_collision-function}

```python
def set_check_collision(check_collision: bool) -> None
```

<small>Enable or disable collision checking.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `check_collision` | bool | required | - |

!!! warning
    Disabling collision checking may result in unsafe trajectories.

#### set_direct_execute {#parameter-set_direct_execute-function}

```python
def set_direct_execute(direct_execute: bool) -> None
```

<small>Set direct execution mode.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `direct_execute` | bool | required | - |

#### set_move_line {#parameter-set_move_line-function}

```python
def set_move_line(move_line: bool) -> None
```

<small>Set Cartesian linear motion mode.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `move_line` | bool | required | - |

!!! note
    Linear motion provides predictable Cartesian paths but may have joint velocity discontinuities.

#### set_reference_frame {#parameter-set_reference_frame-function}

```python
def set_reference_frame(frame: str) -> None
```

<small>Set the reference frame for pose specifications.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `frame` | str | required | - |

!!! note
    Must be a valid frame in the robot's TF tree.

#### set_timeout {#parameter-set_timeout-function}

```python
def set_timeout(timeout: SupportsFloat) -> None
```

<small>Set motion execution timeout.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `timeout` | SupportsFloat | required | - |

!!! note
    Only applies when blocking mode is enabled.

#### set_tool_pose {#parameter-set_tool_pose-function}

```python
def set_tool_pose(tool_pose: bool) -> None
```

<small>Set tool coordinate frame usage.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `tool_pose` | bool | required | - |


---

### PerceptionModule {#perceptionmodule-enum}

<small>Enabled perception pipelines (model sets loaded at init).</small>

| Enum Value | Description |
| --- | --- |
| `FOUNDATION_STEREO` | High-precision stereo depth |
| `LIGHT_STEREO` | Lightweight stereo depth |


---

### Point {#point-class}

<small>3D point

Represents a position in three-dimensional Cartesian space.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `x` | float | - |
| `y` | float | - |
| `z` | float | - |


---

### PointField {#pointfield-class}

<small>Point cloud field descriptor.

Describes one data field in a PointCloud2 point structure, defining its name, type, offset, and count. Compatible with ROS 2 sensor_msgs/PointField.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `count` | int | Number of field elements |
| `datatype` | ... | Data type (DataType enum) |
| `offset` | int | Byte offset of field in a single point |


---

### PointFieldDataType {#pointfielddatatype-enum}

<small>Data type enumeration.

Defines primitive data types for point cloud fields, determining byte size and interpretation method for each field value.</small>

| Enum Value | Description |
| --- | --- |
| `FLOAT32` | 32-bit IEEE 754 floating point (4 bytes) |
| `FLOAT64` | 64-bit IEEE 754 floating point (8 bytes) |
| `INT16` | 16-bit signed integer (2 bytes) |
| `INT32` | 32-bit signed integer (4 bytes) |
| `INT8` | 8-bit signed integer (1 byte) |
| `UINT16` | 16-bit unsigned integer (2 bytes) |
| `UINT32` | 32-bit unsigned integer (4 bytes) |
| `UINT8` | 8-bit unsigned integer (1 byte) |
| `UNKNOWN` | Unknown or unspecified type |


---

### Pose {#pose-class}

<small>Pose (position + orientation) structure.

Represents a full 6-DOF (Degrees of Freedom) pose in 3D space, combining position (translation) and orientation (rotation) information. Commonly used for robot end-effector poses, object poses, and coordinate frame transforms.</small>


---

### PoseState {#posestate-class}

<small>Cartesian pose target specification.

Represents a target end-effector pose in Cartesian space (SE(3)). Extends RobotStates to specify pose-based motion goals for kinematic chains. Used in inverse kinematics and Cartesian trajectory planning. Pose values: position in meters, orientation as unit quaternion. Coordinate frames must exist in the robot's TF tree.</small>

#### get_type {#posestate-get_type-function}

```python
def get_type() -> RobotStatesType
```

<small>Get runtime type identifier.</small>

**Returns**

| Type | Description |
| --- | --- |
| [RobotStatesType](#robotstatestype-enum) | - |


---

### PrimitiveType {#primitivetype-enum}

<small>Geometric representation for linear trajectory collision checking.</small>

| Enum Value | Description |
| --- | --- |
| `CYLINDER` | Swept-volume cylinder with configurable radius (accurate but slower) |
| `LINE` | Zero-thickness line segment (fast but less conservative) |


---

### Quaternion {#quaternion-class}

<small>Quaternion.

Represents a 3D rotation using quaternion representation (x, y, z, w). A unit quaternion has magnitude 1 and represents a valid rotation.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `w` | float | - |
| `x` | float | - |
| `y` | float | - |
| `z` | float | - |


---

### RgbData {#rgbdata-class}

<small>RGB/color image data structure.

Contains compressed color image data from RGB cameras. Compatible with ROS 2 sensor_msgs/CompressedImage format.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `data` | list[int] | Compressed binary data |
| `format` | str | Image format |
| `header` | [Header](#header-class) | Message header |


---

### RobotStates {#robotstates-class}

<small>Robot kinematic state representation.

Encapsulates the complete kinematic state of the robot, including whole-body joint configuration and mobile base pose. This class serves as a base for more specialized state representations (PoseState, JointStates) and is used throughout the planning and control pipeline for state specification and feedback. All angular values are in radians, linear values in meters (SI units). Base pose uses quaternion representation for orientation (x, y, z, qx, qy, qz, qw).</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `base_state` | list[float] | - |
| `whole_body_joint` | list[float] | - |

#### get_type {#robotstates-get_type-function}

```python
def get_type() -> RobotStatesType
```

<small>Get the runtime type of this state object.</small>

**Returns**

| Type | Description |
| --- | --- |
| [RobotStatesType](#robotstatestype-enum) | - |

#### set_base_state {#robotstates-set_base_state-function}

```python
def set_base_state(base_pose: Pose) -> None
```

<small>Set mobile base pose.

Converts Pose structure to internal base_state vector representation.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `base_pose` | [Pose](#pose-class) | required | - |

!!! note
    Quaternion must be unit-normalized (x^2 + y^2 + z^2 + w^2 = 1).

#### set_whole_body_joint {#robotstates-set_whole_body_joint-function}

```python
def set_whole_body_joint(joint_positions: list[float]) -> None
```

<small>Set complete whole-body joint configuration.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `joint_positions` | list[float] | required | - |

!!! note
    Vector size should equal the total number of actuated joints in the robot.


---

### RobotStatesType {#robotstatestype-enum}

<small>Enumeration for distinguishing derived state types.

Used for runtime type identification of RobotStates-derived classes.</small>

| Enum Value | Description |
| --- | --- |
| `JOINT` | JointStates: Joint space target. |
| `POSE` | PoseState: Cartesian pose target. |
| `ROBOT_STATES` | RobotStates: Generic whole-body state. |


---

### SamplerConfig {#samplerconfig-class}

<small>Configuration parameters for sampling-based motion planners.

This structure configures sampling-based planning algorithms (e.g., RRT, RRT*). It controls state space sampling resolution, interpolation settings, path simplification, and planning termination conditions. Sampling-based planners explore the configuration space by randomly sampling states and connecting them to build a motion plan graph.</small>

#### get_interpolate {#samplerconfig-get_interpolate-function}

```python
def get_interpolate() -> bool
```

<small>Check if path interpolation is enabled.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | - |

#### get_interpolation_cnt {#samplerconfig-get_interpolation_cnt-function}

```python
def get_interpolation_cnt() -> int
```

<small>Get the number of interpolation waypoints.</small>

**Returns**

| Type | Description |
| --- | --- |
| int | - |

#### get_max_planning_time {#samplerconfig-get_max_planning_time-function}

```python
def get_max_planning_time() -> float
```

<small>Get maximum planning time budget.</small>

**Returns**

| Type | Description |
| --- | --- |
| float | - |

#### get_max_simplification_time {#samplerconfig-get_max_simplification_time-function}

```python
def get_max_simplification_time() -> float
```

<small>Get maximum path simplification time budget.</small>

**Returns**

| Type | Description |
| --- | --- |
| float | - |

#### get_simplify {#samplerconfig-get_simplify-function}

```python
def get_simplify() -> bool
```

<small>Check if path simplification is enabled.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | - |

#### get_state_check_resolution {#samplerconfig-get_state_check_resolution-function}

```python
def get_state_check_resolution() -> float
```

<small>Get state comparison resolution threshold.</small>

**Returns**

| Type | Description |
| --- | --- |
| float | - |

#### get_state_check_type {#samplerconfig-get_state_check_type-function}

```python
def get_state_check_type() -> StateCheckType
```

<small>Get the configured distance metric for state comparison.</small>

**Returns**

| Type | Description |
| --- | --- |
| [StateCheckType](#statechecktype-enum) | - |

#### get_termination_condition_type {#samplerconfig-get_termination_condition_type-function}

```python
def get_termination_condition_type() -> TerminationConditionType
```

<small>Get planning termination condition.</small>

**Returns**

| Type | Description |
| --- | --- |
| [TerminationConditionType](#terminationconditiontype-enum) | - |

#### print {#samplerconfig-print-function}

```python
def print() -> None
```

<small>Print sampler configuration to standard output.

Outputs all configuration parameters for debugging and verification.</small>

#### set_interpolate {#samplerconfig-set_interpolate-function}

```python
def set_interpolate(enable: bool) -> None
```

<small>Enable or disable path interpolation between sampled states.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `enable` | bool | required | - |

!!! note
    Interpolation improves trajectory smoothness and collision checking accuracy

#### set_interpolation_cnt {#samplerconfig-set_interpolation_cnt-function}

```python
def set_interpolation_cnt(cnt: SupportsInt) -> None
```

<small>Set the number of interpolation waypoints between consecutive samples.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `cnt` | SupportsInt | required | - |

!!! note
    Higher counts improve collision detection but increase computational cost

#### set_max_planning_time {#samplerconfig-set_max_planning_time-function}

```python
def set_max_planning_time(time: SupportsFloat) -> None
```

<small>Set maximum time budget for motion planning.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `time` | SupportsFloat | required | - |

!!! note
    Planning may terminate earlier if exact solution is found (depends on termination condition)

#### set_max_simplification_time {#samplerconfig-set_max_simplification_time-function}

```python
def set_max_simplification_time(time: SupportsFloat) -> None
```

<small>Set maximum time budget for path simplification.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `time` | SupportsFloat | required | - |

!!! note
    Longer simplification time may yield shorter, smoother paths

#### set_simplify {#samplerconfig-set_simplify-function}

```python
def set_simplify(enable: bool) -> None
```

<small>Enable or disable path simplification post-processing.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `enable` | bool | required | - |

!!! note
    Simplification reduces waypoints and improves trajectory efficiency

#### set_state_check_resolution {#samplerconfig-set_state_check_resolution-function}

```python
def set_state_check_resolution(resolution: SupportsFloat) -> None
```

<small>Set state comparison resolution threshold.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `resolution` | SupportsFloat | required | - |

!!! note
    Lower values increase planning precision but may slow down computation

#### set_state_check_type {#samplerconfig-set_state_check_type-function}

```python
def set_state_check_type(type: StateCheckType) -> None
```

<small>Set the distance metric for state comparison.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `type` | [StateCheckType](#statechecktype-enum) | required | - |

#### set_termination_condition_type {#samplerconfig-set_termination_condition_type-function}

```python
def set_termination_condition_type(type: TerminationConditionType) -> None
```

<small>Set planning termination condition.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `type` | [TerminationConditionType](#terminationconditiontype-enum) | required | - |


---

### SeedType {#seedtype-enum}

<small>IK solver seed type enumeration.

Specifies the initialization strategy for inverse kinematics (IK) solvers. Different seed types affect convergence speed and solution quality.</small>

| Enum Value | Description |
| --- | --- |
| `RANDOM_PROGRESSIVE_SEED` | Random progressive seed, tries multiple random seeds iteratively (recommended for robustness) |
| `RANDOM_SEED` | Random seed, generates random initial joint configurations |
| `USER_DEFINED_SEED` | User-defined seed, uses explicitly provided initial joint configuration |


---

### SensorType {#sensortype-enum}

<small>Sensor type enumeration describing various sensors on the robot.

Identifies different sensor types available on the robot for perception, localization, and manipulation tasks.</small>

| Enum Value | Description |
| --- | --- |
| `BASE_LIDAR` | G1 Base LiDAR . |
| `BASE_ULTRASONIC` | Base ultrasonic sensor array, for proximity detection and collision avoidance . |
| `HEAD_LEFT_CAMERA` | Head left camera, typically RGB camera for stereo vision . |
| `HEAD_RIGHT_CAMERA` | Head right camera, typically RGB camera for stereo vision . |
| `LEFT_ARM_CAMERA` | Left arm camera, mounted on left manipulator for visual servoing . |
| `LEFT_ARM_DEPTH_CAMERA` | Left arm depth camera, provides RGB-D data for left arm workspace . |
| `LEFT_FRONT_SURROUND_CAMERA` | G1 left-front surround color camera . |
| `LEFT_REAR_SURROUND_CAMERA` | G1 left-rear surround color camera . |
| `RIGHT_ARM_CAMERA` | Right arm camera, mounted on right manipulator for visual servoing . |
| `RIGHT_ARM_DEPTH_CAMERA` | Right arm depth camera, provides RGB-D data for right arm workspace . |
| `RIGHT_FRONT_SURROUND_CAMERA` | G1 right-front surround color camera . |
| `RIGHT_REAR_SURROUND_CAMERA` | G1 right-rear surround color camera . |
| `TORSO_IMU` | G1 Torso IMU (Inertial Measurement Unit), measures acceleration and angular velocity . |


---

### SingoriXTarget {#singorixtarget-class}

<small>SDK mirror of galbot.singorix_proto.SingoriXTarget.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `header` | [Header](#header-class) | Message header |
| `target_group_trajectory_map` | dict[str, [TargetGroupTrajectory](#targetgrouptrajectory-class)] | Joint-space trajectory map |
| `target_task_trajectory_map` | dict[str, [TargetTaskTrajectory](#targettasktrajectory-class)] | Task-space trajectory map |


---

### StateCheckType {#statechecktype-enum}

<small>Distance metric for comparing states in configuration space.</small>

| Enum Value | Description |
| --- | --- |
| `EUCLIDEAN_DISTANCE` | Cartesian Euclidean distance in joint space (treats joint angles as Cartesian coordinates) |
| `RADIAN_DISTANCE` | Angular distance metric accounting for joint angle wraparound and weighting |


---

### SUCTION_ACTION_STATE {#suction_action_state-enum}

<small>Suction cup action state enumeration.

Represents the operational state of a vacuum suction cup end-effector, tracking the suction process from idle to success or failure.</small>

| Enum Value | Description |
| --- | --- |
| `FAILED` | Suction failed |
| `IDLE` | Not sucking |
| `SUCCESS` | Suction successful |
| `SUCKING` | Currently sucking |


---

### SuctionCupState {#suctioncupstate-class}

<small>Suction cup state.

Contains the current state of a vacuum suction cup gripper, including activation status, pressure reading, and action state.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `action_state` | [SUCTION_ACTION_STATE](#suction_action_state-enum) | Current suction cup action state (SUCTION_ACTION_STATE enum) |
| `activation` | bool | Whether currently sucking |
| `pressure` | float | Current pressure (Pa) |
| `timestamp_ns` | int | Timestamp (nanoseconds) |


---

### TargetConfig {#targetconfig-class}

<small>Common target configuration shared by group and task trajectories.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `target_data` | int | Target data bitmask |
| `target_id` | str | Target identifier |
| `target_priority` | int | Target priority |
| `target_sampling` | [TargetSampling](#targetsampling-enum) | Sampling strategy |
| `target_ts` | [Timestamp](#timestamp-class) | Target timestamp |
| `target_type` | int | Target type bitmask |


---

### TargetGroupTrajectory {#targetgrouptrajectory-class}

<small>Target trajectory for a group of joints.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `group_commands` | list[[GroupCommand](#groupcommand-class)] | Trajectory points |
| `joint_names` | list[str] | Joint names |
| `target_config` | [TargetConfig](#targetconfig-class) | Target configuration |


---

### TargetSampling {#targetsampling-enum}

<small>Sampling strategy for a target trajectory.

Mirrors galbot.singorix_proto.TargetSampling while remaining in the SDK type layer.</small>

| Enum Value | Description |
| --- | --- |
| `TARGET_SAMPLING_B_SPLINES` | B-splines |
| `TARGET_SAMPLING_CUBIC_SPLINES` | Cubic splines |
| `TARGET_SAMPLING_CUSTOM` | Custom sampling |
| `TARGET_SAMPLING_DEFAULT` | Default sampling strategy |
| `TARGET_SAMPLING_DIRECT_PASS` | Direct pass-through |
| `TARGET_SAMPLING_LINEAR_INTERPOLATE` | Linear interpolation |
| `TARGET_SAMPLING_QUINTIC_SPLINES` | Quintic splines |
| `TARGET_SAMPLING_S_CURVE_PROFILE` | S-curve profile |
| `TARGET_SAMPLING_TRAPEZOIDAL_PROFILE` | Trapezoidal profile |


---

### TargetTaskTrajectory {#targettasktrajectory-class}

<small>Target trajectory for task-space control.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `group_names` | list[str] | Related group names |
| `joint_names` | list[str] | Related joint names |
| `subtask_names` | list[str] | Subtask names |
| `target_config` | [TargetConfig](#targetconfig-class) | Target configuration |
| `task_commands` | list[[TaskCommand](#taskcommand-class)] | Trajectory points |


---

### TaskCommand {#taskcommand-class}

<small>Task-space command at a specific time point.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `subtask_commands` | list[[FrameTriad](#frametriad-class)] | Subtask commands at this point |
| `time_from_start_s` | float | Time from trajectory start in seconds |


---

### TerminationConditionType {#terminationconditiontype-enum}

<small>Planning termination criteria.</small>

| Enum Value | Description |
| --- | --- |
| `TIMEOUT` | Terminate only when maximum planning time is exceeded |
| `TIMEOUT_AND_EXACT_SOLUTION` | Terminate when timeout occurs OR exact goal solution is found |


---

### Timestamp {#timestamp-class}

<small>Timestamp structure.

Represents high-precision time points with second and nanosecond components. Compatible with ROS 2 builtin_interfaces/Time and std_msgs/Header timestamp format.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `nanosec` | int | Nanoseconds |
| `sec` | int | Seconds |


---

### Trajectory {#trajectory-class}

<small>Joint trajectory.

Represents a complete robot trajectory consisting of multiple waypoints over time.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `joint_groups` | list[str] | List of joint group names |
| `joint_names` | list[str] | List of joint names |
| `points` | list[[TrajectoryPoint](#trajectorypoint-class)] | List of trajectory points (TrajectoryPoint list) |


---

### TrajectoryControlStatus {#trajectorycontrolstatus-enum}

<small>Robot trajectory execution status enumeration.

Represents the real-time execution status when the robot follows a pre-planned trajectory consisting of multiple waypoints.</small>

| Enum Value | Description |
| --- | --- |
| `COMPLETED` | Trajectory execution completed successfully, reached final target point |
| `DATA_FETCH_FAILED` | Execution data retrieval failed, e.g., joint state or sensor feedback unavailable |
| `ERROR` | Error occurred, trajectory execution cannot continue |
| `INVALID_INPUT` | Input parameters do not meet requirements, trajectory cannot be executed |
| `RUNNING` | Trajectory is currently executing, not yet completed |
| `STOPPED_UNREACHED` | Stopped during trajectory execution without reaching endpoint |


---

### TrajectoryFeasibilityCheckOption {#trajectoryfeasibilitycheckoption-class}

<small>Trajectory validation and feasibility checking configuration.

This structure provides fine-grained control over which feasibility constraints are enforced during trajectory validation. It supports independent toggling of collision detection, joint limit compliance, and velocity profile feasibility. Selectively disabling checks can improve computational performance for debugging, simulation, or scenarios where certain constraints are guaranteed to be satisfied. Disabling feasibility checks may produce trajectories that are unsafe or physically unrealizable. Use with caution and only when constraints are verified through other means.</small>

#### get_disable_collision_check {#trajectoryfeasibilitycheckoption-get_disable_collision_check-function}

```python
def get_disable_collision_check() -> bool
```

<small>Check if collision detection is disabled.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | - |

#### get_disable_joint_limit_check {#trajectoryfeasibilitycheckoption-get_disable_joint_limit_check-function}

```python
def get_disable_joint_limit_check() -> bool
```

<small>Check if joint limit checking is disabled.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | - |

#### get_disable_velocity_feasibility_check {#trajectoryfeasibilitycheckoption-get_disable_velocity_feasibility_check-function}

```python
def get_disable_velocity_feasibility_check() -> bool
```

<small>Check if velocity feasibility checking is disabled.</small>

**Returns**

| Type | Description |
| --- | --- |
| bool | - |

#### print {#trajectoryfeasibilitycheckoption-print-function}

```python
def print() -> None
```

<small>Print trajectory feasibility check configuration to standard output.

Outputs enabled/disabled status for each feasibility check type.</small>

#### set_disable_collision_check {#trajectoryfeasibilitycheckoption-set_disable_collision_check-function}

```python
def set_disable_collision_check(disable: bool) -> None
```

<small>Enable or disable collision detection during trajectory validation.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `disable` | bool | required | - |

!!! warning
    Disabling collision checks may result in unsafe motion plans

#### set_disable_joint_limit_check {#trajectoryfeasibilitycheckoption-set_disable_joint_limit_check-function}

```python
def set_disable_joint_limit_check(disable: bool) -> None
```

<small>Enable or disable joint limit compliance checking.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `disable` | bool | required | - |

!!! warning
    Disabling joint limit checks may damage hardware or violate safety constraints

#### set_disable_velocity_feasibility_check {#trajectoryfeasibilitycheckoption-set_disable_velocity_feasibility_check-function}

```python
def set_disable_velocity_feasibility_check(disable: bool) -> None
```

<small>Enable or disable velocity profile feasibility checking.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `disable` | bool | required | - |

!!! note
    Velocity feasibility ensures the trajectory can be executed within actuator speed limits


---

### TrajectoryPlanConfig {#trajectoryplanconfig-class}

<small>Trajectory planning and parameterization configuration.

This structure configures trajectory generation parameters for converting discrete motion plans into smooth, time-parameterized trajectories. It supports both single-segment and multi-waypoint trajectory planning. Trajectory planning involves computing velocity and acceleration profiles along a geometric path while respecting kinematic constraints.</small>

#### get_min_move_time {#trajectoryplanconfig-get_min_move_time-function}

```python
def get_min_move_time() -> float
```

<small>Get minimum motion segment duration.</small>

**Returns**

| Type | Description |
| --- | --- |
| float | - |

#### get_move_line_intermediate_point {#trajectoryplanconfig-get_move_line_intermediate_point-function}

```python
def get_move_line_intermediate_point() -> float
```

<small>Get waypoint density for linear motion interpolation.</small>

**Returns**

| Type | Description |
| --- | --- |
| float | - |

#### get_way_point_plan_expected_time {#trajectoryplanconfig-get_way_point_plan_expected_time-function}

```python
def get_way_point_plan_expected_time() -> float
```

<small>Get expected multi-waypoint trajectory duration.</small>

**Returns**

| Type | Description |
| --- | --- |
| float | - |

#### print {#trajectoryplanconfig-print-function}

```python
def print() -> None
```

<small>Print trajectory planning configuration to standard output.

Outputs all configuration parameters for debugging and verification.</small>

#### set_min_move_time {#trajectoryplanconfig-set_min_move_time-function}

```python
def set_min_move_time(time: SupportsFloat) -> None
```

<small>Set minimum duration for any motion segment.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `time` | SupportsFloat | required | - |

!!! note
    Non-zero values prevent excessively fast motions; 0.0 allows maximum speed within kinematic limits

#### set_move_line_intermediate_point {#trajectoryplanconfig-set_move_line_intermediate_point-function}

```python
def set_move_line_intermediate_point(value: SupportsFloat) -> None
```

<small>Set waypoint density for Cartesian linear motion interpolation.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `value` | SupportsFloat | required | - |

!!! note
    Higher values improve Cartesian path accuracy but increase computational cost

#### set_way_point_plan_expected_time {#trajectoryplanconfig-set_way_point_plan_expected_time-function}

```python
def set_way_point_plan_expected_time(time: SupportsFloat) -> None
```

<small>Set expected total duration for multi-waypoint trajectory planning.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `time` | SupportsFloat | required | - |

!!! note
    Used as a hint for time-optimal trajectory generation algorithms


---

### TrajectoryPoint {#trajectorypoint-class}

<small>Single trajectory point.

Represents a waypoint in a robot trajectory, specifying joint states at a particular time.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `joint_command_vec` | list[[JointCommand](#jointcommand-class)] | - `joint_command_vec` (`List[JointCommand]`): List of specific joint commands to execute |
| `time_from_start_second` | float | - `time_from_start_second` (`float`): Time from trajectory start (seconds) |


---

### Twist {#twist-class}

<small>6D twist command (linear + angular velocity).</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `angular` | [Vector3](#vector3-class) | Angular velocity vector |
| `linear` | [Vector3](#vector3-class) | Linear velocity vector |


---

### UltrasonicData {#ultrasonicdata-class}

<small>Ultrasonic sensor data structure.

Contains a single ultrasonic distance measurement with timestamp.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `distance` | float | Distance (meters) |
| `timestamp_ns` | int | Timestamp (nanoseconds) |


---

### UltrasonicType {#ultrasonictype-enum}

<small>Chassis ultrasonic sensor probe enumeration (8 directions)

Identifies individual ultrasonic sensors arranged around the mobile base chassis for omnidirectional obstacle detection and proximity sensing.</small>

| Enum Value | Description |
| --- | --- |
| `BACK_LEFT` | Back left ultrasonic sensor |
| `BACK_RIGHT` | Back right ultrasonic sensor |
| `FRONT_LEFT` | Front left ultrasonic sensor |
| `FRONT_RIGHT` | Front right ultrasonic sensor |
| `LEFT_LEFT` | Left side front ultrasonic sensor |
| `LEFT_RIGHT` | Left side rear ultrasonic sensor |
| `RIGHT_LEFT` | Right side front ultrasonic sensor |
| `RIGHT_RIGHT` | Right side rear ultrasonic sensor |


---

### Vector3 {#vector3-class}

<small>3D vector structure

Represents a three-dimensional vector, used for forces, torques, velocities, accelerations, and other vectorial quantities.</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `x` | float | X coordinate |
| `y` | float | Y coordinate |
| `z` | float | Z coordinate |


---

### WBCException {#wbcexception-class}


---

### Wrench {#wrench-class}

<small>6D wrench command (force + torque).</small>

##### Member Variables

| Name | Type | Description |
| --- | --- | --- |
| `force` | [Vector3](#vector3-class) | Force vector |
| `torque` | [Vector3](#vector3-class) | Torque vector |

#### check_motion_status {#wrench-check_motion_status-function}

```python
def check_motion_status(status: MotionStatus) -> str
```

<small>Convert a MotionStatus enum value to a string.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `status` | [MotionStatus](#motionstatus-enum) | required | The motion status to convert. |

**Returns**

| Type | Description |
| --- | --- |
| str | str: The string representation of the motion status. |

#### create_parameter {#wrench-create_parameter-function}

```python
def create_parameter(
    direct_execute: bool,
    blocking: bool,
    timeout: SupportsFloat,
    actuate: str,
    tool_pose: bool,
    check_collision: bool,
    frame: str = 'base_link'
) -> Parameter
```

<small>Create a Parameter instance.</small>

**Parameters**

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `direct_execute` | bool | required | Whether to execute the motion directly. |
| `blocking` | bool | required | Whether to block the execution until completion. |
| `timeout` | SupportsFloat | required | Maximum time to wait for the motion to complete. |
| `actuate` | str | required | Actuation type (position/velocity/torque). |
| `tool_pose` | bool | required | Whether the motion is for a tool pose. |
| `check_collision` | bool | required | Whether to check for collisions. |
| `frame` | str | `'base_link'` | Coordinate frame for the motion. Defaults to "base_link". |

**Returns**

| Type | Description |
| --- | --- |
| [Parameter](#parameter-class) | Parameter: A new Parameter instance. |


---

