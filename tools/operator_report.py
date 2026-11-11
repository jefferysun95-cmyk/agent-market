"""Read-only operator snapshot of Alpha5 SQLite; no server/config/credential imports."""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape
import json
from pathlib import Path
import re
import sqlite3

UTC = timezone.utc
TERMINAL = {'accepted', 'cancelled'}


def timestamp(value):
    if not value:
        return None
    try:
        result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return result.replace(tzinfo=UTC) if result.tzinfo is None else result.astimezone(UTC)
    except (ValueError, TypeError):
        return None


def read_labels(path):
    if not path:
        return set(), set()
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    allowed = {'test_agent_ids', 'test_task_ids'}
    if not isinstance(data, dict) or set(data) - allowed:
        raise ValueError('Labels must contain only test_agent_ids and test_task_ids.')
    values = []
    for key in ('test_agent_ids', 'test_task_ids'):
        items = data.get(key, [])
        if not isinstance(items, list) or len(items) > 10000 or any(
                not isinstance(x, str) or not re.fullmatch('[A-Za-z0-9_-]{1,128}', x) for x in items):
            raise ValueError('Invalid test classification IDs.')
        values.append(set(items))
    return tuple(values)


def snapshot(path, days=7, recent=10, test_agents=None, test_tasks=None, now=None):
    """One consistent, read-only transaction. Whitelisted fields only; never SELECT *."""
    if not 1 <= days <= 90 or not 0 <= recent <= 100:
        raise ValueError('days must be 1..90 and recent 0..100.')
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise ValueError('Database must already exist; no database was created.')
    now = (now or datetime.now(UTC)).astimezone(UTC)
    first_day = (now - timedelta(days=days - 1)).date()
    test_agents, test_tasks = set(test_agents or ()), set(test_tasks or ())
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=5)
    db.row_factory = sqlite3.Row
    try:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'agents', 'tasks'} <= tables:
            raise ValueError('Unsupported database: agents/tasks tables are required.')
        # Extract public metadata in SQL, avoiding token hashes, full profiles and order data.
        agents = [dict(r) for r in db.execute("SELECT id, json_extract(profile,'$.name') AS name, "
                  "json_extract(profile,'$.provider') AS provider, "
                  "json_extract(profile,'$.created_at') AS created_at FROM agents")]
        tasks = [dict(r) for r in db.execute("SELECT t.id,t.buyer,t.status, "
                 "json_extract(t.body,'$.category') AS category, "
                 "json_extract(t.body,'$.created_at') AS created_at, "
                 "json_array_length(t.body,'$.proposals') AS proposal_count, "
                 "(SELECT json_extract(p.value,'$.seller') FROM json_each(t.body,'$.proposals') p "
                 "WHERE json_extract(p.value,'$.id')=json_extract(t.body,'$.selected') LIMIT 1) AS seller "
                 "FROM tasks t")]
        events = ([dict(r) for r in db.execute('SELECT task_id,actor,action,created_at FROM events')]
                  if 'events' in tables else [])
        account_count = contacts = None
        if 'self_service_accounts' in tables:
            account_count, contacts = db.execute('SELECT COUNT(*),COUNT(DISTINCT email_hash) '
                                                'FROM self_service_accounts').fetchone()
        challenges = None
        if 'registration_challenges' in tables:
            challenges = dict(db.execute('SELECT status,COUNT(*) FROM registration_challenges GROUP BY status'))
        db.rollback()
    finally:
        db.close()
    for agent in agents:
        agent['test'] = agent['id'] in test_agents
    for task in tasks:
        task['test'] = task['id'] in test_tasks or task['buyer'] in test_agents or task['seller'] in test_agents
    task_map = {t['id']: t for t in tasks}
    last_event = {}
    daily = {str(first_day + timedelta(days=i)): dict(registered_agents=0, created_tasks=0,
              proposal_events=0, accepted_events=0) for i in range(days)}
    active = set()
    for agent in agents:
        stamp = timestamp(agent['created_at'])
        if stamp and stamp <= now and str(stamp.date()) in daily and not agent['test']:
            daily[str(stamp.date())]['registered_agents'] += 1
    for task in tasks:
        stamp = timestamp(task['created_at'])
        if stamp and stamp <= now and str(stamp.date()) in daily and not task['test']:
            daily[str(stamp.date())]['created_tasks'] += 1
    for event in events:
        stamp = timestamp(event['created_at'])
        if not stamp or stamp > now:
            continue
        tid = event['task_id']
        last_event[tid] = max(last_event.get(tid, stamp), stamp)
        if tid in test_tasks or task_map.get(tid, {}).get('test') or event['actor'] in test_agents:
            continue
        day = str(stamp.date())
        if day in daily and event['action'] in ('proposals', 'accept'):
            daily[day]['proposal_events' if event['action'] == 'proposals' else 'accepted_events'] += 1
        if stamp >= now - timedelta(hours=24):
            active.add(event['actor'])
    remaining = [t for t in tasks if not t['test']]
    stale = []
    for task in remaining:
        last = last_event.get(task['id']) or timestamp(task['created_at'])
        if task['status'] not in TERMINAL and last and now - last >= timedelta(hours=24):
            stale.append(dict(id=task['id'], status=task['status'], last_activity_utc=last.isoformat(),
                              idle_hours=round((now-last).total_seconds()/3600, 1)))
    def newest(rows):
        return sorted(rows, key=lambda x: str(x.get('created_at') or ''), reverse=True)[:recent]
    return dict(schema_version=1, generated_at_utc=now.isoformat(), database_access='read_only_snapshot',
        window=dict(days=days, first_day_utc=str(first_day), today_is_partial=True),
        totals=dict(agents=len(agents), self_service_slots=account_count, verified_contact_addresses=contacts,
                    tasks=len(tasks), task_states=dict(Counter(t['status'] for t in tasks))),
        classified=dict(test_agents=sum(a['test'] for a in agents), test_tasks=sum(t['test'] for t in tasks),
                        unlabelled_agents=sum(not a['test'] for a in agents), unlabelled_tasks=len(remaining),
                        unlabelled_task_states=dict(Counter(t['status'] for t in remaining)),
                        classification_provided=bool(test_agents or test_tasks)),
        unlabelled_activity=dict(event_actors_last_24h=len(active), tasks_with_proposals=sum(
            (t['proposal_count'] or 0) > 0 for t in remaining),
            accepted_tasks=sum(t['status']=='accepted' for t in remaining)),
        daily_unlabelled_utc=[dict(date=k, **v) for k,v in daily.items()],
        retained_challenge_states=challenges,
        recent_agents=newest(agents), recent_tasks=newest(tasks),
        idle_unlabelled_tasks_24h=sorted(stale, key=lambda x:x['idle_hours'], reverse=True)[:recent],
        limitations=[
            'Unlabelled is not verified organic usage; explicitly classify known test identities/orders.',
            'No download/install attribution, real-user count, revenue, live-host or model-balance telemetry.',
            'Accepted is recorded acceptance, not proof of payment or independent delivery correctness.',
            'Challenge records are pruned: retained counts are not lifetime requests or delivered-email counts.',
            'Daily counts use UTC calendar dates; registration counts exclude recovery and profiles without dates.',
            '24h idle is a review hint, not an enforced deadline, failure verdict or automatic action.',
            'This is a point-in-time operator report, not a background monitor; refresh by running again.'
        ])


