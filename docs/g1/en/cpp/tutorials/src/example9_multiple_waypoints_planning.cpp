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

void printStatus(MotionStatus status) {
    if (status == MotionStatus::SUCCESS) {
        std::cout << "Execute result: SUCCESS, completed successfully" << std::endl;
    } else if (status == MotionStatus::TIMEOUT) {
        std::cout << "Execute result: TIMEOUT, timeout occurred" << std::endl;
    } else if (status == MotionStatus::FAULT) {
        std::cout << "Execute result: FAULT, fault occurred, cannot continue" << std::endl;
    } else if (status == MotionStatus::INVALID_INPUT) {
        std::cout << "Execute result: INVALID_INPUT, input parameters do not meet requirements" << std::endl;
    } else if (status == MotionStatus::INIT_FAILED) {
        std::cout << "Execute result: INIT_FAILED, internal communication component creation failed" << std::endl;
    } else if (status == MotionStatus::IN_PROGRESS) {
        std::cout << "Execute result: IN_PROGRESS, motion is in progress but not yet reached" << std::endl;
    } else if (status == MotionStatus::STOPPED_UNREACHED) {
        std::cout << "Execute result: STOPPED_UNREACHED, stopped but not yet reached target" << std::endl;
    } else if (status == MotionStatus::DATA_FETCH_FAILED) {
        std::cout << "Execute result: DATA_FETCH_FAILED, data fetch failed" << std::endl;
    } else if (status == MotionStatus::PUBLISH_FAIL) {
        std::cout << "Execute result: PUBLISH_FAIL, data publish failed" << std::endl;
    } else if (status == MotionStatus::COMM_DISCONNECTED) {
        std::cout << "Execute result: COMM_DISCONNECTED, communication disconnected" << std::endl;
    }
}

/**
 * Helper function: Print planning results
 */
void print_multi_plan_result(const std::string& label, const TrajResult& res, const std::string& chain_name, GalbotMotion& motion) {
    auto status = std::get<0>(res);
    auto traj_map = std::get<1>(res);

    std::cout << "[" << label << "] Status feedback: " << motion.status_to_string(status) << std::endl;
    if (status == MotionStatus::SUCCESS) {
        if (traj_map.count(chain_name) && !traj_map[chain_name].empty()) {
            std::cout << "✅ Multi-point planning successful: Total trajectory points = " << traj_map[chain_name].size() << std::endl;
        } else {
            std::cout << "⚠️ Status SUCCESS but trajectory is empty, possibly due to target coinciding with current pose." << std::endl;
        }
    } else {
        std::cout << "❌ Multi-point planning failed." << std::endl;
    }
    std::cout << "---------------------------------------------------" << std::endl;
}

/* @brief Check if the robot is safe
*/
void check_robot_safety(){
    std::cout << "⚠️  Note: 1. Please ensure the robot's emergency stop button is released; 2. Please ensure there are no obstacles in front, back, left, and right of the robot to avoid unexpected situations. \n" << std::endl;

    char key;
    for(;;){
        std::cout << "Please confirm that the robot's emergency stop button is released and there are no obstacles. Continue? (y/n)...";
        std::cin >> key;

        if(std::tolower(key) == 'y'){
            std::cout << "User confirmed, continuing execution...\n" << std::endl;
            break;
        }else if(std::tolower(key) == 'n'){
            std::cout << "User not confirmed, program exiting...\n" << std::endl;
            exit(0);
        }else{
            std::cout << "Input error, please enter 'y' or 'n'\n" << std::endl;
        }
    }
}

