import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from server import Store
from tools.alpha5_deploy import mail_env, nginx_patch, snapshot, write_new


class DeployTest(unittest.TestCase):
    def test_private_environment_conversion_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'mail.json';target=root/'registration.env'
            value=dict(MARKET_SELF_REGISTRATION='1',MARKET_MAIL_TRANSPORT='zoho_api',MARKET_MAIL_FROM='verify@example.com',
                       MARKET_ZOHO_API_KEY='synthetic-key-with-quotes-"',MARKET_ZOHO_API_URL='https://cpaas.zoho.com/v1.1/email',
                       MARKET_REGISTRATION_SECRET='synthetic-stable-secret-'*2)
            source.write_text(json.dumps(value))
            with patch.dict(os.environ,{},clear=False):mail_env(source,target)
            loaded={k:json.loads(v) for k,v in (line.split('=',1) for line in target.read_text().splitlines())}
            self.assertEqual(value,loaded)
            before=target.read_bytes()
            with patch.dict(os.environ,{},clear=False),self.assertRaises(FileExistsError):mail_env(source,target)
            self.assertEqual(before,target.read_bytes())
            value['OTHER_SECRET']='unexpected';source.write_text(json.dumps(value))
            with self.assertRaises(ValueError):mail_env(source,root/'bad.env')

    def test_nginx_preserves_certificate_and_scopes_domain(self):
        before='server {\n listen 443 ssl;\n server_name api.digolives.com; # managed by Certbot\n ssl_certificate /private/cert.pem;\n location / {\n proxy_pass http://127.0.0.1:8787;\n proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n }\n}\n'
        after=nginx_patch(before)
        self.assertIn('ssl_certificate /private/cert.pem;',after)
        self.assertIn('limit_req zone=market_alpha5 burst=20 nodelay;',after)
        self.assertIn('X-Forwarded-For $remote_addr;',after)
        with self.assertRaises(ValueError):nginx_patch(after)
        with self.assertRaises(ValueError):nginx_patch(before.replace('api.digolives.com','other.example'))

    def test_read_only_identity_order_snapshot_and_existing_file_guard(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'test.db';store=Store(path)
            store.call('POST','/agents',{},dict(name='existing',provider='synthetic'),'synthetic-invite','existing-agent','synthetic-invite')
            before=path.read_bytes();saved=snapshot(path)
            self.assertEqual(before,path.read_bytes())
            self.assertEqual(1,len(saved['agents']))
            target=Path(folder)/'snapshot.json';write_new(target,json.dumps(saved))
            with self.assertRaises(FileExistsError):write_new(target,'overwrite')
            with self.assertRaises(ValueError):snapshot(Path(folder)/'missing.db')
