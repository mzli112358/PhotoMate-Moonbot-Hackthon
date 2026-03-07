#include <chrono>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

#include "galbot_motion.hpp"
#include "galbot_robot.hpp"

using namespace galbot::sdk::g1;

void print_link_names(const std::vector<std::string>& link_names, const std::string& title) {
  std::cout << title << " (共 " << link_names.size() << " 个):" << std::endl;
  for (size_t i = 0; i < link_names.size(); ++i) {
    std::cout << "  " << (i + 1) << ". " << link_names[i] << std::endl;
  }
}

int main() {
  // 获取对象实例
  auto& motion = GalbotMotion::get_instance();
  auto& robot = GalbotRobot::get_instance();

  // 初始化系统
  if (!motion.init()) {
    std::cerr << "GalbotMotion 初始化失败！" << std::endl;
    return -1;
  }
  if (!robot.init()) {
    std::cerr << "GalbotRobot 初始化失败！" << std::endl;
    return -1;
  }

  std::cout << "系统初始化成功！" << std::endl;

  // 程序立即启动，稍等数据就绪时间
  std::this_thread::sleep_for(std::chrono::milliseconds(2000));

  try {
    // 获取所有连杆名称
    std::vector<std::string> all_link_names = motion.get_link_names(false);
    print_link_names(all_link_names, "\n所有连杆名称");

    // 只获取末端执行器连杆名称
    std::vector<std::string> ee_link_names = motion.get_link_names(true);
    print_link_names(ee_link_names, "\n末端执行器连杆名称");
  } catch (const std::exception& e) {
    std::cerr << "获取连杆名称异常: " << e.what() << std::endl;
  }

  // 退出系统并进行SDK资源释放
  robot.request_shutdown();
  robot.wait_for_shutdown();
  robot.destroy();

  return 0;
}
