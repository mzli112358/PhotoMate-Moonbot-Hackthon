#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <string>

#include "galbot_robot.hpp"

void print_joint_positions(const std::vector<double>& positions) {
    std::cout << "当前关节位置：" << std::endl;
    for (size_t i = 0; i < positions.size(); ++i) {
        std::cout << "  关节 " << i << ": " << positions[i] << " rad" << std::endl;
    }
    std::cout << std::endl;
}

std::string execution_status_to_string(galbot::sdk::g1::ControlStatus status) {
    switch (status) {
        case galbot::sdk::g1::ControlStatus::SUCCESS:
            return "SUCCESS";
        case galbot::sdk::g1::ControlStatus::TIMEOUT:
            return "TIMEOUT";
        case galbot::sdk::g1::ControlStatus::FAULT:
            return "FAULT";
        case galbot::sdk::g1::ControlStatus::INVALID_INPUT:
            return "INVALID_INPUT";
        case galbot::sdk::g1::ControlStatus::INIT_FAILED:
            return "INIT_FAILED";
        case galbot::sdk::g1::ControlStatus::IN_PROGRESS:
            return "IN_PROGRESS";
        case galbot::sdk::g1::ControlStatus::STOPPED_UNREACHED:
            return "STOPPED_UNREACHED";
        case galbot::sdk::g1::ControlStatus::DATA_FETCH_FAILED:
            return "DATA_FETCH_FAILED";
        case galbot::sdk::g1::ControlStatus::PUBLISH_FAIL:
            return "PUBLISH_FAIL";
        case galbot::sdk::g1::ControlStatus::COMM_DISCONNECTED:
            return "COMM_DISCONNECTED";
        default:
            return "UNKNOWN_STATUS";
    }
}

int main() {
    // 获取对象实例
    auto& robot = galbot::sdk::g1::GalbotRobot::get_instance();

    // 初始化系统
    if (robot.init()) {
        std::cout << "系统初始化成功！" << std::endl;
    } else {
        std::cerr << "系统初始化失败！" << std::endl;
        return -1;
    }

    // 稍等数据就绪时间
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));

    std::vector<std::string> joint_groups = {"head"};
    std::vector<std::string> joint_names = {};

    std::vector<galbot::sdk::g1::JointCommand> joint_commands(2);
    joint_commands[0].position = 0.2;
    joint_commands[1].position = 0.2;
    // 设置头部关节弧度为0.3 0.3
    galbot::sdk::g1::ControlStatus execution_status =
        robot.set_joint_commands(joint_commands, joint_groups, joint_names);
    if (execution_status != galbot::sdk::g1::ControlStatus::SUCCESS) {
        std::cout << "关节角指令发送失败" << std::endl;
    } else {
        std::cout << "关节角指令发送成功" << std::endl;
    }

    // 稍等一会儿，等待动作执行完成
    std::this_thread::sleep_for(std::chrono::milliseconds(10000));

    // 查询关节位置
    auto ret_positions = robot.get_joint_positions(joint_groups, {});
    print_joint_positions(ret_positions);

    // 第二步：回到初始位置 —— 将两个头部关节都设为 0.0 rad
    joint_commands[0].position = 0.0;
    joint_commands[1].position = 0.0;

    // 使用关节名称设置关节命令，如设置joint_names字段将会覆盖joint_groups
    joint_groups = {""};
    joint_names = {"head_joint1", "head_joint2"};
    execution_status =
        robot.set_joint_commands(joint_commands, joint_groups, joint_names);
    if (execution_status != galbot::sdk::g1::ControlStatus::SUCCESS) {
        std::cout << "关节角指令发送失败" << std::endl;
    } else {
        std::cout << "关节角指令发送成功" << std::endl;
    }

    // 退出系统并进行SDK资源释放
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    std::cout << "\n程序已退出" << std::endl;
    return 0;
}
