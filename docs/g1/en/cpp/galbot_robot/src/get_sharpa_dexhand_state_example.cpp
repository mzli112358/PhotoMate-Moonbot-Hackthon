#include <chrono>
#include <iostream>
#include <thread>
#include <vector>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

void print_joint_state(const std::string& hand_name, const JointStateMessage& joint_state) {
  std::cout << hand_name << " Sharpa dexhand joint state:" << std::endl;
  const auto& joint_state_vec = joint_state.joint_state_vec;
  for (size_t i = 0; i < joint_state_vec.size(); ++i) {
    const auto& js = joint_state_vec[i];
    std::cout << "  joint" << (i + 1) << ": position=" << js.position << ", velocity=" << js.velocity
              << ", effort=" << js.effort << ", current=" << js.current << std::endl;
  }
}

void print_force_sensors(const std::unordered_map<std::string, EffortInfo>& force_sensor_map) {
  if (force_sensor_map.empty()) {
    std::cout << "  (no force sensor data)" << std::endl;
    return;
  }
  for (const auto& sensor_pair : force_sensor_map) {
    const auto& effort = sensor_pair.second;
    std::cout << "  " << sensor_pair.first << " @ " << effort.timestamp_ns
              << ": Fx=" << effort.force.x << ", Fy=" << effort.force.y << ", Fz=" << effort.force.z
              << ", Mx=" << effort.torque.x << ", My=" << effort.torque.y << ", Mz=" << effort.torque.z
              << std::endl;
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

  // Get left Sharpa dexhand state
  DexhandState left_dexhand_state;
  auto status = robot.get_dexhand_state("left_dexhand", left_dexhand_state, DexHandType::SHARPA);

  if (status == ControlStatus::SUCCESS) {
    std::cout << "Left Sharpa dexhand full state:" << std::endl;
    std::cout << "Timestamp (ns): " << left_dexhand_state.timestamp_ns << std::endl;
    print_joint_state("Left", left_dexhand_state.joint_state);
    std::cout << "Force sensors:" << std::endl;
    print_force_sensors(left_dexhand_state.force_sensor_map);
  } else {
    std::cerr << "Failed to get left Sharpa dexhand state!" << std::endl;
  }

  // Get right Sharpa dexhand state
  DexhandState right_dexhand_state;
  status = robot.get_dexhand_state("right_dexhand", right_dexhand_state, DexHandType::SHARPA);

  if (status == ControlStatus::SUCCESS) {
    std::cout << "Right Sharpa dexhand full state:" << std::endl;
    std::cout << "Timestamp (ns): " << right_dexhand_state.timestamp_ns << std::endl;
    print_joint_state("Right", right_dexhand_state.joint_state);
    std::cout << "Force sensors:" << std::endl;
    print_force_sensors(right_dexhand_state.force_sensor_map);
  } else {
    std::cerr << "Failed to get right Sharpa dexhand state!" << std::endl;
  }

  // Exit system and release SDK resources
  robot.request_shutdown();
  robot.wait_for_shutdown();
  robot.destroy();

  return 0;
}
