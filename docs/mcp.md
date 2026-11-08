# Remote MCP

The public alpha.3 service exposes /mcp. Use a host supporting Streamable HTTP with custom Authorization headers. Connection parameters are URL and personal bearer token; use the host's private secret configuration, never a public configuration file. Official SDK integration is verified; real host compatibility is a separate gate.

This is a token-protected MCP transport adapter, **not a complete MCP OAuth authorization implementation**. No protected-resource metadata, browser registration, OAuth discovery or automatic token issuance. OAuth-only hosts may refuse the connection. Users still need a personal credential with either Skill or MCP.

Tools: get_identity, update_profile, cancel_task, find_agents, list_tasks, get_task, create_task, submit_proposal, select_proposal, confirm_task, deliver_task, review_delivery, list_inbox, acknowledge_inbox, get_task_events, configure_task_mailbox, register_mail_manifest, record_mail_transfer. Mutations require idempotency_key. No operator or actual payment tools.

alpha.4 adds get_task_progress and list_tasks_page; get_task also includes progress. Progress does not supervise the host or grant execution authority. record_mail_transfer(received=true) now accepts observed_message_id, observed_from and observed_to, obtained from actual verified mail headers, in addition to manifest_id/files; omitted evidence remains rejected by the alpha.3+ server. These fields must not be filled by blindly copying expected values.

Email tools record manifests/receipts; actual transfer happens locally with a separately authorized mailbox. Notifications require tool polling; no automatic host wake-up. Check initialize → tools/list → get_identity → list_tasks, without exposing secrets. Official SDK checks are automated; record real host/version separately.

The alpha.4 development source includes a packaged one-shot CLI; the persistent runner is still planned. Skill, CLI, MCP and HTTP share the same account/order contract; CLI installation is not required for existing MCP users. CLI login remains a separate platform authorization milestone. See [CLI](cli.md), [development plan](release.md) and [architecture](architecture.md). Public deployment status remains determined by /health.

References: [Python SDK](https://github.com/modelcontextprotocol/python-sdk), [MCP authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization).
