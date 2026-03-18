/**
 * @file galbot_robot.hpp
 * @brief Core robot control interface for Galbot G1 humanoid robot
 *
 * This file provides the main control interface for the Galbot G1 robot,
 * including joint control, end-effector manipulation, sensor data acquisition,
 * and coordinate frame transformations.
 *
 * @author Galbot SDK Team
 * @version 1.5.1
 * @copyright Copyright (c) 2023-2026 Galbot. All rights reserved.
 */

#pragma once

#include <functional>
#include <memory>
#include <unordered_map>
#include <unordered_set>
#include <utility>

#include "type.hpp"

/**
 * @namespace galbot
 * @brief Root namespace for Galbot robotics software
 */
namespace galbot {

/**
 * @namespace galbot::sdk
 * @brief Galbot Software Development Kit namespace
 */
namespace sdk {

/**
 * @namespace galbot::sdk::g1
 * @brief Namespace for Galbot G1 humanoid robot
 */
namespace g1 {

class Parameter;

/**
 * @class GalbotRobot
 * @brief Main robot control interface for Galbot G1 humanoid robot
 *
 * This class provides a singleton interface for controlling the Galbot G1 robot.
 * It supports:
 * - Joint position and trajectory control
 * - End-effector control (grippers and suction cups)
 * - Mobile base velocity control
 * - Sensor data acquisition (IMU, cameras, LiDAR, ultrasonic)
 * - Coordinate frame transformations
 * - System lifecycle management
 *
 * The class follows the singleton pattern to ensure a single instance
 * controls the robot hardware throughout the application lifecycle.
 *
 * @note All angles are in radians unless otherwise specified.
 * @note All linear distances are in meters unless otherwise specified.
 * @note All timestamps are in nanoseconds unless otherwise specified.
 */
class GalbotRobot {
 public:
  /**
   * @brief Get the singleton instance of GalbotRobot
   *
   * @return Reference to the singleton instance
   */
  static GalbotRobot& get_instance();

  /**
   * @brief Initialize the robot control system
   *
   * Initializes the robot hardware communication, middleware, and sensor interfaces.
   * To optimize resource usage, only sensors specified in the enable_sensor_set
   * will be initialized and available for data reading.
   *
   * @param enable_sensor_set Set of sensors to enable. If empty, a default set of sensors
   *                          will be enabled. Specify only required sensors to reduce
   *                          computational overhead and memory consumption.
   * @return true if initialization succeeded
   * @return false if initialization failed
   */
  bool init(const std::unordered_set<SensorType>& enable_sensor_set = {});

