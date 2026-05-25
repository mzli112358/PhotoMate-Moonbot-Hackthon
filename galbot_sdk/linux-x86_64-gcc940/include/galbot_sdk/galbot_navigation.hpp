/**
 * @file galbot_navigation.hpp
 * @brief Navigation interface for mobile robot chassis motion planning and localization
 *
 * This file provides the navigation control interface for the Galbot G1 mobile base,
 * including:
 * - 2D pose estimation and relocalization
 * - Goal-directed navigation with obstacle avoidance
 * - Path planning and reachability checking
 * - Omnidirectional and differential drive motion planning
 *
 * @note All pose coordinates use the map frame unless explicitly stated otherwise.
 * @note Distances are in meters (m), angles in radians (rad), time in seconds (s).
 *
 * @author Galbot SDK Team
 * @version 1.5.1
 * @copyright Copyright (c) 2023-2026 Galbot. All rights reserved.
 * 
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#pragma once

#include "galbot_sdk_type.hpp"

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
 * @class GalbotNavigation
 * @brief Navigation interface for mobile robot chassis motion planning and localization.
 *
 * This class provides a thread-safe singleton interface for controlling the mobile base
 * navigation system. It supports 2D pose estimation, relocalization, goal-directed navigation
 * with dynamic obstacle avoidance, and path planning capabilities.
 *
 * The navigation system operates in a global map frame and provides both blocking and
 * non-blocking navigation modes. It supports both differential drive and omnidirectional
 * motion planning strategies.
 *
 * @note This class uses the singleton pattern with thread-safe initialization.
 * @note All pose coordinates are specified in the map frame unless explicitly stated otherwise.
 *
 * Typical usage:
 * @code
 *   auto& nav = GalbotNavigation::get_instance(MachineType::G1);
 *   if (nav.init()) {
 *     Pose goal;
 *     goal.x = 1.0;  // meters
 *     goal.y = 2.0;  // meters
 *     goal.orientation.w = 1.0;  // identity quaternion (x,y,z default 0)
 *     nav.navigate_to_goal(goal, true, false, 30.0, true);
 *   }
 * @endcode
 *
 */
class GalbotNavigation {
 public:
  virtual ~GalbotNavigation() = default;

  /**
   * @brief Runtime factory for selecting a concrete navigation singleton.
   *
   * This static factory method allows runtime selection of the navigation
   * implementation based on the robot machine type. The method declaration
   * resides in the interface header for compile-time availability, while the
   * actual implementation logic (including platform-specific includes and
   * switch statements) is contained in the corresponding .cpp file. This
   * design keeps the interface clean while enabling platform-specific
   * instantiation without exposing implementation details.
   *
   * @param m Machine type identifier specifying which robot platform to use.
   * @return Reference to the singleton navigation interface instance for the
   *         specified machine type.
   *
   * @note Adding support for a new machine type requires updating the
   *       MachineType enumeration and the factory implementation in the .cpp file.
   */
  static GalbotNavigation& get_instance(MachineType m);

  /**
   * @brief Initialize the navigation subsystem and its dependencies.
   *
   * This method must be called before using any other navigation functions.
   * It initializes communication channels, loads the map, starts the localization
   * module, and prepares the path planner.
   *
   * @return true if initialization succeeded, false otherwise.
   *
   * @note This method should only be called once after obtaining the singleton instance.
   * @note Subsequent calls will return the result of the first initialization attempt.
   *
   * @warning Calling navigation methods before successful initialization will result
   *          in undefined behavior.
   */
  virtual bool init() = 0;

  /**
   * @brief Perform relocalization to re-estimate the robot's pose in the map frame.
   *
   * This method resets the localization filter and provides an initial pose estimate
   * to help the robot re-establish its position in the known map. This is useful
   * when the robot has lost localization or when manually placing the robot at a
   * known position.
   *
   * @param init_pose Initial pose estimate in the map frame: position (x, y, z) in meters
   *                  and orientation as unit quaternion (x, y, z, w). Serves as the starting
   *                  point for the relocalization algorithm.
   *
   * @return NavigationStatus indicating the result of the relocalization request.
   *         See NavigationStatus enumeration for possible values.
   *
   * @note The robot should be stationary during relocalization for best results.
   * @note After calling this method, use is_localized() to verify successful
   *       relocalization before proceeding with navigation tasks.
   */
  virtual NavigationStatus relocalize(const Pose& init_pose) = 0;

