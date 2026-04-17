#include <chrono>
#include <cctype>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

#include "galbot_robot.hpp"
#include "galbot_motion.hpp"

using namespace galbot::sdk;

void print_motion_status(MotionStatus status)
{
    if (status == MotionStatus::SUCCESS) {
        std::cout << "Execution result: SUCCESS, Execution successful\n";
    } else if (status == MotionStatus::TIMEOUT) {
        std::cout << "Execution result: TIMEOUT, Execution timeout\n";
    } else if (status == MotionStatus::FAULT) {
        std::cout << "Execution result: FAULT, Fault occurred, unable to continue execution\n";
    } else if (status == MotionStatus::INVALID_INPUT) {
        std::cout << "Execution result: INVALID_INPUT, Input parameters do not meet requirements\n";
    } else if (status == MotionStatus::INIT_FAILED) {
        std::cout << "Execution result: INIT_FAILED, Internal communication component creation failed\n";
    } else if (status == MotionStatus::IN_PROGRESS) {
        std::cout << "Execution result: IN_PROGRESS, Moving but not in position\n";
    } else if (status == MotionStatus::STOPPED_UNREACHED) {
        std::cout << "Execution result: STOPPED_UNREACHED, Stopped but did not reach target\n";
    } else if (status == MotionStatus::DATA_FETCH_FAILED) {
        std::cout << "Execution result: DATA_FETCH_FAILED, Data acquisition failed\n";
    } else if (status == MotionStatus::PUBLISH_FAIL) {
        std::cout << "Execution result: PUBLISH_FAIL, Data sending failed\n";
    } else if (status == MotionStatus::COMM_DISCONNECTED) {
        std::cout << "Execution result: COMM_DISCONNECTED, Connection failed\n";
    } else {
        std::cout << "Execution result: status=" << static_cast<int>(status) << "\n";
    }
}

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
inline T clamp_val(const T& v, const T& lo, const T& hi)
{
    return (v < lo) ? lo : (v > hi) ? hi : v;
}

inline double orientation_error_angle(const std::vector<double>& A, const std::vector<double>& B)
{
    std::vector<double> qA = quat_normalize({ A[3], A[4], A[5], A[6] });
    std::vector<double> qB = quat_normalize({ B[3], B[4], B[5], B[6] });

    std::vector<double> q_err = quat_multiply(qB, quat_conjugate(qA));
    q_err = quat_normalize(q_err);

    double qw = clamp_val(q_err[3], -1.0, 1.0);

    return 2.0 * std::acos(qw);
}

