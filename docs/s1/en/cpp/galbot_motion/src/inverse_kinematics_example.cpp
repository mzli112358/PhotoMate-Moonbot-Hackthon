#include <chrono>
#include <iostream>
#include <memory>
#include <string>
#include <thread>
#include <tuple>
#include <unordered_map>
#include <vector>

#include "galbot_motion.hpp"
#include "galbot_robot.hpp"

using namespace galbot::sdk;

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
  auto& planner = GalbotMotion::get_instance(MachineType::S1);
  auto& robot = GalbotRobot::get_instance(MachineType::S1);

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

  std::string reference_frame = "base_link";
  std::string target_frame = "EndEffector";
  std::string target_chain = "left_arm";
  auto params = std::make_shared<Parameter>();

  // Get current end-effector pose from robot as target for subsequent IK scenarios
  std::vector<double> target_pose;
  {
    auto [status, pose] = planner.get_end_effector_pose_on_chain(target_chain, target_frame, reference_frame);
    if (status != MotionStatus::SUCCESS || pose.size() != 7) {
      std::cerr << "Failed to get current end-effector pose, cannot continue test." << std::endl;
      return -1;
    }
    target_pose = pose;
    std::cout << "Current " << target_chain << " End-effector pose: ";
    for (double v : target_pose)
      std::cout << v << " ";
    std::cout << std::endl;
    std::cout << "---------------------------------------------------" << std::endl;
  }

  // Scenario 1: Single-chain inverse kinematics (using default parameters)
  try {
    std::cout << ">> Running Scenario 1: Single-chain IK test..." << std::endl;
    std::vector<std::string> one_chain = {target_chain};

    auto res = planner.inverse_kinematics(target_pose, one_chain);
    print_ik_result("Single-chain inverse kinematics", res, planner);
    std::this_thread::sleep_for(std::chrono::milliseconds(800));
  } catch (const std::exception& e) {
    std::cerr << "Scenario 1 exception: " << e.what() << std::endl;
  }

  // Scenario 2: Arm chain + torso inverse kinematics
  try {
    std::cout << ">> Running Scenario 2: Arm chain + torso IK test..." << std::endl;
    std::vector<std::string> chain_with_torso = {target_chain, "torso"};

    auto res =
        planner.inverse_kinematics(target_pose, chain_with_torso, target_frame, reference_frame, {}, false, params);
    print_ik_result("Arm + torso inverse kinematics", res, planner);
    std::this_thread::sleep_for(std::chrono::milliseconds(800));
  } catch (const std::exception& e) {
    std::cerr << "Scenario 2 exception: " << e.what() << std::endl;
  }

  // Scenario 3: invalid chain combination (expected to return INVALID_INPUT)
  try {
    std::cout << ">> Running Scenario 3: Invalid chain-combination test..." << std::endl;
    std::vector<std::string> error_chains = {target_chain, "torso", "head"};

    auto res = planner.inverse_kinematics(target_pose, error_chains, target_frame, reference_frame, {}, false, params);
    print_ik_result("Invalid chain combination detection", res, planner);
  } catch (const std::exception& e) {
    std::cerr << "Scenario 3 exception: " << e.what() << std::endl;
  }

  // Scenario 4: Inverse kinematics with initial reference joint values (using current robot state)
  try {
    std::cout << ">> Running Scenario 4: IK test with initial reference values..." << std::endl;
    std::vector<std::string> one_chain = {target_chain};

    auto current_chain_joints = planner.get_chain_joint_state();
    std::cout << "  Current joint states:" << std::endl;
    for (const auto& [name, joints] : current_chain_joints) {
      std::cout << "    [" << name << "]: ";
      for (double v : joints)
        std::cout << v << " ";
      std::cout << std::endl;
    }

    auto res = planner.inverse_kinematics(target_pose, one_chain, target_frame, reference_frame, current_chain_joints,
                                          false, params);
    print_ik_result("Inverse kinematics with reference values", res, planner);
    std::this_thread::sleep_for(std::chrono::milliseconds(800));
  } catch (const std::exception& e) {
    std::cerr << "Scenario 4 exception: " << e.what() << std::endl;
  }

  // Scenario 5: Inverse kinematics based on RobotStates (get full state from robot)
  try {
    std::cout << ">> Running Scenario 5: IK test based on RobotStates..." << std::endl;

    auto robot_states = planner.get_robot_states();
    auto ref_state = std::make_shared<RobotStates>(robot_states);
    ref_state->chain_name = target_chain;

    std::cout << "  Number of whole-body joints: " << ref_state->whole_body_joint.size() << std::endl;
    std::cout << "  Number of chassis states: " << ref_state->base_state.size() << std::endl;

    std::vector<std::string> one_chain = {target_chain};

    auto res = planner.inverse_kinematics_by_state(target_pose, one_chain, target_frame, reference_frame, ref_state,
                                                   false, params);
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
