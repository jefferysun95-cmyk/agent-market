# Upgrade and rollback (Ubuntu 22.04)

Use a reviewed/pinned commit. Never replace or download the production DB through Git. Keep the old checkout and systemd configuration. This procedure is prepared, not evidence that deployment occurred.

## Prepare

1. Save `systemctl cat agent-market` privately and record original ExecStart/WorkingDirectory. Confirm data path `/var/lib/agent-market/market.db`, service account `agentmarket` and private `/etc/agent-market.env`. Do not print the environment file.
2. Clone the reviewed revision into a **new** `/opt/agent-market-v1.1` directory. Create `.venv`, install requirements.txt there. Leave `/opt/agent-market` untouched for rollback.
3. Run tests and demo using the new virtual environment before directing production traffic to it.
4. Create a private backup directory and run the new `manage.py --db /var/lib/agent-market/market.db backup /private/backup/market-before-v11.db` as an authorized operator. SQLite backup works consistently while the old server is active. Copy it to separate private storage.
5. Reopen a copy with Store; verify known identity/order counts and PRAGMA integrity_check. Do not test restore against production.

## Switch

Create a systemd drop-in (preserve the original service and environment):

```ini
[Service]
WorkingDirectory=/opt/agent-market-v1.1
Environment=MARKET_DB=/var/lib/agent-market/market.db
ExecStart=
ExecStart=/opt/agent-market-v1.1/.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8787 --workers 1 --no-access-log
ReadWritePaths=/var/lib/agent-market
```

Keep User/Group, EnvironmentFile, UMask, restart policy and original hardening. Ensure source/venv readable by service account and DB writable only by it. Reload systemd and restart agent-market. Migration adds tables; no identity/token/order rewrite.

Nginx retains proxy_pass 127.0.0.1:8787. Add `proxy_buffering off;` for MCP and keep 1 MB request limit. Restrict the request rate at the proxy before external use (example `limit_req_zone $binary_remote_addr zone=market:10m rate=5r/s;` in http context, `limit_req zone=market burst=20 nodelay;` in the location). Validate configuration before reloading. Do not expose port8787 publicly. Keep valid HTTPS.

Check HTTPS /health version=1.1.0-alpha.1; old personal identity works; existing accepted orders unchanged; unauthenticated /me and /mcp denied; official MCP initialization/tools work with an authorized test identity. Do not create fake payment records. Real Gmail validation remains local on two authorized user devices.

## Rollback

Stop service. Remove only the new drop-in (preserve unrelated drop-ins), restore old ExecStart/WorkingDirectory and restart. Original server can ignore additive tables, but cannot enforce new mail/inbox rules: pause active 1.1 file tasks and notify affected testers before allowing old behavior.

Normally preserve current DB so no new orders are lost. If DB restoration is required, stop service first, preserve the failed DB privately, and restore the verified backup with correct ownership/permissions. Restoring a backup discards changes after its timestamp; get explicit approval for that loss. Recheck health/old identity and record incident/version.

## Operator credentials

Use manage.py register/rotate/revoke locally with the operator environment loaded privately. Stable --key is required; output credential files outside the repository, never terminal. Deliver personal credentials through an agreed private channel. Rotation invalidates the prior token immediately. Back up the operator secret separately; it is needed for deterministic issuance recovery. No automated email distribution of personal credentials is claimed.
