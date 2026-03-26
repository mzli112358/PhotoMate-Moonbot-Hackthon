#pragma once

#include <set>

#include "galbot_perception_types.hpp"

namespace galbot {
namespace sdk {
namespace g1 {

class GalbotPerception {
 public:
  /**
   * @brief Get the singleton instance of GalbotPerception.
   * @return Reference to the singleton instance.
   */
  static GalbotPerception& get_instance();

  /**
   * @brief Initialize perception and load models for the selected modules.
   * @param enabled_modules Set of perception modules to enable.
   * @return True if every requested module loaded successfully.
   */
  bool init(const std::set<PerceptionModule>& enabled_modules);

  /**
   * @brief Run a single inference for the given module.
   * @note After init, wait ~10s for models to be ready before calling run_once.
   * @param module Perception module to run.
   */
  bool run_once(PerceptionModule module);

  /**
   * @brief Block until the module produces a new result, or timeout. Use with run_once to fetch the latest output.
   * @param module    Perception module.
   * @param timeout_s Timeout in seconds.
   */
  bool wait_for_new_result(PerceptionModule module, double timeout_s = 5.0);

  /**
   * @brief Return the latest cached result for the module without blocking.
   * @param module Perception module.
   * @param result Output detection result.
   * @return True if a result is available, false if none.   */
  bool get_latest_result(PerceptionModule module, DetectionResult& result);

 private:
  GalbotPerception() = default;

  GalbotPerception(const GalbotPerception&) = delete;
  GalbotPerception& operator=(const GalbotPerception&) = delete;
  GalbotPerception(GalbotPerception&&) = delete;
  GalbotPerception& operator=(GalbotPerception&&) = delete;
};

}  // namespace g1
}  // namespace sdk
}  // namespace galbot
