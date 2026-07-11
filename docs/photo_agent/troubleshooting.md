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
- 长会话实测发现，服务端 VAD commit 后会清空当前音频 buffer；`append_image()` 现在在每次发图前都会先 `prime_audio()`，避免 committed 事件与 `_primed` 标志竞态导致 `Error append image before append audio`。

## VAD 与 interval 主动触发

- 实测：VAD 模式手动 commit 返回 `invalid_request_error`；服务端拥有 commit。主动 `response.create` 可用。
- 修复：S3 interval 使用 Manual 双响应：`vad=false -> audio+image+commit -> text-only assessment/tool -> tool result -> audio speech`。只有 speech `response.done` 才计一个逻辑回合并恢复 text-only VAD；下一 interval 从该时刻重新计时。
- 显式上下文：assessment 必须调用 `report_pose_turn`，本地保存模型自由选择/维持/替换的目标、视觉进度与引导意图；下一轮通过 `response.create.instructions` 回传最新 PoseContext。语音 transcript 只记录实际说过的话。
- 实机协议：`create_response(output_modalities=[TEXT])` 可稳定关闭 assessment 音频；Realtime 工具 schema 应保持扁平基础类型。`null` 类型会触发 `Parse RealtimeEvent error`，复杂嵌套 schema 也不稳定。
- 实测延迟：合成帧 smoke 中 assessment 约 1.27s、speech 约 0.47s，Function Call 枚举仍需本地校验。
- 用户 `speech_started` 时取消在途回复并恢复 text-only VAD；VAD 用户回合也通过 `report_pose_turn` 更新或替换目标。
- 官方资料：<https://help.aliyun.com/en/model-studio/omni-realtime-python-sdk>、<https://help.aliyun.com/zh/model-studio/qwen-function-calling>。

## Realtime 模型名称与建连竞态

- 现象：指令中的带日期模型名使 WebSocket 关闭并返回 `url error`；同一端点用 `qwen3.5-omni-flash-realtime` 可建会话。
- 修复：Realtime 默认模型改为专用别名；HTTP 兼容模型名不复用到 WebSocket。
- 竞态：SDK `connect()` 可在 `session.created` 回调前返回；adapter 现在最多等待 5 秒，不再误报「会话未创建」。
- 重连：每个会话使用新 callback generation 和事件队列，忽略旧 WebSocket 的延迟事件，避免污染下一次接待。
- 关闭：该 Realtime 模型不接受 SDK `end_session_async()` 发送的 `session.finish`；现改为记录结束原因后直接关闭 WebSocket。
- 鉴权失败伪装超时：DashScope SDK 在 API Key 无效时会先收到 HTTP 401，但 `connect()` 仍死等 5 秒并抛出网络超时。adapter 现在在 WebSocket 线程已退出时改为提示检查 `DASHSCOPE_API_KEY` 与 workspace 是否匹配。

## S3 评估后无语音输出（session output_audio 被关掉）

- 现象：S3 interval 评估或 `capture_photo` 之后，模型有文字 transcript，但耳机/扬声器无声；日志里 assessment 正常、`report_pose_turn` 已返回，speech 回合却像 text-only（`response_done` 几乎瞬间结束，无 `response.audio.delta`）。
- 根因：**不应**在评估/拍照阶段 `configure(output_audio=False)` 把 Omni session 收成仅 TEXT。DashScope Realtime 要求 session 保持 `output_modalities=[TEXT, AUDIO]`，评估回合只用 **response 级** `create_response(..., output_audio=False)` 静音；若 session 级关掉音频，后续 `configure(output_audio=True)` + speech `create_response` 仍可能不下发 `response.audio.delta`。
- 正确模式（与 `test_response_can_override_output_to_text_only_or_audio` 一致）：
  - `configure(enable_vad=False, output_audio=True)` → assessment `create_response(output_audio=False)`
  - assessment `response.done` → `configure(output_audio=True)` → speech `create_response(output_audio=True)`
- 高发路径（旧代码）：
  - `_coach_guidance_response()` / `start_pose_capture()` session 级 `output_audio=False`；
  - `handle_response_done()` 只恢复 VAD、未显式恢复音频；
  - 拍照失败后 `_say_and_wait()` 在 capturing 静音 session 上直接播报；
  - 质检失败 `quality_failed` 先 `create_response` 后 `configure`（顺序反了）。
