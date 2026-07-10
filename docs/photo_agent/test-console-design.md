# Photo Agent 可视化测试工作台设计

## 理解总结

- 为本地单用户提供 S1–S6 逐模块真实端到端验收工作台。
- 单页使用 S1–S6 状态胶片切换，每次只允许一个 `local-real` 测试运行。
- 前端真正启动/停止摄像头、麦克风、扬声器和 Qwen Omni 会话。
- 展示实时取景、当前状态、转移原因、设备、质检、照片和结构化日志。
- 编辑全局 System Prompt、S2–S6 状态 Context 和所有动作 Prompt，保存为项目默认配置。
- Prompt 支持版本历史、差异和回滚；运行中提交在「下一轮」受控热生效，不取消当前回答。
- 暂不提供人工模拟意图或强制状态跳转按钮，保持真实语音与真实设备验收。

## 假设与非功能要求

- 规模：仅 `127.0.0.1` 的一名操作者，单活动测试。
- 性能：预览约 2 FPS，状态/日志延迟目标小于 500 ms。
- 安全：无登录系统；API Key 只留在后端运行环境，不通过 API 或 DOM 暴露。
- 隐私：预览帧默认不落盘；仅 S4 快门保存照片；日志保持密钥脱敏。
- 可靠性：停止、页面异常和测试完成都必须释放设备、WebSocket 与后台任务。
- 持久化：Prompt 原子写入 `config/photo_agent_prompts.yaml`；最近 20 个版本和 50 次测试记录保存在本地 `data/`。
- 维护：沿用 FastAPI + 原生 HTML/CSS/JS，无新构建链、无 CDN，与现有仓库共同维护。

## 方案选择

### 采用：Prompt Registry + 模块化测试控制器

Prompt Registry 按名称管理三层配置：

1. `system.base`：角色、语气、安全边界和工具规则。
2. `state.S2`–`state.S6`：当前环节与任务上下文。
3. `action.*`：首次询问、补问、姿态引导、倒数、质检失败、满意度询问、交付等具体话术。

未采用单一巨型 Prompt，因为难以定位修改对状态的影响；也未采用工作流 DSL，因为当前只需调试话术，不应让 Prompt 改写本地确定性 FSM。

## 系统架构

```text
Browser /photo-agent
  ├─ REST: schema, prompts, history, test start/stop/status
  ├─ SSE: state, log, quality, photo, prompt-version events
  └─ MJPEG: active camera preview
            │
FastAPI Photo Agent Test Router
            │
PhotoAgentTestController (single active run + cleanup lock)
  ├─ PromptRegistry (atomic YAML + version history)
  ├─ PhotoAgentRuntime / PhotoAgentFSM
  ├─ EventHub / in-memory log handler
  └─ TestRunStore (last 50 summaries)
```

主要 API：

- `GET /api/photo-agent/schema`、`GET /api/photo-agent/status`
- `POST /api/photo-agent/tests/{state}/start`、`POST /api/photo-agent/tests/stop`
- `GET /api/photo-agent/events`（SSE）、`GET /api/photo-agent/preview.mjpg`
- `GET/PUT /api/photo-agent/prompts`
- `GET /api/photo-agent/prompts/history`、`POST /api/photo-agent/prompts/rollback/{version}`
- `GET /api/photo-agent/runs`

## Prompt 热切换语义

- 提交时先原子保存新版本，它立即成为下次启动的默认配置。
- 当前没有运行中响应时，Omni 在下一轮前通过 `session.update` 同步 `system.base`。
- 状态 Context 和 Action Prompt 每次使用时从 Registry 获取，所以自然在下一轮生效。
- 正在生成/播放的回答不取消；页面分别展示「已保存版本」与「当前会话生效版本」。

## 前端设计方向

- 审美：**Darkroom Test Bench / 暗房实验台**，以摄影接触印片和工业仪器为语言。
- DFII：`(4 视觉识别 + 5 场景匹配 + 4 实现可行 + 4 性能安全) - 3 一致性风险 = 14`。
- 识别锚点：顶部六格「状态胶片」，中央实时取景器，右侧 Prompt 实验笔记。
- 字体：离线打包 Space Grotesk（标题/状态）与 IBM Plex Mono（日志/参数）。
- 色彩：石墨黑主场、暖象牙白文字、安全橙操作、青蓝实时状态。
- 动效：仅保留页面进场、活动胶片推进和新日志脉冲，不做装饰性动画。

## 错误与边界

- 第二个启动请求返回 409，页面引导先停止当前测试。
- 设备/Key/Omni 预检失败时不启动部分运行时，并展示脱敏错误。
- 断开 SSE 不停止测试；页面重连后用 status + backlog 恢复画面。
- Prompt 保存使用期望版本号；冲突返回 409，禁止静默覆盖。
- 无活动摄像头时预览显示本地占位画面，不为了预览常驻占用设备。

## 测试策略

- Prompt Registry：默认配置、原子保存、版本冲突、历史上限、回滚、下一轮生效。
- Controller：单活动测试、启停清理、结果记录、日志脱敏、异常复位。
- API：路由合约、本地安全边界、SSE、MJPEG、Prompt 版本和 409 冲突。
- 前端：静态语义、键盘可访问性、移动布局、API 错误、Prompt 编辑/回滚、启停流程。
- 浏览器：Playwright 运行真实 FastAPI，验证 S1–S6 切换、Prompt 保存、状态更新、截图和 console 无错。

## 决策记录

1. 选择单页状态胶片，不创建六个独立 URL，保留测试上下文。
2. 选择 Prompt Registry，拒绝单一巨型 Prompt 和过度复杂的 DSL。
3. 选择「下一轮生效」受控热切换，不中断当前回答。
4. 选择原生 Web 技术与 FastAPI 同进程，不新增 Node/React 工具链。
5. 选择 SSE + MJPEG，匹配本地单用户和低帧率预览，不引入额外双向协议。
6. 仅允许真实语音/设备验收，暂不增加人工状态跳转按钮。
7. 实时预览不常驻占用摄像头，只展示当前测试的真实视频。

