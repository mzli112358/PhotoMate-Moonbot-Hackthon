#include <chrono>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <thread>
#include <unordered_set>
#include <vector>

#include "galbot_robot.hpp"
#include "opencv2/opencv.hpp"

using namespace galbot::sdk;

constexpr double kSpeedRadS = 0.12;
constexpr double kTimeoutS = 20.0;
const std::string kWelcomePcmRel{};

constexpr double kHeadArmsDemoDtS = 0.06;
constexpr int kHeadArmsDemoSeg1 = 28;
constexpr int kHeadArmsDemoSeg2 = 32;
constexpr int kHeadArmsDemoSeg3 = 28;
constexpr double kHeadSwayYawPosRad = 0.22;
constexpr double kHeadSwayYawNegRad = -0.22;

const std::vector<double> kPresetLeg = {0.5, 1.5, 1.0, 0.0, 0.0};
const std::vector<double> kPresetHead = {0.0, 0.0};
const std::vector<double> kPresetLeftArm = {2.0, -1.5, -0.6, -1.7, 0.0, -0.8, 0.0};
const std::vector<double> kPresetRightArm = {-2.0, 1.5, 0.6, 1.7, 0.0, 0.8, 0.0};

const std::vector<std::string> kHeadArmsDemoGroups = {"head", "left_arm", "right_arm"};

TrajectoryPoint make_point(const std::vector<double>& joint_positions_rad, double time_from_start_sec) {
  TrajectoryPoint point;
  point.time_from_start_second = time_from_start_sec;
  for (double q : joint_positions_rad) {
    JointCommand jc;
    jc.position = q;
    point.joint_command_vec.push_back(jc);
  }
  return point;
}

Trajectory build_trajectory(const std::vector<std::vector<double>>& joint_waypoints_rad,
                            const std::vector<std::string>& joint_groups, double time_step_sec) {
  Trajectory trajectory;
  trajectory.joint_groups = joint_groups;
  trajectory.joint_names = {};
  double time_from_start_sec = 0.0;
  for (const std::vector<double>& waypoint : joint_waypoints_rad) {
    time_from_start_sec += time_step_sec;
    trajectory.points.push_back(make_point(waypoint, time_from_start_sec));
  }
  return trajectory;
}

std::vector<std::vector<double>> linspace_rows(const std::vector<double>& start_positions_rad,
                                               const std::vector<double>& end_positions_rad, int num_samples) {
  std::vector<std::vector<double>> out;
  if (num_samples < 2) {
    out.push_back(start_positions_rad);
    return out;
  }
  out.reserve(static_cast<size_t>(num_samples));
  const int n = num_samples - 1;
  for (int sample_idx = 0; sample_idx < num_samples; ++sample_idx) {
    const double blend = static_cast<double>(sample_idx) / static_cast<double>(n);
    std::vector<double> row(start_positions_rad.size());
    for (size_t j = 0; j < start_positions_rad.size(); ++j) {
      row[j] = start_positions_rad[j] + blend * (end_positions_rad[j] - start_positions_rad[j]);
    }
    out.push_back(std::move(row));
  }
  return out;
}

void append_rows(std::vector<std::vector<double>>& dest, const std::vector<std::vector<double>>& src) {
  dest.insert(dest.end(), src.begin(), src.end());
}

std::vector<double> upper_body_preset_pose_rad() {
  std::vector<double> pose;
  pose.reserve(kPresetHead.size() + kPresetLeftArm.size() + kPresetRightArm.size());
  pose.insert(pose.end(), kPresetHead.begin(), kPresetHead.end());
  pose.insert(pose.end(), kPresetLeftArm.begin(), kPresetLeftArm.end());
  pose.insert(pose.end(), kPresetRightArm.begin(), kPresetRightArm.end());
  return pose;
}

