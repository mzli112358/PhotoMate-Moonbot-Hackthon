# 地图格式与建图前提

在调用 `navigate_to_goal()` 之前，必须先在机器人 HPU 上完成建图和定位。本节说明「地图文件到底是什么」。

---

## 地图是什么类型？3D 点云？2D？Nav2？

**结论：主地图是 3D 点云（PCD），不是 Nav2，也不是典型的 ROS `nav_msgs/OccupancyGrid` 栅格地图。**

### 核心文件（必选）

| 文件 | 格式 | 说明 |
|------|------|------|
| `global_cloud.pcd` | **3D 点云**（PCD） | 建图原始输出 |
| `global_cloud_cleaned.pcd` | **3D 点云**（PCD） | 擦除空中杂点后的版本；**定位服务实际使用此文件** |

存放路径示例：

```
/var/maps/room1102/
├── global_cloud.pcd
├── global_cloud_cleaned.pcd   ← 定位读这个
└── ...
```

启用定位时，将整个地图目录放到 **`/var/maps/cur`**（把 `room1102` 重命名为 `cur` 即可）。

### 辅助文件（可选）

| 文件 | 格式 | 说明 |
|------|------|------|
| `map_topo.osm` | **OSM 拓扑地图** | 由 `engine_tools` 从点云转换；用于在 JOSM 里画**电子围栏**（禁止进入区域） |
| 其他内部配置 | Galbot 私有 | PNS 规划器、融合服务等在机载侧读取，应用层通常不直接编辑 |

### 不是什么

- **不是 Nav2**：没有 `map.yaml` + `map.pgm` 那套标准 2D 占据栅格作为主地图。
- **不主要是 2D 地图**：虽然底盘规划在水平面工作（本质上是 2D 导航），但定位和建图的**数据源是 3D LiDAR 点云**，不是预先扫好的平面 occupancy grid。
- **不需要你手写 FAST-LIO**：建图由机载 `mapping_server` 完成，与仓库里已删除的 ROS 包无关。

### 数据流理解

```
Livox 雷达点云
    ↓
mapping_server（SLAM 建图）
    ↓
global_cloud.pcd → 清理杂点 → global_cloud_cleaned.pcd
    ↓
localization_server（点云匹配定位，输出 map 系位姿）
    ↓
service_navigation_plan（在已知地图上路径规划 + 避障）
    ↓
GalbotNavigation.navigate_to_goal()（SDK）
```

规划器在内部会把 3D 环境信息投影/抽取为可规划的平面障碍物表示，但**你作为应用开发者只需要关心 map 坐标系下的 `[x,y,z,qx,qy,qz,qw]`**。

---

## 建图流程 checklist（在 HPU 上操作）

以下命令均在机器人 HPU 终端执行（参见 `vendor/GalbotSDK/docs/s1/zh/routine_operations/`）。

### 1. 前置

- [ ] `service_livox_capture` 雷达进程在运行
- [ ] `/var/maps/` 目录存在且可写
- [ ] 急停松开，用 S1 遥控器控制底盘

### 2. 建图

```bash
/data/galbot/bin/mapping_server
```

遥控器慢速绕场一周，观察关键帧数量增加。

### 3. 保存

```bash
/data/galbot/bin/engine_tools
# 输入 1 → 保存地图，默认路径如 /var/maps/room1102
```

确保目录内有 `global_cloud_cleaned.pcd`（未擦杂点则 `cp global_cloud.pcd global_cloud_cleaned.pcd`）。

### 4. 定位

```bash
# 将 room1102 重命名为 cur，放到 /var/maps/cur
/data/galbot/bin/localization_server
tail -f /userdata/log/localization_server/localization_server.INFO
```

- [ ] 定位分数 **> 0.75**
- [ ] 位姿正常发布
- 分数低：机器人挪到建图起点，`engine_tools` 输入 `2` 发初始位姿

### 5. 导航

- [ ] `service_navigation_plan` 已加载（工作模式可能默认开启）
- [ ] SDK 侧 `nav.init()` 成功，`nav.is_localized()` 为 true
- [ ] 切换底盘控制器 `SWERVE_CHASSIS_POSE_CTRL`（见官方示例）
- [ ] 调用 `navigate_to_goal(goal_pose, ...)`

---

## PhotoMate 拍照点与地图的关系

建图完成后，可以在 map 坐标系下记录多个**拍照航点**（位置 + 朝向），例如毕业典礼现场的 A/B/C 三个合影区：

```python
photo_spots = [
    {"name": "spot_a", "pose": [2.0, 1.5, 0.0, 0, 0, 0.707, 0.707]},
    {"name": "spot_b", "pose": [5.0, -1.0, 0.0, 0, 0, 1.0, 0.0]},
]
```

这些坐标来自建图后的 map 系，与 Nav2 waypoint 概念类似，但通过 `GalbotNavigation.navigate_through_waypoints()` 或循环 `navigate_to_goal()` 调用。
