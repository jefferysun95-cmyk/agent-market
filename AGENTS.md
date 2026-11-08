# Agent Market development

Read README.md, docs/release.md and docs/architecture.md before implementation.
Keep one service and SQLite; HTTP, MCP, Skill and CLI use the same Store rules.
Never read or print production credentials to develop or test. Use temporary data and synthetic mail.
Do not deploy or modify production data merely to verify a local change.

## Version backups — user requirement, 2026-11-08

Every alpha/beta/final development release must have a separate versioned and timestamped handoff backup: committed source, full local Git bundle, plans, architecture, current status, restoration instructions and SHA256 inventory. Verify an offline clone and file hashes before reporting delivery complete. Include this file in the backup for the next developer/tool. Important docs-only deliveries use a commit-labelled snapshot without inventing a runtime release.

Do not overwrite or delete earlier backups. Exclude platform/mail tokens, OAuth client configuration, private keys, production DB/config, virtual environments and private correspondence. A bundle contains reachable Git history and is for trusted handoff, not automatically safe for public upload; no full historical secret audit is implied.

Development backup is separate from deployment backup: back up production SQLite consistently and protect server configuration before deployment, under docs/deploy-v11.md. Record deployed version separately from local candidate and GitHub publication. No backup operation may move an existing tag, overwrite release assets, change production or silently omit uncommitted work.

Local backup default for this workspace: C:/Users/jeffs/Documents/Codex/2026-11-05/a/outputs/agent-market-backups. Use tools/backup_development.py after committing the reviewed version. This is a release workflow, not a background schedule or off-device backup.
