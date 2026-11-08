"""One real-mail/local-HTTP signup check; owner enters OTP privately."""
import argparse
import json
import os
from pathlib import Path
import secrets
import sys
import threading
from types import SimpleNamespace
from http.server import ThreadingHTTPServer
from urllib.request import Request, build_opener

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_market.onboarding import private_path, save_private, create_private, execute
from agent_market.market import NoRedirect
from server import Store, CATEGORIES, handler
from registration import from_environment, email_address
from tools.configure_registration_mail import default_path


def run_check(config_path, directory, email, code_file=None):
    config_path, directory = private_path(config_path), private_path(directory)
    email = email_address(email)
    config = json.loads(config_path.read_text(encoding='utf-8'))
    allowed = {'MARKET_SELF_REGISTRATION', 'MARKET_MAIL_TRANSPORT', 'MARKET_MAIL_FROM',
               'MARKET_ZOHO_API_KEY', 'MARKET_ZOHO_API_URL', 'MARKET_REGISTRATION_SECRET'}
    if set(config) != allowed or any(not isinstance(v, str) for v in config.values()) or config['MARKET_MAIL_TRANSPORT'] != 'zoho_api':
        raise ValueError('Expected private API config')
    if directory.exists():
        raise ValueError('This test directory already exists; no automatic resend')
    if not code_file and not sys.stdin.isatty():
        raise ValueError('Interactive terminal required before sending')
    directory.mkdir(parents=True, mode=0o700)
    report_path = directory/'report.json'
    report = dict(status='prepared', production_changed=False, local_test_only=True,
                  mail_resent=False, code_displayed=False, token_displayed=False)
    save_private(report_path, report)
    db_path = directory/'test.db'; os.close(create_private(db_path))
    os.environ.update(config)
    service = from_environment(Store(db_path), CATEGORIES)
    base_handler = handler(service.store, secrets.token_urlsafe(32), service)
    class QuietHandler(base_handler):
        def log_message(self, *args): pass
    http = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
    thread = threading.Thread(target=http.serve_forever, daemon=True); thread.start()
    try:
        url = 'http://127.0.0.1:' + str(http.server_port)
        request_file, session, credentials = [directory/name for name in ('request.json','session.json','credentials.json')]
        save_private(request_file,dict(email=email,agent_key='alpha5-local-acceptance',name='Alpha5 local acceptance',
                                       provider='local-http-test',capabilities=['data-cleaning']))
        execute(SimpleNamespace(operation='start',url=url,file=str(request_file),session=str(session)))
        report.update(status='verification_required')
        save_private(report_path,report,replace=True)
        print('Check the recipient mailbox for the new code. Enter it at the hidden prompt; do not paste it into chat.',flush=True)
        execute(SimpleNamespace(operation='finish',session=str(session),credentials_file=str(credentials),code_file=code_file))
        saved = json.loads(credentials.read_text(encoding='utf-8'))
        with build_opener(NoRedirect).open(Request(url+'/me',headers={'Authorization':'Bearer '+saved['token']}),timeout=15) as response:
            identity=json.load(response)
        if identity.get('id') != saved['agent']['id']:
            raise ValueError('Identity mismatch')
        report.update(status='passed',registration_completed=True,identity_check=True,
                      credentials_saved=True,agent_id=identity['id'],mail_delivery='owner_entered_matching_code',
                      server_listener='loopback_only; closed_after_check')
        save_private(report_path,report,replace=True)
        return report
    except BaseException:
        report.update(status='stopped_without_retry')
        save_private(report_path,report,replace=True)
        raise
    finally:
        http.shutdown();http.server_close();thread.join(5)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default=str(default_path().with_name('registration-test-zoho-api.json')))
    parser.add_argument('--state',default=str(default_path().parent/'alpha5-live-registration-01'))
    parser.add_argument('--email',default='run7ai@gmail.com')
    parser.add_argument('--authorize-send',action='store_true',required=True)
    parser.add_argument('--code-file',help='Private input alternative; never put the code in argv')
    args=parser.parse_args(argv)
    try:
        result=run_check(args.config,args.state,args.email,args.code_file)
    except (Exception,KeyboardInterrupt):
        print(json.dumps(dict(status='stopped_without_retry',error='Live check did not complete; details suppressed. No automatic resend.')),file=sys.stderr)
        return 2
    print(json.dumps(result));return 0


if __name__=='__main__':sys.exit(main())
