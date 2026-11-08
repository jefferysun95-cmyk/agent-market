import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from agent_market.runner import Runner, RunnerError, validate_policy


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.environment = patch.dict(os.environ, {'MARKET_URL':'https://example.com', 'LOCALAPPDATA':str(self.root)})
        self.environment.start()
        self.now = 1000
        self.calls = []
        self.task = dict(id='task', status='awaiting_confirmation', revision=1,
            progress=dict(phase='awaiting_confirmation', last_event_id=10,
                next_actions=[dict(action='confirm', actor_id='seller', executable=True)]))
        self.policy = dict(actor_id='seller', task_id='task', url='https://example.com',
            expires_at=datetime.fromtimestamp(2000,timezone.utc).isoformat(), max_seconds=30, interval_seconds=1,
            steps=[dict(id='confirm-r1', phase='awaiting_confirmation', revision=1, kind='api', action='confirm',
                body={'revision':1}, key='stable-confirm')])
        self.runner = self.new('job.db')

    def tearDown(self):
        self.environment.stop(); self.temp.cleanup()

    def api(self, method, path, body=None, key=None):
        self.calls.append((method,path,body,key))
        if path=='/me': return {'id':'seller'}
        if method=='GET': return copy.deepcopy(self.task)
        self.task['status']='working'
        self.task['progress'].update(phase='processing',last_event_id=11,next_actions=[])
        return copy.deepcopy(self.task)

    def new(self, name):
        return Runner(self.root/name, self.api, lambda:self.now, self.advance)

    def advance(self, seconds):
        self.now += seconds

    def test_response_loss_after_commit_does_not_repeat_business_action(self):
        def lost(method,path,body=None,key=None):
            value=self.api(method,path,body,key)
            if method=='POST': raise URLError('private detail must not be logged')
            return value
        self.runner.transport=lost
        self.runner.initialize(self.policy)
        self.runner.run()
        self.assertEqual(1,len([c for c in self.calls if c[0]=='POST']))
        self.assertNotIn('private detail',json.dumps(self.runner.state()))
        self.assertEqual('timed_out',self.runner.state()['status'])

    def test_response_loss_before_commit_reuses_original_key_and_body(self):
        attempted=[]
        def before_commit(method,path,body=None,key=None):
            if method=='POST':
                attempted.append((body,key))
                if len(attempted)==1: raise TimeoutError()
            return self.api(method,path,body,key)
        self.runner.transport=before_commit
        self.runner.initialize(self.policy); self.runner.run()
        self.assertEqual([({'revision':1},'stable-confirm')]*2,attempted)

    def test_different_checkpoint_path_cannot_bypass_actor_task_lock(self):
        self.runner.initialize(self.policy)
        other=self.new('other.db'); other.initialize(self.policy)
        lock=self.runner.lock
        self.assertTrue(lock.acquire())
        try:
            self.assertTrue(other.status()['live'])
            with self.assertRaises(RunnerError): other.run()
        finally: lock.close()
        self.assertFalse(other.status()['live'])

    def test_kernel_lock_survives_process_boundary_and_releases_on_crash(self):
        self.runner.initialize(self.policy)
        lock=self.runner.lock
        self.assertTrue(lock.acquire())
        code='from agent_market.runner import InstanceLock; import sys; lock=InstanceLock(sys.argv[1]); print(lock.acquire()); lock.close()'
        try:
            child=subprocess.run([sys.executable,'-c',code,str(lock.path)],capture_output=True,text=True,timeout=10)
            self.assertEqual(0,child.returncode,child.stderr)
            self.assertEqual('False',child.stdout.strip())
        finally: lock.close()
        crash='from agent_market.runner import InstanceLock; import os,sys; lock=InstanceLock(sys.argv[1]); assert lock.acquire(); os._exit(0)'
        child=subprocess.run([sys.executable,'-c',crash,str(lock.path)],capture_output=True,text=True,timeout=10)
        self.assertEqual(0,child.returncode,child.stderr)
        self.assertTrue(lock.acquire());lock.close()

    def test_checkpoint_resume_uses_frozen_policy_after_original_file_changes(self):
        self.runner.initialize(self.policy)
        self.policy['steps'][0]['body']['revision']=99
        fresh=self.new('job.db')
        fresh.run()
        posts=[c for c in self.calls if c[0]=='POST']
        self.assertEqual({'revision':1},posts[0][2])

    def test_expiry_is_not_extended_by_stop_and_resume(self):
        self.runner.initialize(self.policy,mode='watch')
        deadline=self.runner.state()['deadline']
        self.runner.stop()
        self.now=deadline+1
        status=self.runner.resume()
        self.assertEqual('timed_out',status['status'])
        self.assertEqual(deadline,status['deadline'])
        self.assertFalse(status['live'])

    def test_stop_interrupts_wait_without_killing_other_processes(self):
        self.runner.initialize(self.policy,mode='watch')
        def sleep(seconds):
            self.advance(seconds); self.runner.stop()
        self.runner.sleep=sleep
        status=self.runner.run()
        self.assertEqual('stopped',status['status'])
        self.assertFalse(status['live'])
        self.assertEqual(0,len([c for c in self.calls if c[0]=='POST']))

    def test_handoff_requires_ack_and_reports_provider_402_without_claiming_trade_failure(self):
        self.policy['steps'][0]['kind']='handoff'
        self.runner.initialize(self.policy)
        self.assertEqual('awaiting_host',self.runner.run()['status'])
        self.assertEqual(1,len(self.runner.work()))
        self.runner.acknowledge('confirm-r1','provider_402')
        self.assertEqual('provider_402',self.runner.state()['error'])
        self.assertEqual('awaiting_confirmation',self.task['status'])
        self.runner.resume()
        self.assertEqual('awaiting_host',self.runner.state()['status'])
        self.runner.acknowledge('confirm-r1','completed')
        self.assertEqual([],self.runner.work())
        self.assertTrue(self.runner.acknowledge('confirm-r1','completed')['replay'])
        self.assertEqual('awaiting_confirmation',self.task['status'])

    def test_wrong_actor_origin_revision_and_stale_snapshot_block(self):
        for name, change, expected in (
            ('actor',lambda: self.policy.update(actor_id='other'),'identity_mismatch'),
            ('origin',lambda: self.policy.update(url='https://other.example'),'origin_mismatch'),
            ('revision',lambda: self.task.update(revision=2),'revision_changed'),
            ('stale',lambda: None,'stale_snapshot')):
            with self.subTest(name=name):
                self.setUpStateForGuard()
                change()
                r=self.new(name+'.db');r.initialize(self.policy)
                if name=='stale': r.update(last_event_id=99)
                self.assertFalse(r.tick())
                self.assertEqual(expected,r.state()['error'])

    def setUpStateForGuard(self):
        self.policy.update(actor_id='seller',url='https://example.com')
        self.task['revision']=1

    def test_manual_mail_receipts_and_secrets_are_not_policy_handlers(self):
        for action,body in [('mail-received',{}),('confirm',{'token':'never-store'})]:
            value=copy.deepcopy(self.policy)
            value['steps'][0].update(action=action,body=body)
            with self.assertRaises(RunnerError): validate_policy(value)

    def test_auth_failure_exits_and_network_retries_are_bounded(self):
        self.runner.initialize(self.policy)
        def denied(*args): raise HTTPError('https://example.com',401,'private body',{},None)
        self.runner.transport=denied
        self.assertEqual('authentication_failed',self.runner.run()['error'])
        def unreachable(*args): raise URLError('private URL')
        self.runner.transport=unreachable
        self.assertEqual('network_error',self.runner.resume()['error'])
        self.assertLess(self.now,1010)

    def test_watch_is_detection_only_and_terminal_orders_exit(self):
        self.runner.initialize(self.policy,mode='watch')
        self.assertTrue(self.runner.tick())
        self.assertEqual('watching',self.runner.state()['status'])
        self.assertEqual('detection_only',self.runner.status()['orchestration'])
        self.task['status']='accepted'
        self.assertFalse(self.runner.tick())
        self.assertEqual('completed',self.runner.state()['status'])
        self.assertEqual(0,len([c for c in self.calls if c[0]=='POST']))

    def test_configured_host_is_invoked_and_acknowledged_without_human_resume(self):
        self.policy['steps'][0]['kind']='handoff'
        self.policy['host']=dict(argv=[sys.executable,'host.py'],cwd=str(self.root),timeout_seconds=5)
        self.runner.initialize(self.policy)
        def host(config,work,stop,deadline):
            self.assertEqual('stable-confirm',work['intent']['step']['key'])
            self.assertEqual('seller',work['scope']['actor_id'])
            self.api('POST','/tasks/task/confirm',{'revision':1},'stable-confirm')
            return 'completed'
        with patch('agent_market.host.invoke_host',side_effect=host) as invoke:
            self.assertTrue(self.runner.tick())
            self.assertEqual(1,invoke.call_count)
        self.assertEqual([],self.runner.work())
        self.assertEqual('working',self.task['status'])

    def test_host_ack_rejects_superseded_manifest(self):
        self.policy['steps'][0].update(kind='handoff',action='mail-received')
        self.task['progress']['next_actions']=[dict(action='mail-received',actor_id='seller',executable=True,manifest_id='old')]
        self.task['mail']={'manifests':[dict(id='old',kind='input')]}
        self.runner.initialize(self.policy);self.runner.tick()
        self.task['mail']['manifests'].append(dict(id='new',kind='input'))
        with self.assertRaises(RunnerError):self.runner.acknowledge('confirm-r1','completed')