def render_text(data):
    return '\n'.join([
        'Agent Market 运营快照 / Operator snapshot',
        'UTC: ' + data['generated_at_utc'],
        '总身份 / Agents: ' + str(data['totals']['agents']),
        '自助身份槽位 / Self-service slots: ' + str(data['totals']['self_service_slots']),
        '已验证联系地址 / Verified addresses: ' + str(data['totals']['verified_contact_addresses']),
        '总订单 / Tasks: ' + str(data['totals']['tasks']),
        '订单状态 / States: ' + json.dumps(data['totals']['task_states'], ensure_ascii=False),
        '测试分类 / Classification: ' + json.dumps(data['classified'], ensure_ascii=False),
        'Daily unlabelled counts (UTC; not independently identified real users):',
        *[json.dumps(x, ensure_ascii=False) for x in data['daily_unlabelled_utc']],
        '24h idle review hints: ' + json.dumps(data['idle_unlabelled_tasks_24h'], ensure_ascii=False),
        'Retained challenge states: ' + json.dumps(data['retained_challenge_states']),
        *['NOTE: '+x for x in data['limitations']]
    ])


def render_html(data):
    def table(rows):
        if not rows:
            return '<p>暂无记录 / No records</p>'
        keys = list(rows[0])
        return '<table><thead><tr>' + ''.join('<th>'+escape(k)+'</th>' for k in keys) + \
               '</tr></thead><tbody>' + ''.join('<tr>'+''.join('<td>'+escape(str(row.get(k,'')))+
               '</td>' for k in keys)+'</tr>' for row in rows) + '</tbody></table>'
    cards = ''.join('<div><b>'+escape(str(data['totals'][k]))+'</b><span>'+label+'</span></div>' for k,label in
                    [('agents','身份总数 / Agents'),('self_service_slots','自助身份 / Self-service'),
                     ('verified_contact_addresses','验证地址 / Contacts'),('tasks','订单总数 / Tasks')])
    states = [dict(status=k, count=v) for k,v in data['totals']['task_states'].items()]
    return '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Agent Market 运营快照</title><style>body{font:15px system-ui;max-width:1180px;margin:32px auto;padding:0 20px;color:#183047;background:#f4f7fa}h1{margin-bottom:8px}section{background:white;padding:20px;margin:20px 0;border-radius:12px;overflow:auto}.cards{display:flex;gap:16px;flex-wrap:wrap}.cards div{background:#112238;color:white;border-radius:12px;padding:20px;min-width:160px}.cards b{display:block;font-size:32px}.cards span{display:block;margin-top:8px}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:10px;border-bottom:1px solid #dde4ea;font-size:13px}th{background:#edf3f7}small{color:#526576}li{margin:8px 0}</style>