// Slow head yaw left-right (joint2 fixed); arms shift slightly with the sway. Legs not in trajectory.
std::vector<std::vector<double>> build_slow_head_arms_demo_waypoints_rad() {
  const std::vector<double> home = upper_body_preset_pose_rad();
  const std::vector<double> pose_yaw_pos = {
    kHeadSwayYawPosRad, 0.0,
    2.0 + 0.07, -1.5 + 0.04, -0.6, -1.7, 0.0, -0.8 + 0.04, 0.0,
    -2.0 - 0.07, 1.5 - 0.04, 0.6, 1.7, 0.0, 0.8 - 0.04, 0.0
  };
  const std::vector<double> pose_yaw_neg = {
    kHeadSwayYawNegRad, 0.0,
    2.0 - 0.05, -1.5 - 0.03, -0.6, -1.7, 0.0, -0.8 - 0.03, 0.0,
    -2.0 + 0.05, 1.5 + 0.03, 0.6, 1.7, 0.0, 0.8 + 0.03, 0.0
  };

  std::vector<std::vector<double>> rows;
  append_rows(rows, linspace_rows(home, pose_yaw_pos, kHeadArmsDemoSeg1));
  append_rows(rows, linspace_rows(pose_yaw_pos, pose_yaw_neg, kHeadArmsDemoSeg2));
  append_rows(rows, linspace_rows(pose_yaw_neg, home, kHeadArmsDemoSeg3));
  return rows;
}

std::string getenv_string(const std::string& key) {
  const char* v = std::getenv(key.c_str());
  return (v != nullptr && v[0] != '\0') ? std::string(v) : std::string();
}

std::string resolve_welcome_pcm_path() {
  const std::string env_pcm = getenv_string("GALBOT_WELCOME_PCM");
  if (!env_pcm.empty()) {
    return env_pcm;
  }
  return kWelcomePcmRel;
}

