# 逐小时冲刺计划（7/6 18:10 – 7/8 10:15）

> **口径**：计划书全栈，不砍功能。  
> **方法**：VIBE coding —— 多开 Cursor 会话并行（导航 / Agent / 机械 / PPT 调研各一条）。  
> **原则**：能写代码的今晚写；必须真机的标红，8 号 10:15 后按 checklist 秒开。

---

## 一、今晚到底要搞定什么？（7/6 21:00 回家后）

| 模块 | 今晚目标 | 8 号才测的 |
|------|----------|------------|
| **M1 导航** | 到点 + 多航点巡航 + Dashboard API **代码写完** | 建图、定位、`mock:false` 真走 |
| **M6 Agent** | `task_fsm.py` 状态机骨架 + 接导航回调 | 真机串 shoot |
| **M7 感知（发现用户）** | `perception.py` 规则引擎骨架 + mock | 头摄 RGB 真检人 |
| **M2 夹具** | 法兰尺寸查清 + CAD v0.1 + **发打印** | 安装、试夹 |
| **M3 灵巧手** | 读文档、列 API 清单 | 点屏 |
| **M4 Insta360** | 确认 Link 2C = UVC，列 `v4l2` 探测命令 | USB 取流 |
| **PPT** | 架构页大纲（见 `ppt-outline.md`） | 现场素材、录屏 |

**今晚导航模块要「代码搞定」**，不是「真机跑通」。Galbot SDK 封装严，你 8 号主要调：建图 → 定位 → `mock:false` → 点网页航点。

---

## 二、动态避障 —— 要不要自己写？

**不用自己写局部规划。** 文档依据：

- `service_navigation_plan`：全局路径 + **局部避障** + 底盘控制（见 `docs/navigate/galbot-navigation-overview.md`）
- `navigate_to_goal(..., enable_collision_check=True)` 已默认开碰撞检测
- `navigation_through_waypoints(..., enable_collision_check=True)` 同上

你要做的是：

1. 建图时点云覆盖活动区（墙、桌腿、展台）
2. 可选：`engine_tools` 转 `map_topo.osm` 画**电子围栏**（禁止进区）
3. 监控任务状态：`COLLISION` / `CLOSE_TO_OBSTACLE` / `OCCUPIED` → Agent 转 `failed` 或重试

**真机要调的**：速度 `WaypointParams.velocity_scale`、到达阈值、急停恢复 —— 不是重写避障算法。

---

## 三、你的 PCD vs 银河 PCD —— 能伪造成银河的吗？

### 3.1 两套用途，别混

| 用途 | 你的 Livox/FAST-LIO PCD | 银河 `global_cloud_cleaned.pcd` |
|------|-------------------------|----------------------------------|
| **Dashboard 地图展示** | ✅ 已在用 `data/maps/global_cloud.pcd` | ✅ 9 日建图后替换 |
| **Galbot 定位 `localization_server`** | ❌ **不能**当伪银河图用 | ✅ 必须 `mapping_server` 产出 |
| **航点坐标 `waypoints.yaml`** | ❌ 坐标系不对 | ✅ 建图后现场打点 |

文档依据：`docs/navigate/map-format-and-prerequisites.md` —— 定位读 `/var/maps/cur/global_cloud_cleaned.pcd`，由机载 `mapping_server` 生成。

### 3.2 为什么不能「编辑成伪银河 PCD」去导航？

1. **坐标系原点不同**：FAST-LIO 的 map 原点 ≠ Galbot 建图 map 原点；航点 `[x,y,z,q...]` 会整体偏。
2. **定位是点云匹配**：`localization_server` 拿实时雷达去匹配**那张图**；换源点云 → 分数上不去（<0.75）。
3. **字段可简化，语义不能换**：你现有 PCD 是 `x y z intensity normal_* curvature`；展示可投影 2D；给 Galbot 定位仍须赛场建图那份。

### 3.3 今晚可以对 PCD 做的事

- ✅ 继续用现有 PCD 调 Dashboard 显示、mock 下假机器人走位
- ✅ 写脚本 `scripts/strip_pcd_xyz.py`：只留 `x y z` 减小体积（仅展示用）
- ❌ 不要指望伪 PCD 让 8 号跳过建图

**8 号上午**：有往届 `/var/maps/cur` 可先借用看网页；**9 日上午必须自己建图**。

---

## 四、场内巡航怎么实现？（今晚写代码）

**实现路径**（已写入 `app/robot.py` + API）：

```
config/waypoints.yaml  photo_spots 有序列表
        ↓
POST /api/navigation/patrol/start  { "loop": true }
        ↓
真机: GalbotNavigation.navigate_through_waypoints(waypoints)
      或循环 navigate_to_goal（到最后一站再回 spot_home）
Mock: 按序插值假走位
        ↓
WebSocket /ws/pose  +  Dashboard 蓝点移动
        ↓
到航点 → task_fsm 收到 on_arrived → 可进 greet / 等人
```

SDK 示例：`vendor/GalbotSDK/examples/s1/python/galbot_navigation/navigation_through_waypoints.py`

