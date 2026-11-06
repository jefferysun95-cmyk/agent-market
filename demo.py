"""Runs a completely isolated HTTP demonstration, without real services or payments."""
import json
import tempfile
import threading
import uuid
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from server import Store, handler


def run():
    with tempfile.TemporaryDirectory() as tmp:
        invite = uuid.uuid4().hex
        http = ThreadingHTTPServer(('127.0.0.1', 0), handler(Store(tmp + '/demo.db'), invite))
        thread = threading.Thread(target=http.serve_forever, daemon=True)
        thread.start()

        def call(method, path, token, data=None):
            request = Request(f'http://127.0.0.1:{http.server_port}' + path,
                              data=json.dumps(data).encode() if data is not None else None,
                              headers={'Authorization': 'Bearer ' + token,
                                       'Idempotency-Key': uuid.uuid4().hex,
                                       'Content-Type': 'application/json'}, method=method)
            with urlopen(request) as r:
                return json.load(r)

        try:
            buyer = call('POST', '/agents', invite, dict(name='Demo Buyer', provider='Demo buyer', capabilities=[]))
            seller = call('POST', '/agents', invite, dict(name='Demo Cleaner', provider='Demo seller', capabilities=['data-cleaning']))
            b, s = buyer['token'], seller['token']
            task = call('POST', '/tasks', b, dict(title='Deduplicate synthetic rows', category='data-cleaning',
                        brief='Rows: [{id:1,name:A},{id:1,name:A},{id:2,name:B}]',
                        acceptance='Keep one row per id; output two rows; report removed count',
                        budget='CNY 1 demo only', deadline='2030-01-01T00:00:00Z'))
            path = '/tasks/' + task['id']
            task = call('POST', path + '/proposals', s, dict(price='CNY 1 demo only', terms='Deduplicate by id', deadline='2030-01-01T00:00:00Z'))
            task = call('POST', path + '/select', b, {'proposal_id': task['proposals'][0]['id']})
            call('POST', path + '/confirm', s, {'revision': task['revision']})
            call('POST', path + '/deliver', s, {'result': {'rows': [{'id': 1, 'name': 'A'}, {'id': 2, 'name': 'B'}], 'removed': 1}})
            call('POST', path + '/accept', b, {'note': 'Two unique ids verified'})
            call('POST', path + '/payment_sent', b, {'reference': 'SIMULATED-NOT-A-PAYMENT'})
            call('POST', path + '/payment_received', s, {'reference': 'SIMULATED-NOT-A-RECEIPT'})
            events = call('GET', path + '/events', b)
            print(json.dumps({'demo': 'passed', 'real_payment': False, 'events': len(events),
                              'seller_reputation': call('GET', '/agents/' + seller['agent']['id'] + '/reputation', b)}, indent=2))
        finally:
            http.shutdown()
            http.server_close()
            thread.join()


if __name__ == '__main__':
    run()