bool play_pcm(GalbotRobot& robot, const std::string& pcm_file_path) {
  constexpr std::size_t kPcmReadChunkBytes = 2560;
  const std::string audio_stream_id = "install_welcome_pcm";
  std::ifstream pcm_input(pcm_file_path, std::ios::binary);
  if (!pcm_input) {
    std::cerr << "[audio] Failed to open/read PCM: " << pcm_file_path << std::endl;
    return false;
  }
  std::vector<char> buf(kPcmReadChunkBytes);
  while (pcm_input) {
    pcm_input.read(buf.data(), static_cast<std::streamsize>(kPcmReadChunkBytes));
    const std::streamsize n = pcm_input.gcount();
    if (n <= 0) {
      break;
    }
    const std::string chunk(buf.data(), static_cast<std::size_t>(n));
    if (!robot.write_audio_stream_output(chunk, audio_stream_id)) {
      std::cerr << "[audio] write_audio_stream_output failed" << std::endl;
      return false;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
  }
  return true;
}

void print_summary(const std::string& step_description, bool step_passed) {
  std::cout << (step_passed ? "[PASS] " : "[FAIL] ") << step_description << std::endl;
}

int main() {
  bool body_preset_step_passed = false;
  bool welcome_pcm_playback_ok = false;
  bool head_camera_capture_ok = false;

  auto& robot = GalbotRobot::get_instance(MachineType::G1);

  const std::unordered_set<SensorType> required_sensors = {SensorType::HEAD_LEFT_CAMERA};
  if (!robot.init(required_sensors)) {
    std::cerr << "GalbotRobot::init failed" << std::endl;
    return 1;
  }
  std::cout << "Robot initialized (HEAD_LEFT_CAMERA enabled)" << std::endl;
  std::this_thread::sleep_for(std::chrono::duration<double>(5.0));

  if (!robot.set_volume(100.0f)) {
    std::cerr << "[WARN] set_volume(100) failed; welcome PCM may play quietly" << std::endl;
  }

  bool leg_step_ok = false;
  bool upper_step_ok = false;
  bool demo_step_ok = false;

  const ControlStatus leg_set_status =
      robot.set_joint_positions(kPresetLeg, {"leg"}, {}, true, kSpeedRadS, kTimeoutS);
  leg_step_ok = (leg_set_status == ControlStatus::SUCCESS);
  if (!leg_step_ok) {
    std::cerr << "[FAIL] Leg set_joint_positions not SUCCESS (blocking)" << std::endl;
  }
  print_summary("Leg set_joint_positions (blocking)", leg_step_ok);

  if (leg_step_ok) {
    std::vector<double> upper_body_joint_targets_rad;
    upper_body_joint_targets_rad.insert(upper_body_joint_targets_rad.end(), kPresetHead.begin(), kPresetHead.end());
    upper_body_joint_targets_rad.insert(upper_body_joint_targets_rad.end(), kPresetLeftArm.begin(),
                                        kPresetLeftArm.end());
    upper_body_joint_targets_rad.insert(upper_body_joint_targets_rad.end(), kPresetRightArm.begin(),
                                        kPresetRightArm.end());

    const ControlStatus upper_body_set_status =
        robot.set_joint_positions(upper_body_joint_targets_rad, kHeadArmsDemoGroups, {}, true, kSpeedRadS, kTimeoutS);
    upper_step_ok = (upper_body_set_status == ControlStatus::SUCCESS);
    if (!upper_step_ok) {
      std::cerr << "[FAIL] head/left_arm/right_arm set_joint_positions not SUCCESS (blocking)" << std::endl;
    }
    print_summary("Upper set_joint_positions head+arms (blocking)", upper_step_ok);

    if (upper_step_ok) {
      const std::vector<std::vector<double>> demo_waypoints_rad = build_slow_head_arms_demo_waypoints_rad();
      const Trajectory demo_trajectory = build_trajectory(demo_waypoints_rad, kHeadArmsDemoGroups, kHeadArmsDemoDtS);
      const ControlStatus demo_exec_status = robot.execute_joint_trajectory(demo_trajectory, true);
      demo_step_ok = (demo_exec_status == ControlStatus::SUCCESS);
      if (!demo_step_ok) {
        std::cerr << "[FAIL] Head/arms execute_joint_trajectory not SUCCESS (blocking)" << std::endl;
      }
      print_summary("Head/arms demo trajectory (blocking)", demo_step_ok);
    } else {
      std::cerr << "[INFO] Skipping head/arms demo: upper set_joint_positions did not return SUCCESS." << std::endl;
      print_summary("Head/arms demo trajectory (blocking)", false);
    }
  } else {
    std::cerr << "[INFO] Skipping upper-body preset and head/arms demo: leg set_joint_positions not SUCCESS."
              << std::endl;
    print_summary("Upper set_joint_positions head+arms (blocking)", false);
    print_summary("Head/arms demo trajectory (blocking)", false);
  }

  body_preset_step_passed = leg_step_ok && upper_step_ok && demo_step_ok;

  const std::string resolved_welcome_pcm_path = resolve_welcome_pcm_path();
  std::cout << "PCM path: " << resolved_welcome_pcm_path << std::endl;
  if (resolved_welcome_pcm_path.empty()) {
    std::cerr << "[FAIL] Welcome PCM path is empty: set GALBOT_WELCOME_PCM (no built-in default path)."
              << std::endl;
    welcome_pcm_playback_ok = false;
  } else {
    std::ifstream pcm_probe(resolved_welcome_pcm_path, std::ios::binary);
    if (!pcm_probe) {
      std::cerr << "[FAIL] PCM file not found or not readable: " << resolved_welcome_pcm_path << std::endl;
      welcome_pcm_playback_ok = false;
    } else {
      welcome_pcm_playback_ok = play_pcm(robot, resolved_welcome_pcm_path);
    }
  }
  print_summary("Welcome PCM playback", welcome_pcm_playback_ok);

  const std::shared_ptr<RgbData> head_rgb_data = robot.get_rgb_data(SensorType::HEAD_LEFT_CAMERA);
  if (!head_rgb_data) {
    std::cerr << "[FAIL] get_rgb_data returned null" << std::endl;
    head_camera_capture_ok = false;
  } else if (head_rgb_data->data.empty()) {
    std::cerr << "[FAIL] head camera data missing or empty" << std::endl;
    head_camera_capture_ok = false;
  } else {
    head_camera_capture_ok = true;
    std::cout << "Head camera: " << head_rgb_data->data.size() << " bytes format=" << head_rgb_data->format
              << std::endl;
    const std::shared_ptr<cv::Mat> head_image_mat = head_rgb_data->convert_to_cv2_mat();
    if (head_image_mat && !head_image_mat->empty()) {
      std::cout << "  decoded size " << head_image_mat->cols << "x" << head_image_mat->rows << std::endl;
    }
  }
  print_summary("Head camera data", head_camera_capture_ok);

  std::cout << "\n======== Summary ========" << std::endl;
  print_summary("Motion verify (blocking)", body_preset_step_passed);
  print_summary("Audio", welcome_pcm_playback_ok);
  print_summary("Head camera", head_camera_capture_ok);

  const bool installation_all_checks_passed =
      body_preset_step_passed && welcome_pcm_playback_ok && head_camera_capture_ok;
  std::cout << (installation_all_checks_passed ? "\nOverall: PASS\n" : "\nOverall: FAIL\n");

  robot.request_shutdown();
  robot.wait_for_shutdown();
  robot.destroy();

  return installation_all_checks_passed ? 0 : 1;
}
