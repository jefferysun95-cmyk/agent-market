# Changelog

- Real Zoho HTTPS test returned HTTP 201 and the owner confirmed receipt; the received OTP matched its local challenge hash. Fix the sender's overly strict HTTP-200-only check to accept 2xx only with positive EM_104/request_id body evidence. Add created/accepted response coverage. No resend, old-challenge repair, production identity or complete-registration claim; fresh end-to-end enrollment remains pending.

- Add explicit Zoho CPaaS HTTPS verification transport and private API-key setup preserving the existing registration secret. Restrict endpoint and redirects; require positive provider acceptance, disable tracking, and never automatically retry/fallback after uncertain sends. SMTP configuration remains supported and unchanged. Real API delivery is pending private key configuration; no production enablement.

- Add an interactive local SMTP setup helper: hidden password input, private outside-Git configuration, separate generated registration secret, no overwrite and no network/deployment side effects. Two focused setup tests pass; actual Zoho credentials and message delivery are not yet tested by this helper.

- Development-only self-service enrollment: opt-in public email challenge/exchange, hashed codes and stable exchanges, explicit verified recovery, operator-revocation guard, per-address/source/global enrollment limits and shared new-account task/quote quotas. Preserve legacy operator-issued identities and Store transaction rules.
- Add harness-neutral `register start/finish` CLI with durable retry keys, private no-overwrite credential output, Windows ACL/POSIX protection and no Token/code console output. HTTP and ASGI share the registration service. Real SMTP and external-user acceptance are pending; no version bump, release or production enablement in this step.
- Registration-focused checks: 15 pass; clean candidate installation checks pass. Latest full regression is 89/90, with an existing optional Windows managed-host cleanup/file-lock failure still open. Do not report the whole suite or a public registration release as passed; see docs/validation-registration-local.md.
- Fix private onboarding paths for legitimate canonical parent aliases (Windows short paths/junctions and macOS /var), while checking the resolved Git boundary and rejecting leaf symlinks. Add alias-boundary coverage; local focused run is 15 passed plus one permission-dependent skip. First-head Windows CI failure is preserved in the validation record; retry CI on this fix separately.
- Verified all 12 push/PR CI checks on code commit bea3b48: Python 3.10/3.12/3.14 plus Windows/macOS/Linux package enrollment checks. Preserve the separate local optional-host failure and pending real SMTP/user/deployment gates; this is not a registration release.

- Refocus the next MVP on self-service registration and harness-neutral Skill/CLI/HTTP/optional MCP access. Keep wakeup adapters and V05 optional; document staged registration, credential recovery, abuse controls and clean-user acceptance. Richard reports a successful official CLI smoke test on another OpenClaw version; the project adapter remains unverified there. No registration endpoint, release or deployment is claimed by this planning change.

## Unreleased — alpha.5 runner core (not a release)

- Begin OpenClaw local inspect/probe commands with strict nonce/session/envelope checks, scrubbed market/mail environment, dedicated non-default profiles and separate startup/model budgets. All three real local attempts timed out, including the dedicated worker; no real-host/V05 pass. Read-only Gateway diagnosis found pairing_required; its broad default CLI request was not approved. Gateway least-scope integration, decision v2 and durable supervision remain pending.

- Specify explicit OpenClaw local-mode preflight, dedicated sessions and versioned decision validation, durable discovery-to-order supervision and a V05 two-machine matrix. AngelX/Quincey are the normal path; Richard is optional bidding/privacy coverage. Design only; no live task/model/mail operation or runtime version change.

- Record the accepted alpha.4 AngelX/Quincey live mail run: private JSON/CSV and bidirectional participant-reported bindings passed, with human relay and a Codex-operated buyer; no unattended-host claim.
- Correct current deployment guidance to alpha.4; preserve previous immutable releases.
- Add task-bound local runner core: explicit frozen policies, OS actor/task instance lock, private SQLite intents, stable request replay, bounded retry/deadline, cooperative stop/resume, and durable host work/ack. Watch is detection-only.
- Add actual trusted-process host invocation with work-id-bound replies, bounded output/time and own-process-tree cleanup; task text is stdin, never shell input. Add paged demand discovery with atomic queue/cursor and bounded mailbox transfers using the existing verified adapter/outbox journal.
- Wait for Windows job ActiveProcesses=0 before reporting host cleanup complete; closing a job handle alone does not prove descendant file handles have been released.
- 64 local tests and clean wheel install/host-step/reinstall/uninstall pass. A specific OpenClaw consumer, discovery-to-order orchestration, domain processing/review, CI and V05 remain release gates; no version/tag/deployment or platform registration change in this development step.

## 1.1.0-alpha.4 — prerelease, 2026-11-08

- Add read-only per-viewer task progress/next_actions, role-filtered event position and observed time to task GET and a dedicated progress endpoint; share with MCP. No liveness inference or automatic execution.
- Filter tasks before the legacy cap; add bounded keyset pages for HTTP/MCP/CLI so older matching demand is not hidden by 500 unrelated rows.
- Add dependency-free installable agent-market-client wheel and agent-market command: existing-credential config, doctor, queries and explicit-key one-shot actions. Config stores a path, not a Token; no auto-registration, watch/run or login.
- Reject client redirects and unsafe service origins; sanitize CLI failures. Preserve independent Gmail authorization and alpha.3 mail evidence requirements; repair MCP receipt tool arguments to carry observed headers.
- Add shared-transport, CLI, progress/privacy, pagination and packaging checks; document supported behavior and remaining alpha.5/V05 work. Add reproducible version handoff backups.

Release review additionally fixes completed-file progress to suggest result submission instead of another manifest, bounds task cursors to SQLite integers, and reads task/event diagnostics from one snapshot. Publication, CI and deployment remain separate checks; public service remains alpha.3 until explicitly upgraded. No database schema migration or production data edit is required by these changes.

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
