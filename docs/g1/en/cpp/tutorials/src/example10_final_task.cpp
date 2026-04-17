#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <iostream>
#include <memory>
#include <string>
#include <thread>
#include <tuple>
#include <unordered_map>
#include <vector>

#include "galbot_motion.hpp"
#include "galbot_navigation.hpp"
#include "galbot_robot.hpp"

#include <opencv2/opencv.hpp>

using namespace galbot::sdk;

static std::vector<double> pose_to_vector7(const Pose& p) {
  return {p.position.x, p.position.y, p.position.z, p.orientation.x, p.orientation.y, p.orientation.z, p.orientation.w};
}

// Quaternion and rotation matrix utilities (without Eigen)
struct QuaternionST {
  double x, y, z, w;

  QuaternionST(double x = 0, double y = 0, double z = 0, double w = 1) : x(x), y(y), z(z), w(w) {}

  // Convert quaternion to 3x3 rotation matrix
  std::array<std::array<double, 3>, 3> to_matrix() const {
    std::array<std::array<double, 3>, 3> mat;

    double xx = x * x, yy = y * y, zz = z * z;
    double xy = x * y, xz = x * z, yz = y * z;
    double wx = w * x, wy = w * y, wz = w * z;

    mat[0][0] = 1 - 2 * (yy + zz);
    mat[0][1] = 2 * (xy - wz);
    mat[0][2] = 2 * (xz + wy);

    mat[1][0] = 2 * (xy + wz);
    mat[1][1] = 1 - 2 * (xx + zz);
    mat[1][2] = 2 * (yz - wx);

    mat[2][0] = 2 * (xz - wy);
    mat[2][1] = 2 * (yz + wx);
    mat[2][2] = 1 - 2 * (xx + yy);

    return mat;
  }

  // Create quaternion from rotation matrix
  static QuaternionST from_matrix(const std::array<std::array<double, 3>, 3>& mat) {
    double trace = mat[0][0] + mat[1][1] + mat[2][2];
    QuaternionST q;

    if (trace > 0) {
      double s = 0.5 / std::sqrt(trace + 1.0);
      q.w = 0.25 / s;
      q.x = (mat[2][1] - mat[1][2]) * s;
      q.y = (mat[0][2] - mat[2][0]) * s;
      q.z = (mat[1][0] - mat[0][1]) * s;
    } else if (mat[0][0] > mat[1][1] && mat[0][0] > mat[2][2]) {
      double s = 2.0 * std::sqrt(1.0 + mat[0][0] - mat[1][1] - mat[2][2]);
      q.w = (mat[2][1] - mat[1][2]) / s;
      q.x = 0.25 * s;
      q.y = (mat[0][1] + mat[1][0]) / s;
      q.z = (mat[0][2] + mat[2][0]) / s;
    } else if (mat[1][1] > mat[2][2]) {
      double s = 2.0 * std::sqrt(1.0 + mat[1][1] - mat[0][0] - mat[2][2]);
      q.w = (mat[0][2] - mat[2][0]) / s;
      q.x = (mat[0][1] + mat[1][0]) / s;
      q.y = 0.25 * s;
      q.z = (mat[1][2] + mat[2][1]) / s;
    } else {
      double s = 2.0 * std::sqrt(1.0 + mat[2][2] - mat[0][0] - mat[1][1]);
      q.w = (mat[1][0] - mat[0][1]) / s;
      q.x = (mat[0][2] + mat[2][0]) / s;
      q.y = (mat[1][2] + mat[2][1]) / s;
      q.z = 0.25 * s;
    }

    return q;
  }
};

// 4x4 transformation matrix
struct Transform {
  std::array<std::array<double, 4>, 4> mat;

  Transform() {
    // Identity matrix
    for (int i = 0; i < 4; ++i) {
      for (int j = 0; j < 4; ++j) {
        mat[i][j] = (i == j) ? 1.0 : 0.0;
      }
    }
  }

  // Set rotation from quaternion
  void set_rotation(const QuaternionST& q) {
    auto rot = q.to_matrix();
    for (int i = 0; i < 3; ++i) {
      for (int j = 0; j < 3; ++j) {
        mat[i][j] = rot[i][j];
      }
    }
  }

