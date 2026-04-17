#include <iostream>
#include <vector>
#include <string>
#include <unordered_map>
#include <thread>
#include <chrono>
#include <tuple>
#include <memory>
#include <stdexcept>
#include <algorithm>

#include "galbot_motion.hpp"
#include "galbot_robot.hpp"

using namespace galbot::sdk;

// Trajectory return type definition
using TrajResult = std::tuple<MotionStatus, std::unordered_map<std::string, std::vector<std::vector<double>>>>;

/**
 * Helper function: print planning result
 */
void print_multi_plan_result(const std::string& label, const TrajResult& res, const std::string& chain_name, GalbotMotion& planner) {
    auto status = std::get<0>(res);
    auto traj_map = std::get<1>(res);

    std::cout << "[" << label << "] Status feedback: " << planner.status_to_string(status) << std::endl;
    if (status == MotionStatus::SUCCESS) {
        if (traj_map.count(chain_name) && !traj_map[chain_name].empty()) {
            std::cout << "✅ Multi-point planning succeeded: total trajectory points = " << traj_map[chain_name].size() << std::endl;
        } else {
            std::cout << "⚠️ Status is SUCCESS but trajectory is empty; target may overlap current pose." << std::endl;
        }
    } else {
        std::cout << "❌ Multi-point planning failed." << std::endl;
    }
    std::cout << "---------------------------------------------------" << std::endl;
}

int main() {
    auto& planner = GalbotMotion::get_instance(MachineType::S1);
    auto& robot = GalbotRobot::get_instance(MachineType::S1);

    if (!planner.init()) {
        std::cerr << "GalbotMotion initialization failed" << std::endl;
        return -1;
    }
    if (!robot.init()) {
        std::cerr << "GalbotRobot initialization failed" << std::endl;
        return -1;
    }
    
    std::this_thread::sleep_for(std::chrono::seconds(2));

    std::unordered_map<std::string, std::vector<double>> chain_joints = {
        {"torso",     {1.1}},
        {"head",      {0.0000, -0.26}},
        {"left_arm",  {-0.47, -0.94, -0.54, -1.92, 0.2, 0.0, 0.0}},
        {"right_arm", {0.47, 0.94, 0.54, 1.92, -0.2, 0.0, 0.0}}
    };

    std::vector<double> whole_body_joint;
    std::vector<std::string> keys = {"torso", "head", "left_arm", "right_arm"};
    for (const auto& key : keys) {
        whole_body_joint.insert(whole_body_joint.end(), chain_joints[key].begin(), chain_joints[key].end());
    }

    auto params = std::make_shared<Parameter>();
    std::string target_chain = "left_arm";

    // --- Scenario 1: Multi-waypoint planning in Cartesian space (PoseState target) ---
    try {
        std::cout << ">> Running Scenario 1: Multi-waypoint planning in Cartesian space..." << std::endl;

        auto target_pose_state = std::make_shared<PoseState>();
        target_pose_state->chain_name = target_chain;

        // Construct waypoints (3 intermediate poses)
        std::vector<std::vector<double>> waypoint_poses = {
            {0.1267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991},
            {0.2267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991},
            {0.3267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991},
            {0.4267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991}
        };

        auto res = planner.motion_plan_multi_waypoints(
            target_pose_state,
            waypoint_poses,
            nullptr,  // start
            nullptr,  // reference_robot_states
            false,    // enable_collision_check
            params    // params
        );

        print_multi_plan_result("Cartesian multi-waypoint single-chain planning", res, target_chain, planner);
        std::this_thread::sleep_for(std::chrono::milliseconds(800));
    } catch (const std::exception& e) { std::cerr << "Scenario 1 exception: " << e.what() << std::endl; }

    // --- Scenario 2: Multi-waypoint planning in joint space (JointStates target) ---
    try {
        std::cout << ">> Running Scenario 2: Multi-waypoint planning in joint space..." << std::endl;

        auto target_joint = std::make_shared<JointStates>();
        target_joint->chain_name = target_chain;

        // Construct waypoints (3 intermediate poses)
        std::vector<std::vector<double>> waypoints = {
            {0.1267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991},
            {0.2267, 0.4342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991},
            {0.3267, 0.6342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991},
            {0.4267, 0.8342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991}
        };

        auto res = planner.motion_plan_multi_waypoints(
            target_joint,
            waypoints,
            nullptr,
            nullptr,
            false,
            params
        );

        print_multi_plan_result("Joint-space multi-waypoint", res, target_chain, planner);
    } catch (const std::exception& e) { std::cerr << "Scenario 2 exception: " << e.what() << std::endl; }

    // 4. Clean up resources
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();
    return 0;
}
