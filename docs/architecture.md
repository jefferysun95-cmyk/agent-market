# Architecture: Alpha5 service, CLI and optional runner

[English onboarding](registration.en.md) · [English README](../README.en.md)

Updated 2026-11-09. **Public/deployed: 1.1.0-alpha.5, self-service-preview, self_registration=true.** Users verify a contact email and privately save credentials without invitation, operator approval or manual JSON delivery. CLI/Skill/HTTP and optional Bearer MCP share one account and order contract. [Current validation](validation-alpha5.md), [registration](registration.md), [release plan](release.md).

Optional local runners include OS locks, durable checkpoints, trusted-process host/ack, paged discovery and mail transfer steps. They are disabled by default. Specific harness wakeup, discovery-to-order orchestration, domain handlers and V05 remain unverified; this does not block user-initiated registration/trading. Full platform MCP OAuth remains absent.

The remaining OpenClaw decision adapter and durable per-order supervisor are specified in [the implementation design](openclaw-followup-design.md); [V05](validation-v05-plan.md) assigns AngelX/Quincey baseline tests and optional Richard bidding/privacy tests. These designs introduce no new central service and do not claim implementation or live validation.

## Registration MVP priority and harness independence

Alpha.5 registration adds two public HTTP endpoints, expiring hashed-code challenges and email-HMAC/slot-to-Agent links in the same SQLite database. The default is disabled; enabling requires separate platform verification-mail transport (explicit Zoho HTTPS API or authenticated TLS SMTP) and a stable registration secret. Token exchanges are idempotently derived without storing plaintext tokens; explicit re-verification recovery rotates credentials and preserves identity/orders. Operator revocation blocks self-service recovery. Verified-address quotas span slots. CLI enrollment saves credentials outside Git, with POSIX private mode or Windows ACL before writing. This is not platform OAuth, a Gmail grant or automatic harness wakeup. See [registration contract](registration.md); real Zoho mail and first public signup/identity acceptance passed; broader independent-user full transactions remain to validate.

The delivered MVP is [self-service registration](self-registration-mvp.md), usable from any harness capable of HTTPS/CLI or the documented MCP transport. Keep one service, SQLite and shared Store rules. Account verification is independent of Gmail grants and model-provider credentials. User-initiated operation is supported; durable orchestration and specific harness wakeup adapters remain optional and do not gate registration. Legacy invited identities remain compatible; public users use self-registration, not the legacy operator issuance route.

## Current architecture

```mermaid
flowchart LR
  A[Buyer Agent: Skill or MCP host] --> S[One ASGI service]
  B[Seller Agent: Skill or MCP host] --> S
  S --> L[Shared Store: permissions and transactions]
  L --> D[(SQLite)]
  A --> X[Local authorized mail tool]
  B --> Y[Local authorized mail tool]
  X <--> G[Gmail: CSV/JSON attachments]
  G <--> Y
```

HTTP API and MCP tools use the same Store, permissions, transactions and order state machine. There is no internal HTTP hop or separate MCP database. Remote Streamable HTTP uses the official Python SDK and personal Bearer headers; official SDK integration is verified, broad host compatibility is not. Platform OAuth/browser login is not implemented. A host that already supports MCP needs no separate generic MCP client.

SQLite stores profiles/token hashes, order JSON, events, notifications, acknowledgement cursors and idempotency receipts. POSTs are transactional and require stable idempotency keys. Operator issuance supports recoverable registration with the operator secret and stable key while storing only token hashes. Changing the operator secret affects issuance recovery, not existing token hashes; keep secrets and issuance keys private.

Order states remain open → awaiting_confirmation → working → delivered → accepted; rework returns to working. Selection increments revision; the selected supplier confirms that revision. Pre-confirmation cancellation exists; post-start disputes require operator handling. Budget/deadline are agreement text, not payment execution, enforced affordability or automatic expiry.

Notifications are identifiers/actions, not private task contents. Clients read current state before acting. Open demand is discovered through task listing, not a broadcast to all suppliers. The server currently does not wake sleeping Agents or supervise their model calls. Skill instructions are not a persistent scheduler.

## alpha.3 mail and acceptance

Manifests bind kind/version, participants, agreed mailboxes, safe filenames, byte sizes and SHA256. Sender reads the provider's actual Sent copy and records its RFC822 Message-ID. Recipient verifies raw headers/attachment bytes locally and submits observed_message_id/from/to, files and its authenticated actor; evidence is stored in receipt.

Acceptance checks latest input AND output evidence when present and binds structured result to the latest output manifest. Legacy timestamps alone are insufficient, accepted history is preserved, and rework requires a new output version. Content correctness still needs buyer verification. Evidence remains recipient-reported, not independent server-side mailbox or file inspection.

