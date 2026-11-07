import copy
import hashlib
import json
from email import policy
from email.parser import BytesParser
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs
from mail_bridge import Gmail, SendUncertain, compose, extract_verified, transfer, reconcile_input
import tests_support as support


class FakeGmail:
    def __init__(self,email,state_dir,rewrite=False):
        self.email=email;self.state_dir=state_dir;self.rewrite=rewrite
        self.messages={};self.labels={};self.sent=0;self.hide_search=False;self.lose_send_response=False;self.queries=[]
    def call(self,path,data=None):
        if path=='profile':return {'emailAddress':self.email}
        if path.startswith('messages?'):
            query=parse_qs(path.split('?',1)[1]);self.queries.append(query)
            return {'messages':self.search(query['q'][0])}
        if path.startswith('messages/'):
            gid=path.split('/')[1].split('?')[0]
            return {'id':gid,'labelIds':self.labels.get(gid,[])}
    def find(self,mid):return Gmail.find(self,mid)
    def search(self,query):
        if self.hide_search:return []
        found=[]
        for gid,raw in self.messages.items():
            message=BytesParser(policy=policy.default).parsebytes(raw)
            if 'rfc822msgid:' in query:
                matches=str(message['Message-ID']).strip('<>')==query.split('rfc822msgid:',1)[1]
            else:
                matches=query.split('"')[1] in raw.decode('utf-8',errors='replace')
                matches=matches and 'SENT' in self.labels.get(gid,[])
            if matches:found.append({'id':gid})
        return found
    def raw(self,gid):return self.messages[gid]
    def send(self,raw):
        message=BytesParser(policy=policy.default).parsebytes(raw)
        self.sent+=1;gid='g'+str(self.sent)
        if self.rewrite:message.replace_header('Message-ID',f'<rewritten-{gid}@mail.gmail.com>')
        self.messages[gid]=message.as_bytes(policy=policy.SMTP);self.labels[gid]=['SENT']
        if self.lose_send_response:raise TimeoutError('Response lost after Gmail accepted message')
        return {'id':gid,'threadId':'thread-'+gid}


class MailTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.file=self.root/'cleaned.csv';self.file.write_bytes(b'id,qty\n1,2\n')
        self.manifest={'id':'m123','kind':'delivery','version':1,'sender':'s','recipient':'b',
            'from':'seller@example.com','to':'buyer@example.com',
            'files':[{'name':'cleaned.csv','size':len(self.file.read_bytes()),'sha256':hashlib.sha256(self.file.read_bytes()).hexdigest()}]}
        self.role='s';self.fail_api_once=False
        self.task={'status':'working','mail':{'manifests':[self.manifest]}}
    def tearDown(self):self.tmp.cleanup()
    def gmail(self,rewrite=False):return FakeGmail('seller@example.com',self.root/'outbox',rewrite)
    def api(self,method,path,data=None,key=None):
        if path=='/me':return {'id':self.role}
        if method=='GET':return self.task
        if path.endswith('/mail-sent'):
            if self.fail_api_once:self.fail_api_once=False;raise TimeoutError('Platform response lost')
            self.manifest.update(message_id=data['message_id'],sent_at='now')
        if path.endswith('/mail-received'):self.manifest['received_at']='now'
        return self.manifest
    def test_mime_and_hash_rejection(self):
        raw=compose('task',self.manifest,[self.file]);m=dict(self.manifest,message_id='<m123@agent-market.invalid>')
        self.assertEqual(self.file.read_bytes(),extract_verified(raw,m)['cleaned.csv'])
        wrong=copy.deepcopy(m);wrong['files'][0]['sha256']='0'*64
        with self.assertRaises(ValueError):extract_verified(raw,wrong)
    def test_rewritten_message_id_and_spam_receive(self):
        gmail=self.gmail(rewrite=True)
        transfer(self.api,gmail,'task','m123',self.root,True)
        self.assertEqual('<rewritten-g1@mail.gmail.com>',self.manifest['message_id'])
        self.role='b';gmail.email='buyer@example.com';gmail.labels['g1']=['SPAM']
        output=self.root/'received'
        self.assertEqual('received_verified',transfer(self.api,gmail,'task','m123',output)['status'])
        self.assertEqual(self.file.read_bytes(),(output/'cleaned.csv').read_bytes())
        # The real query builder must explicitly cover Spam and Trash.
        Gmail.search(gmail,'in:anywhere rfc822msgid:rewritten-g1@mail.gmail.com')
        self.assertEqual(['true'],gmail.queries[-1]['includeSpamTrash'])
    def test_platform_failure_uses_persisted_gmail_id_without_resend(self):
        gmail=self.gmail(rewrite=True);self.fail_api_once=True
        with self.assertRaises(TimeoutError):transfer(self.api,gmail,'task','m123',self.root,True)
        gmail.hide_search=True
        transfer(self.api,gmail,'task','m123',self.root,True)
        self.assertEqual(1,gmail.sent)
        self.assertEqual('<rewritten-g1@mail.gmail.com>',self.manifest['message_id'])
    def test_uncertain_gmail_send_does_not_resend_when_search_delayed(self):
        gmail=self.gmail(rewrite=True);gmail.lose_send_response=True
        with self.assertRaises(TimeoutError):transfer(self.api,gmail,'task','m123',self.root,True)
        gmail.hide_search=True
        with self.assertRaises(SendUncertain):transfer(self.api,gmail,'task','m123',self.root,True)
        self.assertNotIn('sent_at',self.manifest)
        self.assertEqual(1,gmail.sent)
        gmail.hide_search=False;gmail.lose_send_response=False
        transfer(self.api,gmail,'task','m123',self.root,True)
        self.assertEqual(1,gmail.sent)
    def test_corrupt_sent_copy_never_creates_receipt(self):
        gmail=self.gmail(rewrite=True)
        original=gmail.send
        def corrupt(raw):
            result=original(raw)
            message=BytesParser(policy=policy.default).parsebytes(gmail.messages[result['id']])
            next(message.iter_attachments()).set_payload('Y29ycnVwdA==')
            gmail.messages[result['id']]=message.as_bytes(policy=policy.SMTP)
            return result
        gmail.send=corrupt
        with self.assertRaises(ValueError):transfer(self.api,gmail,'task','m123',self.root,True)
        self.assertNotIn('sent_at',self.manifest)
    def test_old_registered_wrong_id_requires_explicit_reconciliation(self):
        gmail=self.gmail(rewrite=True);gmail.send(compose('task',self.manifest,[self.file]))
        self.manifest.update(message_id='<m123@agent-market.invalid>',sent_at='earlier')
        with self.assertRaises(SendUncertain):transfer(self.api,gmail,'task','m123',self.root,True)
        self.assertEqual(1,gmail.sent)
        self.assertEqual('<m123@agent-market.invalid>',self.manifest['message_id'])


