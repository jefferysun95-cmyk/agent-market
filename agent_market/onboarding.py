"""Harness-neutral registration client. Never print codes or issued credentials."""
import csv
import getpass
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
from urllib.request import Request, build_opener

from .market import NoRedirect, validate_base


class OnboardingError(ValueError):
    pass


def private_path(value):
    path = Path(value).expanduser().absolute()
    if path.is_symlink() or any((parent / '.git').exists() for parent in [path.parent, *path.parent.parents]):
        raise OnboardingError('Use a private file outside any Git checkout, without symlinks.')
    if any(parent.is_symlink() for parent in path.parents) or os.path.normcase(str(path.parent.resolve())) != os.path.normcase(str(path.parent)):
        raise OnboardingError('Private directory must not be a symlink.')
    return path


def create_private(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        if os.name == 'nt':
            options = dict(creationflags=subprocess.CREATE_NO_WINDOW)
            raw = subprocess.check_output(['whoami', '/user', '/fo', 'csv', '/nh'], timeout=10, **options).decode(errors='replace')
            sid = next((cell for row in csv.reader(raw.splitlines()) for cell in row if re.fullmatch(r'S-1-\d+(?:-\d+)+', cell)), None)
            if not sid:
                raise OnboardingError('Cannot establish current Windows identity for private ACL.')
            result = subprocess.run(['icacls', str(path), '/inheritance:r', '/grant:r', '*' + sid + ':(F)'], capture_output=True, timeout=10, **options)
            if result.returncode:
                raise OnboardingError('Cannot restrict private file permissions.')
        return fd
    except Exception as error:
        os.close(fd); path.unlink(missing_ok=True)
        if isinstance(error, subprocess.SubprocessError):
            raise OnboardingError('Private file permission setup did not complete.') from None
        raise


def save_private(path, value, replace=False):
    if not replace:
        fd = create_private(path)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False, indent=2); f.flush(); os.fsync(f.fileno())
        return
    # Candidate is permission-restricted before writing and replacement.
    temp = path.with_name('.registration-' + secrets.token_hex(12))
    try:
        save_private(temp, value)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def public_request(url, endpoint, body, key):
    request = Request(validate_base(url) + endpoint, json.dumps(body).encode(),
                      {'Content-Type': 'application/json', 'Idempotency-Key': key}, method='POST')
    # Never attach existing personal/operator credentials to public onboarding.
    with build_opener(NoRedirect).open(request, timeout=30) as response:
        raw = response.read(65537)
    if len(raw) > 65536:
        raise OnboardingError('Registration response too large.')
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise OnboardingError('Invalid registration response.')
    return result


def execute(args):
    session_path = private_path(args.session)
    if args.operation == 'start':
        url = validate_base(args.url)
        body = json.loads(Path(args.file).expanduser().read_text(encoding='utf-8-sig'))
        if not isinstance(body, dict):
            raise OnboardingError('Registration request must be an object.')
        if session_path.exists():
            state = json.loads(session_path.read_text(encoding='utf-8'))
            if state.get('url') != url or state.get('request') != body:
                raise OnboardingError('Session already belongs to a different registration request.')
        else:
            state = dict(schema_version=1, url=url, request=body,
                         start_key=secrets.token_hex(24), finish_key=secrets.token_hex(24))
            # Save retry keys before any network operation.
            save_private(session_path, state)
        result = public_request(url, '/registration/start', body, state['start_key'])
        cid, expires = result.get('challenge_id'), result.get('expires_at')
        if not isinstance(cid, str) or not re.fullmatch('[0-9a-f]{32}', cid) or type(expires) is not int:
            raise OnboardingError('Invalid verification challenge response.')
        state.update(challenge_id=cid, expires_at=expires)
        save_private(session_path, state, replace=True)
        return dict(status='verification_required', session_file=str(session_path), expires_at=expires,
                    next_step='register finish; enter the code privately')
    state = json.loads(session_path.read_text(encoding='utf-8'))
    if state.get('schema_version') != 1 or not re.fullmatch('[0-9a-f]{32}', state.get('challenge_id', '')):
        raise OnboardingError('Registration session has no valid challenge.')
    target = private_path(args.credentials_file)
    if target == session_path or target.exists():
        raise OnboardingError('Use a new credential filename; existing files are never overwritten.')
    if args.code_file:
        code_path = private_path(args.code_file)
        if code_path.stat().st_size > 128:
            raise OnboardingError('Code file too large.')
        code = code_path.read_text(encoding='utf-8-sig').strip()
    else:
        import sys
        if not sys.stdin.isatty():
            raise OnboardingError('Use a private --code-file when no interactive terminal is available.')
        try:
            code = getpass.getpass('Verification code (hidden): ').strip()
        except EOFError:
            raise OnboardingError('No verification code received.') from None
    if not re.fullmatch('[0-9]{8}', code):
        raise OnboardingError('Eight-digit code required.')
    # Reserve/restrict the output before issuance; failures leave no partial secret.
    fd = create_private(target)
    try:
        issued = public_request(state['url'], '/registration/finish',
                                dict(challenge_id=state['challenge_id'], code=code), state['finish_key'])
        if not isinstance(issued.get('token'), str) or not re.fullmatch('[0-9a-f]{64}', issued['token']) or not isinstance(issued.get('agent'), dict):
            raise OnboardingError('Invalid credential response; keep session and retry the identical exchange.')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            fd = None
            json.dump(issued, f, ensure_ascii=False, indent=2); f.flush(); os.fsync(f.fileno())
    except Exception:
        if fd is not None: os.close(fd)
        target.unlink(missing_ok=True)
        raise
    return dict(registered=True, agent=issued['agent'], credentials_file=str(target), token_displayed=False,
                next_step='config init using this credential file, then doctor')
