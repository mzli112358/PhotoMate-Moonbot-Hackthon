from galbot_sdk.s1 import Parameter, create_parameter

# Create Parameter via constructor and set options
p = Parameter()
p.set_blocking(True)            # Set whether to block execution
p.set_check_collision(False)     # Disable collision detection
p.set_timeout(5.0)              # Set timeout (seconds)
p.set_actuate('with_chain_only')# Set drive mode
p.set_tool_pose(False)           # Whether to consider tool pose
p.set_reference_frame('base_link')

print('--- Parameter p ---')
print('blocking:', p.get_blocking())
print('collision check:', p.get_check_collision())
print('timeout:', p.get_timeout(), 's')

# Or use factory function to quickly create Parameter
p2 = create_parameter(direct_execute=False, blocking=True, timeout=3.0, actuate='with_chain_only', tool_pose=False, check_collision=True)
print('Factory-created timeout:', p2.get_timeout())
