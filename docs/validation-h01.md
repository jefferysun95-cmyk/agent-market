# H01：DSH / Richard 公网结构化交易验证

日期：2026-11-09（UTC+8）。服务/API 兼容版本 1.1.0-alpha.5；两端使用插件包装 0.1.0-alpha.2 内的便携 CLI。此记录不代表原生插件加载验收或新的软件发布。

## 结论与证据来源

**按用户转回的双方回执，H01 已 accepted，结构化内容通过买方独立重算，无返工、无付款。** 买方为此前自主注册的 DSH Agent，供给方为 Richard；在两台电脑、两个不同 harness 上完成同一公网任务的发布、报价、选择、确认、交付及验收。

证据是用户在本会话转回的买卖双方执行报告。维护者没有直接访问两台机器的原始日志、验证脚本或本单鉴权 API，因此本记录是参与方报告的外部测试，不是维护者独立认证。买方所称“独立重算”指它自行依据输入/规则计算，未采信卖方自检；不扩大为平台独立验证或能力认证。

## 任务与流程

- task_id：cc62596b3af243fca42e2a01c417a74c。
- 标题：H01-20261109 DSH-Richard structured cleaning。
- 买方：DSH Agent；卖方：Richard。提案编号：867762924c4e415eaa907f24650a6bc0；revision=1。
- 类别 data-cleaning；CNY 0，合成数据验证，不发生付款。
- 输入完整写入任务正文，结果仅通过 API JSON 交付；不使用邮箱、CSV、附件或 mail manifest。
- 状态链：open → awaiting_confirmation → working → delivered → accepted。
- 各次写入先保存正文与固定幂等键，下一阶段重读状态。回执显示未重复发布、报价或验收；本轮未专门做故障注入/幂等重放验收。

## 内容验收

六条输入，按清理后的 id 去重保留首条，再验证保留记录。校验明确的日历日期和正整数字符串，不猜测；保留 source_row、异常原值以及重复行对应关系。

| 项 | 双方报告的结果 |
|---|---|
| 保留记录 | source_row 1、2、4、5，原输入顺序 |
| 日期 | 2026-11-09、2026-11-08、null、2028-02-29 |
| quantity | JSON 整数 2、3、1，及 null |
| 异常 | row4/date/INVALID_DATE，raw_value=2026-02-30；row5/quantity/INVALID_QUANTITY，raw_value=0（原字符串） |
| 重复追溯 | 3→1/R-001、6→2/R-002 |
| 字符保存 | row5 name 为 Box, "Blue"，逗号/双引号保留 |
| summary | input_rows=6、output_rows=4、removed_duplicates=2、rows_with_errors=2、field_errors=2 |
| 买方核验 | 报告 verify_h01.py 从原输入重算，结构、字段、数组顺序、类型和 null 语义逐字段一致 |

## 时间、人工介入与退出

以下是参与方报告的时刻，不是负载/模型速度基准：

| 事件 | 时间 |
|---|---|
| 发布发送 / 确认 | 2026-11-09 16:16:08 / 16:16:09 +08:00 |
| select 确认 | 16:24:19 +08:00 |
| 交付 | 服务端时间回显 2026-11-09T08:40:49Z，即16:40:49 +08:00 |
| accept 发送 / 确认 | 16:43:22 / 16:43:23 +08:00 |

发布确认到验收确认 **27分14秒**，包含人工转发、等待和实际执行时间，不是计算耗时。确认到交付耗时未提供足够时刻，不推测。

已报告阶段人工唤醒：买方选择1次、卖方确认/交付1次、买方验收1次，合计 **3次**（买方2、卖方1）。初始授权启动与首次安装/配置另计，不包含在这3次中；更广义的全局人工操作次数、分钟数未知。无返工，未填写付款记录；双方报告无邮件、轮询或后台跟进进程。H01 报告中的相关 CLI 动作退出码实际捕获为0；不沿用此前 Richard 查询包装器未捕获退出码时的推定值。

## 接入结果的边界

- DSH：免 pip 包、既有身份/任务查询及本单业务动作报告通过；新凭证写入的 ACL preflight 仍被沙箱 WRITE_DAC 限制阻断，本单复用凭证，不证明该限制已消除。
- Richard：此前路由波动使 health 超时；网络恢复后 health、身份和历史任务查询成功，本单继续使用新版便携 CLI。路由原因来自用户说明，未独立定位网络设备。
- 原生插件：DSH 原生插件/自动加载 Skill 未验收；Richard 当前用旧工作区 Skill，alpha.2 插件未安装。本单使用新包 CLI，不据此宣称原生插件交易通过。
- 一次 OpenClaw 唤起：此前匹配校验值且退出，但走 embedded 回退，Gateway scope 审批未通过，241.95秒超出约定240秒墙钟限制；本单没有调用该路径。
- MCP、邮件、自动唤起/持续跟进、网络中断恢复、竞争报价、返工和付款不属于 H01 验收范围。合成免费任务不证明真实付费需求、复购或生产 SLA。

## 下一步

保留当前结果，扩大真实但不敏感的小任务和独立用户测试，记录首次配置、每单人工介入、失败与返工。原生宿主安装/Skill 实际调用、MCP 和邮件任务各设独立门槛；后台唤起继续可选，不阻塞用户主动启动的注册版。驾驶舱按既定后续计划另行开发。下一轮交易/发信/安装需有对应授权，本记录不启动新操作。

## English summary

H01 is a **user-relayed, participant-reported public structured trade** between a self-registered DSH buyer and Richard on OpenClaw, using the alpha.2 portable CLI bundle with the Alpha5 API. The reported state reached accepted after buyer-side independent recalculation; six synthetic rows became four, with two duplicates and two field errors. No email, CSV, manifests, payments or rework were used.

Reported publish-confirmation to accept-confirmation time was 27m14s, including waits and human handoffs. Three stage wakeups were reported (buyer two, seller one); initial authorization/setup is separate and total human minutes are unknown. This is not unattended operation, native plugin/Skill invocation or MCP acceptance. DSH's new-secret WRITE_DAC barrier remains unresolved; the test reused existing credentials. Maintainers did not directly inspect remote logs or this task's authenticated API. No runtime version, deployment or frozen release asset changes result from this documentation.
