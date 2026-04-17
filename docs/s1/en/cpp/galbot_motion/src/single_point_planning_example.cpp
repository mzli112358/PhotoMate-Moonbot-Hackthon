#include <iostream>
#include <vector>
#include <string>
#include <unordered_map>
#include <thread>
#include <chrono>
#include <tuple>
#include <memory>
#include <stdexcept>

#include "galbot_motion.hpp"
#include "galbot_robot.hpp"

using namespace galbot::sdk;

// Define a trajectory return type to simplify the code
using TrajResult = std::tuple<MotionStatus, std::unordered_map<std::string, std::vector<std::vector<double>>>>;

/**
 * Helper function: print planning result
 */
void print_plan_info(const std::string& label, const TrajResult& res, const std::string& chain_name, GalbotMotion& planner) {
    auto status = std::get<0>(res);
    auto traj_map = std::get<1>(res);

    std::cout << "[" << label << "] Status: " << planner.status_to_string(status) << std::endl;
    if (status == MotionStatus::SUCCESS) {
        if (traj_map.count(chain_name) && !traj_map[chain_name].empty()) {
            std::cout << "✅ Planning succeeded: trajectory points = " << traj_map[chain_name].size() << std::endl;
        } else {
            std::cout << "⚠️ Status is SUCCESS but trajectory is empty (possibly already at target)" << std::endl;
        }
    } else {
        std::cout << "❌ Planning failed" << std::endl;
    }
    std::cout << "---------------------------------------" << std::endl;
}

int main() {

    auto& planner = GalbotMotion::get_instance(MachineType::S1);
    auto& robot = GalbotRobot::get_instance(MachineType::S1);

    if (!planner.init()) {
        std::cerr << "GalbotMotion init FAILED" << std::endl;
        return -1;
    }
    if (!robot.init()) {
        std::cerr << "GalbotRobot init FAILED" << std::endl;
        return -1;
    }
    
    std::this_thread::sleep_for(std::chrono::milliseconds(1000));

    std::unordered_map<std::string, std::vector<double>> chain_joints = {
        {"torso",     {1.1}},
        {"head",      {0.0000, -0.26}},
        {"left_arm",  {-0.47, -0.94, -0.54, -1.92, 0.2, 0.0, 0.0}},
        {"right_arm", {0.47, 0.94, 0.54, 1.92, -0.2, 0.0, 0.0}}
    };

    std::unordered_map<std::string, std::vector<double>> chain_pose_baselink = {
        {"head",      {0.0599, 0.0002, 1.4098, -0.7072, 0.0037, 0.0037, 0.7069}},
        {"left_arm",  {0.1267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991}},
        {"right_arm", {0.1267, -0.2345, 0.7358, -0.0225, 0.0126, -0.0343, 0.9991}}
    };

    auto params = std::make_shared<Parameter>();
    std::string target_chain = "left_arm";

    // NOTE:
    // - GalbotMotion does NOT provide real-time obstacle perception / automatic environment updates today.
    // - When enable_collision_check=true, collision checking uses self-collision + objects you load manually via
    //   add_obstacle/attach_target_object (including point clouds if you load them explicitly).

    // Scenario 1: joint-space planning, target type = joint state
    try {
        std::cout << ">> Scenario 1: joint-space planning (joint target)..." << std::endl;

        // Construct target joint state
        auto target_joint = std::make_shared<JointStates>();
        target_joint->chain_name = target_chain;
        target_joint->joint_positions = chain_joints[target_chain];

        auto res = planner.motion_plan(
            target_joint,   // 1. target
            nullptr,        // 2. start (nullptr means start from current state)
            nullptr,        // 3. reference_robot_states
            false,          // 4. enable_collision_check
            params          // 5. params
        );

        print_plan_info("Joint-space planning (joint target)", res, target_chain, planner);
    } catch (const std::exception& e) { std::cerr << e.what() << std::endl; }

    // Scenario 2: joint-space planning, target type = end-effector pose (Cartesian)
    try {
        std::cout << ">> Scenario 2: joint-space planning (pose target)..." << std::endl;

        // Construct target pose state
        auto target_pose = std::make_shared<PoseState>();
        target_pose->chain_name = target_chain;
        target_pose->frame_id = "EndEffector";
        target_pose->reference_frame = "base_link";
        target_pose->pose = chain_pose_baselink[target_chain];

        auto res = planner.motion_plan(
            target_pose,    // 1. target
            nullptr,        // 2. start
            nullptr,        // 3. reference_robot_states
            false,          // 4. enable_collision_check
            params          // 5. params
        );

        print_plan_info("Joint-space planning (pose target)", res, target_chain, planner);
        std::this_thread::sleep_for(std::chrono::milliseconds(800));
    } catch (const std::exception& e) { std::cerr << e.what() << std::endl; }

    // Scenario 3: joint-space planning with an explicit start state
    try {
        std::cout << ">> Scenario 3: joint-space planning (explicit start)..." << std::endl;

        auto target_joint = std::make_shared<JointStates>();
        target_joint->chain_name = target_chain;
        target_joint->joint_positions = chain_joints[target_chain];

        auto start_joint = std::make_shared<JointStates>();
        start_joint->chain_name = target_chain;
        start_joint->joint_positions = std::vector<double>(7, 0.0); // Use seven zeros as the starting point

        auto res = planner.motion_plan(
            target_joint, 
            start_joint,    // 2. Specify the start point
            nullptr, 
            false, 
            params
        );

        print_plan_info("Joint-space planning (explicit start)", res, target_chain, planner);
    } catch (const std::exception& e) { std::cerr << e.what() << std::endl; }

    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();
    return 0;
}
