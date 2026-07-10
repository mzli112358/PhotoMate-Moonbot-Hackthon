# Photo Agent 排障记录

## 直接执行脚本无法导入 `app`

- 现象：`python scripts/photo_agent/omni_smoke.py` 报 `ModuleNotFoundError: app`。
- 根因：Python 把脚本所在子目录放入 `sys.path`，不是仓库根目录。
- 修复：三个直接入口根据 `__file__` 注入仓库根目录；新增 subprocess 回归测试。
- 回归：`tests/photo_agent/test_script_entrypoints.py`。

## Omni 音频与图像顺序

- 约束：Realtime 以音频为时间线，发图前至少发一次音频；图像 Base64 不超过 256KB，建议约 1fps。
- 修复：`prime_audio()` 发送静音 PCM；`encode_frame()` 逐级缩放/降质直到满足上限。
- 回归：`test_real_client_configures_vad_tools_and_primes_audio_before_image`、`test_encode_frame_obeys_realtime_image_limit`。

## VAD 与 interval 主动触发

- 实测：VAD 模式手动 commit 返回 `invalid_request_error`；服务端拥有 commit。主动 `response.create` 可用。
- 修复：S3 每轮为 `append_image -> response.create`；用户 `speech_started` 时取消在途回复。独立 smoke 改用 Manual 模式验证 commit。
- 官方资料：<https://help.aliyun.com/en/model-studio/omni-realtime-python-sdk>、<https://help.aliyun.com/zh/model-studio/qwen-function-calling>。

## Realtime 模型名称与建连竞态

- 现象：指令中的带日期模型名使 WebSocket 关闭并返回 `url error`；同一端点用 `qwen3.5-omni-flash-realtime` 可建会话。
- 修复：Realtime 默认模型改为专用别名；HTTP 兼容模型名不复用到 WebSocket。
- 竞态：SDK `connect()` 可在 `session.created` 回调前返回；adapter 现在最多等待 5 秒，不再误报「会话未创建」。

## OpenCV 5 与音频退出

- OpenCV `5.0.0.93` 当前包不含 `CascadeClassifier`，S1/S4 无法启动；依赖已限定为 `opencv-python>=4.10,<5`。
- 取消 `asyncio.to_thread(PyAudio.read)` 会留下阻塞 executor 线程，导致业务结束后进程不退出；现改为任务内 100ms 有界读取。

## 当前实机边界

- 真实 Qwen smoke 已全部通过；Camera 0/AVFoundation 读取 1920×1080 帧，Bose QC Headphones 麦克风与扬声器通过。
- 当前画面只包含额头边缘，因此 S1 不唤醒、S4 返回 `face_not_found,blurred` 是正确行为；调整物理机位后再验证正向 happy path。
- Insta360 SDK、Jetson、Galbot 和前端二维码界面尚未提供，保持 adapter/接口边界。

## 运行中断线与设备异常

- Omni `error` / unexpected close 会产生结构化事件，触发本地系统语音提示、关闭云端会话并将 FSM 复位到 S0。
- 麦克风瞬时读写失败会记录 `audio_stream_failed` 并继续下一轮，不让后台任务静默死亡。
- 任一资源 close 失败不会阻止其他 WebSocket、摄像头、音频或后台任务继续释放。