**巡航时发现用户**（感知层，今晚写骨架）：

| 信号 | 技术（优先级） | 今晚 | 9 日真机 |
|------|----------------|------|----------|
| 有人靠近 | 头摄 RGB + 人体框（MediaPipe/YOLO） | mock 随机 | `get_camera_data` 取流 |
| 驻足 >3s | 同一人 bbox 中心位移 < 阈值，计时 | 代码写好 | 调阈值 |
| 举手/招手 | 骨架关键点手腕高于肩 | 可选，第二优先级 | 同上 |
| 网页发起 | Dashboard 按钮「我要拍照」 | ✅ 今晚可做 | 演示备用 |
| 语音 | 现场嘈杂，**不作为 9 日主链路** | 只列 TODO | 路演加分 |

**状态机衔接**：

```
patrol ──(发现用户)──► greet ──(用户确认)──► navigate(合影点) ──► shoot ──► deliver ──► patrol
```

---

## 五、哪些几乎不用调？哪些要真机调？

### 封装好、写好就能用（8 号验证即可）

- `GalbotNavigation.init()` / `navigate_to_goal` / `navigate_through_waypoints`
- `enable_collision_check=True` 避障
- `check_path_reachability` / `check_goal_arrival`
- Dashboard FastAPI + WebSocket（mock 已通）

### 必须真机调（每次 15–60 分钟级）

| 项 | 现象 | 处理 |
|----|------|------|
| 定位分数低 | `is_localized()` false | 挪到建图起点，`relocalize` / `engine_tools` 发初始位姿 |
| 路径不可达 | `check_path_reachability` false | 航点改坐标或清障碍 |
| 到点偏差大 | 拍照构图歪 | 调 `WaypointParams` 到达阈值 |
| 夹具干涉 | 臂撞机身 | 改关节角预设 |
| 点屏偏 | 快门没点上 | 示教坐标 + 视觉二次修正 |

---

## 六、7/6 逐小时（假设 21:00 到家）

| 时间 | 做什么 | 产出 / 完成标志 |
|------|--------|-----------------|
| **21:00–21:20** | 本地起服务：`./scripts/run_dashboard.sh`，确认 `/` 和 `/docs` | 两个 URL 截图发队友 |
| **21:20–21:50** | **Galbot 文档**：`vendor/GalbotSDK/docs/s1/zh/` 或 g1；重点 Routine Operations 建图、example3 导航、example2 臂控 | 笔记：`docs/schedule/notes-galbot-7月6.md`（自己建） |
| **21:50–22:20** | **法兰**：example `get_link_names.py` → 找 `left_arm_end_effector_mount_link`；搜 URDF/机械图（文档教程 example2）；量夹具安装面 | CAD 草图尺寸表（孔距、直径） |
| **22:20–23:10** | **CAD v0.1**：Fusion/FreeCAD —— 法兰转接件 + 弹簧夹固定面；导出 STL | `hardware/phone_mount_v0.1.stl` |
| **23:10–23:20** | **发打印**：自己打印机切片 → 开始打（一夜） | 明早取件 |
| **23:20–00:20** | **Cursor 会话 A**：拉代码最新；测 `POST /api/navigation/go`；加巡航 API（若未合入） | `patrol` API mock 通 |
| **00:20–00:50** | **Cursor 会话 B**：`task_fsm.py` + `POST /api/task/start` | 状态能在 `/api/task/status` 看到 |
| **00:50–01:10** | **Cursor 会话 C**：`perception.py` mock + 「我要拍照」按钮（可选） | FSM 能从 patrol→greet |
| **01:10–01:20** | `git push` / U 盘备份；行李装袋核对 checklist-7月6 | 能睡觉 |
| **01:20** | **睡觉** | — |

### 睡觉期间（手机 / 另一台电脑交给 AI）

开 **独立会话**，不依赖你在线：

| 任务 | 工具建议 | 产出 |
|------|----------|------|
| PPT 12 页骨架 | Cursor / Kimi / GPT | `docs/schedule/ppt-outline.md` 填内容 |
| Insta360 Link 2C Linux UVC | 网页搜 + SDK 页 | `docs/schedule/notes-insta360.md` |
| 灵心巧手 SDK 入口 | 搜文档 | `docs/schedule/notes-dexhand.md` |
| 农大打印店 / 合影板 | 你明早发消息，AI 先写好话术 | 见下文 7/7 |

**不要通宵画图** —— 22:30 前 CAD 定稿发打印即可；后面时间给代码。

---

## 七、7/7 逐小时

