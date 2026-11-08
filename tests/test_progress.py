import copy
import json
from tests_support import Base


class ProgressTest(Base):
    def call(self, token, method, path, data=None, key=None, query=None):
        import uuid
        return self.store.call(method, path, query or {}, data or {}, token, key or uuid.uuid4().hex, self.invite)

    def select(self):
        t = self.call(self.s, 'POST', self.path + '/proposals', dict(price='0', terms='clean', deadline='soon'))
        seller = self.call(self.s, 'GET', '/me')['id']
        p = next(p for p in t['proposals'] if p['seller'] == seller)
        return self.call(self.b, 'POST', self.path + '/select', dict(proposal_id=p['id']))

    def progress(self, token):
        return self.call(token, 'GET', self.path)['progress']

    def test_quote_selection_privacy_and_no_writes(self):
        initial = self.progress(self.b)
        self.assertEqual('awaiting_quote', initial['phase'])
        self.assertEqual('unknown', initial['runtime_status'])
        self.call(self.x, 'POST', self.path + '/proposals', dict(price='secret', terms='private', deadline='soon'))
        outsider = self.progress(self.s)
        self.assertEqual('awaiting_quote', outsider['phase'])
        self.assertEqual(initial['last_event_id'], outsider['last_event_id'])
        self.assertNotIn('secret', json.dumps(outsider))
        self.assertEqual('awaiting_selection', self.progress(self.b)['phase'])
        selected = self.select()
        self.fail(403, self.x, 'GET', self.path + '/progress')
        with self.store.connect() as db:
            before = db.execute('SELECT COUNT(*) FROM events').fetchone()[0]
        p = self.progress(self.s)
        self.assertEqual('awaiting_confirmation', p['phase'])
        self.assertTrue(next(a for a in p['next_actions'] if a['action'] == 'confirm')['executable'])
        self.assertEqual(selected['revision'], p['next_actions'][-1]['revision'])
        with self.store.connect() as db:
            self.assertEqual(before, db.execute('SELECT COUNT(*) FROM events').fetchone()[0])

    def test_independent_mail_config_and_irreversible_missing_mailbox(self):
        self.select()
        self.call(self.b, 'POST', self.path + '/mail-config', dict(address='buyer@example.com'))
        p = self.progress(self.s)
        self.assertEqual('awaiting_mailboxes', p['phase'])
        self.assertTrue(next(a for a in p['next_actions'] if a['action'] == 'mail-config')['executable'])
        self.assertFalse(next(a for a in p['next_actions'] if a['action'] == 'confirm')['executable'])
        # Legacy confirm is still valid, but diagnostics must explain the locked configuration.
        self.call(self.s, 'POST', self.path + '/confirm', dict(revision=1))
        self.assertEqual('blocked_mail_configuration', self.progress(self.b)['phase'])

    def test_input_output_receipts_rework_and_terminal(self):
        self.select()
        for token, address in [(self.b, 'buyer@example.com'), (self.s, 'seller@example.com')]:
            self.call(token, 'POST', self.path + '/mail-config', dict(address=address))
        self.call(self.s, 'POST', self.path + '/confirm', dict(revision=1))
        self.assertEqual('awaiting_input_manifest', self.progress(self.b)['phase'])
        files = [dict(name='rows.csv', size=3, sha256='a' * 64)]
        for kind, sender, receiver in [('input', self.b, self.s), ('delivery', self.s, self.b)]:
            m = self.call(sender, 'POST', self.path + '/mail-manifests', dict(kind=kind, files=files))
            self.assertEqual('awaiting_' + kind + '_send', self.progress(sender)['phase'])
            self.call(sender, 'POST', self.path + '/mail-sent', dict(manifest_id=m['id'], message_id='<actual-' + kind + '>'))
            self.assertEqual('awaiting_' + kind + '_receipt', self.progress(receiver)['phase'])
            if kind == 'delivery':
                self.assertTrue(next(a for a in self.progress(self.s)['next_actions'] if a['action'] == 'deliver')['executable'])
            self.call(receiver, 'POST', self.path + '/mail-received', dict(manifest_id=m['id'], files=files,
                observed_message_id='<actual-' + kind + '>', observed_from=m['from'], observed_to=m['to']))
        self.call(self.s, 'POST', self.path + '/deliver', dict(result={'ok': True}))
        self.assertEqual('awaiting_review', self.progress(self.b)['phase'])
        self.call(self.b, 'POST', self.path + '/request_changes', dict(note='revise'))
        p = self.progress(self.s)
        self.assertEqual(['new_delivery_manifest_required'], next(a for a in p['next_actions'] if a['action'] == 'deliver')['blocked_by'])
        m = self.call(self.s, 'POST', self.path + '/mail-manifests', dict(kind='delivery', files=files))
        self.call(self.s, 'POST', self.path + '/mail-sent', dict(manifest_id=m['id'], message_id='<v2>'))
        self.call(self.b, 'POST', self.path + '/mail-received', dict(manifest_id=m['id'], files=files,
            observed_message_id='<v2>', observed_from=m['from'], observed_to=m['to']))
        self.call(self.s, 'POST', self.path + '/deliver', dict(result={'ok': True}))
        self.call(self.b, 'POST', self.path + '/accept', dict(note='verified'))
        self.assertEqual([], self.progress(self.b)['next_actions'])

    def test_legacy_receipt_is_not_ready(self):
        self.select()
        self.call(self.s, 'POST', self.path + '/confirm', dict(revision=1))
        with self.store.connect() as db:
            t = json.loads(db.execute('SELECT body FROM tasks WHERE id=?', (self.task['id'],)).fetchone()[0])
            t['mail'] = dict(addresses={t['buyer']: 'a@example.com', t['proposals'][0]['seller']: 'b@example.com'},
                manifests=[dict(id='legacy', kind='input', sender=t['buyer'], recipient=t['proposals'][0]['seller'],
                    sent_at='old', received_at='old', message_id='<legacy>', files=[], **{'from': 'a@example.com', 'to': 'b@example.com'})])
            db.execute('UPDATE tasks SET body=? WHERE id=?', (json.dumps(t), t['id']))
        self.assertEqual('awaiting_input_receipt', self.progress(self.s)['phase'])

    def test_filtered_pagination_beyond_500_and_insert_stability(self):
        with self.store.connect() as db:
            for i in range(505):
                t = dict(self.task, id='other-' + str(i), buyer='unrelated', category='web-extraction')
                db.execute('INSERT INTO tasks VALUES(?,?,?,?)', (t['id'], t['buyer'], 'open', json.dumps(t)))
        mine = self.call(self.b, 'GET', '/tasks', query={'scope': ['mine']})
        self.assertEqual([self.task['id']], [t['id'] for t in mine])
        q = {'page': ['true'], 'limit': ['2']}
        first = self.call(self.b, 'GET', '/tasks', query=q)
        self.assertTrue(first['has_more'])
        with self.store.connect() as db:
            t = dict(self.task, id='newest')
            db.execute('INSERT INTO tasks VALUES(?,?,?,?)', (t['id'], t['buyer'], 'open', json.dumps(t)))
        second = self.call(self.b, 'GET', '/tasks', query=dict(q, before=[first['next_cursor']]))
        self.assertFalse({t['id'] for t in first['items']} & {t['id'] for t in second['items']})
        self.assertNotIn('newest', [t['id'] for t in second['items']])
        filtered = self.call(self.b, 'GET', '/tasks', query=dict(q, category=['data-cleaning']))
        self.assertFalse(filtered['has_more'])
        self.assertEqual(2, len(filtered['items']))
        for bad in ['0', '-1', 'nope']:
            with self.assertRaises(Exception) as e:
                self.call(self.b, 'GET', '/tasks', query=dict(q, before=[bad]))
            self.assertEqual(400, e.exception.status)
