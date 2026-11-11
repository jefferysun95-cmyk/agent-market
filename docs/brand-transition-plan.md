# Future display brand: Run7 Agent Market / 未来展示品牌计划

Decision confirmed by the owner on 2026-11-11. **Planning only: the current product remains Agent Market.** This does not authorize an immediate rename, a new namespace, a release, deployment, authentication change or resubmission.

## Goal and scope / 目标与范围

未来展示品牌采用 **Run7 Agent Market**，以区分同名市场与 Skill。先做展示层更新，保持安装、连接、身份和历史交易兼容。没有指定实施版本或日期；在后续正常开发/发布中安排，不为改名另造运行版本。

The brand is a human-facing label. Package identifiers, API contracts and stored identity keys are compatibility surfaces, not text to replace globally. This document is a migration plan, not a uniqueness or trademark clearance.

## Compatibility baseline / 保留现有技术标识

| Surface | Keep during the display-brand phase |
|---|---|
| Repository and Pages paths | jefferysun95-cmyk/agent-market and existing Pages URLs |
| CLI / Python / distribution | agent-market; agent_market; agent-market-client |
| Skill / plugin IDs | agent-market; existing agent-market-plugins marketplace ID and publisher-qualified installs |
| MCP Registry canonical name | io.github.jefferysun95-cmyk/agent-market |
| Service addresses | Existing API, /mcp, registration and health endpoints |
| Credentials and local configuration | Existing tokens, agent IDs, agent_key semantics, environment-variable names, credential paths and config references |
| Business state | SQLite schema, orders, events, revisions, idempotency keys, receipts and payment boundaries |
| Existing releases | Existing tags, archive names, checksums, validation records and backups remain historical evidence |

不要求用户重装、重注册、迁移凭证或更换连接地址；不改数据库、不旋转 Token、不重发验证码、不为验证展示改名创建生产订单。不改 SMTP/Gmail 身份或授权。技术标识若将来确需更改，必须另立兼容迁移设计并获得授权。

## Implementation sequence / 实施顺序

1. **Before the next relevant change:** enumerate affected current entry files and channel metadata; distinguish current guidance from frozen history. Any newly introduced user-facing label should have a clear display-name location rather than create another hard-coded package identity. Keep this proportionate: no configuration framework or database entity solely for branding.
2. **When implementation is explicitly scheduled:** update Chinese/English website titles, README introductions and current onboarding/plugin descriptions together. Transition wording can be `Run7 Agent Market (formerly Agent Market)`. The current title is not changed by this plan.
3. **Normal package release:** update host-supported display names/descriptions while retaining canonical IDs. Claude's plugin name, Skill frontmatter name and registry name are not display-name substitutes; do not rename them globally. Record service version, wrapper version and documentation commit separately. Never replace frozen ZIPs/tags to refresh branding.
4. **Channels one by one:** update owned display metadata where supported and record actual response. For ClawHub, keep the present blocked artifact/support case intact; branding must not bypass scans or be described as fixing them. Registry title changes follow then-current version rules; do not overwrite immutable records. skills.sh discovery can lag. Glama ownership/health and each host approval remain separate. Unsubmitted Cursor/Anthropic/OpenAI materials can adopt the scheduled display name without claiming approval.
5. **Validate and back up:** bilingual and publisher/source checks; manifest/package validation where touched; existing-credential identity and authorized read-only compatibility where needed; preserve rollback metadata. Commit, create a dated handoff snapshot and verify hashes/offline Git recovery under AGENTS.md.

## Acceptance / 验收标准

- Current public guidance consistently explains the new display brand and the retained `agent-market` install identifier.
- All old authorized install commands, repository links, API/MCP addresses and private-config references remain valid; existing identities/orders need no migration.
- Required tests are proportionate to changed files. Do not run a new production signup/trade merely to verify branding.
- Every channel separately records display update, submission, review and installability. A name edit is not proof of security review or health.
- Original histories/releases/checksums remain untouched. If rollback is necessary, revert the display/documentation commit or channel metadata; no database restore or credential change should be required.

## Developer reminder / 持续开发要求

以后涉及 README、网站、Skill、CLI 帮助、插件清单或目录提交资料时，先查本计划：避免新增与未来 Run7 Agent Market 展示名耦合的技术标识，不在本次顺手提前改名。未完成事项如实保留，品牌规划不改变 Alpha5 免费测试、授权和支付边界。
