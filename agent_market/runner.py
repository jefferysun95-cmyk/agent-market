"""Local, task-bound runner core. No mailbox access or arbitrary host execution.

The OS lock owns the instance, SQLite owns durable intent, and the platform
remains the sole authority for business state. Policies are local user input.
"""
from contextlib import contextmanager, closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
from urllib.error import HTTPError, URLError

from .market import request, validate_base, MissingCredential


class RunnerError(ValueError):
    pass


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def validate_policy(policy):
    required = {'actor_id', 'task_id', 'url', 'expires_at', 'max_seconds', 'interval_seconds', 'steps'}
    if not required <= set(policy) or set(policy)-required-{'host','mail'}:
        raise RunnerError('Policy fields must match the documented schema.')
    if 'host' in policy:
        from .host import validate_host
        validate_host(policy['host'])
    if 'mail' in policy:
        mail=policy['mail']
        if not isinstance(mail,dict) or set(mail)!={'credentials_file'} or not Path(mail['credentials_file']).is_absolute():
            raise RunnerError('Mail configuration holds only an absolute credential-file reference.')
    for name in ('actor_id', 'task_id'):
        if not isinstance(policy[name], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', policy[name]):
            raise RunnerError('Invalid policy identity.')
    validate_base(policy['url'])
    expiry = datetime.fromisoformat(policy['expires_at'])
    if expiry.tzinfo is None:
        raise RunnerError('Policy expiry needs a timezone.')
    for key, lo, hi in (('max_seconds', 1, 86400), ('interval_seconds', 1, 60)):
        if type(policy[key]) is not int or not lo <= policy[key] <= hi:
            raise RunnerError('Policy time budget is out of range.')
    if not isinstance(policy['steps'], list) or len(policy['steps']) > 100:
        raise RunnerError('Policy must contain at most 100 steps.')
    ids, keys = set(), set()
    # Mail observations must come from the mail adapter, never canned policy JSON.
    allowed = {'proposals', 'select', 'mail-config', 'confirm', 'deliver', 'accept', 'request_changes', 'cancel'}
    for step in policy['steps']:
        if set(step) != {'id', 'phase', 'revision', 'kind', 'action', 'body', 'key'}:
            raise RunnerError('Invalid step fields.')
        if not isinstance(step['id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', step['id']) or step['id'] in ids:
            raise RunnerError('Step IDs must be unique identifiers.')
        ids.add(step['id'])
        if step['kind'] not in ('api', 'handoff', 'mail_send','mail_receive') or step['action'] not in allowed | {'process_work','mail-manifests','mail-sent','mail-received'}:
            raise RunnerError('Unsupported action or handler.')
        if step['kind'] == 'api' and step['action'] not in allowed:
            raise RunnerError('Business processing requires a host handler.')
        if not isinstance(step['phase'], str) or type(step['revision']) is not int or step['revision'] < 0:
            raise RunnerError('Each step binds a phase and revision.')
        key = step['key']
        if not isinstance(key, str) or not re.fullmatch(r'[\x21-\x7e]{1,200}', key) or key in keys:
            raise RunnerError('Steps need unique explicit stable keys.')
        keys.add(key)
        if not isinstance(step['body'], dict):
            raise RunnerError('Step body must be an object.')
        if step['kind'] in ('mail_send','mail_receive'):
            body=step['body']
            if 'mail' not in policy or step['action']!=('mail-sent' if step['kind']=='mail_send' else 'mail-received'):
                raise RunnerError('Mail steps require the matching transfer action and mail configuration.')
            if set(body)-{'manifest_kind','directory','from','to','files','expected_files'} or not {'manifest_kind','directory','from','to','files'}<=set(body):
                raise RunnerError('Mail scope must bind manifest kind, directory, mailboxes and files.')
            if body['manifest_kind'] not in ('input','delivery') or not Path(body['directory']).is_absolute():
                raise RunnerError('Invalid mail scope.')
            if not isinstance(body['files'],list) or not 1<=len(body['files'])<=10 or len(set(body['files']))!=len(body['files']):
                raise RunnerError('Mail scope requires explicit filenames.')
            if any(not isinstance(f,str) or '/' in f or '\\' in f or ':' in f or f in ('.','..') or Path(f).suffix.lower() not in ('.json','.csv') for f in body['files']):
                raise RunnerError('Unsafe mail filename.')
            if any(not isinstance(body[k],str) or '@' not in body[k] or '\n' in body[k] or '\r' in body[k] for k in ('from','to')):
                raise RunnerError('Mailboxes must be explicitly agreed.')
        def check(value):
            if isinstance(value, dict):
                for k, v in value.items():
                    if any(word in k.lower() for word in ('token', 'password', 'secret', 'authorization')):
                        raise RunnerError('Never place credentials in a runner policy.')
                    check(v)
            elif isinstance(value, list):
                for v in value: check(v)
        check(step['body'])
    encoded(policy)
    return policy


class InstanceLock:
    """Kernel-released lock: stale PID text never proves process liveness."""
    def __init__(self, path):
        self.path = Path(path)
        self.file = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = open(self.path, 'a+b')
        os.chmod(self.path, 0o600)
        if self.path.stat().st_size == 0:
            self.file.write(b'0'); self.file.flush()
        self.file.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.file.close(); self.file = None
            return False
        return True

    def close(self):
        if self.file:
            self.file.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
            self.file.close(); self.file = None


class Runner:
    def __init__(self, path, transport=request, clock=time.time, sleeper=time.sleep):
        self.path = Path(path).resolve()
        self.transport, self.clock, self.sleep = transport, clock, sleeper

    @property
    def lock(self):
        policy = self.state()['policy']
        identity = encoded([policy['url'], policy['actor_id'], policy['task_id']])
        root = Path(os.environ.get('LOCALAPPDATA', Path.home()/'.local/share'))/'AgentMarket/runner-locks'
        return InstanceLock(root/(hashlib.sha256(identity.encode()).hexdigest()+'.lock'))

    @contextmanager
    def db(self):
        if not self.path.is_file():
            raise RunnerError('Checkpoint does not exist.')
        with closing(sqlite3.connect(self.path, timeout=5)) as db, db:
            db.row_factory = sqlite3.Row
            yield db

    def initialize(self, policy, mode='run'):
        validate_policy(policy)
        if mode not in ('run', 'watch'):
            raise RunnerError('Unknown runner mode.')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        with self.db() as db:
            db.execute('CREATE TABLE state (id INTEGER PRIMARY KEY, body TEXT NOT NULL)')
            db.execute('CREATE TABLE intents (id TEXT PRIMARY KEY, body TEXT NOT NULL, status TEXT NOT NULL)')
            now = self.clock()
            expiry = datetime.fromisoformat(policy['expires_at']).timestamp()
            state = dict(policy=policy, policy_sha256=hashlib.sha256(encoded(policy).encode()).hexdigest(),
                mode=mode, status='ready', started_at=now, deadline=min(now+policy['max_seconds'], expiry),
                stop_requested=False, last_event_id=0, last_successful_sync_at=None,
                next_retry_at=None, error=None, phase=None, pid=None)
            db.execute('INSERT INTO state VALUES (1,?)', (encoded(state),))

    def state(self):
        with self.db() as db:
            return json.loads(db.execute('SELECT body FROM state WHERE id=1').fetchone()[0])

    def update(self, **values):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            state = json.loads(db.execute('SELECT body FROM state WHERE id=1').fetchone()[0])
            state.update(values)
            db.execute('UPDATE state SET body=? WHERE id=1', (encoded(state),))
        return state

    def status(self):
        state = self.state()
        lock = self.lock
        available = lock.acquire()
        if available: lock.close()
        return dict(status=state['status'], live=not available, pid=state['pid'] if not available else None,
            phase=state['phase'], last_event_id=state['last_event_id'],
            last_successful_sync_at=state['last_successful_sync_at'], next_retry_at=state['next_retry_at'],
            error=state['error'], stop_requested=state['stop_requested'], deadline=state['deadline'],
            mode=state['mode'], orchestration='detection_only' if state['mode']=='watch' else 'explicit_policy_steps')

    def stop(self):
        self.update(stop_requested=True)
        return self.status()

    def resume(self):
        # An explicit resume clears a prior stop, never extends authority/time.
        lock = self.lock
        if not lock.acquire():
            raise RunnerError('Another instance owns this job.')
        try:
            with self.db() as db:
                db.execute("UPDATE intents SET status='handoff_pending' WHERE status IN ('provider_402','handler_failed')")
            self.update(stop_requested=False, status='ready', error=None)
        finally:
            lock.close()
        return self.run()

    def work(self):
        with self.db() as db:
            return [dict(id=r['id'], status=r['status'], intent=json.loads(r['body']))
                for r in db.execute("SELECT * FROM intents WHERE status='handoff_pending'")]

    def acknowledge(self, step_id, outcome):
        if outcome not in ('completed', 'provider_402', 'handler_failed'):
            raise RunnerError('Unsupported host outcome.')
        state = self.state()
        if validate_base(os.environ.get('MARKET_URL','http://127.0.0.1:8787')) != state['policy']['url']:
            raise RunnerError('Policy origin mismatch.')
        if self.transport('GET','/me')['id'] != state['policy']['actor_id']:
            raise RunnerError('Policy identity mismatch.')
        current = self.transport('GET', '/tasks/' + state['policy']['task_id'])
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM intents WHERE id=?', (step_id,)).fetchone()
            if row is None or row['status'] not in ('handoff_pending', 'completed'):
                raise RunnerError('No matching pending host work.')
            intent = json.loads(row['body'])
            selected_transition=(intent['step']['action']=='select' and current['revision']==intent['revision']+1
                and intent['step']['body'].get('proposal_id') and current.get('selected')==intent['step']['body']['proposal_id'])
            if current['revision'] != intent['revision'] and not selected_transition:
                raise RunnerError('Stale host acknowledgement; revision changed.')
            if intent.get('manifest_id'):
                manifests=current.get('mail',{}).get('manifests',[])
                original=next((m for m in manifests if m['id']==intent['manifest_id']),None)
                if not original or next(m for m in reversed(manifests) if m['kind']==original['kind'])['id']!=original['id']:
                    raise RunnerError('Stale host acknowledgement; manifest changed.')
            if row['status']=='completed':
                return dict(acknowledged=True, replay=True)
            db.execute('UPDATE intents SET status=? WHERE id=?',
                ('completed' if outcome=='completed' else outcome, step_id))
        self.update(status='ready' if outcome=='completed' else 'blocked', error=None if outcome=='completed' else outcome)
        return dict(acknowledged=True, replay=False, outcome=outcome)

    def tick(self):
        state = self.state(); policy = state['policy']
        if state['stop_requested']:
            self.update(status='stopped', next_retry_at=None); return False
        if self.clock() >= state['deadline']:
            self.update(status='timed_out', next_retry_at=None); return False
        origin = validate_base(os.environ.get('MARKET_URL', 'http://127.0.0.1:8787'))
        if origin != policy['url']:
            self.update(status='blocked', error='origin_mismatch'); return False
        me = self.transport('GET', '/me')
        if me['id'] != policy['actor_id']:
            self.update(status='blocked', error='identity_mismatch'); return False
        task = self.transport('GET', '/tasks/' + policy['task_id'])
        if task['id'] != policy['task_id']:
            self.update(status='blocked', error='task_mismatch'); return False
        progress = task['progress']
        if (progress['last_event_id'] or 0) < state['last_event_id']:
            self.update(status='blocked', error='stale_snapshot'); return False
        self.update(phase=progress['phase'], last_event_id=progress['last_event_id'] or 0,
            last_successful_sync_at=self.clock(), next_retry_at=None, error=None)
        if task['status'] in ('accepted', 'cancelled'):
            self.update(status='completed'); return False
        if state['mode']=='watch':
            self.update(status='watching'); return True
        actionable = {a['action'] for a in progress['next_actions']
            if a['executable'] and a['actor_id']==policy['actor_id']}
        for step in policy['steps']:
            if step['phase'] != progress['phase'] or step['action'] not in actionable:
                continue
            if step['revision'] != task['revision']:
                self.update(status='blocked', error='revision_changed'); return False
            action=next(a for a in progress['next_actions'] if a['action']==step['action'] and a['executable'] and a['actor_id']==me['id'])
            intent = dict(step=step, task_id=task['id'], actor_id=me['id'], revision=task['revision'],
                manifest_id=action.get('manifest_id'))
            with self.db() as db:
                db.execute('BEGIN IMMEDIATE')
                old = db.execute('SELECT * FROM intents WHERE id=?', (step['id'],)).fetchone()
                if old and old['body'] != encoded(intent):
                    raise RunnerError('Durable intent differs; do not replace its key or body.')
                if old and old['status']=='completed':
                    continue
                failed = old['status'] if old and old['status'] in ('provider_402', 'handler_failed') else None
                if not old:
                    db.execute('INSERT INTO intents VALUES (?,?,?)',
                        (step['id'], encoded(intent), 'handoff_pending' if step['kind']=='handoff' else 'pending'))
            if failed:
                self.update(status='blocked', error=failed); return False
            if self.state()['stop_requested']:
                self.update(status='stopped'); return False
            if step['kind']=='handoff':
                if policy.get('host'):
                    from .host import invoke_host, HostError
                    work_id=hashlib.sha256(encoded(intent).encode()).hexdigest()
                    self.update(status='invoking_host',host_work_id=work_id)
                    try:
                        outcome=invoke_host(policy['host'],dict(schema_version=1,work_id=work_id,
                            authority='explicit_local_policy_only; re-read current platform state before mutations',
                            scope={k:v for k,v in policy.items() if k!='host'},
                            intent=intent,task=task),lambda:self.state()['stop_requested'],state['deadline'])
                    except HostError as error:
                        self.update(status='stopped' if error.code=='stopped' else 'blocked',error=error.code)
                        return False
                    if outcome!='pending':
                        if outcome not in ('completed','provider_402','handler_failed'):
                            self.update(status='blocked',error=outcome);return False
                        self.acknowledge(step['id'],outcome)
                        return outcome=='completed'
                self.update(status='awaiting_host', error='host_ack_required'); return False
            if step['kind'] in ('mail_send','mail_receive'):
                from .host import invoke_host, HostError
                scope=step['body']
                manifest=next((m for m in reversed(task.get('mail',{}).get('manifests',[])) if m['kind']==scope['manifest_kind']),None)
                if not manifest or manifest['id']!=intent['manifest_id'] or manifest['from']!=scope['from'] or manifest['to']!=scope['to'] or sorted(f['name'] for f in manifest['files'])!=sorted(scope['files']) or ('expected_files' in scope and manifest['files']!=scope['expected_files']):
                    self.update(status='blocked',error='mail_scope_mismatch');return False
                work_id=hashlib.sha256(encoded(intent).encode()).hexdigest()
                work=dict(schema_version=1,work_id=work_id,mail=dict(task_id=task['id'],revision=task['revision'],
                    manifest_id=manifest['id'],directory=scope['directory'],credentials_file=policy['mail']['credentials_file'],
                    send=step['kind']=='mail_send'))
                config=dict(argv=[sys.executable,str(Path(__file__).with_name('mail_worker.py'))],cwd=str(self.path.parent),timeout_seconds=180)
                self.update(status='transferring_mail',host_work_id=work_id)
                try:outcome=invoke_host(config,work,lambda:self.state()['stop_requested'],state['deadline'])
                except HostError as error:
                    self.update(status='stopped' if error.code=='stopped' else 'blocked',
                        error='send_uncertain' if step['kind']=='mail_send' else error.code);return False
                if outcome=='pending':
                    self.update(status='waiting_for_mail');return True
                if outcome!='completed':
                    self.update(status='blocked',error=outcome);return False
                with self.db() as db:
                    db.execute("UPDATE intents SET status='completed' WHERE id=?",(step['id'],))
                self.update(status='running');return True
            # Response loss leaves this exact key/body pending. Resume re-reads
            # current state and replays only when that action is still applicable.
            self.transport('POST', '/tasks/' + task['id'] + '/' + step['action'], step['body'], step['key'])
            with self.db() as db:
                db.execute("UPDATE intents SET status='completed' WHERE id=?", (step['id'],))
            self.update(status='running'); return True
        self.update(status='waiting' if not actionable else 'blocked',
            error=None if not actionable else 'authorization_or_handler_missing')
        return not actionable

    def run(self):
        lock = self.lock
        if not lock.acquire():
            raise RunnerError('Another instance owns this job.')
        try:
            self.update(pid=os.getpid(), status='running')
            failures = 0
            while True:
                try:
                    again = self.tick(); failures = 0
                except HTTPError as error:
                    code = 'authentication_failed' if error.code in (401,403) else 'conflict' if error.code==409 else 'http_error'
                    error.close(); self.update(status='blocked', error=code); break
                except MissingCredential:
                    self.update(status='blocked', error='credentials_missing'); break
                except (URLError, TimeoutError, ConnectionError):
                    failures += 1
                    if failures >= 3:
                        self.update(status='blocked', error='network_error', next_retry_at=None); break
                    again = True
                    self.update(status='retrying', error='network_error')
                if not again: break
                state = self.state()
                delay = min(state['policy']['interval_seconds'] * 2**failures, 60)
                until = min(self.clock()+delay, state['deadline'])
                self.update(next_retry_at=until)
                while self.clock() < until and not self.state()['stop_requested']:
                    self.sleep(min(1, until-self.clock()))
        except KeyboardInterrupt:
            self.update(stop_requested=True, status='stopped')
        except Exception:
            self.update(status='blocked', error='runner_failure')
            raise RunnerError('Runner failed; checkpoint preserved; private details suppressed.') from None
        finally:
            try:
                self.update(pid=None, next_retry_at=None)
            finally:
                lock.close()
        return self.status()
