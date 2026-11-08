import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from registration import Registration
from server import CATEGORIES
from tools import live_registration_check as check


class LiveCheckTest(unittest.TestCase):
    def test_local_http_acceptance_and_repeat_guard_with_synthetic_mail(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); config=root/'config.json'; code=root/'code.txt'
            config.write_text(json.dumps(dict(MARKET_SELF_REGISTRATION='1',MARKET_MAIL_TRANSPORT='zoho_api',
                 MARKET_MAIL_FROM='verify@example.com',MARKET_ZOHO_API_KEY='synthetic-key-123456',
                 MARKET_ZOHO_API_URL='https://cpaas.zoho.com/v1.1/email',MARKET_REGISTRATION_SECRET='synthetic-secret-'*3)))
            sends=[]
            def factory(store,categories):
                def send(recipient,value,cid):
                    sends.append(cid);code.write_text(value)
                return Registration(store,send,'synthetic-secret-'*3,CATEGORIES)
            with patch.dict(os.environ,{},clear=False),patch.object(check,'from_environment',side_effect=factory):
                result=check.run_check(config,root/'live','owner@example.com',str(code))
                self.assertEqual('passed',result['status'])
                self.assertTrue(result['identity_check'])
                self.assertFalse(result['production_changed'])
                token=json.loads((root/'live/credentials.json').read_text())['token']
                self.assertNotIn(token,json.dumps(result))
                with self.assertRaises(ValueError):check.run_check(config,root/'live','owner@example.com',str(code))
                self.assertEqual(1,len(sends))
