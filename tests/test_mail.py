import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from mail_bridge import compose,extract_verified,transfer


class FakeGmail:
    def __init__(self,email):self.email=email;self.messages={};self.sent=0
    def call(self,path,data=None):
        if path=='profile':return {'emailAddress':self.email}
        if path.startswith('messages/'):return {'labelIds':['SENT']}
    def find(self,mid):return [{'id':mid}] if mid in self.messages else []
    def raw(self,mid):return self.messages[mid]
    def send(self,raw):
        from email.parser import BytesParser
        msg=BytesParser().parsebytes(raw);self.messages[str(msg['Message-ID'])]=raw;self.sent+=1


class MailTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.file=self.root/'cleaned.csv';self.file.write_bytes(b'id,qty\n1,2\n')
        self.manifest={'id':'m123','kind':'delivery','version':1,'sender':'s','recipient':'b',
            'from':'seller@example.com','to':'buyer@example.com',
            'files':[{'name':'cleaned.csv','size':len(self.file.read_bytes()),'sha256':hashlib.sha256(self.file.read_bytes()).hexdigest()}]}
    def tearDown(self):self.tmp.cleanup()
    def test_mime_and_hash_rejection(self):
        raw=compose('task',self.manifest,[self.file]);m=dict(self.manifest,message_id='<m123@agent-market.invalid>')
        self.assertEqual(self.file.read_bytes(),extract_verified(raw,m)['cleaned.csv'])
        wrong=copy.deepcopy(m);wrong['files'][0]['sha256']='0'*64
        with self.assertRaises(ValueError):extract_verified(raw,wrong)
    def test_ambiguous_send_recovery_and_receive(self):
        gmail=FakeGmail('seller@example.com');task={'status':'working','mail':{'manifests':[self.manifest]}}
        role=['s'];fail_once=[True]
        def api(method,path,data=None,key=None):
            if path=='/me':return {'id':role[0]}
            if method=='GET':return task
            if path.endswith('/mail-sent'):
                if fail_once[0]:fail_once[0]=False;raise TimeoutError('simulated response loss')
                self.manifest.update(message_id=data['message_id'],sent_at='now')
            if path.endswith('/mail-received'):self.manifest['received_at']='now'
            return self.manifest
        with self.assertRaises(TimeoutError):transfer(api,gmail,'task','m123',self.root,True)
        transfer(api,gmail,'task','m123',self.root,True)
        self.assertEqual(1,gmail.sent)
        role[0]='b';gmail.email='buyer@example.com'
        output=self.root/'received'
        self.assertEqual('received_verified',transfer(api,gmail,'task','m123',output)['status'])
        self.assertEqual(self.file.read_bytes(),(output/'cleaned.csv').read_bytes())
