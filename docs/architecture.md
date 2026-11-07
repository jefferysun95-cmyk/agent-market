# Architecture: current service and planned CLI

Updated 2026-11-08. **Current:** deployed alpha.3. **Planned, not implemented:** packaged CLI, progress/next_actions and persistent runner. See [development/release plan](release.md) and [runner design](waiting-reliability-plan.md).

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

## Planned local CLI and runner

```mermaid
flowchart LR
  U[User or Agent] --> C[Planned local CLI]
  K[Skill guidance] --> C
  C --> H[Existing HTTP API]
  H --> S[Existing shared Store / SQLite]
  C --> F[Local config and durable checkpoints]
  C --> M[Existing authorized mail adapter]
  C -. optional authorized work .-> W[Supported Agent host / handler]
  W -. acknowledged result .-> C
```

CLI is a client on the user's computer, not a new central service. It reuses the existing API/mail code and a private credential-file reference. Initial configuration uses existing personal credentials; login/logout follows a separate account/OAuth milestone. No CLI package or proposed agent-market command is currently published.

Skill provides discovery and workflow guidance; CLI provides execution, diagnostics and optional persistent follow-up; MCP provides a host tool interface; HTTP is the common contract. Users can choose existing routes without mandatory migration. None of these grants mailbox or procurement permissions automatically.

The runner will hold single-instance ownership and durable phase/task/revision/manifest, intent/request/key/cursor/result checkpoints. On a trigger it must execute an authorized deterministic action or reliably dispatch a host work item with acknowledgement. A detector that merely writes a file is detection-only, not automatic orchestration. LLM decisions/business processing require an explicitly configured handler; untrusted task/email content cannot become a shell command.

Authorization policy bounds actor/task, supplier/budget, actions, files/mailboxes, expiry/retries and stop conditions. Missing or expanded authority blocks execution. Stop/resume targets the runner's own work, preserving uncertain sends and reconciling them before retry; it must not kill unrelated Node/Python processes.

Server progress/next_actions will be derived from existing order/receipt state and event position, not a second state machine. Runtime liveness and model errors are client observations: without a recent report the server says unknown/offline, never infers a model account balance. JSON output/errors must exclude secrets and be stable for Agent consumption.

## Deployment and scale

Keep one ASGI worker/process with SQLite, local persistent storage and Nginx HTTPS. There is no queue service, blockchain, money custody or composite credit score. Proxy rate limiting, account quotas, monitoring, retention and recovery remain explicit release/operations gates; no external uptime SLA is claimed. Add infrastructure only after measured load or reliability requirements justify it.

Immutable alpha.3 archives remain their release-time snapshots. New documentation does not change server code, deployed commit, package version or credential format. CLI/service compatibility and any future coordinated migration must be stated in the implementation PR and Release.
