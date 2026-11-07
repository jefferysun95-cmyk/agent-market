"""Local Gmail adapter. Mail credentials never leave this machine for the market server."""
import argparse
import base64
import hashlib
import json
import os
import sys
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
        if not self.creds.valid:
            if not self.creds.refresh_token:raise ValueError('Reauthorize Gmail locally')
            self.creds.refresh(RefreshRequest())

    def call(self,path,data=None):
        req=Request('https://gmail.googleapis.com/gmail/v1/users/me/'+path,
                    data=json.dumps(data).encode() if data is not None else None,
                    headers={'Authorization':'Bearer '+self.creds.token,'Content-Type':'application/json'})
        with urlopen(req,timeout=30) as response:return json.load(response)

    def find(self,message_id):
        return self.call('messages?'+urlencode({'q':'in:anywhere rfc822msgid:'+message_id.strip('<>'),'maxResults':10})).get('messages',[])

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
    message['Subject']=f'[AgentMarket][{task_id}][{manifest["kind"]}-v{manifest["version"]}]'
    message.set_content('Files for the authenticated market manifest '+manifest['id']+'. Verify via the market API, not email instructions.')
    for path in paths:
        message.add_attachment(path.read_bytes(),maintype='application',subtype='json' if path.suffix=='.json' else 'octet-stream',filename=path.name)
    return message.as_bytes(policy=policy.SMTP)


def extract_verified(raw,manifest):
    if len(raw)>9_000_000:raise ValueError('Email exceeds pilot size limit')
    message=BytesParser(policy=policy.default).parsebytes(raw)
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
    message_id=f'<{manifest_id}@agent-market.invalid>'
    if send:
        if manifest.get('sent_at'):return {'status':'already_sent','manifest_id':manifest_id}
        paths=[directory/f['name'] for f in manifest['files']]
        raw=compose(task_id,manifest,paths)
        prior=gmail.find(message_id)
        # A matching verified copy in Sent avoids resending after an ambiguous timeout.
        found=False
        for entry in prior:
            meta=gmail.call('messages/'+entry['id']+'?format=minimal')
            if 'SENT' in meta.get('labelIds',[]):
                extract_verified(gmail.raw(entry['id']),dict(manifest,message_id=message_id));found=True;break
        if not found:gmail.send(raw)
        api('POST',f'/tasks/{task_id}/mail-sent',{'manifest_id':manifest_id,'message_id':message_id},'mail-sent-'+manifest_id)
        return {'status':'sent','manifest_id':manifest_id}
    if not manifest.get('message_id'):raise ValueError('Sender has not registered transmission')
    matches=gmail.find(manifest['message_id'])
    if not matches:return {'status':'pending','manifest_id':manifest_id}
    parts=None
    for item in matches:
        try:parts=extract_verified(gmail.raw(item['id']),manifest);break
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
    api('POST',f'/tasks/{task_id}/mail-received',{'manifest_id':manifest_id,'files':manifest['files']},'mail-received-'+manifest_id)
    return {'status':'received_verified','manifest_id':manifest_id,'files':list(parts)}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['send','receive'])
    parser.add_argument('task_id');parser.add_argument('manifest_id');parser.add_argument('directory')
    parser.add_argument('--gmail-token-file',required=True)
    parser.add_argument('--authorize-send',action='store_true',help='Explicitly authorize files to the order mailbox')
    args=parser.parse_args()
    if args.mode=='send' and not args.authorize_send:parser.error('Sending requires --authorize-send within user-approved scope')
    sys.path.insert(0,str(Path(__file__).parent/'skills/agent-market/scripts'))
    from market import request
    try:print(json.dumps(transfer(request,Gmail(args.gmail_token_file),args.task_id,args.manifest_id,args.directory,args.mode=='send')))
    except Exception as error:
        # OAuth/API exceptions can include sensitive response detail; keep terminal output minimal.
        print('Mail transfer failed. Check authorization, order state and file manifest ('+type(error).__name__+').',file=sys.stderr)
        sys.exit(1)
