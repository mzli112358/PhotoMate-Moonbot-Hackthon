/**
 * 高精度双目深度估计示例：使用 run_once + wait_for_new_result 获取单次推理结果
 */

#include <iostream>
#include <thread>
#include <chrono>

#include "galbot_robot.hpp"
#include "galbot_perception.hpp"
#include "opencv2/opencv.hpp"

using namespace galbot::sdk::g1;

int main() {
    auto& robot = GalbotRobot::get_instance();
    if (!robot.init()) {
        std::cerr << "Robot 初始化失败" << std::endl;
        return -1;
    }

    auto& perception = GalbotPerception::get_instance();
    if (!perception.init({PerceptionModule::FOUNDATION_STEREO})) {
        std::cerr << "感知模块初始化失败" << std::endl;
        return -1;
    }
    // 等待感知模型load
    std::this_thread::sleep_for(std::chrono::seconds(12));
    std::cout << "初始化成功，发送单次推理请求..." << std::endl;

    if (!perception.run_once(PerceptionModule::FOUNDATION_STEREO)) {
        std::cerr << "run_once 命令发送失败" << std::endl;
        return -1;
    }

    std::cout << "等待推理结果..." << std::endl;
    if (!perception.wait_for_new_result(PerceptionModule::FOUNDATION_STEREO, 5.0)) {
        std::cerr << "等待超时，未收到推理结果" << std::endl;
        return -1;
    }

    DetectionResult result;
    if (!perception.get_latest_result(PerceptionModule::FOUNDATION_STEREO, result)) {
        std::cerr << "获取结果失败" << std::endl;
        return -1;
    }

    std::cout << result.getResultInfo() << std::endl;

    if (!result.instanceMask.empty()) {
        cv::Mat depth_map = result.instanceMask;
        std::cout << "深度图 size: " << depth_map.cols << "x" << depth_map.rows
                  << ", type: " << depth_map.type() << std::endl;

        double min_val, max_val;
        cv::minMaxLoc(depth_map, &min_val, &max_val);
        std::cout << "深度值范围: [" << min_val << ", " << max_val << "]" << std::endl;

        cv::Mat depth_f;
        depth_map.convertTo(depth_f, CV_32F);
        cv::Mat mask = (depth_f > 0);

        cv::Mat normalized;
        cv::normalize(depth_f, normalized, 0, 255, cv::NORM_MINMAX, CV_8UC1, mask);

        cv::Mat colored;
        cv::applyColorMap(normalized, colored, cv::COLORMAP_TURBO);

        cv::imwrite("foundation_stereo_depth.jpg", colored);
        std::cout << "深度图已保存至 foundation_stereo_depth.jpg" << std::endl;
    } else {
        std::cout << "未收到深度图 (instanceMask 为空)" << std::endl;
    }

    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
