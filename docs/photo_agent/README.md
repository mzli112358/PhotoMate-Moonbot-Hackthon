# Photo Agent S1–S6 开发与验收

## 定位与边界

V0 是单机单用户服务。`app/photo_agent/` 持有确定性状态机；Qwen Omni 只负责看、听、说、意图理解和工具建议。普通电脑摄像头替代尚未提供 SDK 的 Insta360；Galbot、导航和机械臂不在本链路内。

状态链：`S0 -> S1 -> S2 -> S3 -> S4 -> S5 -> S6 -> S0`。S4 质检失败和 S5 不满意回到 S3。

## 安装与安全配置

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

密钥只允许安全注入：

```bash
export DASHSCOPE_API_KEY='...'
export OMNI_MODEL='qwen3.5-omni-flash-realtime'  # 可选
export DASHSCOPE_WORKSPACE_HOST='llm-iscpge3ysktzaaf2.cn-beijing.maas.aliyuncs.com'  # 可选
# 也可使用 DASHSCOPE_WORKSPACE_ID + DASHSCOPE_REGION=cn|intl 自动构造 Host
```

不得把 Key 写进 `.env` 提交、Markdown、测试、日志或照片元数据。启动自检只显示 `api_key_present`。

## API-first 验证

```bash
# 枚举并最小读取摄像头/麦克风/扬声器
python scripts/photo_agent/device_smoke.py --camera 0 --microphone 1 --speaker 2

# 默认读取真实麦克风，验证建会话、音频后图像、VAD+主动响应、文本/语音、工具调用、结果回传和超时识别
python scripts/photo_agent/omni_smoke.py --microphone 1
```

Omni smoke 通过后再启动真实链。官方 Python SDK 要求 DashScope `>=1.25.17`；图像按 1fps 左右发送，Base64 不超过 256KB，并且先发送音频。VAD 模式由服务端自动 commit，S3 interval 只使用 `append_image + response.create`；smoke 使用独立 Manual 会话验证 `commit + response.create`。

## 运行模式

```bash
# 全 fixture，自动跑完并退出
python -m app.photo_agent.cli --mode mock

# 本机摄像头、麦克风、扬声器、真实 Omni；同时启动照片 HTTP 服务
python -m app.photo_agent.cli --mode local-real

# 只声明预留边界，不假装已接真机
python -m app.photo_agent.cli --mode hardware-real
```

配置位于 `config/app.yaml:photo_agent`，可用环境变量覆盖。设备索引可从 `device_smoke.py` 输出选择。照片默认保存在 `data/photos/`，不会提交 Git。

运行日志为逐行 JSON，包含状态转移、原因、session/response/function call、拍照、质检、photo URL、重试和资源释放；密钥字段会自动脱敏。Omni 异常断线时会安全结束当前会话，并通过本地系统语音命令提示用户。会话在 115 分钟主动回收，避免撞到云端 120 分钟上限。

## 前端最小接口契约

- `GET /api/photos/{photo_id}`：返回 `image/jpeg`；未知 ID 返回 404。
- `GET /api/photos/{photo_id}/meta`：返回前端可直接使用的 `photo_id` 与 `photo_url`。
- `DELETE /api/photos/{photo_id}`：从注册表与本地文件系统删除照片。
- 拍照结果：`{"photo_id": "...", "path": "...", "quality_ok": true, "ok": true}`。
- 交付结果：`{"photo_id": "...", "photo_url": "http://host/api/photos/...", "ok": true}`。
- 软件只保证稳定的 `photo_id` 与可访问 `photo_url`；照片展示、二维码生成和下载 UI 由前端完成。

## 自动化测试

```bash
python -m pytest -q
```

测试覆盖：S1 唤醒/抖动/连接重试；S2 接受/拒绝/两段超时；S3 interval/叠话闸门/VAD 打断/上限；S4 快门重试/耗尽/质检/重拍上限；S5 展示重试/语音兜底/满意/重拍/超时；S6 成功/失败复位；完整 S1–S6；真实单状态 runner；图像限制、设备释放、照片 URL 取回、删除接口、Omni 事件与工具回传、断线恢复、115 分钟回收、JSON 日志和脚本入口。

## 分模块手动验收

每个状态都有独立入口：

```bash
python manual/photo_agent/run_state.py --state S1 --mode mock
python manual/photo_agent/run_state.py --state S2 --mode mock
python manual/photo_agent/run_state.py --state S3 --mode mock
python manual/photo_agent/run_state.py --state S4 --mode mock
python manual/photo_agent/run_state.py --state S5 --mode mock
python manual/photo_agent/run_state.py --state S6 --mode mock
```

将 `mock` 替换为 `local-real` 后，只启动所选状态所需的真实 adapter，不会偷偷跑完整链；到达该状态的验收终态后自动释放资源。S5/S6 会自动启动照片 HTTP 服务。建议按 S1→S6 顺序统一验收，使用耳机避免扬声器回声触发 VAD。

当前逐项完成证据与唯一外部阻塞见 [completion-audit.md](completion-audit.md)。

## Jetson 迁移待验证

- Jetson 上 OpenCV/PyAudio/USB 摄像头设备名与权限。
- Insta360 SDK 的取流、快门、AI 追踪接口，用新 CameraAdapter 替换即可。
- 机器人音频设备索引、现场噪声下 VAD 阈值和网络延迟。
- 现场照片保留时长与批量自动清理策略；当前已提供单张 DELETE 接口。
- 前端真实屏幕展示与二维码 UI。

Git 协作：在 `feat/photo-agent-s1-s6` 本地提交；添加个人 fork 远程并推送该分支；从个人 fork 向 `mzli112358/PhotoMate-Moonbot-Hackthon` 创建 PR，不向无权限上游强推。