  /**
   * @brief Set low-level joint commands for specified joints
   *
   * This interface is suitable for high-frequency control usage
   * For standard joints (legs, head, arms, etc.), only the position field in each JointCommand will be effective; 
   * other fields such as velocity, current/effort, are ignored.
   * For gripper joints, the position field represents gripper width and both velocity and effort fields are supported and effective.
   * Gripper motion uses whichever is slower between the specified velocity and `time_from_start_s`. Therefore, when setting the gripper velocity, 
   * `time_from_start_s` can be set to 0 (fastest arrival), and the gripper will be controlled directly by the specified velocity.
   *
   * @param joint_commands Vector of joint commands containing control parameters for each joint
   * @param joint_groups Joint groups to control. Supported groups: legs, head, left_arm,
   *                     right_arm, gripper, suction_cup. Empty vector defaults to all body
   *                     joints (legs, head, left_arm, right_arm).
   * @param joint_names Specific joint names to control. This parameter takes precedence
   *                    over joint_groups. When provided, joint_groups is ignored.
   * @param time_from_start_s Time in seconds from the start of the motion to execute the command.
   * @return ControlStatus indicating success or failure of command transmission
   */
  ControlStatus set_joint_commands(const std::vector<JointCommand>& joint_commands,
                                   const std::vector<std::string>& joint_groups = {},
                                   const std::vector<std::string>& joint_names = {},
                                   const double time_from_start_s = 10);
  /**
   * @brief Set low-level joint commands for specified joint groups
   *
   * This interface is suitable for high-frequency control usage
   * For standard joints (legs, head, arms, etc.), only the position field in each JointCommand will be effective; 
   * other fields such as velocity, current/effort, are ignored.
   * For gripper joints, the position field represents gripper width and both velocity and effort fields are supported and effective.
   * Gripper motion uses whichever is slower between the specified velocity and `time_from_start_s`. Therefore, when setting the gripper velocity, 
   * `time_from_start_s` can be set to 0 (fastest arrival), and the gripper will be controlled directly by the specified velocity.
   * 
   * @param joint_commands Vector of joint commands containing control parameters for each joint.
   * @param joint_groups Joint groups to control using JointGroup enumerations. Supported groups:
   *                     legs, head, left_arm, right_arm, gripper, suction_cup. Empty vector
   *                     defaults to all body joints (legs, head, left_arm, right_arm).
   * @param joint_names Specific joint names to control. This parameter takes precedence
   *                    over joint_groups. When provided, joint_groups is ignored.
   * @param time_from_start_s Time in seconds from the start of the motion to execute the command.
   * @return ControlStatus indicating success or failure of command transmission.
   */
  ControlStatus set_joint_commands(const std::vector<JointCommand>& joint_commands,
                                   const std::vector<JointGroup>& joint_groups = {},
                                   const std::vector<std::string>& joint_names = {},
                                   const double time_from_start_s = 10);
  /**
   * @brief Set target joint positions for specified joint groups
   *
   * Commands the robot to move specified joints to target positions. The motion
   * is executed as a smooth trajectory with configurable speed limits.
   *
   * @param joint_positions Vector of target joint angles in radians. The order must match
   *                        the joint ordering returned by get_joint_names() for the specified
   *                        joint_groups or joint_names.
   * @param joint_groups Joint groups to control using JointGroup enumerations. Supported groups:
   *                     legs, head, left_arm, right_arm. Empty vector defaults to all body
   *                     joints (legs, head, left_arm, right_arm).
   * @param joint_names Specific joint names to control. This parameter takes precedence over
   *                    joint_groups. When provided, joint_groups is ignored.
   * @param is_blocking If true, blocks until motion completes or timeout occurs.
   *                    If false, returns immediately after command is sent.
   * @param speed_rad_s Maximum joint angular velocity in radians per second (rad/s).
   *                    Default: 0.2 rad/s.
   * @param timeout_s Maximum blocking wait time in seconds. Returns immediately upon timeout
   *                  regardless of execution completion. Default: 15 seconds.
   * @return ControlStatus indicating success or failure of the motion command
   *
   * @note For real-time control scenarios (e.g., teleoperation, VLA inference),
   *       use set_joint_commands() instead.
   */
  ControlStatus set_joint_positions(const std::vector<double>& joint_positions,
                                    const std::vector<JointGroup>& joint_groups = {},
                                    const std::vector<std::string>& joint_names = {}, const bool is_blocking = true,
                                    const double speed_rad_s = 0.2, const double timeout_s = 15);
  /**
   * @brief Set target joint positions for specified joint groups by name
   *
   * Commands the robot to move specified joints to target positions. The motion
   * is executed as a smooth trajectory with configurable speed limits.
   *
   * @param joint_positions Vector of target joint angles in radians. The order must match
   *                        the joint ordering returned by get_joint_names() for the specified
   *                        joint_groups or joint_names.
   * @param joint_groups Joint group names to control. Supported groups: "legs", "head",
   *                     "left_arm", "right_arm". Empty vector defaults to all body joints
   *                     (legs, head, left_arm, right_arm).
   * @param joint_names Specific joint names to control. This parameter takes precedence over
   *                    joint_groups. When provided, joint_groups is ignored.
   * @param is_blocking If true, blocks until motion completes or timeout occurs.
   *                    If false, returns immediately after command is sent.
   * @param speed_rad_s Maximum joint angular velocity in radians per second (rad/s).
   *                    Default: 0.2 rad/s.
   * @param timeout_s Maximum blocking wait time in seconds. Returns immediately upon timeout
   *                  regardless of execution completion. Default: 15 seconds.
   * @return ControlStatus indicating success or failure of the motion command
   *
   * @note For real-time control scenarios (e.g., teleoperation, VLA inference),
   *       use set_joint_commands() instead.
   */
  ControlStatus set_joint_positions(const std::vector<double>& joint_positions,
                                    const std::vector<std::string>& joint_groups = {},
                                    const std::vector<std::string>& joint_names = {}, const bool is_blocking = true,
                                    const double speed_rad_s = 0.2, const double timeout_s = 15);
  /**
   * @brief Get trajectory execution status for specified joint groups
   *
   * Queries the current execution status of trajectories for the specified joint groups.
   * This is useful for monitoring trajectory progress in non-blocking execution mode.
   *
   * @param joint_groups Vector of joint group names to query
   * @return Vector of TrajectoryControlStatus indicating execution state for each group
   */
  std::vector<TrajectoryControlStatus> check_trajectory_execution_status(std::vector<std::string> joint_groups);
  /**
   * @brief Get trajectory execution status for specified joint groups
   *
   * Queries the current execution status of trajectories for the specified joint groups.
   * This is useful for monitoring trajectory progress in non-blocking execution mode.
   *
   * @param joint_groups Vector of JointGroup enumerations to query
   * @return Vector of TrajectoryControlStatus indicating execution state for each group
   */
  std::vector<TrajectoryControlStatus> check_trajectory_execution_status(std::vector<JointGroup> joint_groups);
  /**
   * @brief Execute a pre-planned joint trajectory
   *
   * Executes a trajectory consisting of waypoints with associated joint positions,
   * velocities, and timing information. The trajectory controller interpolates
   * between waypoints to generate smooth motion.
   *
   * @param trajectory Trajectory data structure containing waypoints and timing
   * @param is_blocking If true, blocks until trajectory execution completes.
   *                    If false, returns immediately after trajectory is submitted.
   * @return ControlStatus indicating success or failure of trajectory execution/submission
   */
  ControlStatus execute_joint_trajectory(const Trajectory& trajectory, bool is_blocking = true);
  /**
   * @brief Set joint commands in batch mode (non-blocking)
   *
   * Sets multiple joint command trajectory points in real-time control mode,
   * supporting one-time submission of trajectory control commands for multiple
   * time points. Provides a non-blocking high-frequency trajectory execution
   * interface. Similar to set_joint_commands but supports batch trajectory control,
   * suitable for scenarios such as VLA inference batch output.
   *
   * @param trajectory Trajectory data structure containing waypoints with joint commands.
   *                   Each TrajectoryPoint contains time_from_start and a list of JointCommand.
   *                   JointCommand includes position (rad), velocity (rad/s), acceleration (rad/s²),
   *                   effort (N·m), Kp (position gain), and Kd (velocity gain).
   * @return ControlStatus indicating success or failure of command submission.
   *         Returns immediately without waiting for execution completion (non-blocking).
   */
  ControlStatus set_joint_commands_batch(const Trajectory& trajectory);
  /**
   * @brief Control suction cup activation state
   *
   * Activates or deactivates the specified suction cup end-effector.
   *
   * @param end_effector JointGroup enumeration specifying which suction cup to control
   * @param activate If true, activates vacuum suction. If false, releases suction.
   * @return ControlStatus indicating success or failure of command transmission
   */
  ControlStatus set_suction_cup_command(JointGroup end_effector, bool activate);
  /**
   * @brief Control gripper opening width and force
   *
   * Commands the gripper to move to a specified opening width with controlled
   * velocity and maximum gripping force.
   *
   * @param end_effector JointGroup enumeration specifying which gripper to control
   * @param width_m Target gripper opening width in meters (m), measured between
   *                the inner surfaces of the gripper fingers.
   * @param velocity_mps Gripper closing/opening velocity in meters per second (m/s).
   *                     Default: 0.03 m/s.
   * @param effort Maximum gripping force in Newton-meters (N·m). This limits the
   *               torque applied to prevent damage to grasped objects. Default: 30 N·m.
   * @param is_blocking If true, blocks until gripper reaches target position or times out.
   *                    If false, returns immediately after command is sent.
   * @return ControlStatus indicating success or failure of gripper command
   */
  ControlStatus set_gripper_command(JointGroup end_effector, double width_m, double velocity_mps = 0.03,
                                    double effort = 30, bool is_blocking = true);

