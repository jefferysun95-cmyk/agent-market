# Alpha5 运行器核心（开发分支，未发布）

本文件描述 `feat/alpha5-durable-runner`，不是线上版本。线上仍为 alpha.4；当前先实现任务绑定的核心，不宣称已经达到 V05 无人工推进门槛。

本地回归：49 项通过，其中新增运行器检查 12 项，包括跨进程排他/崩溃释放、固定策略恢复、响应丢失前后、累计到期、停止、身份与 revision 隔离、有限重试、宿主 ack/402 及只读 watch。使用临时数据和模拟网络；不是 V05 双机验证，也不代表跨平台 CI 已运行。

## 已有核心

- `run --policy FILE --state FILE`：前台有界运行，只执行本地明确授权的固定 API 步骤。策略创建后写入本地 SQLite；恢复沿用原请求体及幂等键。
- `watch --policy FILE --state FILE`：只读检测，结果明确标 detection_only；不会自动唤醒 Agent。
- `status --state FILE`：OS 文件锁验证当前 actor/任务是否有实例，旧 PID 文本不视为在线。同一账户、服务、actor、任务使用同一锁，换 checkpoint 文件不能绕过。
- `stop --state FILE`：设置协作停止标志；等待期间每秒检查。不杀其他进程，HTTP 在途调用最多等待当前 30 秒客户端超时，可能已成功的操作保留原意图。
- `resume --state FILE`：先重读当前身份、任务、revision 和进度，再恢复。不会延长累计期限或更换幂等键。
- `work show --state FILE` / `work ack --state FILE --id STEP --outcome completed|provider_402|handler_failed`：持久待办与宿主确认协议。没有宿主消费者时会明确退出 awaiting_host，不把保存文件当作已唤醒。

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

kind 可以是 api 或 handoff；handoff 不执行 HTTP 写入，要求受信宿主读取待办、重新核对条件后执行并确认。ack 只确认宿主处理结果，不替代平台业务状态，不证明邮件接收或内容正确；下一轮仍重新读取平台。旧 revision 的 ack 会被拒绝。

核心 API 白名单为 proposals/select/mail-config/confirm/deliver/accept/request_changes/cancel。精确请求体必须事先授权；业务内容判断、自动选人和条件变更不能由进度提示代替。邮件回执不在白名单内，禁止用固定 JSON 伪造 actual observed 头。

本地 checkpoint 可含业务请求体，应保存在用户私密目录，勿提交 Git 或公开。禁止将 Token、邮箱密码、OAuth 配置放进策略。状态只保存请求意图，不记录原始 HTTP 异常、邮箱内容或附件。仅 POSIX chmod 不等于 Windows ACL 独立认证；运行账户应自行限制目录访问。

## 故障与恢复

网络错误最多连续尝试 3 次，指数退避，受最初累计期限及策略绝对到期限制。HTTP 401/403、409、身份/服务地址不符、revision 改变、旧事件快照立即停止。业务请求可能已提交但响应丢失时，先读最新状态；仍适用才重放原 key/body，不另造 key。

单实例锁由内核随进程退出释放；lock 文件不删除，防止 inode 替换形成两个锁。status 的 live 表示同一作业锁被占用，不独立监督远程 Agent。前台 runner 的宿主若退出，需要系统服务或 Agent 宿主重新调用 resume；当前不擅自安装开机服务。

## 未完成，发布前必须继续

1. 初始需求发现/分页扫描和持久游标，不要求人工转任务号。
2. 真实受信宿主消费者及可靠唤醒；仅有 pull/ack 协议不能宣称睡眠 Agent 会自动执行。
3. 标准邮件桥衔接及发信不确定状态恢复，业务加工/验收处理器；核心不执行任意 shell。
4. 两个身份完整自动衔接、进程级崩溃和并发测试、干净 wheel 安装、跨平台 CI。
5. V05 双机真实正常流程和故障矩阵，审核、GitHub 预发布、版本备份及按固定 commit 部署。

在这些门槛通过前，不发布 alpha.5 为可无人值守的版本，不开启自助注册。当前修改不修改服务器、数据库、旧订单或既有 Release。
