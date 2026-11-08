from datetime import datetime,timezone
import os
from pathlib import Path
import time
from unittest.mock import patch

from tests_support import Base
from tests.test_mail import FakeGmail
from agent_market.runner import Runner
from agent_market.mail_worker import perform
from agent_market.mail_bridge import digest


class RunnerMailTest(Base):
    def setUp(self):
        super().setUp()
        self.root=Path(self.tmp.name)
        self.source=self.root/'input';self.source.mkdir()
        (self.source/'orders.json').write_text('[{"id":1}]',encoding='utf-8')
        self.select()
        for token,address in ((self.b,'buyer@example.com'),(self.s,'seller@example.com')):
            self.call(token,'POST',self.path+'/mail-config',{'address':address})
        self.call(self.s,'POST',self.path+'/confirm',{'revision':1})
        self.manifest=self.call(self.b,'POST',self.path+'/mail-manifests',dict(kind='input',files=[digest(self.source/'orders.json')]))
        self.sender=FakeGmail('buyer@example.com',self.root/'outbox',rewrite=True)
        self.recipient=FakeGmail('seller@example.com',self.root/'recipient-outbox')
        self.recipient.messages=self.sender.messages
        self.recipient.labels=self.sender.labels
        self.environment=patch.dict(os.environ,{'MARKET_URL':'https://example.com','LOCALAPPDATA':str(self.root)})
        self.environment.start()

    def tearDown(self):
        self.environment.stop();super().tearDown()

    def runner(self,token,send):
        actor=self.call(token,'GET','/me')['id']
        api=lambda method,path,data=None,key=None:self.call(token,method,path,data,key)
        mode='mail_send' if send else 'mail_receive'
        policy=dict(actor_id=actor,task_id=self.task['id'],url='https://example.com',
            expires_at=datetime.fromtimestamp(time.time()+100,timezone.utc).isoformat(),max_seconds=30,interval_seconds=1,
            mail={'credentials_file':str(self.root/'private-placeholder.json')},steps=[dict(id=mode,kind=mode,
                action='mail-sent' if send else 'mail-received',phase='awaiting_input_send' if send else 'awaiting_input_receipt',
                revision=1,key='stable-'+mode,body=dict(manifest_kind='input',directory=str(self.source if send else self.root/'received'),
                    **{'from':'buyer@example.com','to':'seller@example.com'},files=['orders.json']))])
        runner=Runner(self.root/(mode+'.db'),api)
        runner.initialize(policy)
        return runner,api

    def test_runner_uses_standard_adapter_and_server_observed_headers_without_manual_receipt(self):
        sender,send_api=self.runner(self.b,True)
        receiver,receive_api=self.runner(self.s,False)
        with patch('agent_market.host.invoke_host',side_effect=lambda cfg,work,*args:perform(work,send_api,lambda path:self.sender)):
            self.assertTrue(sender.tick())
        with patch('agent_market.host.invoke_host',side_effect=lambda cfg,work,*args:perform(work,receive_api,lambda path:self.recipient)):
            self.assertTrue(receiver.tick())
        manifest=self.call(self.b,'GET',self.path)['mail']['manifests'][0]
        self.assertEqual('<rewritten-g1@mail.gmail.com>',manifest['message_id'])
        self.assertEqual(manifest['message_id'],manifest['receipt']['observed_message_id'])
        self.assertEqual('buyer@example.com',manifest['receipt']['observed_from'])
        self.assertEqual('seller@example.com',manifest['receipt']['observed_to'])
        self.assertEqual((self.source/'orders.json').read_bytes(),(self.root/'received/orders.json').read_bytes())
        self.assertEqual(1,self.sender.sent)

    def test_uncertain_send_does_not_resend_on_resume(self):
        runner,api=self.runner(self.b,True)
        self.sender.lose_send_response=True
        with patch('agent_market.host.invoke_host',side_effect=lambda cfg,work,*args:perform(work,api,lambda path:self.sender)):
            self.assertFalse(runner.tick())
            self.assertEqual('send_uncertain',runner.state()['error'])
            self.sender.lose_send_response=False
            self.assertTrue(runner.tick()) # Reconcile existing Sent copy, not a new send.
        self.assertEqual(1,self.sender.sent)

    def test_mail_scope_mismatch_stops_before_any_gmail_call(self):
        runner,api=self.runner(self.b,True)
        self.call(self.b,'POST',self.path+'/mail-manifests',dict(kind='input',files=[dict(name='other.json',size=1,sha256='0'*64)]))
        with patch('agent_market.host.invoke_host') as invoke:
            self.assertFalse(runner.tick());invoke.assert_not_called()
        self.assertEqual('mail_scope_mismatch',runner.state()['error'])

    def test_packaged_and_standalone_mail_bridges_cannot_drift(self):
        root=Path(__file__).parents[1]
        self.assertEqual((root/'mail_bridge.py').read_bytes(),(root/'agent_market/mail_bridge.py').read_bytes())
