# PhotoMate Moonbot Hackathon

PhotoMate 黑客松总项目仓库。

## S1–S6 拍照 Agent（软件链）

本分支新增本地电脑可运行的显式 asyncio 状态机：S1 意图检测 → S2 询问 → S3 interval 姿态引导 → S4 拍照与质检 → S5 复核 → S6 照片链接交付。Omni 负责自然交互和工具调用，本地编排层负责状态、计时、重试与资源释放。

```bash
# 开发依赖
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# 全量自动化测试
python -m pytest -q

# 无硬件、无密钥的完整 mock 链
python -m app.photo_agent.cli --mode mock

# 先独立验证设备与 Omni，再跑真实本地链
python scripts/photo_agent/device_smoke.py --camera 0
export DASHSCOPE_API_KEY='从安全环境注入，勿写入仓库'
python scripts/photo_agent/omni_smoke.py --microphone 1
python -m app.photo_agent.cli --mode local-real
```

分模块验收：

```bash
python manual/photo_agent/run_state.py --state S1 --mode mock
python manual/photo_agent/run_state.py --state S3 --mode local-real
```

可视化测试台（只接受本机访问）：

```bash
export DASHSCOPE_API_KEY='从安全环境注入，勿写入仓库'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

浏览器打开 `http://127.0.0.1:8000/photo-agent`。页面可逐个启动 S1–S6 真实测试、查看摄像头/状态/质检/日志，并编辑全部 System、State 和 Action Prompt。Prompt 保存到 `config/photo_agent_prompts.yaml`，重启保留；运行中保存会从下一轮 Omni 对话生效。

详细范围、配置、API 契约、手动验收、逐项完成审计与已知限制见 [docs/photo_agent/README.md](docs/photo_agent/README.md)。真实 Insta360、Jetson、GalbotSDK 与前端二维码 UI 尚未接入；V0 使用普通电脑摄像头、麦克风、扬声器和本地文件服务。

## 仓库结构

```
PhotoMate-Moonbot-Hackthon/
├── vendor/                 # 平台核心依赖（机器人 SDK）
│   └── GalbotSDK/
├── ros/                    # 预留（导航走 Galbot 机载服务，不用 ROS2 SLAM）
├── third_party/            # 其他开源第三方库
│   ├── cap-x/
│   └── generative_agents/
├── models/                 # AI / 重建模型
│   └── lingbot-map/
├── app/                    # FastAPI 应用（导航 API + WebSocket）
├── webs/                   # Dashboard 静态前端
├── config/                 # app.yaml、waypoints.yaml
├── data/maps/              # 可选 floor_plan.png
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

### Dashboard（Jetson 或开发机）

```bash
# 安装依赖（首次）
pip install -r requirements.txt

# 启动（默认 mock 演示；真机改 config/app.yaml → robot.mock: false）
./scripts/run_dashboard.sh
```

浏览器打开 `http://<本机IP>:8000`（指挥台）或 `http://<本机IP>:8000/docs`（嘉宾文档）。API 调试页在 `/api/swagger`。

### GalbotSDK

```bash
cd vendor/GalbotSDK
source galbot_sdk/linux-x86_64-gcc940/setup.sh
```

导航说明见 [docs/navigate/](./docs/navigate/README.md)（建图 / 定位 / SDK API，不依赖 ROS2）。

赛程与全栈执行计划见 [docs/schedule/](./docs/schedule/README.md)（计划书全部模块，7/11 傍晚前搞定）。

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
