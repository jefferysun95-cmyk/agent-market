"""Build immutable source/Skill/script assets from clean HEAD and verify a wheel."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile
import sys

ROOT=Path(__file__).resolve().parents[1]
def git(*args):
    return subprocess.check_output(['git','-c','safe.directory='+ROOT.as_posix(),'-C',str(ROOT),*args])

def build(wheel,destination):
    sys.path.insert(0,str(ROOT))
    from server import VERSION
    from agent_market import __version__
    if VERSION!=__version__:raise ValueError('Server/client versions differ')
    if git('status','--porcelain').strip():raise ValueError('Commit reviewed source before building a release')
    commit=git('rev-parse','HEAD').decode().strip()
    package=VERSION.replace('-alpha.','a')
    if re.search(r'^version = "([^"]+)"', (ROOT/'pyproject.toml').read_text(),re.M).group(1)!=package:
        raise ValueError('Package version differs')
    names=sorted(n for n in git('ls-files','-z').decode().split('\0') if n)
    for name in names:
        path=Path(name)
        if path.name.startswith('.env') or path.suffix.lower() in ('.db','.sqlite','.key','.pem') or path.name.endswith('credentials.json'):
            raise ValueError('Unexpected sensitive tracked file; audit before packaging')
    data={name:git('show','HEAD:'+name) for name in names}
    with zipfile.ZipFile(wheel) as archive:
        for name,content in data.items():
            if name.startswith('agent_market/') and name.endswith('.py'):
                if archive.read(name).replace(b'\r\n',b'\n')!=content.replace(b'\r\n',b'\n'):
                    raise ValueError('Wheel/source code differs: '+name)
        metadata=archive.read('agent_market_client-'+package+'.dist-info/METADATA').decode()
        if 'Version: '+package not in metadata.splitlines():raise ValueError('Wheel version differs')
    destination=Path(destination).resolve()
    if destination.exists():raise ValueError('Release destination already exists; never overwrite')
    destination.mkdir(parents=True)
    artifacts=[]
    for kind in ('source','skill'):
        target=destination/f'agent-market-{kind}-{VERSION}.zip'
        with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED) as archive:
            for name,content in data.items():
                if kind=='skill' and not name.startswith('skills/agent-market/'):continue
                entry=name if kind=='source' else name.removeprefix('skills/')
                info=zipfile.ZipInfo(entry,(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                info.external_attr=(0o755 if name.endswith('.sh') else 0o644)<<16
                archive.writestr(info,content)
        artifacts.append(target)
        with zipfile.ZipFile(target) as archive:
            for entry in archive.namelist():
                name=entry if kind=='source' else 'skills/'+entry
                if archive.read(entry)!=data[name]:raise ValueError('Archive bytes differ')
    target=destination/Path(wheel).name;target.write_bytes(Path(wheel).read_bytes());artifacts.append(target)
    target=destination/'upgrade_alpha5.sh';target.write_bytes(data['tools/upgrade_alpha5.sh']);artifacts.append(target)
    (destination/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in artifacts),encoding='ascii')
    (destination/'BUILD_RECORD.json').write_text(json.dumps(dict(version=VERSION,commit=commit,source_and_skill_match_head=True,wheel_modules_match_head=True,artifacts=[p.name for p in artifacts]),indent=2),encoding='utf-8')
    return dict(version=VERSION,commit=commit,destination=str(destination),artifacts=[p.name for p in artifacts])

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--wheel',required=True);parser.add_argument('--destination',required=True)
    args=parser.parse_args()
    print(json.dumps(build(args.wheel,args.destination)))
