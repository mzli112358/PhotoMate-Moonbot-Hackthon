#pragma once

#include <sstream>
#include <string>

#include "type.hpp"

namespace galbot {
namespace sdk {
namespace g1 {
/**
 * @brief Initialize the user logger for the Galbot SDK
 *
 * This function initializes the user logger with the specified configuration.
 * The logger supports asynchronous logging to files and console output.
 *
 * @param logger_config Configuration for the logger, including log level, file
 * path, file size, and other settings.
 * @return true if the logger was successfully initialized
 * @return false if the logger initialization failed
 */
bool init_galbot_sdk_logger(const LoggerConfig& logger_config);

class GalbotSdkLogStream {
 public:
  GalbotSdkLogStream(LogLevel level, const char* file, const char* func, int line)
      : level_(level), file_(file), func_(func), line_(line) {}

  template <typename T>
  GalbotSdkLogStream& operator<<(const T& v) {
    buffer_ << v;
    return *this;
  }

  GalbotSdkLogStream& operator<<(std::ostream& (*manip)(std::ostream&) ) {
    manip(buffer_);
    return *this;
  }

  ~GalbotSdkLogStream() noexcept {
    try {
      std::string s = buffer_.str();
      if (!s.empty()) {
        record_log(level_, file_, func_, line_, s.c_str());
      }
    } catch (...) {
      // 析构时不抛异常
    }
  }

 private:
  void record_log(LogLevel level, const char* file, const char* func, int line, const char* msg);

 private:
  LogLevel level_;
  const char* file_;
  const char* func_;
  int line_;
  std::ostringstream buffer_;
};

#define GALBOT_SDK_LOG_TRACE                                                                                        \
  galbot::sdk::g1::GalbotSdkLogStream(galbot::sdk::g1::LogLevel::TRACE,                                             \
                                      (strrchr(__FILE__, '/') ? (strrchr(__FILE__, '/') + 1) : __FILE__), __func__, \
                                      __LINE__)

#define GALBOT_SDK_LOG_DEBUG                                                                                        \
  galbot::sdk::g1::GalbotSdkLogStream(galbot::sdk::g1::LogLevel::DEBUG,                                             \
                                      (strrchr(__FILE__, '/') ? (strrchr(__FILE__, '/') + 1) : __FILE__), __func__, \
                                      __LINE__)

#define GALBOT_SDK_LOG_INFO                                                                                         \
  galbot::sdk::g1::GalbotSdkLogStream(galbot::sdk::g1::LogLevel::INFO,                                              \
                                      (strrchr(__FILE__, '/') ? (strrchr(__FILE__, '/') + 1) : __FILE__), __func__, \
                                      __LINE__)

#define GALBOT_SDK_LOG_WARN                                                                                         \
  galbot::sdk::g1::GalbotSdkLogStream(galbot::sdk::g1::LogLevel::WARN,                                              \
                                      (strrchr(__FILE__, '/') ? (strrchr(__FILE__, '/') + 1) : __FILE__), __func__, \
                                      __LINE__)

#define GALBOT_SDK_LOG_ERROR                                                                                        \
  galbot::sdk::g1::GalbotSdkLogStream(galbot::sdk::g1::LogLevel::ERROR,                                             \
                                      (strrchr(__FILE__, '/') ? (strrchr(__FILE__, '/') + 1) : __FILE__), __func__, \
                                      __LINE__)

#define GALBOT_SDK_LOG_CRITICAL                                                                                     \
  galbot::sdk::g1::GalbotSdkLogStream(galbot::sdk::g1::LogLevel::CRITICAL,                                          \
                                      (strrchr(__FILE__, '/') ? (strrchr(__FILE__, '/') + 1) : __FILE__), __func__, \
                                      __LINE__)

}  // namespace g1
}  // namespace sdk
}  // namespace galbot