  // Set translation
  void set_translation(const std::array<double, 3>& t) {
    mat[0][3] = t[0];
    mat[1][3] = t[1];
    mat[2][3] = t[2];
  }

  // Matrix multiplication
  Transform operator*(const Transform& other) const {
    Transform result;
    for (int i = 0; i < 4; ++i) {
      for (int j = 0; j < 4; ++j) {
        result.mat[i][j] = 0;
        for (int k = 0; k < 4; ++k) {
          result.mat[i][j] += mat[i][k] * other.mat[k][j];
        }
      }
    }
    return result;
  }

  // Transform a 3D point
  std::array<double, 3> transform_point(const std::array<double, 3>& p) const {
    std::array<double, 3> result;
    for (int i = 0; i < 3; ++i) {
      result[i] = mat[i][0] * p[0] + mat[i][1] * p[1] + mat[i][2] * p[2] + mat[i][3];
    }
    return result;
  }

  // Get rotation as quaternion
  QuaternionST get_rotation() const {
    std::array<std::array<double, 3>, 3> rot;
    for (int i = 0; i < 3; ++i) {
      for (int j = 0; j < 3; ++j) {
        rot[i][j] = mat[i][j];
      }
    }
    return QuaternionST::from_matrix(rot);
  }

  // Get translation
  std::array<double, 3> get_translation() const { return {mat[0][3], mat[1][3], mat[2][3]}; }
};

cv::Mat decode_rgb_image(const std::vector<uint8_t>& image_data) {
  cv::Mat nparr(1, image_data.size(), CV_8UC1, (void*) image_data.data());
  cv::Mat img = cv::imdecode(nparr, cv::IMREAD_COLOR);

  if (img.empty()) {
    throw std::runtime_error("Failed to decode RGB Image");
  }
  return img;
}

cv::Mat decode_depth_image(const std::vector<uint8_t>& image_data, float depth_scale, int height = 720,
                           int width = 1280) {
  cv::Mat depth_img(height, width, CV_16UC1);
  std::memcpy(depth_img.data, image_data.data(), image_data.size());

  cv::Mat depth_img_float;
  depth_img.convertTo(depth_img_float, CV_32FC1, 1.0 / depth_scale);

  return depth_img_float;
}

std::vector<double> get_navigation_pose(const std::vector<double>& object_goal_pose, GalbotMotion& motion,
                                        const std::string& arm = "left_arm") {
  if (arm != "left_arm" && arm != "right_arm") {
    throw std::invalid_argument("arm must be left_arm or right_arm");
  }

  try {
    auto [status, ee_pose_in_base] = motion.get_end_effector_pose(arm + "_end_effector_mount_link", "base_link");

    double offset_y;
    if (status != MotionStatus::SUCCESS) {
      std::cout << "❌ Failed to get end effector pose: status=" << (int) status << std::endl;
      // Align with Python: still use reported EE y when the call fails (if available)
      offset_y = (ee_pose_in_base.size() >= 2) ? ee_pose_in_base[1] : 0.0;
    } else {
      std::cout << "✅ Successfully got end effector pose" << std::endl;
      offset_y = 0.3;
    }

    // Create transformation matrix for base goal pose
    Transform base_goal_pose_mat;
    QuaternionST obj_quat(object_goal_pose[3], object_goal_pose[4], object_goal_pose[5], object_goal_pose[6]);
    base_goal_pose_mat.set_rotation(obj_quat);
    base_goal_pose_mat.set_translation({object_goal_pose[0], object_goal_pose[1], 0.0});

    // Apply offset: move 0.6m backward and offset_y in y direction
    Transform offset_mat;
    offset_mat.set_translation({-0.6, -offset_y, 0.0});

    base_goal_pose_mat = base_goal_pose_mat * offset_mat;

    // Extract pose
    auto pos = base_goal_pose_mat.get_translation();
    auto quat = base_goal_pose_mat.get_rotation();

    return {pos[0], pos[1], pos[2], quat.x, quat.y, quat.z, quat.w};

  } catch (const std::exception& e) {
    std::cout << "Failed to get navigation target pose: " << e.what() << std::endl;
    return {1.0, -1.0, 0.0, 0.0, 0.0, 0.0, 1.0};
  }
}

