# G1 腿部高度调整（真机备忘）

> 2026-07-09 在赛场真机 `galbot-echo`（Orin HPU）上验证通过。

## 机器分工（先搞清楚控谁）

| 机器 | IP | 用户 | 作用 |
|------|-----|------|------|
| **Orin / Jetson HPU**（上位机） | `172.16.23.137` | `galbot` | **调腿高、导航、GalbotSDK、PhotoMate** — 开发/调试主要连这台 |
| **XCU**（下位机） | `172.16.23.196` | `root` | 底盘底层实时控制，一般**不直接** SSH 上去调腿高 |

腿部高度通过 **GalbotSDK → 机载运控服务**（`service_motion_plan`、`robot_state_publish`、`singorix_wbcs_main` 等）下发，这些服务跑在 **Orin** 上。

---

## 已验证成功的升腿指令（G1）

### 背景

升腿前读取到的 leg 关节（单位 rad）：

```text
[0.041, 0.136, 0.095, -0.003, -0.002]   # 蹲低/未站立
```

关节名：`leg_joint1` … `leg_joint5`（共 5 个）。

### 成功命令（第三条脚本）

```python
import time
from galbot_sdk.g1 import GalbotRobot, ControlStatus

r = GalbotRobot()
r.init()
time.sleep(3)

leg_std = [0.5, 1.5, 1.0, 0.0, 0.0]   # G1 标准站立姿态
st = r.set_joint_positions(leg_std, ["leg"], [], True, 0.1, 20.0)
print(st)   # ControlStatus.SUCCESS

r.request_shutdown()
r.wait_for_shutdown()
r.destroy()
```

**结论**：把 leg 设到 `[0.5, 1.5, 1.0, 0.0, 0.0]` 成功让机器人站起来。该值与 SDK 官方 `installation_welcome_verify.py` 中的 `_K_PRESET_LEG` 一致。

### 失败命令（第二条脚本，勿照搬）

```python
cur = r.get_joint_positions(["leg"], [])[0]   # ❌ 错：这是单个 float，不是 5 元组
leg_up = list(cur)                            # TypeError: 'float' object is not iterable
```

**正确读法**：

```python
cur_list = r.get_joint_positions(["leg"], [])
print(cur_list)                    # 外层 list
# 若返回 [[j1,j2,j3,j4,j5]]，则 joints = cur_list[0]
# 若返回 [j1,j2,j3,j4,j5]，则 joints = cur_list
```

---

## 常用姿态参考（G1，rad）

| 名称 | leg 五关节 | 说明 |
|------|------------|------|
| 标准站立 | `[0.5, 1.5, 1.0, 0.0, 0.0]` | 官方预设，已验证 |
| 偏低 | `[0.25, 1.1, 0.85, 0.0, 0.0]` | `whole_body_reset` 示例 |
| 微调升高 | 在**当前值**基础上 `joint2 += 0.05`、`joint3 += 0.05` | 小步试探，勿一次跳太大 |

参数建议：

- `speed_rad_s = 0.1`（慢）
- `timeout_s = 20.0`
- `is_block = True`（阻塞等到位）

---

## 在 Orin 上执行（一键复制）

```bash
ssh galbot@172.16.23.137

python3 <<'PY'
import time
from galbot_sdk.g1 import GalbotRobot, ControlStatus

r = GalbotRobot()
assert r.init(), "init 失败"
time.sleep(3)

print("升前:", r.get_joint_positions(["leg"], []))
leg_std = [0.5, 1.5, 1.0, 0.0, 0.0]
st = r.set_joint_positions(leg_std, ["leg"], [], True, 0.1, 20.0)
print("结果:", st.name if hasattr(st, "name") else st)
print("升后:", r.get_joint_positions(["leg"], []))

r.request_shutdown(); r.wait_for_shutdown(); r.destroy()
PY
```

### 安全前提

1. 急停已松开  
2. 周围无障碍物  
3. `service_motion_plan`、`robot_state_publish` 等服务在跑（`ls /data/galbot/bin/` 可见）

---

## 相关 SDK 文件

