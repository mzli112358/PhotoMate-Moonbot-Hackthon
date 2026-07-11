# Photo Agent 开发协作规则

## 项目目标与范围

- 本仓库的照片 Agent V0 目标：在本地电脑跑通 S1–S6，即意图检测、询问、姿态引导、拍照与质检、复核、照片链接交付。
- 软件工程师负责 S1–S6；S0、机器人导航、机械臂与 GalbotSDK 不在本任务内，不修改队友的机器人代码。
- 状态链固定为 `S0 IDLE -> S1 DETECT_INTENT -> S2 ASK_INTENT -> S3 POSE_GUIDANCE -> S5 REVIEW -> S6 DELIVER -> S0`；S3 拍照质检失败与 S5 不满意可回 S3。

## 职责边界

- Omni：看、听、说、理解意图、返回工具调用；不是状态机，也不承担精确计时。
- 编排层：显式状态、SessionContext、超时、interval、重试、转移、资源释放。
- Demo 当前默认跳过拍后质检（`skip_quality_check: true`）；恢复 OpenCV 质检时设为 `false` 或 `PHOTOMATE_PHOTO_AGENT__SKIP_QUALITY_CHECK=0`。
- CameraAdapter：V0 用普通电脑摄像头取流并保存当前帧；Insta360 仅预留适配器。
- DeliveryAdapter/FastAPI：保存照片、稳定 `photo_id`、可访问 `photo_url`；二维码 UI 与下载页由前端负责。
- V0 `mock` 使用 fixture；`local-real` 使用本机摄像头/麦克风/扬声器和真实 Omni；`hardware-real` 只保留配置与接口，不假装已接入 Jetson/Insta360/Galbot。

## 技术与工程约定

- Python 3.10+、asyncio、显式 FSM、FastAPI、OpenCV、WebSocket/DashScope Realtime；不引入 LangGraph 或自主 Agent 主控制器。
- 新软件链位于 `app/photo_agent/`；测试位于 `tests/photo_agent/`；独立 API smoke tests 位于 `scripts/photo_agent/`；手动验收入口位于 `manual/photo_agent/`；产品文档位于 `docs/photo_agent/`。
- `State`、事件与 `SessionContext` 是唯一状态契约。每次用户接待持有一个 Omni 会话；结束时必须取消后台任务、关闭设备和 WebSocket，并完整 reset。
- 外部依赖通过 adapter/Protocol 隔离；真实实现与 mock 使用相同契约。禁止在核心 FSM 中直接调用摄像头、文件服务或 SDK 全局对象。
- 所有配置来自 `config/app.yaml` 与环境变量；设备索引、Host、端口、照片目录、Base URL、模型均可配置，不绑定 macOS。

## API-first 与密钥规则

- 外部 API/SDK/硬件必须先做独立最小验证：枚举或建连 -> 最小读写 -> 错误验证 -> adapter -> 主链。
- Omni smoke test 必须先验证建会话、音频后图像、文本/语音、VAD/Manual、`response.create`、Function Calling、工具结果续答、超时和断线识别，再标记 real 可用。
- 只从 `DASHSCOPE_API_KEY`、`DASHSCOPE_WORKSPACE_ID`、`DASHSCOPE_REGION`、`OMNI_MODEL` 等环境变量读取密钥与连接配置。
- 绝不把 API Key、`.env`、真实照片或运行数据写入 Git、Markdown、测试快照或日志；日志只能显示 key 是否存在。

## 测试与运行规则

- 新功能严格 TDD：先写一个会因缺失行为而失败的测试，确认失败原因，再做最小实现，最后重构并跑全量回归。
- 每个 S1–S6 状态都覆盖正常、转移、超时、异常、重试、调用顺序、资源释放与结构化日志。
- 必须覆盖完整 happy path、S3 质检回环、S5 重拍回环、S6 失败仍复位，以及无任务/句柄/会话泄漏。
- 自动化测试：`python -m pytest -q`。
- mock 完整链：`python -m app.photo_agent.cli --mode mock`。
- local-real：`python -m app.photo_agent.cli --mode local-real`；运行前先执行独立设备与 Omni smoke tests。
- 分状态手动测试：`python manual/photo_agent/run_state.py --state S1 --mode mock`（替换 S1–S6；real 需显式选择）。
- 启动必须输出分支/commit、运行模式、状态、模型、API Host、key 是否存在、设备、照片目录/Base URL、adapter real/mock 与缺失依赖；不得输出密钥。

## Git 与协作边界

- 当前开发分支为 `feat/photo-agent-s1-s6`；上游 `origin` 只读使用，不强推。
- 不初始化或递归更新 `vendor/GalbotSDK` 等无关子模块，不修改机器人团队负责的导航/机械臂代码。
- 只提交本任务范围文件。完成后本地提交，推送到个人 fork，再向上游发 PR。
- 若工作区出现非本任务的队友改动，保留并绕开；无法绕开时停止并说明冲突。

## 排障与记录

- 先复现并区分本地代码、SDK、网络、权限、设备或第三方服务；复杂问题优先查官方文档/SDK/错误码，再查匹配版本的公开 issue，最后做单变量实验。
- 解决复杂问题后在 `docs/photo_agent/troubleshooting.md` 记录现象、根因、证据链接、修复、回归测试与限制。
- 当前状态：S1–S6 软件链、mock/本地 adapter、Omni adapter、照片 API、独立 smoke 和真实分状态入口已完成；真实 Omni smoke 与本机设备已通过。真人 S1 正向唤醒已通过，不间断整链已到 S4 并验证质检重拍；最终 S6 复验按用户「暂停测试」要求停止。最新会话代际、VAD commit、音频关闭竞态和 Ctrl-C 修复已通过 91 个测试并纳入当前分支。真实 Insta360、Jetson、Galbot、现场网络与前端 UI 保持待团队验证。
