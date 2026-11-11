# Cursor native preview acceptance — 2026-11-11

Service/client: 1.1.0-alpha.5. Source preview: 69ec0381ea48602dcc342be61fcd3137b57d4aa7. The frozen plugin-v0.1.0-alpha.3 Release is unchanged and does not include the Cursor manifest.

## Verified on the actual host

- Owner installed and signed in to Cursor 3.29.15 (86776fcb52ca505783155631089b65d646f9b030), Windows x64. Official installer signature Valid, Anysphere, Inc.
- Reviewed current source copied to a new local plugin directory; 72 package files matched. Customize displayed Agent Market, Local, version 0.1.0-alpha.3 and one Skill. Opening the Skill showed its actual source under `.cursor/plugins/local/agent-market/skills/agent-market/SKILL.md`.
- In a dedicated test workspace/chat the Cursor model read that bundled Skill and ran its portable client. Client version 1.1.0-alpha.5, actual exit 0. One unauthenticated health GET with TLS certificate/hostname checks and a 15-second timeout returned HTTP 200, self_registration true, actual exit 0. A preceding local quoting error exited 1 before HTTP and was corrected.
- A dedicated new signup passed storage preflight and one register start through the native model. First contact address hit HTTP 429 at finish; Alpha5 source has a maximum-three-slots-per-address branch, but the client masked the raw server reason. No credential was retained for that attempt. Owner selected another address; a new independent session passed preflight/start and owner-local hidden finish generated a new private credential. Temporary code files were removed.

## Remaining / not claimed

The Cursor model started preparing explicit new-config identity/service/task queries, then the host displayed “You've hit your usage limit”. Those queries and a native free transaction remain unverified. Credential-file existence is not an independent identity-query result. No Pro purchase, plan/model changes or automated retries were made. Resume with this same new identity, not a fresh registration.

No business mail, payment, persistent scanner or unattended trading was tested here. A generic “Try in Chat” attempt was stopped and excluded: its tool label mentioned local config; its access extent was not independently certified. Only the later bounded acceptance chat supports the above results.

## Publisher application

Public fields were prepared at the official publisher page with the repository, English website and the above limitations. The owner completed final submission on 2026-11-11. The authenticated official page displayed **“Thanks for applying”** and **“We've received your submission”**; the coordinator independently re-read that success state and retained a local screenshot. No application number or review deadline was displayed. Status is **submitted / awaiting review**, not approved or publicly installable. No duplicate application was submitted by the coordinator. New square SVG at `assets/agent-market-logo.svg` is a listing asset only; technical IDs and runtime are unchanged. Future display-brand work remains separately planned.

Private profiles/sessions/credentials, hidden input, account content and test-machine paths are excluded from the public evidence and developer backup.