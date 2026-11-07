import concurrent.futures
import tempfile
import unittest
import uuid
from server import Store, Problem


class MarketTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(self.tmp.name + '/test.db')
        self.invite = 'test-invitation'
        self.b = self.register('buyer')
        self.s = self.register('seller')
        self.x = self.register('outsider')
        self.task = self.call(self.b, 'POST', '/tasks', dict(title='Clean rows', category='data-cleaning',
                         brief='Synthetic rows', acceptance='Unique ids', budget='CNY 10', deadline='2030-01-01'))
        self.path = '/tasks/' + self.task['id']

    def tearDown(self):
        self.tmp.cleanup()

    def register(self, name):
        return self.store.call('POST', '/agents', {}, {'name': name, 'provider': name},
                               self.invite, uuid.uuid4().hex, self.invite)['token']

    def call(self, token, method, path, data=None, key=None):
        return self.store.call(method, path, {}, data or {}, token, key or uuid.uuid4().hex, self.invite)

    def fail(self, status, token, method, path, data=None):
        with self.assertRaises(Problem) as context:
            self.call(token, method, path, data)
        self.assertEqual(status, context.exception.status)

    def select(self):
        task = self.call(self.s, 'POST', self.path + '/proposals',
                         dict(price='CNY 5', terms='Deduplication', deadline='2030-01-01'))
        return self.call(self.b, 'POST', self.path + '/select', {'proposal_id': task['proposals'][0]['id']})

    def test_full_lifecycle_private_and_payment(self):
        selected = self.select()
        self.fail(403, self.x, 'GET', self.path)
        self.fail(403, self.b, 'POST', self.path + '/confirm', {'revision': selected['revision']})
        self.fail(409, self.s, 'POST', self.path + '/confirm', {'revision': 0})
        self.call(self.s, 'POST', self.path + '/confirm', {'revision': selected['revision']})
        self.fail(403, self.b, 'POST', self.path + '/select', {'proposal_id': selected['selected']})
        self.fail(409, self.x, 'POST', self.path + '/deliver', {'result': {'ok': True}})
        self.call(self.s, 'POST', self.path + '/deliver', {'result': {'rows': [1, 2]}})
        self.call(self.b, 'POST', self.path + '/request_changes', {'note': 'Add removed count'})
        self.call(self.s, 'POST', self.path + '/deliver', {'result': {'rows': [1, 2], 'removed': 1}})
        self.call(self.b, 'POST', self.path + '/accept', {'note': 'Checked'})
        self.fail(403, self.x, 'POST', self.path + '/payment_received', {'reference': 'fake'})
        self.call(self.b, 'POST', self.path + '/payment_sent', {'reference': 'assertion'})
        self.call(self.s, 'POST', self.path + '/payment_received', {'reference': 'assertion'})
        me = self.call(self.b, 'GET', '/me')
        stats = self.call(self.b, 'GET', '/agents/' + me['id'] + '/reputation')
        self.assertEqual(1, stats['seller_confirmed_received'])
        self.assertGreater(len(self.call(self.b, 'GET', self.path + '/events')), 5)

    def test_idempotency_concurrent_and_conflict(self):
        payload = dict(price='CNY 5', terms='Deduplicate', deadline='2030-01-01')
        def submit(_):
            return self.call(self.s, 'POST', self.path + '/proposals', payload, 'same-request')
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(submit, range(4)))
        self.assertEqual(1, len({r['proposals'][0]['id'] for r in results}))
        with self.assertRaises(Problem) as context:
            self.call(self.s, 'POST', self.path + '/proposals', payload | {'price': 'CNY 6'}, 'same-request')
        self.assertEqual(409, context.exception.status)
        self.assertEqual(1, len(self.call(self.b, 'GET', self.path)['proposals']))

    def test_auth_validation_cancellation_and_quote_privacy(self):
        self.fail(401, 'wrong', 'GET', '/agents')
        self.fail(400, self.b, 'POST', '/tasks', {'title': 'Incomplete'})
        self.select()
        self.call(self.b, 'POST', self.path + '/cancel')
        self.fail(403, self.s, 'POST', self.path + '/confirm', {'revision': 1})

    def test_other_quotes_not_visible(self):
        for token in [self.s, self.x]:
            self.call(token, 'POST', self.path + '/proposals', dict(price='CNY 1', terms='Scope', deadline='soon'))
        view = self.call(self.s, 'GET', self.path)
        self.assertEqual(1, len(view['proposals']))
        self.assertEqual(2, len(self.call(self.b, 'GET', self.path)['proposals']))

    def test_persistence(self):
        self.store = Store(self.tmp.name + '/test.db')
        self.assertEqual('open', self.call(self.b, 'GET', self.path)['status'])


if __name__ == '__main__':
    unittest.main()
