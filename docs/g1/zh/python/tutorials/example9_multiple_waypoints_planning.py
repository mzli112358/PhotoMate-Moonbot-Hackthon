import time

try:
    import galbot_sdk.g1 as gm
    from galbot_sdk.g1 import GalbotRobot
    from galbot_sdk.g1 import GalbotMotion
    from galbot_sdk.g1 import GalbotNavigation
    from galbot_sdk.g1 import SensorType, G1JointGroup, ControlStatus, Trajectory, TrajectoryPoint, JointCommand
except ImportError:
    print("Failed to import galbot_sdk, please install it first or check if it is in PYTHONPATH")
    exit(1)

def printStatus(status):
        if(status == gm.MotionStatus.SUCCESS):
            print("Execute result: SUCCESS, completed successfully")
        elif(status == gm.MotionStatus.TIMEOUT):
            print("Execute result: TIMEOUT, timeout occurred")
        elif(status == gm.MotionStatus.FAULT):
            print("Execute result: FAULT, fault occurred, cannot continue")    
        elif(status == gm.MotionStatus.INVALID_INPUT):
            print("Execute result: INVALID_INPUT, input parameters do not meet requirements")
        elif(status == gm.MotionStatus.INIT_FAILED):
            print("Execute result: INIT_FAILED, internal communication component creation failed")
        elif(status == gm.MotionStatus.IN_PROGRESS):
            print("Execute result: IN_PROGRESS, motion is in progress but not yet reached")
        elif(status == gm.MotionStatus.STOPPED_UNREACHED):
            print("Execute result: STOPPED_UNREACHED, stopped but not yet reached target")
        elif(status == gm.MotionStatus.DATA_FETCH_FAILED):
            print("Execute result: DATA_FETCH_FAILED, data fetch failed")
        elif(status == gm.MotionStatus.PUBLISH_FAIL):
            print("Execute result: PUBLISH_FAIL, data publish failed")
        elif(status == gm.MotionStatus.COMM_DISCONNECTED):
            print("Execute result: COMM_DISCONNECTED, communication disconnected")

def check_robot_safety() -> None:
    """
    Check if the robot is safe to operate.
    Prompts the user to confirm safety conditions before proceeding.
    """
    # Prompt for precautions
    print(
        "⚠️  Note: 1. Please ensure the robot's emergency stop button is released; "
        "2. Please ensure there are no obstacles in front, back, left, and right "
        "of the robot to avoid unexpected situations."
    )
    
    while True:
        key = input(
            "Please confirm that the robot's emergency stop button is released "
            "and there are no obstacles. Continue? (y/n)..."
        ).lower()
        
        if key == 'y':
            print("User confirmed, continuing execution...")
            break
        elif key == 'n':
            print("User not confirmed, program exiting...")
            exit(1)
        else:
            print("Input error, please enter 'y' or 'n'")

