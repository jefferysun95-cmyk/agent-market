"""Offline validation of public Registry metadata; no secrets or network."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parent
source = json.loads((root / "schema/SOURCE.json").read_text(encoding="utf-8"))
schema_bytes = (root / "schema/server-2025-12-11.json").read_bytes()
if hashlib.sha256(schema_bytes).hexdigest() != source["sha256"]:
    raise SystemExit("FAIL: official schema snapshot checksum")
try:
    import jsonschema
except ImportError:
    raise SystemExit("Use the server development environment with jsonschema; no publication was attempted.")
metadata = json.loads((root / "server.json").read_text(encoding="utf-8"))
jsonschema.Draft7Validator(json.loads(schema_bytes)).validate(metadata)
assert metadata["$schema"] == source["source"]
assert metadata["name"] == "io.github.jefferysun95-cmyk/agent-market"
assert metadata["remotes"] and not metadata.get("packages")
for remote in metadata["remotes"]:
    assert remote["type"] == "streamable-http"
    assert remote["url"] == "https://api.digolives.com/mcp"
    headers = remote["headers"]
    assert len(headers) == 1 and headers[0]["name"] == "Authorization"
    assert headers[0]["isSecret"] is True and headers[0]["isRequired"] is True
    assert not any(k in headers[0] for k in ("value", "default"))
print(json.dumps({"status": "metadata_validated", "official_schema": True,
                  "network_requests": 0, "published": False, "credentials_read": False}))
