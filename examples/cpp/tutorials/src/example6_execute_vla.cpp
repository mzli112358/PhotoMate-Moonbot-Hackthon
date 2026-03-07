#include<iostream>
#include<fstream>
#include<thread>
#include<chrono>
#include "opencv2/opencv.hpp"

#include "galbot_robot.hpp"
#include "galbot_motion.hpp"
#include "galbot_navigation.hpp"

using namespace galbot::sdk::g1;

/**
 * Generate target point for trajectory
 */
TrajectoryPoint generateTargetPoint(const std::vector<double>& q, double targetTime = 10.0) {
    TrajectoryPoint jointPosition;
    jointPosition.time_from_start_second = targetTime;
    
    for (double joint : q) {
        JointCommand jointCmd;
        jointCmd.position = joint;
        jointPosition.joint_command_vec.push_back(jointCmd);
    }
    
    return jointPosition;
}

/**
 * Generate trajectory for joints
 */
std::shared_ptr<Trajectory> generateTargetTrajectory(
    const std::vector<std::vector<double>>& trajectory,
    const std::vector<std::string>& jointGroups,
    const std::vector<std::string>& jointNames,
    double dt = 0.008
) {
    if (trajectory.empty()) {
        return nullptr;
    }
    
    auto traj = std::make_shared<Trajectory>();
    traj->joint_groups = jointGroups;
    traj->joint_names = jointNames;
    
    double currentTime = 0.0;
    for (const auto& state : trajectory) {
        currentTime += dt;
        TrajectoryPoint trajPoint = generateTargetPoint(state, currentTime);
        traj->points.push_back(trajPoint);
    }
    
    return traj;
}

/**
 * Print joint states
 */
void printJointStates(const std::vector<JointState>& jointStates) {
    for (const auto& js : jointStates) {
        std::cout << " : position = " << js.position 
             << " , velocity = " << js.velocity
             << " , acceleration = " << js.acceleration
             << " , effort = " << js.effort
             << " , current = " << js.current << std::endl;
    }
}

/**
 * Fake VLA (Vision-Language-Action) model implementation
 */
std::map<std::string, std::vector<std::vector<double>>> fakeVla(const std::unordered_map<SensorType, std::shared_ptr<cv::Mat>>& rgbDataDict) {
    std::cout << "Fake VLA executing..." << std::endl;
    
    const int numPoints = 200;
    std::map<std::string, std::vector<std::vector<double>>> result;
    
    // Right arm trajectory
    std::vector<double> rightArmStart = {-2.0, 1.59, 0.6, 1.7, 0.0, 0.8, 0.0};
    std::vector<double> rightArmEnd = {-1.5, 1.59, 0.6, 1.5, 0.0, 0.6, 0.0};
    std::vector<std::vector<double>> rightArmTraj(numPoints);
    for (int i = 0; i < numPoints; ++i) {
        std::vector<double> point(7);
        for (int j = 0; j < 7; ++j) {
            point[j] = rightArmStart[j] + (rightArmEnd[j] - rightArmStart[j]) * i / (numPoints - 1);
        }
        rightArmTraj[i] = point;
    }
    
    // Left arm trajectory
    std::vector<double> leftArmPos = {1.9999, -1.6000, -0.5999, -1.6999, 0.0000, -0.7999, 0.0000};
    std::vector<std::vector<double>> leftArmTraj(numPoints, leftArmPos);
    
    // Head trajectory
    std::vector<double> headPos = {0.0, 0.0};
    std::vector<std::vector<double>> headTraj(numPoints, headPos);
    
    // Leg trajectory
    std::vector<double> legPos = {0.299, 1.199, 0.849, 0.0000, 0.0};
    std::vector<std::vector<double>> legTraj(numPoints, legPos);
    
    result["leg"] = legTraj;
    result["head"] = headTraj;
    result["left_arm"] = leftArmTraj;
    result["right_arm"] = rightArmTraj;
    
    return result;
}

