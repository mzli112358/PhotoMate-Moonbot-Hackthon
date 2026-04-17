#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <string>

#include "galbot_robot.hpp"

using namespace galbot::sdk;

int main() {
    // Get object instance
    auto& robot = GalbotRobot::get_instance(MachineType::G1);

    // Initialize system
    if (robot.init()) {
        std::cout << "System initialized successfully!" << std::endl;
    } else {
        std::cerr << "System initialization failed!" << std::endl;
        return -1;
    }

    // Program started, waiting for data
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));

    // Please confirm the surrounding environment before chassis testing
    // Set chassis speed, linear_velocity first two fields are x and y velocities, angular_velocity third field is z rotation speed
    std::array<double, 3> linear_velocity = {0.05, 0.0, 0.0};    // 0.05 m/s
    std::array<double, 3> angular_velocity = {0.0, 0.0, 0.1};    // 0.1 rad/s
    double duration_s = 2.0;  // Automatically stop after 2 seconds

    if (robot.set_base_velocity(linear_velocity, angular_velocity, duration_s) == ControlStatus::SUCCESS) {
        std::cout << "Chassis speed set successfully; will stop in " << duration_s << " seconds then auto-stop." << std::endl;
    } else {
        std::cerr << "Set chassis speed failed." << std::endl;
    }

    // Wait for auto-stop to complete (with small buffer time)
    std::this_thread::sleep_for(std::chrono::duration<double>(duration_s + 0.5));

    // Exit system and release SDK resources
    robot.request_shutdown();
    robot.wait_for_shutdown();
    robot.destroy();

    return 0;
}
