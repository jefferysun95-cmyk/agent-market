# 1.1 release checklist

Current target: `1.1.0-alpha.2`, a developer candidate with a client mail fix compatible with the deployed alpha.1 API. Do not claim live mail recovery until current-manifest receipts and delivery verification pass.

## GitHub sequence

1. Issue scoped to each feature/bug → branch → PR with tests/docs/CHANGELOG.
2. CI passes, maintainer reviews permissions/compatibility and merges.
3. Tag the reviewed candidate version; publish a GitHub prerelease with Skill zip and source, checksum and known limitations.
4. Deploy a pinned commit after a consistent backup; record health version and rollback checkpoint.
5. Promote to `1.1.0-beta.1` only after the live gates below. Update README, Pages and installation snippets together.

After staging reviewed source, `python package_release.py` builds source/Skill zip files and SHA256SUMS in ignored dist/. Archives use Git index content, excluding local environment/DB/mail credentials. Verify archive contents before attaching them to a prerelease.

## Automated gates

- Existing lifecycle/concurrency/persistence; credential replay, rotation and revocation.
- Participant inbox replay/ack, quote privacy, manifest role/hash/version gate.
- MIME send/receive recovery using fake Gmail, unexpected/hash-mismatched file rejection.
- Real MCP SDK handshake/tool call and HTTP permission/size checks.
- SQLite backup recovery and migration preserve old identities/orders.
- Provider-rewritten RFC822 Message-ID, explicit Spam/Trash lookup, interrupted send/receipt recovery and auditable alpha.1 input-manifest replacement without resending.
- Before beta, complete the P0 [waiting reliability plan](waiting-reliability-plan.md): durable discovery/work loop, fresh state reporting, next responsible actor, timeouts and restart recovery. This is planned work, not an implemented alpha.2 feature.

## Live gates (pending, never inferred from mocks)

- Two separately authorized Gmail mailboxes: input and three output CSVs, retry, wrong attachment, rework; verify JSON/CSV meaning and record no human file forwarding.
- One real Skill host and at least one remote MCP host using personal-token headers; record host/version/config. A second MCP host is required before broad compatibility claims.
- Backup restore in a temporary copy, production upgrade, HTTPS/old identity checks, rollback rehearsal. Keep the original backup private.
- At least one external user completes onboarding without the maintainer touching their credentials. Record time and intervention count.

## Later 1.1 milestones

- Simplify credential onboarding with a documented private channel first; platform OAuth/self-service identity is separately designed and reviewed.
- Durable polling integration with a host scheduler, bounded retry/backoff and observable failures.
- Validate real public/non-sensitive tasks and repeat use; do not treat free synthetic orders as paid-market validation.
