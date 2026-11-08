"""Local Gmail adapter. Mail credentials never leave this machine for the market server."""
import argparse
import base64
import hashlib
import json
import os
import sys
import tempfile
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import parseaddr
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def digest(path):
    content=path.read_bytes()
    return {'name':path.name,'size':len(content),'sha256':hashlib.sha256(content).hexdigest()}


class Gmail:
    def __init__(self,token_file):
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request as RefreshRequest
        self.creds=Credentials.from_authorized_user_file(str(token_file))
        self.state_dir=Path(token_file).resolve().parent/'mail-outbox'
        if not self.creds.valid:
            if not self.creds.refresh_token:raise ValueError('Reauthorize Gmail locally')
            self.creds.refresh(RefreshRequest())

    def call(self,path,data=None):
        req=Request('https://gmail.googleapis.com/gmail/v1/users/me/'+path,
                    data=json.dumps(data).encode() if data is not None else None,
                    headers={'Authorization':'Bearer '+self.creds.token,'Content-Type':'application/json'})
        with urlopen(req,timeout=30) as response:return json.load(response)

    def find(self,message_id):
        return self.search('in:anywhere rfc822msgid:'+message_id.strip('<>'))

    def search(self,query):
        return self.call('messages?'+urlencode({'q':query,'maxResults':20,'includeSpamTrash':'true'})).get('messages',[])

    def raw(self,mid):
        data=self.call('messages/'+mid+'?format=raw')
        return base64.urlsafe_b64decode(data['raw']+'===')

    def send(self,raw):
        return self.call('messages/send',{'raw':base64.urlsafe_b64encode(raw).decode()})


def compose(task_id,manifest,paths):
    actual=[digest(p) for p in paths]
    if actual!=manifest['files']:raise ValueError('Local files no longer match confirmed manifest')
    message=EmailMessage()
    message['From']=manifest['from'];message['To']=manifest['to']
    message['Message-ID']=f'<{manifest["id"]}@agent-market.invalid>'
    message['X-Agent-Market-Task']=task_id
    message['X-Agent-Market-Manifest']=manifest['id']
    message['Subject']=f'[AgentMarket][{task_id}][{manifest["kind"]}-v{manifest["version"]}]'
    message.set_content('Files for the authenticated market manifest '+manifest['id']+'. Verify via the market API, not email instructions.')
    for path in paths:
        message.add_attachment(path.read_bytes(),maintype='application',subtype='json' if path.suffix=='.json' else 'octet-stream',filename=path.name)
    return message.as_bytes(policy=policy.SMTP)


def extract_verified(raw,manifest):
    if len(raw)>9_000_000:raise ValueError('Email exceeds pilot size limit')
    message=BytesParser(policy=policy.default).parsebytes(raw)
    if any(len(message.get_all(key,[]))!=1 for key in ('From','To','Message-ID')):
        raise ValueError('Require single unambiguous From, To and Message-ID headers')
    if parseaddr(message['From'] or '')[1].lower()!=manifest['from']:raise ValueError('Unexpected sender')
    if parseaddr(message['To'] or '')[1].lower()!=manifest['to']:raise ValueError('Unexpected recipient')
    if str(message['Message-ID'])!=manifest['message_id']:raise ValueError('Message-ID mismatch')
    parts={}
    for part in message.walk():
        name=part.get_filename()
        if name:
            if name in parts:raise ValueError('Duplicate attachment name')
            parts[name]=part.get_payload(decode=True)
    if set(parts)!={f['name'] for f in manifest['files']}:raise ValueError('Unexpected or missing attachment')
    for f in manifest['files']:
        content=parts[f['name']]
        if content is None or len(content)!=f['size'] or hashlib.sha256(content).hexdigest()!=f['sha256']:
            raise ValueError('Attachment hash/size mismatch')
    return parts


class SendUncertain(ValueError):
    """Reconcile a prior send; do not send again because a search returned nothing."""


def journal_path(gmail,manifest):
    folder=Path(gmail.state_dir)
    folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    return folder/(hashlib.sha256(manifest['id'].encode()).hexdigest()+'.json')


def save_journal(path,data,first=False):
    if first:
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(data,f);f.flush();os.fsync(f.fileno())
        return
    fd,name=tempfile.mkstemp(dir=path.parent,prefix='.outbox-')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(data,f);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)