  ControlStatus get_dexterous_hand_state(const JointGroup end_effector, JointStateMessage& joint_state);

  /**
   * @brief Control dexhand opening width and force
   *
   * Commands the dexhand to move to a specified opening width with controlled
   * velocity and maximum gripping force.
   *
   * @param end_effector JointGroup enumeration specifying which dexhand to control
   * @param dexhand_command Vector of dexhand commands containing control parameters for each joint
   *                        inspire: [position, velocity, acceleration, effort] range [0-1000, 0-1000, --, 0-1000]
   *                        brainco：[position, velocity, acceleration, effort] range [0-100, -100-100， --， --]
   * @param is_blocking If true, blocks until dexhand reaches target position or times out.
   * @return ControlStatus indicating success or failure of dexhand command
   */
  ControlStatus set_dexhand_command(JointGroup end_effector, const std::vector<JointCommand>& dexhand_command,
                                    bool is_blocking = true);
  /**
   * @brief Get current gripper state
   *
   * Retrieves the current state of the specified gripper, including position,
   * velocity, and force measurements.
   *
   * @param end_effector JointGroup enumeration specifying which gripper to query
   * @return Shared pointer to GripperState, or nullptr if retrieval fails
   */
  std::shared_ptr<GripperState> get_gripper_state(const JointGroup end_effector);
  /**
   * @brief Get current suction cup state
   *
   * Retrieves the current state of the specified suction cup, including
   * activation status and vacuum pressure measurements.
   *
   * @param end_effector JointGroup enumeration specifying which suction cup to query
   * @return Shared pointer to SuctionCupState, or nullptr if retrieval fails
   */
  std::shared_ptr<SuctionCupState> get_suction_cup_state(const JointGroup end_effector);

  /**
   * @brief Get current joint positions by group name
   *
   * Retrieves the current angular positions of joints in the specified groups.
   * The returned vector order matches the joint ordering from get_joint_names().
   *
   * @param joint_groups Joint group names to query. Empty vector retrieves all body joints.
   * @param joint_names Specific joint names to query. This parameter takes precedence
   *                    over joint_groups. When provided, joint_groups is ignored.
   * @return Vector of current joint angles in radians
   */
  std::vector<double> get_joint_positions(const std::vector<std::string>& joint_groups,
                                          const std::vector<std::string>& joint_names);

  /**
   * @brief Get current joint positions by group enumeration
   *
   * Retrieves the current angular positions of joints in the specified groups.
   * The returned vector order matches the joint ordering from get_joint_names().
   *
   * @param joint_groups JointGroup enumerations to query. Empty vector retrieves all body joints.
   * @param joint_names Specific joint names to query. This parameter takes precedence
   *                    over joint_groups. When provided, joint_groups is ignored.
   * @return Vector of current joint angles in radians
   */
  std::vector<double> get_joint_positions(const std::vector<JointGroup>& joint_groups,
                                          const std::vector<std::string>& joint_names = {});
  /**
   * @brief Get available joint group names for the robot
   *
   * Retrieves all joint group names defined in the robot's kinematic configuration.
   * This is useful for discovering available control groups at runtime.
   *
   * @return Vector of joint group names, or empty vector if retrieval fails
   */
  std::vector<std::string> get_joint_group_names();
  /**
   * @brief Get robot joint names by group name
   *
   * Retrieves the names of joints belonging to specified joint groups. This
   * is useful for determining the correct ordering when setting joint positions.
   *
   * @param only_active_joint If true, returns only actuated joints (excludes passive/fixed joints).
   *                          If false, returns all joints including passive ones.
   * @param joint_groups Joint group names to query. Empty vector retrieves joints from all groups.
   * @return Vector of joint names in kinematic chain order
   */
  std::vector<std::string> get_joint_names(bool only_active_joint = true,
                                           const std::vector<std::string>& joint_groups = {});
  /**
   * @brief Get robot joint names by group enumeration
   *
   * Retrieves the names of joints belonging to specified joint groups. This
   * is useful for determining the correct ordering when setting joint positions.
   *
   * @param only_active_joint If true, returns only actuated joints (excludes passive/fixed joints).
   *                          If false, returns all joints including passive ones.
   * @param joint_groups JointGroup enumerations to query. Empty vector retrieves joints from all groups.
   * @return Vector of joint names in kinematic chain order
   */
  std::vector<std::string> get_joint_names(bool only_active_joint = true,
                                           const std::vector<JointGroup>& joint_groups = {});

