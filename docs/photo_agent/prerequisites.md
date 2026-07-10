# Photo Agent 前置信息（已脱敏）

- Realtime WebSocket 模型：`qwen3.5-omni-flash-realtime`
- Workspace Host：`llm-iscpge3ysktzaaf2.cn-beijing.maas.aliyuncs.com`
- OpenAI 兼容地址：`https://llm-iscpge3ysktzaaf2.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`
- DashScope 地址：`https://llm-iscpge3ysktzaaf2.cn-beijing.maas.aliyuncs.com/api/v1`
- Realtime WebSocket：`wss://llm-iscpge3ysktzaaf2.cn-beijing.maas.aliyuncs.com/api-ws/v1/realtime`
- 实测注意：带日期的 `qwen3.5-omni-flash-2026-03-15` 在该 Workspace Realtime 端点会被拒绝；必须使用 Realtime 别名。

API Key 明文已移除。应用只能从环境变量或安全密钥注入读取：

```text
DASHSCOPE_API_KEY
DASHSCOPE_WORKSPACE_ID
DASHSCOPE_REGION
OMNI_MODEL
```

任何密钥、`.env`、本地照片和运行数据都不得提交。当前没有上游写权限；完成本地分支后推送个人 fork，再向上游发 Pull Request。
