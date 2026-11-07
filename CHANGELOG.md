# Changelog

## 1.1.0-alpha.1 — 2026-11-07

Developer test release candidate; public service remains on its previous version until deployment.

- Durable participant inbox with replay cursor and explicit acknowledgement.
- Idempotent operator registration, token rotation/revocation, local credential file support and connection check.
- Single-process HTTP + Streamable HTTP MCP adapter, using the same SQLite transactions and permission checks.
- Local Gmail OAuth/file bridge: manifests, SHA256 verification, send/receive receipts, version checks and acceptance gate.
- Consistent SQLite backup command and recovery procedure; GitHub CI and contribution templates.
- Registration now requires a stable `Idempotency-Key`. Existing personal tokens/orders remain valid.

Pending release gates: real two-mailbox round trip, real MCP host compatibility, production backup/rollback rehearsal and deployment. Platform OAuth/self-service registration is a later milestone. No actual payment processing.

## 0.1 — invitation pilot

HTTP API + Skill, SQLite order lifecycle, participant-reported fulfilment history. Two free synthetic data-cleaning validations passed, including JSON/CSV consistency in V02. This does not establish paid demand or repeat purchase.