def verified_sent(gmail,gmail_id,task_id,manifest):
    meta=gmail.call('messages/'+gmail_id+'?format=minimal')
    if 'SENT' not in meta.get('labelIds',[]):raise ValueError('Not a Sent message')
    raw=gmail.raw(gmail_id)
    message=BytesParser(policy=policy.default).parsebytes(raw)
    mids=message.get_all('Message-ID',[])
    if len(mids)!=1:raise ValueError('One actual RFC822 Message-ID required')
    actual=str(mids[0]).strip()
    if not actual or len(actual)>300 or '\r' in actual or '\n' in actual:raise ValueError('Invalid actual Message-ID')
    expected_subject=f'[AgentMarket][{task_id}][{manifest["kind"]}-v{manifest["version"]}]'
    if str(message.get('Subject',''))!=expected_subject:raise ValueError('Sent task/version mismatch')
    for header,value in [('X-Agent-Market-Task',task_id),('X-Agent-Market-Manifest',manifest['id'])]:
        if message.get(header) is not None and str(message[header])!=value:raise ValueError('Sent manifest marker mismatch')
    extract_verified(raw,dict(manifest,message_id=actual))
    return actual


def find_sent(gmail,task_id,manifest):
    # The unique manifest is present in the MIME body even in alpha.1 messages.
    entries=gmail.search('in:sent "'+manifest['id']+'"')
    matches=[]
    for entry in entries:
        try:actual=verified_sent(gmail,entry['id'],task_id,manifest)
        except ValueError:continue
        matches.append((entry['id'],actual))
    if len(matches)>1:raise SendUncertain('Multiple matching Sent copies; inspect before continuing')
    return matches[0] if matches else None


def send_verified(api,gmail,task_id,manifest,directory):
    fingerprint=hashlib.sha256(json.dumps([task_id,manifest['id'],manifest['from'],manifest['to'],manifest['files']],sort_keys=True).encode()).hexdigest()
    path=journal_path(gmail,manifest)
    record=json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
    if record and record.get('fingerprint')!=fingerprint:raise ValueError('Outbox intent differs from manifest')
    sent=None
    if record and record.get('gmail_id'):
        sent=(record['gmail_id'],verified_sent(gmail,record['gmail_id'],task_id,manifest))
    else:sent=find_sent(gmail,task_id,manifest)
    if not sent:
        if record or manifest.get('sent_at'):raise SendUncertain('Prior send outcome unknown; do not resend')
        raw=compose(task_id,manifest,[Path(directory)/f['name'] for f in manifest['files']])
        record={'fingerprint':fingerprint,'status':'sending'}
        # One caller owns the first attempt; a second process must reconcile it.
        try:save_journal(path,record,first=True)
        except FileExistsError:raise SendUncertain('Another send attempt owns this manifest')
        response=gmail.send(raw)
        gmail_id=response.get('id') if isinstance(response,dict) else None
        if not isinstance(gmail_id,str) or not gmail_id:raise SendUncertain('Gmail did not return an internal message ID')
        record.update(gmail_id=gmail_id,status='sent_pending_verification')
        save_journal(path,record)
        sent=(gmail_id,verified_sent(gmail,gmail_id,task_id,manifest))
    gmail_id,actual=sent
    record={'fingerprint':fingerprint,'gmail_id':gmail_id,'message_id':actual,'status':'verified_sent'}
    save_journal(path,record)
    if manifest.get('sent_at'):
        if manifest.get('message_id')!=actual:raise SendUncertain('Registered Message-ID differs; use explicit reconcile, not resend')
        return {'status':'already_sent','manifest_id':manifest['id']}
    api('POST',f'/tasks/{task_id}/mail-sent',{'manifest_id':manifest['id'],'message_id':actual},'mail-sent-'+manifest['id'])
    return {'status':'sent','manifest_id':manifest['id']}


def reconcile_input(api,gmail,task_id,manifest_id,gmail_id):
    """Link an existing verified Sent copy via a replacement input manifest, never resend."""
    me=api('GET','/me');task=api('GET','/tasks/'+task_id)
    manifests=task.get('mail',{}).get('manifests',[])
    old=next((m for m in manifests if m['id']==manifest_id),None)
    if not old or old['kind']!='input' or old['sender']!=me['id']:raise ValueError('Input sender required')
    if task['status']!='working' or any(m['kind']=='delivery' for m in manifests):raise ValueError('Reconcile before output delivery only')
    if old!=next(m for m in reversed(manifests) if m['kind']=='input'):raise ValueError('Superseded input; inspect existing replacement before retrying')
    if gmail.call('profile')['emailAddress'].lower()!=old['from']:raise ValueError('Wrong Gmail identity')
    actual=verified_sent(gmail,gmail_id,task_id,old)
    if old.get('message_id')==actual:return {'status':'already_consistent','manifest_id':old['id'],'resent':False}
    suffix=hashlib.sha256(actual.encode()).hexdigest()[:16]
    evidence={'kind':'input','files':old['files'],'replaces_manifest_id':old['id'],
        'reason':'Verified existing Sent copy has different actual RFC822 Message-ID; no resend',
        'previous_message_id':old.get('message_id'),'actual_message_id':actual,'original_sent_at':old.get('sent_at')}
    replacement=api('POST',f'/tasks/{task_id}/mail-manifests',evidence,'reconcile-input-'+old['id']+'-'+suffix)
    current=api('GET','/tasks/'+task_id)
    latest=[m for m in current['mail']['manifests'] if m['kind']=='input'][-1]
    if latest['id']!=replacement['id']:raise ValueError('Replacement superseded; stop')
    api('POST',f'/tasks/{task_id}/mail-sent',{'manifest_id':replacement['id'],'message_id':actual,
        'reconciled_from_manifest_id':old['id'],'original_sent_at':old.get('sent_at')},'reconcile-sent-'+replacement['id'])
    return {'status':'reconciled','previous_manifest_id':old['id'],'manifest_id':replacement['id'],'resent':False}