<h1>Agent Market · 运营快照</h1><small>只读 / Read-only · UTC ''' + escape(data['generated_at_utc']) + \
        '</small><p>未标记不等于真实用户；含历史测试。此文件不会自动刷新，也不会发出网络请求。</p><div class="cards">'+cards+ \
        '</div><section><h2>订单状态（全部）</h2>'+table(states)+ \
        '</section><section><h2>测试分类</h2>'+table([data['classified']])+ \
        '</section><section><h2>每日活动（未标记，UTC）</h2>'+table(data['daily_unlabelled_utc'])+ \
        '</section><section><h2>超过24小时未推进（未标记，仅供检查）</h2>'+table(data['idle_unlabelled_tasks_24h'])+ \
        '</section><section><h2>最近身份</h2>'+table(data['recent_agents'])+ \
        '</section><section><h2>最近订单（不含正文/价格/邮箱）</h2>'+table(data['recent_tasks'])+ \
        '</section><section><h2>统计边界</h2><ul>'+''.join('<li>'+escape(x)+'</li>' for x in data['limitations'])+ \
        '</ul></section></html>'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True, help='Existing server database; never creates or migrates it')
    parser.add_argument('--days', type=int, default=7, help='UTC calendar days, including partial today, 1..90')
    parser.add_argument('--recent', type=int, default=10, help='Metadata rows, 0..100; use 0 for aggregate-only output')
    parser.add_argument('--labels', help='Optional private JSON: test_agent_ids and test_task_ids')
    parser.add_argument('--format', choices=('text','json','html'), default='text')
    args = parser.parse_args()
    try:
        agents,tasks = read_labels(args.labels)
        report = snapshot(args.db, args.days, args.recent, agents, tasks)
    except (ValueError, OSError, sqlite3.Error):
        parser.exit(2, 'Cannot read operator snapshot. Check existing DB path/schema, read permissions and labels; no migration or retry was attempted.\n')
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.format=='json' else
          render_html(report) if args.format=='html' else render_text(report))


if __name__ == '__main__':
    main()