void navigation_to_goal(GalbotNavigation& nav, const std::vector<double>& goal_pose, int retry_cnt = 3) {
  try {
    auto cur_pose = nav.get_current_pose();
    std::cout << "Current pose: [";
    for (auto val : pose_to_vector7(cur_pose))
      std::cout << val << " ";
    std::cout << "]" << std::endl;

    Pose goal(goal_pose);
    if (nav.check_path_reachability(goal, cur_pose)) {
      retry_cnt = 3;
      NavigationStatus status;

      while (true) {
        status = nav.navigate_to_goal(goal, true, true, 20.0f);
        std::this_thread::sleep_for(std::chrono::milliseconds(500));
        retry_cnt--;

        if (nav.check_goal_arrival() || retry_cnt < 0) {
          break;
        } else {
          std::cout << "Navigation failed: status=" << (int) status << ", retrying: " << retry_cnt << std::endl;
        }
      }

      std::cout << "navigate_to_goal return status: " << (int) status << std::endl;
      std::cout << "Has arrived: " << nav.check_goal_arrival() << std::endl;
    } else {
      std::cout << "Path unreachable or unsafe" << std::endl;
    }
  } catch (const std::exception& e) {
    std::cout << "Exception occurred during navigation: " << e.what() << std::endl;
  }
}

void lift_camera_up(GalbotMotion& motion, const std::vector<double>& target_pose, const std::string& target_chain,
                    const std::string& reference_frame) {
  try {
    int retry_cnt = 3;
    std::vector<double> cur_ee_pose;
    MotionStatus status;

    while (true) {
      std::tie(status, cur_ee_pose) =
          motion.get_end_effector_pose_on_chain(target_chain, "EndEffector", reference_frame);

      std::this_thread::sleep_for(std::chrono::milliseconds(500));
      retry_cnt--;

      if (status == MotionStatus::SUCCESS) {
        std::cout << "✅ Successfully got end effector pose" << std::endl;
        break;
      } else if (retry_cnt < 0) {
        cur_ee_pose = {0.1267, 0.2342, 0.7356, 0.0220, 0.0127, 0.0343, 0.9991};
        std::cout << "❌ Failed to get end effector pose, using default" << std::endl;
        break;
      } else {
        std::cout << "Failed to get end effector pose: status=" << (int) status << ", retrying: " << retry_cnt
                  << std::endl;
      }
    }

    std::vector<double> tgt_ee_pose = cur_ee_pose;
    tgt_ee_pose[2] = target_pose[2] - 0.1;

    std::cout << "Target end effector pose: [";
    for (auto val : tgt_ee_pose)
      std::cout << val << " ";
    std::cout << "]" << std::endl;

    retry_cnt = 3;
    while (true) {
      status = motion.set_end_effector_pose(tgt_ee_pose, target_chain, reference_frame, nullptr, false, true, 5.0,
                                            std::make_shared<Parameter>());

      std::this_thread::sleep_for(std::chrono::milliseconds(500));
      retry_cnt--;

      if (status == MotionStatus::SUCCESS || retry_cnt < 0) {
        std::cout << "✅ Successfully set end effector pose: status=" << (int) status << std::endl;
        break;
      } else {
        std::cout << "Failed to set end effector pose: status=" << (int) status << ", retrying: " << retry_cnt
                  << std::endl;
      }
    }
  } catch (const std::exception& e) {
    std::cout << "❌ Failed to lift camera: " << e.what() << std::endl;
  }
}

std::vector<double> detect_target(const cv::Mat& img, const cv::Mat& depth_img) {
  try {
    // NOTE: This is a placeholder function
    // In real-world scenario, implement actual computer vision detection

    // OpenCV frame: x right, y down, z forward
    std::vector<double> default_pose = {0.0, 0.20, 0.29, 0.0, 0.71, 0.0, 0.71};

    return default_pose;
  } catch (const std::exception& e) {
    std::cout << "Target detection exception: " << e.what() << std::endl;
    return {};
  }
}