  /**
   * @brief Get real-time joint states by group name
   *
   * Retrieves comprehensive state information for specified joints, including
   * position, velocity, acceleration, effort (torque), and other feedback data.
   *
   * @param joint_group_vec Joint group names to query. Empty vector defaults to all body joints.
   * @param joint_names_vec Specific joint names to query. This parameter takes precedence
   *                        over joint_group_vec. When provided, joint_group_vec is ignored.
   * @return Vector of JointState structures containing current state for each joint
   */
  std::vector<JointState> get_joint_states(const std::vector<std::string>& joint_group_vec,
                                           const std::vector<std::string>& joint_names_vec = {});
  /**
   * @brief Get real-time joint states by group enumeration
   *
   * Retrieves comprehensive state information for specified joints, including
   * position, velocity, acceleration, effort (torque), and other feedback data.
   *
   * @param joint_group JointGroup enumerations to query. Empty vector defaults to all body joints.
   * @param joint_names Specific joint names to query. This parameter takes precedence
   *                    over joint_group. When provided, joint_group is ignored.
   * @return Vector of JointState structures containing current state for each joint
   */
  std::vector<JointState> get_joint_states(const std::vector<JointGroup>& joint_group,
                                           const std::vector<std::string>& joint_names = {});

  /**
   * @brief Set mobile base velocity command
   *
   * Commands the robot's mobile base to move with specified linear and angular velocities.
   * Velocities are expressed in the robot's base frame coordinate system.
   *
   * @param linear_velocity Linear velocity in meters per second (m/s), expressed in base frame.
   *                        Order: {vx, vy, vz} where:
   *                        - vx: forward/backward velocity (positive forward)
   *                        - vy: left/right velocity (positive left)
   *                        - vz: up/down velocity (typically 0 for ground robots)
   * @param angular_velocity Angular velocity in radians per second (rad/s), expressed in base frame.
   *                         Order: {wx, wy, wz} where:
   *                         - wx: roll rate (rotation about x-axis)
   *                         - wy: pitch rate (rotation about y-axis)
   *                         - wz: yaw rate (rotation about z-axis, positive counter-clockwise)
   * @param duration_s Duration in seconds to maintain the velocity command before auto-stop.
   *                   If <= 0, the command behaves as legacy mode (no automatic stop).
   * @return ControlStatus indicating success or failure of command transmission
   */
  ControlStatus set_base_velocity(const std::array<double, 3>& linear_velocity,
                                  const std::array<double, 3>& angular_velocity, double duration_s = 0.0);
  /**
   * @brief Set mobile base pose command
   *
   * Commands the robot's mobile base to move to a specified pose in its reference frame.
   * This uses the chassis pose controller (CHASSIS_POSE_CTRL).
   *
   * @param base_pose Target base pose [x, y, z, qx, qy, qz, qw]
   * @param is_blocking If true, waits for controller response; if false, returns immediately after request
   * @param timeout_s Timeout for blocking request (seconds)
   * @return ControlStatus indicating success or failure of command transmission
   */
  ControlStatus set_base_pose(const Pose& base_pose, bool is_blocking = true, double timeout_s = 15.0);
  /**
   * @brief Set mobile base pose (x, y, yaw) with selectable frames
   *
   * @param x Target x position (meters)
   * @param y Target y position (meters)
   * @param yaw Target yaw (radians)
   * @param frame_id Frame id of target. Options: "base_link" / "odom" / "map". Default: "odom"
   * @param reference_frame_id Reference frame id. Options: "odom" / "map"
   * @param is_blocking If true, waits for controller response; if false, returns immediately after request
   * @param timeout_s Timeout for blocking request (seconds)
   * @return ControlStatus indicating success or failure of command transmission
   */
  ControlStatus set_base_pose(double x, double y, double yaw, const std::string& frame_id = "odom",
                              const std::string& reference_frame_id = "odom", bool is_blocking = true,
                              double timeout_s = 15.0);
  /**
   * @brief Set mobile base pose (x, y, yaw) with explicit interpolation time
   *
   * @param x Target x position (meters)
   * @param y Target y position (meters)
   * @param yaw Target yaw (radians)
   * @param frame_id Frame id of target. Options: "base_link" / "odom" / "map"
   * @param reference_frame_id Reference frame id. Options: "odom" / "map"
   * @param time_from_start_s Chassis pose interpolation time (seconds)
   * @param is_blocking If true, waits for controller response; if false, returns immediately after request
   * @param timeout_s Request timeout (seconds)
   * @return ControlStatus indicating success or failure of command transmission
   */
  ControlStatus set_base_pose(double x, double y, double yaw, const std::string& frame_id,
                              const std::string& reference_frame_id, double time_from_start_s, bool is_blocking = true,
                              double timeout_s = 15.0);
  /**
   * @brief Execute a whole-body target with base velocity
   *
   * Sends joint position commands for the full body (legs, head, left_arm, right_arm) and
   * a chassis twist command using existing joint/base interfaces. Commands are dispatched
   * in sequence (no multithreading) but start in close succession.
   *
   * @param joint_positions Whole-body joint positions: leg(5) + head(2) + left_arm(7) + right_arm(7)
   * @param linear_velocity Base linear velocity [vx, vy, vz] in base frame (m/s)
   * @param angular_velocity Base angular velocity [wx, wy, wz] in base frame (rad/s)
   * @param is_blocking If true, waits for joint execution to complete or timeout
   * @param speed_rad_s Max joint speed for the joint target (rad/s)
   * @param timeout_s Timeout for blocking wait (seconds)
   * @return ControlStatus indicating success or failure of the command
   */
  ControlStatus execute_whole_body_target(const std::vector<double>& joint_positions,
                                          const std::array<double, 3>& linear_velocity,
                                          const std::array<double, 3>& angular_velocity, bool is_blocking = true,
                                          double speed_rad_s = 0.2, double timeout_s = 15.0);
  /**
   * @brief Execute a whole-body target with base pose
   *
   * Sends joint position commands for the full body (legs, head, left_arm, right_arm) and
   * a chassis pose command using existing joint/base interfaces. Commands are dispatched
   * in sequence (no multithreading) but start in close succession.
   *
   * @param joint_positions Whole-body joint positions: leg(5) + head(2) + left_arm(7) + right_arm(7)
   * @param base_pose Target base pose [x, y, z, qx, qy, qz, qw]
   * @param is_blocking If true, waits for joint execution to complete or timeout
   * @param speed_rad_s Max joint speed for the joint target (rad/s)
   * @param timeout_s Timeout for blocking wait (seconds)
   * @return ControlStatus indicating success or failure of the command
   */
  ControlStatus execute_whole_body_target(const std::vector<double>& joint_positions, const Pose& base_pose,
                                          bool is_blocking = true, double speed_rad_s = 0.2, double timeout_s = 15.0);
  /**
   * @brief Execute a whole-body target with base pose (x, y, yaw) and selectable frames
   *
   * @param joint_positions Whole-body joint positions: leg(5) + head(2) + left_arm(7) + right_arm(7)
   * @param x Target x position (meters)
   * @param y Target y position (meters)
   * @param yaw Target yaw (radians)
   * @param frame_id Frame id of target. Options: "base_link" / "odom" / "map". Default: "odom"
   * @param reference_frame_id Reference frame id. Options: "odom" / "map"
   * @param is_blocking If true, waits for joint execution to complete or timeout
   * @param speed_rad_s Max joint speed for the joint target (rad/s)
   * @param time_from_start_s Chassis pose interpolation duration (seconds)
   * @param timeout_s Timeout for blocking wait (seconds)
   * @return ControlStatus indicating success or failure of the command
   */
  ControlStatus execute_whole_body_target(const std::vector<double>& joint_positions, double x, double y, double yaw,
                                          const std::string& frame_id = "odom",
                                          const std::string& reference_frame_id = "odom", bool is_blocking = true,
                                          double speed_rad_s = 0.2, double time_from_start_s = 10.0,
                                          double timeout_s = 15.0);
  /**
   * @brief Emergency stop mobile base movement
   *
   * Immediately commands the mobile base to stop all motion. This is a safety
   * function that should be used when immediate cessation of base motion is required.
   *
   * @return ControlStatus indicating success or failure of command transmission
   */
  ControlStatus stop_base();
  /**
   * @brief One-key zero: move whole-body joints to zero and base to zero pose
   *
   * This calls GalbotMotion::move_whole_body_joint_zero for joint zeroing, and
   * commands the base pose to zero. If params is nullptr, default_param is used.
   *
   * @param base_zero_pose Target base zero pose [x, y, z, qx, qy, qz, qw]
   * @param is_blocking Whether to block on joint zeroing
   * @param leg_head_speed_rad_s Max joint speed for leg/head direct control (rad/s)
   * @param leg_head_timeout_s Timeout for leg/head direct control (seconds)
   * @param params Motion planning parameters (nullptr uses default_param)
   * @return Pair of (MotionStatus for joints, ControlStatus for base)
   */
  std::pair<MotionStatus, ControlStatus> zero_whole_body_and_base(const Pose& base_zero_pose, bool is_blocking = true,
                                                                  double leg_head_speed_rad_s = 0.2,
                                                                  double leg_head_timeout_s = 15.0,
                                                                  std::shared_ptr<Parameter> params = nullptr);
  /**
   * @brief One-key zero: move whole-body joints to zero and base (x,y,yaw) to zero with selectable frames
   *
   * @param frame_id Frame id of target. Options: "base_link" / "odom" / "map". Default: "odom"
   * @param reference_frame_id Reference frame id. Options: "odom" / "map"
   * @param is_blocking Whether to block on joint zeroing
   * @param leg_head_speed_rad_s Max joint speed for leg/head direct control (rad/s)
   * @param leg_head_timeout_s Timeout for leg/head direct control (seconds)
   * @param params Motion planning parameters (nullptr uses default_param)
   * @return Pair of (MotionStatus for joints, ControlStatus for base)
   */
  std::pair<MotionStatus, ControlStatus> zero_whole_body_and_base(
      const std::string& frame_id = "odom", const std::string& reference_frame_id = "odom", bool is_blocking = true,
      double leg_head_speed_rad_s = 0.2, double leg_head_timeout_s = 15.0, std::shared_ptr<Parameter> params = nullptr);
  /**
   * @brief Stop all currently executing joint trajectories
   *
   * Immediately halts execution of all active joint trajectories across all joint groups.
   * Joints will maintain their current positions after stopping.
   *
   * @return ControlStatus indicating success or failure of command transmission
   */
  ControlStatus stop_trajectory_execution();

