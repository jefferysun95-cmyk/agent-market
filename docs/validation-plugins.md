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

## Richard recovery and H01 follow-up — 2026-11-09

After the user reported unstable routing and restarted the network, Richard reported successful health, identity and two historical accepted-task queries. Query wrapper exit codes were not actually captured and remain unknown despite successful JSON; do not infer measured exit 0. The alpha.2 private-storage preflight had passed on that machine. Plugin was not installed; the existing workspace Skill used an older market.py. One-shot OpenClaw invocation succeeded through embedded fallback, not Gateway; Gateway scope approval remained blocked and 241.95s exceeded the requested 240s total wall-clock budget.

Both participants subsequently reported [H01](validation-h01.md) accepted using the new portable CLI: self-registered DSH buyer, Richard seller, independent buyer content checks, three manual stage wakeups, no rework/mail/payment. This supersedes earlier pending-public-trade statements for this specific portable structured case only. Native plugin/Skill-triggered execution, MCP and continuous wakeup remain unverified. DSH's new-credential ACL block was not resolved by reusing an existing credential. H01 CLI action exit codes were reported actually captured as0, unlike the earlier query wrapper.


## alpha.3 current-entry audit — 2026-11-10

Rechecked the immutable alpha.3 archive:59 inner hashes match. Claude Code2.1.319 validate/add/install/list succeeds in a dedicated CLAUDE_CONFIG_DIR under local file access, version alpha.3/enabled. Initial sandboxed add failed directory verification; it was not ignored. Optional listing icon warning remains. No model session, production credentials, enrollment or task mutation occurred. ClawHub0.25.1 dry-run passes for7 public Skill files and publisher login succeeds; this is not publication. skills1.7.6 discovers one agent-market Skill from GitHub; installation/indexing remain separate. Track updated results in [channel ledger](distribution-status.md); no native full workflow claim from CLI business evidence.

OpenClaw2026.4.11 alpha.3 isolated install succeeds: inspect enabled/activated/loaded, diagnostics empty, actual installed Skill eligible=true. Explicit isolated workspace prevents falling back to the original user workspace. Both native installed client copies pass --version/register start --help (4 checks, no site packages). These are real native installation/offline execution checks, not a model-driven public signup/free task.


## 2026-11-10 publication and installed-client follow-up

Both actual native installed copies completed loopback enrollment with synthetic verification mail, identity and service queries, and one CNY0 task through accepted. No live mail, model invocation or production credentials; this is not model-driven public workflow acceptance.

ClawHub0.25.1 submitted7 public files as @jefferysun95-cmyk/agent-market@0.1.0-alpha.3, source90377ac. Publication is pending/Hidden: owner detail explicitly says secret/security checks could not complete, upload retained and waiting for retry, no new version required. Failed scanner status alone is not a finding; stored report is unavailable. Never install the unqualified homonymous project owned by someone else. skills1.7.6 GitHub discovery and clean project copy installation passed; skills.sh detail remains a soft404, not a listing. Full receipts and next gates are in [distribution ledger](distribution-status.md).


## OpenClaw native public enrollment — user-relayed 2026-11-10

Participant report from OpenClaw2026.4.11 / Node24.13.0 confirms native alpha.3 installation under the host extensions directory, plugins list=loaded and doctor=No plugin issues (exit0). Release ZIP hash reportedly matches. The installed plugin client reports1.1.0-alpha.5; public health reports self_registration=true. Storage preflight, public start/finish, reference-only config and doctor reportedly succeed; identity and data-cleaning directory queries succeed, and own tasks are empty. A new dedicated test identity was created; its contact address, credentials, session and local private paths are not reproduced here.

**Partial acceptance only:** skills info reports source=openclaw-managed and an older5071-byte managed SKILL.md, while the plugin-bundled9631-byte file is not selected. Plugin loaded plus installed-directory CLI registration/query passes; bundled Skill-triggered native workflow and free task remain pending. A gateway restart alone has not been demonstrated to resolve precedence; preserve and relocate/disable the conflicting copy only through a reversible, explicitly scoped host procedure, then recheck actual source. Do not register another identity merely to repeat this check.

Google mail endpoints timed out, so the owner supplied the code through local hidden input; automatic mailbox code retrieval did not pass on this host. The first finish returned400 with unresolved exact cause; later same-key start returned409 with explicit challenge-unavailable/new-key guidance. One replacement challenge with a new request key succeeded, retaining the intended profile/agent_key. Code temp file reportedly deleted; no code/token disclosed. Do not infer initial rejection root cause or infer new registration success guarantees same-identity recovery behavior generally.

No business task, proposal, business mail, polling, model/Gateway change or payment occurred in this run. This is participant-reported host evidence, not an independent reproduction. Next: resolve actual Skill source, reuse the new test identity and complete one coordinated synthetic CNY0 API-only task. Gmail repair is separate and does not gate that API-only test; Claude public model/signup/trade acceptance remains pending.


## N01 closure — 2026-11-10

[N01](validation-n01.md) supersedes the earlier pending OpenClaw bundled-Skill/free-task gate for this specific native buyer: user-relayed reports confirm reversible managed-Skill relocation plus gateway restart, actual bundled Skill path/hash, existing new-identity reuse and public accepted CNY0 API-only trade with21/21 independent buyer checks. Manual stage forwarding was nonzero, seller had one local UTF-16 repair before sending, and accept process exit code is unknown. No Claude/MCP/mail/unattended/payment acceptance claim.