std::vector<double> pose_camera_to_base(GalbotRobot& robot, const std::vector<double>& pose_camera) {
  std::string source_frame = "left_arm_camera_color_optical_frame";
  std::string target_frame = "base_link";

  auto [base_to_cam, success] = robot.get_transform(target_frame, source_frame);

  if (!success || base_to_cam.empty()) {
    std::cout << "Failed to get transform from camera to chassis" << std::endl;
    return {};
  } else {
    std::cout << "base_to_cam: [";
    for (auto val : base_to_cam)
      std::cout << val << " ";
    std::cout << "]" << std::endl;
  }

  Transform base_to_cam_mat;
  QuaternionST quat(base_to_cam[3], base_to_cam[4], base_to_cam[5], base_to_cam[6]);
  base_to_cam_mat.set_rotation(quat);
  base_to_cam_mat.set_translation({base_to_cam[0], base_to_cam[1], base_to_cam[2]});

  std::array<double, 3> cam_pos = {pose_camera[0], pose_camera[1], pose_camera[2]};
  auto pose_base = base_to_cam_mat.transform_point(cam_pos);

  return {pose_base[0], pose_base[1], pose_base[2], 0.0, 0.0, 0.0, 1.0};
}

std::vector<double> detect_object(GalbotRobot& robot, const std::string& arm = "left_arm") {
  const std::vector<double> k_zero_pose = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0};

  try {
    SensorType rgb_sensor, depth_sensor;

    if (arm == "left_arm") {
      rgb_sensor = SensorType::LEFT_ARM_CAMERA;
      depth_sensor = SensorType::LEFT_ARM_DEPTH_CAMERA;
    } else if (arm == "right_arm") {
      rgb_sensor = SensorType::RIGHT_ARM_CAMERA;
      depth_sensor = SensorType::RIGHT_ARM_DEPTH_CAMERA;
    } else {
      throw std::invalid_argument("arm must be left_arm or right_arm");
    }

    auto rgb_image_data = robot.get_rgb_data(rgb_sensor);
    auto depth_data = robot.get_depth_data(depth_sensor);

    // Match Python: need both RGB and depth before running detection (otherwise NameError there).
    if (!rgb_image_data) {
      std::cout << "No rgb image data!" << std::endl;
      return k_zero_pose;
    }
    std::cout << "Get rgb image success" << std::endl;

    if (!depth_data) {
      std::cout << "No depth_data!" << std::endl;
      return k_zero_pose;
    }
    std::cout << "Get depth data success" << std::endl;

    auto img_ptr = rgb_image_data->convert_to_cv2_mat();
    auto depth_ptr = depth_data->convert_to_cv2_mat();
    if (!img_ptr || img_ptr->empty()) {
      std::cout << "Failed to decode rgb image" << std::endl;
      return k_zero_pose;
    }
    if (!depth_ptr || depth_ptr->empty()) {
      std::cout << "Failed to decode depth image" << std::endl;
      return k_zero_pose;
    }

    cv::Mat img = *img_ptr;
    cv::Mat depth_img = *depth_ptr;

    auto object_pose_camera = detect_target(img, depth_img);

    if (object_pose_camera.empty()) {
      std::cout << "Target detection failed" << std::endl;
      return k_zero_pose;
    }

    std::cout << "object_pose_camera: [";
    for (auto val : object_pose_camera)
      std::cout << val << " ";
    std::cout << "]" << std::endl;

    auto object_pose_base = pose_camera_to_base(robot, object_pose_camera);
    if (object_pose_base.size() != 7) {
      std::cout << "Target pose in chassis coordinate system: (invalid / transform failed)" << std::endl;
      return k_zero_pose;
    }
    std::cout << "Target pose in chassis coordinate system: [";
    for (auto val : object_pose_base)
      std::cout << val << " ";
    std::cout << "]" << std::endl;

    return object_pose_base;

  } catch (const std::exception& e) {
    std::cout << "Target detection exception: " << e.what() << std::endl;
    return k_zero_pose;
  }
}

void check_robot_safety() {
  std::cout << "⚠️  Note: 1. Please ensure the emergency stop button of the robot is released; "
            << "2. Please ensure there are no obstructions around the robot to avoid unexpected situations. "
            << "3. Please ensure the area around the robot is clear of obstacles." << std::endl;

  while (true) {
    std::cout << "Please confirm that the robot's emergency stop button is released "
              << "and there are no obstructions, continue? (y/n)..." << std::endl;

    std::string key;
    std::cin >> key;

    if (key == "y" || key == "Y") {
      std::cout << "User confirmed, continuing..." << std::endl;
      break;
    } else if (key == "n" || key == "N") {
      std::cout << "User did not confirm, exiting program..." << std::endl;
      exit(1);
    } else {
      std::cout << "Invalid input, please enter 'y' or 'n'" << std::endl;
    }
  }
}

