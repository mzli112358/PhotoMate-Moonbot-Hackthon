# Galbot 导航能力概览

PhotoMate 项目的到点导航**不依赖**本仓库中的 ROS2 包（`FAST_LIO`、`livox_ros_driver2`）。银河通用在机器人 HPU（上位机，如 Jetson）上提供完整的地图引擎 + 定位 + 路径规划闭环，应用层通过 **GalbotSDK** 的 `GalbotNavigation` 接口调用。

官方文档路径：`vendor/GalbotSDK/docs/s1/zh/`（本地可 `python3 -m http.server 8000` 后浏览器打开）。

---

## 一、银河通用提供了什么导航？

分三层理解：

### 1. 机载后台服务（在机器人 HPU 上跑）

| 服务 | 路径 | 作用 |
|------|------|------|
| 雷达采集 | `/data/galbot/bin/service_livox_capture` | Livox 雷达点云 |
| 建图 | `/data/galbot/bin/mapping_server` | SLAM 建图，生成点云地图 |
| 定位 | `/data/galbot/bin/localization_server` | 在已有地图上实时定位 |
| 导航规划 | `/data/galbot/bin/service_navigation_plan` | 全局路径规划 + 局部避障 + 底盘控制 |
| 地图工具 | `/data/galbot/bin/engine_tools` | 保存地图、发初始位姿、点云转 OSM 等 |

地图存在 `/var/maps/`，定位默认读 `/var/maps/cur`。

### 2. SDK 接口：`GalbotNavigation`（应用代码里调用的）

文档头文件和示例里提供的主要 API：

| API | 用途 |
|-----|------|
| `init()` | 初始化导航子系统（加载地图、启动定位模块、准备规划器） |
| `relocalize(init_pose)` | 重定位，给初始位姿 |
| `is_localized()` | 是否已成功定位 |
| `get_current_pose()` | 当前在地图坐标系下的位姿 |
| `navigate_to_goal()` | 到点导航（核心），支持避障、阻塞/非阻塞 |
| `navigate_to_goal_v2()` | v2 版到点导航，可调速度上限 |
| `navigate_through_waypoints()` | 多航点顺序导航 |
| `navigate_along_trajectory()` | 沿轨迹导航 |
| `set_navigation_target()` | 动态目标（跟踪/遥控类） |
| `move_straight_to()` | 相对里程计短距离移动，**不需要地图定位** |
| `navigate_with_velocity()` | 速度指令导航 |
| `check_path_reachability()` | 检查起点到终点是否有路 |
| `check_goal_arrival()` | 是否到达目标 |
| `stop_navigation()` | 停止当前导航 |

位姿格式统一为 `[x, y, z, qx, qy, qz, qw]`，在 **map 坐标系**下（单位：米、四元数）。

### 3. 与 ROS / Nav2 的关系

| 对比项 | Galbot 官方导航 | ROS Nav2 生态 |
|--------|----------------|---------------|
| 建图 | `mapping_server` → PCD 点云 | slam_toolbox / cartographer 等 |
| 定位 | `localization_server` | AMCL 等 |
| 规划 | `service_navigation_plan`（PNS） | Nav2 planner + controller |
| 应用调用 | `GalbotNavigation` Python/C++ SDK | ROS2 topic / action |
| PhotoMate 是否使用 | **是** | **否**（已移除相关子模块） |

Galbot 内部通信可能兼容 ROS 风格的消息格式（如 PointCloud2），但**应用开发不需要启动 ROS2、不需要 Nav2**。

---

## 二、到点导航前提（简要）

完整操作见 [map-format-and-prerequisites.md](./map-format-and-prerequisites.md)。

```
雷达服务 → 建图 → 保存 PCD → /var/maps/cur → 定位分数 > 0.75 → service_navigation_plan 已加载 → SDK navigate_to_goal
```

最小代码路径参考：`vendor/GalbotSDK/examples/s1/python/galbot_navigation/complete_example.py`。
