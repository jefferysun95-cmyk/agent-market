"""Opt-in email registration. No mailbox grants or harness-specific dependency."""
import hashlib
import hmac
import json
import os
import re
import secrets
import smtplib
import ssl
import time
import uuid
from email.message import EmailMessage


SCHEMA = '''
CREATE TABLE IF NOT EXISTS registration_challenges(
 id TEXT PRIMARY KEY, key_hash TEXT UNIQUE NOT NULL, fingerprint TEXT NOT NULL,
 email_hash TEXT NOT NULL, agent_key TEXT NOT NULL, purpose TEXT NOT NULL,
 profile TEXT NOT NULL, code_hash TEXT NOT NULL, created INTEGER NOT NULL,
 expires INTEGER NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
 finish_key_hash TEXT, agent_id TEXT, peer_hash TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS registration_email ON registration_challenges(email_hash,created);
CREATE INDEX IF NOT EXISTS registration_peer ON registration_challenges(peer_hash,created);
CREATE TABLE IF NOT EXISTS self_service_accounts(
 email_hash TEXT NOT NULL, agent_key TEXT NOT NULL, agent_id TEXT UNIQUE NOT NULL,
 created INTEGER NOT NULL, recovery_blocked INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(email_hash,agent_key));
'''


class RegistrationError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def email_address(value):
    # Deliberately small ASCII policy, no display names, header injection or aliases
    # inferred across providers. Both local/domain case fold is our account policy.
    if not isinstance(value, str) or len(value) > 254 or not re.fullmatch(
            r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}", value):
        raise RegistrationError(400, 'Invalid contact email')
    local, domain = value.lower().split('@')
    if local.startswith('.') or local.endswith('.') or '..' in local or any(
            not label or len(label) > 63 or label.startswith('-') or label.endswith('-') for label in domain.split('.')):
        raise RegistrationError(400, 'Invalid contact email')
    return local + '@' + domain


def request_key(key):
    if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,128}', key):
        raise RegistrationError(400, 'Use a private random Idempotency-Key (16..128 URL-safe characters)')
    return digest(key)


