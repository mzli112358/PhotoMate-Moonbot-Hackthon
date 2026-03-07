#include <chrono>
#include <cmath>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

#include "galbot_robot.hpp"

using namespace galbot::sdk::g1;

std::string control_status_to_string(ControlStatus status) {
  switch (status) {
    case ControlStatus::SUCCESS:
      return "SUCCESS";
    case ControlStatus::INVALID_INPUT:
      return "INVALID_INPUT";
    case ControlStatus::INIT_FAILED:
      return "INIT_FAILED";
    case ControlStatus::COMM_DISCONNECTED:
      return "COMM_DISCONNECTED";
    case ControlStatus::FAULT:
      return "FAULT";
    case ControlStatus::PUBLISH_FAIL:
      return "PUBLISH_FAIL";
    default:
      return "UNKNOWN_STATUS";
  }
}

std::vector<TrajectoryPoint> generate_batch_trajectory(int32_t joint_size, double ampl = 0.2, double cycle = 10,
                                                       int num_points = 10) {
  double amplitude = -ampl;
  double frequency = 1.0 / cycle;
  double phase = -M_PI / 2;
  double offset = amplitude;
  double dt = cycle / num_points;

  std::vector<TrajectoryPoint> trajectory_data_vec;
  trajectory_data_vec.resize(num_points);
  // 创建批量轨迹点
  for (int i = 0; i < num_points; ++i) {
    double t = i * dt;
    trajectory_data_vec[i].time_from_start_second = t;
    trajectory_data_vec[i].joint_command_vec.resize(joint_size);
    // 添加关节命令
    for (int j = 0; j < joint_size; ++j) {
      trajectory_data_vec[i].joint_command_vec[j].position =
          offset + amplitude * std::sin(2 * M_PI * frequency * t + phase);
      trajectory_data_vec[i].joint_command_vec[j].velocity =
          amplitude * 2 * M_PI * frequency * std::cos(2 * M_PI * frequency * t + phase);
      // trajectory_data_vec[i].joint_command_vec[j].acceleration = 0.0;
      // trajectory_data_vec[i].joint_command_vec[j].effort = 0.0;
    }
  }

  return trajectory_data_vec;
}

int main() {
  // 获取对象实例
  auto& robot = GalbotRobot::get_instance();

  // 初始化系统
  if (robot.init()) {
    std::cout << "系统初始化成功！" << std::endl;
  } else {
    std::cerr << "系统初始化失败！" << std::endl;
    return -1;
  }

  // 程序立即启动，稍等数据就绪时间
  std::this_thread::sleep_for(std::chrono::milliseconds(2000));

  // 批量设置关节指令
  Trajectory trajectory;
  // 填写要控制的关节组名称，关节组名称包括["leg", "head", "left_arm", "right_arm", "left_gripper", "right_gripper"]
  trajectory.joint_groups = {"head"};
  // 如需控制指定关节角度，可填写该字段，如填写将覆盖joint_groups字段
  trajectory.joint_names = {};
  // 生成批量轨迹点（包含多个时间点的关节指令）
  trajectory.points = generate_batch_trajectory(2, 0.2, 10.0, 10);

  // 批量设置关节指令（非阻塞，立即返回）
  ControlStatus status = robot.set_joint_commands_batch(trajectory);
  std::cout << "批量设置关节指令状态: " << control_status_to_string(status) << std::endl;

  if (status == ControlStatus::SUCCESS) {
    std::cout << "批量指令已提交，正在后台执行（非阻塞）" << std::endl;
  } else {
    std::cerr << "批量指令提交失败！" << std::endl;
  }

  // 等待一段时间让指令执行
  std::this_thread::sleep_for(std::chrono::milliseconds(1000));

  // 退出系统并进行SDK资源释放
  robot.request_shutdown();
  robot.wait_for_shutdown();
  robot.destroy();

  return 0;
}
