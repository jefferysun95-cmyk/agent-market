"""Interactively save private platform SMTP settings; no network or deployment."""
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import secrets
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_market.onboarding import private_path, save_private
from registration import email_address


def default_path():
    root = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'AgentMarket' if os.name == 'nt' else Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'agent-market'
    return root / 'registration-test-mail.json'


def configure(target):
    target = private_path(target)
    if target.exists():
        raise ValueError('Private configuration already exists; no overwrite or secret rotation performed.')
    host = input('SMTP host (use the value in your Zoho Agent) [smtp.zeptomail.com]: ').strip() or 'smtp.zeptomail.com'
    port = input('SMTP port [465]: ').strip() or '465'
    user = input('SMTP username [emailapikey]: ').strip() or 'emailapikey'
    sender = input('From address [verify@run7.ai]: ').strip() or 'verify@run7.ai'
    if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?', host) or port not in ('465', '587') or not user or len(user) > 254 or any(c in user for c in '\r\n'):
        raise ValueError('Invalid SMTP connection settings.')
    sender = email_address(sender)
    password = getpass.getpass('SMTP password (hidden, never paste it in chat): ')
    if not password or len(password) > 4096 or '\r' in password or '\n' in password:
        raise ValueError('Invalid SMTP password input.')
    config = dict(MARKET_SELF_REGISTRATION='1', MARKET_SMTP_HOST=host, MARKET_SMTP_PORT=port,
                  MARKET_SMTP_USER=user, MARKET_SMTP_FROM=sender, MARKET_SMTP_PASSWORD=password,
                  MARKET_REGISTRATION_SECRET=secrets.token_urlsafe(48))
    save_private(target, config)
    return dict(saved=True, config_file=str(target), sender=sender, network_requests=0,
                production_changed=False, secret_displayed=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=str(default_path()))
    args = parser.parse_args(argv)
    try:
        result = configure(args.output)
    except (Exception, KeyboardInterrupt):
        print(json.dumps(dict(saved=False, error='Configuration was not completed; check input, existing file and private path. Secret details suppressed.')), file=sys.stderr)
        return 2
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())
