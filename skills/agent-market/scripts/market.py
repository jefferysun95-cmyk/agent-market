"""Small JSON API client. Secrets are read from environment, never CLI arguments."""
import argparse
import json
import os
import sys
import uuid
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlparse


def request(method, path, data=None, key=None, invite=False):
    base = os.environ.get('MARKET_URL', 'http://127.0.0.1:8787').rstrip('/')
    url = urlparse(base)
    if url.scheme != 'https' and not (url.scheme == 'http' and url.hostname in ['127.0.0.1', 'localhost', '::1']):
        raise ValueError('Use HTTPS for remote servers')
    if not path.startswith('/') or path.startswith('//'):
        raise ValueError('API path must start with one /')
    secret = os.environ.get('MARKET_INVITE_TOKEN' if invite else 'MARKET_TOKEN', '')
    headers = {'Authorization': 'Bearer ' + secret, 'Content-Type': 'application/json'}
    if method == 'POST':
        headers['Idempotency-Key'] = key or uuid.uuid4().hex
    req = Request(base + path, data=json.dumps(data).encode() if data is not None else None,
                  headers=headers, method=method)
    with urlopen(req, timeout=30) as response:
        return json.load(response)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('method', choices=['GET', 'POST'])
    p.add_argument('path')
    p.add_argument('--file', help='JSON request file')
    p.add_argument('--key', help='Reuse the same key when retrying the exact same mutation')
    p.add_argument('--invite', action='store_true', help='Register using invitation credential')
    args = p.parse_args()
    try:
        payload = None
        if args.file:
            with open(args.file, encoding='utf-8-sig') as f:
                payload = json.load(f)
        print(json.dumps(request(args.method, args.path, payload, args.key, args.invite), ensure_ascii=False, indent=2))
    except HTTPError as e:
        print(e.read().decode(), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
