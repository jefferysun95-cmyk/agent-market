import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from unittest.mock import patch
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
from tests_support import Base
from server import handler
from agent_market.cli import main


class CLITest(Base):
    def setUp(self):
        super().setUp()
        self.http = ThreadingHTTPServer(('127.0.0.1', 0), handler(self.store, self.invite))
        self.worker = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.worker.start()
        self.directory = Path(self.tmp.name) / '私有配置'
        self.directory.mkdir()
        self.creds = self.directory / 'credentials.json'
        self.creds.write_text(json.dumps(dict(token=self.b)), encoding='utf-8')
        self.config = self.directory / 'client.json'
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('MARKET_')}
        self.env['MARKET_CONFIG_FILE'] = str(self.config)

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.worker.join(3)
        super().tearDown()

    def cli(self, *args, code=0):
        p = subprocess.run([sys.executable, '-m', 'agent_market.cli', *args], env=self.env, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(code, p.returncode, p.stderr)
        self.assertNotIn(self.b, p.stdout + p.stderr)
        return json.loads(p.stdout if code == 0 else p.stderr)

    def init(self):
        return self.cli('config', 'init', '--url', f'http://127.0.0.1:{self.http.server_port}', '--credentials-file', str(self.creds))

    def test_config_reference_doctor_and_progress(self):
        self.init()
        self.assertNotIn(self.b, self.config.read_text(encoding='utf-8'))
        self.assertEqual(self.b, json.loads(self.creds.read_text())['token'])
        self.cli('config', 'init', '--url', 'https://example.com', '--credentials-file', str(self.creds), code=2)
        d = self.cli('doctor')['data']
        self.assertEqual('buyer', d['identity']['name'])
        self.assertEqual('one_shot; no_watch_or_wakeup', d['runtime'])
        p = self.cli('tasks', 'progress', self.task['id'])['data']
        self.assertEqual('awaiting_quote', p['phase'])
        listing = self.cli('tasks', 'list', '--mine')['data']
        self.assertEqual(self.task['id'], listing['items'][0]['id'])

    def test_mutation_replay_conflict_and_auth_failure(self):
        self.init()
        body = self.directory / 'create.json'
        payload = {k: self.task[k] for k in ('title', 'category', 'brief', 'acceptance', 'deadline', 'budget')}
        body.write_text(json.dumps(payload), encoding='utf-8')
        first = self.cli('task', 'create', '--file', str(body), '--key', 'same-create')['data']
        again = self.cli('task', 'create', '--file', str(body), '--key', 'same-create')['data']
        self.assertEqual(first['id'], again['id'])
        payload['title'] = 'changed'
        body.write_text(json.dumps(payload), encoding='utf-8')
        self.assertEqual('conflict', self.cli('task', 'create', '--file', str(body), '--key', 'same-create', code=4)['error']['code'])
        self.creds.write_text(json.dumps(dict(token='invalid')), encoding='utf-8')
        self.assertEqual('authentication_failed', self.cli('identity', code=3)['error']['code'])

    def test_no_secret_errors_and_unsafe_service_origins(self):
        self.assertEqual('credentials_missing', self.cli('identity', code=3)['error']['code'])
        for url in ('http://example.com', 'https://user:secret@example.com', 'https://example.com/?token=secret'):
            self.cli('config', 'init', '--url', url, '--credentials-file', str(self.creds), code=2)
        self.init()
        with patch.dict(os.environ, self.env, clear=True), patch('agent_market.cli.request', side_effect=HTTPError('https://secret', 500, 'private-token', {}, io.BytesIO(b'private-token'))):
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(5, main(['identity']))
            self.assertNotIn('private-token', out.getvalue() + err.getvalue())
        self.cli('tasks', 'show', '../admin', code=2)

    def test_skill_and_packaged_transport_match(self):
        root = Path(__file__).parents[1]
        self.assertEqual((root / 'agent_market/market.py').read_bytes(), (root / 'skills/agent-market/scripts/market.py').read_bytes())

    def test_redirect_does_not_forward_credentials(self):
        from agent_market.market import NoRedirect
        from urllib.request import Request
        req = Request('https://example.com', headers={'Authorization': 'Bearer synthetic'})
        self.assertIsNone(NoRedirect().redirect_request(req, None, 302, 'redirect', {}, 'https://other.example'))
