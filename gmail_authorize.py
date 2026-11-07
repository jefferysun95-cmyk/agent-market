"""Explicit local OAuth handoff; never uploads mailbox credentials to Agent Market."""
import argparse
import os
from pathlib import Path

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--client-secrets',required=True,help='Google Desktop OAuth app JSON')
    parser.add_argument('--output',required=True,help='New private token file outside repository')
    args=parser.parse_args()
    output=Path(args.output).expanduser().resolve()
    if output.exists():parser.error('Output exists; choose a new path or revoke/replace explicitly')
    if Path(__file__).parent.resolve() in output.parents:parser.error('Keep Gmail credentials outside repository')
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow=InstalledAppFlow.from_client_secrets_file(args.client_secrets,
        ['https://www.googleapis.com/auth/gmail.readonly','https://www.googleapis.com/auth/gmail.send'])
    credentials=flow.run_local_server(port=0,open_browser=True)
    output.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:f.write(credentials.to_json())
    print('Gmail authorization saved locally. Do not share the file.')
