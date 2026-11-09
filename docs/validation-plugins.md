# Plugin packaging validation — 0.1.0-alpha.1

Date: 2026-11-09. This packaging preview wraps the running 1.1.0-alpha.5 client without changing its service version. No production registration, mail send, task or payment was executed in these checks.

## Implemented and checked

- Shared canonical Skill and Python CLI entry; manifests for Claude Code marketplace/plugin and OpenClaw. The plugin has no background hooks/services or automatic signup.
- Four isolated tests: manifest wiring; copied plugin outside Git under a path with spaces using Python without site packages; actionable missing-bundle failure; authenticated identity against a temporary loopback server with synthetic credentials and no token output.
- Full regression before the final identity test: 105 tests completed, one directory-symlink permission skip. The final plugin-specific suite includes the added identity case; CI on the final commit is tracked separately.
- npm dry-run whitelist: 25 files, no Python caches. Node imported the no-op OpenClaw registration entry successfully.
- Claude Code **2.1.319** official `plugin validate .`: passed. Optional listing-icon advice remains; this is not official directory approval. In an isolated CLAUDE_CONFIG_DIR, `plugin marketplace add ./` and `plugin install agent-market@agent-market-plugins` succeeded; the installed copy returned client version 1.1.0-alpha.5. No model/auth session was started. Its install metadata reflected the precommit source HEAD; final GitHub commit packaging/CI are checked separately, not inferred from that value.
- OpenClaw **2026.4.11 (769908e)** installed the local npm archive in isolated OPENCLAW_STATE_DIR/OPENCLAW_CONFIG_PATH. Native inspect reported enabled/activated/status=loaded; skills info resolved the installed Skill and eligible=true. Installed client returned 1.1.0-alpha.5. The first inspection exposed the host's default workspace path; the temporary config was then made explicit with its own workspace and plugins.allow. Original Agent configuration was not modified; no Gateway/model was started.

## Remaining gates

Native installation is not model-driven workflow acceptance. A real Agent still needs to invoke the installed Skill, complete an explicitly authorized new registration/identity check and a free task. Broader host versions, public ClawHub/npm listings, skills.sh indexing and official directory approvals are pending; no listing URLs are claimed. Python 3.10+ and host shell permission remain prerequisites. Gmail authorization is separate.

GitHub delivery: reviewed PR/CI, commit-pinned plugin ZIP and independent checksums; existing service tag/assets unchanged. A versioned handoff backup with hash and offline-restore verification is required. [Installation](plugins.md) · [中文](plugins.zh.md).

## 0.1.0-alpha.2 onboarding update — 2026-11-09

Six new isolated preflight tests check both private output directories and probe cleanup, no credential overwrite, ACL denial before mail, finish denial before OTP entry, Windows ACL failure cleanup, and Git-path rejection. The copied no-site-packages portable client now runs the actual preflight command; manifest versions must agree. Recovery regression confirms start/wrong codes preserve the old token until a successful finish rotates it.

Local full suite: 112 tests, OK (one Windows directory-symlink permission skip). Synthetic demo passes; Node syntax check and npm dry-run allowlist pass (54 files; no caches). Claude Code 2.1.319 native manifest validator passes; optional listing-icon warning remains. Native OpenClaw installation evidence above is from alpha.1, not rerun for alpha.2. Final PR CI and commit-pinned archive verification are checked at publication.

DSH external feedback is user-reported evidence: public CLI signup/identity/directory queries worked, local synthetic trade worked, but native DSH plugin/automatic Skill loading/MCP/public trade were not verified. At publication, the updated bundle's actual DSH retest was pending; see the later external report below. Reuse that existing identity; run offline preflight with unused private filenames and then read-only identity checks. Do not create a second public identity for an installation check. No new live email or production trade was requested by this repair.

Packaging version/build commit identify the enhancement while API/client compatibility stays Alpha5. Frozen service/client release assets and running backend are unchanged. The current installation and registration guides supersede ambiguous supplement instructions; historical reports above retain their original context.

## DSH external retest reported by user — 2026-11-09

Evidence source: the user relayed DSH's report; the maintainer did not directly observe that machine. Harness Python 3.12.14 was used, not the older system interpreter. The reported ZIP SHA256 a2e9a41fe3d6437e05ecc1cd5931214c451685e47d976d035cd8f3b4de593ae6 matches the published alpha.2 archive; the reporter checked all 54 inner hashes and source commit 838776f. No pip/venv was needed; client version returned Alpha5. Existing identity and empty own-task query succeeded; no new signup, mail, task or polling was performed.

**Private-write preflight remains environment-blocked, not passed.** The reporter could create an ordinary file but icacls returned Access is denied (exit 5), consistent with sandbox WRITE_DAC denial. Requested target files remained absent and probe cleanup was reported successful. The error response has no successful payload metrics: network_requests=0 was not independently measured from that response, and no credential issuance was observed. Do not relabel this as successful sandbox onboarding or bypass ACLs.

This does not block existing credential read-only use, which requires no issuance preflight. A separate new-registration/recovery write check would require the owner to choose scoped permission or a trusted local terminal. No blanket full-filesystem permission is required for identity queries. Native DSH plugin loading, automatic Skill discovery, MCP and a public trade remain unverified. Richard/OpenClaw's current retest is pending; earlier one-shot model invocation is separate evidence.

Documentation clarifies unused preflight filenames/existing-file rejection, exact start --credentials-file behavior, read-only applicability, DACL restrictions, marketplace manifest versus installed Skill path, and renaming an extracted root while keeping its structure. This follow-up is documentation only: no application/package version bump or replacement of frozen archives; use main-branch guides for these clarifications.