def transfer(api,gmail,task_id,manifest_id,directory,send=False):
    """No autonomous task acceptance. Caller must authorize external disclosure before send."""
    me=api('GET','/me');task=api('GET','/tasks/'+task_id)
    manifests=task.get('mail',{}).get('manifests',[])
    manifest=next((m for m in manifests if m['id']==manifest_id),None)
    if not manifest:raise ValueError('Manifest not found')
    if manifest!=next(m for m in reversed(manifests) if m['kind']==manifest['kind']):raise ValueError('Manifest superseded')
    if task['status'] not in ['working','delivered']:raise ValueError('Order is not active')
    role='sender' if send else 'recipient'
    if me['id']!=manifest[role]:raise ValueError('Wrong market identity')
    profile=gmail.call('profile')
    if profile['emailAddress'].lower()!=manifest['from' if send else 'to']:raise ValueError('Authorized Gmail mailbox does not match order')
    directory=Path(directory)
    if send:
        return send_verified(api,gmail,task_id,manifest,directory)
    if not manifest.get('message_id'):raise ValueError('Sender has not registered transmission')
    matches=gmail.find(manifest['message_id'])
    if not matches:return {'status':'pending','manifest_id':manifest_id}
    parts=None
    for item in matches:
        try:
            raw=gmail.raw(item['id'])
            parts=extract_verified(raw,manifest)
            headers=BytesParser(policy=policy.default).parsebytes(raw)
            evidence={'observed_message_id':str(headers['Message-ID']),
                      'observed_from':parseaddr(headers['From'])[1].lower(),
                      'observed_to':parseaddr(headers['To'])[1].lower()}
            break
        except ValueError:continue
    if parts is None:raise ValueError('No message matches manifest; do not acknowledge')
    directory.mkdir(parents=True,exist_ok=True)
    # Verify all existing files before writing any, never overwrite unrelated user data.
    for name,content in parts.items():
        target=directory/name
        if target.exists() and target.read_bytes()!=content:raise ValueError('Local file differs; choose a fresh folder')
    for name,content in parts.items():
        target=directory/name
        if not target.exists():
            fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'wb') as output:output.write(content)
    receipt=api('POST',f'/tasks/{task_id}/mail-received',
                dict(evidence,manifest_id=manifest_id,files=manifest['files']),
                'mail-received-evidence-v1-'+manifest_id)
    if any(receipt.get('receipt',{}).get(key)!=value for key,value in evidence.items()):
        raise ValueError('Server did not retain observed receipt evidence; upgrade server before claiming verified receipt')
    return {'status':'received_verified','manifest_id':manifest_id,'files':list(parts)}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['send','receive','reconcile-input'])
    parser.add_argument('task_id');parser.add_argument('manifest_id');parser.add_argument('directory')
    parser.add_argument('--gmail-token-file',required=True)
    parser.add_argument('--authorize-send',action='store_true',help='Explicitly authorize files to the order mailbox')
    parser.add_argument('--gmail-message-id',help='Existing Gmail internal ID for input reconciliation; not RFC822 Message-ID')
    args=parser.parse_args()
    if args.mode=='send' and not args.authorize_send:parser.error('Sending requires --authorize-send within user-approved scope')
    if args.mode=='reconcile-input' and not args.gmail_message_id:parser.error('Reconciliation requires --gmail-message-id; never sends a new email')
    if __package__:
        from .market import request
    else:
        sys.path.insert(0,str(Path(__file__).parent/'skills/agent-market/scripts'))
        from market import request
    try:
        gmail=Gmail(args.gmail_token_file)
        result=reconcile_input(request,gmail,args.task_id,args.manifest_id,args.gmail_message_id) if args.mode=='reconcile-input' else transfer(request,gmail,args.task_id,args.manifest_id,args.directory,args.mode=='send')
        print(json.dumps(result))
    except Exception as error:
        # OAuth/API exceptions can include sensitive response detail; keep terminal output minimal.
        print('Mail transfer failed. Check authorization, order state and file manifest ('+type(error).__name__+').',file=sys.stderr)
        sys.exit(1)