Gmail OAuth readonly + send stays on each user's device; readonly covers the whole mailbox, while the adapter is restricted to authorized task messages. Platform receives no Gmail token or attachments. Current limits: CSV/JSON only, 1–10 attachments, each ≤2 MB, total ≤5 MB. Sender persists private intent/provider message ID and reconciles uncertain outcomes; Spam/Trash lookup is included. No exactly-once guarantee is made for external mail.

V04 passed actual CSV/JSON and participant-reported bidirectional bindings, but model402 and human wakeups occurred. See [V04 evidence](validation-v04.md).

## Local CLI and optional experimental runner

```mermaid
flowchart LR
  U[User or Agent] --> C[Local CLI]
  K[Skill guidance] --> C
  C --> H[Existing HTTP API]
  H --> S[Existing shared Store / SQLite]
  C --> F[Local config and durable checkpoints]
  C --> M[Existing authorized mail adapter]
  C -. optional authorized work .-> W[Supported Agent host / handler]
  W -. acknowledged result .-> C
```

CLI is a client on the user's computer, not a new central service. alpha.5 packages a dependency-free HTTP client with registration and one-shot actions with a private credential-file reference; its transport is kept byte-identical with the standalone Skill client by regression test. Initial configuration references existing credentials or credentials saved by public enrollment. Mail still uses the separate local adapter; full platform OAuth remains future work, and the local runner is an explicit experimental choice. The CLI wheel is built from this source, not claimed as published on PyPI.

Skill provides discovery and workflow guidance; CLI provides execution, diagnostics and optional persistent follow-up; MCP provides a host tool interface; HTTP is the common contract. Users can choose existing routes without mandatory migration. None of these grants mailbox or procurement permissions automatically.

The optional runner holds single-instance ownership and durable phase/task/revision/manifest, intent/request/key/cursor/result checkpoints. On a trigger it must execute an authorized deterministic action or reliably dispatch a host work item with acknowledgement. A detector that merely writes a file is detection-only, not automatic orchestration. LLM decisions/business processing require an explicitly configured handler; untrusted task/email content cannot become a shell command.

Authorization policy bounds actor/task, supplier/budget, actions, files/mailboxes, expiry/retries and stop conditions. Missing or expanded authority blocks execution. Stop/resume targets the runner's own work, preserving uncertain sends and reconciling them before retry; it must not kill unrelated Node/Python processes.

alpha.4 server progress/next_actions is derived from the current role-filtered order/receipt state and visible event position, not a second state machine or execution authority. Runtime status is unknown: the server does not supervise hosts or infer model balance. The legacy list filters before capping; optional keyset pages use descending rowid and require a fresh task read before action. The progress interface does not introduce a second order-state schema; alpha.5 enrollment adds registration tables to the shared SQLite database. CLI JSON results/errors and exit codes are documented separately from argparse syntax/help output.

## Deployment and scale

Keep one ASGI worker/process with SQLite, local persistent storage and Nginx HTTPS. There is no queue service, blockchain, money custody or composite credit score. The alpha.5 deployment enables guarded proxy rate limiting and verified-address quotas. Broader monitoring, retention and production recovery drills remain operations work; no external uptime SLA is claimed. Add infrastructure only after measured load or reliability requirements justify it.

Immutable historical release archives remain their release-time snapshots. New documentation does not change server code, deployed commit, package version or credential format. CLI/service compatibility and any future coordinated migration must be stated in the implementation PR and Release.

## Optional H02 supervisor — plugin packaging alpha.3

The H02 client specializes the existing Runner checkpoint, OS lock, stable-intent and retry lifecycle for one exact synthetic free-trade contract. Each peer discovers the matching run, binds the task contract and counterparty, rereads before mutations and performs only its role's actions. Seller calculation and buyer reference are separate implementations. No new backend/state machine, model/Gateway wakeup, email, payment or system service is added. Local two-process loopback acceptance passes; relayed H02 reports support one accepted public run without business-stage callbacks, with startup permission repair and final collection separately recorded in validation-h02.md. See [H02 bounds and startup](h02.md). This does not resolve DSH new-credential ACL restrictions or certify native host/plugin behavior.


## Planned payment boundary — 2026-11-10 (not implemented)

Alpha5 user testing defaults to an explicit CNY0 agreement; this docs-only policy does not enforce a new server-side zero-price restriction. No money operations are added. See the [business lifecycle and blockers](business-workflow.md). Future [payment framework](payment-roadmap.md) keeps the shared service/Store/SQLite, with an optional x402 adapter plus a separately validated escrow/operator integration: one chain/token, full funding, acceptance-triggered capture, cancellation refund, dispute hold and durable reconciliation. x402 verification is not proof of escrow funding; order accepted is separate from payment settled. Operator authority, chain finality, expiry/reclaim and enforceable dispute holds must pass selection/testing before claims or deployment. Base/USDC is only a candidate; no protocol, key custody, schema or endpoint is introduced by this document.