  /**
   * @brief Reload a controller
   *
   * Reinitializes the controller. Equivalent to a full restart cycle: stop -> reset -> start.
   * Useful for error recovery or applying configuration changes.
   *
   * @param group_name Name of the joint group to reload. Supported groups: chassis,
   * legs, head, left_arm, right_arm, gripper, or "all" to reload all controllers (default).
   * @return ControlStatus indicating success or failure of the reload operation
   */
  ControlStatus reload_controller(const std::string& group_name = "all");
  /**
   * @brief Reload a controller
   *
   * Reinitializes the controller. Equivalent to a full restart cycle: stop -> reset -> start.
   * Useful for error recovery or applying configuration changes.
   *
   * @param joint_group JointGroup enumeration of the joint group to reload.
   * @return ControlStatus indicating success or failure of the reload operation
   */
  ControlStatus reload_controller(const JointGroup joint_group);

  /**
   * @brief Switch active controller strategy
   *
   * Transitions hardware control to a new strategy.
   * Operation sequence: stop(old) -> release(old) -> acquire(new) -> start(new).
   *
   * @param controller_name Name of the controller to switch to.
   * @return ControlStatus indicating success or failure of the switch operation.
   */
  ControlStatus switch_controller(ControllerName controller_name);

  /**
   * @brief Get active controller name for specified joint group
   *
   * @param group_name Name of the joint group to query.
   * @return ControllerName Name of the active controller.
   */
  ControllerName get_active_controller(const std::string& group_name);
  /**
   * @brief Get active controller name for specified joint group
   *
   * @param joint_group JointGroup enumeration of the joint group to query.
   * @return ControllerName Name of the active controller.
   */
  ControllerName get_active_controller(const JointGroup joint_group);

