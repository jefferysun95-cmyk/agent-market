"""Explicit local OpenClaw adapter. Never dispatches a market mutation."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
import uuid

from .host import HostError,run_host_process


class OpenClawError(ValueError):
    pass


def validate_profile(profile):
    required={'schema_version','mode','runtime','entry','agent_id','workspace','timeout_seconds','dedicated_agent'}
    if not isinstance(profile,dict) or not required<=set(profile) or set(profile)-required-{'startup_grace_seconds'}:
        raise OpenClawError('Invalid OpenClaw profile fields.')
    if type(profile['schema_version']) is not int or profile['schema_version']!=1 or profile['mode']!='local':
        raise OpenClawError('Only explicit local mode profile v1 is supported.')
    for field in ('runtime','entry','workspace'):
        if not isinstance(profile[field],str) or not Path(profile[field]).is_absolute():
            raise OpenClawError('OpenClaw paths must be absolute.')
    if Path(profile['runtime']).suffix.lower() in ('.cmd','.bat','.ps1','.sh') or Path(profile['entry']).suffix.lower() not in ('.js','.mjs','.cjs'):
        raise OpenClawError('Use a native runtime and the installed OpenClaw JS entry, never a shell wrapper.')
    if not isinstance(profile['agent_id'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',profile['agent_id']):
        raise OpenClawError('Invalid OpenClaw internal agent ID.')
    if profile['dedicated_agent'] is not True or profile['agent_id'].lower() in ('main','default'):
        raise OpenClawError('A dedicated non-default OpenClaw agent is required; session-id alone does not isolate the main session.')
    if type(profile['timeout_seconds']) is not int or not 10<=profile['timeout_seconds']<=180:
        raise OpenClawError('OpenClaw timeout must be 10..180 seconds.')
    grace=profile.get('startup_grace_seconds',20)
    if type(grace) is not int or not 0<=grace<=120:
        raise OpenClawError('OpenClaw startup grace must be 0..120 seconds; total is at most 300.')
    return profile


def inspect_profile(profile):
    validate_profile(profile)
    missing=[k for k in ('runtime','entry') if not Path(profile[k]).is_file()]
    if not Path(profile['workspace']).is_dir():missing.append('workspace')
    return dict(profile_valid=True,mode='local',agent_id=profile['agent_id'],dedicated_agent_declared=True,paths_ready=not missing,
        missing=missing,model_probe='not_run',market_access='not_requested',mail_access='not_requested')


def parse_envelope(raw):
    """2026.4 CLI envelope: payloads + meta. Ignore only preceding log lines.

    Accept exactly one complete terminal envelope; never extract arbitrary model
    JSON from logs, and never use model text as provider/error metadata.
    """
    try:text=raw.decode('utf-8')
    except UnicodeError:raise OpenClawError('OpenClaw output is not UTF-8.') from None
    candidates=[]
    for match in re.finditer(r'(?m)^\{',text):
        try:value,end=json.JSONDecoder().raw_decode(text[match.start():])
        except ValueError:continue
        if text[match.start()+end:].strip():continue
        if isinstance(value,dict) and set(value)<= {'payloads','meta','delivery'} and {'payloads','meta'}<=set(value):
            candidates.append(value)
    if len(candidates)!=1:raise OpenClawError('Unsupported or ambiguous OpenClaw output envelope.')
    envelope=candidates[0]
    if envelope.get('delivery') or not isinstance(envelope['payloads'],list) or not isinstance(envelope['meta'],dict):
        raise OpenClawError('Unexpected delivery or malformed OpenClaw response.')
    meta=envelope['meta']
    if meta.get('aborted') is True or meta.get('stopReason') in ('error','aborted','timeout'):
        raise OpenClawError('OpenClaw did not complete the model turn.')
    agent=meta.get('agentMeta')
    if not isinstance(agent,dict) or any(not isinstance(agent.get(k),str) or not agent[k] for k in ('provider','model')):
        raise OpenClawError('OpenClaw provider/model metadata missing; cannot claim a model probe.')
    texts=[p.get('text') for p in envelope['payloads'] if isinstance(p,dict) and isinstance(p.get('text'),str) and p['text'].strip()]
    if len(texts)!=1 or any(not isinstance(p,dict) or p.get('isError') or p.get('mediaUrl') or p.get('mediaUrls') for p in envelope['payloads']):
        raise OpenClawError('Expected exactly one text-only model result.')
    return texts[0].strip(),agent,meta


def parse_model_json(text):
    if text.startswith('```json\n') and text.endswith('\n```'):text=text[8:-4]
    def reject_constant(value):raise ValueError('Non-finite JSON')
    def unique(pairs):
        out={}
        for key,value in pairs:
            if key in out:raise ValueError('Duplicate JSON key')
            out[key]=value
        return out
    try:value=json.loads(text,parse_constant=reject_constant,object_pairs_hook=unique)
    except ValueError:raise OpenClawError('Model result must be one strict JSON object.') from None
    if not isinstance(value,dict):raise OpenClawError('Model result must be an object.')
    return value


def execute_json(profile,work_id,prompt,should_stop=lambda:False,deadline=None):
    report=inspect_profile(profile)
    if not report['paths_ready']:raise OpenClawError('OpenClaw profile paths are unavailable.')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',work_id):raise OpenClawError('Invalid work identifier.')
    session=str(uuid.uuid5(uuid.NAMESPACE_URL,'agent-market:'+profile['agent_id']+':'+work_id))
    argv=[profile['runtime'],profile['entry'],'agent','--local','--agent',profile['agent_id'],
        '--session-id',session,'--json','--timeout',str(profile['timeout_seconds']),'--message',prompt]
    # Existing model provider authorization remains under OpenClaw's control.
    # Do not pass market/Gmail credentials or operator invitation through env.
    env={k:v for k,v in os.environ.items() if not k.startswith(('MARKET_','GMAIL_','IMAP_','SMTP_'))}
    started=time.monotonic()
    raw=run_host_process(dict(argv=argv,cwd=profile['workspace'],timeout_seconds=profile['timeout_seconds']+profile.get('startup_grace_seconds',20)),
        {},should_stop,deadline,env=env,stdin_null=True)
    text,agent,meta=parse_envelope(raw)
    if agent.get('sessionId') and agent['sessionId']!=session:
        raise OpenClawError('OpenClaw session binding differs.')
    result=parse_model_json(text)
    proof=dict(mode='local',session_id=session,provider=agent['provider'],model=agent['model'],
        model_budget_seconds=profile['timeout_seconds'],outer_budget_seconds=profile['timeout_seconds']+profile.get('startup_grace_seconds',20),
        adapter_elapsed_seconds=round(time.monotonic()-started,3),
        observed_at=datetime.now(timezone.utc).isoformat(),envelope_sha256=hashlib.sha256(raw).hexdigest())
    if type(meta.get('durationMs')) in (int,float):proof['reported_duration_ms']=meta['durationMs']
    return result,proof


def probe(profile):
    work_id='probe_'+uuid.uuid4().hex
    nonce=uuid.uuid4().hex
    expected=dict(work_id=work_id,kind='readiness',nonce=nonce)
    prompt=('Agent Market read-only model readiness check. Do not call any tools, read files, access the network, '
        'send messages, edit memory or change any task. Reply with exactly the following JSON object and nothing else: '
        +json.dumps(expected,separators=(',',':')))
    result,proof=execute_json(profile,work_id,prompt)
    if result!=expected:raise OpenClawError('Model readiness nonce/work binding failed.')
    return dict(ready=True,model_probe='actual_openclaw_cli_turn',proof=proof,
        market_mutations='not_requested',mail_operations='not_requested',
        host_tools_independently_audited=False)