- 修复：S3 全程保持 session `output_audio=True`；评估/拍照仅 response 级 text-only。会话配置已收敛为三个语义化助手：`_configure_listening()`（VAD 开 + 工具，S3 空闲）、`_configure_tool_turn()`（VAD 关 + 工具，评估/拍照）、`_configure_pose_speech()`（VAD 开 + 无工具，出声引导）；`_say_and_wait()` 作兜底。
- 诊断：日志应出现 `s3_speech_turn_started`（`output_audio_enabled=true`）及 `response_audio_summary`（`audio_delta_count>0`）。若为 0，检查 Bose 输出设备 index（应为 3，不是 4）。
- 实机确认（2026-07-11）：按上述修复后 S3 引导语音恢复正常。
- Demo 当前默认 `skip_quality_check: true`（`config/app.yaml` / `PHOTOMATE_PHOTO_AGENT__SKIP_QUALITY_CHECK`），拍照后不再走 OpenCV 闭眼/模糊回环；恢复质检时设为 `false`。

## S3「直接拍照」不触发拍照与 Manual 语音无法打断

- 状态链说明：S4 已删除；预期不是 `S3→S4`，而是 `S3 assessing/speaking/capturing → S5`，快门在 S3 内执行。
- 直接拍照根因：旧 `state.S3` 提示模型在用户说“直接拍照”时调用 `capture_photo`，但 dispatcher 只允许 `phase=capturing` 调用；用户 VAD 回合处于 `assessing`，因此属于 pipeline/工具契约冲突，不是模型能力不足。
- 修复：用户明确要求拍照时模型必须调用 `report_pose_readiness(ready)`；FSM 在该 VAD assessment 的 `response.done` 后先播简短确认，再启动 text-only `action.S3.capture`，由模型调用 `capture_photo`。
- 达标播报：`report_pose_turn(complete)` 不再直接跳到 capturing，而是设置 `capture_after_speech`，先播 `guidance_intent`，播完再拍。
- VAD 根因：旧 speaking 仍配置 `enable_vad=false`，且麦克风循环在 VAD 关闭时主动丢弃音频，因此用户无法打断。现所有可听 S3 speaking 均启用 VAD；`speech_started` 会取消当前 response，并清除待拍标记，避免被打断后继续拍照。
- 竞态：capture 的 `response.done` 可能晚于 `capture_photo` 回调；runtime 现在按 `response_id` 关联 assessment/capture/speech，迟到的 capture done 不会误结束「我拍好啦」。

## 测试台手动测 S3 被 60s 墙钟超时打断

- 现象：`{"ok":false,"tested_state":"S3","error":"manual state timed out after 60.0s","result_state":"S3"}`。S3 引导到拍照常超过一分钟，默认超时会误杀仍在进行的会话。
- 修复：`run_manual_state` / `_run_until_states` 默认 `timeout=None`（不限时），直到进入目标状态或操作员点停止；单测仍可显式传入短 timeout。

## OpenCV 5 与音频退出

- OpenCV `5.0.0.93` 当前包不含 `CascadeClassifier`，S1/S4 无法启动；依赖已限定为 `opencv-python>=4.10,<5`。
- 取消 `asyncio.to_thread(PyAudio.read)` 会留下阻塞 executor 线程，导致业务结束后进程不退出；现改为任务内 100ms 有界读取。

## 当前实机边界

- 真实 Qwen smoke 已全部通过；Camera 0/AVFoundation 读取 1920×1080 帧，Bose QC Headphones 麦克风与扬声器通过。
- 调整机位后，真人 S1 正向唤醒已通过；真实整链已达 S4 并验证模糊重拍回环，最终 S6 URL 复验因用户要求暂停而未继续。
- MacBook 麦克风 + MacBook 扬声器会把 Omni 输出重新收音，触发 VAD 回声自对话。现场验收应使用耳机输出，或后续在真机音频链接入 AEC；不为了压回声禁用用户打断能力。
- Insta360 SDK、Jetson、Galbot 和前端二维码界面尚未提供，保持 adapter/接口边界。

## 运行中断线与设备异常

- Omni `error` / unexpected close 会产生结构化事件，触发本地系统语音提示、关闭云端会话并将 FSM 复位到 S0。
- 麦克风瞬时读写失败会记录 `audio_stream_failed` 并继续下一轮，不让后台任务静默死亡。
- 任一资源 close 失败不会阻止其他 WebSocket、摄像头、音频或后台任务继续释放。
