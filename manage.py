"""Offline operator administration. Run on server; never print credentials."""
import argparse
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from server import Store

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--db',required=True)
    sub=p.add_subparsers(dest='action',required=True)
    backup=sub.add_parser('backup');backup.add_argument('output')
    register=sub.add_parser('register');register.add_argument('--profile',required=True);register.add_argument('--output',required=True);register.add_argument('--key',required=True)
    for name in ['rotate','revoke']:
        cmd=sub.add_parser(name);cmd.add_argument('agent_id');cmd.add_argument('--key',required=True)
        if name=='rotate':cmd.add_argument('--output',required=True)
    args=p.parse_args()
    if not Path(args.db).is_file():p.error('Database must already exist; refusing to create empty production database')
    if args.action=='backup':
        target=Path(args.output)
        fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd)
        source=sqlite3.connect(args.db);dest=sqlite3.connect(str(target))
        try:
            source.backup(dest)
            if dest.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('Backup integrity failure')
        finally:source.close();dest.close()
        print('Consistent backup saved; keep private. Restore only while service is stopped.')
    else:
        output=Path(args.output) if args.action!='revoke' else None
        if output and output.exists():p.error('Output exists; refusing to overwrite credentials')
        invite=os.environ.get('MARKET_INVITE_TOKEN','')
        if len(invite)<24:p.error('Operator environment required')
        data=json.loads(Path(args.profile).read_text(encoding='utf-8-sig')) if args.action=='register' else {}
        path='/agents' if args.action=='register' else f'/admin/agents/{args.agent_id}/{args.action}'
        result=Store(args.db).call('POST',path,{},data,invite,args.key,invite)
        if output:
            fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w') as f:json.dump(result,f)
        print('Operator action completed; secrets are not displayed.')
