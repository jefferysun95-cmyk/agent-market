"""Build a commit-pinned plugin archive without altering frozen service releases."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = ('.claude-plugin/', 'plugins/openclaw/', 'skills/agent-market/', 'agent_market/')
FILES = {'package.json', 'openclaw.plugin.json', 'README.md', 'README.en.md', 'LICENSE', 'docs/plugins.md', 'docs/plugins.zh.md', 'docs/validation-plugins.md'}


def git(*args):
    return subprocess.check_output(['git', '-c', 'safe.directory='+ROOT.as_posix(), '-C', str(ROOT), *args])


def selected_files():
    return sorted(p for p in git('ls-files').decode().splitlines()
                  if p in FILES or p.startswith(ALLOWED))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if git('status', '--porcelain').strip():
        raise SystemExit('Commit reviewed work first; archive uses tracked HEAD only.')
    head = git('rev-parse', 'HEAD').decode().strip()
    target = Path(args.output).resolve()
    # Build outside source internals. Never export into private configuration trees.
    if target == ROOT or target in ROOT.parents or '.git' in target.parts:
        raise SystemExit('Choose a new output directory.')
    target.mkdir(parents=True, exist_ok=False)
    archive = target / ('agent-market-plugin-0.1.0-alpha.1-'+head[:7]+'.zip')
    hashes = {}
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as z:
        for name in selected_files():
            if any(part in ('__pycache__', '.git', '.venv', 'private') for part in Path(name).parts) or name.endswith(('.db', '.pem', '-credentials.json')):
                raise SystemExit('Unexpected private/build file in allowlisted source.')
            data = git('show', head+':'+name)
            z.writestr('agent-market-plugin/'+name, data)
            hashes[name] = hashlib.sha256(data).hexdigest()
        z.writestr('agent-market-plugin/PLUGIN_BUILD.json', json.dumps(dict(
            plugin_version='0.1.0-alpha.1', service_client_version='1.1.0-alpha.5',
            source_commit=head, files=hashes, private_credentials=False), indent=2))
    with zipfile.ZipFile(archive) as z:
        for name, expected in hashes.items():
            if hashlib.sha256(z.read('agent-market-plugin/'+name)).hexdigest() != expected:
                raise SystemExit('Archive verification failed.')
    (target/'SHA256SUMS.txt').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n', encoding='utf8')
    print(json.dumps(dict(archive=str(archive), commit=head, files=len(hashes), byte_verification='PASS')))


if __name__ == '__main__':
    main()