| 时间 | 做什么 | 产出 |
|------|--------|------|
| **06:00–06:15** | 取 3D 打印件；试装弹簧夹（桌面假法兰） | 知道 v0.2 要改啥 |
| **06:15–08:30** | **Agent 深化**：`task_fsm` 接 `shoot_phone` / `shoot_camera` 分支；`config/app.yaml` 加 `patrol`、`perception` 段 | 本地 mock 跑通 idle→patrol→greet→navigate |
| **08:30–09:00** | 洗漱早餐；**农大打印店**微信：合影板 60×90cm ×2，7/8 下午前能否取 | 订单号 / 到店时间 |
| **09:00–12:00** | 行李最终装；打印件进箱；**PPT** 按 outline 做 1–6 页 | pptx 前半 |
| **12:00–13:00** | 午饭；去机场交通 | — |
| **13:00–15:00** | 机场值机；**无网前**把仓库 `git push` | 云端有最新代码 |
| **15:00–起飞** | 机场：背 demo 话术；改 PPT 7–9 页 | — |
| **飞行中** | **离线 PPT** 10–12 页 + 路演台词默念 | 完整 pptx 初稿 |
| **落地–酒店** | 打车；酒店 WiFi 下 `git pull`；看 AI 写的调研笔记 | — |
| **酒店 1–1.5h** | **Cursor**：Insta360 `scripts/probe_cameras.sh`；打印机驱动调研记笔记 | 脚本进仓库 |
| **23:00 前** | 睡觉；设 7/8 06:00 闹钟 | — |

---

## 八、7/8 逐小时（10:00 拿机器）

| 时间 | 做什么 | 产出 |
|------|--------|------|
| **06:00–07:00** | 洗漱；检查行李（夹具、打印机、Insta360、网线） | — |
| **07:00–08:00** | 去赛场交通；联系队友分工 | — |
| **08:00–09:30** | 到场踩点（若允许）：场地形状、插座、WiFi 密码 | 纸质草图 |
| **09:30–10:00** | 领机器人；记 Jetson IP；连 WiFi/热点 | SSH 通 |
| **10:00–10:15** | 硬件快装：夹具、USB 相机、手 | 线束不挡雷达 |
| **10:15–10:30** | **快速启动**（见下「10:15 启动清单」） | Dashboard 手机可开 |
| **10:30–12:00** | `mock:false`；探测 Galbot 服务；**不建图** | SDK init 成功 |
| **下午** | 场地侦察；合影板到货；mock 网页给队友看 | 见 checklist-7月8日 |
| **晚上** | 早睡；**9 日 07:00 建图** | — |

### 10:15 启动清单（15 分钟复制粘贴）

```bash
cd PhotoMate-Moonbot-Hackthon
git pull
git submodule update --init --recursive
pip install -r requirements.txt
source vendor/GalbotSDK/galbot_sdk/linux-aarch64-gcc940/setup.sh
# 先 mock:true 确认网页
./scripts/run_dashboard.sh
# 手机浏览器：http://<IP>:8000  和  /docs
# 再改 config/app.yaml mock:false，重启，看 /api/robot/status
```

---

## 九、影石 Insta360 —— 今晚要下 SDK 吗？

**Link 2C 优先走 UVC，不必今晚下全量 SDK。**

1. Linux 上：`lsusb` → `v4l2-ctl --list-devices` → OpenCV `VideoCapture(0)`
2. Galbot 头摄也可用 `get_camera_data.py` 做构图预览
3. **Insta360 官方 SDK**：若要做机内防抖/专用协议再下；**9 日阻塞再搞**

今晚只写：`docs/schedule/notes-insta360.md` + `scripts/probe_cameras.sh`

---

## 十、法兰 / CAD 搜索清单（21:50 那档）

1. 本地：`vendor/GalbotSDK/docs/s1/zh/tutorials/` → example2 臂操作 → `left_arm_end_effector_mount_link`
2. `get_link_names(only_end_effector=True)` —— **8 号真机**跑一遍最准
3. 计划书：`docs/plan/AI草案整理1.md`「手腕法兰、3D打印转接件」
4. 若没有公开 STEP：用卡尺量现成夹具安装孔 → 做 **长圆孔** 滑槽吸收误差
5. CAD 导出 STL → 切片 → 打印 **8–10h** → 7/7 早上取

---

## 十一、多 Cursor 会话并行建议

| 会话 | 分支/目录 | 今晚任务 |
|------|-----------|----------|
| **A 导航** | `app/robot.py`, `app/main.py` | 巡航 API、航点循环 |
| **B Agent** | `app/task_fsm.py`, `app/perception.py` | 状态机 + 发现用户 |
| **C 硬件** | `hardware/`, `docs/schedule/notes-*.md` | CAD 尺寸、打印参数 |
| **D 文案** | `docs/schedule/ppt-outline.md` | PPT 页级文案 |

合并前：`git pull`；冲突主要在 `app/main.py`，约定 **A 先合、B 后合**。

---

## 十二、相关文件

| 文件 | 作用 |
|------|------|
| [full-scope.md](./full-scope.md) | M1–M7 模块定义 |
| [checklist-7月6日-出发前.md](./checklist-7月6日-出发前.md) | 今晚行李与代码 |
| [checklist-7月8日-上机.md](./checklist-7月8日-上机.md) | 8 日细节 |
| [ppt-outline.md](./ppt-outline.md) | 路演 PPT 逐页 |
| [glossary.md](./glossary.md) | 嘉宾 docs 等名词 |
