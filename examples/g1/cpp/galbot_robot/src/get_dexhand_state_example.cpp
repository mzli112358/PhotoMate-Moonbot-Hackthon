#include <chrono>
#include <iostream>
#include <thread>
#include <vector>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

void print_joint_states(const std::string& hand_name, const DexhandState& dexhand_state) {
  std::cout << hand_name << " dexterous hand state:" << std::endl;
  std::cout << "Timestamp (ns): " << dexhand_state.timestamp_ns << std::endl;

  const auto& joint_state_vec = dexhand_state.joint_state.joint_state_vec;
  for (size_t i = 0; i < joint_state_vec.size(); ++i) {
    const auto& js = joint_state_vec[i];
    std::cout << "  " << hand_name << "_dexhand_joint" << (i + 1) << ": position=" << js.position
              << ", velocity=" << js.velocity << ", acceleration=" << js.acceleration
              << ", effort=" << js.effort << ", current=" << js.current << std::endl;
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

  // Get left dexhand state
  DexhandState left_dexhand_state;
  auto status = robot.get_dexhand_state("left_dexhand", left_dexhand_state, DexHandType::INSPIRE);

  if (status == ControlStatus::SUCCESS) {
    print_joint_states("Left", left_dexhand_state);
  } else {
    std::cerr << "Failed to get left dexterous hand state!" << std::endl;
  }

  // Get right dexhand state
  DexhandState right_dexhand_state;
  status = robot.get_dexhand_state("right_dexhand", right_dexhand_state, DexHandType::INSPIRE);

  if (status == ControlStatus::SUCCESS) {
    print_joint_states("Right", right_dexhand_state);
  } else {
    std::cerr << "Failed to get right dexterous hand state!" << std::endl;
  }

  // Exit system and release SDK resources
  robot.request_shutdown();
  robot.wait_for_shutdown();
  robot.destroy();

  return 0;
}
