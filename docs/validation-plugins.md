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
