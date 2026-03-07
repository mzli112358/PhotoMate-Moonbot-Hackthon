#include <chrono>
#include <iostream>
#include <thread>
#include <vector>

#include "galbot_motion.hpp"
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
    auto& motion = GalbotMotion::get_instance();

    if (!robot.init()) {
        std::cerr << "GalbotRobot init failed." << std::endl;
        return -1;
    }
    if (!motion.init()) {
        std::cerr << "GalbotMotion init failed." << std::endl;
        return -1;
    }

    std::this_thread::sleep_for(std::chrono::milliseconds(2000));

    // Whole-body joints: leg(5) + head(2) + left_arm(7) + right_arm(7)
    std::vector<double> whole_body_joint_1 = {
        0.25, 1.1, 0.85, 0.0, 0.0,                       // leg
        0.5, 0.5,                                       // head
        2.0, -1.55, -0.55, -1.7, -0.0, -0.8, 0.2,       // left_arm
        -2.0, 1.55, 0.55, 1.7, 0.0, 0.8, 0.2            // right_arm
    };

    // Base pose command odom(x, y, yaw)
    double base_x_1 = 0.2;
    double base_y_1 = 0.0;
    double base_yaw_1 = 0.0;

    // 可选坐标系（frame_id: base_link/odom/map, reference_frame_id: odom/map）
    const std::string frame_id = "base_link";
    const std::string reference_frame_id = "odom";

    // 底盘位姿插值时间（秒），用于生成平滑底盘轨迹
    const double base_time_s = 10.0;

    // 阻塞等待超时时间（秒），建议设置为大于底盘位姿插值时间
    const double timeout_s = 15.0;

    std::cout << "=== Whole-body + base pose (odom) ===" << std::endl;
    ControlStatus pose_status = robot.execute_whole_body_target(
        whole_body_joint_1,
        base_x_1,
        base_y_1,
        base_yaw_1,
        frame_id,
        reference_frame_id,
        /*is_blocking=*/true,
        /*speed_rad_s=*/0.1,
        /*time_from_start_s=*/base_time_s,
        /*timeout_s=*/timeout_s);

    std::cout << "execute_whole_body_target (pose) status: "
              << control_status_to_string(pose_status) << std::endl;

    std::this_thread::sleep_for(std::chrono::milliseconds(1000));

    // 一键回零
    auto result = robot.zero_whole_body_and_base(
        frame_id,
        reference_frame_id,
        /*is_blocking=*/true,
        /*leg_head_speed_rad_s=*/0.2,
        /*leg_head_timeout_s=*/15.0,
        /*params=*/default_param);
    
    std::cout << "Zero joint status: " << motion.status_to_string(result.first) << std::endl;
    std::cout << "Zero base status: " << control_status_to_string(result.second) << std::endl;

    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
