# QuickStart — 复制粘贴即用

> 在 **Orin 真机** `galbot-echo` 上操作。路径固定，直接复制到终端执行。

```bash
cd ~/Documents/PhotoMate-Moonbot-Hackthon
```

---

## 一次性依赖（灵巧手 CAN 控制）

```bash
pip3 install python-can PyYAML
python3 -c "import can; print('python-can OK')"
```

---

## 灵巧手 Linker Hand O6 · 左手 · PEAK PCAN → can0

### 拉起 CAN（重启后或 can0 DOWN 时执行）

```bash
sudo ip link set can0 up type can bitrate 1000000
ip -br link show can0
```

### 扫描确认设备

```bash
cd ~/Documents/PhotoMate-Moonbot-Hackthon/vendor/linkerhand-python-sdk
./find_linker_hand.sh
```

期望：串码 `LHO6-...`，CAN ID `028`（左手）。

### 手势指令（6 个数：拇指弯, 拇指摆, 食指, 中指, 无名指, 小指）

**伸出食指（壹）**

```bash
cd ~/Documents/PhotoMate-Moonbot-Hackthon/vendor/linkerhand-python-sdk
python3 example/L10/get_status/get_set_state.py \
  --hand_joint O6 \
  --hand_type left \
  --position 125 18 255 0 0 0
```

**点赞（大拇哥）**

```bash
python3 example/L10/get_status/get_set_state.py \
  --hand_joint O6 \
  --hand_type left \
  --position 250 79 0 0 0 0
```

**张开**

```bash
python3 example/L10/get_status/get_set_state.py \
  --hand_joint O6 \
  --hand_type left \
  --position 250 250 250 250 250 250
```

**握拳**

```bash
python3 example/L10/get_status/get_set_state.py \
  --hand_joint O6 \
  --hand_type left \
  --position 102 18 0 0 0 0
```

> SSH 远程用上面命令行即可。**GUI**（`gui_control.py`）需要本机显示器或 ToDesk 桌面，纯 SSH 看不到界面，一般不必装 PyQt5。

---

## Xbox 手柄遥控底盘

### 启动

```bash
cd ~/Documents/PhotoMate-Moonbot-Hackthon
./scripts/run_xbox_teleop.sh
```

慢速试机：

```bash
./scripts/run_xbox_teleop.sh --safe
```

带避障：

```bash
./scripts/run_xbox_teleop.sh --mode nav
```

正常速度（默认，不慢速）：

```bash
cd ~/Documents/PhotoMate-Moonbot-Hackthon
./scripts/run_xbox_teleop.sh
```
默认大约：前后 0.5 m/s，转向 1.0 rad/s。

想再快一点：

```bash
cd ~/Documents/PhotoMate-Moonbot-Hackthon
./scripts/run_xbox_teleop.sh --max-vx 0.8 --max-yaw 1.2
```

### 停止

在运行 teleop 的终端 `Ctrl+C`，或：

```bash
pkill -f 'xbox_teleop.py|run_xbox_teleop.sh'
```

---

## PhotoMate Dashboard（Web）

### Mock 演示（不连真机）

```bash
cd ~/Documents/PhotoMate-Moonbot-Hackthon
PHOTOMATE_MOCK=true ./scripts/run_dashboard.sh
```

浏览器：`http://<本机IP>:8000`

### 真机（改 config/app.yaml → robot.mock: false 后）

```bash
cd ~/Documents/PhotoMate-Moonbot-Hackthon
PHOTOMATE_MOCK=false ./scripts/run_dashboard.sh
```

---

## GalbotSDK 环境（手动跑 SDK 示例时）

```bash
cd ~/Documents/PhotoMate-Moonbot-Hackthon
source vendor/GalbotSDK/galbot_sdk/linux-aarch64-gcc940/setup.sh
```
