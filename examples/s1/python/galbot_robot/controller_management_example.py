import time

from galbot_sdk.s1 import GalbotRobot, ControlStatus, S1ControllerName, S1JointGroup


def print_active_controller(group_name, controller_name):
    print(f"Active controller for {group_name}: {controller_name}")


def print_status(operation, status):
    if status == ControlStatus.SUCCESS:
        print(f"{operation}: SUCCESS")
    else:
        # Assuming status can be cast to int or printed directly
        print(f"{operation}: FAILED (Status: {status})")


def main():
    # Get robot instance and init
    robot = GalbotRobot()
    print("Initializing robot...")
    if robot.init():
        print("System initialized successfully!")
    else:
        print("System initialization failed!")
        return

    # Wait for data readiness
    time.sleep(1)

    # Define the controller we want to test
    # Using LEFT_ARM_PVT_CTRL as the test subject
    test_controller = S1ControllerName.LEFT_ARM_PVT_CTRL
    controller_str = "LEFT_ARM_PVT_CTRL"
    test_group = S1JointGroup.left_arm
    group_str = "left_arm"

    print("\n--- Starting Controller Management Example ---")

    # 1. Get active controller before switching
    active_controller = robot.get_active_controller(test_group)
    print_active_controller(group_str, active_controller)

    # 2. Switch controller
    print(f"\n[Test 1] Switching to {controller_str}...")
    status = robot.switch_controller(test_controller)
    print_status("switch_controller", status)

    time.sleep(0.5)
    active_controller = robot.get_active_controller(test_group)
    print_active_controller(group_str, active_controller)

    # 3. Stop controller
    print(f"\n[Test 2] Stopping controller for group {group_str}...")
    # Using string overload/version for group
    status = robot.stop_controller(test_group)
    print_status("stop_controller", status)

    time.sleep(0.5)

    # 4. Release controller
    print(f"\n[Test 3] Releasing controller for group {group_str}...")
    status = robot.release_controller(test_group)
    print_status("release_controller", status)

    time.sleep(0.5)

    # 5. Acquire controller
    print(f"\n[Test 4] Acquiring {controller_str}...")
    status = robot.acquire_controller(test_controller)
    print_status("acquire_controller", status)

    time.sleep(0.5)

    # 6. Start controller
    print(f"\n[Test 5] Starting controller for group {group_str}...")
    status = robot.start_controller(test_group)
    print_status("start_controller", status)

    time.sleep(0.5)

    print("\n--- Controller Management Example Finished ---")

    # Shutdown
    robot.request_shutdown()
    robot.wait_for_shutdown()
    robot.destroy()
    print("Resources released successfully")


if __name__ == "__main__":
    main()
