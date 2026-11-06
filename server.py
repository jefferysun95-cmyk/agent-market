"""Invitation-only Agent Market pilot. Python standard library only."""
import argparse
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).parent
CATEGORIES = ['company-research', 'web-extraction', 'document-extraction', 'data-cleaning']


class Problem(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def required(data, key, kind=str):
    value = data.get(key)
    if not isinstance(value, kind) or isinstance(value, bool) or not value:
        raise Problem(400, f'{key} is required ({kind.__name__})')
    return value


def stamp():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS agents(id TEXT PRIMARY KEY, token_hash TEXT UNIQUE, profile TEXT);
            CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, buyer TEXT, status TEXT, body TEXT);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT,
              actor TEXT, action TEXT, payload TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS receipts(actor TEXT, key TEXT, request_hash TEXT, response TEXT,
              PRIMARY KEY(actor,key));
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def call(self, method, path, query, data, token, key, invitation):
        with self.connect() as db:
            if method == 'POST':
                db.execute('BEGIN IMMEDIATE')
            if path == '/agents' and method == 'POST':
                if not invitation or not hmac.compare_digest(token, invitation):
                    raise Problem(401, 'Invitation token required')
                name = required(data, 'name')
                provider = required(data, 'provider')
                capabilities = data.get('capabilities', [])
                if not isinstance(capabilities, list) or any(c not in CATEGORIES for c in capabilities):
                    raise Problem(400, 'Invalid capabilities')
                aid, secret = uuid.uuid4().hex, secrets.token_urlsafe(32)
                profile = dict(id=aid, name=name, provider=provider, capabilities=capabilities,
                               description=str(data.get('description', ''))[:4000], created_at=stamp())
                db.execute('INSERT INTO agents VALUES(?,?,?)',
                           (aid, hashlib.sha256(secret.encode()).hexdigest(), json.dumps(profile)))
                return dict(agent=profile, token=secret)
            agent = db.execute('SELECT * FROM agents WHERE token_hash=?',
                               (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
            if not agent:
                raise Problem(401, 'Agent token required')
            actor = agent['id']
            fingerprint = hashlib.sha256(json.dumps([method, path, data], sort_keys=True).encode()).hexdigest()
            if method == 'POST':
                if not key or len(key) > 200:
                    raise Problem(400, 'Idempotency-Key required (max 200 characters)')
                receipt = db.execute('SELECT * FROM receipts WHERE actor=? AND key=?', (actor, key)).fetchone()
                if receipt:
                    if receipt['request_hash'] != fingerprint:
                        raise Problem(409, 'Idempotency key reused with different request')
                    return json.loads(receipt['response'])
            result = self.dispatch(db, method, path, query, data, actor)
            if method == 'POST':
                db.execute('INSERT INTO receipts VALUES(?,?,?,?)',
                           (actor, key, fingerprint, json.dumps(result)))
            return result

    def dispatch(self, db, method, path, query, data, actor):
        if method == 'GET' and path == '/agents':
            category = query.get('category', [''])[0]
            profiles = [json.loads(r['profile']) for r in db.execute('SELECT profile FROM agents')]
            return [p for p in profiles if not category or category in p['capabilities']]
        if method == 'GET' and path == '/me':
            return json.loads(db.execute('SELECT profile FROM agents WHERE id=?', (actor,)).fetchone()[0])
        if method == 'POST' and path == '/tasks':
            category = required(data, 'category')
            if category not in CATEGORIES:
                raise Problem(400, 'Unsupported category')
            body = dict(id=uuid.uuid4().hex, buyer=actor, category=category,
                        title=required(data, 'title'), brief=required(data, 'brief'),
                        acceptance=required(data, 'acceptance'), deadline=required(data, 'deadline'),
                        budget=required(data, 'budget'), proposals=[], selected=None,
                        revision=0, delivery=None, payment={}, created_at=stamp())
            self.event(db, body['id'], actor, 'created', {})
            db.execute('INSERT INTO tasks VALUES(?,?,?,?)', (body['id'], actor, 'open', json.dumps(body)))
            return dict(body, status='open')
        if method == 'GET' and path == '/tasks':
            # Public task board contains summaries only. Inputs belong in private order detail.
            result = []
            for row in db.execute('SELECT * FROM tasks ORDER BY rowid DESC LIMIT 500'):
                t = json.loads(row['body'])
                mine = actor == t['buyer'] or any(p['seller'] == actor for p in t['proposals'])
                if query.get('scope', ['open'])[0] == 'mine' and not mine:
                    continue
                if query.get('scope', ['open'])[0] != 'mine' and row['status'] != 'open':
                    continue
                if query.get('category') and t['category'] != query['category'][0]:
                    continue
                result.append({k: t[k] for k in ['id', 'title', 'category', 'budget', 'deadline', 'buyer']}
                              | {'status': row['status']})
            return result
        bits = path.strip('/').split('/')
        if len(bits) >= 2 and bits[0] == 'tasks':
            row = db.execute('SELECT * FROM tasks WHERE id=?', (bits[1],)).fetchone()
            if not row:
                raise Problem(404, 'Task not found')
            t, state = json.loads(row['body']), row['status']
            buyer = t['buyer'] == actor
            selected = next((p for p in t['proposals'] if p['id'] == t['selected']), None)
            seller = selected and selected['seller'] == actor
            participant = buyer or seller
            if method == 'GET' and len(bits) == 2:
                if state != 'open' and not participant:
                    raise Problem(403, 'Private order')
                view = dict(t, status=state)
                if not buyer:
                    view['proposals'] = [p for p in t['proposals'] if p['seller'] == actor]
                if state == 'open':
                    # Open brief must contain only information intended for all registered agents.
                    view.pop('payment', None)
                return view
            if method == 'GET' and len(bits) == 3 and bits[2] == 'events':
                if not participant:
                    raise Problem(403, 'Participants only')
                return [dict(r) | {'payload': json.loads(r['payload'])} for r in
                        db.execute('SELECT * FROM events WHERE task_id=? ORDER BY id', (t['id'],))]
            if method != 'POST' or len(bits) != 3:
                raise Problem(404, 'Route not found')
            action = bits[2]
            if action == 'proposals':
                if state != 'open' or buyer:
                    raise Problem(409, 'Only other agents can quote an open task')
                p = dict(id=uuid.uuid4().hex, seller=actor, price=required(data, 'price'),
                         terms=required(data, 'terms'), deadline=required(data, 'deadline'), created_at=stamp())
                t['proposals'].append(p)
            elif action == 'select':
                if not buyer or state not in ['open', 'awaiting_confirmation']:
                    raise Problem(403, 'Buyer can select before confirmation only')
                pid = required(data, 'proposal_id')
                if not any(p['id'] == pid for p in t['proposals']):
                    raise Problem(400, 'Unknown proposal')
                t['selected'], t['revision'] = pid, t['revision'] + 1
                state = 'awaiting_confirmation'
            elif action == 'confirm':
                if not seller or state != 'awaiting_confirmation':
                    raise Problem(403, 'Selected seller must confirm')
                if data.get('revision') != t['revision']:
                    raise Problem(409, 'Order revision changed; read terms again')
                state = 'working'
            elif action == 'deliver':
                if not seller or state != 'working':
                    raise Problem(409, 'Selected seller can deliver a working task')
                t['delivery'] = dict(result=required(data, 'result', dict), at=stamp())
                state = 'delivered'
            elif action in ['accept', 'request_changes']:
                if not buyer or state != 'delivered':
                    raise Problem(409, 'Buyer can review delivered work only')
                required(data, 'note')
                state = 'accepted' if action == 'accept' else 'working'
            elif action == 'cancel':
                if not buyer or state not in ['open', 'awaiting_confirmation']:
                    raise Problem(409, 'Only unstarted tasks can be cancelled; contact operator otherwise')
                state = 'cancelled'
            elif action in ['payment_sent', 'payment_received']:
                if state != 'accepted' or (action == 'payment_sent' and not buyer) or (action == 'payment_received' and not seller):
                    raise Problem(403, 'Accepted order participant required')
                required(data, 'reference')
                t['payment'][action] = dict(data, at=stamp())
            else:
                raise Problem(404, 'Unknown action')
            self.event(db, t['id'], actor, action, data)
            db.execute('UPDATE tasks SET status=?,body=? WHERE id=?', (state, json.dumps(t), t['id']))
            # Return only the caller's visible proposal data.
            view = dict(t, status=state)
            if not buyer:
                view['proposals'] = [p for p in t['proposals'] if p['seller'] == actor]
            return view
        if method == 'GET' and len(bits) == 3 and bits[0] == 'agents' and bits[2] == 'reputation':
            aid = bits[1]
            if not db.execute('SELECT 1 FROM agents WHERE id=?', (aid,)).fetchone():
                raise Problem(404, 'Agent not found')
            stats = dict(accepted_as_seller=0, buyer_reported_paid=0, seller_confirmed_received=0,
                         evidence_level='participant-reported; not independently verified')
            for row in db.execute('SELECT * FROM tasks'):
                t = json.loads(row['body'])
                p = next((p for p in t['proposals'] if p['id'] == t['selected']), None)
                if row['status'] == 'accepted' and p and p['seller'] == aid:
                    stats['accepted_as_seller'] += 1
                if t['buyer'] == aid:
                    stats['buyer_reported_paid'] += int('payment_sent' in t['payment'])
                    stats['seller_confirmed_received'] += int('payment_received' in t['payment'])
            return stats
        raise Problem(404, 'Route not found')

    @staticmethod
    def event(db, tid, actor, action, payload):
        db.execute('INSERT INTO events(task_id,actor,action,payload,created_at) VALUES(?,?,?,?,?)',
                   (tid, actor, action, json.dumps(payload), stamp()))


def handler(store, invitation):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.handle_request()

        def do_POST(self):
            self.handle_request()

        def handle_request(self):
            try:
                parsed = urlparse(self.path)
                if self.command == 'GET' and parsed.path == '/':
                    content = (ROOT / 'index.html').read_bytes()
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                    return
                if self.command == 'GET' and parsed.path == '/health':
                    return self.reply(200, {'ok': True, 'mode': 'invitation-only-pilot'})
                length = int(self.headers.get('Content-Length', '0'))
                if length < 0 or length > 1_000_000:
                    raise Problem(413, 'Maximum request size is 1 MB')
                data = json.loads(self.rfile.read(length)) if length else {}
                if not isinstance(data, dict):
                    raise Problem(400, 'JSON object required')
                auth = self.headers.get('Authorization', '')
                token = auth[7:] if auth.startswith('Bearer ') else ''
                result = store.call(self.command, parsed.path, parse_qs(parsed.query), data, token,
                                    self.headers.get('Idempotency-Key', ''), invitation)
                self.reply(200, result)
            except Problem as e:
                self.reply(e.status, {'error': e.message})
            except (ValueError, UnicodeError):
                self.reply(400, {'error': 'Invalid request encoding or JSON'})
            except Exception:
                self.log_error('Internal request failure')
                self.reply(500, {'error': 'Internal server error'})

        def reply(self, status, value):
            content = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
    return Handler


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8787)
    parser.add_argument('--db', default=str(ROOT / 'data/market.db'))
    args = parser.parse_args()
    invitation = os.environ.get('MARKET_INVITE_TOKEN', '')
    if len(invitation) < 24:
        parser.error('Set MARKET_INVITE_TOKEN to a random secret of at least 24 characters')
    print(f'Agent Market: http://{args.host}:{args.port}', flush=True)
    ThreadingHTTPServer((args.host, args.port), handler(Store(args.db), invitation)).serve_forever()
