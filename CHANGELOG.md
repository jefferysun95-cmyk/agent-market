# Changelog

## 1.1.0-alpha.2 — 2026-11-07

Client mail reliability fix, compatible with the alpha.1 order API; no production database migration needed.

- Search explicitly includes Spam/Trash. Receipt still requires exact sender, recipient, actual RFC822 Message-ID and attachment hashes.
- Read back Gmail's actual Sent copy using its internal message ID before recording mail-sent; do not assume the custom MIME Message-ID survived sending.
- Persist a private local outbox intent and Gmail ID. Retry a lost platform response without resending; uncertain Gmail sends reconcile against Sent, and stop if still uncertain.
- Explicit reconcile-input command preserves the old manifest, creates an auditable replacement with identical file hashes and binds the verified existing message. Never sends a second email. Available only before output delivery.
- Regression tests cover rewritten Message-ID, Spam, response loss, corrupted Sent attachments and alpha.1 record recovery.

This fixes the confirmed V03 mail mismatch; broader automatic waiting/worker recovery remains a separate beta gate. Release and live-recovery status must be reported separately from local tests.

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