class Registration:
    def __init__(self, store, sender, secret, categories, clock=time.time):
        if not callable(sender) or not isinstance(secret, str) or len(secret) < 32:
            raise ValueError('Registration requires a sender and a separate secret of at least 32 characters')
        self.store, self.sender, self.secret, self.categories, self.clock = store, sender, secret, categories, clock

    def mac(self, value):
        return hmac.new(self.secret.encode(), value.encode(), hashlib.sha256).hexdigest()

    def call(self, method, path, data, key, peer):
        if method != 'POST':
            raise RegistrationError(405, 'Registration requires POST')
        if not isinstance(data, dict):
            raise RegistrationError(400, 'JSON object required')
        if path == '/registration/start':
            return self.start(data, key, peer)
        if path == '/registration/finish':
            return self.finish(data, key)
        raise RegistrationError(404, 'Unknown registration route')

    def start(self, data, key, peer):
        key_hash = request_key(key)
        if set(data) - {'email', 'agent_key', 'purpose', 'name', 'provider', 'capabilities', 'description'}:
            raise RegistrationError(400, 'Unsupported registration fields')
        email = email_address(data.get('email'))
        slot, purpose = data.get('agent_key'), data.get('purpose', 'register')
        if not isinstance(slot, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', slot):
            raise RegistrationError(400, 'agent_key must be a stable lowercase account slot, max 64 characters')
        if purpose not in ('register', 'recover'):
            raise RegistrationError(400, 'Invalid registration purpose')
        profile = {}
        if purpose == 'register':
            for field, limit in (('name', 100), ('provider', 100), ('description', 4000)):
                value = data.get(field, '' if field == 'description' else None)
                if not isinstance(value, str) or len(value) > limit or (field != 'description' and not value.strip()):
                    raise RegistrationError(400, 'Invalid ' + field)
                profile[field] = value
            caps = data.get('capabilities', [])
            if not isinstance(caps, list) or len(caps) > len(self.categories) or any(c not in self.categories for c in caps) or len(set(caps)) != len(caps):
                raise RegistrationError(400, 'Invalid capabilities')
            profile['capabilities'] = caps
        elif set(data) - {'email', 'agent_key', 'purpose'}:
            raise RegistrationError(400, 'Recovery cannot change a profile')
        email_hash = self.mac('email:' + email)
        peer_hash = self.mac('peer:' + str(peer))
        fingerprint = digest(json.dumps([email_hash, slot, purpose, profile], sort_keys=True))
        now, cid, code = int(self.clock()), uuid.uuid4().hex, f'{secrets.randbelow(100_000_000):08d}'
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM registration_challenges WHERE expires < ?', (now - 86400,))
            existing = db.execute('SELECT * FROM registration_challenges WHERE key_hash=?', (key_hash,)).fetchone()
            if existing:
                if existing['fingerprint'] != fingerprint:
                    raise RegistrationError(409, 'Registration key reused with different request')
                if existing['status'] not in ('sent', 'complete') or existing['expires'] <= now:
                    raise RegistrationError(409, 'Challenge unavailable; request a new code with a new key')
                return {'challenge_id': existing['id'], 'expires_at': existing['expires'], 'status': 'verification_required'}
            for column, value, limit in (('email_hash', email_hash, 5), ('peer_hash', peer_hash, 10)):
                count = db.execute(f'SELECT COUNT(*) FROM registration_challenges WHERE {column}=? AND created>?', (value, now - 3600)).fetchone()[0]
                if count >= limit:
                    raise RegistrationError(429, 'Registration request limit reached; try later')
            if db.execute('SELECT COUNT(*) FROM registration_challenges WHERE created>?', (now - 3600,)).fetchone()[0] >= 100:
                raise RegistrationError(429, 'Registration request limit reached; try later')
            db.execute('INSERT INTO registration_challenges(id,key_hash,fingerprint,email_hash,agent_key,purpose,profile,code_hash,created,expires,status,peer_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                       (cid, key_hash, fingerprint, email_hash, slot, purpose, json.dumps(profile), self.mac('code:' + cid + ':' + code), now, now + 600, 'sending', peer_hash))
        # Never hold a database write lock across SMTP or expose sender exceptions.
        try:
            self.sender(email, code, cid)
        except Exception:
            with self.store.connect() as db:
                db.execute("UPDATE registration_challenges SET status='send_failed' WHERE id=?", (cid,))
            raise RegistrationError(503, 'Verification mail outcome uncertain; do not retry the same challenge') from None
        with self.store.connect() as db:
            db.execute("UPDATE registration_challenges SET status='sent' WHERE id=?", (cid,))
        return {'challenge_id': cid, 'expires_at': now + 600, 'status': 'verification_required'}

    def finish(self, data, key):
        finish_key = request_key(key)
        cid, code = data.get('challenge_id'), data.get('code')
        if set(data) != {'challenge_id', 'code'} or not isinstance(cid, str) or not re.fullmatch('[0-9a-f]{32}', cid) or not isinstance(code, str) or not re.fullmatch('[0-9]{8}', code):
            raise RegistrationError(400, 'challenge_id and eight-digit code required')
        now, failure, result = int(self.clock()), None, None
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM registration_challenges WHERE id=?', (cid,)).fetchone()
            if not row or row['expires'] <= now or row['status'] not in ('sent', 'complete') or row['attempts'] >= 5:
                failure = RegistrationError(400, 'Verification unavailable, expired or locked')
            elif not hmac.compare_digest(row['code_hash'], self.mac('code:' + cid + ':' + code)):
                # Commit failed attempts; raising inside connect() would roll back.
                db.execute('UPDATE registration_challenges SET attempts=attempts+1 WHERE id=?', (cid,))
                failure = RegistrationError(400, 'Verification failed')
            elif row['status'] == 'complete':
                if row['finish_key_hash'] != finish_key:
                    failure = RegistrationError(409, 'Code consumed; retry only the identical exchange or request recovery')
                else:
                    token = self.mac('credential:' + cid + ':' + finish_key)
                    agent = db.execute('SELECT * FROM agents WHERE id=?', (row['agent_id'],)).fetchone()
                    if not agent or agent['token_hash'] != digest(token):
                        failure = RegistrationError(409, 'Credential superseded or revoked')
                    else:
                        result = {'agent': json.loads(agent['profile']), 'token': token}
            else:
                account = db.execute('SELECT agent_id,recovery_blocked FROM self_service_accounts WHERE email_hash=? AND agent_key=?', (row['email_hash'], row['agent_key'])).fetchone()
                if row['purpose'] == 'register' and account:
                    failure = RegistrationError(409, 'Account slot already exists; request explicit recovery')
                elif row['purpose'] == 'recover' and not account:
                    failure = RegistrationError(409, 'No self-service account in this slot; legacy identities require operator recovery')
                elif account and account['recovery_blocked']:
                    failure = RegistrationError(403, 'Account recovery blocked; contact operator')
                elif not account and db.execute('SELECT COUNT(*) FROM self_service_accounts WHERE email_hash=?', (row['email_hash'],)).fetchone()[0] >= 3:
                    failure = RegistrationError(429, 'Maximum three Agent slots per verified address')
                else:
                    token = self.mac('credential:' + cid + ':' + finish_key)
                    if account:
                        aid = account['agent_id']
                        profile = json.loads(db.execute('SELECT profile FROM agents WHERE id=?', (aid,)).fetchone()[0])
                        db.execute('UPDATE agents SET token_hash=? WHERE id=?', (digest(token), aid))
                    else:
                        aid, profile = uuid.uuid4().hex, json.loads(row['profile'])
                        from datetime import datetime, timezone
                        profile.update(id=aid, available=True, application_ref='', created_at=datetime.fromtimestamp(now, timezone.utc).isoformat())
                        db.execute('INSERT INTO agents VALUES(?,?,?)', (aid, digest(token), json.dumps(profile)))
                        db.execute('INSERT INTO self_service_accounts(email_hash,agent_key,agent_id,created) VALUES(?,?,?,?)', (row['email_hash'], row['agent_key'], aid, now))
                    db.execute("UPDATE registration_challenges SET status='superseded' WHERE email_hash=? AND agent_key=? AND id<>?", (row['email_hash'], row['agent_key'], cid))
                    db.execute("UPDATE registration_challenges SET status='complete',finish_key_hash=?,agent_id=? WHERE id=?", (finish_key, aid, cid))
                    result = {'agent': profile, 'token': token}
        if failure:
            raise failure
        return result


def from_environment(store, categories):
    """Disabled by default; an explicitly enabled but broken setup fails startup."""
    if os.environ.get('MARKET_SELF_REGISTRATION') != '1':
        return None
    transport_name = os.environ.get('MARKET_MAIL_TRANSPORT', 'smtp')
    sender = email_address(os.environ.get('MARKET_MAIL_FROM', os.environ.get('MARKET_SMTP_FROM', '')))
    if transport_name == 'zoho_api':
        from registration_mail import zoho_sender, ZOHO_ENDPOINT
        send = zoho_sender(sender, os.environ.get('MARKET_ZOHO_API_KEY', ''), os.environ.get('MARKET_ZOHO_API_URL', ZOHO_ENDPOINT))
        return Registration(store, send, os.environ.get('MARKET_REGISTRATION_SECRET', ''), categories)
    if transport_name != 'smtp':
        raise ValueError('Unsupported registration mail transport')
    host = os.environ.get('MARKET_SMTP_HOST', '')
    user = os.environ.get('MARKET_SMTP_USER', '')
    password = os.environ.get('MARKET_SMTP_PASSWORD', '')
    port = int(os.environ.get('MARKET_SMTP_PORT', '465'))
    if not host or not user or not password or port not in (465, 587):
        raise ValueError('Authenticated TLS SMTP configuration required')
    def send(email, code, cid):
        message = EmailMessage()
        message['From'], message['To'] = sender, email
        message['Subject'] = 'Agent Market verification code'
        message.set_content(f'Your Agent Market code is {code}. It expires in 10 minutes.\nRequest: {cid}\nIgnore this message if you did not request it. Never share the code publicly.')
        context = ssl.create_default_context()
        transport = smtplib.SMTP_SSL(host, port, timeout=15, context=context) if port == 465 else smtplib.SMTP(host, port, timeout=15)
        with transport as smtp:
            if port == 587:
                smtp.ehlo(); smtp.starttls(context=context); smtp.ehlo()
            smtp.login(user, password)
            smtp.send_message(message)
    return Registration(store, send, os.environ.get('MARKET_REGISTRATION_SECRET', ''), categories)
