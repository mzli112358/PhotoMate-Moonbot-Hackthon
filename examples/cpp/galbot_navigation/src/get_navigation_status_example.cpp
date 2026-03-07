/**
 * 示例：非阻塞导航中轮询 get_navigation_status，根据 SUCCESS/FAILED 或超时及时退出，
 * 避免卡死并走错误逻辑。
 */
#include "galbot_navigation.hpp"
#include "galbot_robot.hpp"

#include <chrono>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

using namespace galbot::sdk::g1;

int main() {
    auto& navigation = GalbotNavigation::get_instance();
    auto& robot = GalbotRobot::get_instance();

    if (!robot.init()) {
        std::cerr << "Base instance 初始化失败！" << std::endl;
        return -1;
    }
    if (!navigation.init()) {
        std::cerr << "Navigation instance 初始化失败！" << std::endl;
        return -1;
    }
    auto res = robot.switch_controller(ControllerName::CHASSIS_POSE_CTRL);
    if (res != ControlStatus::SUCCESS) {
        std::cerr << "切换控制器失败！" << std::endl;
        return -1;
    }
    Pose goal_pose(std::vector<double>{0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0});
    const double timeout_s = 20.0;
    const double poll_interval_s = 0.5;

    // 非阻塞导航
    navigation.navigate_to_goal(goal_pose, true, false, static_cast<float>(timeout_s));
    auto start = std::chrono::steady_clock::now();

    while (true) {
        NavigationTaskStatus status = navigation.get_navigation_status();
        auto elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();

        if (status == NavigationTaskStatus::SUCCESS) {
            std::cout << "已到达目标" << std::endl;
            break;
        }
        if (status == NavigationTaskStatus::FAILED) {
            std::cout << "导航失败，及时退出错误逻辑" << std::endl;
            break;
        }
        if (elapsed >= timeout_s) {
            std::cout << "导航超时，及时退出" << std::endl;
            break;
        }

        if (status == NavigationTaskStatus::RUNNING) {
            std::cout << "正在导航... 状态: RUNNING, 已用时: " << elapsed << "s" << std::endl;
        } else {
            std::cout << "状态: UNKNOWN, 已用时: " << elapsed << "s" << std::endl;
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(static_cast<int>(poll_interval_s * 1000)));
    }

    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();
    std::cout << "资源释放成功" << std::endl;
    return 0;
}
