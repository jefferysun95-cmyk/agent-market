"""Real localhost SDK integration. No live credentials or external accounts."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

HAS_MCP=all(importlib.util.find_spec(name) for name in ['mcp','httpx','uvicorn'])


@unittest.skipUnless(HAS_MCP,'Install requirements.txt for MCP integration')
class MCPTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import httpx
        cls.temp=tempfile.TemporaryDirectory()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        cls.url=f'http://127.0.0.1:{port}'
        cls.invite='synthetic-test-invitation-only-123456'
        env=dict(os.environ,MARKET_DB=str(Path(cls.temp.name)/'test.db'),MARKET_INVITE_TOKEN=cls.invite)
        cls.proc=subprocess.Popen([sys.executable,'-m','uvicorn','app:app','--host','127.0.0.1','--port',str(port),'--no-access-log'],
            cwd=Path(__file__).parents[1],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                if httpx.get(cls.url+'/health',timeout=1).status_code==200:break
            except httpx.HTTPError:pass
            if cls.proc.poll() is not None:raise RuntimeError('ASGI server exited during startup')
            time.sleep(.1)
        else:raise RuntimeError('ASGI startup timed out')
        cls.tokens=[]
        for name in ['buyer','seller']:
            response=httpx.post(cls.url+'/agents',json={'name':name,'provider':'synthetic'},headers={
                'Authorization':'Bearer '+cls.invite,'Idempotency-Key':'register-'+name})
            response.raise_for_status();cls.tokens.append(response.json()['token'])

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate();cls.proc.wait(timeout=10);cls.temp.cleanup()

    def test_sdk_initialization_identity_isolation_and_shared_http(self):
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client
        import httpx
        async def scenario(token,name):
            async with httpx.AsyncClient(headers={'Authorization':'Bearer '+token}) as client, streamable_http_client(self.url+'/mcp',http_client=client) as (read,write,_):
                async with ClientSession(read,write) as session:
                    await session.initialize()
                    tool_names={t.name for t in (await session.list_tools()).tools}
                    self.assertIn('create_task',tool_names);self.assertIn('list_inbox',tool_names)
                    self.assertNotIn('register_agent',tool_names)
                    result=await session.call_tool('get_identity',{})
                    self.assertFalse(result.isError)
                    identity=json.loads(result.content[0].text)
                    self.assertEqual(name,identity['name'])
                    self.assertNotIn('token',identity)
                    if name=='buyer':
                        result=await session.call_tool('create_task',dict(title='SDK synthetic task',category='data-cleaning',brief='public synthetic rows',acceptance='unique IDs',budget='CNY 0',deadline='2030-01-01',idempotency_key='sdk-create'))
                        self.assertFalse(result.isError)
                        task=json.loads(result.content[0].text)
                        response=await asyncio.to_thread(httpx.get,self.url+'/tasks/'+task['id'],headers={'Authorization':'Bearer '+token})
                        self.assertEqual('SDK synthetic task',response.json()['title'])
        async def run():await asyncio.gather(*(scenario(t,n) for t,n in zip(self.tokens,['buyer','seller'])))
        asyncio.run(run())

    def test_auth_and_body_limits(self):
        import httpx
        self.assertEqual(401,httpx.post(self.url+'/mcp',json={}).status_code)
        self.assertEqual(401,httpx.get(self.url+'/me').status_code)
        headers={'Authorization':'Bearer '+self.tokens[0]}
        self.assertEqual(413,httpx.post(self.url+'/mcp',headers=headers,content=b'x'*1000001).status_code)
        self.assertEqual(413,httpx.post(self.url+'/tasks',headers=headers,content=b'x'*1000001).status_code)
        self.assertEqual(400,httpx.post(self.url+'/tasks',headers=headers,json=[]).status_code)