class ReconcileStoreTest(support.Base):
    def test_real_store_replacement_preserves_old_record_and_receives_spam(self):
        selected=self.select()
        self.call(self.b,'POST',self.path+'/mail-config',{'address':'buyer@example.com'})
        self.call(self.s,'POST',self.path+'/mail-config',{'address':'seller@example.com'})
        self.call(self.s,'POST',self.path+'/confirm',{'revision':selected['revision']})
        root=Path(self.tmp.name);source=root/'input.json';source.write_bytes(b'{"rows":[1]}')
        files=[{'name':source.name,'size':source.stat().st_size,'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}]
        old=self.call(self.b,'POST',self.path+'/mail-manifests',{'kind':'input','files':files})
        gmail=FakeGmail('buyer@example.com',root/'outbox',rewrite=True)
        legacy=BytesParser(policy=policy.default).parsebytes(compose(self.task['id'],old,[source]))
        del legacy['X-Agent-Market-Task'];del legacy['X-Agent-Market-Manifest']
        result=gmail.send(legacy.as_bytes(policy=policy.SMTP))
        self.call(self.b,'POST',self.path+'/mail-sent',{'manifest_id':old['id'],'message_id':'<wrong@agent-market.invalid>'})
        actor=[self.b]
        def api(method,path,data=None,key=None):return self.call(actor[0],method,path,data,key)
        actor[0]=self.s
        with self.assertRaises(ValueError):reconcile_input(api,gmail,self.task['id'],old['id'],result['id'])
        self.assertEqual(1,len(self.call(self.b,'GET',self.path)['mail']['manifests']))
        actor[0]=self.b
        correction=reconcile_input(api,gmail,self.task['id'],old['id'],result['id'])
        self.assertFalse(correction['resent']);self.assertEqual(1,gmail.sent)
        task=api('GET',self.path);manifests=task['mail']['manifests']
        self.assertEqual('<wrong@agent-market.invalid>',manifests[0]['message_id'])
        self.assertEqual('<rewritten-g1@mail.gmail.com>',manifests[1]['message_id'])
        self.assertEqual(2,manifests[1]['version'])
        events=api('GET',self.path+'/events')
        self.assertTrue(any(e['payload'].get('replaces_manifest_id')==old['id'] for e in events))
        with self.assertRaises(ValueError):reconcile_input(api,gmail,self.task['id'],old['id'],result['id'])
        self.assertEqual(2,len(api('GET',self.path)['mail']['manifests']))
        actor[0]=self.s;gmail.email='seller@example.com';gmail.labels[result['id']]=['SPAM']
        self.assertEqual('received_verified',transfer(api,gmail,self.task['id'],correction['manifest_id'],root/'received')['status'])
        self.assertEqual(source.read_bytes(),(root/'received'/source.name).read_bytes())
