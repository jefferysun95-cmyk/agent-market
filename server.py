"""Invitation-only Agent Market pilot. Python standard library only."""
import argparse
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import uuid
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).parent
CATEGORIES = ['company-research', 'web-extraction', 'document-extraction', 'data-cleaning']
VERSION = '1.1.0-alpha.4'


def receipt_matches(manifest):
    """Participant-reported binding, not independent proof of mailbox access."""
    evidence = manifest.get('receipt', {})
    return bool(manifest.get('sent_at') and manifest.get('received_at')
                and manifest.get('message_id')
                and evidence.get('observed_message_id') == manifest['message_id']
                and evidence.get('observed_from') == manifest['from']
                and evidence.get('observed_to') == manifest['to']
                and evidence.get('files') == manifest['files']
                and evidence.get('actor') == manifest['recipient'])


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
            CREATE TABLE IF NOT EXISTS admin_receipts(key TEXT PRIMARY KEY, fingerprint TEXT, agent_id TEXT, operation TEXT);
            CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY AUTOINCREMENT, recipient TEXT,
              task_id TEXT, action TEXT, created_at TEXT);
            CREATE INDEX IF NOT EXISTS notifications_recipient ON notifications(recipient,id);
            CREATE TABLE IF NOT EXISTS inbox_cursors(agent_id TEXT PRIMARY KEY, cursor INTEGER NOT NULL);
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
            if path.startswith('/admin/') or (path == '/agents' and method == 'POST'):
                if not invitation or not hmac.compare_digest(token, invitation):
                    raise Problem(401, 'Operator credential required')
                return self.admin(db,method,path,data,key,invitation)
            agent = db.execute('SELECT * FROM agents WHERE token_hash=?',
                               (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
            if not agent:
                raise Problem(401, 'Agent token missing, invalid or revoked')
            actor = agent['id']
            fingerprint = hashlib.sha256(json.dumps([method, path, data], sort_keys=True).encode()).hexdigest()
            if method == 'POST':
                if not key or len(key) > 200:
                    raise Problem(400, 'Idempotency-Key required (max 200 characters)')
                receipt = db.execute('SELECT * FROM receipts WHERE actor=? AND key=?', (actor, key)).fetchone()
                if receipt:
                    if receipt['request_hash'] != fingerprint:
                        raise Problem(409, 'Idempotency key reused with different request')
                    result=json.loads(receipt['response'])
                    # Old receipts must not expose a now-private order to a deselected seller.
                    if path.startswith('/tasks/'):
                        row=db.execute('SELECT body,status FROM tasks WHERE id=?',(path.split('/')[2],)).fetchone()
                        if row:
                            current=json.loads(row['body'])
                            selected=next((p for p in current['proposals'] if p['id']==current['selected']),None)
                            if row['status']!='open' and current['buyer']!=actor and (not selected or selected['seller']!=actor):
                                raise Problem(403,'Order access changed')
                    return result
            result = self.dispatch(db, method, path, query, data, actor)
            if method == 'POST':
                db.execute('INSERT INTO receipts VALUES(?,?,?,?)',
                           (actor, key, fingerprint, json.dumps(result)))
            return result

    def admin(self,db,method,path,data,key,invitation):
        if method=='GET' and path=='/admin/agents':
            return [json.loads(r[0]) for r in db.execute('SELECT profile FROM agents')]
        if method!='POST':raise Problem(404,'Unknown operator route')
        if not key or len(key)>200:raise Problem(400,'Idempotency-Key required for operator writes')
        fingerprint=hashlib.sha256(json.dumps([path,data],sort_keys=True).encode()).hexdigest()
        secret=hmac.new(invitation.encode(), ('agent-token-v1:'+key+':'+fingerprint).encode(),hashlib.sha256).hexdigest()
        receipt=db.execute('SELECT * FROM admin_receipts WHERE key=?',(key,)).fetchone()
        if receipt:
            if receipt['fingerprint']!=fingerprint:raise Problem(409,'Operator key reused with different request')
            row=db.execute('SELECT * FROM agents WHERE id=?',(receipt['agent_id'],)).fetchone()
            if receipt['operation']=='revoke':return {'revoked':True,'agent_id':receipt['agent_id']}
            if row['token_hash']!=hashlib.sha256(secret.encode()).hexdigest():
                raise Problem(409,'Credential superseded; do not replay old issuance')
            return {'agent':json.loads(row['profile']),'token':secret}
        if path=='/agents':
                name = required(data, 'name')
                provider = required(data, 'provider')
                capabilities = data.get('capabilities', [])
                if not isinstance(capabilities, list) or any(c not in CATEGORIES for c in capabilities):
                    raise Problem(400, 'Invalid capabilities')
                aid = uuid.uuid4().hex
                profile = dict(id=aid, name=name, provider=provider, capabilities=capabilities,
                               description=str(data.get('description', ''))[:4000], available=True,
                               application_ref=str(data.get('application_ref',''))[:300], created_at=stamp())
                db.execute('INSERT INTO agents VALUES(?,?,?)',
                           (aid, hashlib.sha256(secret.encode()).hexdigest(), json.dumps(profile)))
                db.execute('INSERT INTO admin_receipts VALUES(?,?,?,?)',(key,fingerprint,aid,'register'))
                return dict(agent=profile, token=secret)
        bits=path.strip('/').split('/')
        if len(bits)==4 and bits[:2]==['admin','agents'] and bits[3] in ['rotate','revoke']:
            aid,op=bits[2],bits[3]
            row=db.execute('SELECT * FROM agents WHERE id=?',(aid,)).fetchone()
            if not row:raise Problem(404,'Agent not found')
            token_hash=hashlib.sha256(secret.encode()).hexdigest() if op=='rotate' else 'revoked:'+uuid.uuid4().hex
            db.execute('UPDATE agents SET token_hash=? WHERE id=?',(token_hash,aid))
            db.execute('INSERT INTO admin_receipts VALUES(?,?,?,?)',(key,fingerprint,aid,op))
            return {'agent':json.loads(row['profile']),'token':secret} if op=='rotate' else {'revoked':True,'agent_id':aid}
        raise Problem(404,'Unknown operator route')

    def dispatch(self, db, method, path, query, data, actor):
        if method=='POST' and path=='/me/profile':
            profile=json.loads(db.execute('SELECT profile FROM agents WHERE id=?',(actor,)).fetchone()[0])
            if 'capabilities' in data:
                caps=data['capabilities']
                if not isinstance(caps,list) or any(c not in CATEGORIES for c in caps):raise Problem(400,'Invalid capabilities')
                profile['capabilities']=caps
            if 'available' in data:
                if type(data['available']) is not bool:raise Problem(400,'available must be boolean')
                profile['available']=data['available']
            if 'description' in data:profile['description']=str(data['description'])[:4000]
            db.execute('UPDATE agents SET profile=? WHERE id=?',(json.dumps(profile),actor))
            return profile
        if method=='GET' and path=='/inbox':
            saved=db.execute('SELECT cursor FROM inbox_cursors WHERE agent_id=?',(actor,)).fetchone()
            try:after=int(query.get('after',[str(saved[0] if saved else 0)])[0])
            except ValueError:raise Problem(400,'Invalid inbox cursor')
            if after<0:raise Problem(400,'Invalid inbox cursor')
            rows=db.execute('SELECT id,task_id,action,created_at FROM notifications WHERE recipient=? AND id>? ORDER BY id LIMIT 100',(actor,after)).fetchall()
            return {'items':[dict(r) for r in rows], 'next_cursor':rows[-1]['id'] if rows else after}
        if method=='POST' and path=='/inbox/ack':
            cursor=data.get('cursor')
            if type(cursor) is not int or cursor<0:raise Problem(400,'Invalid inbox cursor')
            if cursor and not db.execute('SELECT 1 FROM notifications WHERE recipient=? AND id=?',(actor,cursor)).fetchone():raise Problem(400,'Cursor not in own inbox')
            db.execute('INSERT INTO inbox_cursors VALUES(?,?) ON CONFLICT(agent_id) DO UPDATE SET cursor=MAX(cursor,excluded.cursor)',(actor,cursor))
            return {'acknowledged':cursor}
        if method == 'GET' and path == '/agents':
            category = query.get('category', [''])[0]
            profiles = [json.loads(r['profile']) for r in db.execute('SELECT profile FROM agents')]
            return [p for p in profiles if p.get('available',True) and (not category or category in p['capabilities'])]
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
            paged = query.get('page', ['false'])[0] == 'true'
            try:
                before = int(query.get('before', ['9223372036854775807'])[0])
                limit = int(query.get('limit', ['100'])[0]) if paged else 500
            except ValueError:
                raise Problem(400, 'Invalid task cursor or limit')
            if before < 1 or (paged and not 1 <= limit <= 100):
                raise Problem(400, 'Invalid task cursor or limit')
            cursors = []
            # Filter before capping results. Descending rowid is stable for inserts;
            # callers must still re-read mutable order state before executing.
            for row in db.execute('SELECT rowid AS cursor,* FROM tasks WHERE rowid<? ORDER BY rowid DESC', (before,)):
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
                cursors.append(row['cursor'])
                if len(result) > limit:
                    break
            if paged:
                return {'items': result[:limit], 'has_more': len(result) > limit,
                        'next_cursor': str(cursors[limit-1]) if len(result) > limit else None,
                        'observed_at': stamp()}
            return result[:limit]
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
            if method == 'GET' and (len(bits) == 2 or len(bits) == 3 and bits[2] == 'progress'):
                if state != 'open' and not participant:
                    raise Problem(403, 'Private order')
                view = dict(t, status=state)
                if not buyer:
                    view['proposals'] = [p for p in t['proposals'] if p['seller'] == actor]
                if state == 'open':
                    # Open brief must contain only information intended for all registered agents.
                    view.pop('payment', None)
                from progress import describe
                # Same visibility as /events: competitors' quote activity and
                # private mail events cannot leak through diagnostic metadata.
                event = db.execute('SELECT id,created_at FROM events WHERE task_id=? '
                    'AND (? OR (actor IN (?,?) AND action NOT LIKE ?)) ORDER BY id DESC LIMIT 1',
                    (t['id'], buyer, actor, t['buyer'], 'mail-%')).fetchone()
                view['progress'] = describe(view, actor, event)
                if len(bits) == 3:
                    return view['progress']
                return view
            if method == 'GET' and len(bits) == 3 and bits[2] == 'events':
                if not participant:
                    raise Problem(403, 'Participants only')
                return [dict(r) | {'payload': json.loads(r['payload'])} for r in
                        db.execute('SELECT * FROM events WHERE task_id=? ORDER BY id', (t['id'],))
                        if (buyer or r['actor'] in [actor,t['buyer']])
                        and (buyer or not r['action'].startswith('mail-'))]
            if method != 'POST' or len(bits) != 3:
                raise Problem(404, 'Route not found')
            action = bits[2]
            if action in ['mail-config','mail-manifests','mail-sent','mail-received']:
                if not participant:raise Problem(403,'Order participants only')
                result=self.mail_action(t,state,actor,buyer,seller,action,data)
                self.event(db,t['id'],actor,action,data)
                db.execute('UPDATE tasks SET body=? WHERE id=?',(json.dumps(t),t['id']))
                return result
            if action == 'proposals':
                if state != 'open' or buyer:
                    raise Problem(409, 'Only other agents can quote an open task')
                profile=json.loads(db.execute('SELECT profile FROM agents WHERE id=?',(actor,)).fetchone()[0])
                if not profile.get('available',True):raise Problem(409,'Agent paused for new proposals')
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
                t.pop('mail', None)
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
                manifests=[m for m in t.get('mail',{}).get('manifests',[]) if m['kind']=='delivery']
                manifest_id=manifests[-1]['id'] if manifests else None
                if t.get('delivery') and manifest_id and t['delivery'].get('manifest_id')==manifest_id:
                    raise Problem(409,'Reworked file delivery requires a new manifest')
                t['delivery'] = dict(result=required(data, 'result', dict), at=stamp(),manifest_id=manifest_id)
                state = 'delivered'
            elif action in ['accept', 'request_changes']:
                if not buyer or state != 'delivered':
                    raise Problem(409, 'Buyer can review delivered work only')
                required(data, 'note')
                if action=='accept':
                    manifests=t.get('mail',{}).get('manifests',[])
                    for kind in ('input','delivery'):
                        latest=next((m for m in reversed(manifests) if m['kind']==kind),None)
                        if latest and not receipt_matches(latest):
                            raise Problem(409,'Latest '+kind+' mail requires matching observed receipt evidence; legacy timestamps alone are insufficient')
                    deliveries=[m for m in manifests if m['kind']=='delivery']
                    if deliveries and t['delivery'].get('manifest_id')!=deliveries[-1]['id']:raise Problem(409,'Latest mail delivery not bound to this result')
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
    def mail_action(t,state,actor,buyer,seller,action,data):
        mail=t.setdefault('mail',{'addresses':{},'manifests':[]})
        if action=='mail-config':
            if state!='awaiting_confirmation':raise Problem(409,'Mailboxes can only be configured before seller confirmation')
            address=required(data,'address')
            if len(address)>254 or not re.fullmatch(r'[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',address):raise Problem(400,'Invalid mailbox')
            mail['addresses'][actor]=address.lower()
            return {'configured':True}
        if state not in ['working','delivered']:raise Problem(409,'Mail transfer requires an active order')
        selected=next(p for p in t['proposals'] if p['id']==t['selected'])
        for party in [t['buyer'],selected['seller']]:
            if party not in mail['addresses']:raise Problem(409,'Both parties must configure mailboxes')
        if action=='mail-manifests':
            kind=required(data,'kind')
            if kind not in ['input','delivery'] or (kind=='input' and not buyer) or (kind=='delivery' and not seller):raise Problem(403,'Wrong manifest sender')
            files=required(data,'files',list)
            if not 1<=len(files)<=10:raise Problem(400,'Require one to ten attachments')
            clean=[];names=set()
            for f in files:
                if not isinstance(f,dict):raise Problem(400,'Invalid attachment')
                name=required(f,'name'); digest=required(f,'sha256');size=f.get('size')
                if len(name)>120 or not re.fullmatch(r'[A-Za-z0-9_-]+\.(csv|json)',name) or name in names:raise Problem(400,'Unique safe CSV/JSON filenames required')
                if type(size) is not int or not 0<size<=2_000_000:raise Problem(400,'Attachment size must be 1..2000000 bytes')
                if not re.fullmatch('[a-f0-9]{64}',digest):raise Problem(400,'Invalid SHA256')
                names.add(name);clean.append({'name':name,'sha256':digest,'size':size})
            if sum(f['size'] for f in clean)>5_000_000:raise Problem(400,'Attachment total exceeds 5 MB')
            if kind=='delivery' and state!='working':raise Problem(409,'Delivery manifest requires working task')
            if kind=='input' and any(m['kind']=='delivery' for m in mail['manifests']):raise Problem(409,'Input changes after delivery require a new agreement')
            recipient=selected['seller'] if buyer else t['buyer']
            manifest={'id':uuid.uuid4().hex,'kind':kind,'version':1+sum(m['kind']==kind for m in mail['manifests']),
                      'sender':actor,'recipient':recipient,'from':mail['addresses'][actor],
                      'to':mail['addresses'][recipient],'files':clean,'created_at':stamp()}
            mail['manifests'].append(manifest)
            return manifest
        manifest=next((m for m in mail['manifests'] if m['id']==data.get('manifest_id')),None)
        if not manifest:raise Problem(404,'Manifest not found')
        latest=next(m for m in reversed(mail['manifests']) if m['kind']==manifest['kind'])
        if manifest!=latest:raise Problem(409,'Superseded manifest')
        if action=='mail-sent':
            if manifest['sender']!=actor:raise Problem(403,'Sender only')
            message=required(data,'message_id')
            if len(message)>300 or '\r' in message or '\n' in message:raise Problem(400,'Invalid Message-ID')
            if manifest.get('message_id') and manifest['message_id']!=message:raise Problem(409,'Manifest already sent; inspect before retrying')
            manifest.update(message_id=message,sent_at=manifest.get('sent_at',stamp()))
        else:
            if manifest['recipient']!=actor:raise Problem(403,'Recipient only')
            if not manifest.get('sent_at'):raise Problem(409,'Sender has not recorded transmission')
            if data.get('files')!=manifest['files']:raise Problem(409,'File manifest mismatch')
            evidence={key:required(data,key) for key in ('observed_message_id','observed_from','observed_to')}
            if (evidence['observed_message_id']!=manifest['message_id']
                    or evidence['observed_from']!=manifest['from'] or evidence['observed_to']!=manifest['to']):
                raise Problem(409,'Observed mail headers do not match sender receipt and agreed mailboxes')
            evidence.update(files=manifest['files'],actor=actor,evidence_level='recipient-reported; not independently verified')
            if manifest.get('receipt') and manifest['receipt']!=evidence:raise Problem(409,'Receipt evidence already recorded; inspect before retrying')
            manifest['receipt']=evidence
            manifest['received_at']=manifest.get('received_at',stamp())
        return manifest

    @staticmethod
    def event(db, tid, actor, action, payload):
        db.execute('INSERT INTO events(task_id,actor,action,payload,created_at) VALUES(?,?,?,?,?)',
                   (tid, actor, action, json.dumps(payload), stamp()))
        row=db.execute('SELECT body FROM tasks WHERE id=?',(tid,)).fetchone()
        if row:
            t=json.loads(row['body']);recipients={t['buyer']}
            pid=payload.get('proposal_id') if action=='select' else t.get('selected')
            p=next((p for p in t['proposals'] if p['id']==pid),None)
            if p:recipients.add(p['seller'])
            if action=='select':
                prior=next((p for p in t['proposals'] if p['id']==t.get('selected')),None)
                if prior:recipients.add(prior['seller'])
            for recipient in recipients-{actor}:
                db.execute('INSERT INTO notifications(recipient,task_id,action,created_at) VALUES(?,?,?,?)',(recipient,tid,action,stamp()))


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
                    return self.reply(200, {'ok': True, 'mode': 'invitation-only-pilot','version':VERSION})
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
