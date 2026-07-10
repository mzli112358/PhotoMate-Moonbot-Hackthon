# CodingAgent 开发指令完成审计

审计日期：2026-07-10。判定原则：只把当前文件、命令输出或外部状态能直接证明的事项标为完成。

| 要求 | 状态 | 当前证据 |
|---|---|---|
| clone 上游、独立分支、不初始化父目录/无关子模块 | 完成 | 仓库分支 `feat/photo-agent-s1-s6`；`origin` 保持上游，`fork` 为个人仓库 |
| PRD 与脱敏前置信息入库 | 完成 | `docs/photo_agent/PRD.md`、`prerequisites.md` |
| 仓库级 AGENTS.md | 完成 | 覆盖目标、边界、状态、API-first、测试、密钥、Git 与当前状态 |
| Python/asyncio/显式 FSM/adapter/FastAPI，且不使用 LangGraph | 完成 | `app/photo_agent/` 与架构测试 |
| S1–S6 正常、超时、异常、重试、回环、调用顺序与复位 | 完成 | 全量 pytest；含快门/展示/交付耗尽与语音兜底 |
| S1→S6 mock 完整链 | 完成 | `python -m app.photo_agent.cli --mode mock` 返回成功并输出完整 JSON 状态日志 |
| mock photo_url 指向本次正确照片 | 完成 | `test_full_chain_photo_url_fetches_the_captured_file` 实际通过 ASGI 获取相同文件 bytes |
| 本地照片接口与前端契约 | 完成 | GET 文件、GET meta、DELETE 本地照片；未知 ID 404 |
| 摄像头、麦克风、扬声器独立 smoke | 完成 | Camera 0/AVFoundation: 1920×1080；Bose QC Headphones 麦克风: 3200 bytes；Bose QC Headphones 扬声器写入成功 |
| 设备选择与启动显示实际设备 | 完成 | YAML/env 设备索引；adapter `device_name`；CLI/manual preflight 输出实际名称 |
| Qwen smoke 脚本覆盖 12 项 | 完成 | 真实运行 `ok: true`：两个干净会话覆盖建连、真实麦克风、音频后图像、文本/语音、Manual commit+response、Function Calling、工具结果续答与 timeout |
| OmniClient 接入真实状态机 | 完成 | 专属 Workspace 真实会话已验证；修复 Realtime 模型别名、VAD/Manual 边界、延迟 `session.created` 竞态与工具调用遵从 |
| 每个 S1–S6 可单独运行 | 完成 | `run_manual_state` 六状态参数化测试；`manual/photo_agent/run_state.py --state Sx --mode local-real` 只运行指定状态 |
| mock/local-real/hardware-real 模式 | 完成 | mock 与 local-real 实现；hardware-real 明确预留且不会假装接入 |
| 结构化可观察性 | 完成 | 逐行 JSON：state、reason、session/response/call、capture、quality、URL、retry、release；密钥脱敏 |
| 120 分钟会话边界 | 完成 | 115 分钟主动回收测试，避免撞云端硬上限 |
| 断线和本地兜底 | 完成 | unexpected close/error 触发系统本地语音提示、释放会话并回到 S0 |
| 无后台任务/文件句柄/会话泄漏 | 完成 | 真实 S6 进程自然退出；修复 PyAudio 取消后遗留 executor 读线程，并有回归测试 |
| README、运行、测试、手动验收、Jetson 风险、排障文档 | 完成 | `README.md`、`docs/photo_agent/README.md`、`design.md`、`troubleshooting.md` |
| 本地提交、个人 fork、上游 PR | 完成 | PR #1 已创建；本轮审计修复待追加提交并推送 |
| 真实 Qwen + 本地设备分状态链 | 完成 | S2 静默超时复位、S3 约 5 秒引导、S4 快门+质检回环、S5 超时默认接受、S6 URL 交付+复位均使用真实 adapter 通过 |
| 真人 S1 正向唤醒 + 不间断 S1→S6 | **物理复验待办** | 实拍画面只包含额头下缘，不满足「完整正脸」唤醒/质检条件；S1 保持未唤醒、S4 返回 `face_not_found,blurred` 均符合设计 |

## 剩余物理验收

调整摄像头或坐姿，使完整正脸进入画面，然后执行：

```bash
python -m app.photo_agent.cli --mode local-real
```

不间断跑完 S1→S6 并打开本次 URL 后，才可把最后一项标记为完成。
