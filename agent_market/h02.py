"""H02-only deterministic free-trade supervisor; no model, mailbox or host calls.

Uses the existing runner lock/checkpoint/retry lifecycle and the shared HTTP API.
It is an opt-in experiment, not general autonomous procurement.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import urlencode

from .market import validate_base, request
from .onboarding import private_path
from .runner import Runner, RunnerError, encoded

PROTOCOL = 'agent-market-h02-v1'
BUDGET = 'CNY 0; H02 synthetic validation; no payment'
PRICE = 'CNY 0 total'
RULES = ('Trim id/name; deduplicate by trimmed id keeping first before field validation; '
         'dates only YYYY-MM-DD or YYYY/MM/DD and real calendar dates, normalize or null+INVALID_DATE; '
         'quantity only positive ASCII integer strings, normalize or null+INVALID_QUANTITY; '
         'preserve source_row, raw exception values, order and punctuation; '
         'errors alphabetical, exceptions by source_row/field, duplicates by source_row.')
ACCEPTANCE = ('API result only: rows/exceptions/duplicates/summary; exact H02 schema and independent '
              'buyer comparison. No email, CSV, manifest, attachments, payment or model invocation.')
TERMS = PROTOCOL + ': ' + RULES + ' ' + ACCEPTANCE + ' No additional conditions.'


def fixture(run_id):
    prefix = hashlib.sha256(run_id.encode()).hexdigest()[:8]
    def row(n, suffix, name, date, qty):
        return dict(source_row=n, id=prefix+suffix, name=name, date=date, quantity=qty)
    return [row(1,'-01',' Pencil ','2026/11/09','2'),
            row(2,'-02','Notebook','2026-11-08','3'),
            row(3,'-01','Duplicate','invalid','two'),
            row(4,'-03','Eraser','2026-02-30','1'),
            row(5,'-04',' Box, "Blue" ','2028/02/29','0'),
            row(6,'-02','Duplicate','2026/11/08','4')]


def clean(rows):
    """Seller computes from actual task input; does not read the buyer oracle."""
    kept, output, exceptions, duplicates = {}, [], [], []
    for raw in rows:
        identity = raw['id'].strip()
        if identity in kept:
            duplicates.append(dict(source_row=raw['source_row'], kept_source_row=kept[identity], id=identity))
            continue
        kept[identity] = raw['source_row']
        item = dict(source_row=raw['source_row'], id=identity, name=raw['name'].strip(), date=None, quantity=None, errors=[])
        date = raw['date']
        if re.fullmatch(r'[0-9]{4}([-\/])[0-9]{2}\1[0-9]{2}', date):
            try: item['date'] = datetime.strptime(date.replace('/', '-'), '%Y-%m-%d').date().isoformat()
            except ValueError: pass
        if item['date'] is None:
            item['errors'].append('INVALID_DATE')
            exceptions.append(dict(source_row=raw['source_row'], field='date', code='INVALID_DATE', raw_value=date))
        qty = raw['quantity']
        if re.fullmatch('[0-9]+', qty) and int(qty) > 0:
            item['quantity'] = int(qty)
        else:
            item['errors'].append('INVALID_QUANTITY')
            exceptions.append(dict(source_row=raw['source_row'], field='quantity', code='INVALID_QUANTITY', raw_value=qty))
        item['errors'].sort()
        output.append(item)
    exceptions.sort(key=lambda value:(value['source_row'], value['field']))
    return dict(rows=output, exceptions=exceptions, duplicates=duplicates,
                summary=dict(input_rows=len(rows), output_rows=len(output), removed_duplicates=len(duplicates),
                             rows_with_errors=sum(bool(r['errors']) for r in output), field_errors=len(exceptions)))


def expected(run_id):
    """Independent buyer reference for this fixed synthetic experiment only."""
    ids = [hashlib.sha256(run_id.encode()).hexdigest()[:8]+'-'+v for v in ('01','02','03','04')]
    return dict(rows=[
        dict(source_row=1,id=ids[0],name='Pencil',date='2026-11-09',quantity=2,errors=[]),
        dict(source_row=2,id=ids[1],name='Notebook',date='2026-11-08',quantity=3,errors=[]),
        dict(source_row=4,id=ids[2],name='Eraser',date=None,quantity=1,errors=['INVALID_DATE']),
        dict(source_row=5,id=ids[3],name='Box, "Blue"',date='2028-02-29',quantity=None,errors=['INVALID_QUANTITY'])],
        exceptions=[dict(source_row=4,field='date',code='INVALID_DATE',raw_value='2026-02-30'),
                    dict(source_row=5,field='quantity',code='INVALID_QUANTITY',raw_value='0')],
        duplicates=[dict(source_row=3,kept_source_row=1,id=ids[0]),dict(source_row=6,kept_source_row=2,id=ids[1])],
        summary=dict(input_rows=6,output_rows=4,removed_duplicates=2,rows_with_errors=2,field_errors=2))


class Halt(Exception):
    def __init__(self, code, status='blocked'):
        self.code, self.status = code, status


class H02(Runner):
    def __init__(self,path,transport=None,clock=time.time,sleeper=time.sleep):
        super().__init__(path,transport or self.http,clock,sleeper)

    def http(self,method,path,body=None,key=None):
        remaining=self.state()['deadline']-self.clock()
        if remaining<=0: raise Halt('authorization_expired','timed_out')
        return request(method,path,body,key,timeout=max(0.1,min(10,remaining)))

    def initialize_trial(self, role, run_id, buyer, seller, url, max_seconds=1800, interval_seconds=10):
        if role not in ('buyer','seller') or not re.fullmatch(r'h02-[a-z0-9-]{1,64}',run_id):
            raise RunnerError('H02 requires buyer/seller and a shared h02- run identifier.')
        if buyer == seller or any(not re.fullmatch('[0-9a-f]{32}', value) for value in (buyer,seller)):
            raise RunnerError('H02 requires distinct exact platform identity IDs.')
        if type(max_seconds) is not int or not 1 <= max_seconds <= 1800:
            raise RunnerError('H02 authority is bounded to at most 1800 seconds.')
        # Synthetic checkpoint only; credential issuance still uses create_private/ACL.
        # On Windows it inherits the user's existing private directory permissions.
        self.path = private_path(self.path)
        now = self.clock()
        actor = buyer if role == 'buyer' else seller
        digest = hashlib.sha256(encoded([validate_base(url),actor,run_id]).encode()).hexdigest()
        base = dict(actor_id=actor,task_id='h02_'+digest[:32],url=validate_base(url),
                    expires_at=datetime.fromtimestamp(now+max_seconds,timezone.utc).isoformat(),
                    max_seconds=max_seconds,interval_seconds=interval_seconds,steps=[])
        super().initialize(base)
        plan = dict(protocol=PROTOCOL,role=role,run_id=run_id,buyer=buyer,seller=seller,
                    title='H02 '+run_id+' structured zero-handoff')
        body = self.contract(plan)
        body['deadline'] = datetime.fromtimestamp(now+86400,timezone.utc).isoformat()
        self.update(h02=plan, task_id=None, task_contract=None, create_body=body,
                    resumes=0, verification=None, synchronization_cycles=0, audit=[])

    @staticmethod
    def contract(plan):
        return dict(title=plan['title'],category='data-cleaning',budget=BUDGET,acceptance=ACCEPTANCE,
                    brief=encoded(dict(protocol=PROTOCOL,run_id=plan['run_id'],seller=plan['seller'],
                                       input=fixture(plan['run_id']),rules=RULES)))

    def guard(self):
        state = self.state()
        if state['stop_requested']: raise Halt('stop_requested','stopped')
        if self.clock() >= state['deadline']: raise Halt('authorization_expired','timed_out')
        if validate_base(os.environ.get('MARKET_URL','http://127.0.0.1:8787')) != state['policy']['url']:
            raise Halt('origin_mismatch')

    def api(self, method, path, body=None, key=None):
        self.guard()
        return self.transport(method,path,body,key)

    def find(self):
        state = self.state(); plan = state['h02']; matches = set()
        scopes = ['mine'] + (['open'] if plan['role']=='seller' else [])
        for scope in scopes:
            before = None; seen = set()
            for _ in range(10):
                query = dict(page='true',limit=100,scope=scope)
                if before: query['before'] = before
                page = self.api('GET','/tasks?'+urlencode(query))
                for task in page['items']:
                    if task['title'] == plan['title'] and task['buyer'] == plan['buyer']:
                        matches.add(task['id'])
                if not page['has_more']: break
                before = page['next_cursor']
                if not before or before in seen: raise Halt('invalid_pagination')
                seen.add(before)
            else: raise Halt('discovery_page_limit')
        if len(matches)>1: raise Halt('ambiguous_task')
        return next(iter(matches),None)

    def checked(self, task):
        state = self.state(); plan = state['h02']
        contract = self.contract(plan)
        if task.get('buyer') != plan['buyer'] or any(task.get(k)!=v for k,v in contract.items()):
            raise Halt('task_scope_mismatch')
        if state['task_id'] and task.get('id')!=state['task_id']: raise Halt('task_identity_mismatch')
        try:
            deadline = datetime.fromisoformat(task['deadline'])
            if deadline.tzinfo is None or deadline.timestamp() <= self.clock() or deadline.timestamp()>self.clock()+90000:
                raise ValueError()
        except (ValueError,TypeError,KeyError): raise Halt('task_deadline_mismatch') from None
        if plan['role']=='buyer' and task['deadline']!=state['create_body']['deadline']:
            raise Halt('buyer_creation_body_changed')
        bound = dict(contract,deadline=task['deadline'],buyer=task['buyer'])
        if state['task_contract'] and state['task_contract']!=bound: raise Halt('task_contract_changed')
        if task.get('mail') or task.get('payment'): raise Halt('unexpected_mail_or_payment')
        revision = task.get('revision')
        if type(revision) is not int or revision != (0 if task['status']=='open' else 1):
            raise Halt('unexpected_revision')
        selected = task.get('selected')
        if task['status']=='open':
            if selected is not None: raise Halt('unexpected_selection')
        else:
            proposal = next((p for p in task['proposals'] if p['id']==selected),None)
            if not proposal or not self.offer_matches(proposal,task,plan): raise Halt('selected_terms_mismatch')
        self.resolve_pending(task)
        self.update(task_id=task['id'],task_contract=bound,phase=task['status'],
                    synchronization_cycles=state['synchronization_cycles']+1,
                    last_successful_sync_at=self.clock(),error=None)
        return task

    def resolve_pending(self, task):
        """Reconcile a lost response only from a matching current order fact."""
        plan=self.state()['h02']
        own=any(self.offer_matches(p,task,plan) for p in task['proposals'])
        with self.db() as db:
            for row in db.execute("SELECT * FROM intents WHERE status='pending'").fetchall():
                action=row['id'];intent=json.loads(row['body'])
                observed=(action=='create' or action=='propose' and own or
                          action=='select' and bool(task['selected']) or
                          action=='confirm-r1' and task['status'] in ('working','delivered','accepted') or
                          action=='deliver-v1' and task.get('delivery') and
                          encoded(task['delivery'].get('result'))==encoded(intent['body']['result']) or
                          action=='accept' and task['status']=='accepted')
                if observed:
                    db.execute("UPDATE intents SET status='observed_committed' WHERE id=?",(action,))
                    latest=json.loads(db.execute('SELECT body FROM state WHERE id=1').fetchone()[0])
                    for attempt in latest['audit']:
                        if attempt['action']==action and attempt['outcome']=='pending':
                            attempt.update(outcome='observed_committed',observed_at=self.clock())
                    db.execute('UPDATE state SET body=? WHERE id=1',(encoded(latest),))


    @staticmethod
    def offer_matches(proposal,task,plan):
        return (proposal.get('seller')==plan['seller'] and proposal.get('price')==PRICE and
                proposal.get('terms')==TERMS and proposal.get('deadline')==task['deadline'])

    def write(self, action, path, body, task=None):
        # Re-read the current contract immediately before any order mutation.
        if task is not None:
            current = self.checked(self.api('GET','/tasks/'+task['id']))
            if any(current.get(k)!=task.get(k) for k in ('status','revision','selected')):
                raise Halt('state_changed_before_write')
        state=self.state()
        key='h02-'+hashlib.sha256(encoded([state['policy']['url'],state['policy']['actor_id'],state['h02']['run_id']]).encode()).hexdigest()[:32]+'-'+action
        intent=encoded(dict(path=path,body=body,key=key))
        with self.db() as db:
            old=db.execute('SELECT * FROM intents WHERE id=?',(action,)).fetchone()
            if old and old['body']!=intent: raise Halt('intent_changed')
            if old and old['status'] in ('completed','observed_committed'): raise Halt('completed_action_still_requested')
            if not old: db.execute('INSERT INTO intents VALUES (?,?,?)',(action,intent,'pending'))
        audit=self.state()['audit']
        audit.append(dict(action=action,started_at=self.clock(),outcome='pending'))
        self.update(audit=audit)
        result=self.api('POST',path,body,key)
        audit=self.state()['audit'];audit[-1].update(confirmed_at=self.clock(),outcome='http_success')
        self.update(audit=audit)
        with self.db() as db: db.execute("UPDATE intents SET status='completed' WHERE id=?",(action,))
        self.update(status='running')
        return result

    def tick(self):
        try: return self.advance()
        except Halt as error:
            self.update(status=error.status,error=error.code)
            return False

    def advance(self):
        self.guard();state=self.state();plan=state['h02']
        if self.api('GET','/me')['id']!=state['policy']['actor_id']: raise Halt('identity_mismatch')
        identity=state['task_id'] or self.find()
        if not identity:
            if plan['role']=='buyer':
                task=self.write('create','/tasks',state['create_body'])
                self.checked(dict(task,status=task.get('status','open')))
            else:self.update(status='waiting',phase='awaiting_task')
            return True
        task=self.checked(self.api('GET','/tasks/'+identity));path='/tasks/'+task['id']
        if task['status']=='accepted':
            if not task.get('delivery') or encoded(task['delivery'].get('result'))!=encoded(expected(plan['run_id'])):
                raise Halt('accepted_content_mismatch')
            self.update(status='completed',verification='content_PASS')
            return False
        if task['status'] not in ('open','awaiting_confirmation','working','delivered'):
            raise Halt('unexpected_task_state')
        if task['status']=='open':
            offers=[p for p in task['proposals'] if p.get('seller')==plan['seller']]
            if len(offers)>1 or any(not self.offer_matches(p,task,plan) for p in offers):
                raise Halt('proposal_terms_mismatch')
            if plan['role']=='seller' and not offers:
                self.write('propose',path+'/proposals',dict(price=PRICE,terms=TERMS,deadline=task['deadline']),task)
                return True
            if plan['role']=='buyer' and offers:
                self.write('select',path+'/select',dict(proposal_id=offers[0]['id']),task)
                return True
        elif plan['role']=='seller' and task['status']=='awaiting_confirmation':
            self.write('confirm-r1',path+'/confirm',dict(revision=task['revision']),task)
            return True
        elif plan['role']=='seller' and task['status']=='working':
            if task.get('delivery') is not None: raise Halt('rework_not_authorized')
            source=json.loads(task['brief'])['input']
            self.write('deliver-v1',path+'/deliver',dict(result=clean(source)),task)
            return True
        elif plan['role']=='buyer' and task['status']=='delivered':
            if not task.get('delivery') or encoded(task['delivery'].get('result'))!=encoded(expected(plan['run_id'])):
                self.update(verification='content_FAIL')
                raise Halt('content_mismatch')
            self.update(verification='content_PASS')
            self.write('accept',path+'/accept',dict(note='H02 independent deterministic buyer comparison PASS; no stage callback requested; no payment.'),task)
            return True
        self.update(status='waiting')
        return True

    def resume(self):
        self.update(resumes=self.state()['resumes']+1)
        return super().resume()

    def status(self):
        result=super().status();state=self.state()
        with self.db() as db:
            actions=[dict(action=row['id'],status=row['status']) for row in db.execute('SELECT * FROM intents ORDER BY rowid')]
        exit_path=self.path.with_suffix(self.path.suffix+'.exit.json')
        try:process_exit=json.loads(exit_path.read_text(encoding='utf-8')) if exit_path.exists() else None
        except (OSError,ValueError):process_exit='unavailable'
        result.update(process_exit=process_exit,experiment='H02',orchestration='deterministic_free_trade_only',
                      role=state['h02']['role'],run_id=state['h02']['run_id'],task_id=state['task_id'],
                      verification=state['verification'],resume_requests=state['resumes'],
                      stage_callbacks_required=0,human_interventions='not_independently_observed',
                      model_invocations=0,actions=actions,audit=state['audit'])
        return result


def launch(args):
    """Start exactly one scoped supervisor, then return without chat polling."""
    state=private_path(args.state)
    if state.exists(): raise RunnerError('Checkpoint exists; inspect h02 status. Launch never replaces or resumes it.')
    state.parent.mkdir(parents=True,exist_ok=True)
    stdout=state.with_suffix(state.suffix+'.stdout.json')
    stderr=state.with_suffix(state.suffix+'.stderr.json')
    exit_file=state.with_suffix(state.suffix+'.exit.json')
    process_file=state.with_suffix(state.suffix+'.process.json')
    if exit_file.exists() or process_file.exists():
        raise RunnerError('Prior process evidence exists; inspect it rather than replacing it.')
    # Observer captures the actual OS child exit code after the chat caller exits.
    # Its hard wall budget is authority +20 seconds for startup/in-flight shutdown.
    argv=[sys.executable,str(Path(__file__).with_name('h02_worker.py')),'--observe',
          str(exit_file),str(process_file),str(args.max_seconds+20),'--','h02','start',
          '--role',args.role,'--run-id',args.run_id,'--buyer-id',args.buyer_id,'--seller-id',args.seller_id,
          '--url',args.url,'--state',str(state),'--max-seconds',str(args.max_seconds),
          '--interval-seconds',str(args.interval_seconds),'--authorize-free-trade']
    options={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {'start_new_session':True}
    # Exclusive logs: do not overwrite prior evidence or follow an existing link.
    with os.fdopen(os.open(stdout,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'w',encoding='utf-8') as out:
        with os.fdopen(os.open(stderr,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'w',encoding='utf-8') as err:
            child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=out,stderr=err,
                                   shell=False,close_fds=True,**options)
    until=time.monotonic()+5
    business_pid=None
    while child.poll() is None and time.monotonic()<until:
        try:
            info=json.loads(process_file.read_text(encoding='utf-8'))
            if info['observer_pid']!=child.pid:raise RunnerError('Process observer mismatch')
            business_pid=info['child_pid']
            status=H02(state).state()
            if status.get('pid')==business_pid:break
        except (OSError,ValueError,KeyError):pass
        except Exception:
            # SQLite may still be creating its schema; bounded readiness only.
            pass
        time.sleep(0.1)
    code=child.poll()
    return dict(launch_status='started' if code is None else 'exited_early',pid=business_pid,observer_pid=child.pid,
                startup_exit_code=code,state_file=str(state),stdout_file=str(stdout),stderr_file=str(stderr),exit_file=str(exit_file),
                note='Check h02 status; cross-turn child survival depends on the harness. No completion or identity success is implied.')
