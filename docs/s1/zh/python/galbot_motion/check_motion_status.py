from galbot_sdk.s1 import MotionStatus, check_motion_status

status_str = check_motion_status(MotionStatus.SUCCESS)
print('MotionStatus string:', status_str)