  /**
   * @brief Acquire hardware authority
   *
   * Designates the controller to take ownership of the hardware.
   * Opposite of release_controller. Controller must still be started to begin execution.
   *
   * @param controller_name Name of the controller to acquire.
   * @return ControlStatus indicating success or failure of the acquire operation.
   */
  ControlStatus acquire_controller(ControllerName controller_name);

  /**
   * @brief Release hardware authority
   *
   * Yields control of the hardware, freeing the joints.
   * Opposite of acquire_controller. Implicitly stops execution if running.
   *
   * @param group_name Name of the joint group to release. Supported groups: chassis,
   * legs, head, left_arm, right_arm, gripper, or "all" to release all controllers (default).
   * @return ControlStatus indicating success or failure of the release operation
   */
  ControlStatus release_controller(const std::string& group_name = "all");
  /**
   * @brief Release hardware authority
   *
   * Yields control of the hardware, freeing the joints.
   * Opposite of acquire_controller. Implicitly stops execution if running.
   *
   * @param joint_group JointGroup enumeration of the joint group to release.
   * @return ControlStatus indicating success or failure of the release operation
   */
  ControlStatus release_controller(const JointGroup joint_group);

  /**
   * @brief Start controller execution
   *
   * Activates the controller to begin sending commands.
   * Opposite of stop_controller. Requires prior hardware authority (acquire).
   *
   * @param group_name Name of the joint group to start. Supported groups: chassis,
   * legs, head, left_arm, right_arm, gripper, or "all" to start all controllers (default).
   * @return ControlStatus indicating success or failure of the start operation
   */
  ControlStatus start_controller(const std::string& group_name = "all");
  /**
   * @brief Start controller execution
   *
   * Activates the controller to begin sending commands.
   * Opposite of stop_controller. Requires prior hardware authority (acquire).
   *
   * @param joint_group JointGroup enumeration of the joint group to start.
   * @return ControlStatus indicating success or failure of the start operation
   */
  ControlStatus start_controller(const JointGroup joint_group);

  /**
   * @brief Stop controller execution
   *
   * Halts command execution but retains hardware authority.
   * Opposite of start_controller.
   *
   * @param group_name Name of the joint group to stop. Supported groups: chassis,
   * legs, head, left_arm, right_arm, gripper, or "all" to stop all controllers (default).
   * @return ControlStatus indicating success or failure of the stop operation
   */
  ControlStatus stop_controller(const std::string& group_name = "all");
  /**
   * @brief Stop controller execution
   *
   * Halts command execution but retains hardware authority.
   * Opposite of start_controller.
   *
   * @param joint_group JointGroup enumeration of the joint group to stop.
   * @return ControlStatus indicating success or failure of the stop operation
   */
  ControlStatus stop_controller(const JointGroup joint_group);

  /**
   * @brief Get IMU (Inertial Measurement Unit) sensor data
   *
   * Retrieves the latest IMU measurements including linear acceleration,
   * angular velocity, and orientation estimation.
   *
   * @param imu_type SensorType enumeration specifying which IMU to query
   * @return Shared pointer to ImuData structure, or nullptr if sensor is not enabled
   *         or data retrieval fails
   *
   * @note The IMU sensor must be enabled during initialization via enable_sensor_set
   * @note Acceleration is in meters per second squared (m/s²)
   * @note Angular velocity is in radians per second (rad/s)
   */
  std::shared_ptr<ImuData> get_imu_data(SensorType imu_type);

  /**
   * @brief Get robot odometry information
   *
   * Retrieves the robot's current pose and velocity estimates from the odometry system.
   * Odometry typically fuses wheel encoders, IMU, and other proprioceptive sensors.
   *
   * @return Shared pointer to OdomData containing:
   *         - Position in meters (m) relative to odometry frame origin
   *         - Orientation as quaternion
   *         - Linear velocity in meters per second (m/s)
   *         - Angular velocity in radians per second (rad/s)
   *         - Timestamp in nanoseconds
   *         Returns nullptr if odometry is unavailable.
   */
  std::shared_ptr<OdomData> get_odom();
  /**
   * @brief Get device information
   *
   * Retrieves basic device information including device model, serial number,
   * firmware version, hardware version, and manufacturer. This information
   * is used for device management, version control, system diagnostics, and
   * device identification.
   *
   * @return Shared pointer to DeviceInfo structure containing:
   *         - model: Device model name or identifier
   *         - serial_number: Unique serial number for device identification
   *         - firmware_version: System firmware version string
   *         - hardware_version: Hardware version or revision number
   *         - manufacturer: Manufacturer name or company identifier
   *         Returns nullptr if device information retrieval fails.
   */
  std::shared_ptr<DeviceInfo> get_device_information();

