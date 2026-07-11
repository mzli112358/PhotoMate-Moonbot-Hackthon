# PhotoMate 部署文档（机器人现场部署）

面向：在机器人（Linux / Jetson，或 macOS 调试机）上部署 PhotoMate 拍照 Agent 前后端的同学。

---

## 1. 架构概览

```
┌────────────────────┐        /api、/ws 代理         ┌──────────────────────────┐
│  前端 (Vite/React)  │  ───────────────────────────▶ │  后端 (FastAPI, 端口 8000) │
│  端口 8080 /flow/   │                                │  PhotoAgent 状态机 S1-S6   │
└────────────────────┘                                │  相机 / 麦克风 / 扬声器      │
        ▲  浏览器(kiosk)                               │  Qwen-Omni 实时语音         │
        │                                              │  Supabase 上传 + 二维码      │
        └──────────────────────────────────────────────┘
```

- **后端**：FastAPI（`app/main.py`），端口 `8000`。驱动 S1(寻人)→S2(询问/选设备模式)→S3(取景拍照)→S5(复核)→S6(交付分享) 的状态机，并通过 SSE 把状态推给前端。
- **前端**：React + Vite（`frontend/`），dev 端口 `8080`，`base=/flow/`，把 `/api` 与 `/ws` 代理到后端 `8000`。
- **同机部署（推荐）**：前后端跑在同一台机器（机器人本机），浏览器以 kiosk 方式打开 `http://127.0.0.1:8080/flow/`。
- **调试台（可选）**：`http://127.0.0.1:8000/photo-agent` — 单状态隔离测试，**现场演示请用 `/flow/` 完整流程**。

---

## 2. 前置依赖

| 类别 | 要求 |
| --- | --- |
| Python | 3.11（建议用独立 venv） |
| Node.js | 18+（跑前端 Vite） |
| 系统库 | `portaudio`（PyAudio 依赖）、OpenCV 运行库 |
| 硬件 | USB/CSI 摄像头（推荐 Insta360 Link 2，自带固件级人脸追踪）、麦克风、扬声器 |
| 网络 | 能访问阿里云百炼（DashScope）与 Supabase 的公网 |

系统库安装示例：

```bash
# Debian/Ubuntu/Jetson
sudo apt-get update && sudo apt-get install -y portaudio19-dev libgl1 libglib2.0-0

# macOS
brew install portaudio
```

> **Jetson 注意**：`requirements.txt` 中的 `pywebrtc-audio`（WebRTC AEC 回声消除）在部分 Jetson 上可能没有预编译 wheel。若 `pip install` 失败，可先跳过该包——程序会自动降级为半双工 mic 门控；长期方案是从源码编译 `webrtc-audio-processing` 后再安装。详见下文「音频与回声消除」。

---

## 3. 拉取代码

