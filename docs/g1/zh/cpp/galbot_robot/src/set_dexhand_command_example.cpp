#include <chrono>
#include <cstdlib>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

namespace {

DexHandType parse_dexhand_type(const std::string& type_name) {
  if (type_name == "inspire" || type_name == "INSPIRE") {
    return DexHandType::INSPIRE;
  }
  if (type_name == "brainco" || type_name == "BRAINCO") {
    return DexHandType::BRAINCO;
  }
  if (type_name == "sharpa" || type_name == "SHARPA") {
    return DexHandType::SHARPA;
  }
  std::cerr << "Unknown dexhand type '" << type_name << "'. Choose from: inspire, brainco, sharpa"
            << std::endl;
  std::exit(1);
}

size_t dexhand_joint_count(DexHandType dexhand_type) {
  return dexhand_type == DexHandType::SHARPA ? 22 : 6;
}

std::vector<JointCommand> make_dexhand_command(size_t joint_count, double position) {
  std::vector<JointCommand> commands(joint_count);
  for (auto& cmd : commands) {
    cmd.position = position;
  }
  return commands;
}

void default_positions(DexHandType dexhand_type, double& left_position, double& right_position) {
  if (dexhand_type == DexHandType::SHARPA) {
    left_position = 0.0;
    right_position = 0.0;
    return;
  }
  if (dexhand_type == DexHandType::BRAINCO) {
    left_position = 50.0;
    right_position = 80.0;
    return;
  }
  left_position = 500.0;
  right_position = 800.0;
}

const char* dexhand_type_label(DexHandType dexhand_type) {
  switch (dexhand_type) {
    case DexHandType::BRAINCO:
      return "brainco";
    case DexHandType::SHARPA:
      return "sharpa";
    case DexHandType::INSPIRE:
    default:
      return "inspire";
  }
}

void print_usage(const char* program_name) {
  std::cerr << "Usage: " << program_name << " [inspire|brainco|sharpa]" << std::endl;
  std::cerr << "  inspire (default): 6 joints, position range 0-1000" << std::endl;
  std::cerr << "  brainco:           6 joints, position range 0-100" << std::endl;
  std::cerr << "  sharpa:            22 joints, relaxed position uses 0.0" << std::endl;
}

}  // namespace

int main(int argc, char* argv[]) {
  std::string type_arg = "inspire";
  if (argc > 2) {
    print_usage(argv[0]);
    return 1;
  }
  if (argc == 2) {
    type_arg = argv[1];
  }

  const auto dexhand_type = parse_dexhand_type(type_arg);
  const char* type_label = dexhand_type_label(dexhand_type);

  auto& robot = GalbotRobot::get_instance(MachineType::G1);

  if (robot.init()) {
    std::cout << "System initialized successfully!" << std::endl;
  } else {
    std::cerr << "System initialization failed!" << std::endl;
    return -1;
  }

  std::this_thread::sleep_for(std::chrono::milliseconds(2000));

  const size_t joint_count = dexhand_joint_count(dexhand_type);
  double left_position = 0.0;
  double right_position = 0.0;
  default_positions(dexhand_type, left_position, right_position);

  const bool is_blocking = false;

  auto left_command = make_dexhand_command(joint_count, left_position);
  ControlStatus status =
      robot.set_dexhand_command("left_dexhand", left_command, dexhand_type, is_blocking);

  if (status == ControlStatus::SUCCESS) {
    std::cout << "Set left " << type_label << " dexhand successfully (" << joint_count
              << " joints, position=" << left_position << ")!" << std::endl;
  } else {
    std::cerr << "Failed to set left " << type_label << " dexhand command!" << std::endl;
  }

  const int sleep_ms = dexhand_type == DexHandType::SHARPA ? 1000 : 2000;
  std::this_thread::sleep_for(std::chrono::milliseconds(sleep_ms));

  auto right_command = make_dexhand_command(joint_count, right_position);
  status = robot.set_dexhand_command("right_dexhand", right_command, dexhand_type, is_blocking);

  if (status == ControlStatus::SUCCESS) {
    std::cout << "Set right " << type_label << " dexhand successfully (" << joint_count
              << " joints, position=" << right_position << ")!" << std::endl;
  } else {
    std::cerr << "Failed to set right " << type_label << " dexhand command!" << std::endl;
  }

  robot.request_shutdown();
  robot.wait_for_shutdown();
  robot.destroy();

  return 0;
}
