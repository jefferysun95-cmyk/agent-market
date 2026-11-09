# H02：零交易阶段人工唤醒验证

2026-11-09。插件包装 **0.1.0-alpha.3**，服务/API兼容版本 **1.1.0-alpha.5**。**公网 DSH 买方 / Richard 卖方报告同单 accepted，成功运行期间交易阶段人工唤醒为0。** 安装启动修复与最终只读收集另记，不称从安装到收尾完全无人介入。

## 证据来源与范围

维护者收到用户转回的双方 checkpoint/audit、观察器真实退出记录、进程检查，以及买方通过原身份只读查询的任务和服务端事件报告。维护者未直接进入两台远端电脑、读取其私密日志或以生产凭证独立查询该任务。以下均为参与方回传证据，不是第三方独立认证；公开资料不包含邮箱、验证码、Token或本机私密路径。

任务 `8f75eebc8c044791b7cc93b893a08bfd`，run-id `h02-20261109-01`，标题 H02 h02-20261109-01 structured zero-handoff，revision=1，指定 DSH 买方与 Richard 卖方，单份CNY0提案。payment={}，无邮件、CSV、manifest或付款。

## 服务端时间线（买方只读查询回传）

| event | action | actor | UTC，2026-11-09 |
|---|---|---|---|
| 61 | created | buyer | 11:51:48.635915Z |
| 62 | proposals | seller | 11:52:24.062300Z |
| 63 | select | buyer | 11:52:30.597014Z |
| 64 | confirm | seller | 11:52:44.442634Z |
| 65 | deliver | seller | 11:52:58.249656Z |
| 66 | accept | buyer | 11:53:00.808927Z |

发布到验收 **72.173秒**（约1分12秒），不是首次配置到结束的总成本或性能承诺。按报告六个业务事件各一次、顺序正确。卖方本机时间比服务端对应事件约早2分30秒；不能合并两台机器的墙钟推导耗时，时差原因未独立核实。买方成功启动到本机完成约95秒另计。

## 双端结果

| 项 | DSH buyer | Richard seller |
|---|---|---|
| 本机 status / phase | completed / accepted | completed / accepted |
| task_id | 同上 | 同上 |
| verification | content_PASS | content_PASS |
| business_exit_code（观察器记录） | 0 | 0 |
| hard_timeout_triggered | false | false |
| resume_requests / model_invocations | 0 / 0 | 0 / 0 |
| 已知业务及观察器 PID | 均退出 | 均退出 |

服务端存档 result：input_rows=6、output_rows=4、removed_duplicates=2、rows_with_errors=2、field_errors=2，4条输出；买方独立参考比较报告PASS。程序内部有10秒间隔查询，不应把“未额外写轮询脚本”写成“没有轮询”。human_interventions=not_independently_observed 保留，不能把该字段或stage_callbacks_required=0本身当作实际零介入证据。

## 启动失败、权限与成本

首次 DSH 业务进程在HTTP请求前因 `%LOCALAPPDATA%/AgentMarket/runner-locks` 工作区外路径被拒绝而退出2，checkpoint已创建但无task/intents/steps。参与方报告之后放行锁目录、核对并删除旧未运行checkpoint及4个侧文件，使用同一run-id/路径重新启动成功。这是**安装启动修复**，不是第一次尝试就通过；旧本地文件未保留，不能声称离线重查过原失败文件。正常交易六步期间没有再次人工推进或resume。新state的resume_requests=0不抹去首次失败历史。

普通沙箱下最终 status 仍曾被锁文件权限拒绝，参与方用一次只读完整文件访问收集成功。这是**最终收集成本**，不算交易推进，也不宣称status已解决沙箱权限问题。后续开发应在创建checkpoint/请求网络前诊断锁目录权限，并改善无需写目录的只读诊断；不能用重定向LOCALAPPDATA、换锁域或关闭锁规避单实例保护。

Richard初始报告网络错误后自动退避；最终同单正常完成。模型欠费导致聊天报告延迟，程序不调用模型，双方model_invocations=0，不能把模型欠费记成交易执行中断。没有足够日志细节量化所有网络重试次数。双方初始授权/安装启动、修复、最终只读收集次数与分钟数没有统一原始计时，不补造全流程人工总数。口径为：**成功运行内阶段人工唤醒=0；首次接入及收尾有人参与。**

## 本地实现及发布验证（先前时点）

- 17项专项：买卖方不同启动顺序、丢响应恢复/稳定key、独立内容/严格类型、身份/来源/条款/到期拦截、同actor/run锁、stop/resume不续期、观察器硬超时。
- 两个真实CLI经回环HTTP完成accepted；两个launch启动器退出后子进程继续完成，实际退出码0，无阶段回调。
- 本地完整129项，1项Windows符号链接权限跳过，其余通过。PR #19共14项CI通过；运行源码commit `30f44f5419b7fa5105f8f65e6c414fd43f413248`。已发布ZIP的59项文件哈希及下载校验通过，候选包解压后双进程交易通过。
- 线上仍Alpha5；本次结果文档不改运行代码、旧包、tag、Release或数据库。

## 结论与下一门槛

H01的3次阶段人工唤醒，在H02成功运行内降为0；只适用于指定双方、固定规则合成CNY0、纯API结果的确定性跟进。它不证明模型自主采购/验收、原生插件/Skill/MCP、通用后台唤起、付费需求或任意网络故障恢复通过。自动收验证码注册独立见[S01](validation-s01.md)，未把S01新身份与H02旧身份拼成同一条全新用户全链路测试。

下一步先收敛首次接入锁/权限与只读诊断；然后用新注册身份验证明确授权的非敏感小任务，分别记录模型业务决策、邮箱/文件、返工和人工成本。可靠模型唤起仍为可选增强，不阻塞注册MVP。

## English summary

Participant reports support one accepted public H02 trade between DSH and Richard, with zero human business-stage wakeups during the successful run, independent buyer content PASS, both actual child exit codes0, no hard timeout/resume and no residual observed child/observer. Six reported server events span72.173seconds. This is deterministic execution without model, mail or payment calls, not native plugin/MCP or general LLM autonomy certification. The first buyer startup failed on a sandbox-external lock directory; scoped permission/setup retry and elevated final read-only collection are separate human costs. Seller clock differs by about150seconds; use server event times. The maintainer received relayed reports, not direct remote logs or an independent authenticated server audit. Frozen artifacts and deployment remain unchanged.