int main() {
    check_robot_safety();

    auto& motion = GalbotMotion::get_instance(MachineType::G1);
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    if (!motion.init()) {
        std::cerr << "GalbotMotion initialization failed" << std::endl;
        return -1;
    }
    if (!robot.init()) {
        std::cerr << "GalbotRobot initialization failed" << std::endl;
        return -1;
    }

    std::this_thread::sleep_for(std::chrono::seconds(2));

    // Add a box collision object into Motion environment
    try {
        std::string obstacle_id = "box_test_1";
        std::string obj_type = "box";
        std::vector<double> obj_pose = {1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0};
        std::array<double, 3> obj_size = {1.0, 1.0, 1.0};
        std::string target_frame = "world";
        
        MotionStatus status = motion.add_obstacle(
            obstacle_id,
            obj_type,
            obj_pose,
            obj_size,
            target_frame
        );
        
        printStatus(status);
        std::cout << "✅ Obstacle " << obstacle_id << " added successfully" << std::endl;
        
        motion.clear_obstacle();
        std::cout << "✅ Obstacle " << obstacle_id << " cleared successfully" << std::endl;
    } catch (const std::exception& e) {
        std::cout << "Failed to add obstacle: " << e.what() << std::endl;
    }
    
    std::unordered_map<std::string, std::vector<double>> chain_joints = {
        {"leg",       {0.4992, 1.4991, 1.0005, 0.0000, -0.0004}},
        {"head",      {0.0000, 0.0}},
        {"left_arm",  {1.9999, -1.6000, -0.5999, -1.6999, 0.0000, -0.7999, 0.0000}},
        {"right_arm", {-2.0000, 1.6001, 0.6001, 1.7000, 0.0000, 0.8000, 0.0000}}
    };

    std::vector<double> whole_body_joint;
    std::vector<std::string> keys = {"leg", "head", "left_arm", "right_arm"};
    for (const auto& key : keys) {
        whole_body_joint.insert(whole_body_joint.end(), chain_joints[key].begin(), chain_joints[key].end());
    }

    auto params = std::make_shared<Parameter>();
    std::string target_chain = "left_arm";

    // --- Scenario 1: Cartesian space multi-waypoint planning (PoseState target) ---
    try {
        std::cout << ">> Executing Scenario 1: Cartesian space multi-waypoint planning..." << std::endl;

        auto target_pose_state = std::make_shared<PoseState>();
        target_pose_state->chain_name = target_chain;

        // Construct waypoints (3 intermediate poses)
        std::vector<std::vector<double>> waypoint_poses = {
            {0.1267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991},
            {0.2267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991},
            {0.3267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991},
            {0.4267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991}
        };

        auto res = motion.motion_plan_multi_waypoints(
            target_pose_state,
            waypoint_poses,
            nullptr,  // start
            nullptr,  // reference_robot_states
            false,    // enable_collision_check
            params    // params
        );

        print_multi_plan_result("Cartesian multi-point single-chain planning", res, target_chain, motion);
        std::this_thread::sleep_for(std::chrono::milliseconds(800));
    } catch (const std::exception& e) { std::cerr << "Scenario 1 exception: " << e.what() << std::endl; }

    // --- Scenario 2: Joint space multi-waypoint planning (JointStates target) ---
    try {
        std::cout << ">> Executing Scenario 2: Joint space multi-waypoint planning..." << std::endl;

        auto target_joint = std::make_shared<JointStates>();
        target_joint->chain_name = target_chain;

        // Construct waypoints (3 intermediate poses)
        std::vector<std::vector<double>> waypoints = {
            {0.1267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991},
            {0.2267, 0.4342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991},
            {0.3267, 0.6342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991},
            {0.4267, 0.8342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991}
        };

        auto res = motion.motion_plan_multi_waypoints(
            target_joint,
            waypoints,
            nullptr,
            nullptr,
            false,
            params
        );

        print_multi_plan_result("Joint space multi-point", res, target_chain, motion);
    
        // Clear all obstacles
        motion.clear_obstacle();
        std::cout << "✅ Clear all obstacles successfully" << std::endl;
        
        // Check trajectory execution status
        std::vector<std::string> chain_names;
        for (const auto& pair : chain_joints) {
            chain_names.push_back(pair.first);
        }
        std::vector<TrajectoryControlStatus> status = robot.check_trajectory_execution_status(chain_names);
        std::cout << "✅ Check trajectory execution status" << std::endl;
    } catch (const std::exception& e) { 
        std::cerr << "Scenario 2 exception: " << e.what() << std::endl; 
    }

    // 4. Clean up resources
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();
    return 0;
}