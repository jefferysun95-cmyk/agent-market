"""Package-owned mail handler; emits only the bounded host protocol."""
import json
from pathlib import Path
import sys
from urllib.error import HTTPError,URLError

# The trusted supervisor invokes this file by absolute path from any cwd.
if __package__ is None:
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from agent_market.mail_bridge import Gmail,transfer,SendUncertain
from agent_market.market import request


def perform(work,api=request,gmail_factory=Gmail):
    context=work['mail']
    current=api('GET','/tasks/'+context['task_id'])
    if current['revision']!=context['revision']:return 'mail_validation_failed'
    try:
        gmail=gmail_factory(context['credentials_file'])
        result=transfer(api,gmail,context['task_id'],context['manifest_id'],context['directory'],context['send'])
        return 'pending' if result['status']=='pending' else 'completed'
    except ImportError:return 'mail_dependencies_missing'
    except SendUncertain:return 'send_uncertain'
    except (TimeoutError,ConnectionError,URLError):
        return 'send_uncertain' if context['send'] else 'mail_service_failed'
    except HTTPError as error:
        code='mail_auth_failed' if error.code in (401,403) else 'mail_service_failed'
        error.close();return code
    except Exception as error:
        # Class name is inspected locally; provider messages are never emitted.
        if type(error).__name__ in ('RefreshError','DefaultCredentialsError'):return 'mail_auth_failed'
        return 'mail_validation_failed'


if __name__=='__main__':
    work=None
    try:
        work=json.load(sys.stdin)
        outcome=perform(work)
    except Exception:outcome='mail_service_failed'
    if work is None:sys.exit(2)
    print(json.dumps(dict(schema_version=1,work_id=work['work_id'],outcome=outcome)))
