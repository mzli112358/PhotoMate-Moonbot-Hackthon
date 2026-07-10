# Web Dashboard 与应用层架构

本文回答：执行层之上用什么做应用？网页放哪台机器？Dashboard 上的地图和机器人位置怎么显示？和 FastAPI、ROS 的关系是什么？

---

## 分层架构（推荐）

```
┌─────────────────────────────────────────────────────────┐
│  展示层：Web Dashboard / Portal（用户手机/平板浏览器）      │
│  React / Vue + Canvas / Three.js 地图可视化               │
└───────────────────────────┬─────────────────────────────┘
                            │ HTTP REST + WebSocket
┌───────────────────────────▼─────────────────────────────┐
│  应用层：PhotoMate Backend（FastAPI）                     │
│  - 任务状态机（idle / navigate / shoot / return）         │
│  - 航点管理、排队、风格配置                               │
│  - WebSocket 推送机器人位姿、任务进度                      │
│  - （可选）Agent 对话 / 语音引导                          │
└───────────────────────────┬─────────────────────────────┘
                            │ Python import / 同进程或本地 RPC
┌───────────────────────────▼─────────────────────────────┐
│  执行层：GalbotSDK                                        │
│  GalbotNavigation / GalbotRobot / 相机 / 机械臂           │
└───────────────────────────┬─────────────────────────────┘
                            │ 机载 IPC / 私有服务
┌───────────────────────────▼─────────────────────────────┐
│  平台层：Galbot 机载服务（非 ROS）                         │
│  localization_server / service_navigation_plan / ...      │
└─────────────────────────────────────────────────────────┘
```

### 各层职责

| 层 | 技术选型 | 职责 |
|----|----------|------|
| 展示层 | `webs/` 前端项目 | Dashboard、地图、机器人图标、任务按钮、照片预览 |
| 应用层 | **FastAPI** + WebSocket | API、状态机、与 SDK 桥接、向浏览器推实时数据 |
| 执行层 | **GalbotSDK** | 导航、感知、机械臂——直接调官方 Python API |
| 平台层 | Galbot 机载二进制服务 | 建图、定位、规划——不由 PhotoMate 实现 |

**和 Agent 的关系**：黑客松阶段可先用硬编码状态机 + 简单语音；对话引导、多轮交互可作为 FastAPI 里的 service 模块，或独立进程通过 HTTP 调用，不必和导航绑死。

---

## 服务器放 Jetson 还是台式机？

### 推荐：现场 Demo → Jetson 上跑 Backend + 静态前端

```
用户手机浏览器  ──WiFi/LAN──►  http://<机器人IP>:8000
                                    │
                              Jetson (HPU)
                              ├── FastAPI (PhotoMate)
                              ├── GalbotSDK
                              └── 机载导航/定位服务
```

**优点**

- 延迟低：位姿轮询 `get_current_pose()` 在本机，无跨机网络抖动
- 部署简单：一条 WiFi，用户扫二维码或访问固定 IP 即可
- 与官方示例一致：SDK 本来就要在机器人侧运行

**缺点**

- Jetson 算力有限，重型 AI（大图模型、实时 3D 重建）需裁剪或放云端

### 备选：开发机台式机 + Jetson 分机

```
浏览器 → 台式机 FastAPI → HTTP/gRPC → Jetson 上的 SDK 薄代理
```

适合**多人远程联调**或 Jetson 上只跑 Galbot 服务、应用放服务器。现场活动 Demo 通常不如本机一体化稳。

### 结论

| 场景 | 放哪 |
|------|------|
| 黑客松现场、毕业典礼 | **Jetson（HPU）** 跑 Backend + 提供网页 |
| 日常写代码 | **本机** git 开发，SSH / rsync 部署到 Jetson |
| 重 AI 推理 | 本机或云 GPU，结果通过 API 回 Jetson |

---

## 项目代码放本机还是 Jetson？

**Git 仓库放本机（开发机）**，Jetson 上是**部署目标**。

推荐工作流：

