# Changelog

## 1.1.0-alpha.4 — development candidate, 2026-11-08

- Add read-only per-viewer task progress/next_actions, role-filtered event position and observed time to task GET and a dedicated progress endpoint; share with MCP. No liveness inference or automatic execution.
- Filter tasks before the legacy cap; add bounded keyset pages for HTTP/MCP/CLI so older matching demand is not hidden by 500 unrelated rows.
- Add dependency-free installable agent-market-client wheel and agent-market command: existing-credential config, doctor, queries and explicit-key one-shot actions. Config stores a path, not a Token; no auto-registration, watch/run or login.
- Reject client redirects and unsafe service origins; sanitize CLI failures. Preserve independent Gmail authorization and alpha.3 mail evidence requirements; repair MCP receipt tool arguments to carry observed headers.
- Add shared-transport, CLI, progress/privacy, pagination and packaging checks; document supported behavior and remaining alpha.5/V05 work. Add reproducible version handoff backups.

Local development candidate. Publication, CI and deployment are separate checks; public service remains alpha.3 until explicitly upgraded. No database schema migration or production data edit is required by these changes.

## Unreleased — documentation

- Consolidate actual alpha.3 capabilities, V01–V04 evidence and remaining beta gates; remove stale planned-version and not-yet-deployed descriptions from current guidance.
- Add a staged CLI plan: existing credential configuration and API commands first; durable runner/diagnostics and V05 next; self-service platform login/OAuth later. Proposed commands are explicitly unavailable, with no fictitious package-install instructions.
- Rewrite architecture/release/runner/onboarding documents around shared Skill/CLI/MCP/HTTP contracts; keep single-service SQLite and independent mailbox authorization.
- Clarify the current entry as obtaining operator-issued credentials, without implying self-service registration exists. No runtime/API/package version change.

## 1.1.0-alpha.3 — 2026-11-08

- Require recipient-observed RFC822 Message-ID, From and To with file receipts; reject omitted or mismatched evidence. Persist evidence with explicit participant-reported status.
- Acceptance checks latest input AND output receipt evidence, plus output/result version binding. Legacy timestamps alone are not full protocol evidence; accepted history remains readable and unchanged.
- Local receiver submits values parsed from the verified email and rejects an old server response that does not retain evidence. Reject duplicate identity headers.
- Add V03 incident report and staged deployment/V04 gates. Standard-tool failure must not silently fall back to generic receipt POSTs.

Breaking receipt contract: deploy server and clients together after handling active legacy orders. Published and deployed; existing three Agents and three accepted orders were checked against the backup. V04 content and participant-reported bidirectional mail bindings passed, with human-assisted orchestration after a model 402 interruption. No automatic migration of legacy receipts into verified evidence. See [V04 report](docs/validation-v04.md); persistent autonomous execution is still a beta gate.

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
