import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError

from registration_mail import zoho_sender, MailDeliveryError, NoRedirect, ZOHO_ENDPOINT
from registration import from_environment
from server import CATEGORIES
from tools import configure_zoho_api as setup


class ZohoRegistrationTest(unittest.TestCase):
    key = 'synthetic-private-api-key-123456'

    def response(self, payload, status=200):
        result = MagicMock()
        result.__enter__.return_value.status = status
        result.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        return result

    def test_exact_request_and_positive_acceptance_not_delivery(self):
        response = self.response(dict(data=[dict(code='EM_104')], request_id='req-synthetic'))
        with patch('registration_mail.build_opener') as build:
            build.return_value.open.return_value = response
            result = zoho_sender('verify@example.com', self.key)('user@example.com', '12345678', 'test-request')
            request = build.return_value.open.call_args.args[0]
            self.assertEqual(ZOHO_ENDPOINT, request.full_url)
            self.assertEqual('Zoho-enczapikey ' + self.key, request.get_header('Authorization'))
            payload = json.loads(request.data)
            self.assertEqual('user@example.com', payload['to'][0]['email_address']['address'])
            self.assertIn('12345678', payload['textbody'])
            self.assertFalse(payload['track_opens'])
            self.assertFalse(payload['track_clicks'])
            self.assertIs(build.call_args.args[0], NoRedirect)
            self.assertEqual(1, build.return_value.open.call_count)
            self.assertTrue(result['provider_accepted'])
            self.assertFalse(result['mailbox_delivery_confirmed'])
            self.assertNotIn(self.key, json.dumps(result))

    def test_rejects_unconfirmed_error_oversize_or_redirect_without_retry(self):
        for payload in ({}, dict(data=[dict(code='ERROR')], request_id='req-x'),
                        dict(data=[dict(code='EM_104')]), dict(error='rejected', data=[dict(code='EM_104')], request_id='req-x')):
            with patch('registration_mail.build_opener') as build:
                build.return_value.open.return_value = self.response(payload)
                with self.assertRaises(MailDeliveryError):
                    zoho_sender('verify@example.com', self.key)('user@example.com', '12345678', 'id')
                self.assertEqual(1, build.return_value.open.call_count)
        with patch('registration_mail.build_opener') as build:
            build.return_value.open.side_effect = HTTPError(ZOHO_ENDPOINT, 302, 'untrusted text', {}, io.BytesIO())
            with self.assertRaises(MailDeliveryError) as caught:
                zoho_sender('verify@example.com', self.key)('user@example.com', '12345678', 'id')
            self.assertEqual(302, caught.exception.http_status)
            self.assertNotIn('untrusted text', str(caught.exception))
            self.assertEqual(1, build.return_value.open.call_count)

    def test_created_or_accepted_requires_positive_body_not_status_alone(self):
        for status in (201, 202):
            with patch('registration_mail.build_opener') as build:
                build.return_value.open.return_value = self.response(dict(data=[dict(code='EM_104')], request_id='req-created'), status)
                result = zoho_sender('verify@example.com', self.key)('user@example.com', '12345678', 'id')
                self.assertEqual(status, result['http_status'])
                self.assertTrue(result['provider_accepted'])
                self.assertFalse(result['mailbox_delivery_confirmed'])
                self.assertEqual(1, build.return_value.open.call_count)
            with patch('registration_mail.build_opener') as build:
                build.return_value.open.return_value = self.response(dict(message='unexpected'), status)
                with self.assertRaises(MailDeliveryError):
                    zoho_sender('verify@example.com', self.key)('user@example.com', '12345678', 'id')
        self.assertIsNone(NoRedirect().redirect_request(None, None, None, None, None, None))
        with patch('registration_mail.build_opener') as build:
            response = self.response({})
            response.__enter__.return_value.read.return_value = b'x' * 65537
            build.return_value.open.return_value = response
            with self.assertRaises(MailDeliveryError):
                zoho_sender('verify@example.com', self.key)('user@example.com', '12345678', 'id')
            self.assertEqual(1, build.return_value.open.call_count)

    def test_bad_endpoint_or_key_fails_before_network_and_factory_selects_api(self):
        for endpoint in ('http://cpaas.zoho.com/v1.1/email', 'https://cpass.zoho.com/v1.1/email', 'https://other.example/v1.1/email'):
            with self.assertRaises(ValueError): zoho_sender('verify@example.com', self.key, endpoint)
        with self.assertRaises(ValueError): zoho_sender('verify@example.com', 'injected\r\nheader')
        with patch.dict(os.environ, dict(MARKET_SELF_REGISTRATION='1', MARKET_MAIL_TRANSPORT='zoho_api',
                        MARKET_MAIL_FROM='verify@example.com', MARKET_ZOHO_API_KEY=self.key,
                        MARKET_REGISTRATION_SECRET='synthetic-registration-secret-'*2), clear=True), patch('registration.smtplib.SMTP_SSL') as smtp:
            service = from_environment(None, CATEGORIES)
            self.assertIsNotNone(service)
            smtp.assert_not_called()

    def test_api_setup_preserves_secret_and_old_config_never_echoes_key(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder)/'smtp.json', Path(folder)/'api.json'
            old = dict(MARKET_SMTP_FROM='verify@example.com', MARKET_SMTP_PASSWORD='synthetic-smtp-password',
                       MARKET_REGISTRATION_SECRET='synthetic-existing-registration-secret-'*2)
            source.write_text(json.dumps(old), encoding='utf-8')
            before = source.read_bytes()
            output = io.StringIO()
            with patch.object(setup.getpass,'getpass',return_value=self.key), contextlib.redirect_stdout(output):
                self.assertEqual(0,setup.main(['--smtp-config',str(source),'--output',str(target)]))
            self.assertNotIn(self.key, output.getvalue())
            configured=json.loads(target.read_text())
            self.assertEqual(old['MARKET_REGISTRATION_SECRET'],configured['MARKET_REGISTRATION_SECRET'])
            self.assertNotIn('MARKET_SMTP_PASSWORD',configured)
            self.assertEqual(before,source.read_bytes())
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(2,setup.main(['--smtp-config',str(source),'--output',str(target)]))
