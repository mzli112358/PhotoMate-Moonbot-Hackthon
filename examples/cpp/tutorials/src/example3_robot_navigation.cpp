#include<iostream>
#include<fstream>
#include<thread>
#include<chrono>
#include <array>
#include <cmath>
#include <algorithm>
#include <stdexcept>
#include "opencv2/opencv.hpp"

#include "galbot_robot.hpp"
#include "galbot_motion.hpp"
#include "galbot_navigation.hpp"

using namespace galbot::sdk::g1;

inline std::vector<double> quat_normalize(const std::vector<double>& q)
{
    double norm = std::sqrt(
        q[0]*q[0] + q[1]*q[1] +
        q[2]*q[2] + q[3]*q[3]
    );
    if (norm <= 0.0)
        throw std::runtime_error("Zero-norm quaternion");

    return std::vector<double>{ q[0]/norm, q[1]/norm, q[2]/norm, q[3]/norm };
}
inline std::vector<double> quat_conjugate(const std::vector<double>& q)
{
    return std::vector<double>{ -q[0], -q[1], -q[2], q[3] };
}

inline std::vector<double> quat_multiply(const std::vector<double>& q1, const std::vector<double>& q2)
{
    const double x1 = q1[0];
    const double y1 = q1[1];
    const double z1 = q1[2];
    const double w1 = q1[3];
    const double x2 = q2[0];
    const double y2 = q2[1];
    const double z2 = q2[2];
    const double w2 = q2[3];

    return std::vector<double>{
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
        w1*w2 - x1*x2 - y1*y2 - z1*z2
    };
}

template <typename T>
inline T clamp(const T& v, const T& lo, const T& hi)
{
    return (v < lo) ? lo : (v > hi) ? hi : v;
}

inline double orientation_error_angle(const std::vector<double>& A, const std::vector<double>& B)
{
    std::vector<double> qA = quat_normalize({ A[3], A[4], A[5], A[6] });
    std::vector<double> qB = quat_normalize({ B[3], B[4], B[5], B[6] });

    std::vector<double> q_err = quat_multiply(qB, quat_conjugate(qA));
    q_err = quat_normalize(q_err);

    // 数值稳定
    double qw = clamp(q_err[3], -1.0, 1.0);

    return 2.0 * std::acos(qw);
}

struct PoseError
{
    double position_error_norm;   // meters
    double orientation_error_rad;
    double orientation_error_deg;
};

inline PoseError calculate_error(const std::vector<double>& pose1, const std::vector<double>& pose2)
{
    double dx = pose1[0] - pose2[0];
    double dy = pose1[1] - pose2[1];
    double dz = pose1[2] - pose2[2];

    double pos_err = std::sqrt(dx*dx + dy*dy + dz*dz);
    double rot_err = orientation_error_angle(pose1, pose2);

    return PoseError{
        pos_err,
        rot_err,
        rot_err * 180.0 / M_PI
    };
}

Pose local_pose_to_global(Pose cur_pose, Pose local_pose){
    
}

void demo_square_move(GalbotRobot& robot, GalbotNavigation& navi){
    Pose local_pose(std::vector<double>{0.5, 0.0, 0.0, 0.0, 0.0, 0.707, 0.707});

    for(int i=0; i<4; ++i){
        Pose current_pose = navi.get_current_pose();
        std::cout << "Current pose: [" 
                  << current_pose.position.x << ", "
                  << current_pose.position.y << ", "
                  << current_pose.position.z << ", "
                  << current_pose.orientation.x << ", "
                  << current_pose.orientation.y << ", "
                  << current_pose.orientation.z << ", "
                  << current_pose.orientation.w << "]" << std::endl;

        Pose goal_pose = local_pose_to_global(current_pose, local_pose);
        
        if(navi.check_path_reachability(goal_pose, current_pose)){
            int retry_cnt = 3;
            for(;;){
                // navi.move_to_goal(goal_pose);
                std::this_thread::sleep_for(std::chrono::seconds(1));
                navi.navigate_to_goal(goal_pose, true, true, 30);
                retry_cnt -= 1;
                if(navi.check_goal_arrival() || retry_cnt <= 0){
                    break;
                }else{
                    std::cout << "Navigation failed, retry count: " << retry_cnt << std::endl;
                }
            }
        }
    }
    Pose final_pose = navi.get_current_pose();
    std::cout << "Final pose: [" 
              << final_pose.position.x << ", "
              << final_pose.position.y << ", "
              << final_pose.position.z << ", "
              << final_pose.orientation.x << ", "
              << final_pose.orientation.y << ", "
              << final_pose.orientation.z << ", "
              << final_pose.orientation.w << "]" << std::endl;
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
        GalbotNavigation& navi = GalbotNavigation::get_instance();        

        /* Initialize robot */
        if (robot.init()) {
            std::cout << "Initialization successful" << std::endl;
            std::cout << "Is robot running: " << robot.is_running() << std::endl;
        }else{
            std::cerr << "Initialization failed" << std::endl;
        }
        /** Initialize navigation */
        if (navi.init()) {
            std::cout << "Navigation initialization successful" << std::endl;
        }else{
            std::cerr << "Navigation initialization failed" << std::endl;
        }

        /* Wait for data preparation */
        std::this_thread::sleep_for(std::chrono::milliseconds(3000));
        
        /** If not localized, relocalize */
        bool is_localized = navi.is_localized();
        std::cout << "Is robot localized: " << is_localized << std::endl;
        while(!is_localized){
            NavigationStatus status = navi.relocalize(std::vector<double>{0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0});
            std::this_thread::sleep_for(std::chrono::seconds(3));
            std::cout << "Waiting for localization..." << std::endl;
            is_localized = navi.is_localized();
        }

        /** If localized, move the robot */
        demo_square_move(robot, navi);

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