struct PoseError
{
    double position_error_norm;
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

void print_pose_error(const char* label, const PoseError& e)
{
    std::cout << label
              << " position_error_norm: " << e.position_error_norm
              << " m, orientation_error_rad: " << e.orientation_error_rad
              << ", orientation_error_deg: " << e.orientation_error_deg << "\n";
}

void check_robot_safety()
{
    std::cout << "⚠️  Note: 1. Please ensure the robot's emergency stop button is released; 2. Please ensure there are no obstacles in front, back, left, and right of the robot to avoid unexpected situations.\n\n";

    char key;
    for (;;) {
        std::cout << "Please confirm that the robot's emergency stop button is released and there are no obstacles. Continue? (y/n)...";
        std::cin >> key;

        if (std::tolower(static_cast<unsigned char>(key)) == 'y') {
            std::cout << "User confirmed, continuing execution...\n\n";
            break;
        }
        if (std::tolower(static_cast<unsigned char>(key)) == 'n') {
            std::cout << "User not confirmed, program exiting...\n\n";
            std::exit(1);
        }
        std::cout << "Input error, please enter 'y' or 'n'\n\n";
    }
}

void print_pose_line(const char* prefix, const std::vector<double>& pose)
{
    std::cout << prefix;
    for (double v : pose) {
        std::cout << v << " ";
    }
    std::cout << "\n";
}

int main()
{
    check_robot_safety();
    try {
        auto& motion = GalbotMotion::get_instance(MachineType::S1);
        auto& robot = GalbotRobot::get_instance(MachineType::S1);

        struct SdkCleanup {
            GalbotRobot& r;
            explicit SdkCleanup(GalbotRobot& ref) : r(ref) {}
            ~SdkCleanup()
            {
                r.request_shutdown();
                r.wait_for_shutdown();
                r.destroy();
            }
        } cleanup{robot};

        if (motion.init()) {
            std::cout << "GalbotMotion initialization successful\n";
        } else {
            std::cout << "GalbotMotion initialization failed\n";
        }
        if (robot.init()) {
            std::cout << "GalbotRobot initialization successful\n";
        } else {
            std::cout << "GalbotRobot initialization failed\n";
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(3000));

        MotionStatus zero_status = motion.move_whole_body_joint_zero(
            true, 0.2, 15.0, std::make_shared<Parameter>());
        print_motion_status(zero_status);
        if (zero_status != MotionStatus::SUCCESS) {
            std::cout << "❌ move_whole_body_joint_zero failed, stop demo to avoid risky posture.\n";
            return 0;
        }
        std::cout << "✅ whole-body zero completed, start arm manipulation demo from safe pose.\n";

        const std::string target_frame = "EndEffector";
        const std::string reference_frame = "base_link";
        const std::string target_chain = "left_arm";
        const std::string end_link = "left_arm_end_effector_mount_link";

        std::vector<double> original_pose;
        {
            auto ret_pose = motion.get_end_effector_pose_on_chain(
                target_chain, target_frame, reference_frame);
            if (std::get<0>(ret_pose) != MotionStatus::SUCCESS) {
                std::cerr << "❌ Failed to get end-effector pose\n";
                return 0;
            }
            original_pose = std::get<1>(ret_pose);
            std::cout << "✅ Current " << target_chain << " end-effector pose: ";
            print_pose_line("", original_pose);
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(800));

        std::vector<double> target_pose = {
            original_pose[0] + 0.04,
            original_pose[1],
            original_pose[2] + 0.02,
            original_pose[3],
            original_pose[4],
            original_pose[5],
            original_pose[6]
        };
        std::cout << "✅ S1 target pose (relative to zero pose): ";
        print_pose_line("", target_pose);

        std::unordered_map<std::string, std::vector<double>> joint_angles_ik;
        {
            const bool enable_collision_check = false;
            auto ret_ik = motion.inverse_kinematics(
                target_pose,
                {target_chain},
                target_frame,
                reference_frame,
                {},
                enable_collision_check,
                std::make_shared<Parameter>());
            if (std::get<0>(ret_ik) != MotionStatus::SUCCESS) {
                std::cerr << "❌ IK solving failed\n";
                return 0;
            }
            joint_angles_ik = std::get<1>(ret_ik);
            std::cout << "✅ Target " << target_chain << " IK solving successful joint_angles_ik: ";
            print_pose_line("", joint_angles_ik[target_chain]);
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(1000));

        ControlStatus set_joints_status = robot.set_joint_positions(
            joint_angles_ik[target_chain],
            {target_chain},
            {},
            true,
            0.1,
            20.0);
        if (set_joints_status != ControlStatus::SUCCESS) {
            std::cerr << "❌ Setting joint group angles failed\n";
            return 0;
        }
        std::cout << "✅ Setting " << target_chain << " joint group angles successful.\n";
        std::this_thread::sleep_for(std::chrono::milliseconds(1000));

        {
            auto ret_verify = motion.get_end_effector_pose_on_chain(
                target_chain, target_frame, reference_frame);
            if (std::get<0>(ret_verify) != MotionStatus::SUCCESS) {
                std::cerr << "❌ Failed to get end-effector pose after set joints\n";
                return 0;
            }
            const std::vector<double>& tgt_pose_ik = std::get<1>(ret_verify);
            std::cout << "✅ Getting " << target_chain << " end-effector pose successful: ";
            print_pose_line("", tgt_pose_ik);
            PoseError err = calculate_error(tgt_pose_ik, target_pose);
            print_pose_error("End-effector pose error:", err);
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(1000));

        {
            const bool enable_collision_check = false;
            auto ret_fk = motion.forward_kinematics(
                end_link,
                reference_frame,
                joint_angles_ik,
                std::make_shared<Parameter>());
            if (std::get<0>(ret_fk) != MotionStatus::SUCCESS) {
                std::cerr << "❌ FK solving failed\n";
                return 0;
            }
            const std::vector<double>& tgt_pose_fk = std::get<1>(ret_fk);
            std::cout << "✅ Target " << target_chain << " FK solving successful: ";
            print_pose_line("", tgt_pose_fk);
            PoseError err = calculate_error(tgt_pose_fk, target_pose);
            print_pose_error("FK solving error:", err);
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(3000));
        std::cout << "\n";

        {
            const bool enable_collision_check = false;
            MotionStatus ret_restore = motion.set_end_effector_pose(
                original_pose,
                target_chain,
                reference_frame,
                nullptr,
                enable_collision_check,
                true,
                5.0,
                std::make_shared<Parameter>());
            if (ret_restore != MotionStatus::SUCCESS) {
                std::cerr << "❌ Setting end-effector pose failed\n";
                return 0;
            }
            std::cout << "✅ Setting end-effector pose successful: status=" << static_cast<int>(ret_restore) << "\n";
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(1000));

        {
            auto ret_final = motion.get_end_effector_pose_on_chain(
                target_chain, target_frame, reference_frame);
            if (std::get<0>(ret_final) != MotionStatus::SUCCESS) {
                std::cerr << "❌ Failed to get end-effector pose after restore\n";
                return 0;
            }
            const std::vector<double>& original_pose_rec = std::get<1>(ret_final);
            std::cout << "✅ Getting " << target_chain << " end-effector pose successful: ";
            print_pose_line("", original_pose_rec);
            PoseError err = calculate_error(original_pose_rec, original_pose);
            print_pose_error("Restore end-effector pose error:", err);
        }
    } catch (const std::exception& e) {
        std::cerr << "❌ Main program exception: " << e.what() << "\n";
        return 1;
    }

    return 0;
}
