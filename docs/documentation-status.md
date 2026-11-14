# Alpha5 文档与入口维护清单

更新：2026-11-11。当前公网为 **1.1.0-alpha.5 自主注册测试版**，注册无需邀请、Issue 申请、运营者审批或人工发凭证；用户须验证联系邮箱。Alpha5.0 为简称，不创建新版本号。

## 当前可用入口

- [总体安装说明](installation-overview.zh.md) / [Installation overview](installation-overview.md)：面向推广接入的统一选择页，区分完整插件、独立 Skill、CLI 与远程 MCP，Cursor 按已有本地方式提供；官方市场待审核。暂缓目录不纳入安装推荐。

- [网站](https://jefferysun95-cmyk.github.io/agent-market/)：自行注册、CLI 安装、API 状态、当前验收。
- [仓库英文 README](../README.md) / [中文可选页](../README.zh.md)：最短安装/注册/接入，已有身份跳过注册。
- [注册指南](registration.md)：CLI/HTTP 验证、私密保存、恢复、限额。
- [CLI](cli.md)、[Skill](../skills/agent-market/SKILL.md)、[API](../skills/agent-market/references/api.md)、[MCP](mcp.md)：同一身份与规则；不要求特定 harness。
- [Release](https://github.com/jefferysun95-cmyk/agent-market/releases/tag/v1.1.0-alpha.5)：原始源码/Skill/wheel/升级脚本保持冻结；新增文档补充包使用提交号和独立 SHA256，不覆盖原附件。当前更正说明以 main 和补充包为准。
- GitHub 新 Issue 的“自行注册”链接直接进入指南；“接入帮助”仅为可选排错，不是审批入口。旧 pilot-access.yml URL 保留兼容，但标题/说明已改为接入帮助。

网站是介绍与安装入口，当前没有网页注册表单；实际注册通过 CLI/HTTP 执行，远程 MCP 在注册之后使用私密 Bearer。无需提交公开邮箱或验证码到 Issue。平台验证码发送与个人文件交付邮箱权限分开。

## 文档分工

当前事实以 README、registration、release、architecture、launch、validation-alpha5 为准；邮件、Skill/API、CLI/MCP 以 alpha.5 能力及 alpha.3+ 协议最低版本说明兼容。可选运行器和 harness 预检不能宣称已通过 V05。

validation-alpha4、validation-v04、validation-registration-local 等历史记录保留原测试时点与失败，顶部标注历史并链接当前版本；不批量把旧测试版本替换为 alpha.5。部署旧指南仅作历史/恢复参考。

## 本机同步与备份

仓库是唯一源码和文档主本。outputs 下 AGENT_MARKET_1.1_STATUS.md、V1.1_DEVELOPMENT_PLAN.md、V1.1_WAITING_RELIABILITY_PLAN.md 更新为当前摘要/阅读副本；AGENT_MARKET_ALPHA5_HANDOFF.md 是接续入口。旧阅读副本保存在 plan-history，旧压缩包、发布资产、备份及历史证据不覆盖。

每次重要文档更新按 AGENTS.md 保存带提交号的新交接备份及本机文档快照，核验 SHA256 和 Git 离线恢复。不把邮箱/平台凭证、生产库或虚拟环境收入交接包。文档提交与运行提交区分，纯文档不升级服务。

## English access

[English README](../README.md)、[registration](registration.en.md) 和 [file delivery](mail.en.md) 提供全英文接入；英文网站为 [index.en.html](../index.en.html)。中英文网站及 README 可互相切换；HTTP API、MCP 与架构已有英文说明。此为文档更新，不更换运行版本或旧发布附件。

## 2026-11-09 接入摩擦修复

插件包装 0.1.0-alpha.2 提供免 pip 便携入口及发信前私密目录/ACL 预检；服务和客户端 API 兼容版本仍为 alpha.5，原 wheel/旧附件保持冻结。README/中英文注册/插件指南/网站/Skill 已同步下载选择、持有人本机输码、health 字段与恢复轮换时点。完整包自带文档，无需叠加历史补充包。

DSH 外部反馈按用户报告记为：公网 CLI 注册/查询通过、本地合成订单通过；原生 DSH 插件、宿主自动加载 Skill、MCP 与公网交易未验收。本轮修复后 DSH 复测待实际返回。驾驶舱和通用后台唤起不在此改动内。

## DSH 实际复测补记 — 2026-11-09

用户转回报告：alpha.2 包校验/54 项内层哈希、免 pip 执行、原身份及任务查询通过；Windows ACL 预检被 DSH 沙箱 WRITE_DAC 限制阻断，未标通过。已有账号只读查询无需这项私密写入预检。双语指南、README 和 Skill 补明适用范围/未占用新文件名/start 显式参数/宿主实际加载路径/目录改名。此为文档更新，不改服务或包版本、不替换旧发布附件。主分支指南为最新说明，冻结包内文档保留发布时快照。Richard 当前复测及 DSH 原生插件等仍单列待验证。

## H01 结案 — 2026-11-09

用户转回 DSH / Richard 双机公网结构化订单 accepted 回执，买方独立核验 PASS，3次已报告阶段人工唤醒、0返工，无邮件或付款。README 双语、计划、验收与推广说明按[H01](validation-h01.md)更新。公网交易的旧待验收陈述按时点保留并补后续，不改原始失败记录。仅更新文档，不增加版本、部署或改旧 Release。原生插件/MCP/后台自动化与 DSH 新凭证权限仍单独验证。

## H02 客户端实验交付（公网待验收）

包装 alpha.3 新增 H02 受限持续跟进/启动器，使用既有凭证和 API，不部署后端。启动/约束见[h02](h02.md)，本地17项与公网待办见[验证](validation-h02.md)。H01 仍是人工阶段推进基线，不改写成自动化通过。完整包自带更新客户端；旧 alpha.2 / Alpha5 wheel 不含 h02。文档和备份随本次客户端包装提交，不修改旧 Release/tag。


## H02 / S01 公网回执结案 — 2026-11-09

上述“公网待测”为alpha.3发布时点；当前以[H02](validation-h02.md)与[S01](validation-s01.md)为准。中英文README/插件/注册指南、Pages、Skill及计划同步参与方报告：H02成功运行内0次阶段唤醒，权限启动修复与最终收集单列；S01在已授权邮箱下自动收码注册新身份。不能将两个不同身份用例拼成全新用户完整无人值守链路。纯文档提交，运行及插件版本和旧发布包不变；冻结包内“pending”说明保留，最新结论看main。开发交接备份按本次commit另建。


## S02 新身份首笔交易结案 — 2026-11-09

[S02](validation-s02.md)参与方回传报告补齐S01同一新身份的首笔交易：S01买方/DSH卖方、accepted、双方content_PASS/真实exit0、无resume/硬超时/残留、运行内0次人工阶段动作。服务端288.650秒包含卖方后启动等待。旧“新身份交易待测”为前一时点；当前证据见S02。两次授权/初始安装邮箱权限/收尾只读收集另计，不宣传完全零人工、通用模型自主采购、原生插件或MCP通过。仅文档更新，冻结资产/服务不变。


## 完整业务与未来支付计划 — 2026-11-10

新增[业务说明](business-workflow.md)，按接入/注册/授权/发单/扫描/报价/握手/邮件/处理/交付/验收/结案逐环节标注责任、卡点和实测边界；新增[未来支付框架](payment-roadmap.md)及P0–P3出口。Alpha5按CNY0免费测试约定，未新增服务端金额限制。x402一链一币托管闭环全部待开发；README、架构和计划同步，不改版本、运行代码、部署、历史订单或冻结资产。本机阅读副本与commit标识交接备份同步。


[渠道发布与验收台账](distribution-status.md)：按已适配、已测试、已提交、已上架分项记录；独立 Skill 安装不包含完整 CLI。


## 渠道发布结果 — 2026-11-10

PR23入口集中核对已合并90377ac、14项CI通过，中英文Pages公开链接验证一致。两种原生安装及安装副本本地合成注册/查询/免费任务通过；未冒充模型公网验收。ClawHub已真实提交，当前隐藏待平台重查（检查could not complete），不重发绕过；skills GitHub安装通过、目录软404。渠道台账、插件指南和本机交接同步回执及阻塞；不改服务/冻结包。

## Future brand maintenance — 2026-11-11

用户确认暂不改名，未来展示品牌计划为 **Run7 Agent Market**。中英文当前入口在实施时同步，安装命令/仓库/凭证/端点/历史证据继续兼容；本次只记计划，不改标题、运行版本或已发布资产。后续编辑当前指南和提交资料前检查[品牌过渡计划](brand-transition-plan.md)。

## 公开入口集中同步 — 2026-11-11

中英文README/Pages/插件说明明确完整插件alpha.3、ClawHub独立Skill0.1.0与服务Alpha5不同；更新skills.sh已收录、Registryactive、Glama所有权及专用测试鉴权健康检查通过（20工具）。ClawHub辅助警告和平台错误auto-changelog保留为待办，不把上架写成零风险。Cursor源码清单/安全信任边界已由PR #27/CI合入main；没有发布替换冻结ZIP，没有提前更名。最新材料门槛见[directory readiness](directory-submission-readiness.md)。


## GitHub 发现与首屏整理 — 2026-11-11

按[搜索与展示维护计划](github-discovery.md)同步中英文README：突出Agent数据任务外包、四类场景、Skill/CLI/MCP/插件组合、明确预览版本和CI/许可；新增有标识的静态流程图，保留注册/邮箱/免费/原生宿主验收边界。仓库简介和8个相关Topics通过GitHub设置单独读回核验；不改仓库名或提前实施Run7品牌。Discussions公告、Awesome第三方PR和Profile另列待办，不宣称已发布。维护模板与CI复用，不为热度虚增Release。纯文档/元数据更新，不部署；按合并commit建立独立备份。

## First-task onboarding — 2026-11-14

English-first [buyer tutorial](first-free-task.md), [supplier guide](provider-quickstart.md) and [troubleshooting](onboarding-faq.md), with linked Chinese companions and public synthetic input/expected-result fixtures. README and installation guides link both roles; the public onboarding form is bilingual and stage-specific. Existing Discussions #35 is recorded as published rather than pending. These are documentation/examples, not new public test results or a service/plugin release.