void pick_and_place(GalbotRobot& robot, GalbotNavigation& nav, GalbotMotion& motion,
                    const std::vector<double>& object_pose_base, const std::string& target_chain,
                    const std::string& reference_frame) {
  try {
    // Attach tool to end effector
    auto status = motion.attach_tool("left_arm", "galbot_gripper");
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    if (status != MotionStatus::SUCCESS) {
      std::cout << "❌ Failed to attach tool: status=" << (int) status << std::endl;
    } else {
      std::cout << "✅ Successfully attached tool: status=" << (int) status << std::endl;
    }

    // Open left gripper
    auto gripper_status = robot.set_gripper_command("left_gripper", 0.1, 0.05, 10, false);
    std::this_thread::sleep_for(std::chrono::milliseconds(500));
    std::cout << "✅ Successfully set left gripper width to 0.1m: status=" << (int) gripper_status << std::endl;

    std::cout << "object_pose_base: [";
    for (auto val : object_pose_base)
      std::cout << val << " ";
    std::cout << "]" << std::endl;

    // Reach to target position
    int retry_cnt = 3;
    while (true) {
      status = motion.set_end_effector_pose(object_pose_base, target_chain, reference_frame, nullptr, false, true, 5.0,
                                            std::make_shared<Parameter>());

      std::this_thread::sleep_for(std::chrono::seconds(1));
      retry_cnt--;

      if (status == MotionStatus::SUCCESS || retry_cnt < 0) {
        break;
      } else {
        std::cout << "Failed to set end effector pose: status=" << (int) status << ", retry count: " << retry_cnt
                  << std::endl;
      }
    }

    if (status != MotionStatus::SUCCESS) {
      std::cout << "❌ Failed to set end effector pose: status=" << (int) status << std::endl;
    } else {
      std::cout << "✅ Successfully set end effector pose: status=" << (int) status << std::endl;
    }

    // Close gripper to grasp object
    gripper_status = robot.set_gripper_command("left_gripper", 0.02, 0.05, 10, false);
    std::this_thread::sleep_for(std::chrono::milliseconds(500));
    std::cout << "✅ Successfully closed left gripper: status=" << (int) gripper_status << std::endl;

    // Attach target object (box scale length/width/height in m; default {} is zero and INVALID_INPUT)
    std::array<double, 3> grasp_box_scale{0.05, 0.05, 0.05};
    status = motion.attach_target_object("grasped_box", "box", {0, 0, 0, 0, 0, 0, 1}, grasp_box_scale, "", "left_arm",
                                         "ee_base");
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    if (status != MotionStatus::SUCCESS) {
      std::cout << "❌ Failed to attach target object: status=" << (int) status << std::endl;
    } else {
      std::cout << "✅ Successfully attached target object: status=" << (int) status << std::endl;
    }

    // Return to initial position
    navigation_to_goal(nav, {0, 0, 0, 0, 0, 0, 1});
    std::this_thread::sleep_for(std::chrono::seconds(2));
    std::cout << "✅ Successfully returned to initial position" << std::endl;

    // Release target
    gripper_status = robot.set_gripper_command("left_gripper", 0.1, 0.05, 10, false);
    std::this_thread::sleep_for(std::chrono::milliseconds(500));
    std::cout << "✅ Successfully released left gripper: status=" << (int) gripper_status << std::endl;

    // Detach target object
    status = motion.detach_target_object("grasped_box");
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    if (status != MotionStatus::SUCCESS) {
      std::cout << "❌ Failed to detach target object: status=" << (int) status << std::endl;
    } else {
      std::cout << "✅ Successfully detached target object: status=" << (int) status << std::endl;
    }

    // Detach tool from end effector
    status = motion.detach_tool("left_arm");
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    if (status != MotionStatus::SUCCESS) {
      std::cout << "❌ Failed to detach tool: status=" << (int) status << std::endl;
    } else {
      std::cout << "✅ Successfully detached tool: status=" << (int) status << std::endl;
    }

  } catch (const std::exception& e) {
    std::cout << "Exception occurred during pick_and_place: " << e.what() << std::endl;
  }
}

