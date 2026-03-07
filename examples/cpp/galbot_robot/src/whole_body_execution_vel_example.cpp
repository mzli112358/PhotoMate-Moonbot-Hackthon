#include <array>
#include <chrono>
#include <iostream>
#include <thread>
#include <vector>

#include "galbot_robot.hpp"

using namespace galbot::sdk::g1;

namespace {
const char* control_status_to_string(ControlStatus status) {
    switch (status) {
        case ControlStatus::SUCCESS:
            return "SUCCESS";
        case ControlStatus::TIMEOUT:
            return "TIMEOUT";
        case ControlStatus::FAULT:
            return "FAULT";
        case ControlStatus::INVALID_INPUT:
            return "INVALID_INPUT";
        case ControlStatus::INIT_FAILED:
            return "INIT_FAILED";
        case ControlStatus::IN_PROGRESS:
            return "IN_PROGRESS";
        case ControlStatus::STOPPED_UNREACHED:
            return "STOPPED_UNREACHED";
        case ControlStatus::DATA_FETCH_FAILED:
            return "DATA_FETCH_FAILED";
        case ControlStatus::PUBLISH_FAIL:
            return "PUBLISH_FAIL";
        case ControlStatus::COMM_DISCONNECTED:
            return "COMM_DISCONNECTED";
        default:
            return "UNKNOWN_STATUS";
    }
}
}  // namespace

int main() {
    auto& robot = GalbotRobot::get_instance();

    if (robot.init()) {
        std::cout << "系统初始化成功！" << std::endl;
    } else {
        std::cerr << "系统初始化失败！" << std::endl;
        return -1;
    }

    std::this_thread::sleep_for(std::chrono::milliseconds(2000));

    // Whole-body joints: leg(5) + head(2) + left_arm(7) + right_arm(7)
    std::vector<double> whole_body_joint_1 = {
        0.3, 1.2, 0.85, 0.0, 0.0,                       // leg
        0.5, 0.5,                                       // head
        2.0, -1.55, -0.55, -1.7, -0.0, -0.8, 0.0,       // left_arm
        -2.0, 1.55, 0.55, 1.7, 0.0, 0.8, 0.0            // right_arm
    };
    std::vector<double> whole_body_joint_2 = {
        0.3, 1.2, 0.85, 0.0, 0.0,                       // leg
        0.0, 0.0,                                       // head
        2.0, -1.55, -0.55, -1.7, -0.0, -0.8, 0.0,       // left_arm
        -2.0, 1.55, 0.55, 1.7, 0.0, 0.8, 0.0            // right_arm
    };

    // Base velocity command (twist)
    std::array<double, 3> linear_velocity_1 = {0.1, 0.0, 0.0};
    std::array<double, 3> angular_velocity_1 = {0.0, 0.0, 0.0};
    std::array<double, 3> linear_velocity_2 = {-0.1, 0.0, 0.0};
    std::array<double, 3> angular_velocity_2 = {0.0, 0.0, 0.0};

    std::cout << "=== Whole-body + base velocity ===" << std::endl;
    ControlStatus vel_status = robot.execute_whole_body_target(
        whole_body_joint_1,
        linear_velocity_1,
        angular_velocity_1,
        /*is_blocking=*/false,
        /*speed_rad_s=*/0.1,
        /*timeout_s=*/10.0);
    std::cout << "execute_whole_body_target (twist) status: "
              << control_status_to_string(vel_status) << std::endl;
    
    // 底盘运动1s后停止
    std::this_thread::sleep_for(std::chrono::milliseconds(1000));
    robot.stop_base();

    // 等待5s关节运动完成
    std::this_thread::sleep_for(std::chrono::milliseconds(5000));

    vel_status = robot.execute_whole_body_target(
        whole_body_joint_2,
        linear_velocity_2,
        angular_velocity_2,
        /*is_blocking=*/false,
        /*speed_rad_s=*/0.1,
        /*timeout_s=*/10.0);
    std::cout << "execute_whole_body_target (twist) status: "
              << control_status_to_string(vel_status) << std::endl;

    // 底盘运动1s后停止
    std::this_thread::sleep_for(std::chrono::milliseconds(1000));
    robot.stop_base();

    // 等待5s关节运动完成
    std::this_thread::sleep_for(std::chrono::milliseconds(5000));

    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
