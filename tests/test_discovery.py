from datetime import datetime,timezone
import os
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urlparse,parse_qs
from unittest.mock import patch
import sys

from agent_market.discovery import Discovery


class DiscoveryTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.environment=patch.dict(os.environ,{'MARKET_URL':'https://example.com','LOCALAPPDATA':str(self.root)})
        self.environment.start()
        self.policy=dict(actor_id='seller',url='https://example.com',category='data-cleaning',
            buyers=['buyer'],budgets=['CNY 0'],expires_at=datetime.fromtimestamp(2000,timezone.utc).isoformat(),
            max_seconds=100,interval_seconds=1,max_pages=20)
        self.rows=[dict(id='task-'+str(i),status='open',category='data-cleaning',buyer='other',budget='CNY 0',proposals=[]) for i in range(601)]
        self.rows[-1]['buyer']='buyer'
        self.before=[];self.full_reads=[]
        self.runner=Discovery(self.root/'scan.db',self.api,lambda:1000,lambda seconds:None)

    def tearDown(self):self.environment.stop();self.temp.cleanup()

    def api(self,method,path,*args):
        self.assertEqual('GET',method)
        if path=='/me':return {'id':'seller'}
        if path.startswith('/tasks?'):
            query=parse_qs(urlparse(path).query)
            before=int(query.get('before',['10000'])[0]);self.before.append(before)
            start=0 if before==10000 else 10000-before
            items=self.rows[start:start+100]
            cursor=str(10000-start-len(items)) if start+len(items)<len(self.rows) else None
            return dict(items=items,next_cursor=cursor)
        task_id=path.split('/')[-1];self.full_reads.append(task_id)
        return next(t for t in self.rows if t['id']==task_id).copy()

    def test_more_than_500_irrelevant_rows_and_restart_do_not_hide_match(self):
        self.runner.initialize(self.policy)
        self.runner.tick();self.runner.tick()
        cursor=self.runner.state()['cursor']
        restored=Discovery(self.root/'scan.db',self.api,lambda:1000,lambda seconds:None)
        self.assertEqual(cursor,restored.state()['cursor'])
        for _ in range(5):self.assertTrue(restored.tick())
        pending=restored.work()
        self.assertEqual(1,len(pending))
        self.assertEqual('task-600',pending[0]['intent']['task_id'])
        self.assertFalse(restored.tick()) # No configured host is explicit, not fake automation.
        self.assertEqual('awaiting_host',restored.state()['status'])
        self.assertEqual(['task-600'],self.full_reads)

    def test_real_dispatch_ack_is_not_repeated_on_next_scan(self):
        self.rows=self.rows[-1:]
        self.policy['host']=dict(argv=[sys.executable,'host.py'],cwd=str(self.root),timeout_seconds=5)
        self.runner.initialize(self.policy)
        with patch('agent_market.discovery.invoke_host',return_value='completed') as invoke:
            self.runner.tick();self.runner.tick();self.runner.tick();self.runner.tick()
            self.assertEqual(1,invoke.call_count)
            work=invoke.call_args.args[1]
            self.assertEqual('task-600',work['task']['id'])
            self.assertEqual(['buyer'],work['scope']['buyers'])
        self.assertEqual([],self.runner.work())

    def test_cached_demand_is_re_read_and_closed_or_already_quoted_is_not_dispatched(self):
        self.rows=self.rows[-1:]
        self.policy['host']=dict(argv=[sys.executable,'host.py'],cwd=str(self.root),timeout_seconds=5)
        self.runner.initialize(self.policy);self.runner.tick()
        self.rows[0]['proposals']=[{'seller':'seller'}]
        with patch('agent_market.discovery.invoke_host') as invoke:
            self.runner.tick();invoke.assert_not_called()
        self.assertEqual([],self.runner.work())

    def test_cursor_regression_and_page_limit_stop_instead_of_looping(self):
        self.policy['max_pages']=1
        self.runner.initialize(self.policy)
        self.runner.tick()
        self.assertFalse(self.runner.tick())
        self.assertEqual('discovery_page_limit',self.runner.state()['error'])

    def test_stop_and_origin_change_prevent_network_calls(self):
        self.runner.initialize(self.policy)
        self.runner.stop()
        self.assertFalse(self.runner.tick())
        self.assertEqual([],self.before)
        self.runner.update(stop_requested=False)
        with patch.dict(os.environ,{'MARKET_URL':'https://different.example'}):
            self.assertFalse(self.runner.tick())
        self.assertEqual('origin_mismatch',self.runner.state()['error'])
        self.assertEqual([],self.before)
