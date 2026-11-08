"""Private deployment preparation and read-only preservation checks; never sends mail."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def write_new(path, content, mode=0o600):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,mode)
    with os.fdopen(fd,'w',encoding='utf-8') as f:
        f.write(content);f.flush();os.fsync(f.fileno())

def mail_env(source,target):
    from registration import from_environment
    from server import CATEGORIES
    data=json.loads(Path(source).read_text(encoding='utf-8'))
    expected={'MARKET_SELF_REGISTRATION','MARKET_MAIL_TRANSPORT','MARKET_MAIL_FROM',
              'MARKET_ZOHO_API_KEY','MARKET_ZOHO_API_URL','MARKET_REGISTRATION_SECRET'}
    if set(data)!=expected or any(not isinstance(v,str) or not v.isascii() or any(ord(c)<32 or ord(c)>126 for c in v) for v in data.values()):
        raise ValueError('Invalid private registration configuration')
    if data['MARKET_SELF_REGISTRATION']!='1' or data['MARKET_MAIL_TRANSPORT']!='zoho_api':
        raise ValueError('Expected explicit API registration configuration')
    os.environ.update(data)
    from_environment(None,CATEGORIES)  # Validate only; no sender call.
    write_new(target,''.join(k+'='+json.dumps(v)+'\n' for k,v in sorted(data.items())))

def nginx_patch(text):
    if re.search(r'\blimit_req\b',text):
        raise ValueError('Existing rate limits require review; configuration not overwritten')
    names=re.findall(r'^\s*server_name\s+([^;]+);',text,re.M)
    if not names or any(name.strip()!='api.digolives.com' for name in names):
        raise ValueError('Expected a dedicated api.digolives.com site')
    result,count=re.subn(r'(^[ \t]*server_name[ \t]+api\.digolives\.com[ \t]*;[^\n]*\n)',
        r'\1    limit_req zone=market_alpha5 burst=20 nodelay;\n    limit_req_status 429;\n',text,flags=re.M)
    if count!=len(names):raise ValueError('Unrecognized server_name layout')
    result=re.sub(r'proxy_set_header\s+X-Forwarded-For\s+[^;]+;',
                  'proxy_set_header X-Forwarded-For $remote_addr;',result)
    return result

def snapshot(path):
    if not Path(path).is_file():raise ValueError('Existing database required')
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
    try:
        if db.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Database check failed')
        return {table:{row[0]:hashlib.sha256(json.dumps(list(row[1:]),ensure_ascii=False).encode()).hexdigest()
                       for row in db.execute('SELECT '+fields+' FROM '+table)}
                for table,fields in [('agents','id,token_hash,profile'),('tasks','id,buyer,status,body')]}
    finally:db.close()

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    c=sub.add_parser('mail-env');c.add_argument('source');c.add_argument('output')
    c=sub.add_parser('nginx');c.add_argument('source');c.add_argument('output')
    c=sub.add_parser('snapshot');c.add_argument('db');c.add_argument('output')
    c=sub.add_parser('verify');c.add_argument('db');c.add_argument('before')
    a=p.parse_args()
    try:
        if a.action=='mail-env':mail_env(a.source,a.output)
        elif a.action=='nginx':write_new(a.output,nginx_patch(Path(a.source).read_text(encoding='utf-8')))
        elif a.action=='snapshot':write_new(a.output,json.dumps(snapshot(a.db)))
        else:
            before=json.loads(Path(a.before).read_text());after=snapshot(a.db)
            for table,rows in before.items():
                if any(after[table].get(key)!=value for key,value in rows.items()):
                    raise ValueError('Existing identity/order changed; inspect private backup')
            print(json.dumps(dict(existing_records_preserved=True,counts={k:len(v) for k,v in before.items()})))
        return 0
    except Exception:
        print('Deployment check failed; private values suppressed. Review paths/configuration and backups.',file=sys.stderr)
        return 1

if __name__=='__main__':sys.exit(main())
