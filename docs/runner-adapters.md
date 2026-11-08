# Alpha5 开发适配契约

仅描述当前开发分支，不是公开 alpha.4 的使用说明。仍需真实宿主与 V05 验证后才能发布。

当前下述为已实现的通用 v1 契约；真实 OpenClaw、拟新增决策 v2 和持续工作接管见[后续设计](openclaw-followup-design.md)，双机执行及通过门槛见[V05](validation-v05-plan.md)。设计字段不得直接作为当前 v1 参数使用。

## 受信宿主

在本地策略加入 host：

```json
{"host":{"argv":["/absolute/python","/absolute/trusted_adapter.py"],"cwd":"/absolute/private/job","timeout_seconds":120}}
```

程序路径由用户配置，不从任务或邮件生成；shell=False，不接受 cmd/bat/ps1/sh 作为入口。任务内容只通过 stdin 的 JSON 传递，不能拼接成命令。适配器使用当前用户权限，不是文件/网络安全容器；它必须自己落实 scope 和最新平台状态，不能运行附件中的指令。

输入含 schema_version=1、work_id、scope、intent 及当前 task。scope 是本地授权策略，不包含 host argv；intent 含 task/actor/revision/manifest、动作、原始 body 与 key。宿主必须按 work_id 去重，API 写入使用原稳定 key。超出授权就报告失败，不自行选择其他供给方或扩大文件范围。

stdout 必须仅返回以下对象，work_id 与输入一致：

```json
{"schema_version":1,"work_id":"FROM_INPUT","outcome":"completed"}
```

outcome 支持 completed、pending、provider_402、handler_failed 和邮件适配器错误码。pending 表示尚未完成，runner 退出 awaiting_host，不能宣称已经执行；宿主后续须按持久待办完成并 ack/resume。通用消费者可以完成一次业务动作后返回；任务状态仍由平台决定。

程序等待期间可被 stop/到期终止。POSIX 使用专属进程组，Windows 使用 KILL_ON_JOB_CLOSE Job Object；自有 bootstrap 在隔离成功前不启动宿主。只清理本次进程树。宿主不能靠自行后台派生子进程来绕过生命周期；需长期任务时使用独立且受信的宿主服务及可靠待办协议。每次调用最多 300 秒，输出上限 64 KiB，原 stdout/stderr 不进入运行器日志。

## 发现需求

discover 的本地 policy 字段为 actor_id、url、category、buyers（明确买方 ID 列表）、budgets（约定文本精确列表）、expires_at、max_seconds、interval_seconds、max_pages；可选 host。不接受任务内容提供的策略。

一次最多扫描配置页数，每页最多 100 条；每次完整扫描后重新从最新需求开始。待办和游标同事务保存；重启沿用未完成页。每项工作只存 task_id/actor/purpose；调用宿主前重读全文，已关闭、已报价或不再匹配的任务直接跳过。主机回报已处理可能是报价或明确放弃，不等于任务成交。发现能力不是自助注册，也不自动产生超出策略的报价授权。

## 直接邮件步骤

本地策略可加入 `mail: {"credentials_file":"/absolute/private/gmail-token.json"}`。只保存引用，不复制 OAuth 内容。构建包可选 mail 依赖与 requirements-mail.txt 一致；基础 CLI 不强制安装 Google 库，缺依赖时报告 mail_dependencies_missing。

步骤 kind=mail_send/action=mail-sent 或 kind=mail_receive/action=mail-received；body 必须指定 manifest_kind（input/delivery）、绝对 directory、from/to、files（明确 CSV/JSON 文件名列表）。可用 expected_files 进一步锁定完整元数据。from/to、文件名、清单方向和版本均须匹配最新平台状态。

邮件桥在受控进程中执行，重新核对 revision、身份、profile 和清单。发送仍先写私密 outbox 意图、回读实际 Sent Message-ID，再登记；收件包含 Spam/Trash 并校验真实头、附件字节、哈希后登记观察值。pending 有界重试；授权失败、证据不符或发送不确定直接停止。发送调用被中断/超时也标 send_uncertain；恢复先用原 outbox 对账，不重建清单或盲目重发。

单独的 mail_bridge.py 与安装包内实现保持字节一致并由回归测试约束。镜像是同一协议实现的分发方式，不建立第二套业务规则。仅在开发分支构建候选包，既有 alpha.4 Release 资产不会被替换。
