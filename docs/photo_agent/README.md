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
export OMNI_MODEL='qwen3.5-omni-flash-2026-03-15'  # 可选
export DASHSCOPE_WORKSPACE_HOST='llm-iscpge3ysktzaaf2.cn-beijing.maas.aliyuncs.com'  # 可选
```

不得把 Key 写进 `.env` 提交、Markdown、测试、日志或照片元数据。启动自检只显示 `api_key_present`。

## API-first 验证

```bash
# 枚举并最小读取摄像头/麦克风/扬声器
python scripts/photo_agent/device_smoke.py --camera 0 --microphone 1 --speaker 2

# 合成音画验证真实 Omni：建会话、音频后图像、VAD+主动响应、文本/语音、工具调用、结果回传、超时/错误识别
python scripts/photo_agent/omni_smoke.py
```

Omni smoke 通过后再启动真实链。官方 Python SDK 要求 DashScope `>=1.25.17`；图像按 1fps 左右发送，Base64 不超过 256KB，并且先发送音频。VAD 模式允许主动 `commit + response.create`，因此 S3 interval 采用该顺序。

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

## 前端最小接口契约

- `GET /api/photos/{photo_id}`：返回 `image/jpeg`；未知 ID 返回 404。
- 拍照结果：`{"photo_id": "...", "path": "...", "quality_ok": true, "ok": true}`。
- 交付结果：`{"photo_id": "...", "photo_url": "http://host/api/photos/...", "ok": true}`。
- 软件只保证稳定的 `photo_id` 与可访问 `photo_url`；照片展示、二维码生成和下载 UI 由前端完成。

## 自动化测试

```bash
python -m pytest -q
```

测试覆盖：S1 唤醒/抖动/连接重试；S2 接受/拒绝/两段超时；S3 interval/叠话闸门/VAD 打断/上限；S4 快门重试/质检/重拍上限；S5 满意/重拍/超时；S6 成功/失败复位；完整 S1–S6；图像限制、设备释放、照片 API、Omni 事件与工具回传、脚本入口。

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

将 `mock` 替换为 `local-real` 后会启动真实完整链，并打印该状态对应的用户动作。建议按 S1→S6 顺序统一验收，使用耳机避免扬声器回声触发 VAD。

## Jetson 迁移待验证

- Jetson 上 OpenCV/PyAudio/USB 摄像头设备名与权限。
- Insta360 SDK 的取流、快门、AI 追踪接口，用新 CameraAdapter 替换即可。
- 机器人音频设备索引、现场噪声下 VAD 阈值和网络延迟。
- 照片保留/自动删除策略与现场隐私告知。
- 前端真实屏幕展示与二维码 UI。

Git 协作：在 `feat/photo-agent-s1-s6` 本地提交；添加个人 fork 远程并推送该分支；从个人 fork 向 `mzli112358/PhotoMate-Moonbot-Hackthon` 创建 PR，不向无权限上游强推。
