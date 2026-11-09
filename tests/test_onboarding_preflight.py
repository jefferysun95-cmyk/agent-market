"""Onboarding fails locally before mail/issuance; no private-storage downgrade."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_market.cli import main
from agent_market import onboarding


class PreflightTest(unittest.TestCase):
    def test_offline_probe_checks_both_directories_without_writing_actual_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            session, target = root/'state/signup.json', root/'secrets/credential.json'
            with patch.object(onboarding, 'public_request') as request:
                result = onboarding.preflight(session, target)
            request.assert_not_called()
            self.assertEqual(result['status'], 'preflight_passed')
            self.assertEqual(result['network_requests'], 0)
            self.assertFalse(session.exists())
            self.assertFalse(target.exists())
            self.assertFalse(list(root.rglob('.agent-market-preflight-*')))

    def test_existing_credential_and_same_file_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            session = Path(folder)/'session.json'
            target = Path(folder)/'credential.json'
            target.write_text('private sentinel')
            for candidate in (target, session):
                with self.assertRaises(onboarding.OnboardingError):
                    onboarding.preflight(session, candidate)
            self.assertEqual(target.read_text(), 'private sentinel')

    def test_start_permission_denial_sends_no_code_and_saves_no_state(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            profile = root/'profile.json'
            profile.write_text(json.dumps({'email': 'synthetic@example.com'}))
            output = io.StringIO()
            with patch.object(onboarding, 'create_private', side_effect=onboarding.OnboardingError('ACL denied')), \
                 patch.object(onboarding, 'public_request') as request, \
                 contextlib.redirect_stderr(output):
                code = main(['register', 'start', '--url', 'https://example.com', '--file', str(profile),
                             '--session', str(root/'session.json'), '--credentials-file', str(root/'credential.json')])
            self.assertEqual(code, 2)
            self.assertIn('preflight failed', output.getvalue())
            self.assertIn('Windows ACL', output.getvalue())
            request.assert_not_called()
            self.assertEqual(list(root.iterdir()), [profile])

    def test_finish_permission_denial_happens_before_otp_prompt_or_request(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            session = root/'session.json'
            session.write_text(json.dumps({'schema_version': 1, 'challenge_id': 'a'*32}))
            with patch.object(onboarding, 'create_private', side_effect=PermissionError), \
                 patch.object(onboarding.getpass, 'getpass') as prompt, \
                 patch.object(onboarding, 'public_request') as request, \
                 contextlib.redirect_stderr(io.StringIO()):
                code = main(['register', 'finish', '--session', str(session), '--credentials-file', str(root/'credential.json')])
            self.assertEqual(code, 2)
            prompt.assert_not_called()
            request.assert_not_called()
            self.assertEqual(list(root.iterdir()), [session])

    def test_windows_acl_failure_removes_empty_probe(self):
        # Exercise the real create_private failure cleanup without depending on
        # host platform/sandbox ACL rights. The file contains no secret bytes.
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/'probe'
            with patch.object(onboarding.os, 'name', 'nt'), \
                 patch.object(onboarding.subprocess, 'CREATE_NO_WINDOW', 0, create=True), \
                 patch.object(onboarding.subprocess, 'check_output', return_value=b'"user","S-1-5-21-123"'), \
                 patch.object(onboarding.subprocess, 'run') as acl:
                acl.return_value.returncode = 1
                with self.assertRaises(onboarding.OnboardingError):
                    onboarding.create_private(target)
            self.assertFalse(target.exists())

    def test_git_paths_fail_before_any_network(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'.git').mkdir()
            with patch.object(onboarding, 'public_request') as request:
                with self.assertRaises(onboarding.OnboardingError):
                    onboarding.preflight(root/'state.json', root/'credential.json')
            request.assert_not_called()
