# Contributing

Discuss the user problem in an Issue, then use a focused branch and pull request. Small documentation, adapter and test contributions are welcome. Never attach credentials, mailbox contents or production databases.

```sh
python -m venv .venv
# Activate the virtual environment for your shell.
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python demo.py
```

Python 3.10+; email dependencies are optional (`requirements-mail.txt`). Include changed behavior, tests and compatibility notes in the PR. Update CHANGELOG and the relevant human or protocol documentation. Keep HTTP/MCP authorization in Store and email credentials on the user's device.

CI uses synthetic data and fake email; do not add real tokens as test fixtures. Live release checks belong in [the release checklist](docs/release.md). A maintainer merges reviewed work, tags the version and publishes a prerelease before promoting it to beta.
