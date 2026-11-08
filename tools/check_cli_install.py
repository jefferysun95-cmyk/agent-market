"""Install/reinstall/uninstall a wheel in a clean venv; synthetic localhost only."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import venv
from http.server import ThreadingHTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import Store, handler


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('wheel')
    wheel = Path(p.parse_args().wheel).resolve()
    with tempfile.TemporaryDirectory(prefix='market-install-') as temp:
        root = Path(temp)
        venv.create(root / 'venv', with_pip=True)
        binary = root / 'venv' / ('Scripts' if os.name == 'nt' else 'bin')
        python = binary / ('python.exe' if os.name == 'nt' else 'python')
        cli = binary / ('agent-market.exe' if os.name == 'nt' else 'agent-market')
        env = {k:v for k,v in os.environ.items() if not k.startswith('MARKET_') and k != 'PYTHONPATH'}
        env['PYTHONIOENCODING'] = 'utf-8'
        private = root / 'private-配置'
        private.mkdir()
        credentials = private / 'credentials.json'
        config = private / 'client.json'
        env['MARKET_CONFIG_FILE'] = str(config)
        store = Store(root / 'test.db')
        registration = store.call('POST', '/agents', {}, dict(name='install-check', provider='synthetic'), 'synthetic-invite', 'register', 'synthetic-invite')
        credentials.write_text(json.dumps(registration), encoding='utf-8')
        original = credentials.read_bytes()
        http = ThreadingHTTPServer(('127.0.0.1', 0), handler(store, 'synthetic-invite'))
        thread = threading.Thread(target=http.serve_forever, daemon=True)
        thread.start()

        def run(*args):
            result = subprocess.run([str(a) for a in args], cwd=root, env=env, capture_output=True, text=True, encoding='utf-8', timeout=90)
            if result.returncode:
                raise RuntimeError('Clean install command failed: ' + result.stderr)
            if registration['token'] in result.stdout + result.stderr:
                raise RuntimeError('Credential leaked')
            return result.stdout

        try:
            run(python, '-m', 'pip', 'install', '--no-index', '--no-deps', wheel)
            assert '1.1.0-alpha.4' in run(cli, '--version')
            run(cli, 'config', 'init', '--url', f'http://127.0.0.1:{http.server_port}', '--credentials-file', credentials)
            doctor = json.loads(run(cli, 'doctor'))
            assert doctor['data']['identity']['name'] == 'install-check'
            tasks = json.loads(run(cli, 'tasks', 'list', '--mine'))
            assert tasks['data']['items'] == []
            saved = config.read_bytes()
            run(python, '-m', 'pip', 'install', '--no-index', '--no-deps', '--force-reinstall', wheel)
            assert json.loads(run(cli, 'identity'))['data']['name'] == 'install-check'
            run(python, '-m', 'pip', 'uninstall', '-y', 'agent-market-client')
            assert config.read_bytes() == saved and credentials.read_bytes() == original
            print('PASS: clean wheel install, installed CLI/config/doctor/query, same-version reinstall, uninstall preserves private files')
        finally:
            http.shutdown(); http.server_close(); thread.join(3)


if __name__ == '__main__':
    main()
