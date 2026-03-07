#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <string>

#include "galbot_robot.hpp"

using namespace galbot::sdk::g1;

std::string force_sensor_type_to_string(GalbotOneFoxtrotSensor sensor_type) {
    switch (sensor_type) {
        case GalbotOneFoxtrotSensor::LEFT_WRIST_FORCE:
            return "LEFT_WRIST_FORCE";
        case GalbotOneFoxtrotSensor::RIGHT_WRIST_FORCE:
            return "RIGHT_WRIST_FORCE";
        default:
            return "UNKNOWN_FORCE_SENSOR";
    }
}

void print_force_data(GalbotOneFoxtrotSensor sensor_type, const std::shared_ptr<ForceData>& force_data) {
    std::cout << "--- " << force_sensor_type_to_string(sensor_type) << " ---" << std::endl;
    if (!force_data) {
        std::cerr << "  Force data is empty" << std::endl;
        return;
    }

    std::cout << "  Timestamp (ns): " << force_data->timestamp_ns << std::endl;
    std::cout << "  Force (N):  "
              << "fx=" << force_data->force.x << ", "
              << "fy=" << force_data->force.y << ", "
              << "fz=" << force_data->force.z << std::endl;
    std::cout << "  Torque (Nm): "
              << "tx=" << force_data->torque.x << ", "
              << "ty=" << force_data->torque.y << ", "
              << "tz=" << force_data->torque.z << std::endl;
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

    // 获取左腕力传感器数据
    std::cout << "\n===== 获取左腕力传感器数据 =====" << std::endl;
    auto left_force_data = robot.get_force_sensor_data(GalbotOneFoxtrotSensor::LEFT_WRIST_FORCE);
    print_force_data(GalbotOneFoxtrotSensor::LEFT_WRIST_FORCE, left_force_data);

    // 获取右腕力传感器数据
    std::cout << "\n===== 获取右腕力传感器数据 =====" << std::endl;
    auto right_force_data = robot.get_force_sensor_data(GalbotOneFoxtrotSensor::RIGHT_WRIST_FORCE);
    print_force_data(GalbotOneFoxtrotSensor::RIGHT_WRIST_FORCE, right_force_data);

    // 遍历获取所有力传感器数据
    std::cout << "\n===== 获取所有力传感器数据 =====" << std::endl;
    for (int i = 0; i < static_cast<int>(GalbotOneFoxtrotSensor::FORCE_NUM); ++i) {
        auto sensor_type = static_cast<GalbotOneFoxtrotSensor>(i);
        auto force_data = robot.get_force_sensor_data(sensor_type);
        print_force_data(sensor_type, force_data);
    }

    // 退出系统并进行SDK资源释放
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
