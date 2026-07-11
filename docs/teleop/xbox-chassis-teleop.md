# Xbox 手柄遥控 Galbot G1 底盘

> 2026-07-11 在真机 `galbot-echo`（Orin HPU）上验证：蓝牙 Xbox Wireless Controller + `scripts/run_xbox_teleop.sh`。

## 真机信息

| 项 | 值 |
|----|-----|
| 机型 | **Galbot G1** |
| 主机名 | `galbot-echo` |
| 配置 | `config/app.yaml` → `robot.model: g1` |
| 控制栈 | GalbotSDK（**不用 ROS1/ROS2**） |

G1 底盘控制器常量（与 S1 不同）：

| 模式 | SDK 控制器 | API |
|------|-----------|-----|
| 直接遥控 `direct` | `CHASSIS_TWIST_CTRL` | `GalbotRobot.set_base_velocity()` |
| 带避障 `nav` | `CHASSIS_POSE_CTRL` | `GalbotNavigation.navigate_with_velocity()` |

官方参考示例：

- `vendor/GalbotSDK/examples/g1/python/galbot_robot/set_base_velocity.py`
- `vendor/GalbotSDK/examples/g1/python/galbot_navigation/navigate_with_velocity.py`

---

## 架构（对比 ROS joy）

```
ROS 生态:  joy_node → /joy → teleop_twist_joy → /cmd_vel → 底盘

PhotoMate: Xbox /dev/input/js0 → scripts/xbox_teleop.py → GalbotSDK → 底盘
```

---

## 前置条件

1. 在 **Orin**（`galbot-echo`）上操作，不是开发机 mock
2. `config/app.yaml` 中 `robot.mock: false`
3. 机器人已站立、急停可用、周围无障碍
4. Xbox 手柄连到 **Orin**（蓝牙/USB 只能绑一台机器）

### 连接 Xbox 手柄

1. Orin：**设置 → Bluetooth** → 配对/连接 **Xbox Wireless Controller**
2. 验证：

```bash
ls /dev/input/js*
cat /proc/bus/input/devices | grep -A6 -i xbox
```

应看到类似：

```text
N: Name="Xbox Wireless Controller"
H: Handlers=kbd js0 event12
```

若 `js0` 暂时不存在，先断开手柄再重连，或等几秒后重试 `ls`。

---

## 快速开始

```bash
cd ~/Documents/PhotoMate-Moonbot-Hackthon
./scripts/run_xbox_teleop.sh
```

启动后会打印速度上限与发送频率。操作：

| 输入 | 动作 |
|------|------|
| 左摇杆 | 前后 / 横移 |
| 右摇杆 | 原地转向 |
| `Ctrl+C` | 停车并退出 |

---

## 速度档位

| 场景 | 命令 |
|------|------|
| **正常速度（推荐）** | `./scripts/run_xbox_teleop.sh` |
| **更快一点** | `./scripts/run_xbox_teleop.sh --max-vx 0.8 --max-yaw 1.2` |
| **慢速安全** | `./scripts/run_xbox_teleop.sh --safe` |
| **有障碍 / 赛场** | `./scripts/run_xbox_teleop.sh --mode nav` |

### 默认参数（2026-07-11）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--max-vx` | `0.5` m/s | 摇杆满推前后速度 |
| `--max-vy` | `0.3` m/s | 横移速度 |
| `--max-yaw` | `1.0` rad/s | 转向角速度 |
| `--rate-hz` | `30` | 指令发送频率 |
| `--cmd-duration` | `0`（direct）/ `0.15`（nav） | 每条速度指令持续时间 |
| `--deadzone` | `0.08` | 摇杆死区 |

### 机载限速

满推摇杆时看终端输出的 `vx`：

- 若卡在 **约 0.5–0.7 m/s**，是 **G1 机载/SDK 限速**，不是脚本 bug
- `--max-vx 4` 也不会超过机载上限
- 赛场空旷场地用 **0.5–0.8 m/s** 通常够用

`--safe`（0.15 m/s）适合首次试机或拥挤区域；会感觉明显偏慢，属正常。

---

## 模式说明

### `direct`（默认）

- 调用 `set_base_velocity`
- 响应快，适合空旷场地
- `cmd_duration=0`：持续发速，松杆需靠脚本发零速度停车

### `nav`

- 调用 `navigate_with_velocity`
- 带运行时避障检查
- 适合有地图、有障碍的赛场通道

---

## 方向校正

G1 + Xbox 蓝牙默认 **三轴取反**（前后/横移/转向与摇杆物理方向对齐）。

若某一轴仍反了：

```bash
./scripts/run_xbox_teleop.sh --no-invert-vx    # 仅前后
./scripts/run_xbox_teleop.sh --no-invert-yaw   # 仅转向
```

轴号因手柄型号可能不同，用 `jstest` 确认：

```bash
sudo apt install joystick
jstest /dev/input/js0
```

自定义轴映射：

```bash
./scripts/run_xbox_teleop.sh --axis-vx 1 --axis-vy 0 --axis-yaw 3
```

---

## 常用参数一览

```bash
./scripts/run_xbox_teleop.sh \
  --device auto \          # 自动找 Xbox；也可写 /dev/input/js0
  --model g1 \              # 默认读 config/app.yaml
  --mode direct \           # direct | nav
  --max-vx 0.5 \
  --max-yaw 1.0 \
  --safe \                  # 慢速：0.15 / 0.3
  --no-invert-vx            # 方向微调
```

---

## 故障排查

| 现象 | 处理 |
|------|------|
| `未找到手柄设备` | 在 Orin 蓝牙里连接 Xbox；确认 `ls /dev/input/js*` |
| 手柄连在笔记本上 | 先从笔记本断开，再在 `galbot-echo` 连接 |
| `SWERVE_CHASSIS_POSE_CTRL` 报错 | 旧脚本问题；G1 应使用 `CHASSIS_TWIST_CTRL` / `CHASSIS_POSE_CTRL` |
| 方向全反 | 用默认脚本（已默认取反）；勿加 `--no-invert-*` |
| 很慢 | 不要用 `--safe`；默认或 `--max-vx 0.8` |
| 满推仍只有 ~0.6 m/s | 机载限速，正常 |
| 无 ROS joy | 预期行为；本项目不走 ROS |

---

## 与腿高 / 导航的关系

- 升腿、站立：见 [docs/leg_height/README.md](../leg_height/README.md)
- 到点导航、建图：见 [docs/navigate/README.md](../navigate/README.md)
- 底盘遥控与导航 **不要同时** 抢底盘控制权；遥控前确认无巡逻/导航任务在跑

---

## 文件索引

| 路径 | 作用 |
|------|------|
| `scripts/xbox_teleop.py` | 读 `/dev/input/js0`，映射速度，调 GalbotSDK |
| `scripts/run_xbox_teleop.sh` | source `vendor/GalbotSDK/.../setup.sh` 后启动 |
| `config/app.yaml` | `robot.model`、`hostname`、`mock` |
