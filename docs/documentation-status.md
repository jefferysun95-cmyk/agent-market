# Alpha5 文档与入口维护清单

更新：2026-11-09。当前公网为 **1.1.0-alpha.5 自主注册测试版**，注册无需邀请、Issue 申请、运营者审批或人工发凭证；用户须验证联系邮箱。Alpha5.0 为简称，不创建新版本号。

## 当前可用入口

- [网站](https://jefferysun95-cmyk.github.io/agent-market/)：自行注册、CLI 安装、API 状态、当前验收。
- [仓库 README](../README.md)：最短安装/注册/接入，已有身份跳过注册。
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
