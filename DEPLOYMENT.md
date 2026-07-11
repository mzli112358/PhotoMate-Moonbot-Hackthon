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

---

## 3. 拉取代码

仓库分支：`feat/photo-agent-s1-s6`

```bash
git clone https://github.com/TheNight-Watch/PhotoMate-Moonbot-Hackthon.git
cd PhotoMate-Moonbot-Hackthon
git checkout feat/photo-agent-s1-s6
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
> 若 Supabase 未配置或密钥无写权限，系统会**自动回退**到本地链接 `/api/photos/{id}`（仅同网可访问），二维码仍能生成。

### 4.3 启动后端

```bash
# 关键：用 local-real 模式（默认是 mock，不会真正调用硬件/语音）
unset PHOTOMATE_PHOTO_AGENT__MICROPHONE_INDEX PHOTOMATE_PHOTO_AGENT__SPEAKER_INDEX
PHOTOMATE_PHOTO_AGENT__MODE=local-real \
  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- `--host 0.0.0.0`：允许局域网访问（手机扫本地回退链接时需要；用 Supabase 公链则不强制）。
- `unset ...`：清掉可能残留的固定音频索引，让程序**自动选择**设备（输出优先耳机、输入优先内置麦克风），避免设备选错导致 500。
- 看到 `Application startup complete` 即启动成功。

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

> 生产可选：`npm run build` 会输出到 `../webs/flow`；当前 FastAPI 未挂载该静态目录，现场演示直接用上面的 `npm run dev` 最稳妥。

---

## 6. 端到端流程验收

后端与前端都启动后，打开 `/flow/`，点「开始会话」，按状态机走完整流程：

1. **寻人页 `/search`**（S1/S2）：实时画面 + 语音「需要拍照吗」。用户拒绝 → 回到寻人循环。
2. 用户接受 → 语音问 **手机 / Insta360** → 选 Insta → 语音问 **一键拍照 / 录像** → 选拍照。
3. **取景页 `/preview`**（S3）：实时画面 + 姿态引导，随后自动拍照。
4. **复核页 `/review`**（S5）：显示刚拍的照片；语音说「文件获取」保存 / 「再来一张」重拍。
5. **分享页 `/post`**（S6）：显示真实二维码 + 下载链接，手机扫码即可下载。
6. 分享页停留约 **60 秒** 后自动重启，进入下一轮寻人循环。

---

## 7.（可选）Insta360 云台/追踪服务

Insta360 Link 2 自带**固件级人脸追踪**，无需项目内的 CV 追踪。若要用云台控制：

```bash
cd InstaSDK/insta360-link2-sdk-标准UVC
INSTA_PTZ_PORT=8788 python -u ptz_server.py
# 控制台 UI: http://127.0.0.1:8788
```

---

## 8. 环境变量参考

| 变量 | 作用 | 默认 |
| --- | --- | --- |
| `DASHSCOPE_API_KEY` | Qwen-Omni 实时语音密钥（必填） | 无 |
| `SUPABASE_URL` / `SUPABASE_BUCKET` / `SUPABASE_SERVICE_KEY` | 照片上传对象存储 | 未配置则本地回退 |
| `PHOTOMATE_PHOTO_AGENT__MODE` | 运行模式：`local-real` 真实 / `mock` 模拟 | `mock` |
| `PHOTOMATE_PHOTO_AGENT__CAMERA_INDEX` | 摄像头索引（自动选择失败时手动指定） | `0` |
| `PHOTOMATE_PHOTO_AGENT__MICROPHONE_INDEX` | 麦克风索引（留空=自动） | 自动 |
| `PHOTOMATE_PHOTO_AGENT__SPEAKER_INDEX` | 扬声器索引（留空=自动） | 自动 |
| `PHOTOMATE_PHOTO_AGENT__CAMERA_ROTATION_DEG` | 画面旋转角度 | `0` |
| `PHOTOMATE_PHOTO_AGENT__BASE_URL` | 本地回退链接使用的基址（手机扫码时改成机器人局域网 IP） | `http://127.0.0.1:8000` |

---

## 9. 常见问题排查

- **`omni_recoverable_error`（日志 WARNING）**：良性、自愈。仅在「append image before append audio」这一协议顺序问题时出现，会自动 `prime_audio()` 修复，不影响会话，无需处理。
- **Omni WebSocket handshake failed**：`DASHSCOPE_API_KEY` 缺失/过期/workspace 不匹配。确认 `.env` 已放到项目根目录且 key 有效；不要在 shell 里 export 一个旧的同名变量覆盖它。
- **没有声音 / 设备不可用（500 / channel 错误）**：多为音频设备选错。用上面的 `unset ... MICROPHONE_INDEX SPEAKER_INDEX` 让其自动选择；仍不行时用 `PHOTOMATE_PHOTO_AGENT__MICROPHONE_INDEX/SPEAKER_INDEX` 手动指定正确索引。
- **端口被占用**：`lsof -ti :8000 :8080 | xargs kill -9` 清理后重启。
- **前端能开但无数据/不切页**：确认后端 8000 已起、`/flow/` 是通过 8080（有 `/api` 代理）访问，而不是直接开静态文件。
- **二维码指向 `127.0.0.1`**：说明该照片走了本地回退（Supabase 未生效）。检查 `.env` 的 Supabase 三项；用公链时二维码是 `https://<supabase>/storage/v1/object/public/media/...`，公网可扫。

---

## 10. 安全须知

- `.env` 内含明文密钥（DashScope、Supabase secret key），**务必走安全渠道传递**，不要提交到仓库、不要贴到公开聊天。
- Supabase `sb_secret_...` 拥有存储完整写权限；一旦泄露，请到 Supabase 控制台 **重置密钥**，DashScope key 同理到百炼控制台重置。
- 小米打印机接入为**预留占位**，待官方 API 文档后再实现。