def main():
    check_robot_safety()
    try:
        # Get GalbotMotion and GalbotRobot singletons
        robot = GalbotRobot()
        motion = GalbotMotion()
        nav = GalbotNavigation()

        if robot.init():
            print("GalbotRobot initialized successfully")
        else:
            print("GalbotRobot initialization failed")
        if motion.init():
            print("GalbotMotion initialized successfully")
        else:
            print("GalbotMotion initialization failed")
        if nav.init():
            print("GalbotNavigation initialized successfully")
        else:
            print("GalbotNavigation initialization failed")
        
        # Add a box collision object into Motion environment.
        # This affects Motion-side collision checking (e.g., motion_plan/check_collision).
        try:
            obstacle_id = "box_test_1"
            obj_type = "box"
            obj_pose = [1.0, 0.0, 1.0, 0,0,0,1]
            obj_size = [1.0, 1.0, 1.0]
            target_frame = "world"
            status = motion.add_obstacle(
                obstacle_id=obstacle_id,
                obstacle_type=obj_type,
                pose=obj_pose,
                scale=obj_size,
                target_frame=target_frame
            )
            printStatus(status)
            print(f"✅ Obstacle {obstacle_id} added successfully")
            motion.clear_obstacle()
            print(f"✅ Obstacle {obstacle_id} cleared successfully")
        except Exception as e:
            print(f"Failed to add obstacle {obstacle_id}: {e}")

        # Wait for data to be ready
        time.sleep(2)

        chain_joints = {
            "leg": [0.4992,1.4991,1.0005,0.0000,-0.0004],
            "head": [0.0000,0.0],
            "left_arm": [1.9999,-1.6000,-0.5999,-1.6999,0.0000,-0.7999,0.0000],
            "right_arm": [-2.0000,1.6001,0.6001,1.7000,0.0000,0.8000,0.0000]
        }
        chain_pose_baselink = {
            "leg": [0.0596,-0.0000,1.0327,0.5000,0.5003,0.4997,0.5000],
            "head": [0.0599,0.0002,1.4098,-0.7072,0.0037,0.0037,0.7069],
            "left_arm": [0.1267,0.2342,0.7356,0.0220,0.0127,0.0343,0.9991],
            "right_arm": [0.1267,-0.2345,0.7358,-0.0225,0.0126,-0.0343,0.9991]
        }
        whole_body_joint = [
            num for key in ["leg", "head", "left_arm", "right_arm"]
            for num in chain_joints[key]
        ]
        base_state = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]
        custom_param = gm.Parameter()

        # Scene 1: Multi-path Point Planning in Cartesian Space (PoseState Target)
        try:
            # Construct target pose
            target_pose_state = gm.PoseState()
            target_pose_state.chain_name = "left_arm"

            # Construct waypoints (3 intermediate poses)
            waypoint_poses = [
                [0.1267,0.2342,0.7356,0.0220,0.0127,0.0343,0.9991],
                [0.2267,0.2342,0.7356,0.0220,0.0127,0.0343,0.9991],
                [0.3267,0.2342,0.7356,0.0220,0.0127,0.0343,0.9991],
                [0.4267,0.2342,0.7356,0.0220,0.0127,0.0343,0.9991],
            ]

            status, traj = motion.motion_plan_multi_waypoints(
                target=target_pose_state,
                waypoint_poses=waypoint_poses,
                enable_collision_check=False,
                params=custom_param
            )
            time.sleep(1)
            printStatus(status)
            if status == gm.MotionStatus.SUCCESS:
                if traj != {}:
                    print(f"✅ Multi-path Point Planning in Cartesian Space (PoseState Target) Success: trajectory points={len(traj[target_pose_state.chain_name])}")
                else:
                    print(f"⚠️ Multi-path Point Planning in Cartesian Space (PoseState Target) Success: trajectory is empty, possibly already at target; check whether the target matches current state or is within tolerance")
            else:
                print(f"❌ Multi-path Point Planning in Cartesian Space (PoseState Target) Failed: {status}")
                status = robot.stop_trajectory_execution()
                printStatus(status)

        except Exception as e:
            print(f"❌ Multi-path Point Planning in Cartesian Space (PoseState Target) Exception: {e}")

        # Scene 2: Multi-path Point Planning in Joint Space (JointStates Target)
        try:
            # Construct target joint
            target_joint = gm.JointStates()
            target_joint.chain_name = "left_arm"

            # Construct waypoints (3 intermediate joint states)
            waypoints = [
                [0.1267,0.2342,0.7356,0.0220,0.0127,0.0343,0.9991],
                [0.2267,0.4342,0.7356,0.0220,0.0127,0.0343,0.9991],
                [0.3267,0.6342,0.7356,0.0220,0.0127,0.0343,0.9991],
                [0.4267,0.8342,0.7356,0.0220,0.0127,0.0343,0.9991]
            ]

            status, traj = motion.motion_plan_multi_waypoints(
                target=target_joint,
                waypoint_poses=waypoints,
                enable_collision_check=False,
                params=custom_param
            )
            printStatus(status)

            if status == gm.MotionStatus.SUCCESS:
                if traj != {}:
                    print(f"✅ Multi-path Point Planning in Joint Space (JointStates Target) Success: trajectory points={len(traj[target_joint.chain_name])}")
                else:
                    print(f"⚠️ Multi-path Point Planning in Joint Space (JointStates Target) Success: trajectory is empty, possibly already at target; check whether the target matches current state or is within tolerance")
            else:
                print(f"❌ Multi-path Point Planning in Joint Space (JointStates Target) Failed: {status}")
                status = robot.stop_trajectory_execution()
                printStatus(status)
        except Exception as e:
            print(f"❌ Multi-path Point Planning in Joint Space (JointStates Target) Exception: {e}")

        # Clear all obstacles
        motion.clear_obstacle()
        print("✅ Clear all obstacles successfully")
        
        # Check trajectory execution status
        status = robot.check_trajectory_execution_status(chain_joints.keys())
        print(f"✅ Check trajectory execution status: {status}")
        
        printStatus(status)

    except Exception as e:
        print(f"An exception occurred: {e}")
    finally:
        # Actively send SIGINT shutdown signal
        robot.request_shutdown()
        # Wait to enter shutdown state
        robot.wait_for_shutdown()
        # Release SDK resources
        robot.destroy()
        print('Resource release successful')

if __name__ == "__main__":
    main()