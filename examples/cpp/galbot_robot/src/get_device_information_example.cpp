#include <chrono>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

#include "galbot_robot.hpp"

using namespace galbot::sdk::g1;

void print_device_info(const std::shared_ptr<DeviceInfo>& device_info) {
  if (!device_info) {
    std::cerr << "Device information is empty" << std::endl;
    return;
  }

  std::cout << "设备信息：" << std::endl;
  std::cout << "  型号: " << (device_info->model.empty() ? "N/A" : device_info->model) << std::endl;
  std::cout << "  序列号: " << (device_info->serial_number.empty() ? "N/A" : device_info->serial_number) << std::endl;
  std::cout << "  固件版本: " << (device_info->firmware_version.empty() ? "N/A" : device_info->firmware_version)
            << std::endl;
  std::cout << "  硬件版本: " << (device_info->hardware_version.empty() ? "N/A" : device_info->hardware_version)
            << std::endl;
  std::cout << "  制造商: " << (device_info->manufacturer.empty() ? "N/A" : device_info->manufacturer) << std::endl;
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
  std::this_thread::sleep_for(std::chrono::milliseconds(1000));

  // 获取设备信息
  std::shared_ptr<DeviceInfo> device_info = robot.get_device_information();
  if (device_info) {
    std::cout << "设备信息获取成功！" << std::endl;
    print_device_info(device_info);
  } else {
    std::cerr << "设备信息获取失败！" << std::endl;
  }

  // 退出系统并进行SDK资源释放
  robot.request_shutdown();
  robot.wait_for_shutdown();
  robot.destroy();

  return 0;
}