  /**
   * @brief Check whether the robot is currently localized in the map.
   *
   * This method queries the localization system to determine if the robot has
   * a valid pose estimate with sufficient confidence. A robot that is not
   * localized should not perform navigation tasks.
   *
   * @return true if the robot is localized with acceptable confidence,
   *         false if localization is lost or uncertain.
   *
   * @note It is recommended to check localization status before issuing
   *       navigation commands.
   * @note If this returns false, consider calling relocalize() with a known
   *       pose estimate.
   */
  virtual bool is_localized() = 0;

  /**
   * @brief Get the current estimated pose of the robot chassis in the map frame.
   *
   * This method returns the most recent pose estimate from the localization system.
   * The pose represents the position and orientation of the robot's base_link frame
   * relative to the map frame origin.
   *
   * @return Pose: position (x, y, z) in meters and orientation as unit quaternion (x, y, z, w)
   *         in the map frame.
   *
   * @note The returned pose is only valid if is_localized() returns true.
   * @note The pose represents the center of the robot's base footprint.
   */
  virtual Pose get_current_pose() = 0;

  /**
   * @brief Navigate the robot to a target goal pose in the map frame.
   *
   * This method commands the mobile base to navigate to a specified goal pose using
   * the global path planner and local trajectory controller. The planner will compute
   * a collision-free path from the current pose to the goal, considering both static
   * map obstacles and dynamic obstacles if collision checking is enabled.
   *
   * @param goal_pose Target goal pose in the map frame: position (x, y, z) in meters and
   *                  target orientation as unit quaternion (x, y, z, w).
   * @param enable_collision_check If true, enables dynamic obstacle detection and
   *                               avoidance during navigation. If false, only static
   *                               map obstacles are considered. Default: true.
   * @param is_blocking Execution mode flag. Default: false.
   *                    - false (non-blocking): Returns immediately after sending the
   *                      navigation command. The return status indicates whether the
   *                      command was successfully sent, not whether the goal was reached.
   *                    - true (blocking): Blocks until the goal is reached, navigation
   *                      fails, or timeout occurs. The return status reflects the final
   *                      navigation outcome.
   * @param timeout Maximum wait time in seconds for blocking mode. Default: 8.0 seconds.
   *                Only relevant when is_blocking is true. If the goal is not reached
   *                within this time, the method returns with a timeout status.
   * @param omni_plan Motion planning mode flag. Default: true.
   *                  - true: Enables omnidirectional motion planning (holonomic drive),
   *                    allowing the robot to move in any direction and rotate independently.
   *                  - false: Uses differential drive planning with kinematic constraints.
   *
   * @return NavigationStatus indicating the result:
   *         - In non-blocking mode: Command acceptance status
   *         - In blocking mode: Final navigation outcome (success, failure, timeout)
   *
   * @note The robot must be localized (is_localized() returns true) before calling this method.
   * @note For blocking mode, the calling thread will be blocked until completion or timeout.
   * @note The actual navigation time may exceed the timeout value in blocking mode before
   *       the method returns.
   *
   * @warning In non-blocking mode, monitor navigation progress separately to detect
   *          completion or failures.
   */
  virtual NavigationStatus navigate_to_goal(const Pose& goal_pose, bool enable_collision_check = true,
                                            bool is_blocking = false, float timeout = 8, bool omni_plan = true) = 0;

