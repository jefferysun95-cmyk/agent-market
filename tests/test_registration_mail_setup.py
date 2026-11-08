import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location('registration_mail_setup', Path(__file__).parents[1] / 'tools/configure_registration_mail.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class MailSetupTest(unittest.TestCase):
    def test_hidden_input_private_file_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'mail.json'
            output = io.StringIO()
            with patch('builtins.input', side_effect=['', '', '', '']), patch.object(setup.getpass, 'getpass', return_value='synthetic-private-password'), contextlib.redirect_stdout(output):
                self.assertEqual(0, setup.main(['--output', str(path)]))
            self.assertNotIn('synthetic-private-password', output.getvalue())
            value = json.loads(path.read_text())
            self.assertEqual('verify@run7.ai', value['MARKET_SMTP_FROM'])
            self.assertEqual('465', value['MARKET_SMTP_PORT'])
            self.assertGreaterEqual(len(value['MARKET_REGISTRATION_SECRET']), 32)
            original = path.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(2, setup.main(['--output', str(path)]))
            self.assertEqual(original, path.read_bytes())

    def test_bad_port_does_not_request_password_or_write(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'mail.json'
            with patch('builtins.input', side_effect=['', '25', '', '']), patch.object(setup.getpass, 'getpass') as password, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(2, setup.main(['--output', str(path)]))
            password.assert_not_called()
            self.assertFalse(path.exists())
