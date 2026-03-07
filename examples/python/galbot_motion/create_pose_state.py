from galbot_sdk.g1 import create_joint_state, create_pose_state, JointStates, PoseState, Pose

# 使用工厂函数创建辅助对象
js = create_joint_state()
ps = create_pose_state()

# 填充示例字段
js.chain_name = 'left_arm'
js.joint_positions = [0.0] * 7

ps.chain_name = 'left_arm'
# 7 维向量: x, y, z, qx, qy, qz, qw
ps.pose = Pose([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0])

print(type(js), js.chain_name)
print(type(ps), ps.chain_name)