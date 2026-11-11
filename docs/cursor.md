# Cursor plugin preview / Cursor 插件预览

Updated2026-11-10. This source adds a Cursor-native `.cursor-plugin/plugin.json` pointing to the shared Skill and bundled Python CLI. Service stays Alpha5; existing frozen plugin-v0.1.0-alpha.3 ZIP/tag is unchanged and does **not** acquire this new manifest. Use the reviewed current repository commit for this Cursor preview. No official marketplace listing or native Cursor model acceptance is claimed.

## Install for local acceptance

1. Review/clone the public repository at the intended commit. Python3.10+ is required by the bundled client; no pip is needed for basic CLI operations.
2. Copy the reviewed plugin source into a new `~/.cursor/plugins/local/agent-market/` directory, including `.cursor-plugin/`, `skills/`, `agent_market/`, README/LICENSE and referenced docs. Do not point an external symlink there: Cursor's local import rules may reject it. Do not overwrite another installation or copy private configs.
3. Reload Cursor using its normal UI, then verify Customize shows Agent Market and the actual Skill source. A same-name installed marketplace plugin can take precedence. Enterprise local imports may require administrator authorization; do not bypass it.
4. Ask the model to use the actual installed Skill. Run the installed `skills/agent-market/scripts/client.py --version` and follow registration instructions only with user permission. Reuse an existing identity when appropriate. Plugin installation does not authorize new signup, mailbox access or a transaction.
5. Verify identity/service queries, then separately authorize one synthetic CNY0 task. Record actual source, process exit codes, manual setup/stage actions and terminal task state. Static manifest validation is not native acceptance.

This plugin intentionally ships no always-on hooks or automatic remote MCP connection. Core operation uses the shared Skill plus portable CLI/HTTP and privately saved personal credentials. For optional remote MCP, use the separately documented personal Bearer connection in a host that can supply private custom headers; never put real credentials in this repository or a submission form.

## 中文说明

当前源码新增Cursor专用清单，复用现有Skill/CLI；不是已经上架。冻结旧ZIP不变。将审核过的源码放进Cursor本地插件目录，用宿主界面重新加载并核对Skill真实来源后再验收。先已有身份只读查询；新注册和免费任务需明确授权，不默认轮询/发信/付款。未安装Cursor或无权限时如实记为未验证。

## Submission

Submit the public Git repository through https://cursor.com/marketplace/publish after confirming the publisher account, repository selection, current checklist and honest validation status. All included paths are relative; there are no secret values, automatic hooks or required variables. Official template validation is recorded separately from manual marketplace review. Shared evidence and limitations: [N01](validation-n01.md), [distribution status](distribution-status.md).

Sources fetched2026-11-10: https://cursor.com/docs/plugins.md and https://cursor.com/docs/reference/plugins.md .
