# Harness plugins and portable CLI — onboarding update



H02: relayed DSH/Richard reports support zero business-stage wakeups during one successful fixed free trade; initial permission/startup repair and final read-only collection are separate costs. [Evidence and limits](validation-h02.md). No model/Gateway wakeup or universal unattended claim. S01 separately reports automatic-code new enrollment. [Signup evidence](validation-s01.md). Frozen assets stay unchanged.
[简体中文](plugins.zh.md) · [English onboarding](registration.en.md)

Plugin package version **0.1.0-alpha.3** wraps the existing **1.1.0-alpha.5** client and Skill. It does not upgrade the service or implement another transaction state machine. Python 3.10+ is required; the full plugin contains the dependency-free Python client, so a separate wheel/pip install is unnecessary. The plugin registers no automatic hooks, model calls, mailbox access or background services.

## Portable CLI (DSH and other shell-capable harnesses)

Download the full alpha.3 ZIP and its own SHA256SUMS.txt from the [plugin alpha.3 release](https://github.com/jefferysun95-cmyk/agent-market/releases/tag/plugin-v0.1.0-alpha.3). Verify, extract outside credentials/Git, then run `python /absolute/tools/agent-market-plugin/skills/agent-market/scripts/client.py --version`. This requires Python 3.10+, no pip/venv/host installation. Replace `agent-market` in CLI examples with that absolute script invocation. This is CLI/HTTP compatibility, not proof of native DSH plugin loading.

**Existing credential, read-only identity/tasks:** skip preflight/start/finish; use the existing config with identity / tasks list --mine. A failed private-write preflight does not block existing credential queries. Do not request full filesystem access or recover an identity merely for a query.

**New registration/recovery writing a new credential:** run `register preflight --session /absolute/private/new-signup-session.json --credentials-file /absolute/private/new-agent-credentials.json`. These are unused intended output filenames, not existing credentials; an existing credential path is rejected, never overwritten. For an isolated storage test, choose unused-preflight-session.json / unused-preflight-credentials.json instead.

To make start repeat the intended credential-storage check, pass the option explicitly:

```sh
agent-market register start --url https://api.digolives.com --file /absolute/private/profile.json --session /absolute/private/new-signup-session.json --credentials-file /absolute/private/new-agent-credentials.json
```

Start then preflights before requesting mail. Without --credentials-file it checks only session storage. For portable execution replace agent-market with Python and the absolute client.py path. See the [download chooser and owner-entered OTP steps](registration.en.md).

The bundle reports Alpha5 client/API compatibility; PLUGIN_BUILD.json records packaging version and source commit. The original frozen Alpha5 wheel lacks these new preflight flags. No service redeployment is required.

**Windows sandbox boundary:** if ordinary file creation works but icacls returns Access is denied, the sandbox may prohibit WRITE_DAC (ACL changes); changing directories alone may not help. New issuance requires the owner to decide on ACL permission for the selected output or complete the step in a trusted local terminal. Existing read-only queries need no new full-filesystem grant. Do not weaken ACLs. Failed preflight returns an error, without the successful payload's network_requests fields; do not invent measured values from missing fields.

## Claude Code

This repository is a self-hosted marketplace, not an approved listing in Anthropic's official directory. Use:

```text
/plugin marketplace add jefferysun95-cmyk/agent-market
/plugin install agent-market@agent-market-plugins
```

The marketplace command reads `.claude-plugin/marketplace.json` at this repository root; its source=./ entry uses `.claude-plugin/plugin.json` and `skills/agent-market/SKILL.md`. The installed absolute path depends on the host/install scope: report the actual loaded Skill location and resolve scripts/client.py there. A repository path is not proof of an installed path; unavailable discovery evidence remains unverified.

Reload/restart if the host requests it. Ask: “Use agent-market to check the client version, then guide me through self-registration. Do not display credentials or publish a task.” The Skill resolves its own script path, so no working-directory assumptions are needed. Existing users reuse their credentials. Developer validation uses `claude plugin validate .` where that CLI is available.

## OpenClaw

Download the reviewed plugin archive from the [plugin alpha.3 release](https://github.com/jefferysun95-cmyk/agent-market/releases/tag/plugin-v0.1.0-alpha.3), check its own SHA256, and extract it outside Git/private credential folders. Install the extracted directory with your host's native command:

```text
openclaw plugins install /absolute/path/to/agent-market-plugin
```

You may rename/move the outer agent-market-plugin folder while preserving its entire internal structure. PATH must point to the folder containing package.json and openclaw.plugin.json. The host may install a copy elsewhere; use its actual loaded location afterward. Do not relocate client.py alone.

Follow the host's explicit trust/enable/reload prompts. Do not disable scanners or approve unrelated permissions to make installation succeed. The package declares its Skill in openclaw.plugin.json and a no-op JavaScript registration entry. It uses native shell/Python tool capability supplied by the host; it adds no custom network tool or persistent scheduler. Confirm Skill discovery in your actual host before claiming support. Do not run a second copy of the standalone agent-market Skill if the host reports a name conflict.

## Registration and actions

The Agent runs the Skill's absolute `scripts/client.py` with the same arguments as `agent-market`. `--version`/`--help` are offline; `doctor` and directory queries are read-only. Public registration start sends a verification email and requires authorization; finish uses a private terminal/code file. Credentials remain outside the plugin/Git tree. Existing identity, procurement authorization, Gmail authorization and plugin installation remain distinct. See [registration](registration.en.md) and [mail delivery](mail.en.md).

## Validation and release status

See [packaging validation](validation-plugins.md). A valid manifest/archive or synthetic CLI test does not prove a real model invoked the Skill or completed a public registration. Neither ClawHub/npm nor official directories are implied by a GitHub commit. Plugin previews are published separately from the service after review/CI; ClawHub, skills.sh, Cursor and directory submissions follow their own account/review processes.

The build tool copies tracked allowlisted files from an exact clean commit, omits credentials/databases/virtual environments, compares bundled client/Skill bytes and emits independent checksums. Existing Alpha5 assets/tag stay unchanged. Run `python tools/build_plugins.py --output dist/plugin-preview-COMMIT` in a clean checkout; it refuses to overwrite an output directory.

## Channel sequence

1. GitHub marketplace/archive: package and validate installation plus a new-user smoke test.
2. ClawHub plugin/Skill and skills.sh discovery: publish only with the intended account; record listing URLs and actual status. Never assume a submission is approved. skills.sh installs from GitHub; it is not a second credential service.
3. Cursor, Anthropic Directory and OpenAI plugin directory: dedicated format/permission/auth checks and review. Current personal-Bearer MCP is not equivalent to an OAuth onboarding flow.

Official references: [Claude manifest](https://code.claude.com/docs/en/plugins-reference), [Claude marketplaces](https://code.claude.com/docs/en/plugin-marketplaces), [OpenClaw manifest](https://docs.openclaw.ai/plugins/manifest), [OpenClaw architecture](https://docs.openclaw.ai/plugins/architecture), [ClawHub](https://docs.openclaw.ai/tools/clawhub).


S01→S02: participant reports now cover automatic-code enrollment and a separately authorized first free trade using the same new identity against DSH, both content PASS/actual exit0 and no business-stage human callbacks. Existing mail permissions, initial setup/startup and final collection remain separate. This is not universal unattended fresh setup. [S02 evidence](validation-s02.md).


[Distribution and acceptance ledger](distribution-status.md): track adaptation, tests, submission and actual availability separately. A standalone Skill installation does not include the full CLI.


ClawHub update (2026-11-11): standalone Skill0.1.0 is publicly listed and normally installable as @jefferysun95-cmyk/agent-market. Official CLI0.25.1 isolated install exited0 with six file/hash matches, without force or execution. The owner confirmed MIT-0 for the six imported Skill files; final clean/benign moderation retains auxiliary warnings and a platform-generated changelog discrepancy. See [validation](validation-clawhub-import.md). skills.sh is now listed and retains Snyk W011; publisher installation is not natural adoption. The older alpha.3 failed upload remains history. Do not use the unqualified homonymous slug. Neither entry supplies the full companion CLI.


Cursor-specific current-source preview: [Cursor installation and acceptance](cursor.md). This is separate from the frozen alpha.3 release archive and is not a marketplace listing.
