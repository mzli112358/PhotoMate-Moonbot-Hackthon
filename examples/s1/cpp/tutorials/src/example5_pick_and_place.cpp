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

using namespace galbot::sdk;

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

    // Numerically stable
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

Pose get_navigation_pose(const Pose& object_pose, const GalbotMotion& motion){
    /**
     * Please complete the function to calculate the navigation pose.
     * For convenience, we set it default as [0.7, -0.3, 0.0, 0.0, 0.0, 0.0, 1.0],
     */

    return Pose(std::vector<double>{0.7, 0.7, 0.0, 0.0, 0.0, 0.0, 1.0});
}

void navigation_to_goal(GalbotNavigation& navi, const Pose& goal_pose){
    Pose current_pose = navi.get_current_pose();
    std::cout << "Current pose: [" 
              << current_pose.position.x << ", "
              << current_pose.position.y << ", "
              << current_pose.position.z << "]" << std::endl;

    if (navi.check_path_reachability(goal_pose, current_pose)){
        int retry_cnt = 3;
        for(;;){
            NavigationStatus status = navi.navigate_to_goal(goal_pose, true, true, 20.0);
            std::this_thread::sleep_for(std::chrono::seconds(1));
            retry_cnt -= 1;
            if (navi.check_goal_arrival() || retry_cnt < 0){
                break;
            }else{
                std::cout << "Navigation failed, retry count: " << retry_cnt << std::endl;
            }
        }
        std::cout << "has arrived: " << navi.check_goal_arrival() << std::endl;
    }else{
        std::cout << "The path to the goal is not reachable." << std::endl;
    }
}

void lift_camera_up(GalbotMotion& motion, const std::string& target_chain, double lift_delta_z = 0.05){
    int retry_cnt = 3;
    std::vector<double> cur_ee_pose;
    std::string frame_id = "EndEffector";
    std::string reference_frame = "base_link";
    for(;;){
        std::tuple<MotionStatus, std::vector<double>> motion_status = motion.get_end_effector_pose_on_chain(
            target_chain, frame_id, reference_frame
        );
        std::this_thread::sleep_for(std::chrono::seconds(1));

        retry_cnt -= 1;
        if (retry_cnt < 0){
            std::cout << "Retry " << retry_cnt << " times, get end effector pose failed." << std::endl;
            break;
        }else if (std::get<0>(motion_status) == MotionStatus::SUCCESS){
            cur_ee_pose = std::get<1>(motion_status);
            std::cout << "Get end effector pose success, pose: [" 
                      << cur_ee_pose[0] << ", "
                      << cur_ee_pose[1] << ", "
                      << cur_ee_pose[2] << "]" << std::endl;
            break;
        }else{
            std::cout << "Get end effector pose failed, retry count: " << retry_cnt << std::endl;
        }
    }

    std::vector<double> target_ee_pose = cur_ee_pose;
    target_ee_pose[2] += lift_delta_z;

    retry_cnt = 3;
    for(;;){
        MotionStatus motion_status2 = motion.set_end_effector_pose(
            target_ee_pose,
            target_chain, 
            reference_frame,
            nullptr,
            false, 
            true, 
            5.0,
            std::make_shared<Parameter>()
        );
        std::this_thread::sleep_for(std::chrono::seconds(1));

        retry_cnt -= 1;
        if (retry_cnt < 0){
            std::cout << "Retry " << retry_cnt << " times, set end effector pose failed." << std::endl;
            break;
        }else if (motion_status2 == MotionStatus::SUCCESS){
            std::cout << "Set end effector pose success." << std::endl;
            break;
        }else{
            std::cout << "Set end effector pose failed, retry count: " << retry_cnt << std::endl;
        }
    }
}

std::vector<double> detect_target(std::shared_ptr<cv::Mat> rgb_image, std::shared_ptr<cv::Mat> depth_image){
    /**
     * This function is a placeholder. In a real-world scenario, you would implement
     * target detection using computer vision techniques. For this example, we assume a default pose.
     */
    return std::vector<double>{-0.05, 0.1, 0.12, 0.0, 0.0, 0.0, 1.0};
}

std::vector<double> pose_camera_to_base(GalbotRobot& robot, const Pose& object_pose_camera){
    /**
     * This function is a placeholder. You should implement the transformation from camera pose to chassis pose.
     */
    return std::vector<double>{0.2, 0.2, 0.8, 0.0, 0.0, 0.0, 1.0};
}

std::vector<double> detect_object(GalbotRobot& robot, std::string arm){
    /** Get rgb and depth data from robot sensor */
    std::shared_ptr<RgbData> rgb_data;
    std::shared_ptr<DepthData> depth_data;
    if (arm == "left_arm"){
        rgb_data = robot.get_rgb_data(SensorType::LEFT_ARM_CAMERA);
        depth_data = robot.get_depth_data(SensorType::LEFT_ARM_DEPTH_CAMERA);
    }else if (arm == "right_arm"){
        rgb_data = robot.get_rgb_data(SensorType::RIGHT_ARM_CAMERA);
        depth_data = robot.get_depth_data(SensorType::RIGHT_ARM_DEPTH_CAMERA);
    }else{
        std::cout << "Invalid arm name: " << arm << std::endl;
    }

    /** Convert rgb and depth data to cv::Mat */
    std::shared_ptr<cv::Mat> rgb_image, depth_image;
    if (rgb_data){
        rgb_image = rgb_data->convert_to_cv2_mat();
        std::cout << "Get rgb image success" << std::endl;
    }else{
        std::cout << "Get rgb image failed" << std::endl;
    }
    if (depth_data){
        depth_image = depth_data->convert_to_cv2_mat();
        std::cout << "Get depth image success" << std::endl;
    }else{
        std::cout << "Get depth image failed" << std::endl;
    }

    if (rgb_image && depth_image){
        std::cout << "Detected target..." << std::endl;
        std::vector<double> object_pose_camera = detect_target(rgb_image, depth_image);
        std::vector<double> object_pose_base = pose_camera_to_base(robot, object_pose_camera);
        return object_pose_base;
    }else{
        std::cout << "Get rgb or depth image failed" << std::endl;
        return std::vector<double>{0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0};
    }
}

