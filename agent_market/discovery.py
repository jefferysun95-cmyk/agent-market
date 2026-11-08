"""Bounded paged demand discovery with durable, acknowledged host work."""
import hashlib
import json
import os
from urllib.parse import urlencode

from .host import invoke_host, HostError, validate_host
from .market import validate_base
from .runner import Runner,RunnerError,encoded


class Discovery(Runner):
    def initialize(self, policy, mode='discover'):
        required={'actor_id','url','category','buyers','budgets','expires_at','max_seconds','interval_seconds','max_pages'}
        if not required<=set(policy) or set(policy)-required-{'host'}:
            raise RunnerError('Invalid discovery policy fields.')
        for key in ('category',):
            if not isinstance(policy[key],str) or not 1<=len(policy[key])<=100:
                raise RunnerError('Discovery category required.')
        for key in ('buyers','budgets'):
            if not isinstance(policy[key],list) or not 1<=len(policy[key])<=100 or any(not isinstance(v,str) or not v for v in policy[key]):
                raise RunnerError('Discovery requires explicit buyer and budget allowlists.')
        if type(policy['max_pages']) is not int or not 1<=policy['max_pages']<=1000:
            raise RunnerError('Discovery scan must have a page bound.')
        if 'host' in policy:validate_host(policy['host'])
        base={k:policy[k] for k in ('actor_id','url','expires_at','max_seconds','interval_seconds')}
        base.update(task_id='discovery_'+hashlib.sha256(policy['category'].encode()).hexdigest(),steps=[])
        super().initialize(base)
        self.update(mode='discover',discovery=policy,cursor=None,page_count=0,scan_round=0)

    def eligible(self, task, policy):
        return task['status']=='open' and task['category']==policy['category'] and task['buyer'] in policy['buyers'] and task['buyer']!=policy['actor_id'] and task['budget'] in policy['budgets'] and not any(p['seller']==policy['actor_id'] for p in task.get('proposals',[]))

    def acknowledge(self, step_id, outcome):
        if outcome not in ('completed','provider_402','handler_failed'):
            raise RunnerError('Unsupported discovery host outcome.')
        state=self.state();policy=state['discovery']
        if validate_base(os.environ.get('MARKET_URL','http://127.0.0.1:8787'))!=policy['url'] or self.transport('GET','/me')['id']!=policy['actor_id']:
            raise RunnerError('Discovery host identity/origin mismatch.')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM intents WHERE id=?',(step_id,)).fetchone()
            if row is None or row['status'] not in ('handoff_pending','completed'):
                raise RunnerError('No pending discovery work.')
            if row['status']=='completed':return dict(acknowledged=True,replay=True)
            db.execute('UPDATE intents SET status=? WHERE id=?',('completed' if outcome=='completed' else outcome,step_id))
        self.update(status='ready' if outcome=='completed' else 'blocked',error=None if outcome=='completed' else outcome)
        return dict(acknowledged=True,replay=False,outcome=outcome)

    def tick(self):
        state=self.state();policy=state['discovery']
        if state['stop_requested']:
            self.update(status='stopped');return False
        if self.clock()>=state['deadline']:
            self.update(status='timed_out');return False
        if validate_base(os.environ.get('MARKET_URL','http://127.0.0.1:8787'))!=policy['url']:
            self.update(status='blocked',error='origin_mismatch');return False
        if self.transport('GET','/me')['id']!=policy['actor_id']:
            self.update(status='blocked',error='identity_mismatch');return False
        pending=self.work()
        if pending:
            item=pending[0];intent=item['intent']
            current=self.transport('GET','/tasks/'+intent['task_id'])
            if current['id']!=intent['task_id']:
                self.update(status='blocked',error='task_mismatch');return False
            if not self.eligible(current,policy):
                self.acknowledge(item['id'],'completed')
                return True # Selected/closed/already bid: never act on cached demand.
            if not policy.get('host'):
                self.update(status='awaiting_host',error='host_ack_required');return False
            self.update(status='invoking_host',host_work_id=item['id'])
            try:
                outcome=invoke_host(policy['host'],dict(schema_version=1,work_id=item['id'],
                    authority='evaluate_demand_within_explicit_policy; re-read before any mutation',
                    intent=intent,task=current,scope={k:v for k,v in policy.items() if k!='host'}),
                    lambda:self.state()['stop_requested'],state['deadline'])
            except HostError as error:
                self.update(status='stopped' if error.code=='stopped' else 'blocked',error=error.code);return False
            if outcome=='pending':
                self.update(status='awaiting_host',error='host_ack_required');return False
            self.acknowledge(item['id'],outcome)
            return outcome=='completed'
        if state['page_count']>=policy['max_pages']:
            self.update(status='blocked',error='discovery_page_limit');return False
        query=dict(page='true',scope='open',category=policy['category'],limit=100)
        if state['cursor'] is not None:query['before']=state['cursor']
        page=self.transport('GET','/tasks?'+urlencode(query))
        if not isinstance(page,dict) or not isinstance(page.get('items'),list) or 'next_cursor' not in page:
            raise RunnerError('Discovery requires paged tasks from alpha.4 or later.')
        cursor=page['next_cursor']
        if cursor is not None and (not isinstance(cursor,str) or not cursor.isdecimal() or int(cursor)<=0 or (state['cursor'] is not None and int(cursor)>=int(state['cursor']))):
            raise RunnerError('Discovery cursor did not advance.')
        # Queue + cursor commit atomically. A crash cannot advance past lost work.
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            for task in page['items']:
                if not self.eligible(task,policy):continue
                work_id=hashlib.sha256(encoded([policy['url'],policy['actor_id'],task['id'],'evaluate_demand']).encode()).hexdigest()
                intent=dict(task_id=task['id'],actor_id=policy['actor_id'],purpose='evaluate_demand')
                db.execute("INSERT OR IGNORE INTO intents VALUES (?,?, 'handoff_pending')",(work_id,encoded(intent)))
            latest=json.loads(db.execute('SELECT body FROM state WHERE id=1').fetchone()[0])
            latest.update(cursor=cursor,page_count=state['page_count']+1 if cursor else 0,
                scan_round=state['scan_round']+(cursor is None),status='scanning',phase='discovering_open_demand',
                last_successful_sync_at=self.clock(),error=None,next_retry_at=None)
            db.execute('UPDATE state SET body=? WHERE id=1',(encoded(latest),))
        return True

    def status(self):
        result=super().status();state=self.state()
        result.update(orchestration='bounded_discovery_with_host_ack' if state['discovery'].get('host') else 'discovery_detection_only',
            cursor=state['cursor'],scan_round=state['scan_round'],pending_work=len(self.work()))
        return result
