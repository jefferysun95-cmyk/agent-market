# MCP Registry publication — active

This remote-only published metadata reuses the existing Alpha5 service. It does not deploy a server, change authentication, distribute credentials or imply listing approval. Version1.1.0-alpha.5 identifies the published service version; no runtime or frozen Release change occurs.

- Published namespace: `io.github.jefferysun95-cmyk/agent-market`.
- Remote transport: Streamable HTTP at `https://api.digolives.com/mcp`.
- Personal `Authorization` header is required and secret. Register with contact-email verification using [English onboarding](../docs/registration.en.md). Hosts must supply `Bearer <personal token>` privately; no actual token/default value belongs in metadata.
- GitHub owner authorization and publication completed2026-11-10. The exact namespace/version was read back with status=active; see PUBLICATION.json. Schema validation alone remains distinct from publication and live MCP client acceptance.

## Local metadata validation

The official schema is vendored unchanged under schema/ with its original URL, retrieval date and SHA256. With the existing server development environment (jsonschema is required for this validation only):

```sh
python registry/validate.py
```

This command performs no network requests and reads no credentials. It checks the official schema, checksum and required private-header declaration. Publishing requires the official mcp-publisher separately; do not bundle its login files or tool binary in this repository.

## Publication gates

1. Recheck the then-current publisher release/schema; use the vendor release checksum before executing a download.
2. Owner completes GitHub device login locally; never share publisher tokens/codes in chat or Git. Review displayed account before confirming.
3. Recheck public health/version and unauthenticated MCP rejection; a failure must not be fixed by weakening auth. An authorized host separately tests initialize/tools-list/identity without sharing its personal token.
4. Validate exact final server.json and confirm onboarding. Check for an existing namespace/version before publishing; never blindly publish twice after an uncertain response.
5. Run the official publisher against this reviewed file once; retain a redacted receipt. Read back the exact namespace/version from the official Registry and compare metadata.
6. Only then mark registered/discoverable. Registry metadata discovery is distinct from Cursor/OpenAI/Claude directory approval and per-host connection support.

Current remote auth is personal Bearer, not full platform OAuth. No user payment or email mailbox grant is added by this listing. The CLI/Skill path remains available to hosts lacking custom-header MCP support.

Official references: https://modelcontextprotocol.io/registry/quickstart and https://modelcontextprotocol.io/registry/remote-servers .
