#include <chrono>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <string>
#include <thread>
#include <tuple>
#include <unordered_map>
#include <vector>

#include "galbot_motion.hpp"
#include "galbot_robot.hpp"

using namespace galbot::sdk;

void print_vector(const std::vector<double>& values) {
  std::cout << "[";
  for (size_t i = 0; i < values.size(); ++i) {
    if (i > 0) {
      std::cout << ", ";
    }
    std::cout << values[i];
  }
  std::cout << "]";
}

void print_joint_state(const std::unordered_map<std::string, std::vector<double>>& joint_state) {
  std::cout << "{" << std::endl;
  for (const auto& pair : joint_state) {
    std::cout << "    " << pair.first << ": ";
    print_vector(pair.second);
    std::cout << std::endl;
  }
  std::cout << "  }" << std::endl;
}

void print_get_jacobian_params(const std::string& chain_name,
                               const std::string& target_frame,
                               const std::string& reference_frame,
                               const std::unordered_map<std::string, std::vector<double>>& joint_state) {
  std::cout << "get_jacobian parameters:" << std::endl;
  std::cout << "  chain_name: " << chain_name << std::endl;
  std::cout << "  target_frame: " << target_frame << std::endl;
  std::cout << "  reference_frame: " << reference_frame << std::endl;
  std::cout << "  joint_state: ";
  print_joint_state(joint_state);
}

void print_jacobian(const std::string& label,
                    const std::tuple<MotionStatus, std::vector<std::vector<double>>>& result,
                    GalbotMotion& motion) {
  const auto status = std::get<0>(result);
  const auto& matrix = std::get<1>(result);

  std::cout << "[" << label << "] Status: " << motion.status_to_string(status) << std::endl;
  if (status != MotionStatus::SUCCESS || matrix.empty()) {
    std::cout << "Jacobian computation failed or returned an empty matrix." << std::endl;
    return;
  }

  std::cout << "Jacobian matrix (" << matrix.size() << "x" << matrix[0].size() << "):" << std::endl;
  for (size_t r = 0; r < matrix.size(); ++r) {
    std::cout << "  row " << r << ": ";
    for (double value : matrix[r]) {
      std::cout << std::setw(10) << std::fixed << std::setprecision(5) << value << " ";
    }
    std::cout << std::endl;
  }
}

std::vector<double> make_fixed_joint_values(size_t dof) {
  static const std::vector<double> fixed_values = {-1.2, -0.8, -0.4, 0.0, 0.4, 0.8, 1.2};
  std::vector<double> values;
  values.reserve(dof);
  for (size_t i = 0; i < dof; ++i) {
    values.push_back(fixed_values[i % fixed_values.size()]);
  }
  return values;
}

size_t get_chain_dof(const std::string& chain_name,
                     const std::unordered_map<std::string, std::vector<double>>& current_chain_joint_state) {
  const auto current_it = current_chain_joint_state.find(chain_name);
  if (current_it != current_chain_joint_state.end() && !current_it->second.empty()) {
    return current_it->second.size();
  }

  const std::map<std::string, size_t> fallback_dof = {
      {"head", 2}, {"left_arm", 7}, {"right_arm", 7}, {"leg", 5}, {"torso", 1}};
  const auto fallback_it = fallback_dof.find(chain_name);
  if (fallback_it != fallback_dof.end()) {
    return fallback_it->second;
  }
  return 0;
}

int main() {
  auto& motion = GalbotMotion::get_instance(MachineType::G1);
  auto& robot = GalbotRobot::get_instance(MachineType::G1);

  if (!motion.init()) {
    std::cerr << "GalbotMotion initialization failed." << std::endl;
    return 1;
  }
  if (!robot.init()) {
    std::cerr << "GalbotRobot initialization failed." << std::endl;
    return 1;
  }

  std::this_thread::sleep_for(std::chrono::seconds(3));

  std::set<std::string> support_chains = motion.get_support_chains();
  if (support_chains.empty()) {
    support_chains = {"head", "left_arm", "right_arm", "leg"};
  }

  std::unordered_map<std::string, std::vector<double>> current_chain_joint_state;
  try {
    current_chain_joint_state = motion.get_chain_joint_state();
  } catch (const std::exception& e) {
    std::cerr << "get_chain_joint_state exception: " << e.what() << std::endl;
  }

  const std::string target_frame = "EndEffector";
  const std::string reference_frame = "base_link";

  for (const auto& chain_name : support_chains) {
    const size_t dof = get_chain_dof(chain_name, current_chain_joint_state);
    if (dof == 0) {
      std::cerr << "Skip chain '" << chain_name << "': unable to determine chain DOF." << std::endl;
      continue;
    }

    std::unordered_map<std::string, std::vector<double>> joint_state = {
        {chain_name, make_fixed_joint_values(dof)}};

    try {
      std::cout << "=== get_jacobian: " << chain_name << " ===" << std::endl;
      print_get_jacobian_params(chain_name, target_frame, reference_frame, joint_state);
      auto result = motion.get_jacobian(chain_name, target_frame, reference_frame, joint_state);
      print_jacobian(chain_name, result, motion);
    } catch (const std::exception& e) {
      std::cerr << chain_name << " exception: " << e.what() << std::endl;
    }
  }

  robot.request_shutdown();
  robot.wait_for_shutdown();
  robot.destroy();

  return 0;
}
