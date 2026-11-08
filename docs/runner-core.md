# Alpha5 运行器核心（可选实验功能）

本文件保留 `feat/alpha5-durable-runner` 的开发历史。本版注册 MVP 可独立使用；以下运行器必须显式配置并启动，默认关闭，不宣称达到 V05 无人工推进或通用 harness 自动唤起门槛。线上版本以 /health 为准。

本地回归：64 项通过，包括运行器核心、跨进程排他/崩溃释放、固定策略恢复、响应丢失、停止、宿主调用与进程树清理、需求发现、标准邮件桥衔接及发送不确定对账。干净 wheel 安装实际调用受信宿主，观察 localhost 业务写入后在授权边界停止；重装/卸载保留私密文件。使用临时数据和模拟邮箱；不是 V05 双机验证，也不代表跨平台 CI 已运行。

## 已有核心

- `run --policy FILE --state FILE`：前台有界运行，只执行本地明确授权的固定 API 步骤。策略创建后写入本地 SQLite；恢复沿用原请求体及幂等键。
- `watch --policy FILE --state FILE`：只读检测，结果明确标 detection_only；不会自动唤醒 Agent。
- `status --state FILE`：OS 文件锁验证当前 actor/任务是否有实例，旧 PID 文本不视为在线。同一账户、服务、actor、任务使用同一锁，换 checkpoint 文件不能绕过。
- `stop --state FILE`：设置协作停止标志；等待期间每秒检查。不杀其他进程，HTTP 在途调用最多等待当前 30 秒客户端超时，可能已成功的操作保留原意图。
- `resume --state FILE`：先重读当前身份、任务、revision 和进度，再恢复。不会延长累计期限或更换幂等键。
- `work show --state FILE` / `work ack --state FILE --id STEP --outcome completed|provider_402|handler_failed`：持久待办与宿主确认协议。没有宿主消费者时会明确退出 awaiting_host，不把保存文件当作已唤醒。
- 策略可配置本地受信 `host`，handoff 命中后实际启动程序，校验 work_id 与结构化回报，再读最新订单继续；不是只保存待办文件。
- `discover --policy FILE --state FILE`：按类别、指定买方和预算列表分页发现需求；游标与待办原子持久化，执行前重读单笔任务，避免旧缓存、重复报价或前 500 条遮挡。没有 host 时明确为 detection-only。
- `mail_send` / `mail_receive` 步骤：直接衔接标准邮件桥，绑定双方邮箱、目录、文件名和最新清单。实际头/哈希及发送意图对账机制不变；禁止固定 JSON 补回执。

run 返回 blocked/timed_out 时命令非零退出；状态查询本身正常返回。CLI 不回显原始网络异常/凭证。402 只有在宿主实际观察并明确上报时记为 provider_402；平台 HTTP 402 不被猜测为模型余额不足。

## 本地策略示例

策略是用户自己的授权文件，不从任务正文、邮件或附件读取。以下仅允许已知提案的 revision 1 确认；不是通用接单授权：

```json
{
  "actor_id": "SELLER_ID",
  "task_id": "TASK_ID",
  "url": "https://api.digolives.com",
  "expires_at": "2026-11-09T18:00:00+08:00",
  "max_seconds": 1800,
  "interval_seconds": 20,
  "steps": [{
    "id": "confirm-r1",
    "phase": "awaiting_confirmation",
    "revision": 1,
    "kind": "api",
    "action": "confirm",
    "body": {"revision": 1},
    "key": "my-job-confirm-r1"
  }]
}
```

kind 可以是 api、handoff、mail_send 或 mail_receive。handoff 委托受信宿主重新核对条件后执行并确认。ack 不替代平台业务状态，不证明邮件接收或内容正确；下一轮仍重新读取平台。旧 revision/清单的 ack 被拒绝；明确 proposal_id 的 select 完成后，允许其预期的 revision+1 转换。

核心 API 白名单为 proposals/select/mail-config/confirm/deliver/accept/request_changes/cancel。精确请求体必须事先授权；业务内容判断、自动选人和条件变更不能由进度提示代替。邮件回执不在白名单内，禁止用固定 JSON 伪造 actual observed 头。

本地 checkpoint 可含业务请求体，应保存在用户私密目录，勿提交 Git 或公开。禁止将 Token、邮箱密码、OAuth 配置放进策略。状态只保存请求意图，不记录原始 HTTP 异常、邮箱内容或附件。仅 POSIX chmod 不等于 Windows ACL 独立认证；运行账户应自行限制目录访问。

## 故障与恢复

网络错误最多连续尝试 3 次，指数退避，受最初累计期限及策略绝对到期限制。HTTP 401/403、409、身份/服务地址不符、revision 改变、旧事件快照立即停止。业务请求可能已提交但响应丢失时，先读最新状态；仍适用才重放原 key/body，不另造 key。

单实例锁由内核随进程退出释放；lock 文件不删除，防止 inode 替换形成两个锁。status 的 live 表示同一作业锁被占用，不独立监督远程 Agent。前台 runner 的宿主若退出，需要系统服务或 Agent 宿主重新调用 resume；当前不擅自安装开机服务。

## 未完成，发布前必须继续

1. 将宿主协议接到真实 OpenClaw/其他 Agent 消费者；通用子进程适配已实现，不等于当前 OpenClaw 已配对或自动接通。
2. 需求发现后创建/恢复单笔工作、动态报价选择及业务加工/私有验收处理器的完整授权方案。
3. 两个身份完整自动衔接、运行进程中断/重启场景、跨平台 CI。
4. V05 双机真实正常流程和故障矩阵，审核、GitHub 预发布、版本备份及按固定 commit 部署。

在这些门槛通过前，不将运行器宣传为可无人值守。范围已调整：自主注册按[独立 MVP 计划](self-registration-mvp.md)先行，不再以本节或 V05 为前置门槛。当前修改不修改服务器、数据库、旧订单或既有 Release。

宿主与邮件步骤的具体开发契约见[适配说明](runner-adapters.md)。

余下真实宿主与工作接管按[OpenClaw/持续跟进设计](openclaw-followup-design.md)实现；AngelX/Quincey 的双机出口按[V05 计划](validation-v05-plan.md)验收。Richard 是可选并发与权限验证，不自动替换正常主线供方。