```bash
# 本机：开发、提交
git clone ... PhotoMate-Moonbot-Hackthon
# 编辑 webs/、app/、config/ ...

# 部署到 Jetson（示例）
rsync -avz --exclude .git ./  galbot@<robot-ip>:~/PhotoMate/
ssh galbot@<robot-ip> 'cd ~/PhotoMate && uvicorn app.main:app --host 0.0.0.0 --port 8000'
```

仓库里建议逐步补齐：

```
PhotoMate-Moonbot-Hackthon/
├── app/              # FastAPI 应用（待建）
├── webs/             # 前端 Dashboard（待建）
├── config/
│   └── waypoints.yaml   # 拍照航点（map 坐标系）
└── vendor/GalbotSDK/    # 子模块，Jetson 上 source setup.sh
```

不要在 Jetson 上直接当唯一代码副本；保持本机 Git 为 source of truth。

---

## Dashboard 地图区：显示机器人位置与朝向

### 不是 ROS

浏览器里的地图 **不是 RViz，也不是 ROS2 topic**。

数据链路：

```
localization_server（机载）
        ↓
GalbotNavigation.get_current_pose()  →  [x, y, z, qx, qy, qz, qw]
        ↓
FastAPI 后台线程 / 定时任务（如 5–10 Hz）
        ↓
WebSocket 推送到浏览器  →  { "x": 1.2, "y": 3.4, "yaw": 0.78 }
        ↓
前端 Canvas / SVG / Three.js 画点 + 朝向线
```

### 地图底图从哪来？

| 方案 | 做法 | 复杂度 |
|------|------|--------|
| **A. 2D 俯视图（推荐 MVP）** | 把 `global_cloud_cleaned.pcd` 投影为 PNG（俯视 z 切片），或 CloudCompare 导出正射图 | 低 |
| **B. 点云 Web 渲染** | Three.js + PCD loader 加载点云，机器人图标叠加 | 中 |
| **C. 仅网格 + 坐标** | 不显示真实地图，只画坐标轴和机器人轨迹 | 最低（调试够用） |

黑客松建议 **方案 A**：建图后导出一张俯视 PNG 放到 `webs/public/map.png`，航点和机器人位姿都画在这张图上。

### 朝向「小线」怎么画

从四元数 `[qx, qy, qz, qw]` 算出 yaw（绕 z 轴转角），在 `(x, y)` 画：

- 圆点：机器人位置
- 线段：`(x, y)` → `(x + L·cos(yaw), y + L·sin(yaw))`，长度 `L` 如 0.3 m 按屏幕比例缩放

伪代码：

```python
import math

def yaw_from_quat(qx, qy, qz, qw):
    siny_cosp = 2 * (qw * qz + qx * qy)
    cosy_cosp = 1 - 2 * (qy * qy + qz * qz)
    return math.atan2(siny_cosp, cosy_cosp)
```

前端收到 WebSocket 消息后更新 marker，不要用轮询整页刷新。

### FastAPI 最小骨架（示意）

```python
# app/main.py（示意，非完整实现）
from fastapi import FastAPI, WebSocket
from galbot_sdk.g1 import GalbotNavigation  # 按实际机型 G1/S1

app = FastAPI()
nav = GalbotNavigation()
nav.init()

@app.websocket("/ws/pose")
async def pose_stream(ws: WebSocket):
    await ws.accept()
    while True:
        pose = nav.get_current_pose()  # [x,y,z,qx,qy,qz,qw]
        await ws.send_json({"pose": pose, "localized": nav.is_localized()})
        await asyncio.sleep(0.2)
```

静态前端由 FastAPI `StaticFiles` 挂载 `webs/dist`，或开发时用 Vite proxy。

---

## 和草案文档的对应关系

结合 `docs/plan/AI草案整理1.md`、`AI草案整理2.md` 中的会场拍照流程：

1. **建图**（本节）→ 会场 PCD 地图 + 拍照航点
2. **导航**（`galbot-navigation-overview.md`）→ 机器人巡航到合影区
3. **应用层**（本节）→ Dashboard 选 spot、看机器人移动、触发拍照任务
4. **执行层**（后续文档）→ 接手机、构图、点快门

导航是地基；Dashboard 是运营界面；两者通过 FastAPI + WebSocket 连接，**全程不需要 ROS**。
