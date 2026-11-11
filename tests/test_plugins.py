"""Packaging tests use isolated copies; no host configuration or network mutations."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PluginTest(unittest.TestCase):
    def test_manifests_point_to_shipped_skill_and_entry(self):
        claude = json.loads((ROOT/'.claude-plugin/plugin.json').read_text())
        market = json.loads((ROOT/'.claude-plugin/marketplace.json').read_text())
        claw = json.loads((ROOT/'openclaw.plugin.json').read_text())
        cursor = json.loads((ROOT/'.cursor-plugin/plugin.json').read_text())
        package = json.loads((ROOT/'package.json').read_text())
        self.assertEqual(claude['name'], claw['id'])
        self.assertEqual(cursor['name'], claude['name'])
        self.assertEqual(cursor['version'], claude['version'])
        self.assertTrue((ROOT/cursor['skills']/'agent-market/SKILL.md').is_file())
        self.assertNotIn('mcpServers', cursor)
        self.assertNotIn('hooks', cursor)
        self.assertEqual(claude['version'], package['version'])
        self.assertEqual(market['plugins'][0]['source'], './')
        self.assertEqual(market['plugins'][0]['version'], claude['version'])
        self.assertEqual(claw['version'], claude['version'])
        self.assertTrue((ROOT/claude['skills']/'agent-market/SKILL.md').is_file())
        for path in package['openclaw']['extensions']:
            self.assertTrue((ROOT/path).is_file())
        self.assertEqual(claw['configSchema']['properties'], {})
        self.assertNotIn('hooks', claude)
        self.assertNotIn('scripts', package)

    def test_installed_copy_works_outside_repo_and_without_pip(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)/'plugin with spaces'
            shutil.copytree(ROOT/'agent_market', root/'agent_market', ignore=shutil.ignore_patterns('__pycache__'))
            entry = root/'skills/agent-market/scripts/client.py'
            entry.parent.mkdir(parents=True)
            shutil.copy2(ROOT/'skills/agent-market/scripts/client.py', entry)
            # Isolated Python excludes installed site packages and user paths.
            result = subprocess.run([sys.executable, '-I', '-S', str(entry), '--version'],
                                    cwd=folder, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('1.1.0-alpha.5', result.stdout)
            result = subprocess.run([sys.executable, '-I', '-S', str(entry), 'register', 'start', '--help'],
                                    cwd=folder, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('--session', result.stdout)
            result = subprocess.run([sys.executable, '-I', '-S', str(entry), 'register', 'preflight',
                                     '--session', str(Path(folder)/'private/session.json'),
                                     '--credentials-file', str(Path(folder)/'private/credentials.json')],
                                    cwd=folder, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['data']['status'], 'preflight_passed')
            self.assertFalse(list(root.rglob('*credentials*')))
            self.assertFalse(list((Path(folder)/'private').iterdir()))

    def test_standalone_missing_bundle_fails_without_installation(self):
        with tempfile.TemporaryDirectory() as folder:
            entry = Path(folder)/'skills/agent-market/scripts/client.py'
            entry.parent.mkdir(parents=True)
            shutil.copy2(ROOT/'skills/agent-market/scripts/client.py', entry)
            result = subprocess.run([sys.executable, '-I', '-S', str(entry), '--version'],
                                    cwd=folder, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stderr)['error']['code'], 'client_not_bundled')

    def test_plugin_identity_uses_only_explicit_private_config(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                valid = self.path == '/me' and self.headers.get('Authorization') == 'Bearer synthetic-plugin-token'
                self.send_response(200 if valid else 401)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'id': 'synthetic-id', 'name': 'PluginTest'} if valid else {'error': 'unauthorized'}).encode())
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                cred = root/'credential.json'
                cred.write_text(json.dumps({'token': 'synthetic-plugin-token'}))
                config = root/'client.json'
                config.write_text(json.dumps({'url': 'http://127.0.0.1:'+str(server.server_port), 'credentials_file': str(cred)}))
                env = {k:v for k,v in os.environ.items() if k not in ('MARKET_URL', 'MARKET_TOKEN', 'MARKET_CREDENTIALS_FILE', 'MARKET_CONFIG_FILE')}
                result = subprocess.run([sys.executable, '-I', '-S', str(ROOT/'skills/agent-market/scripts/client.py'), '--config', str(config), 'identity'],
                                        env=env, cwd=folder, capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)['data']['name'], 'PluginTest')
                self.assertNotIn('synthetic-plugin-token', result.stdout+result.stderr)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
