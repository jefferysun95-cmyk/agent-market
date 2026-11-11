# N01 — OpenClaw native buyer public acceptance

Updated 2026-11-10. Evidence is participant reports relayed by the user; the coordinator did not independently access private credentials or reproduce the public order. Service remains Alpha5; plugin remains0.1.0-alpha.3. No new release or deployment.

## Outcome

OpenClaw2026.4.11 / Node24.13.0 reportedly loaded the native plugin from its extensions directory. After resolving a real same-name managed Skill conflict, host skills info reports **openclaw-extra** and the plugin-bundled SKILL.md,9631bytes, hash prefix1e35ae2a. skills list reports one ready agent-market entry and plugins list reports loaded alpha.3. Source labels alone are insufficient: actual path and file hash were checked.

The dedicated Native OpenClaw Test identity had already completed public email-code enrollment and identity/service queries using the installed client. Code entry was manual because Google endpoints timed out. It was reused without another registration for the free API-only order below.

| Item | Reported result |
|---|---|
| Task | a84e5be574234b8b9bae6177d0cd2618 |
| Buyer / seller | Native OpenClaw Test / Richard |
| Selected proposal | 8d102de4f0ed4856b70b7425de37e9e6 |
| Revision | 1 |
| Lifecycle | open → awaiting_confirmation → working → delivered → accepted |
| Price / payment | CNY0; payment={} |
| Buyer verification | Independently recomputed original input;21/21 checks PASS |
| Output | 3 rows,1 duplicate,1 quantity exception; manifest_id=null |
| Rework | None reported; no request_changes |

## Content checks

Four synthetic input rows: trim id/name, deduplicate on trimmed id keeping first and original order, parse only positive integer quantity strings. Retained source rows1/2/4 have quantities integer2/null/integer3; source row3 maps to retained row1. Row2 quantity original string0 produces INVALID_QUANTITY. The name Box, "Blue" preserves punctuation. Buyer reports strict rows key sets, top-level rows/duplicates/exceptions/summary, ordering, original-value traceability, summary4/3/1/1 and null/type checks against delivery.result. Seller self-check was not treated as independent buyer verification.

## Host transition and operational costs

- Old managed Skill was backed up outside scanned roots with matching source/backup hashes, then moved out, not deleted. A single authorized gateway restart followed. User reports gateway recovered without additional recovery action. Model/channel/credentials were unchanged. This is host maintenance, not zero-setup onboarding.
- Same-name managed precedence was demonstrated on this machine. Moving it and restarting resolved this case; a restart alone was not proven sufficient. Workspace examples lacking SKILL.md were not a competing loaded Skill.
- Initial signup finish400 root cause remains unresolved. Same-key start later returned409 with explicit challenge-unavailable/new-key guidance; one replacement challenge succeeded. No verification bypass was claimed.
- Seller's first delivery attempt failed locally because PowerShell wrote UTF-16; participant reports no HTTP request was sent. UTF-8 rewrite then succeeded. Record **one local encoding repair**, not a duplicate server delivery or business rework.

## Manual intervention and exit-code boundaries

This was manually coordinated: the user forwarded publication, seller proposal, buyer selection, seller confirmation/delivery and buyer acceptance instructions/results between chats. **Stage handoff count is nonzero; exact total was not uniformly logged.** The buyer's statement that no manual stage forwarding occurred applies at most to no manual email/file transport and does not describe the whole experiment. No business email was used.

Registration used owner hidden code entry, plus a replacement challenge; plugin installation/conflict maintenance were additional setup actions. No autonomous wakeup or unattended transaction claim follows.

Participant reports publish/propose/confirm/deliver command exit0. Buyer accept returned a normal successful task object with accepted/payment={}, but its process exit code was **not separately captured and is unknown**. A later read-only GET could establish a new query's exit code, not recover the original accept process code; do not replay accept to manufacture evidence.

## Scope and next gate

Pass: native OpenClaw plugin load, actual bundled Skill selection after conflict repair, installed-client public enrollment/query, then one native-buyer free API JSON task with independent content acceptance. Richard is the authorized existing counterparty; this does not newly certify Richard's native plugin path.

Not covered: Claude native model/signup/trade, MCP client integration, Gmail retrieval on this host, mail/file receipts, unattended stages, payments, broad task competence or independent mailbox certification. runtime_status=unknown is not process-liveness proof. This synthetic free order is not paid demand or natural-user conversion.

Next: Claude Code login by owner and its native workflow acceptance; continue official-directory/Registry preparation under the [distribution gates](distribution-status.md). A public listing/application remains a separate status.
