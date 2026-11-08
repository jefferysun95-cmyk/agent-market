"""Install/reinstall/uninstall a wheel in a clean venv; synthetic localhost only."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import venv
from datetime import datetime,timezone
import time
from http.server import ThreadingHTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import Store, handler


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('wheel')
    wheel = Path(p.parse_args().wheel).resolve()
    with tempfile.TemporaryDirectory(prefix='market-install-') as temp:
        root = Path(temp)
        venv.create(root / 'venv', with_pip=True)
        binary = root / 'venv' / ('Scripts' if os.name == 'nt' else 'bin')
        python = binary / ('python.exe' if os.name == 'nt' else 'python')
        cli = binary / ('agent-market.exe' if os.name == 'nt' else 'agent-market')
        env = {k:v for k,v in os.environ.items() if not k.startswith('MARKET_') and k != 'PYTHONPATH'}
        env['PYTHONIOENCODING'] = 'utf-8'
        env['LOCALAPPDATA'] = str(root/'runtime')
        private = root / 'private-配置'
        private.mkdir()
        credentials = private / 'credentials.json'
        config = private / 'client.json'
        env['MARKET_CONFIG_FILE'] = str(config)
        store = Store(root / 'test.db')
        registration = store.call('POST', '/agents', {}, dict(name='install-check', provider='synthetic'), 'synthetic-invite', 'register', 'synthetic-invite')
        credentials.write_text(json.dumps(registration), encoding='utf-8')
        original = credentials.read_bytes()
        http = ThreadingHTTPServer(('127.0.0.1', 0), handler(store, 'synthetic-invite'))
        thread = threading.Thread(target=http.serve_forever, daemon=True)
        thread.start()

        def run(*args, expected=0):
            result = subprocess.run([str(a) for a in args], cwd=root, env=env, capture_output=True, text=True, encoding='utf-8', timeout=90)
            if result.returncode != expected:
                raise RuntimeError('Clean install command failed: ' + result.stderr)
            if registration['token'] in result.stdout + result.stderr:
                raise RuntimeError('Credential leaked')
            return result.stdout if expected==0 else result.stderr

        try:
            run(python, '-m', 'pip', 'install', '--no-index', '--no-deps', wheel)
            assert '1.1.0-alpha.4' in run(cli, '--version')
            run(cli, 'config', 'init', '--url', f'http://127.0.0.1:{http.server_port}', '--credentials-file', credentials)
            doctor = json.loads(run(cli, 'doctor'))
            assert doctor['data']['identity']['name'] == 'install-check'
            tasks = json.loads(run(cli, 'tasks', 'list', '--mine'))
            assert tasks['data']['items'] == []
            # Profile inspection is offline and never launches a real model.
            simulated_entry=private/'simulated-openclaw.mjs';simulated_entry.write_text('',encoding='utf-8')
            profile=private/'openclaw-profile.json'
            profile.write_text(json.dumps(dict(schema_version=1,mode='local',runtime=str(python),entry=str(simulated_entry),
                agent_id='agent-market-install-check',workspace=str(private),timeout_seconds=10,dedicated_agent=True)),encoding='utf-8')
            inspected=json.loads(run(cli,'openclaw','inspect','--profile',profile))['data']
            assert inspected['paths_ready'] and inspected['model_probe']=='not_run'
            # Installed runner invokes a trusted consumer and then stops when
            # the next business action is outside this fixture's authorization.
            task=store.call('POST','/tasks',{},dict(title='Installed runner check',category='data-cleaning',
                brief='Synthetic',acceptance='Select the fixed fixture proposal',budget='CNY 0',deadline='2030-01-01'),
                registration['token'],'create-installed-runner','synthetic-invite')
            host=root/'trusted_host.py'
            host.write_text('''import json,sys
from agent_market.market import request
w=json.load(sys.stdin)
t=request('GET','/tasks/'+w['intent']['task_id'])
assert t['buyer']==w['scope']['actor_id'] and t['status']=='open'
request('POST','/tasks/'+t['id']+'/select',w['intent']['step']['body'],w['intent']['step']['key'])
print(json.dumps(dict(schema_version=1,work_id=w['work_id'],outcome='completed')))
''',encoding='utf-8')
            policy=dict(actor_id=registration['agent']['id'],task_id=task['id'],
                url=f'http://127.0.0.1:{http.server_port}',expires_at=datetime.fromtimestamp(time.time()+60,timezone.utc).isoformat(),
                max_seconds=30,interval_seconds=1,
                host=dict(argv=[str(python),str(host)],cwd=str(root),timeout_seconds=10),
                steps=[dict(id='select-fixture',phase='awaiting_selection',revision=0,kind='handoff',action='select',body={},key='select-installed-fixture')])
            supplier=store.call('POST','/agents',{},dict(name='fixture-seller',provider='synthetic'),
                'synthetic-invite','register-installed-seller','synthetic-invite')
            quoted=store.call('POST','/tasks/'+task['id']+'/proposals',{},dict(price='CNY 0',terms='synthetic',deadline='2030-01-01'),
                supplier['token'],'fixture-proposal','synthetic-invite')
            policy['steps'][0]['body']={'proposal_id':quoted['proposals'][0]['id']}
            policy_file=private/'runner-policy.json';policy_file.write_text(json.dumps(policy),encoding='utf-8')
            result=json.loads(run(cli,'run','--policy',policy_file,'--state',private/'job.db',expected=7))
            assert result['error']['code']=='authorization_or_handler_missing'
            current=store.call('GET','/tasks/'+task['id'],{}, {},registration['token'],None,'synthetic-invite')
            assert current['selected']==quoted['proposals'][0]['id']
            assert json.loads(run(cli,'status','--state',private/'job.db'))['data']['live'] is False
            saved = config.read_bytes()
            run(python, '-m', 'pip', 'install', '--no-index', '--no-deps', '--force-reinstall', wheel)
            assert json.loads(run(cli, 'identity'))['data']['name'] == 'install-check'
            run(python, '-m', 'pip', 'uninstall', '-y', 'agent-market-client')
            assert config.read_bytes() == saved and credentials.read_bytes() == original
            print('PASS: clean wheel install, installed CLI/host-runner, reinstall/uninstall preserve private files')
        finally:
            http.shutdown(); http.server_close(); thread.join(3)


if __name__ == '__main__':
    main()
