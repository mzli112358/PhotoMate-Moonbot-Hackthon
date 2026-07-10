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

- 结论：官方 SDK 文档说明 VAD 开启时仍可主动 `commit`、`create_response` 和 `cancel_response`。
- 实现：S3 每轮为 `append_image -> commit_input -> response.create`；用户 speech_started 时取消在途回复。
- 官方资料：<https://help.aliyun.com/en/model-studio/omni-realtime-python-sdk>、<https://help.aliyun.com/zh/model-studio/qwen-function-calling>。

## 当前待真实验证

- 当前环境未设置 `DASHSCOPE_API_KEY`，所以真实云端 smoke 明确返回 blocked；未以 mock 冒充通过。
- 2026-07-10 首次运行时摄像头权限未授权；授权后复测已通过：Camera 0/AVFoundation 读取 1920×1080 帧、Bose QC Headphones 麦克风读取 3200 bytes、Bose QC Headphones 扬声器最小写入成功。
- Insta360 SDK、Jetson、Galbot 和前端二维码界面尚未提供，保持 adapter/接口边界。

## 运行中断线与设备异常

- Omni `error` / unexpected close 会产生结构化事件，触发本地系统语音提示、关闭云端会话并将 FSM 复位到 S0。
- 麦克风瞬时读写失败会记录 `audio_stream_failed` 并继续下一轮，不让后台任务静默死亡。
- 任一资源 close 失败不会阻止其他 WebSocket、摄像头、音频或后台任务继续释放。
