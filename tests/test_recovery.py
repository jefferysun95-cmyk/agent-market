import hashlib
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from server import Store


class RecoveryTest(unittest.TestCase):
    def test_legacy_schema_and_online_backup_restore(self):
        with tempfile.TemporaryDirectory() as temp:
            dbpath=Path(temp)/'old.db';backup=Path(temp)/'backup.db'
            # Minimal pre-1.1 schema and old random token: migration cannot reissue it.
            with closing(sqlite3.connect(dbpath)) as db:
                db.executescript('''CREATE TABLE agents(id TEXT PRIMARY KEY,token_hash TEXT UNIQUE,profile TEXT);
                    CREATE TABLE tasks(id TEXT PRIMARY KEY,buyer TEXT,status TEXT,body TEXT);''')
                db.execute('INSERT INTO agents VALUES(?,?,?)',('legacy',hashlib.sha256(b'old-token').hexdigest(),json.dumps({'id':'legacy','name':'old','capabilities':[]})))
                order={'id':'old-order','buyer':'legacy','proposals':[],'selected':None,'payment':{},'revision':1,'delivery':{'result':{'rows':[1,2]}}}
                db.execute('INSERT INTO tasks VALUES(?,?,?,?)',('old-order','legacy','accepted',json.dumps(order)))
                db.commit()
            store=Store(dbpath)
            self.assertEqual('legacy',store.call('GET','/me',{}, {},'old-token','','')['id'])
            subprocess.run([sys.executable,'manage.py','--db',str(dbpath),'backup',str(backup)],check=True,capture_output=True,cwd=Path(__file__).parents[1])
            restored=Store(backup)
            self.assertEqual('legacy',restored.call('GET','/me',{}, {},'old-token','','')['id'])
            task=restored.call('GET','/tasks/old-order',{}, {},'old-token','','')
            self.assertEqual('accepted',task['status'])
            self.assertEqual([1,2],task['delivery']['result']['rows'])
            with closing(sqlite3.connect(backup)) as db:self.assertEqual('ok',db.execute('PRAGMA integrity_check').fetchone()[0])
            # Never replace an existing backup implicitly.
            result=subprocess.run([sys.executable,'manage.py','--db',str(dbpath),'backup',str(backup)],capture_output=True,cwd=Path(__file__).parents[1])
            self.assertNotEqual(0,result.returncode)