- `vendor/GalbotSDK/examples/g1/python/galbot_robot/installation_welcome_verify.py` — `_K_PRESET_LEG`
- `vendor/GalbotSDK/examples/g1/python/galbot_robot/set_joint_positions.py` — 关节控制模板
- `vendor/GalbotSDK/examples/g1/python/galbot_robot/whole_body_reset_zero_map_example.py` — 偏低 leg 示例

---

## 本机 vs Jetson：一定要 SSH 吗？

### 核心事实

**GalbotSDK 必须在与机载服务同一侧运行**（即 Orin/Jetson 上）。  
SDK 通过本机 IPC 连接 `/data/galbot/bin/` 里的运控、导航服务，**不能**在你 x86 开发机上直接 `import galbot_sdk` 就遥控真机（x86 版 SDK 是仿真/离线开发用，且连不上机载 embosa 总线）。

所以：

| 方式 | 是否可行 | 说明 |
|------|----------|------|
| SSH 进 Orin 跑 Python | ✅ 最简单 | 你现在的做法；本机键盘 → SSH 会话 → Orin 执行 |
| `ssh -t galbot@IP 'python3 ...'` | ✅ | 不交互登录，一条命令远程执行 |
| rsync 代码到 Orin，在 Orin 上跑脚本/服务 | ✅ 推荐长期方案 | 本机开发，Jetson 部署执行 |
| 本机浏览器访问 Jetson 上的 PhotoMate API | ✅ 不必 SSH | FastAPI 跑在 Orin，`mock: false` 时由应用层调 SDK |
| 本机直接 import galbot_sdk 控真机 | ❌ | 架构上不通 |

### 三台「角色」分工

```
┌─────────────────────┐         WiFi/网线          ┌──────────────────────┐
│  你的 x86 开发机      │  ──SSH / HTTP / rsync──►  │  Orin (172.16.23.137) │
│  (4090 PC)          │                           │  GalbotSDK + 机载服务  │
│                     │                           │  PhotoMate 部署目标    │
│  · Git 仓库主副本    │                           └──────────┬───────────┘
│  · 写代码/文档       │                                      │ 机载总线
│  · mock 演示         │                           ┌──────────▼───────────┐
│  · 重 AI 推理(可选)  │                           │  XCU (172.16.23.196)  │
└─────────────────────┘                           │  底盘底层              │
                                                  └──────────────────────┘
```

| 资产 | 放哪 | 作用 |
|------|------|------|
| **Git 仓库**（PhotoMate-Moonbot-Hackthon） | **本机 x86** 为主 | 版本管理、开发、文档、子模块；source of truth |
| **部署副本** | **Orin** `~/PhotoMate/` 等 | `rsync` / `git pull` 后现场跑 Dashboard、调 SDK |
| **GalbotSDK 子模块** | 两边都可有 | 本机 x86_64 读文档/离线；**真机必须 aarch64 + 机载服务** |
| **机载二进制服务** | Orin `/data/galbot/bin/` | 厂商预装，不由本仓库提供 |

### 项目文件夹到底干什么？

**不是「只能放 Jetson」**，而是：

1. **本机**：写 `app/`、`webs/`、`docs/`、`config/`，`mock: true` 本地调试 UI 和状态机  
2. **Jetson**：同步同一份代码，`mock: false`，真机执行  
3. 最终用户（嘉宾手机）访问的是 **`http://<Orin-IP>:8000`**，不是访问你 4090

更完整的分层说明见：[web-dashboard-architecture.md](../navigate/web-dashboard-architecture.md)。

### 不想每次 SSH 的替代路径

1. **部署 PhotoMate 到 Orin**，本机浏览器点网页按钮（后续可在 Dashboard 加快捷操作）  
2. **本机一条远程命令**：`ssh galbot@172.16.23.137 'cd ~/PhotoMate && python3 scripts/xxx.py'`  
3. **赛场联调**：Orin 上常驻 `uvicorn app.main:app`，本机只改代码 + rsync

---

## 底盘键盘遥控（补充）

腿高调好后，底盘移动同样要在 **Orin** 侧调用 `set_base_velocity` 或机载 `galbot_sdk_examples`。  
键盘控制需 `ssh -t`（分配伪终端）。详见赛场联调时的口头备忘，或后续补 `docs/leg_height/chassis-keyboard-teleop.md`。
