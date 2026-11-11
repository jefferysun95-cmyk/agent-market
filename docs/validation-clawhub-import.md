# ClawHub GitHub import and clean install — 2026-11-11

## Actual outcome

**Public listing and normal clean-directory installation passed.** Publisher: `jefferysun95-cmyk`; Skill: `agent-market`; ClawHub Skill version: `0.1.0`; selected source: public repository `jefferysun95-cmyk/agent-market`, path `skills/agent-market`, six files. The owner explicitly confirmed MIT-0 for these six files at publication time. This does not relicense the entire repository or overwrite historical GitHub releases.

[Listing](https://clawhub.ai/jefferysun95-cmyk/skills/agent-market). The import UI generated version 0.1.0 and initially reported waiting checks; later the public page rendered the Skill and install command. Official CLI0.25.1 exact-owner/version inspect returned real skill/owner/version/files and a clean final moderation verdict. A fresh isolated directory install exited0 without --force or --force-install; six byte sizes and SHA256 values matched. No installed scripts were executed or copied into the user's actual harness; no signup, task, mail or payment was performed.

The service remains **1.1.0-alpha.5** and the frozen full plugin release remains **0.1.0-alpha.3**. ClawHub0.1.0 is an independent standalone Skill version, not an application upgrade or full CLI/plugin installation.

## Install

```sh
clawhub install @jefferysun95-cmyk/agent-market --version 0.1.0
```

The listing also shows `openclaw skills install @jefferysun95-cmyk/agent-market`; the clean-install result here is specifically official ClawHub CLI0.25.1. Do not use the unqualified homonymous slug. Standalone Skill contains guidance and the HTTP helper; scripts/client.py alone needs a separately installed full companion client. Installation grants no procurement or mailbox authority.

## Security boundaries

Final moderation/LLM result is clean/benign with medium confidence, **not a guarantee of safety**. Security metadata hasWarnings=true; auxiliary SkillSpector reports suspicious/CRITICAL with10 issues. The final LLM assessment treats many alerts as purpose-expected or unrelated, but explicitly records partial coverage/missing-reference and install-mechanism caveats. Preserve both results; do not advertise all scanners passed or hide the auxiliary warnings. No force/bypass flags were used.

The earlier owner upload0.1.0-alpha.3 remains historical: checks_failed and no report were observed. This successful GitHub-source import does not establish the old attempt's private root cause or that all bytes were identical. Do not delete/rewrite its retained evidence or mark support Issue4508 resolved without separately checking it.

## Platform-generated changelog discrepancy

The imported0.1.0 changelog is auto-generated and refers to Base Sepolia prediction-market files not belonging to this project's history. Record this as a platform metadata discrepancy consistent with homonymous-project mixing; its precise cause is unconfirmed. The six installed files and exact publisher are independently verified below. Do not copy that auto-generated history into our CHANGELOG. No editable version-changelog control was found in the reviewed UI; correction/support follow-up remains pending.

## Installed artifact hashes

| Path | Bytes | SHA256 |
|---|---:|---|
| `SKILL.md` | 11203 | `027378ba40366674912c60246b5e3dfee7c6468982462f185a70f0a5d331492c` |
| `references/api.md` | 4850 | `b25c97228f5b8819e93196b88554e98db3b64c8fc6c223f164404a2320457c7d` |
| `references/registration.md` | 4405 | `789bf007cac5baef09d42860cee81939e31932c6682619fdba345447f591d155` |
| `references/v11.md` | 4085 | `3af4a46cec0c47eb8ce8f7a2b26198647856775990ca65a25857400c33aeca17` |
| `scripts/client.py` | 738 | `6ed5bfc09b5ccd6df827265207be4336b405aae024dacd0664b83b5266dccbf6` |
| `scripts/market.py` | 3800 | `1da4b77120a9b598333641de9ad73a4f94cbfe1add75e8b22267eddd257f5666` |

## Evidence and remaining work

Local operational receipts are in the workspace's `work/clawhub-cause-20261111/`: github-import-receipt.json, github-import-010-inspect.json, github-import-install.txt and clawhub-public-installed.png. They contain public publication/validation data, not user credentials. The installed artifact was not executed. This validates distribution, not a new native-harness loading/signup/transaction scenario. Public guidance synchronization and channel review outcomes remain separately tracked in [distribution status](distribution-status.md).
