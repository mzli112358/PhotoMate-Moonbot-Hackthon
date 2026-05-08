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

  // Set left dexhand command (6 joints)
  std::vector<JointCommand> dexhand_command(6);
  // Set each joint position (range depends on dexhand type: inspire 0-1000, brainco 0-100)
  dexhand_command[0].position = 500;
  dexhand_command[1].position = 500;
  dexhand_command[2].position = 500;
  dexhand_command[3].position = 500;
  dexhand_command[4].position = 500;
  dexhand_command[5].position = 500;

  bool is_blocking = false;
  ControlStatus status = robot.set_dexhand_command("left_dexhand", dexhand_command, DexHandType::INSPIRE, is_blocking);

  if (status == ControlStatus::SUCCESS) {
    std::cout << "Set left dexhand command successfully!" << std::endl;
  } else {
    std::cerr << "Failed to set left dexhand command!" << std::endl;
  }

  std::this_thread::sleep_for(std::chrono::milliseconds(2000));

  // Set right dexhand command with different positions
  dexhand_command[0].position = 800;
  dexhand_command[1].position = 800;
  dexhand_command[2].position = 800;
  dexhand_command[3].position = 800;
  dexhand_command[4].position = 800;
  dexhand_command[5].position = 800;

  is_blocking = false;
  status = robot.set_dexhand_command("right_dexhand", dexhand_command, DexHandType::INSPIRE, is_blocking);

  if (status == ControlStatus::SUCCESS) {
    std::cout << "Set right dexhand command successfully!" << std::endl;
  } else {
    std::cerr << "Failed to set right dexhand command!" << std::endl;
  }

  // Exit system and release SDK resources
  robot.request_shutdown();
  robot.wait_for_shutdown();
  robot.destroy();

  return 0;
}
