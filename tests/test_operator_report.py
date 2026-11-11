import hashlib
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone

SPEC = importlib.util.spec_from_file_location('operator_report', Path(__file__).parents[1]/'tools/operator_report.py')
report = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(report)
NOW = datetime(2026,11,11,12,tzinfo=timezone.utc)


class OperatorReportTest(unittest.TestCase):
    def seed(self, path):
        from server import Store
        Store(path)
        with closing(sqlite3.connect(path)) as db, db:
            for aid,name in [('buyer','<script>alert(1)</script>'),('supplier','Supplier'),('new','New')]:
                profile=dict(name=name,provider='test-harness',created_at='2026-11-10T10:00:00+00:00')
                db.execute('INSERT INTO agents VALUES(?,?,?)',(aid,'DO_NOT_SHOW_TOKEN_HASH_'+aid,json.dumps(profile)))
            for tid,buyer,status,proposals,selected,date in [
                    ('t1','buyer','accepted',[dict(id='p1',seller='supplier',price='PRIVATE_PRICE')],'p1','2026-11-10T11:00:00+00:00'),
                    ('t2','new','open',[],None,'2026-11-09T09:00:00+00:00'),
                    ('t3','new','cancelled',[],None,'2026-11-11T09:00:00+00:00')]:
                body=dict(title='DO_NOT_SHOW_TITLE',brief='DO_NOT_SHOW_BRIEF',acceptance='PRIVATE_ACCEPTANCE',
                          category='data-cleaning',proposals=proposals,selected=selected,created_at=date,
                          payment={'PRIVATE_PAYMENT':'DO_NOT_SHOW'},delivery={'result':'DO_NOT_SHOW_RESULT'})
                db.execute('INSERT INTO tasks VALUES(?,?,?,?)',(tid,buyer,status,json.dumps(body)))
            for tid,actor,action,date in [('t1','supplier','proposals','2026-11-10T11:01:00+00:00'),
                       ('t1','buyer','accept','2026-11-11T09:00:00+00:00'),
                       ('t2','new','created','2026-11-09T09:00:00+00:00')]:
                db.execute('INSERT INTO events(task_id,actor,action,payload,created_at) VALUES(?,?,?,?,?)',
                           (tid,actor,action,'DO_NOT_SHOW_EVENT_PAYLOAD',date))
            db.execute('INSERT INTO self_service_accounts VALUES(?,?,?, ?,?)',('DO_NOT_SHOW_EMAIL_HASH','new-slot','new',1794304800,0))
            db.execute('INSERT INTO registration_challenges(id,key_hash,fingerprint,email_hash,agent_key,purpose,profile,code_hash,created,expires,status,peer_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                       ('challenge','DO_NOT_SHOW_KEY','private','private','new-slot','recover','{}','DO_NOT_SHOW_CODE_HASH',1,2,'complete','private'))

    def test_counts_labels_dates_and_private_field_exclusion(self):
        with tempfile.TemporaryDirectory() as temp:
            db=Path(temp)/'market.db';self.seed(db)
            before=hashlib.sha256(db.read_bytes()).hexdigest()
            data=report.snapshot(db,days=3,test_agents={'supplier'},now=NOW)
            self.assertEqual(3,data['totals']['agents'])
            self.assertEqual(3,data['totals']['tasks'])
            self.assertEqual(1,data['totals']['self_service_slots'])
            self.assertEqual(1,data['totals']['verified_contact_addresses'])
            self.assertEqual(1,data['classified']['test_tasks'])
            self.assertEqual(2,data['classified']['unlabelled_tasks'])
            self.assertEqual(0,data['unlabelled_activity']['accepted_tasks'])
            self.assertEqual([1,0,1],[r['created_tasks'] for r in data['daily_unlabelled_utc']])
            self.assertEqual([0,0,0],[r['accepted_events'] for r in data['daily_unlabelled_utc']])
            self.assertEqual('t2',data['idle_unlabelled_tasks_24h'][0]['id'])
            self.assertEqual({'complete':1},data['retained_challenge_states'])
            self.assertEqual(before,hashlib.sha256(db.read_bytes()).hexdigest())
            for output in (json.dumps(data),report.render_text(data),report.render_html(data)):
                for secret in ('DO_NOT_SHOW','PRIVATE_PRICE','PRIVATE_ACCEPTANCE','PRIVATE_PAYMENT','token_hash','code_hash','email_hash'):
                    self.assertNotIn(secret,output)
            html=report.render_html(data)
            self.assertNotIn('<script>',html)
            self.assertIn('&lt;script&gt;',html)
            self.assertIn("default-src 'none'",html)

    def test_legacy_missing_database_and_restricted_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            db=Path(temp)/'missing.db'
            with self.assertRaises(ValueError):report.snapshot(db)
            self.assertFalse(db.exists())
            with closing(sqlite3.connect(db)) as conn, conn:
                conn.executescript('CREATE TABLE agents(id,token_hash,profile);CREATE TABLE tasks(id,buyer,status,body);')
                conn.execute('INSERT INTO agents VALUES(?,?,?)',('legacy','private','{"name":"old"}'))
                conn.execute('INSERT INTO tasks VALUES(?,?,?,?)',('old','legacy','accepted','{"proposals":[]}'))
            data=report.snapshot(db,recent=0,now=NOW)
            self.assertIsNone(data['totals']['self_service_slots'])
            self.assertIsNone(data['retained_challenge_states'])
            self.assertEqual([],data['recent_tasks'])
            self.assertEqual(1,data['unlabelled_activity']['accepted_tasks'])
            self.assertEqual(0,sum(r['registered_agents'] for r in data['daily_unlabelled_utc']))

    def test_live_wal_snapshot_and_cli_no_side_effects(self):
        with tempfile.TemporaryDirectory() as temp:
            db=Path(temp)/'live.db';self.seed(db)
            with closing(sqlite3.connect(db)) as writer, writer:
                writer.execute('PRAGMA journal_mode=WAL')
                writer.execute('UPDATE tasks SET status=? WHERE id=?',('working','t2'))
                writer.commit()
                writer.execute('BEGIN IMMEDIATE')
                writer.execute('UPDATE tasks SET status=? WHERE id=?',('delivered','t2'))
                data=report.snapshot(db,now=NOW)
                self.assertEqual(1,data['totals']['task_states']['working'])
                self.assertNotIn('delivered',data['totals']['task_states'])
                writer.rollback()
            script=Path(__file__).parents[1]/'tools/operator_report.py'
            p=subprocess.run([sys.executable,str(script),'--db',str(db),'--format','json','--recent','0'],capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(0,p.returncode,p.stderr)
            self.assertEqual('read_only_snapshot',json.loads(p.stdout)['database_access'])
            bad=subprocess.run([sys.executable,str(script),'--db',str(db),'--days','0'],capture_output=True,text=True)
            self.assertEqual(2,bad.returncode)

    def test_labels_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'labels.json'
            p.write_text('{"test_agent_ids":["supplier"],"test_task_ids":["t2"]}',encoding='utf-8')
            self.assertEqual(({'supplier'},{'t2'}),report.read_labels(p))
            p.write_text('{"token":"not-a-label"}',encoding='utf-8')
            with self.assertRaises(ValueError):report.read_labels(p)
