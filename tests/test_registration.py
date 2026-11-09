import concurrent.futures
import asyncio
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from registration import Registration, RegistrationError, from_environment
from server import Store, CATEGORIES, Problem, handler


class RegistrationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'test.db'
        self.store = Store(self.path)
        self.now = 1_800_000_000
        self.sent = []
        self.reg = Registration(self.store, lambda *args: self.sent.append(args), 'synthetic-registration-secret-' * 2,
                                CATEGORIES, clock=lambda: self.now)
        self.body = dict(email='person@example.com', agent_key='buyer', name='Synthetic buyer', provider='test', capabilities=[])
        self.seq = 0

    def tearDown(self):
        self.temp.cleanup()

    def key(self):
        self.seq += 1
        return 'synthetic-key-' + str(self.seq).zfill(8)

    def begin(self, **changes):
        return self.reg.start(dict(self.body, **changes), self.key(), '192.0.2.1')

    def finish(self, challenge, key=None):
        code = next(code for _, code, cid in self.sent if cid == challenge['challenge_id'])
        return self.reg.finish(dict(challenge_id=challenge['challenge_id'], code=code), key or self.key())

    def recover(self):
        return self.reg.start(dict(email=self.body['email'], agent_key='buyer', purpose='recover'), self.key(), '192.0.2.1')

    def error(self, status, func, *args):
        with self.assertRaises((Problem, RegistrationError)) as caught:
            func(*args)
        self.assertEqual(status, caught.exception.status)

    def test_register_replay_privacy_and_restart(self):
        start_key, finish_key = self.key(), self.key()
        challenge = self.reg.start(self.body, start_key, '192.0.2.1')
        self.assertEqual(challenge, self.reg.start(self.body, start_key, '192.0.2.1'))
        self.assertEqual(1, len(self.sent))
        issued = self.finish(challenge, finish_key)
        self.assertEqual(issued, self.finish(challenge, finish_key))
        self.assertEqual(issued['agent'], self.store.call('GET', '/me', {}, {}, issued['token'], '', ''))
        self.assertNotIn('email', json.dumps(issued['agent']))
        self.assertNotIn(issued['token'].encode(), self.path.read_bytes())
        self.assertNotIn(self.sent[0][1].encode(), self.path.read_bytes())
        self.assertNotIn(b'person@example.com', self.path.read_bytes())
        self.reg = Registration(Store(self.path), lambda *args: self.sent.append(args), self.reg.secret, CATEGORIES, clock=lambda: self.now)
        self.assertEqual(issued, self.finish(challenge, finish_key))
        self.error(409, self.finish, challenge, self.key())

    def test_failed_attempts_commit_and_expire(self):
        c = self.begin()
        actual = self.sent[-1][1]
        bad = '00000000' if actual != '00000000' else '11111111'
        for _ in range(5):
            self.error(400, self.reg.finish, dict(challenge_id=c['challenge_id'], code=bad), self.key())
        self.error(400, self.finish, c)
        with self.store.connect() as db:
            self.assertEqual(5, db.execute('SELECT attempts FROM registration_challenges').fetchone()[0])
        c = self.begin(agent_key='other')
        self.now += 601
        self.error(400, self.finish, c)

    def test_recovery_rotates_and_supersedes_old_exchanges(self):
        c = self.begin(); k = self.key(); old = self.finish(c, k)
        recovery = self.recover()
        self.assertEqual(old['agent'], self.store.call('GET', '/me', {}, {}, old['token'], '', ''))
        actual = next(code for _, code, cid in self.sent if cid == recovery['challenge_id'])
        wrong = '00000000' if actual != '00000000' else '11111111'
        self.error(400, self.reg.finish, dict(challenge_id=recovery['challenge_id'], code=wrong), self.key())
        self.assertEqual(old['agent'], self.store.call('GET', '/me', {}, {}, old['token'], '', ''))
        new = self.finish(recovery)
        self.assertEqual(old['agent']['id'], new['agent']['id'])
        self.error(401, self.store.call, 'GET', '/me', {}, {}, old['token'], '', '')
        self.assertEqual(new['agent'], self.store.call('GET', '/me', {}, {}, new['token'], '', ''))
        self.error(400, self.finish, c, k)
        self.assertNotIn(new['token'].encode(), self.path.read_bytes())

    def test_existing_slot_does_not_rotate_without_recovery(self):
        issued = self.finish(self.begin())
        self.error(409, self.finish, self.begin(name='Another display name'))
        self.assertEqual(issued['agent'], self.store.call('GET', '/me', {}, {}, issued['token'], '', ''))
        missing = self.reg.start(dict(email='unknown@example.com', agent_key='buyer', purpose='recover'), self.key(), '192.0.2.1')
        self.error(409, self.finish, missing)

    def test_operator_revoke_cannot_be_bypassed_by_recovery(self):
        issued = self.finish(self.begin())
        invite = 'synthetic-operator-secret-' * 2
        self.store.call('POST', '/admin/agents/' + issued['agent']['id'] + '/revoke', {}, {}, invite, 'operator-revoke', invite)
        self.error(403, self.finish, self.recover())

    def test_address_peer_and_global_request_limits(self):
        for _ in range(5): self.begin()
        self.error(429, self.begin)
        for i in range(5): self.begin(email=f'other{i}@example.com')
        self.error(429, self.reg.start, dict(self.body, email='new-peer-limit@example.com'), self.key(), '192.0.2.1')
        with self.store.connect() as db:
            db.execute('DELETE FROM registration_challenges')
        for i in range(100):
            self.reg.start(dict(self.body, email=f'user{i}@example.com'), self.key(), f'192.0.2.{i}')
        self.error(429, self.reg.start, dict(self.body, email='last@example.com'), self.key(), 'different-peer')

    def test_three_slots_and_shared_daily_quota(self):
        issued = [self.finish(self.begin(agent_key='slot' + str(i))) for i in range(3)]
        self.error(429, self.finish, self.begin(agent_key='fourth'))
        token = issued[0]['token']
        task = dict(title='synthetic', category='data-cleaning', brief='public synthetic', acceptance='valid', deadline='later', budget='CNY 0')
        for i in range(20):
            actor_token = issued[i % 3]['token']
            self.store.call('POST', '/tasks', {}, task, actor_token, 'task-' + str(i), '')
        self.error(429, self.store.call, 'POST', '/tasks', {}, task, token, 'over-quota', '')
        # A safe replay is still recoverable after hitting a quota.
        self.store.call('POST', '/tasks', {}, task, token, 'task-0', '')

    def test_concurrent_finish_creates_one_identity(self):
        c, k = self.begin(), self.key()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.finish(c, k), range(2)))
        self.assertEqual(results[0], results[1])
        with self.store.connect() as db:
            self.assertEqual(1, db.execute('SELECT COUNT(*) FROM agents').fetchone()[0])

    def test_two_new_accounts_complete_a_free_transaction(self):
        buyer = self.finish(self.begin())['token']
        seller = self.finish(self.begin(email='supplier@example.com', agent_key='seller', capabilities=['data-cleaning']))['token']
        def call(token, path, body):
            return self.store.call('POST', path, {}, body, token, self.key(), '')
        task = call(buyer, '/tasks', dict(title='Synthetic free onboarding test', category='data-cleaning',
                    brief='One public synthetic row', acceptance='Return exactly one row', budget='CNY 0', deadline='later'))
        path = '/tasks/' + task['id']
        proposal = call(seller, path + '/proposals', dict(price='CNY 0', terms='Exactly one synthetic row', deadline='later'))
        chosen = call(buyer, path + '/select', dict(proposal_id=proposal['proposals'][0]['id']))
        call(seller, path + '/confirm', dict(revision=chosen['revision']))
        call(seller, path + '/deliver', dict(result={'rows': [{'id': 1}]}))
        accepted = call(buyer, path + '/accept', dict(note='Synthetic result checked; no payment'))
        self.assertEqual('accepted', accepted['status'])
        self.assertEqual({}, accepted['payment'])

    def test_validation_and_conflicting_start_key(self):
        key = self.key()
        self.reg.start(self.body, key, 'peer')
        self.error(409, self.reg.start, dict(self.body, name='changed'), key, 'peer')
        for email in ('x\r\nBcc: other@example.com', 'x@localhost', '..x@example.com'):
            self.error(400, self.reg.start, dict(self.body, email=email), self.key(), 'peer')
        self.error(400, self.reg.start, dict(self.body, capabilities=['invented']), self.key(), 'peer')
        self.error(400, self.reg.start, self.body, 'short', 'peer')

    def test_uncertain_mail_not_retried_and_disabled_configuration(self):
        key = self.key()
        def failed(*args):
            self.sent.append(args)
            raise RuntimeError('synthetic SMTP secret must not leak')
        self.reg.sender = failed
        self.error(503, self.reg.start, self.body, key, 'peer')
        self.error(409, self.reg.start, self.body, key, 'peer')
        self.assertEqual(1, len(self.sent))
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(from_environment(self.store, CATEGORIES))
        with patch.dict(os.environ, {'MARKET_SELF_REGISTRATION': '1'}, clear=True):
            with self.assertRaises((ValueError, RegistrationError)):
                from_environment(self.store, CATEGORIES)

    def test_smtp_requires_verified_tls_before_login(self):
        config = dict(MARKET_SELF_REGISTRATION='1', MARKET_REGISTRATION_SECRET='synthetic-secret-' * 3,
                      MARKET_SMTP_HOST='smtp.example.com', MARKET_SMTP_USER='synthetic-user',
                      MARKET_SMTP_PASSWORD='synthetic-password', MARKET_SMTP_FROM='verify@example.com')
        for port in ('465', '587'):
            with patch.dict(os.environ, dict(config, MARKET_SMTP_PORT=port), clear=True), \
                    patch('registration.smtplib.SMTP') as plain, patch('registration.smtplib.SMTP_SSL') as secure:
                reg = from_environment(self.store, CATEGORIES)
                reg.sender('recipient@example.com', '12345678', 'synthetic-id')
                constructor = secure if port == '465' else plain
                smtp = constructor.return_value.__enter__.return_value
                smtp.login.assert_called_once_with('synthetic-user', 'synthetic-password')
                if port == '587':
                    smtp.starttls.assert_called_once()
                    names = [call[0] for call in smtp.method_calls]
                    self.assertLess(names.index('starttls'), names.index('login'))
                    context = smtp.starttls.call_args.kwargs['context']
                else:
                    plain.assert_not_called()
                    context = secure.call_args.kwargs['context']
                import ssl
                self.assertTrue(context.check_hostname)
                self.assertEqual(ssl.CERT_REQUIRED, context.verify_mode)
                message = smtp.send_message.call_args.args[0]
                self.assertEqual('recipient@example.com', message['To'])
                self.assertIn('12345678', message.get_content())
        with patch.dict(os.environ, dict(config, MARKET_SMTP_PORT='25'), clear=True):
            with self.assertRaises(ValueError): from_environment(self.store, CATEGORIES)

    def test_http_public_routes_and_disabled_default(self):
        for reg in (None, self.reg):
            server = ThreadingHTTPServer(('127.0.0.1', 0), handler(self.store, 'operator-only-secret', reg))
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                base = 'http://127.0.0.1:' + str(server.server_port)
                with urlopen(base + '/health') as response:
                    self.assertEqual(reg is not None, json.load(response)['self_registration'])
                request = Request(base + '/registration/start', json.dumps(self.body).encode(),
                                  {'Content-Type': 'application/json', 'Idempotency-Key': self.key()})
                if reg is None:
                    with self.assertRaises(HTTPError) as caught: urlopen(request)
                    self.assertEqual(503, caught.exception.code)
                    caught.exception.close()
                    continue
                with urlopen(request) as response:
                    challenge = json.load(response)
                    self.assertEqual('no-store', response.headers['Cache-Control'])
                code = self.sent[-1][1]
                request = Request(base + '/registration/finish', json.dumps(dict(challenge_id=challenge['challenge_id'], code=code)).encode(),
                                  {'Content-Type': 'application/json', 'Idempotency-Key': self.key()})
                with urlopen(request) as response: issued = json.load(response)
                with urlopen(Request(base + '/me', headers={'Authorization': 'Bearer ' + issued['token']})) as response:
                    self.assertEqual(issued['agent']['id'], json.load(response)['id'])
            finally:
                server.shutdown(); server.server_close(); thread.join()

    def test_cli_registration_private_save_retry_and_no_token_output(self):
        from agent_market.cli import main
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler(self.store, 'operator-only-secret', self.reg))
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        directory = Path(self.temp.name)
        request, session, creds, code_file = [directory / name for name in ('request.json', 'session.json', 'creds.json', 'code.txt')]
        request.write_text(json.dumps(self.body), encoding='utf-8')
        def run(*args):
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                status = main(list(args))
            return status, stdout.getvalue() + stderr.getvalue()
        try:
            args = ('register', 'start', '--url', 'http://127.0.0.1:' + str(server.server_port), '--file', str(request), '--session', str(session))
            with patch.dict(os.environ, {'MARKET_TOKEN': 'synthetic-unrelated-token', 'MARKET_CONFIG_FILE': str(directory / 'absent.json')}):
                self.assertEqual(0, run(*args)[0])
                self.assertEqual(0, run(*args)[0])
                self.assertEqual(1, len(self.sent))
                code_file.write_text(self.sent[0][1], encoding='utf-8')
                finish = ('register', 'finish', '--session', str(session), '--credentials-file', str(creds), '--code-file', str(code_file))
                # Lost response: the service issues, client sees a network error.
                from agent_market import onboarding
                real = onboarding.public_request
                def lost(*a):
                    real(*a)
                    raise TimeoutError('synthetic response loss')
                with patch.object(onboarding, 'public_request', side_effect=lost):
                    self.assertEqual(6, run(*finish)[0])
                self.assertFalse(creds.exists())
                status, report = run(*finish)
                self.assertEqual(0, status, report)
                token = json.loads(creds.read_text(encoding='utf-8'))['token']
                self.assertNotIn(token, report)
                self.assertNotIn(self.sent[0][1], report)
                self.assertNotIn(token, session.read_text(encoding='utf-8'))
                self.assertEqual(2, run(*finish)[0])
                self.assertEqual(token, json.loads(creds.read_text(encoding='utf-8'))['token'])
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_private_parent_alias_resolves_but_cannot_escape_git_boundary(self):
        from agent_market.onboarding import private_path, OnboardingError
        directory = Path(self.temp.name)
        target = directory / 'real'; target.mkdir()
        alias = directory / 'alias'
        try:
            alias.symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest('Directory symlinks unavailable for this test account')
        self.assertEqual(target.resolve() / 'state.json', private_path(alias / 'state.json'))
        (target / '.git').mkdir()
        with self.assertRaises(OnboardingError): private_path(alias / 'state.json')
        (target / '.git').rmdir()
        (target / 'secret.json').write_text('{}')
        leaf = directory / 'leaf.json'; leaf.symlink_to(target / 'secret.json')
        with self.assertRaises(OnboardingError): private_path(leaf)

    def test_asgi_uses_the_same_registration_and_store(self):
        # No network, real Gmail or production database; call the ASGI transport.
        try:
            import mcp
        except ImportError:
            self.skipTest('Optional MCP/ASGI dependencies are not installed')
        with patch.dict(os.environ, {'MARKET_DB': str(self.path), 'MARKET_INVITE_TOKEN': 'synthetic-operator-secret-' * 2, 'MARKET_SELF_REGISTRATION': '0'}):
            import app as asgi
        async def post(path, data, key, peer='192.0.2.50'):
            messages = []
            async def receive(): return dict(type='http.request', body=json.dumps(data).encode(), more_body=False)
            async def send(message): messages.append(message)
            scope = dict(type='http', path=path, method='POST', client=(peer, 1234), query_string=b'',
                         headers=[(b'idempotency-key', key.encode())])
            await asgi.app(scope, receive, send)
            return messages[0]['status'], json.loads(messages[1]['body'])
        with patch.object(asgi, 'registration', self.reg), patch.object(asgi, 'store', self.store):
            status, c = asyncio.run(post('/registration/start', self.body, self.key()))
            self.assertEqual(200, status)
            status, issued = asyncio.run(post('/registration/finish', dict(challenge_id=c['challenge_id'], code=self.sent[-1][1]), self.key()))
            self.assertEqual(200, status)
            self.assertEqual(issued['agent'], self.store.call('GET', '/me', {}, {}, issued['token'], '', ''))
            with patch.object(asgi, 'registration', None):
                self.assertEqual(503, asyncio.run(post('/registration/start', self.body, self.key()))[0])


if __name__ == '__main__':
    unittest.main()
