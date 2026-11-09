"""Small JSON API client. Secrets are read from environment, never CLI arguments."""
import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
from urllib.parse import urlparse


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward a bearer header to a redirect destination.
        return None


class MissingCredential(ValueError):
    pass


def validate_base(base):
    if not isinstance(base, str):raise ValueError('Invalid service URL')
    base = base.rstrip('/')
    url = urlparse(base)
    if not url.hostname or url.username or url.password or url.query or url.fragment or url.path:
        raise ValueError('Use a service origin without credentials, query or path')
    if url.scheme != 'https' and not (url.scheme == 'http' and url.hostname in ['127.0.0.1', 'localhost', '::1']):
        raise ValueError('Use HTTPS for remote servers')
    return base


def health():
    base = validate_base(os.environ.get('MARKET_URL', 'http://127.0.0.1:8787'))
    with build_opener(NoRedirect).open(Request(base + '/health'), timeout=30) as response:
        return json.load(response)


def request(method, path, data=None, key=None, invite=False, timeout=30):
    base = validate_base(os.environ.get('MARKET_URL', 'http://127.0.0.1:8787'))
    if not path.startswith('/') or path.startswith('//') or '#' in path or '\\' in path:
        raise ValueError('API path must start with one /')
    secret = os.environ.get('MARKET_INVITE_TOKEN' if invite else 'MARKET_TOKEN', '')
    credential_file=os.environ.get('MARKET_CREDENTIALS_FILE','')
    if not invite and not secret and credential_file:
        with open(credential_file,encoding='utf-8-sig') as f:secret=json.load(f).get('token','')
    if not secret:raise MissingCredential('Personal credential missing; set MARKET_CREDENTIALS_FILE or MARKET_TOKEN')
    headers = {'Authorization': 'Bearer ' + secret, 'Content-Type': 'application/json'}
    if method == 'POST':
        headers['Idempotency-Key'] = key or uuid.uuid4().hex
    req = Request(base + path, data=json.dumps(data).encode() if data is not None else None,
                  headers=headers, method=method)
    with build_opener(NoRedirect).open(req, timeout=timeout) as response:
        return json.load(response)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('method', choices=['GET', 'POST'])
    p.add_argument('path')
    p.add_argument('--file', help='JSON request file')
    p.add_argument('--key', help='Reuse the same key when retrying the exact same mutation')
    p.add_argument('--invite', action='store_true', help='Register using invitation credential')
    p.add_argument('--doctor', action='store_true', help='Read-only identity/connection check; does not show token')
    args = p.parse_args()
    try:
        payload = None
        if args.file:
            with open(args.file, encoding='utf-8-sig') as f:
                payload = json.load(f)
        if args.doctor:
            identity=request('GET','/me')
            print(json.dumps({'ok':True,'name':identity['name'],'capabilities':identity['capabilities']},ensure_ascii=False))
        else:print(json.dumps(request(args.method, args.path, payload, args.key, args.invite), ensure_ascii=False, indent=2))
    except HTTPError as e:
        print(e.read().decode(), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # Header/URL exceptions can contain credential bytes; never echo them.
        print('Client request failed ('+type(e).__name__+'). Check connection and private configuration.', file=sys.stderr)
        sys.exit(1)
