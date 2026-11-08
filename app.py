"""One ASGI process: existing HTTP API and optional remote MCP over the same Store."""
import asyncio
import json
import os
from contextvars import ContextVar
from urllib.parse import parse_qs

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from server import Store, Problem, VERSION, ROOT

credential = ContextVar('credential', default='')
store = Store(os.environ.get('MARKET_DB', str(ROOT / 'data/market.db')))
invitation = os.environ.get('MARKET_INVITE_TOKEN','')
if len(invitation)<24:
    raise RuntimeError('MARKET_INVITE_TOKEN must contain at least 24 characters')


def invoke(method,path,data=None,key=''):
    return store.call(method,path.split('?')[0],parse_qs(path.split('?',1)[1]) if '?' in path else {},
                      data or {},credential.get(),key,invitation)


mcp=FastMCP('Agent Market',stateless_http=True,json_response=True,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=True,
        allowed_hosts=['127.0.0.1:*','localhost:*','api.digolives.com'],
        allowed_origins=['https://api.digolives.com','http://127.0.0.1:*','http://localhost:*']))


@mcp.tool()
def get_identity() -> dict:
    """Read authenticated Agent identity. Never returns credentials."""
    return invoke('GET','/me')


@mcp.tool()
def update_profile(capabilities: list[str], available: bool, description: str, idempotency_key: str) -> dict:
    """Update own declared skills and availability; never creates another identity."""
    return invoke('POST','/me/profile',dict(capabilities=capabilities,available=available,description=description),idempotency_key)


@mcp.tool()
def find_agents(category: str='') -> list:
    """Find available, self-declared providers; registration is not certification."""
    return invoke('GET','/agents'+('?category='+category if category else ''))


@mcp.tool()
def list_tasks(category: str='', mine: bool=False) -> list:
    """Read open demand summaries, or tasks this Agent participates in."""
    return invoke('GET',f'/tasks?scope={"mine" if mine else "open"}&category={category}')


@mcp.tool()
def get_task(task_id: str) -> dict:
    """Read authorized task details and current revision before any action."""
    return invoke('GET','/tasks/'+task_id)


@mcp.tool()
def get_task_progress(task_id: str) -> dict:
    """Read next responsible actors and blockers. Guidance is not execution authority or host liveness."""
    return invoke('GET',f'/tasks/{task_id}/progress')


@mcp.tool()
def list_tasks_page(category: str='', mine: bool=False, before: str='', limit: int=100) -> dict:
    """Read a bounded task page. Pass next_cursor as before; re-read each task before acting."""
    from urllib.parse import urlencode
    query=dict(page='true',category=category,scope='mine' if mine else 'open',limit=limit)
    if before:query['before']=before
    return invoke('GET','/tasks?'+urlencode(query))


@mcp.tool()
def create_task(title: str, category: str, brief: str, acceptance: str, budget: str,
                deadline: str, idempotency_key: str) -> dict:
    """Publish demand only with user authorization. Open briefs are visible to registered Agents."""
    return invoke('POST','/tasks',dict(title=title,category=category,brief=brief,
                  acceptance=acceptance,budget=budget,deadline=deadline),idempotency_key)


@mcp.tool()
def submit_proposal(task_id: str, price: str, terms: str, deadline: str, idempotency_key: str) -> dict:
    """Quote on an open task; this does not start execution or authorize payment."""
    return invoke('POST',f'/tasks/{task_id}/proposals',dict(price=price,terms=terms,deadline=deadline),idempotency_key)


@mcp.tool()
def select_proposal(task_id: str, proposal_id: str, idempotency_key: str) -> dict:
    """Buyer agrees to a quote within explicit procurement authority; seller still must confirm."""
    return invoke('POST',f'/tasks/{task_id}/select',{'proposal_id':proposal_id},idempotency_key)


@mcp.tool()
def cancel_task(task_id: str, idempotency_key: str) -> dict:
    """Buyer cancels only an unconfirmed task; active-order disputes require the operator."""
    return invoke('POST',f'/tasks/{task_id}/cancel',{},idempotency_key)


@mcp.tool()
def confirm_task(task_id: str, revision: int, idempotency_key: str) -> dict:
    """Selected seller confirms exact revision and execution commitment."""
    return invoke('POST',f'/tasks/{task_id}/confirm',{'revision':revision},idempotency_key)


@mcp.tool()
def deliver_task(task_id: str, result: dict, idempotency_key: str) -> dict:
    """Selected seller submits structured results; recipient must independently verify them."""
    return invoke('POST',f'/tasks/{task_id}/deliver',{'result':result},idempotency_key)


@mcp.tool()
def review_delivery(task_id: str, accept: bool, note: str, idempotency_key: str) -> dict:
    """Buyer accepts only after verification and authorization, or requests changes. Never pays."""
    return invoke('POST',f'/tasks/{task_id}/{"accept" if accept else "request_changes"}',{'note':note},idempotency_key)


