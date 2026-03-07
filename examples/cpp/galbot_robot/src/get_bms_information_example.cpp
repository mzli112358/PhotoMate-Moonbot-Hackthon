#include <iostream>
#include <chrono>
#include <thread>
#include <string>

#include "galbot_robot.hpp"

using namespace galbot::sdk::g1;

void print_bms_information(const std::shared_ptr<BmsInfo>& bms_info) {
    if (!bms_info) {
        std::cerr << "BMS信息为空" << std::endl;
        return;
    }

    std::cout << "Voltage (V): " << bms_info->voltage << std::endl;
    std::cout << "Current (A): " << bms_info->current << std::endl;
    std::cout << "Battery level (%): " << bms_info->battery_level << std::endl;
    std::cout << "Temperature (C): " << bms_info->temperature << std::endl;
    std::cout << "Charging status: " << std::boolalpha << bms_info->charging_status
              << std::noboolalpha << std::endl;
    std::cout << "Health status: " << std::boolalpha << bms_info->health_status
              << std::noboolalpha << std::endl;
    std::cout << "Capacity (Ah): " << bms_info->capacity << std::endl;
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
    std::this_thread::sleep_for(std::chrono::milliseconds(3000));

    // 获取BMS信息
    auto bms_info = robot.get_bms_information();
    if (bms_info) {
        std::cout << "BMS信息获取成功！" << std::endl;
        print_bms_information(bms_info);
    } else {
        std::cerr << "BMS信息获取失败！" << std::endl;
    }

    // 退出系统并进行SDK资源释放
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
