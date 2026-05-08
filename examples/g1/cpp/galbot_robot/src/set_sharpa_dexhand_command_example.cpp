#include <chrono>
#include <iostream>
#include <thread>
#include <vector>

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

  // Set left Sharpa dexhand command (22 joints)
  std::vector<JointCommand> dexhand_command(22);

  // Relaxed position (all zeros)
  for (int i = 0; i < 22; ++i) {
    dexhand_command[i].position = 0.0;
  }

  bool is_blocking = false;
  ControlStatus status = robot.set_dexhand_command("left_dexhand", dexhand_command, DexHandType::SHARPA, is_blocking);

  if (status == ControlStatus::SUCCESS) {
    std::cout << "Set left Sharpa dexhand relaxed position successfully!" << std::endl;
  } else {
    std::cerr << "Failed to set left Sharpa dexhand command!" << std::endl;
  }

  std::this_thread::sleep_for(std::chrono::milliseconds(1000));

  // Set right Sharpa dexhand command with relaxed position
  status = robot.set_dexhand_command("right_dexhand", dexhand_command, DexHandType::SHARPA, is_blocking);

  if (status == ControlStatus::SUCCESS) {
    std::cout << "Set right Sharpa dexhand relaxed position successfully!" << std::endl;
  } else {
    std::cerr << "Failed to set right Sharpa dexhand command!" << std::endl;
  }

  // Exit system and release SDK resources
  robot.request_shutdown();
  robot.wait_for_shutdown();
  robot.destroy();

  return 0;
}
