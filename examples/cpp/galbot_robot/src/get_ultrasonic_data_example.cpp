#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <string>
#include <unordered_set>

#include "galbot_robot.hpp"

using namespace galbot::sdk::g1;

std::string ultrasonic_type_to_string(UltrasonicType ultrasonic_type) {
    switch (ultrasonic_type) {
        case UltrasonicType::FRONT_LEFT:
            return "FRONT_LEFT";
        case UltrasonicType::FRONT_RIGHT:
            return "FRONT_RIGHT";
        case UltrasonicType::RIGHT_LEFT:
            return "RIGHT_LEFT";
        case UltrasonicType::RIGHT_RIGHT:
            return "RIGHT_RIGHT";
        case UltrasonicType::BACK_LEFT:
            return "BACK_LEFT";
        case UltrasonicType::BACK_RIGHT:
            return "BACK_RIGHT";
        case UltrasonicType::LEFT_LEFT:
            return "LEFT_LEFT";
        case UltrasonicType::LEFT_RIGHT:
            return "LEFT_RIGHT";
        default:
            return "UNKNOWN_ULTRASONIC";
    }
}

void print_ultrasonic_data(UltrasonicType ultrasonic_type, const std::shared_ptr<UltrasonicData>& ultrasonic_data) {
    std::cout << "--- " << ultrasonic_type_to_string(ultrasonic_type) << " ---" << std::endl;
    if (!ultrasonic_data) {
        std::cerr << "  Ultrasonic data is empty" << std::endl;
        return;
    }

    std::cout << "  Timestamp (ns): " << ultrasonic_data->timestamp_ns << std::endl;
    std::cout << "  Distance (m): " << ultrasonic_data->distance << std::endl;
}

int main() {
    // 获取对象实例
    auto& robot = GalbotRobot::get_instance();

    // 初始化传感器，为节省资源，只有初始化中传入的传感器可获取数据
    std::unordered_set<SensorType> sensor_types = {
        SensorType::BASE_ULTRASONIC  // 底盘超声波传感器
    };

    // 初始化系统
    if (robot.init(sensor_types)) {
        std::cout << "系统初始化成功！" << std::endl;
    } else {
        std::cerr << "系统初始化失败！" << std::endl;
        return -1;
    }

    // 程序立即启动，稍等数据就绪时间
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));

    // 获取单个超声波传感器数据
    std::cout << "\n===== 获取单个超声波传感器数据 =====" << std::endl;
    auto ultrasonic_data = robot.get_ultrasonic_data(UltrasonicType::FRONT_LEFT);
    print_ultrasonic_data(UltrasonicType::FRONT_LEFT, ultrasonic_data);

    // 遍历获取所有8个超声波传感器数据
    std::cout << "\n===== 获取所有超声波传感器数据 =====" << std::endl;
    for (int i = 0; i < static_cast<int>(UltrasonicType::ULTRASONIC_NUM); ++i) {
        auto ultrasonic_type = static_cast<UltrasonicType>(i);
        auto data = robot.get_ultrasonic_data(ultrasonic_type);
        print_ultrasonic_data(ultrasonic_type, data);
    }

    // 退出系统并进行SDK资源释放
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