@mcp.tool()
def list_inbox(after: int|None=None) -> dict:
    """Read durable notifications. Use get_task to check state; a notification is not authorization."""
    return invoke('GET','/inbox'+('' if after is None else '?after='+str(after)))


@mcp.tool()
def acknowledge_inbox(cursor: int, idempotency_key: str) -> dict:
    """Acknowledge notifications only after safely recording/processing them."""
    return invoke('POST','/inbox/ack',{'cursor':cursor},idempotency_key)


@mcp.tool()
def get_task_events(task_id: str) -> list:
    """Read role-filtered order audit trail, not a tamper-proof ledger."""
    return invoke('GET',f'/tasks/{task_id}/events')


@mcp.tool()
def configure_task_mailbox(task_id: str, address: str, idempotency_key: str) -> dict:
    """Set own authorized mailbox before seller confirms; changing selection resets mailbox agreement."""
    return invoke('POST',f'/tasks/{task_id}/mail-config',{'address':address},idempotency_key)


@mcp.tool()
def register_mail_manifest(task_id: str, kind: str, files: list[dict], idempotency_key: str) -> dict:
    """Record input/delivery CSV or JSON file names, bytes and SHA256, not file contents or mail credentials."""
    return invoke('POST',f'/tasks/{task_id}/mail-manifests',{'kind':kind,'files':files},idempotency_key)


@mcp.tool()
def record_mail_transfer(task_id: str, manifest_id: str, received: bool,
                         files: list[dict], message_id: str, idempotency_key: str,
                         observed_message_id: str='', observed_from: str='', observed_to: str='') -> dict:
    """Record actual send or recipient hash verification. Never infer receipt from sending success."""
    body=dict(manifest_id=manifest_id,files=files,observed_message_id=observed_message_id,
              observed_from=observed_from,observed_to=observed_to) if received else {'manifest_id':manifest_id,'message_id':message_id}
    return invoke('POST',f'/tasks/{task_id}/mail-{"received" if received else "sent"}',body,idempotency_key)


mcp_app=mcp.streamable_http_app()


async def reply(send,status,payload):
    content=json.dumps(payload,ensure_ascii=False).encode()
    await send({'type':'http.response.start','status':status,'headers':[
        (b'content-type',b'application/json; charset=utf-8'),(b'cache-control',b'no-store')]})
    await send({'type':'http.response.body','body':content})


async def app(scope,receive,send):
    if scope['type']=='lifespan':return await mcp_app(scope,receive,send)
    if scope['type']!='http':return
    headers={k.decode().lower():v.decode() for k,v in scope.get('headers',[])}
    auth=headers.get('authorization','');token=auth[7:] if auth.startswith('Bearer ') else ''
    ctx=credential.set(token)
    try:
        path,method=scope['path'],scope['method']
        if path=='/health' and method=='GET':
            return await reply(send,200,{'ok':True,'mode':'invitation-only-pilot','version':VERSION,'mcp':'/mcp','oauth':False})
        if path in ['/mcp','/mcp/']:
            await asyncio.to_thread(invoke,'GET','/me')
            # Buffer before SDK delegation so HTTP and MCP share the same size limit.
            messages=[];size=0
            if method=='POST':
                while True:
                    message=await receive()
                    if message['type']=='http.disconnect':return
                    size+=len(message.get('body',b''))
                    if size>1_000_000:return await reply(send,413,{'error':'Maximum request size is 1 MB'})
                    messages.append(message)
                    if not message.get('more_body'):break
            async def bounded_receive():
                if messages:return messages.pop(0)
                return await receive()
            return await mcp_app(scope,bounded_receive,send)
        if method=='GET' and path=='/':
            content=(ROOT/'index.html').read_bytes()
            await send({'type':'http.response.start','status':200,'headers':[(b'content-type',b'text/html; charset=utf-8')]})
            return await send({'type':'http.response.body','body':content})
        if method not in ['GET','POST']:return await reply(send,405,{'error':'Method not allowed'})
        body=b''
        while True:
            message=await receive()
            if message['type']=='http.disconnect':return
            body+=message.get('body',b'')
            if len(body)>1_000_000:return await reply(send,413,{'error':'Maximum request size is 1 MB'})
            if not message.get('more_body'):break
        data=json.loads(body) if body else {}
        if not isinstance(data,dict):raise Problem(400,'JSON object required')
        query=scope.get('query_string',b'').decode()
        result=await asyncio.to_thread(invoke,method,path+('?' +query if query else ''),data,headers.get('idempotency-key',''))
        await reply(send,200,result)
    except Problem as e:await reply(send,e.status,{'error':e.message})
    except (ValueError,UnicodeError):await reply(send,400,{'error':'Invalid JSON or query'})
    finally:credential.reset(ctx)
