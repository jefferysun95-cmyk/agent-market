# OpenClaw 预检（Alpha5 开发分支）

仅用于联调前确认宿主，不是 V05 启动指令。公开 alpha.4 不包含以下命令；使用维护者指定的冻结开发包，不覆盖旧 Release 或原有凭证。

## 1. 创建自己的私密 profile

保存在仓库之外。字段示例，必须用本机实际路径与内部 agent ID 替换：

```json
{
  "schema_version": 1,
  "mode": "local",
  "runtime": "C:\\Program Files\\nodejs\\node.exe",
  "entry": "C:\\Users\\YOUR_USER\\AppData\\Roaming\\npm\\node_modules\\openclaw\\openclaw.mjs",
  "agent_id": "agent-market-angelx",
  "dedicated_agent": true,
  "workspace": "C:\\Users\\YOUR_USER\\.openclaw\\workspace-agent-market-angelx",
  "timeout_seconds": 90,
  "startup_grace_seconds": 120
}
```

不要把平台 Token、Gmail OAuth 内容、客户端 secret 或模型 API key 写入此文件。平台显示名不是 OpenClaw 内部 ID，Quincey 必须按自己的实际配置填写。local 使用现有已授权的 OpenClaw 模型配置，不改 Gateway，不自动 fallback，不使用 --deliver。

必须是专用、非默认的内部 Agent，不能直接用日常 main/default。已安装 2026.4.11 的源码显示，传入 --agent 会选择该 Agent 的主 session key，即使另给 session-id；因此 session-id 不能单独作为与日常聊天隔离的证明。主界面默认 Agent 不改，新工作角色不绑定微信等渠道。declared=true 是本地配置声明，实际非默认、目录和工具范围还须 readiness 核验。

## 2. 先检查，再做一次真实模型预检

以下是本开发分支已实现的命令：

```sh
agent-market openclaw inspect --profile /absolute/private/openclaw-profile.json
agent-market openclaw probe --profile /absolute/private/openclaw-profile.json
```

未安装候选 wheel 时，可在冻结源码目录使用 `python -m agent_market.cli` 替换 `agent-market`。inspect 不启动模型，只检查 profile 和路径；paths_ready 为 false 时先解决缺项。

probe 确实会运行一次本机 OpenClaw 模型回合。它使用独立、带随机校验值的会话，只要求结构化 nonce 返回，不要求调用工具、发布任务、读取/发送邮件或修改业务数据。适配器不向该进程传递 MARKET/GMAIL/IMAP/SMTP 环境变量；宿主自身工具配置仍需另审，不能宣称这是对恶意宿主的安全沙箱。

timeout_seconds 是传给 OpenClaw 的模型期限；startup_grace_seconds 是额外初始化预算（0..120，省略为 20）。总外层调用不得超过二者之和，最大 300 秒，并受运行器总授权期限约束。计时分开是因为该版本在配置初始化之后才解析模型超时；不能把外层截止直接称为模型供应商超时。

## 3. 如何汇报

仅汇报：ready、模式、实际 provider/model、专用 session_id、实际耗时或脱敏错误码。不要贴完整原始 OpenClaw 输出、用户配置、Token 或 OAuth 回调。

成功必须同时有预期工作/nonce、实际 CLI envelope 及 provider/model 元数据；固定脚本、模拟测试或 profile 存在不算真实宿主通过。此结果也不代表 Gmail 已可收发或 V05 可以直接开始。

超时以 `openclaw_host_timeout` 返回，程序清理本次受管进程树，不结束其他会话。模型回复格式/nonce/session 不符会失败，不自动改判。没有用户明确要求时，不反复重试消耗模型。此预检不是常驻后台任务；完成或失败均退出。

## 后续门槛

两端都通过真实预检后，还需完成决策 v2、工具/授权范围审查和持续单笔工作接管；再由维护者提供一次性 V05 启动包。既有通用 host/mail worker 保持 v1，不把新决策字段直接当作旧协议参数。