当前功能分支：`feat/photo-agent-s1-s6`（PR: [mzli112358/PhotoMate-Moonbot-Hackthon#1](https://github.com/mzli112358/PhotoMate-Moonbot-Hackthon/pull/1)）

```bash
git clone https://github.com/TheNight-Watch/PhotoMate-Moonbot-Hackthon.git
cd PhotoMate-Moonbot-Hackthon
git checkout feat/photo-agent-s1-s6
git pull
```

> 若从主仓库 `mzli112358/PhotoMate-Moonbot-Hackthon` 拉取，请确认该分支已合并。

---

## 4. 后端部署

### 4.1 安装依赖

```bash
python3.11 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4.2 放置 `.env`（密钥，重点）

`.env` 已被 `.gitignore` 忽略，**不会随仓库分发**，需要单独获取后放到**项目根目录**（与 `app/`、`requirements.txt` 同级）。应用启动时由 `app/config.py` 的 `load_dotenv()` 自动加载。

`.env` 至少包含以下变量（**真实值请通过安全渠道向项目负责人索取，切勿提交到仓库或走公开聊天**）：

```ini
# 阿里云百炼 Qwen-Omni 实时语音 API Key
DASHSCOPE_API_KEY='sk-ws-xxxxxxxx'

# Supabase 对象存储（照片上传 + 生成可扫码下载公链）
SUPABASE_URL='https://xxxxxxxx.supabase.co'
SUPABASE_BUCKET='media'
# 服务端上传必须用 secret key（sb_secret_... ），能绕过 RLS；publishable/anon key 会 403
SUPABASE_SERVICE_KEY='sb_secret_xxxxxxxx'
```

> DashScope 的 workspace host / 模型名 / voice 都有内置默认值（见 `app/photo_agent/config.py` 与 `config/app.yaml`），一般无需在 `.env` 里配置。
>
> 若 Supabase 未配置或密钥无写权限，系统会**自动回退**到本地链接 `/api/photos/{id}`（仅同网可访问），二维码仍能生成。此时需把 `PHOTOMATE_PHOTO_AGENT__BASE_URL` 设为机器人局域网 IP（见 §8）。

### 4.3 部署前自检（推荐）

在启动完整服务前，先确认硬件与 API 可用：

```bash
source .venv/bin/activate

# 1) 相机 / 麦克风 / 扬声器
python scripts/photo_agent/device_smoke.py
# 输出 JSON 中 camera/microphone/speaker 均为 ok:true

# 2) DashScope Omni 连通性（需要 .env 里的 DASHSCOPE_API_KEY）
PHOTOMATE_PHOTO_AGENT__MODE=local-real \
  python scripts/photo_agent/omni_smoke.py
# 最终 ok: true

# 3)（可选）AEC 回声消除效果
python scripts/photo_agent/aec_e2e.py
# ERLE > 15 dB 为合格；加 --disable-aec 可对比基线
```

### 4.4 启动后端

```bash
source .venv/bin/activate
cd /path/to/PhotoMate-Moonbot-Hackthon   # 项目根目录

# 关键：用 local-real 模式（默认是 mock，不会真正调用硬件/语音）
unset PHOTOMATE_PHOTO_AGENT__MICROPHONE_INDEX PHOTOMATE_PHOTO_AGENT__SPEAKER_INDEX
PHOTOMATE_PHOTO_AGENT__MODE=local-real \
  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- `--host 0.0.0.0`：允许局域网访问（手机扫本地回退链接时需要；用 Supabase 公链则不强制）。
- `unset ...`：清掉可能残留的固定音频索引，让程序**自动选择**设备（输出优先耳机、输入优先内置麦克风），避免设备选错导致 500。
- 看到 `Application startup complete` 即启动成功。
- 启动后日志/设备信息里会显示 `aec` 模式：`aec`（WebRTC 回声消除已启用）或 `gate`（降级为半双工门控）。

---

## 5. 前端部署

```bash
cd frontend
npm install
npm run dev        # Vite dev server，端口 8080，代理 /api、/ws 到 8000
```

浏览器（机器人屏幕的 kiosk 浏览器）打开：

```
http://127.0.0.1:8080/flow/
```

右下角会出现 **「开始会话」** 按钮——**必须点击**才会启动 S1→S6 完整循环；后端不会自动开始。

> **无屏幕 / 纯 SSH 部署（Jetson）**：见下文 **§5.1 远程操作**——可用命令行启动会话，或用笔记本 SSH 端口转发/局域网访问前端。

> **生产说明**：当前 FastAPI **未挂载** `webs/flow` 静态目录，现场演示请保持 `npm run dev` 运行。若需纯后端单进程部署，需先 `npm run build` 并在 `app/main.py` 增加 `/flow/` 静态挂载（尚未实现）。

### 5.1 远程操作（SSH + 笔记本）

Jetson 无本地屏幕时，有两种常用方式：

#### 方式 A：命令行启动（不需要看前端）

后端 `uvicorn` 跑起来后，**「开始会话」等价于一条 HTTP 请求**：

```bash
# 在 Jetson 上（或 SSH 远程执行）
chmod +x scripts/photo_agent/session_cli.sh
./scripts/photo_agent/session_cli.sh start

# 查看当前状态（state=S1/S2/...，active=true 表示会话在跑）
./scripts/photo_agent/session_cli.sh status

# 结束会话
./scripts/photo_agent/session_cli.sh stop
```

从**笔记本**一条命令启动（把 `jetson` 换成你的 SSH 主机名/IP）：

```bash
ssh jetson 'cd PhotoMate-Moonbot-Hackthon && ./scripts/photo_agent/session_cli.sh start'
```

等价的 raw curl：

```bash
curl -X POST http://127.0.0.1:8000/api/photo-agent/session/start \
  -H "Content-Type: application/json" -d '{}'
```

可选指定设备索引：

```bash
curl -X POST http://127.0.0.1:8000/api/photo-agent/session/start \
  -H "Content-Type: application/json" \
  -d '{"camera_index":0,"microphone_index":1,"speaker_index":2}'
```

#### 方式 B：在笔记本浏览器看实时前端

前后端都在 Jetson 上跑，笔记本和 Jetson 在同一局域网（或 SSH 可达）。

**B1 — SSH 端口转发（推荐，不改配置）**

在**笔记本**上开一条 SSH，把 Jetson 的前端端口转过来（Vite 会把 `/api` 代理到 Jetson 本机 8000，所以**只转发 8080 即可**）：

```bash
ssh -L 8080:127.0.0.1:8080 user@<Jetson局域网IP>
```

保持该终端不关，笔记本浏览器打开：

```
http://127.0.0.1:8080/flow/
```

即可看到与 Jetson 上相同的实时界面（寻人画面、状态切页、复核照片、二维码等）。可以点「开始会话」，也可以用上面的 CLI 启动。

**B2 — 局域网直连（Jetson 监听所有网卡）**

Jetson 上前端用 LAN 模式启动：

```bash
cd frontend
npm run dev:lan    # 等价于 vite dev --host 0.0.0.0
```

笔记本浏览器打开（把 IP 换成 Jetson 的实际地址）：

```
http://<Jetson局域网IP>:8080/flow/
```

> 若笔记本访问不了 8080，检查 Jetson 防火墙：`sudo ufw allow 8080/tcp`（如启用了 ufw）。

**实时预览（仅画面，无 UI）**

即使不看前端，也可在笔记本上看相机 MJPEG 流（需能访问 Jetson 8000 端口，或再转发 `-L 8000:127.0.0.1:8000`）：

```
http://127.0.0.1:8000/api/photo-agent/session/preview.mjpg
```

会话状态 JSON：

```
http://127.0.0.1:8000/api/photo-agent/session/state
```

---

## 6. 快速启动（两个终端）

**终端 1 — 后端：**

```bash
cd /path/to/PhotoMate-Moonbot-Hackthon
source .venv/bin/activate
unset PHOTOMATE_PHOTO_AGENT__MICROPHONE_INDEX PHOTOMATE_PHOTO_AGENT__SPEAKER_INDEX
PHOTOMATE_PHOTO_AGENT__MODE=local-real \
  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**终端 2 — 前端：**

```bash
cd /path/to/PhotoMate-Moonbot-Hackthon/frontend
npm run dev
```

**浏览器：** `http://127.0.0.1:8080/flow/` → 点「开始会话」。

---

## 7. 端到端流程验收

后端与前端都启动后，打开 `/flow/`，点「开始会话」，按状态机走完整流程：

1. **寻人页 `/search`**（S1/S2）：实时画面 + 语音「欢迎来到探月黑客松…需要拍照吗」。用户拒绝 → 回到寻人循环。
2. 用户接受 → 语音问 **手机 / Insta360** → 选 Insta → 语音问 **一键拍照 / 录像** → 选拍照。
3. **取景页 `/preview`**（S3）：实时画面 + 姿态引导（默认引导到打卡立牌旁），随后自动拍照。
4. **复核页 `/review`**（S5）：显示刚拍的照片；语音说「文件获取」保存 / 「再来一张」重拍。
5. **分享页 `/post`**（S6）：显示真实二维码 + 下载链接，手机扫码即可下载。
6. 分享页停留约 **60 秒** 后自动重启，进入下一轮寻人循环。

语音提示词可在 `config/photo_agent_prompts.yaml` 中调整（探月黑客松场景已预置）。

---

## 8. 机器人现场配置

`config/app.yaml` 中 `photo_agent` 段可按机器人硬件覆盖（或通过环境变量）：

| 配置项 | 机器人建议 | 说明 |
| --- | --- | --- |
| `camera_index` | `0` | USB 摄像头索引；多摄像头时用 `device_smoke.py` 确认 |
| `camera_rotation_deg` | Linux 上通常 `0` | macOS + Insta360 Link 2 开发机用 `270`；画面方向不对时调整 |
| `microphone_index` / `speaker_index` | `auto` | 留空自动选择；固定索引易出错 |
| `base_url` | `http://<机器人局域网IP>:8000` | 仅 Supabase 未生效、走本地回退链接时需要 |
| `guidance_interval_s` | `5` 或 `8` | S3 姿态评估间隔（秒） |
| `skip_quality_check` | `true` | 演示默认跳过 OpenCV 质检 |

环境变量前缀均为 `PHOTOMATE_PHOTO_AGENT__`，例如：

```bash
export PHOTOMATE_PHOTO_AGENT__CAMERA_ROTATION_DEG=0
export PHOTOMATE_PHOTO_AGENT__BASE_URL='http://192.168.1.100:8000'
```

---

## 9. 音频与回声消除（AEC）

机器人现场常见问题是：**扬声器播放 Omni 语音 → 麦克风再次收音 → VAD 误判为用户说话**，导致自问自答或流程乱跳。

优先级：

1. **首选**：外接耳机/定向扬声器，物理隔离回声（最稳）。
2. **次选**：启用内置 WebRTC AEC（默认开启）。启动后设备信息中 `aec: aec` 表示生效；`aec: gate` 表示 AEC 库不可用，已降级为播放时静音 mic。
3. **Jetson 无 wheel 时**：可设 `PHOTOMATE_PHOTO_AGENT__AEC_ENABLED=0` 并配合耳机使用。

| 变量 | 作用 | 默认 |
| --- | --- | --- |
| `PHOTOMATE_PHOTO_AGENT__AEC_ENABLED` | 是否启用 AEC | `true` |
| `PHOTOMATE_PHOTO_AGENT__AEC_GATE_FALLBACK` | AEC 不可用时是否半双工门控 | `true` |
| `PHOTOMATE_PHOTO_AGENT__AEC_STREAM_DELAY_MS` | 播放→收音延迟补偿（ms） | `120` |

---

## 10.（可选）Insta360 云台/追踪服务

Insta360 Link 2 自带**固件级人脸追踪**，无需项目内的 CV 追踪。若要用云台控制：

```bash
cd InstaSDK/insta360-link2-sdk-标准UVC
INSTA_PTZ_PORT=8788 python -u ptz_server.py
# 控制台 UI: http://127.0.0.1:8788
```

---

## 11.（可选）开机自启

现场 kiosk 可用 systemd 管理两个服务。示例（路径按实际修改）：

`/etc/systemd/system/photomate-backend.service`：

```ini
[Unit]
Description=PhotoMate Backend
After=network.target

[Service]
Type=simple
User=robot
WorkingDirectory=/home/robot/PhotoMate-Moonbot-Hackthon
Environment=PHOTOMATE_PHOTO_AGENT__MODE=local-real
ExecStart=/home/robot/PhotoMate-Moonbot-Hackthon/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/photomate-frontend.service`：

```ini
[Unit]
Description=PhotoMate Frontend (Vite)
After=photomate-backend.service

[Service]
Type=simple
User=robot
WorkingDirectory=/home/robot/PhotoMate-Moonbot-Hackthon/frontend
ExecStart=/usr/bin/npm run dev
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now photomate-backend photomate-frontend
```

浏览器 kiosk 可配置为开机打开 `http://127.0.0.1:8080/flow/`（Chromium `--kiosk` 等，按机器人 OS 文档操作）。

---

## 12. 环境变量参考

| 变量 | 作用 | 默认 |
| --- | --- | --- |
| `DASHSCOPE_API_KEY` | Qwen-Omni 实时语音密钥（必填） | 无 |
| `SUPABASE_URL` / `SUPABASE_BUCKET` / `SUPABASE_SERVICE_KEY` | 照片上传对象存储 | 未配置则本地回退 |
| `PHOTOMATE_PHOTO_AGENT__MODE` | 运行模式：`local-real` 真实 / `mock` 模拟 | `mock` |
| `PHOTOMATE_PHOTO_AGENT__CAMERA_INDEX` | 摄像头索引 | `0` |
| `PHOTOMATE_PHOTO_AGENT__MICROPHONE_INDEX` | 麦克风索引（留空=自动） | 自动 |
| `PHOTOMATE_PHOTO_AGENT__SPEAKER_INDEX` | 扬声器索引（留空=自动） | 自动 |
| `PHOTOMATE_PHOTO_AGENT__CAMERA_ROTATION_DEG` | 画面旋转角度 | `0`（开发机 macOS 可能为 `270`） |
| `PHOTOMATE_PHOTO_AGENT__BASE_URL` | 本地回退链接基址 | `http://127.0.0.1:8000` |
| `PHOTOMATE_PHOTO_AGENT__GUIDANCE_INTERVAL_S` | S3 评估间隔（秒） | `5` |
| `PHOTOMATE_PHOTO_AGENT__SKIP_QUALITY_CHECK` | 跳过拍后 OpenCV 质检 | `true` |
| `PHOTOMATE_PHOTO_AGENT__AEC_ENABLED` | WebRTC 回声消除 | `true` |
| `PHOTOMATE_PHOTO_AGENT__AEC_GATE_FALLBACK` | AEC 降级半双工 | `true` |
| `PHOTOMATE_PHOTO_AGENT__AEC_STREAM_DELAY_MS` | AEC 延迟补偿 | `120` |

---

## 13. 常见问题排查

- **`omni_recoverable_error`（日志 WARNING）**：良性、自愈。仅在「append image before append audio」协议顺序问题时出现，会自动 `prime_audio()` 修复，不影响会话，无需处理。
- **Omni WebSocket handshake failed**：`DASHSCOPE_API_KEY` 缺失/过期/workspace 不匹配。确认 `.env` 已放到项目根目录且 key 有效；不要在 shell 里 export 一个旧的同名变量覆盖它。
- **没有声音 / 设备不可用（500 / channel 错误）**：多为音频设备选错。用 `unset ... MICROPHONE_INDEX SPEAKER_INDEX` 让其自动选择；仍不行时用 `device_smoke.py` 列出设备后手动指定索引。
- **VAD 自问自答 / 流程乱跳**：扬声器回声被 mic 再次收音。优先换耳机；或确认日志中 `aec: aec`；Jetson 上 AEC 不可用时设 `AEC_ENABLED=0` 并必须用耳机。
- **S5 说「再来一张」没反应**：已修复（进入 S5 时会重新启用 Omni tools）。请确认部署的是最新 `feat/photo-agent-s1-s6` 分支。
- **S3 话术重复或太长**：已优化滚动历史去重 + 短句 prompt；更新代码后重启后端即可加载新 prompt。
- **端口被占用**：`lsof -ti :8000 :8080 | xargs kill -9` 清理后重启。
- **前端能开但无数据/不切页**：确认后端 8000 已起、已点「开始会话」、`/flow/` 是通过 8080（有 `/api` 代理）访问。
- **二维码指向 `127.0.0.1`**：说明该照片走了本地回退（Supabase 未生效）。检查 `.env` 的 Supabase 三项；或设置 `PHOTOMATE_PHOTO_AGENT__BASE_URL` 为机器人局域网 IP。

---

## 14. 安全须知

- `.env` 内含明文密钥（DashScope、Supabase secret key），**务必走安全渠道传递**，不要提交到仓库、不要贴到公开聊天。
- Supabase `sb_secret_...` 拥有存储完整写权限；一旦泄露，请到 Supabase 控制台 **重置密钥**，DashScope key 同理到百炼控制台重置。
- 小米打印机接入为**预留占位**，待官方 API 文档后再实现。