std::map<std::string, std::vector<std::vector<double>>> estimate_vla(GalbotRobot& robot, const std::unordered_set<SensorType>& enable_sensor_set){
    /** Get RGB images from enabled cameras */
    std::unordered_map<SensorType, std::shared_ptr<cv::Mat>> rgb_images;
    for(const auto& sensor_type : enable_sensor_set){
        if(sensor_type == SensorType::LEFT_ARM_CAMERA || sensor_type == SensorType::RIGHT_ARM_CAMERA ||
            sensor_type == SensorType::HEAD_LEFT_CAMERA || sensor_type == SensorType::HEAD_RIGHT_CAMERA){
            std::shared_ptr<RgbData> rgb_data = robot.get_rgb_data(sensor_type);
            if(rgb_data){
                std::shared_ptr<cv::Mat> rgb_image = rgb_data->convert_to_cv2_mat();
                rgb_images[sensor_type] = rgb_image;
            }else{
                std::cerr << "Failed to get RGB data. " << std::endl;
            }
        }
    }
    std::cout << "RGB images size: " << rgb_images.size() << std::endl;

     /** Estimate VLA */
    std::map<std::string, std::vector<std::vector<double>>> vla = fakeVla(rgb_images);
    return vla;
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

int main(){
    check_robot_safety();
    try{
        /* Get robot instance  */
        GalbotRobot& robot = GalbotRobot::get_instance();
        GalbotMotion& motion = GalbotMotion::get_instance();
        GalbotNavigation& navigation = GalbotNavigation::get_instance();

        /** Enable sensor type */
        std::unordered_set<SensorType> enable_sensor_set = {
            SensorType::LEFT_ARM_CAMERA,
            SensorType::RIGHT_ARM_CAMERA,
            SensorType::HEAD_LEFT_CAMERA,
            SensorType::HEAD_RIGHT_CAMERA
        };

        /* Initialize robot */
        if (robot.init(enable_sensor_set)) {
            std::cout << "Initialization successful" << std::endl;
            std::cout << "Is robot running: " << robot.is_running() << std::endl;
        }else{
            std::cerr << "Initialization failed" << std::endl;
        }
        if (!motion.init()) {
            std::cerr << "Motion initialization failed" << std::endl;
        }else{
            std::cout << "Motion initialization successful" << std::endl;
        }
        if (!navigation.init()) {
            std::cerr << "Navigation initialization failed" << std::endl;
        }else{
            std::cout << "Navigation initialization successful" << std::endl;
        }

        /* Wait for data preparation */
        std::this_thread::sleep_for(std::chrono::milliseconds(3000));
        
        /** Estimate VLA actions */
        std::map<std::string, std::vector<std::vector<double>>> joint_positions = estimate_vla(robot, enable_sensor_set);

        // Generate target trajectory
        std::vector<std::string> jointGroups;
        std::vector<std::vector<double>> jointTraj;
        
        for (const auto& [group, traj] : joint_positions) {
            jointGroups.push_back(group);
            if (jointTraj.empty()) {
                jointTraj = traj;
            } else {
                // Concatenate trajectories
                for (size_t i = 0; i < traj.size(); ++i) {
                    jointTraj[i].insert(jointTraj[i].end(), traj[i].begin(), traj[i].end());
                }
            }
        }
        
        // Final joint position check
        std::vector<double> wholeBodyJoint = jointTraj.back();
        std::vector<double> baseState = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0};
        
        RobotStates checkState;
        checkState.whole_body_joint = wholeBodyJoint;
        checkState.base_state = baseState;
        
        std::cout << "✅ Final joint position check state: [";
        for (double val : wholeBodyJoint) std::cout << val << " ";
        std::cout << "]" << std::endl;
        
        // Check collision
        // std::tuple<MotionStatus, std::vector<bool>> collisionResult = motion.check_collision(std::vector<std::shared_ptr<RobotStates>>{std::make_shared<RobotStates>(checkState)}, true);
        // MotionStatus status = std::get<0>(collisionResult);
        // std::vector<bool> collisionRes = std::get<1>(collisionResult);
        auto [status, collisionRes] = motion.check_collision(std::vector<std::shared_ptr<RobotStates>>{std::make_shared<RobotStates>(checkState)}, true);
        std::this_thread::sleep_for(std::chrono::seconds(1));
        
        if (status == MotionStatus::SUCCESS) {
            std::cout << "✅ OK: collision check finished: " << collisionRes[0] 
                 << " (False=no collision)" << std::endl;
            
            // Execute trajectory
            auto trajectory = generateTargetTrajectory(jointTraj, jointGroups, {});
            if (trajectory != nullptr) {
                ControlStatus execStatus = robot.execute_joint_trajectory(*trajectory, true);
                std::this_thread::sleep_for(std::chrono::seconds(1));
                
                if (execStatus == ControlStatus::SUCCESS) {
                    std::cout << "✅ Joint trajectory execution successful." << std::endl;
                } else {
                    std::cout << "❌ Joint trajectory execution failed." << std::endl;
                }
                
                // Check joint state
                auto jointStates = robot.get_joint_states(jointGroups, {});
                printJointStates(jointStates);
                std::cout << "✅ Final joint position check state after execution" << std::endl;
            } else {
                std::cout << "❌ Generated trajectory is invalid, cannot execute." << std::endl;
            }
        } else {
            std::cout << "❌ Collision check failed, will not execute the joint trajectory." << std::endl;
        }

        /** Actively send SIGINT exit signal to the robot */
        robot.request_shutdown();
        /** Wait to enter shutdown state */
        robot.wait_for_shutdown();
        /** Release SDK resources */
        robot.destroy();
        std::cout << "Resource release successful" << std::endl;    
    }catch(const std::exception& e){
        std::cout << "Error: " << e.what() << std::endl;
    }

    return 0;
}
