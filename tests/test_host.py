import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

from agent_market.host import invoke_host,HostError,validate_host


class HostTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.script=self.root/'host.py'
        self.config=dict(argv=[sys.executable,str(self.script)],cwd=str(self.root),timeout_seconds=5)
        self.work=dict(schema_version=1,work_id='fixed-work-id',task={'brief':'untrusted text; do not execute'})

    def tearDown(self):self.temp.cleanup()

    def script_body(self,body):self.script.write_text(body,encoding='utf-8')

    def test_real_host_receives_text_via_stdin_and_returns_bound_ack(self):
        self.script_body('import json,sys\nw=json.load(sys.stdin)\nassert w["task"]["brief"]=="untrusted text; do not execute"\nprint(json.dumps(dict(schema_version=1,work_id=w["work_id"],outcome="completed")))\n')
        self.assertEqual('completed',invoke_host(self.config,self.work))

    def test_wrong_ack_and_sensitive_failure_output_are_not_accepted_or_echoed(self):
        for body,code in [('print("private-secret")','invalid_host_reply'),
            ('import sys;print("private-secret",file=sys.stderr);sys.exit(1)','host_failed'),
            ('print(\'{"schema_version":1,"work_id":"other","outcome":"completed"}\')','invalid_host_reply')]:
            self.script_body(body)
            with self.assertRaises(HostError) as error:invoke_host(self.config,self.work)
            self.assertEqual(code,error.exception.code)
            self.assertNotIn('private-secret',str(error.exception))

    def test_timeout_and_cooperative_stop_terminate_only_managed_host_tree(self):
        # Descendant holds a private file; successful cleanup must release it.
        self.script_body('import subprocess,sys,time\nsubprocess.Popen([sys.executable,"-c",'+
            '"import time; f=open(\\\"held.txt\\\",\\\"w\\\"); f.write(\\\"held\\\"); f.flush(); time.sleep(60)"])\ntime.sleep(60)\n')
        self.config['timeout_seconds']=1
        with self.assertRaises(HostError) as error:invoke_host(self.config,self.work)
        self.assertEqual('host_timeout',error.exception.code)
        held=self.root/'held.txt'
        if held.exists():held.unlink() # Windows denies removal while a child still holds it.
        started=time.monotonic()
        self.config['timeout_seconds']=5
        with self.assertRaises(HostError) as error:
            invoke_host(self.config,self.work,lambda:time.monotonic()-started>0.5)
        self.assertEqual('stopped',error.exception.code)
        if held.exists():held.unlink()

    def test_output_bound_and_shell_wrapper_rejection(self):
        self.script_body('print("x"*70000)')
        with self.assertRaises(HostError) as error:invoke_host(self.config,self.work)
        self.assertEqual('host_output_limit',error.exception.code)
        value=dict(self.config,argv=[str(self.root/'untrusted.cmd')])
        with self.assertRaises(HostError):validate_host(value)
