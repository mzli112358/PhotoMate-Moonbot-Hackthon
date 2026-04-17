#include <chrono>
#include <iostream>
#include <memory>
#include <string>
#include <thread>
#include <vector>

#include "galbot_motion.hpp"
#include "galbot_robot.hpp"

using namespace galbot::sdk;

// Helper function: print pose information
void print_pose_info(const std::string& label, const std::vector<double>& pose) {
  if (pose.size() == 7) {
    std::cout << "[" << label << "] Pose: "
              << "pos(" << pose[0] << ", " << pose[1] << ", " << pose[2] << "), "
              << "ori(" << pose[3] << ", " << pose[4] << ", " << pose[5] << ", " << pose[6] << ")" << std::endl;
  }
}

int main() {
  auto& planner = GalbotMotion::get_instance(MachineType::S1);
  auto& robot = GalbotRobot::get_instance(MachineType::S1);

  if (!planner.init()) {
    std::cerr << "GalbotMotion initialization failed" << std::endl;
    return -1;
  }
  if (!robot.init()) {
    std::cerr << "GalbotRobot initialization failed" << std::endl;
    return -1;
  }

  std::this_thread::sleep_for(std::chrono::milliseconds(1000));

  std::string reference_frame = "base_link";
  std::string target_frame = "EndEffector";
  std::string target_chain = "right_arm";
  std::string end_ee_link = "right_arm_end_effector_mount_link";
  auto custom_param = std::make_shared<Parameter>();

  // --- Scenario 1: Get end-effector pose (basic version) ---
  try {
    std::cout << ">> Scenario 1: Getting the basic end-effector pose..." << std::endl;

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
  std::vector<double> current_pose;
  try {
    std::cout << ">> Scenario 2: Getting pose by specified chain name..." << std::endl;

    auto res = planner.get_end_effector_pose_on_chain(target_chain, target_frame, reference_frame);

    MotionStatus status = std::get<0>(res);
    current_pose = std::get<1>(res);

    std::cout << "Execution status: " << planner.status_to_string(status) << std::endl;
    if (status == MotionStatus::SUCCESS) {
      print_pose_info("Specified chain name version", current_pose);
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(800));
  } catch (const std::exception& e) {
    std::cerr << "❌ Scenario 2 exception: " << e.what() << std::endl;
  }

  // --- Scenario 3: Set end-effector pose (small offset from current pose) ---
  try {
    std::cout << ">> Scenario 3: Setting end-effector pose..." << std::endl;

    if (current_pose.size() != 7) {
      std::cerr << "❌ Unable to get current pose; skipping Scenario 3" << std::endl;
    } else {
      std::vector<double> target_pose = current_pose;
      target_pose[2] -= 0.05;  // Move downward 5 cm in z direction

      print_pose_info("Target pose", target_pose);

      MotionStatus status = planner.set_end_effector_pose(target_pose,      // 1. target_pose
                                                          target_chain,     // 2. chain_name
                                                          reference_frame,  // 3. reference_frame
                                                          nullptr,          // 4. reference_robot_states
                                                          false,            // 5. enable_collision_check
                                                          true,             // 6. is_blocking
                                                          5.0,              // 7. timeout
                                                          custom_param      // 8. params
      );

      std::cout << "Set status: " << planner.status_to_string(status) << std::endl;
      if (status == MotionStatus::SUCCESS) {
        std::cout << "✅ Motion execution completed" << std::endl;
      }
    }
  } catch (const std::exception& e) {
    std::cerr << "❌ Pose-setting exception: " << e.what() << std::endl;
  }

  // --- Scenario 4: Get end-effector pose after execution to verify result ---
  try {
    std::cout << ">> Scenario 4: Getting end-effector pose after motion..." << std::endl;

    auto res = planner.get_end_effector_pose(end_ee_link, reference_frame);

    MotionStatus status = std::get<0>(res);
    std::vector<double> pose = std::get<1>(res);

    std::cout << "Execution status: " << planner.status_to_string(status) << std::endl;
    if (status == MotionStatus::SUCCESS) {
      print_pose_info("After motion", pose);
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
