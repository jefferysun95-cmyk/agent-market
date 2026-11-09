"""H02 real Store/HTTP tests; synthetic identities only, no public operations."""
import copy
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError,URLError
from urllib.parse import urlsplit,parse_qs
from http.server import ThreadingHTTPServer

from agent_market.h02 import H02,clean,fixture,expected
from agent_market.runner import RunnerError
from server import Store,Problem,handler

ROOT=Path(__file__).resolve().parents[1]


class H02Test(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.env=patch.dict(os.environ,dict(MARKET_URL='https://synthetic.example',LOCALAPPDATA=str(self.root)));self.env.start()
        self.store=Store(self.root/'store.db');self.invite='synthetic-invite';self.now=1800000000
        self.accounts=[];self.calls=[]
        for role in ('buyer','seller'):
            self.accounts.append(self.store.call('POST','/agents',{},dict(name=role,provider='synthetic',capabilities=['data-cleaning']),self.invite,'synthetic-register-'+role,self.invite))
        self.buyer=self.make('buyer');self.seller=self.make('seller')

    def tearDown(self):
        self.env.stop();self.temp.cleanup()

    def transport(self,role):
        token=self.accounts[0 if role=='buyer' else 1]['token']
        def call(method,path,body=None,key=None):
            self.calls.append((role,method,path,copy.deepcopy(body),key))
            url=urlsplit(path)
            try:return self.store.call(method,url.path,parse_qs(url.query),body or {},token,key or '',self.invite)
            except Problem as error:raise HTTPError('https://synthetic.example',error.status,'synthetic',{},None) from None
        return call

    def make(self,role,path=None):
        trial=H02(path or self.root/(role+'.db'),self.transport(role),lambda:self.now,lambda seconds:None)
        trial.initialize_trial(role,'h02-synthetic-01',self.accounts[0]['agent']['id'],self.accounts[1]['agent']['id'],
                               'https://synthetic.example',max_seconds=30,interval_seconds=1)
        return trial

    def cycle(self,first='buyer'):
        peers=(self.buyer,self.seller) if first=='buyer' else (self.seller,self.buyer)
        for _ in range(16):
            for peer in peers:
                if peer.state()['status'] not in ('completed','blocked'):peer.tick()
            self.now+=1
            if all(p.state()['status']=='completed' for p in peers):return
        self.fail([p.status() for p in peers])

    def setup_working(self):
        self.buyer.tick();self.seller.tick();self.buyer.tick();self.seller.tick()
        self.assertEqual(self.seller.state()['phase'],'awaiting_confirmation')

    def test_normal_flow_buyer_first_without_host_or_resume(self):
        self.cycle()
        self.assertEqual(self.buyer.state()['task_id'],self.seller.state()['task_id'])
        actions=[c[2].split('/')[-1] for c in self.calls if c[1]=='POST']
        self.assertEqual(actions,['tasks','proposals','select','confirm','deliver','accept'])
        for peer in (self.buyer,self.seller):
            self.assertEqual(peer.status()['resume_requests'],0)
            self.assertEqual(peer.status()['stage_callbacks_required'],0)
            self.assertEqual(peer.status()['verification'],'content_PASS')

    def test_seller_starts_before_buyer_and_keeps_following_after_quote(self):
        self.assertTrue(self.seller.tick());self.assertEqual(self.seller.state()['phase'],'awaiting_task')
        self.cycle('seller')
        self.assertEqual(self.seller.state()['status'],'completed')

    def test_response_lost_after_create_does_not_create_again(self):
        original=self.buyer.transport;lost=[False]
        def call(*args):
            result=original(*args)
            if args[0]=='POST' and args[1]=='/tasks' and not lost[0]:
                lost[0]=True;raise URLError('synthetic lost response')
            return result
        self.buyer.transport=call
        with self.assertRaises(URLError):self.buyer.tick()
        self.buyer=H02(self.buyer.path,original,lambda:self.now)
        self.cycle()
        self.assertEqual(1,len([c for c in self.calls if c[1:3]==('POST','/tasks')]))
        self.assertIn(dict(action='create',status='observed_committed'),self.buyer.status()['actions'])

    def test_response_lost_before_write_reuses_identical_intent(self):
        self.buyer.tick();original=self.seller.transport;attempts=[]
        def call(method,path,body=None,key=None):
            if method=='POST':
                attempts.append((copy.deepcopy(body),key))
                if len(attempts)==1:raise TimeoutError()
            return original(method,path,body,key)
        self.seller.transport=call
        with self.assertRaises(TimeoutError):self.seller.tick()
        self.seller.tick()
        self.assertEqual(attempts[0],attempts[1])
        self.cycle()

    def test_delivery_loss_reconciles_after_process_restart(self):
        self.setup_working();original=self.seller.transport
        def lost(method,path,body=None,key=None):
            result=original(method,path,body,key)
            if method=='POST' and path.endswith('/deliver'):raise TimeoutError()
            return result
        self.seller.transport=lost
        with self.assertRaises(TimeoutError):self.seller.tick()
        self.seller=H02(self.seller.path,original,lambda:self.now)
        self.cycle()
        self.assertEqual(1,len([c for c in self.calls if c[1]=='POST' and c[2].endswith('/deliver')]))
        self.assertIn(dict(action='deliver-v1',status='observed_committed'),self.seller.status()['actions'])

    def mutate(self,fn):
        with self.store.connect() as db:
            row=db.execute('SELECT * FROM tasks').fetchone();body=json.loads(row['body']);fn(body)
            db.execute('UPDATE tasks SET body=? WHERE id=?',(json.dumps(body),body['id']))

    def test_changed_terms_block_confirm(self):
        self.buyer.tick();self.seller.tick();self.buyer.tick()
        self.mutate(lambda t:t['proposals'][0].update(price='CNY 10'))
        self.assertFalse(self.seller.tick());self.assertEqual(self.seller.state()['error'],'selected_terms_mismatch')
        self.assertFalse(any(c[1]=='POST' and c[2].endswith('/confirm') for c in self.calls))

    def test_corrupted_content_blocks_accept_and_bool_is_not_an_integer(self):
        self.setup_working();self.seller.tick()
        self.mutate(lambda t:t['delivery']['result']['rows'][0].update(quantity=True))
        self.assertFalse(self.buyer.tick());self.assertEqual(self.buyer.state()['error'],'content_mismatch')
        self.assertFalse(any(c[1]=='POST' and c[2].endswith('/accept') for c in self.calls))

    def test_duplicate_matching_tasks_stop_without_guessing(self):
        self.buyer.tick()
        self.transport('buyer')('POST','/tasks',self.buyer.state()['create_body'],'separate-synthetic-duplicate')
        self.assertFalse(self.seller.tick());self.assertEqual(self.seller.state()['error'],'ambiguous_task')

    def test_identity_origin_and_expiry_are_hard_boundaries(self):
        self.buyer.transport=self.transport('seller')
        self.assertFalse(self.buyer.tick());self.assertEqual(self.buyer.state()['error'],'identity_mismatch')
        self.buyer.transport=self.transport('buyer')
        with patch.dict(os.environ,MARKET_URL='https://other.example'):
            self.assertFalse(self.buyer.tick());self.assertEqual(self.buyer.state()['error'],'origin_mismatch')
        deadline=self.buyer.state()['deadline'];self.now=deadline
        self.assertFalse(self.buyer.tick());self.assertEqual(self.buyer.state()['status'],'timed_out')
        self.assertEqual([], [c for c in self.calls if c[1]=='POST'])

    def test_cancellation_and_network_budget_do_not_spin(self):
        self.buyer.update(stop_requested=True)
        self.assertFalse(self.buyer.tick());self.assertEqual(self.buyer.state()['status'],'stopped')
        self.buyer.update(stop_requested=False)
        count=[0]
        def failure(*args):count[0]+=1;raise URLError('sensitive text')
        self.buyer.transport=failure
        self.buyer.sleep=lambda seconds:setattr(self,'now',self.now+seconds)
        result=self.buyer.run()
        self.assertEqual(count[0],3);self.assertEqual(result['error'],'network_error')
        self.assertNotIn('sensitive text',json.dumps(self.buyer.state()))

    def test_same_actor_and_run_lock_cannot_be_bypassed_with_new_checkpoint(self):
        other=self.make('buyer',self.root/'other.db');lock=self.buyer.lock
        self.assertTrue(lock.acquire())
        try:
            with self.assertRaises(RunnerError):other.run()
        finally:lock.close()

    def test_seller_calculation_and_independent_oracle_match_for_two_run_ids(self):
        for run in ('h02-synthetic-01','h02-second'):
            self.assertEqual(clean(fixture(run)),expected(run))
        self.assertNotEqual(expected('h02-synthetic-01'),expected('h02-second'))

    def test_expiry_during_read_prevents_later_write_and_resume_does_not_extend_it(self):
        self.buyer.tick();self.seller.tick()
        original=self.buyer.transport;deadline=self.buyer.state()['deadline']
        def expire(method,path,body=None,key=None):
            result=original(method,path,body,key)
            if method=='GET' and path.startswith('/tasks/'):
                self.now=deadline
            return result
        self.buyer.transport=expire
        self.assertFalse(self.buyer.tick())
        self.assertEqual(self.buyer.state()['status'],'timed_out')
        self.assertFalse(any(c[1]=='POST' and c[2].endswith('/select') for c in self.calls))
        self.buyer.resume()
        self.assertEqual(self.buyer.state()['deadline'],deadline)
        self.assertEqual(self.buyer.state()['status'],'timed_out')

    def test_http_timeout_uses_remaining_authority_and_keeps_default_client_compatible(self):
        peer=H02(self.buyer.path,clock=lambda:self.now)
        with patch('agent_market.h02.request',return_value={'id':'synthetic'}) as request:
            peer.http('GET','/me')
            self.assertEqual(request.call_args.kwargs['timeout'],10)
            self.now=self.buyer.state()['deadline']-2
            peer.http('GET','/me')
            self.assertEqual(request.call_args.kwargs['timeout'],2)

    def test_exit_observer_enforces_wall_budget_and_records_actual_child_exit(self):
        exit_file=self.root/'observer-exit.json';process_file=self.root/'observer-process.json'
        server=ThreadingHTTPServer(('127.0.0.1',0),handler(self.store,self.invite))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        url='http://127.0.0.1:'+str(server.server_port)
        env=dict(os.environ,MARKET_URL=url,MARKET_TOKEN=self.accounts[1]['token'],
                 MARKET_CONFIG_FILE=str(self.root/'no-config.json'),LOCALAPPDATA=str(self.root))
        try:
            args=['h02','start','--role','seller','--run-id','h02-observer-budget',
                  '--buyer-id',self.accounts[0]['agent']['id'],'--seller-id',self.accounts[1]['agent']['id'],
                  '--url',url,'--state',str(self.root/'observer.db'),'--max-seconds','20',
                  '--interval-seconds','1','--authorize-free-trade']
            result=subprocess.run([sys.executable,str(ROOT/'agent_market/h02_worker.py'),'--observe',
                                   str(exit_file),str(process_file),'0','--',*args],env=env,
                                  capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,124,result.stderr)
            record=json.loads(exit_file.read_text(encoding='utf-8'))
            self.assertTrue(record['hard_timeout_triggered'])
            self.assertNotEqual(record['business_exit_code'],0)
            self.assertNotEqual(record['observer_pid'],record['child_pid'])
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)

    def test_two_actual_cli_processes_finish_via_loopback_http_without_callbacks(self):
        self.cli_pair('start')

    def test_launchers_exit_and_two_background_children_finish_without_callbacks(self):
        self.cli_pair('launch')

    def cli_pair(self,entry):
        server=ThreadingHTTPServer(('127.0.0.1',0),handler(self.store,self.invite))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();children=[]
        try:
            for index,role in [(1,'seller'),(0,'buyer')]:
                credential=self.root/(role+'-credential.json');credential.write_text(json.dumps({'token':self.accounts[index]['token']}))
                url='http://127.0.0.1:'+str(server.server_port)
                env=dict(os.environ,MARKET_URL=url,MARKET_CREDENTIALS_FILE=str(credential),LOCALAPPDATA=str(self.root))
                env.pop('MARKET_TOKEN',None);env['MARKET_CONFIG_FILE']=str(self.root/'no-config.json')
                argv=[sys.executable,str(ROOT/'skills/agent-market/scripts/client.py'),'h02',entry,
                      '--role',role,'--run-id','h02-process-pair','--buyer-id',self.accounts[0]['agent']['id'],
                      '--seller-id',self.accounts[1]['agent']['id'],'--url',url,'--state',str(self.root/(role+'-http.db')),
                      '--interval-seconds','1','--max-seconds','20','--authorize-free-trade']
                children.append(subprocess.Popen(argv,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True))
            for child in children:
                stdout,stderr=child.communicate(timeout=25)
                self.assertEqual(child.returncode,0,stderr+stdout)
                result=json.loads(stdout)['data']
                if entry=='start':
                    self.assertEqual(result['status'],'completed')
                    self.assertEqual(result['resume_requests'],0);self.assertEqual(result['model_invocations'],0)
                else:self.assertEqual(result['launch_status'],'started')
                self.assertNotIn('"token"',stdout+stderr)
            if entry=='launch':
                until=time.monotonic()+25
                while time.monotonic()<until:
                    states=[H02(self.root/(r+'-http.db')).status() for r in ('buyer','seller')]
                    if all(s['status']=='completed' and not s['live'] and isinstance(s['process_exit'],dict) for s in states):break
                    time.sleep(0.2)
                self.assertTrue(all(s['status']=='completed' and not s['live'] for s in states),states)
                for r in ('buyer','seller'):
                    output=json.loads((self.root/(r+'-http.db.stdout.json')).read_text(encoding='utf-8'))
                    self.assertTrue(output['ok']);self.assertEqual(output['data']['resume_requests'],0)
                    observed=json.loads((self.root/(r+'-http.db.exit.json')).read_text(encoding='utf-8'))
                    self.assertEqual(observed['business_exit_code'],0)
                    self.assertFalse(observed['hard_timeout_triggered'])
        finally:
            for r in ('buyer','seller'):
                checkpoint=self.root/(r+'-http.db')
                if checkpoint.exists():
                    try:H02(checkpoint).stop()
                    except Exception:pass
            for child in children:
                if child.poll() is None:child.kill();child.communicate()
            server.shutdown();server.server_close();thread.join(timeout=5)