void run_move_whole_body_joint_zero(GalbotMotion& motion, const std::string& phase) {
  int retry_cnt = 3;
  const std::string suffix = phase.empty() ? "" : (" [" + phase + "]");
  while (true) {
    auto zero_status = motion.move_whole_body_joint_zero(true, 0.2, 15.0, std::make_shared<Parameter>());
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    if (zero_status == MotionStatus::SUCCESS) {
      std::cout << "✅ Successfully moved whole body joint zero" << suffix << ": status=" << (int) zero_status
                << std::endl;
      break;
    }

    retry_cnt--;
    if (retry_cnt < 0) {
      std::cout << "❌ Failed to move_whole_body_joint_zero after retries" << suffix << ", status=" << (int) zero_status
                << std::endl;
      break;
    }
    std::cout << "Failed to move_whole_body_joint_zero" << suffix << ": retry count: " << retry_cnt
              << ", status=" << (int) zero_status << std::endl;
  }
}

int main() {
  check_robot_safety();

  // Get robot instances
  auto& robot = GalbotRobot::get_instance(MachineType::G1);
  auto& motion = GalbotMotion::get_instance(MachineType::G1);
  auto& nav = GalbotNavigation::get_instance(MachineType::G1);

  try {
    // Enable sensors
    std::unordered_set<SensorType> enable_sensor_set = {SensorType::LEFT_ARM_CAMERA, SensorType::LEFT_ARM_DEPTH_CAMERA,
                                                        SensorType::BASE_LIDAR, SensorType::TORSO_IMU};

    // Initialize robot
    if (robot.init(enable_sensor_set)) {
      std::cout << "GalbotRobot initialization successful" << std::endl;
    } else {
      std::cout << "GalbotRobot initialization failed" << std::endl;
    }

    if (motion.init()) {
      std::cout << "GalbotMotion initialization successful" << std::endl;
    } else {
      std::cout << "GalbotMotion initialization failed" << std::endl;
    }

    if (nav.init()) {
      std::cout << "GalbotNavigation initialization successful" << std::endl;
    } else {
      std::cout << "GalbotNavigation initialization failed" << std::endl;
    }

    // Wait for data readiness
    std::this_thread::sleep_for(std::chrono::seconds(1));

    // Reset whole body to SDK zero pose before navigation and perception
    run_move_whole_body_joint_zero(motion, "startup");

    // Relocalize robot if not localized
    while (true) {
      if (nav.is_localized()) {
        std::cout << "✅ Robot localized successfully, proceeding to navigate to goal..." << std::endl;
        break;
      } else {
        std::cout << "❌ Navigation not localized, relocalizing..." << std::endl;
        nav.relocalize(Pose(std::vector<double>{0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0}));
        std::this_thread::sleep_for(std::chrono::seconds(2));
      }
    }

    // Calculate navigation target pose
    std::vector<double> object_goal_pose = {1.0, -1.0, 1.0, 0, 0, 0, 1};
    auto base_goal_pose = get_navigation_pose(object_goal_pose, motion);

    std::cout << "Navigation target pose: [";
    for (auto val : base_goal_pose)
      std::cout << val << " ";
    std::cout << "]" << std::endl;

    // Navigate to target pose
    navigation_to_goal(nav, base_goal_pose);
    std::cout << std::endl;

    // Lift camera
    lift_camera_up(motion, object_goal_pose, "left_arm", "base_link");
    std::cout << std::endl;

    // Detect target
    auto object_pose_base = detect_object(robot, "left_arm");
    std::cout << std::endl;

    if (object_pose_base.size() != 7) {
      std::cout << "Skipping pick_and_place: invalid object pose (expected 7 values)" << std::endl;
    } else {
      pick_and_place(robot, nav, motion, object_pose_base, "left_arm", "base_link");
    }
    std::cout << std::endl;

    // After grasping target, move the whole body back to SDK zero pose
    run_move_whole_body_joint_zero(motion, "post-grasp");

  } catch (const std::exception& e) {
    std::cout << "Exception occurred: " << e.what() << std::endl;
  }

  // Cleanup
  robot.request_shutdown();
  robot.wait_for_shutdown();
  robot.destroy();
  std::cout << "Resource release successful" << std::endl;

  return 0;
}