  /**
   * @brief Get latest RGB image from specified camera
   *
   * Retrieves the most recent color image captured by the specified RGB camera.
   *
   * @param rgb_camera SensorType enumeration specifying which RGB camera to query
   * @return Shared pointer to RgbData containing image buffer, dimensions, encoding,
   *         and timestamp. Returns nullptr if camera is not enabled or data retrieval fails.
   *
   * @note The camera sensor must be enabled during initialization via enable_sensor_set
   */
  std::shared_ptr<RgbData> get_rgb_data(const SensorType rgb_camera);

  /**
   * @brief Get latest depth image from specified camera
   *
   * Retrieves the most recent depth image captured by the specified depth camera.
   * Depth values typically represent distance from the camera sensor.
   *
   * @param depth_camera SensorType enumeration specifying which depth camera to query
   * @return Shared pointer to DepthData containing depth image buffer, dimensions,
   *         encoding, and timestamp. Returns nullptr if camera is not enabled or
   *         data retrieval fails.
   *
   * @note The camera sensor must be enabled during initialization via enable_sensor_set
   * @note Depth values are typically in millimeters (mm) or meters (m) depending on sensor
   */
  std::shared_ptr<DepthData> get_depth_data(const SensorType depth_camera);
  /**
   * @brief Get latest LiDAR point cloud data
   *
   * Retrieves the most recent 3D point cloud captured by the specified LiDAR sensor.
   * Each point typically contains (x, y, z) coordinates and optional intensity values.
   *
   * @param lidar SensorType enumeration specifying which LiDAR to query
   * @return Shared pointer to LidarData (PointCloud2 format) containing point cloud
   *         with coordinates in meters (m) relative to the LiDAR frame. Returns nullptr
   *         if LiDAR is not enabled or data retrieval fails.
   *
   * @note The LiDAR sensor must be enabled during initialization via enable_sensor_set
   */
  std::shared_ptr<LidarData> get_lidar_data(const SensorType lidar);

  /**
   * @brief Get distance measurement from specified ultrasonic sensor
   *
   * Retrieves the latest distance measurement from one of the ultrasonic range sensors.
   * The robot typically has multiple ultrasonic sensors arranged around its perimeter.
   *
   * @param ultrasonic_type UltrasonicType enumeration specifying which ultrasonic
   *                        sensor to query (one of 8 directional sensors)
   * @return Shared pointer to UltrasonicData containing distance in meters (m),
   *         or nullptr if sensor is not enabled or data retrieval fails
   *
   * @note The ultrasonic sensor must be enabled during initialization via enable_sensor_set
   */
  std::shared_ptr<UltrasonicData> get_ultrasonic_data(const UltrasonicType ultrasonic_type);

  /**
   * @brief Get camera intrinsic parameters
   *
   * Retrieves the intrinsic parameters of the specified camera, including
   * focal lengths, principal points, and distortion coefficients, etc.
   *
   * @param camera SensorType enumeration specifying which camera to query
   * @return Shared pointer to CameraInfo containing:
   *         - focal_length_x, focal_length_y: Focal lengths in pixels
   *         - principal_point_x, principal_point_y: Principal point coordinates in pixels
   *         - distortion_coeffs: Vector of distortion coefficients (e.g., k1, k2, p1, p2, k3)
   *         - more camera-specific parameters as needed
   *         Returns nullptr if camera is not enabled or data retrieval fails.
   *
   * @note The camera sensor must be enabled during initialization via enable_sensor_set
   */
  std::shared_ptr<CameraInfo> get_camera_intrinsic(const SensorType camera);

  /**
   * @brief Query coordinate frame transformation (TF)
   *
   * Queries the transformation between two coordinate frames in the robot's TF tree.
   * This is used for converting poses and positions between different reference frames
   * (e.g., from camera frame to base frame, from end-effector to world frame).
   *
   * @param target_frame Name of the target coordinate frame (frame to transform into).
   *                     Examples: map, base_link, imu_base_link. The actual list is determined by
   *                     get_frame_names().
   * @param source_frame Name of the source coordinate frame (frame to transform from).
   *                     Examples: map, base_link, imu_base_link. The actual list is determined by
   *                     get_frame_names().
   * @param timestamp_ns Desired transform timestamp in nanoseconds. Pass 0 to get
   *                     the most recent available transformation.
   * @param timeout_ms Maximum time to wait for the transform in milliseconds.
   *                   Default: 100 milliseconds.
   *
   * @return Pair containing:
   *         - Vector of 7 doubles representing the transform [x, y, z, qx, qy, qz, qw]
   *           where (x, y, z) is translation in meters and (qx, qy, qz, qw) is
   *           orientation quaternion
   *         - Timestamp in nanoseconds when the transform was valid
   *         Returns empty vector and timestamp 0 if retrieval fails or times out.
   */
  std::pair<std::vector<double>, int64_t> get_transform(const std::string& target_frame,
                                                        const std::string& source_frame, int64_t timestamp_ns = 0,
                                                        int64_t timeout_ms = 100);
  /**
   * @brief Get all frame names
   *
   * @return std::vector<std::string> All frame names
   */
  std::vector<std::string> get_frame_names();
  /**
   * @brief Get sensor extrinsic parameters
   *
   * Retrieves the extrinsic parameters of the specified sensor, including
   * rotation and translation vectors relative to the robot's base frame.
   *
   * @param sensor SensorType enumeration specifying which sensor to query
   * @param reference_frame Name of the reference coordinate frame (frame to transform from)
   *                        Default is "base_link".
   * @return Pair containing:
   *         - Vector of 7 doubles representing the transform [x, y, z, qx, qy, qz, qw]
   *           where (x, y, z) is translation in meters and (qx, qy, qz, qw) is
   *           orientation quaternion
   *         - Timestamp in nanoseconds when the transform was valid
   *         Returns empty vector and timestamp 0 if retrieval fails.
   *
   * @note The sensor must be enabled during initialization via enable_sensor_set
   */
  std::pair<std::vector<double>, int64_t> get_sensor_extrinsic(const SensorType sensor_id,
                                                               const std::string& reference_frame = "base_link");
  /**
   * @brief Get force/torque sensor data
   *
   * Retrieves the latest measurements from the specified force/torque sensor.
   * These sensors are typically mounted at wrists or end-effectors for contact
   * force monitoring and compliance control.
   *
   * @param sensor_type GalbotOneFoxtrotSensor enumeration specifying which force sensor to query
   * @return Shared pointer to ForceData containing:
   *         - Force vector in Newtons (N): [fx, fy, fz]
   *         - Torque vector in Newton-meters (N·m): [tx, ty, tz]
   *         - Timestamp in nanoseconds
   *         Returns nullptr if sensor is not enabled or data retrieval fails.
   *
   * @note The force sensor must be enabled during initialization via enable_sensor_set
   * @note The returned values are raw readings and include the self-weight of the end-effectors.
   */
  std::shared_ptr<ForceData> get_force_sensor_data(const GalbotOneFoxtrotSensor sensor_type);

