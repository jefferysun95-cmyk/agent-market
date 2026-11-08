"""Save a separate private Zoho API setup, preserving the registration secret."""
import argparse
import getpass
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_market.onboarding import private_path, save_private
from tools.configure_registration_mail import default_path
from registration import email_address
from registration_mail import zoho_sender, ZOHO_ENDPOINT


def configure(source, target):
    source, target = private_path(source), private_path(target)
    if source == target or target.exists():
        raise ValueError('Use a new API configuration filename; existing files are never overwritten')
    previous = json.loads(source.read_text(encoding='utf-8'))
    secret = previous.get('MARKET_REGISTRATION_SECRET')
    sender = email_address(previous.get('MARKET_MAIL_FROM', previous.get('MARKET_SMTP_FROM', '')))
    if not isinstance(secret, str) or len(secret) < 32:
        raise ValueError('Existing registration secret unavailable; no new secret generated')
    key = getpass.getpass('Zoho API Setup Default API Key (hidden): ').strip()
    if key.startswith('Zoho-enczapikey '):
        key = key[len('Zoho-enczapikey '):].strip()
    zoho_sender(sender, key)  # Configuration validation only, never calls send.
    config = dict(MARKET_SELF_REGISTRATION='1', MARKET_MAIL_TRANSPORT='zoho_api',
                  MARKET_MAIL_FROM=sender, MARKET_ZOHO_API_KEY=key, MARKET_ZOHO_API_URL=ZOHO_ENDPOINT,
                  MARKET_REGISTRATION_SECRET=secret)
    save_private(target, config)
    return dict(saved=True, config_file=str(target), sender=sender, transport='zoho_api',
                registration_secret_preserved=True, smtp_config_unchanged=True, network_requests=0,
                production_changed=False, secret_displayed=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smtp-config', default=str(default_path()))
    parser.add_argument('--output', default=str(default_path().with_name('registration-test-zoho-api.json')))
    args = parser.parse_args(argv)
    try:
        result = configure(args.smtp_config, args.output)
    except (Exception, KeyboardInterrupt):
        print(json.dumps(dict(saved=False, error='Setup did not complete; check existing private config, API key and output filename. Details suppressed.')), file=sys.stderr)
        return 2
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())