void pick_and_place(
    GalbotRobot& robot, 
    GalbotMotion& motion, 
    GalbotNavigation& navi, 
    const std::vector<double>& object_pose_base, 
    std::string target_chain, 
    std::string reference_frame){
    
    /** Open gripper */
    ControlStatus status = robot.set_gripper_command(
        "left_gripper", 0.1, 0.05, 10, false
    );
    std::this_thread::sleep_for(std::chrono::seconds(1));
    if (status == ControlStatus::SUCCESS){
        std::cout << "Open gripper success" << std::endl;
    }else{
        std::cout << "Open gripper failed" << std::endl;
    }

    /** Move to pre-grasp pose */
    int retry_cnt = 3;
    for(;;){
        MotionStatus motion_status = motion.set_end_effector_pose(
            object_pose_base,
            target_chain, 
            reference_frame,
            nullptr,
            false, 
            true, 
            5.0,
            std::make_shared<Parameter>()
        );
        std::this_thread::sleep_for(std::chrono::seconds(1));

        retry_cnt -= 1;
        if (retry_cnt < 0){
            std::cout << "Retry " << retry_cnt << " times, set end effector pose failed." << std::endl;
            break;
        }else if (motion_status == MotionStatus::SUCCESS){
            std::cout << "Set end effector pose success." << std::endl;
            break;
        }else{
            std::cout << "Set end effector pose failed, retry count: " << retry_cnt << std::endl;
        }
    }

    /** Close gripper */
    ControlStatus status1 = robot.set_gripper_command(
        "left_gripper", 0.02, 0.05, 10, false
    );
    std::this_thread::sleep_for(std::chrono::seconds(1));
    if (status1 == ControlStatus::SUCCESS){
        std::cout << "Close gripper success" << std::endl;
    }else{
        std::cout << "Close gripper failed" << std::endl;
    }

    /** Return to initial position */
    navigation_to_goal(navi, Pose(std::vector<double>{0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0}));
    std::this_thread::sleep_for(std::chrono::seconds(1));

    /** Open gripper to release object */
    ControlStatus status2 = robot.set_gripper_command(
        "left_gripper", 0.1, 0.05, 10, false
    );
    std::this_thread::sleep_for(std::chrono::seconds(1));
    if (status2 == ControlStatus::SUCCESS){
        std::cout << "Open gripper to release object success" << std::endl;
    }else{
        std::cout << "Open gripper to release object failed" << std::endl;
    }
}

int main(){
    check_robot_safety();
    try{
        /* Get robot instance  */
        auto& robot = GalbotRobot::get_instance(MachineType::S1); 
        auto& motion = GalbotMotion::get_instance(MachineType::S1);
        auto& navi = GalbotNavigation::get_instance(MachineType::S1);        

        /* Initialize robot */
        if (robot.init({SensorType::LEFT_ARM_CAMERA, SensorType::LEFT_ARM_DEPTH_CAMERA})) {
            std::cout << "Initialization successful" << std::endl;
            std::cout << "Is robot running: " << robot.is_running() << std::endl;
        }else{
            std::cerr << "Initialization failed" << std::endl;
        }
        /** Initialize motion */
        if (motion.init()) {
            std::cout << "Motion initialization successful" << std::endl;
        }else{
            std::cerr << "Motion initialization failed" << std::endl;
        }
        /** Initialize navigation */
        if (navi.init()) {
            std::cout << "Navigation initialization successful" << std::endl;
        }else{
            std::cerr << "Navigation initialization failed" << std::endl;
        }

        /* Wait for data preparation */
        std::this_thread::sleep_for(std::chrono::milliseconds(3000));
        
        /** Calculate navigation target pose */
        Pose object_goal_pose(std::vector<double>{1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 1.0});
        Pose base_goal_pose = get_navigation_pose(object_goal_pose, motion);

        /** Navigate to the navigation pose */
        navigation_to_goal(navi, base_goal_pose);

        /** Get original joint positions for recovery */
        std::string target_chain = "left_arm";
        std::string reference_frame = "base_link";
        std::vector<double> original_joint_positions = robot.get_joint_positions(std::vector<std::string>{target_chain}, {});

        /** Lift the camera up for better view */
        lift_camera_up(motion, target_chain);

        /** Detect object pose */
        std::vector<double> object_pose_base = detect_object(robot, target_chain);

        /** Pick the object and move to original position */
        pick_and_place(robot, motion, navi, object_pose_base, target_chain, reference_frame);
        
        ControlStatus status = robot.set_joint_positions(
            original_joint_positions, 
            std::vector<std::string>{target_chain}, 
            {},
            true,
            0.3,
            30.0
        );
        if (status == ControlStatus::SUCCESS) {
            std::cout << "Joint recover sucess." << std::endl;
        } else {
            std::cerr << "Joint recover failed." << std::endl;
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
