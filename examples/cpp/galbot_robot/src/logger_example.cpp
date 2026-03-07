#include <iostream>

#include "galbot_robot.hpp"
#include "galbot_sdk_logger.hpp"

using namespace galbot::sdk::g1;

int main() {
  // 获取 GalbotRobot 的单例并初始化
  auto& robot = GalbotRobot::get_instance();
  robot.init();
  // ==============================
  // 1. 初始化 SDK 日志
  // ==============================
  LoggerConfig logger_config;
  // 日志生成路径，如不填充，默认生成在~/galbot_sdk_log/user_log路径
  logger_config.path = "";
  // 日志文件名，如不填充，默认日志名称为<process_name>_<current_time>_<pid>_<thread_id>.log
  logger_config.file_name = "";
  // 单个日志文件最大字节数
  logger_config.file_max_size = 1024 * 1024 * 10; // 10MB
  // 循环日志文件最大数量，单个文件写满后新建文件，最多保留 file_max_num 个文件
  logger_config.file_max_num = 5;
  // 输出日志最低等级
  logger_config.level = LogLevel::DEBUG;
  // 是否输出到终端，默认为 false
  logger_config.console_output = false;

  if (!init_galbot_sdk_logger(logger_config)) {
    std::cerr << "failed to init galbot sdk logger" << std::endl;
    return -1;
  } else {
    std::cout << "galbot sdk logger initialized successfully" << std::endl;
  }

  // ==============================
  // 2. 打印不同级别日志
  // ==============================
  GALBOT_SDK_LOG_TRACE << "this is trace log";
  GALBOT_SDK_LOG_DEBUG << "this is debug log";
  GALBOT_SDK_LOG_INFO << "this is info log";
  GALBOT_SDK_LOG_WARN << "this is warning log";
  GALBOT_SDK_LOG_ERROR << "this is error log";
  GALBOT_SDK_LOG_CRITICAL << "this is critical log";

  // ==============================
  // 3. 支持链式 << 风格
  // ==============================
  int robot_id = 3;
  GALBOT_SDK_LOG_INFO << "robot_id = " << robot_id;

  GALBOT_SDK_LOG_INFO << "example program finished";

  // 退出系统并进行SDK资源、logger资源释放
  robot.request_shutdown();
  robot.wait_for_shutdown();
  robot.destroy();
  return 0;
}
