"""Restricted Zoho CPaaS HTTPS verification sender. No redirects or retries."""
import json
import re
from urllib.error import HTTPError
from urllib.request import Request, HTTPRedirectHandler, build_opener


ZOHO_ENDPOINT = 'https://cpaas.zoho.com/v1.1/email'


class MailDeliveryError(ValueError):
    def __init__(self, code, http_status=None):
        self.code, self.http_status = code, http_status
        super().__init__(code)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def zoho_sender(sender, api_key, endpoint=ZOHO_ENDPOINT):
    if endpoint != ZOHO_ENDPOINT:
        raise ValueError('Use the supported Zoho CPaaS HTTPS endpoint, not an SMTP host or arbitrary URL')
    if not isinstance(api_key, str) or not 16 <= len(api_key) <= 4096 or any(ord(c) < 33 or ord(c) > 126 for c in api_key):
        raise ValueError('Invalid private Zoho API key')

    def send(recipient, code, challenge_id):
        body = {'from': {'address': sender, 'name': 'Agent Market'},
                'to': [{'email_address': {'address': recipient}}],
                'subject': 'Agent Market verification code',
                'textbody': f'Your Agent Market code is {code}. It expires in 10 minutes.\nRequest: {challenge_id}\nIgnore this message if you did not request it. Please do not reply.',
                'client_reference': challenge_id, 'track_opens': False, 'track_clicks': False}
        request = Request(endpoint, json.dumps(body).encode(), method='POST',
                          headers={'Authorization': 'Zoho-enczapikey ' + api_key, 'Content-Type': 'application/json'})
        try:
            with build_opener(NoRedirect).open(request, timeout=15) as response:
                status, raw = response.status, response.read(65537)
        except HTTPError as error:
            status = error.code
            error.close()
            raise MailDeliveryError('zoho_request_not_accepted', status) from None
        if len(raw) > 65536 or not 200 <= status < 300:
            raise MailDeliveryError('zoho_response_unconfirmed', status)
        try:
            result = json.loads(raw)
        except (ValueError, UnicodeError):
            raise MailDeliveryError('zoho_response_unconfirmed', status) from None
        data = result.get('data') if isinstance(result, dict) else None
        if (not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict)
                or data[0].get('code') != 'EM_104' or result.get('error')
                or not isinstance(result.get('request_id'), str)
                or not re.fullmatch(r'[A-Za-z0-9._:-]{1,300}', result['request_id'])):
            raise MailDeliveryError('zoho_response_unconfirmed', status)
        return {'transport': 'zoho_api', 'http_status': status, 'provider_accepted': True, 'request_id': result['request_id'],
                'mailbox_delivery_confirmed': False}
    return send
