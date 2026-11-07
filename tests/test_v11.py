import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from tests_support import *


class BetaTest(Base):
    def test_registration_idempotent_revocation_rotation(self):
        profile={'name':'new','provider':'operator'}
        first=self.store.call('POST','/agents',{},profile,self.invite,'stable-register',self.invite)
        again=self.store.call('POST','/agents',{},profile,self.invite,'stable-register',self.invite)
        self.assertEqual(first,again)
        aid=first['agent']['id']
        rotated=self.store.call('POST',f'/admin/agents/{aid}/rotate',{}, {},self.invite,'rotate',self.invite)
        self.fail(401,first['token'],'GET','/me')
        self.assertEqual(aid,self.call(rotated['token'],'GET','/me')['id'])
        with self.assertRaises(Problem):self.store.call('POST','/agents',{},profile,self.invite,'stable-register',self.invite)
        self.store.call('POST',f'/admin/agents/{aid}/revoke',{}, {},self.invite,'revoke',self.invite)
        self.fail(401,rotated['token'],'GET','/me')
        # Issued raw tokens are never persisted, including idempotency receipts.
        self.assertNotIn(rotated['token'].encode(),Path(self.tmp.name+'/test.db').read_bytes())

    def test_inbox_replay_ack_and_privacy(self):
        selected=self.select()
        inbox=self.call(self.s,'GET','/inbox')
        self.assertEqual('select',inbox['items'][-1]['action'])
        self.assertEqual(self.task['id'],inbox['items'][-1]['task_id'])
        self.assertEqual(inbox,self.call(self.s,'GET','/inbox'))
        self.fail(400,self.x,'POST','/inbox/ack',{'cursor':inbox['next_cursor']})
        self.call(self.s,'POST','/inbox/ack',{'cursor':inbox['next_cursor']})
        self.assertEqual([],self.call(self.s,'GET','/inbox')['items'])
        self.call(self.s,'POST',self.path+'/confirm',{'revision':selected['revision']})
        self.assertTrue(self.call(self.b,'GET','/inbox')['items'])

    def configure(self):
        selected=self.select()
        self.call(self.b,'POST',self.path+'/mail-config',{'address':'buyer@example.com'})
        self.call(self.s,'POST',self.path+'/mail-config',{'address':'seller@example.com'})
        self.call(self.s,'POST',self.path+'/confirm',{'revision':selected['revision']})

    def test_mail_roles_hashes_and_acceptance(self):
        self.configure()
        files=[{'name':'cleaned.csv','size':3,'sha256':hashlib.sha256(b'a,b').hexdigest()}]
        m=self.call(self.s,'POST',self.path+'/mail-manifests',{'kind':'delivery','files':files})
        self.fail(403,self.b,'POST',self.path+'/mail-sent',{'manifest_id':m['id'],'message_id':'<x>'})
        self.call(self.s,'POST',self.path+'/mail-sent',{'manifest_id':m['id'],'message_id':'<x>'})
        self.fail(409,self.b,'POST',self.path+'/mail-received',{'manifest_id':m['id'],'files':[]})
        self.call(self.s,'POST',self.path+'/deliver',{'result':{'ok':True}})
        self.fail(409,self.b,'POST',self.path+'/accept',{'note':'premature'})
        self.call(self.b,'POST',self.path+'/mail-received',{'manifest_id':m['id'],'files':files})
        self.assertEqual('accepted',self.call(self.b,'POST',self.path+'/accept',{'note':'verified'})['status'])

    def test_events_do_not_leak_other_quotes(self):
        self.call(self.x,'POST',self.path+'/proposals',{'price':'SECRET PRICE','terms':'private terms','deadline':'soon'})
        selected=self.select()
        events=self.call(self.s,'GET',self.path+'/events')
        self.assertNotIn('SECRET PRICE',json.dumps(events))

    def test_paused_profile(self):
        me=self.call(self.s,'POST','/me/profile',{'available':False})
        self.assertFalse(me['available'])
        self.assertNotIn(me['id'],[a['id'] for a in self.call(self.b,'GET','/agents')])
        self.fail(409,self.s,'POST',self.path+'/proposals',{'price':'0','terms':'x','deadline':'soon'})

    def test_rework_requires_new_file_version(self):
        self.configure()
        files=[{'name':'cleaned.csv','size':3,'sha256':hashlib.sha256(b'a,b').hexdigest()}]
        m=self.call(self.s,'POST',self.path+'/mail-manifests',{'kind':'delivery','files':files})
        self.call(self.s,'POST',self.path+'/mail-sent',{'manifest_id':m['id'],'message_id':'<v1>'})
        self.call(self.b,'POST',self.path+'/mail-received',{'manifest_id':m['id'],'files':files})
        self.call(self.s,'POST',self.path+'/deliver',{'result':{'v':1}})
        self.call(self.b,'POST',self.path+'/request_changes',{'note':'fix contents'})
        self.fail(409,self.s,'POST',self.path+'/deliver',{'result':{'v':2}})
        m2=self.call(self.s,'POST',self.path+'/mail-manifests',{'kind':'delivery','files':files})
        self.call(self.s,'POST',self.path+'/deliver',{'result':{'v':2}})
        self.fail(409,self.b,'POST',self.path+'/accept',{'note':'stale receipt'})
        self.call(self.s,'POST',self.path+'/mail-sent',{'manifest_id':m2['id'],'message_id':'<v2>'})
        self.call(self.b,'POST',self.path+'/mail-received',{'manifest_id':m2['id'],'files':files})
        self.assertEqual('accepted',self.call(self.b,'POST',self.path+'/accept',{'note':'checked v2'})['status'])


if __name__=='__main__':unittest.main()
