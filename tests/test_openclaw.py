import json
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from agent_market.openclaw import inspect_profile,parse_envelope,parse_model_json,probe,validate_profile,OpenClawError
from agent_market.host import HostError


class OpenClawTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.entry=self.root/'simulated-openclaw.mjs'
        self.profile=dict(schema_version=1,mode='local',runtime=sys.executable,entry=str(self.entry),
            agent_id='agent-market-test',workspace=str(self.root),timeout_seconds=10,dedicated_agent=True)
        self.entry.write_text('''import json,os,sys
assert '--local' in sys.argv and '--deliver' not in sys.argv
assert not any(k.startswith(('MARKET_','GMAIL_','IMAP_','SMTP_')) for k in os.environ)
prompt=sys.argv[sys.argv.index('--message')+1]
expected=json.loads(prompt[prompt.index('{'):])
session=sys.argv[sys.argv.index('--session-id')+1]
print('[simulated CLI startup log]')
print(json.dumps(dict(payloads=[dict(text=json.dumps(expected))],meta=dict(durationMs=3,agentMeta=dict(provider='simulated',model='test-only',sessionId=session)))))
''',encoding='utf-8')

    def tearDown(self):self.temp.cleanup()

    def envelope(self,text='{"ok":true}',**meta):
        return json.dumps(dict(payloads=[{'text':text}],meta=dict(agentMeta={'provider':'simulated','model':'test-only'},**meta))).encode()

    def test_inspect_does_not_start_a_model(self):
        with patch('agent_market.openclaw.run_host_process') as execute:
            report=inspect_profile(self.profile);execute.assert_not_called()
        self.assertTrue(report['paths_ready']);self.assertEqual('not_run',report['model_probe'])

    def test_simulated_cli_probe_has_nonce_session_and_scrubbed_environment(self):
        with patch.dict(os.environ,{'MARKET_TOKEN':'test-secret','GMAIL_TOKEN':'test-mail-secret'}):
            result=probe(self.profile)
        self.assertTrue(result['ready'])
        self.assertEqual('simulated',result['proof']['provider'])
        self.assertNotIn('test-secret',json.dumps(result))
        self.assertFalse(result['host_tools_independently_audited'])

    def test_ambiguous_outputs_error_payloads_and_missing_metadata_rejected(self):
        bad=[b'{"payloads":[],"meta":{}}',self.envelope(aborted=True),self.envelope(stopReason='error'),
             b'{"payloads":[{"text":"ok","isError":true}],"meta":{"agentMeta":{"provider":"p","model":"m"}}}',
             self.envelope()+b'\ntrailing untrusted text']
        for raw in bad:
            with self.subTest(raw=raw[:40]),self.assertRaises(OpenClawError):parse_envelope(raw)

    def test_model_json_rejects_duplicate_keys_nonfinite_and_non_object(self):
        for text in ('{"x":1,"x":2}','{"x":NaN}','[]','{"ok":true} trophy'):
            with self.assertRaises(OpenClawError):parse_model_json(text)
        self.assertEqual({'ok':True},parse_model_json('```json\n{"ok":true}\n```'))

    def test_explicit_local_mode_only_no_shell_or_relative_paths(self):
        for override in ({'mode':'gateway'},{'runtime':'openclaw.cmd'},{'entry':'relative.mjs'},
            {'runtime':str(self.root/'openclaw.cmd')},{'schema_version':True},{'agent_id':'main'},{'dedicated_agent':False},
            {'startup_grace_seconds':121},{'startup_grace_seconds':True}):
            with self.assertRaises(OpenClawError):validate_profile(dict(self.profile,**override))

    def test_session_mismatch_and_wrong_nonce_fail_probe(self):
        for raw in (self.envelope('{"kind":"readiness","nonce":"wrong"}'),
            json.dumps(dict(payloads=[{'text':'{}'}],meta={'agentMeta':{'provider':'p','model':'m','sessionId':'other'}})).encode()):
            with patch('agent_market.openclaw.run_host_process',return_value=raw),self.assertRaises(OpenClawError):probe(self.profile)

    def test_default_agent_rejected_before_any_runtime_invocation(self):
        with patch('agent_market.openclaw.run_host_process') as invoke,self.assertRaises(OpenClawError):
            probe(dict(self.profile,agent_id='main'))
        invoke.assert_not_called()

    def test_cli_timeout_reports_a_specific_sanitized_host_error(self):
        from agent_market.cli import main
        path=self.root/'profile.json';path.write_text(json.dumps(self.profile),encoding='utf-8')
        out,err=io.StringIO(),io.StringIO()
        with patch.dict(os.environ,{'MARKET_CONFIG_FILE':str(self.root/'absent.json')},clear=True),\
                patch('agent_market.openclaw.probe',side_effect=HostError('host_timeout')),\
                contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            self.assertEqual(7,main(['openclaw','probe','--profile',str(path)]))
        self.assertEqual('openclaw_host_timeout',json.loads(err.getvalue())['error']['code'])
        self.assertEqual('',out.getvalue())
