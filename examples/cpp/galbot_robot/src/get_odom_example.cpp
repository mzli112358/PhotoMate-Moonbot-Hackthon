#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <string>

#include "galbot_robot.hpp"

using namespace galbot::sdk::g1;

void print_odom_data(const std::shared_ptr<OdomData>& odom_data) {
    if (!odom_data) {
        std::cerr << "Odom data is empty" << std::endl;
        return;
    }

    std::cout << "Timestamp (ns): " << odom_data->timestamp_ns << std::endl;

    std::cout << "Position (m): "
              << "x=" << odom_data->position[0] << ", "
              << "y=" << odom_data->position[1] << ", "
              << "z=" << odom_data->position[2] << std::endl;

    std::cout << "Orientation (quaternion): "
              << "qx=" << odom_data->orientation[0] << ", "
              << "qy=" << odom_data->orientation[1] << ", "
              << "qz=" << odom_data->orientation[2] << ", "
              << "qw=" << odom_data->orientation[3] << std::endl;
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

    // 获取里程计数据
    std::shared_ptr<OdomData> odom_data = robot.get_odom();
    if (odom_data) {
        std::cout << "里程计数据获取成功！" << std::endl;
        print_odom_data(odom_data);
    } else {
        std::cerr << "里程计数据获取失败！" << std::endl;
    }

    // 退出系统并进行SDK资源释放
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