  /**
   * @brief Move the robot to a relative target pose in the odometry frame.
   *
   * This method commands the robot to move to a pose specified relative to its
   * current position in the odometry (odom) frame. This is useful for short,
   * precise movements where map-based planning is not needed. Unlike navigate_to_goal(),
   * this method does NOT perform dynamic obstacle detection or global path planning.
   * It uses omnidirectional motion planning for direct movement to the target.
   *
   * @param goal_pose Target pose relative to the current base_link frame: position (x, y, z)
   *                  in meters (typically x forward, y left, z up) and relative orientation as
   *                  unit quaternion (x, y, z, w).
   * @param is_blocking Execution mode flag. Default: true.
   *                    - true (blocking): Blocks until the motion is complete, fails,
   *                      or timeout occurs. The return status reflects the final outcome.
   *                    - false (non-blocking): Returns immediately after sending the
   *                      motion command. The return status indicates command acceptance.
   * @param timeout Maximum wait time in seconds for blocking mode. Default: 8.0 seconds.
   *                Only relevant when is_blocking is true.
   *
   * @return NavigationStatus indicating the result:
   *         - In non-blocking mode: Command acceptance status
   *         - In blocking mode: Final motion outcome (success, failure, timeout)
   *
   * @note This method does NOT check for obstacles or collisions. Use only when the
   *       path is known to be clear.
   * @note This method uses the odometry frame and does NOT require map localization.
   * @note Suitable for small, precise adjustments such as final approach positioning
   *       or docking maneuvers.
   *
   * @warning Since collision checking is disabled, ensure the path is obstacle-free
   *          before calling this method to avoid collisions.
   * @warning Odometry drift may affect accuracy over longer distances. For accurate
   *          long-distance navigation, use navigate_to_goal() instead.
   */
  virtual NavigationStatus move_straight_to(const Pose& goal_pose, bool is_blocking = true, float timeout = 8) = 0;

  /**
   * @brief Stop the current navigation task and bring the robot to a halt.
   *
   * This method immediately cancels any ongoing navigation command (from either
   * navigate_to_goal() or move_straight_to()) and commands the robot to stop.
   * The robot will decelerate according to its kinematic constraints and come
   * to a safe stop.
   *
   * @return NavigationStatus indicating whether the stop command was successfully
   *         sent to the navigation system.
   *
   * @note This method can be called at any time during navigation, including
   *       when using non-blocking navigation modes.
   * @note After stopping, the robot's position may not match the original goal.
   * @note The robot will attempt to stop smoothly following its acceleration limits.
   */
  virtual NavigationStatus stop_navigation() = 0;

  /**
   * @brief Check if a collision-free path exists from start to goal in the map.
   *
   * This method queries the global path planner to determine if a valid,
   * collision-free path exists between the specified start and goal poses.
   * This is useful for validating goal poses before attempting navigation,
   * or for multi-goal path planning.
   *
   * @param goal_pose Goal pose in the map frame: position (x, y, z) in meters and orientation
   *                  quaternion (x, y, z, w).
   * @param start_pose Start pose in the map frame: position (x, y, z) in meters and orientation
   *                   quaternion (x, y, z, w).
   *
   * @return true if a collision-free path exists from start to goal,
   *         false if no valid path can be found.
   *
   * @note This method only checks for static obstacles based on the map data.
   *       Dynamic obstacles are not considered.
   * @note The path computation may take some time depending on distance and
   *       map complexity.
   * @note A return value of true does not guarantee successful navigation, as
   *       dynamic obstacles or localization errors may still cause failures.
   */
  virtual bool check_path_reachability(const Pose& goal_pose, const Pose& start_pose) = 0;

  /**
   * @brief Check if the robot has successfully reached the current goal.
   *
   * This method queries the navigation system to determine if the robot has
   * arrived at the goal pose within acceptable position and orientation tolerances.
   * This is particularly useful when using non-blocking navigation mode to poll
   * for completion.
   *
   * @return true if the robot has reached the goal within tolerance thresholds,
   *         false if still navigating, no active goal, or goal not yet reached.
   *
   * @note This method is most useful in non-blocking navigation scenarios where
   *       the application needs to monitor progress.
   * @note The tolerance thresholds for "arrival" are defined by the navigation
   *       system's internal parameters (typically a few centimeters in position
   *       and a few degrees in orientation).
   * @note If no navigation command is active, this method returns false.
   */
  virtual bool check_goal_arrival() = 0;

  /**
   * @brief Get the current navigation task state.
   *
   * Returns the most recent task state reported by the navigation system
   * (UNKNOWN, RUNNING, SUCCESS, or FAILED). Use this when running non-blocking
   * navigation to poll for state and exit error logic in time on FAILED or
   * timeout, avoiding deadlock or indefinite wait.
   *
   * @return NavigationTaskStatus Current task state. UNKNOWN if no status yet;
   *         RUNNING while navigating; SUCCESS or FAILED when task has finished.
   *
   * @note Useful in non-blocking navigation: loop on get_navigation_status()
   *       and break on SUCCESS, FAILED, or after a timeout.
   */
  virtual NavigationTaskStatus get_navigation_status() = 0;
};

}  // namespace sdk
}  // namespace galbot
