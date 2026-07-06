# PhotoMate Moonbot Hackathon

PhotoMate 黑客松总项目仓库。

## 仓库结构

```
PhotoMate-Moonbot-Hackthon/
├── vendor/                 # 平台核心依赖（机器人 SDK）
│   └── GalbotSDK/
├── ros/                    # ROS2 相关包
│   ├── livox_ros_driver2/
│   └── FAST_LIO/
├── third_party/            # 其他开源第三方库
│   ├── cap-x/
│   └── generative_agents/
├── models/                 # AI / 重建模型
│   └── lingbot-map/
├── config/                 # 项目配置文件（待添加）
├── data/                   # 数据集、录包、地图等
├── docs/                   # 项目文档
├── scripts/                # 部署与自动化脚本
├── tools/                  # 开发工具
├── webs/                   # Web 前端 / 可视化
├── manual/                 # 操作手册
├── archive/                # 归档文件
├── reserve/                # 预留目录
├── README.md
└── .gitmodules
```

## 子模块一览

| 目录 | 分类 | 来源 | 分支 | 说明 |
|------|------|------|------|------|
| `vendor/GalbotSDK/` | vendor | [mzli112358/PhotoMate-Moonbot-Hackthon](https://github.com/mzli112358/PhotoMate-Moonbot-Hackthon.git) | `5745f32` | Galbot SDK（历史提交，独立 SDK 布局） |
| `ros/livox_ros_driver2/` | ros | [Livox-SDK/livox_ros_driver2](https://github.com/Livox-SDK/livox_ros_driver2.git) | `master` | Livox MID-360 官方 ROS2 驱动 |
| `ros/FAST_LIO/` | ros | [hku-mars/FAST_LIO](https://github.com/hku-mars/FAST_LIO.git) | `ROS2` | FAST-LIO 官方 ROS2 版 |
| `third_party/cap-x/` | third_party | [capgym/cap-x](https://github.com/capgym/cap-x.git) | `main` | CaP-X：Code-as-Policy 机器人操控 |
| `third_party/generative_agents/` | third_party | [joonspk-research/generative_agents](https://github.com/joonspk-research/generative_agents.git) | `main` | 斯坦福 25 人 AI 小镇 |
| `models/lingbot-map/` | models | [Robbyant/lingbot-map](https://github.com/Robbyant/lingbot-map.git) | `main` | LingBot-Map 流式 3D 重建 |

## 克隆与初始化

```bash
git clone --recurse-submodules https://github.com/mzli112358/PhotoMate-Moonbot-Hackthon.git
cd PhotoMate-Moonbot-Hackthon
```

若已克隆但未拉取子模块：

```bash
git submodule update --init --recursive
```

更新所有子模块到各自跟踪分支的最新提交：

```bash
git submodule update --remote --merge
```

## 快速参考

### GalbotSDK

```bash
cd vendor/GalbotSDK
source galbot_sdk/linux-x86_64-gcc940/setup.sh
```

### Livox MID-360

```bash
cd ros/livox_ros_driver2
# ros2 launch livox_ros_driver2 rviz_MID360_launch.py
```

### FAST-LIO (ROS2)

```bash
cd ros/FAST_LIO
# 在 ROS2 workspace 中 colcon build
```

### CaP-X

```bash
cd third_party/cap-x
```

### Generative Agents

```bash
cd third_party/generative_agents
```

### LingBot-Map

```bash
cd models/lingbot-map
```
