#include<iostream>
#include<fstream>
#include<thread>
#include<chrono>
#include "opencv2/opencv.hpp"

#include "galbot_robot.hpp"

using namespace galbot::sdk;

void demo_heart_pose(GalbotRobot& robot,
                     const std::vector<std::string>& joint_group_names,
                     const std::vector<std::vector<double>>& position_seq,
                     bool is_blocking, double max_speed, double timeout_s){
    /** Get current joint group angles for subsequent restoration */
    std::vector<double> original_pos = robot.get_joint_positions(joint_group_names, {});
    for (auto a: original_pos){
        std::cout << "Current angles of joint group " << a << std::endl;
    }

    /** Execute heart pose sequence */
    int pos_idx = 0;
    std::cout << "Starting heart gesture..." << std::endl;
    while (pos_idx < position_seq.size()) {
        std::this_thread::sleep_for(std::chrono::seconds(1));
        std::vector<double> pos = position_seq[pos_idx];
        ControlStatus control_status = robot.set_joint_positions(
            pos, joint_group_names, {}, is_blocking, max_speed, timeout_s);
        if (control_status == ControlStatus::SUCCESS) {
            pos_idx++;
        } else {
            std::cerr << "Failed to set joint positions." << std::endl;
            break;
        }
    }

    /** Restore original joint positions */
    robot.set_joint_positions(original_pos, joint_group_names, {}, is_blocking, max_speed, timeout_s);
    std::cout << "Restored joint positions of joint group " << std::endl;
    
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
        auto& robot = GalbotRobot::get_instance(MachineType::G1); 

        /* Initialize robot */
        if (robot.init()) {
            std::cout << "Initialization successful" << std::endl;
            std::cout << "Is robot running: " << robot.is_running() << std::endl;
        }else{
            std::cerr << "Initialization failed" << std::endl;
        }

        /* Wait for data preparation */
        std::this_thread::sleep_for(std::chrono::milliseconds(3000));
        
        /** Get joint names */
        std::vector<std::string> joint_names = robot.get_joint_names(true, {"leg", "head", "left_arm", "right_arm"});
        if (joint_names.empty()) {
            std::cerr << "No joint names available!" << std::endl;
        } else {
            for (const auto& name : joint_names) {
                std::cout << name << std::endl;
            }
        }

        /** Get joint positions using joint group names, empty returns all joints by default */
        std::vector<std::string> joint_group_names = {"left_arm", "right_arm"};
        std::vector<std::vector<double>> position_seq = {{1.53, 0.36, -2.54, -1.80, 0.12, -0.82, 0.09,
             -1.53, -0.36, 2.54, 1.80, -0.12, 0.82, -0.09}}; // right_arm
        bool is_blocking = true;
        double max_speed = 0.1;
        double timeout_s = 20;

        demo_heart_pose(robot, joint_group_names, position_seq,
                        is_blocking, max_speed, timeout_s);


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
