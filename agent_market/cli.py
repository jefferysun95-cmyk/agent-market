"""Explicit client actions and opt-in local workers; mailbox grants remain separate."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from . import __version__
from .market import request, validate_base, health, MissingCredential


class ClientError(Exception):
    def __init__(self, code, message, exit_code=2):
        self.code, self.message, self.exit_code = code, message, exit_code


def config_path():
    if os.environ.get('MARKET_CONFIG_FILE'):
        return Path(os.environ['MARKET_CONFIG_FILE']).expanduser()
    if os.name == 'nt':
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'AgentMarket/client.json'
    return Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'agent-market/client.json'


def load_json(path):
    value = json.load(sys.stdin) if path == '-' else json.loads(Path(path).expanduser().read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise ClientError('invalid_input', 'JSON object required.')
    return value


def configure(args):
    target = Path(args.config).expanduser() if args.config else config_path()
    if args.command == 'config':
        url = validate_base(args.url)
        credentials = Path(args.credentials_file).expanduser().resolve()
        if target.resolve() == credentials:
            raise ClientError('invalid_config', 'Config and credentials must be separate files.')
        if target.exists() and not args.force:
            raise ClientError('config_exists', 'Config exists; use --force to replace only the client config.')
        if not isinstance(load_json(str(credentials)).get('token'), str) or not load_json(str(credentials))['token']:
            raise ClientError('credentials_missing', 'Personal credential file has no token.', 3)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(prefix='.client-', dir=target.parent)
        try:
            os.chmod(temp, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(dict(url=url, credentials_file=str(credentials)), f, ensure_ascii=False, indent=2)
            # Exclusive creation prevents accidental concurrent replacement.
            if not args.force:
                with open(target, 'xb') as f:
                    os.chmod(target, 0o600)
                    f.write(Path(temp).read_bytes())
            else:
                os.replace(temp, target)
        finally:
            Path(temp).unlink(missing_ok=True)
        return dict(configured=True, credential_storage='reference_only', network_requests=0)
    config = load_json(str(target)) if target.exists() else {}
    if not os.environ.get('MARKET_URL') and config.get('url'):
        os.environ['MARKET_URL'] = config['url']
    if not os.environ.get('MARKET_CREDENTIALS_FILE') and config.get('credentials_file'):
        os.environ['MARKET_CREDENTIALS_FILE'] = config['credentials_file']
    return None


def parser():
    p = argparse.ArgumentParser(prog='agent-market', description='One-shot Agent Market CLI. Writes require explicit stable keys.')
    p.add_argument('--version', action='version', version=__version__)
    p.add_argument('--config', help='Client config file (contains a credential path, never the Token)')
    sub = p.add_subparsers(dest='command', required=True)
    c = sub.add_parser('config').add_subparsers(dest='operation', required=True).add_parser('init')
    c.add_argument('--url', required=True)
    c.add_argument('--credentials-file', required=True)
    c.add_argument('--force', action='store_true')
    sub.add_parser('doctor')
    sub.add_parser('identity')
    registration=sub.add_parser('register').add_subparsers(dest='operation',required=True)
    start=registration.add_parser('start')
    start.add_argument('--url',required=True)
    start.add_argument('--file',required=True,help='Private registration/recovery request JSON')
    start.add_argument('--session',required=True,help='Private retry state outside Git')
    finish=registration.add_parser('finish')
    finish.add_argument('--session',required=True)
    finish.add_argument('--credentials-file',required=True,help='New private credential file; never overwritten')
    finish.add_argument('--code-file',help='Private code file for non-interactive Agent use; otherwise hidden terminal prompt')
    oc=sub.add_parser('openclaw').add_subparsers(dest='operation',required=True)
    for name in ('inspect','probe'):
        command=oc.add_parser(name)
        command.add_argument('--profile',required=True,help='Private OpenClaw local-mode profile JSON')
    for name in ('run', 'watch', 'discover', 'resume', 'status', 'stop'):
        command = sub.add_parser(name)
        command.add_argument('--state', required=True, help='Private durable job checkpoint')
        if name in ('run', 'watch', 'discover'):
            command.add_argument('--policy', required=True, help='Explicit local authorization policy JSON')
    work = sub.add_parser('work').add_subparsers(dest='operation', required=True)
    work.add_parser('show').add_argument('--state', required=True)
    ack = work.add_parser('ack')
    ack.add_argument('--state', required=True)
    ack.add_argument('--id', required=True)
    ack.add_argument('--outcome', required=True, choices=['completed', 'provider_402', 'handler_failed'])
    s = sub.add_parser('services').add_subparsers(dest='operation', required=True).add_parser('list')
    s.add_argument('--category', default='')
    ts = sub.add_parser('tasks').add_subparsers(dest='operation', required=True)
    listing = ts.add_parser('list')
    listing.add_argument('--mine', action='store_true')
    listing.add_argument('--category', default='')
    listing.add_argument('--before', default='')
    listing.add_argument('--limit', type=int, default=100)
    for name in ('show', 'progress', 'events'):
        ts.add_parser(name).add_argument('task_id')
    actions = sub.add_parser('task').add_subparsers(dest='action', required=True)
    for action in ('create', 'propose', 'select', 'confirm', 'deliver', 'accept', 'request-changes',
                   'cancel', 'mail-config', 'manifest', 'mail-sent', 'mail-received'):
        a = actions.add_parser(action)
        if action != 'create':
            a.add_argument('task_id')
        a.add_argument('--file', required=action != 'cancel', help='JSON body file, or - for stdin')
        a.add_argument('--key', required=True, help='Stable idempotency key; reuse with identical body on retry')
    return p


def task_id(value):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value):
        raise ClientError('invalid_input', 'Invalid task identifier.')
    return value


def execute(args):
    if args.command == 'register':
        from .onboarding import execute as onboard, OnboardingError
        try:
            return onboard(args)
        except OnboardingError as error:
            raise ClientError('registration_input',str(error)) from None
    result = configure(args)
    if args.command == 'config':
        return result
    if args.command=='openclaw':
        from .openclaw import inspect_profile,probe,OpenClawError
        from .host import HostError
        profile=load_json(args.profile)
        try:
            return inspect_profile(profile) if args.operation=='inspect' else probe(profile)
        except HostError as error:
            raise ClientError('openclaw_'+error.code,'OpenClaw execution did not complete; no market or mail operation was requested.',7) from None
        except OpenClawError as error:
            raise ClientError('openclaw_validation_failed',str(error),7) from None
    if args.command in ('run', 'watch', 'discover', 'resume', 'status', 'stop', 'work'):
        from .runner import Runner
        runner = Runner(args.state)
        if args.command=='discover' or (args.command not in ('run','watch') and runner.state().get('mode')=='discover'):
            from .discovery import Discovery
            runner=Discovery(args.state)
        if args.command in ('run', 'watch', 'discover'):
            runner.initialize(load_json(args.policy), args.command)
        if args.command in ('run', 'watch', 'discover', 'resume'):
            value = runner.resume() if args.command=='resume' else runner.run()
            if value['status'] in ('blocked', 'timed_out'):
                code = value['error'] or value['status']
                status = 3 if code in ('credentials_missing','authentication_failed','identity_mismatch') else 4 if code=='conflict' else 6 if code=='network_error' else 7
                raise ClientError(code, 'Runner stopped; inspect its private checkpoint with status before resuming.', status)
            return value
        if args.command == 'work':
            return runner.work() if args.operation=='show' else runner.acknowledge(args.id, args.outcome)
        return runner.status() if args.command=='status' else runner.stop()
    if args.command == 'doctor':
        service = health()
        if not service.get('ok'):
            raise ClientError('service_unhealthy', 'Health endpoint did not report ok.', 5)
        me = request('GET', '/me')
        version = service.get('version', 'unknown')
        return dict(ok=bool(service.get('ok')), client_version=__version__,
            server_version=version, compatibility='alpha4_features_available' if version == __version__ else 'version_differs; verify feature compatibility',
            identity=dict(id=me['id'], name=me['name'], capabilities=me['capabilities']),
            mail_authorization='not_checked; separate local authorization required',
            runtime='one_shot; no_watch_or_wakeup', next_step='tasks list or services list')
    if args.command == 'identity':
        return request('GET', '/me')
    if args.command == 'services':
        return request('GET', '/agents?' + urlencode({'category': args.category}))
    if args.command == 'tasks':
        if args.operation == 'list':
            if not 1 <= args.limit <= 100:
                raise ClientError('invalid_input', 'Limit must be 1..100.')
            q = dict(page='true', scope='mine' if args.mine else 'open', category=args.category, limit=args.limit)
            if args.before:
                q['before'] = args.before
            value = request('GET', '/tasks?' + urlencode(q))
            if not isinstance(value, dict):
                raise ClientError('server_upgrade_required', 'Paged tasks require server alpha.4 or later; legacy API/Skill remains available.', 5)
            return value
        path = '/tasks/' + task_id(args.task_id)
        if args.operation != 'show':
            path += '/' + args.operation
        return request('GET', path)
    if not args.key or len(args.key) > 200 or any(ord(c) < 33 or ord(c) > 126 for c in args.key):
        raise ClientError('invalid_input', 'Key must contain 1..200 printable ASCII characters without spaces.')
    body = load_json(args.file) if args.file else {}
    endpoint = {'propose': 'proposals', 'request-changes': 'request_changes', 'manifest': 'mail-manifests'}.get(args.action, args.action)
    path = '/tasks' if args.action == 'create' else '/tasks/' + task_id(args.task_id) + '/' + endpoint
    return request('POST', path, body, args.key)


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        result = execute(args)
        print(json.dumps(dict(ok=True, data=result), ensure_ascii=False))
        return 0
    except ClientError as e:
        code, message, status = e.code, e.message, e.exit_code
    except MissingCredential:
        code, message, status = 'credentials_missing', 'Configure an existing private credential file or environment credential.', 3
    except HTTPError as e:
        code, status = ('authentication_failed', 3) if e.code in (401, 403) else ('conflict', 4) if e.code == 409 else ('server_upgrade_required', 5) if e.code == 404 and getattr(args, 'operation', '') == 'progress' else ('http_error', 5)
        message = 'Request rejected (HTTP ' + str(e.code) + '); re-read current state and check authorization/configuration.'
        e.close()
    except (URLError, TimeoutError, ConnectionError):
        code, message, status = 'network_error', 'Network or TLS request failed; no automatic retry was made.', 6
    except (OSError, ValueError, TypeError, KeyError):
        code, message, status = 'invalid_config_or_input', 'Check private configuration and JSON input. Details suppressed to protect credentials.', 2
    print(json.dumps(dict(ok=False, error=dict(code=code, message=message)), ensure_ascii=False), file=sys.stderr)
    return status


if __name__ == '__main__':
    sys.exit(main())