  /**
   * @brief Start microphone streaming audio input
   *
   * @param callback Audio data callback function with signature: void(const std::shared_ptr<AudioData>)
   * @param chunk_size Audio data chunk size in bytes, default value 2560. Dynamic configuration not supported yet
   * @param use_raw_audio Whether to use raw audio, default false. Dynamic configuration not supported yet.
   *                      true means output raw audio directly, false means output processed audio
   * @return std::string Stream ID used to identify this audio input stream
   */
  std::string start_microphone_stream_input(std::function<void(const std::shared_ptr<AudioData>)> callback,
                                            int chunk_size = 2560, bool use_raw_audio = false);
  /**
   * @brief Stop the specified microphone streaming audio input
   *
   * @param stream_id Audio input stream ID to stop. If empty string, stops all active streams
   */
  void stop_microphone_stream_input(const std::string& stream_id = "");

  /**
   * @brief Write PCM format audio data chunk to audio output stream for real-time playback
   *
   * @param audio_chunk Audio data chunk in PCM format (16000 Hz, 16-bit little-endian), single channel
   * @param stream_id Audio stream ID to distinguish different audio sources. Empty string means use default stream
   * @return bool Returns operation result. True means audio data has been successfully written and playback task
   * issued, False means write failed
   */
  bool write_audio_stream_output(const std::string& audio_chunk, const std::string& stream_id = "");
  /**
   * @brief Stop the specified audio output stream or all active audio output streams playback
   *
   * @param stream_id Audio output stream ID to stop. Empty string means stop all active audio output streams
   */
  void stop_audio_stream_output(const std::string& stream_id = "");
  /**
   * @brief Get current system global volume value
   *
   * @return float Returns current volume value, range 0.0 to 100.0
   */
  float get_volume();
  /**
   * @brief Set system global volume value
   *
   * @param volume Target volume value, range 0.0 to 100.0
   * @return bool Returns the volume setting result. True indicates the volume was set successfully, False indicates the
   * volume setting failed.
   */
  bool set_volume(float volume);

  /**
   * @brief Check if the robot control system is running
   *
   * Queries whether the robot control system is still active or if a shutdown
   * signal (e.g., SIGINT, SIGTERM) has been received.
   *
   * @return true if system is running normally
   * @return false if shutdown signal has been received and system is preparing to exit
   */
  bool is_running();
  /**
   * @brief Request system shutdown
   *
   * Programmatically sends a shutdown signal (SIGINT) to initiate graceful
   * system shutdown. This triggers registered exit callbacks and begins
   * resource cleanup.
   */
  void request_shutdown();
  /**
   * @brief Block until shutdown signal is received
   *
   * Blocks the calling thread indefinitely until a shutdown signal (SIGINT, SIGTERM)
   * is received. This is useful for keeping the main thread alive while background
   * threads handle robot control.
   *
   * @note This function will return when is_running() becomes false
   */
  void wait_for_shutdown();
  /**
   * @brief Clean up system resources
   *
   * Performs cleanup of robot control system resources including middleware
   * connections, sensor interfaces, and communication channels. Should be called
   * before program exit to ensure graceful shutdown.
   *
   * @note This function should be called after request_shutdown() or when
   *       is_running() returns false
   */
  void destroy();
  /**
   * @brief Register callback function for shutdown event
   *
   * Registers a user-defined callback function that will be invoked when a
   * shutdown signal is received. Multiple callbacks can be registered and
   * will be executed in registration order.
   *
   * @param exit_function Callback function with signature void() to be executed
   *                      during shutdown. Use this to perform application-specific
   *                      cleanup (e.g., saving data, stopping threads).
   *
   * @note Callbacks should complete quickly to avoid delaying shutdown
   */
  void register_exit_callback(std::function<void()> exit_function);

  /**
   * @brief Get BMS (Battery Management System) information
   *
   * @return Shared pointer to BmsInfo containing battery information
   */
  std::shared_ptr<BmsInfo> get_bms_information();

  /**
   * @brief Get log information
   *
   * @return Shared pointer to LogInfo containing log information
   */
  std::shared_ptr<LogInfo> get_log_information(uint64 timewindow_s, LogLevel log_level);

 private:
  // Default constructor (private for singleton pattern)
  GalbotRobot() = default;

  // Delete copy and move operations to enforce singleton pattern
  GalbotRobot(const GalbotRobot&) = delete;
  GalbotRobot& operator=(const GalbotRobot&) = delete;
  GalbotRobot(GalbotRobot&&) = delete;
  GalbotRobot& operator=(GalbotRobot&&) = delete;
};

}  // namespace g1
}  // namespace sdk
}  // namespace galbot
