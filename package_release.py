"""Build public archives from the Git index only, never ignored local state."""
import hashlib
from pathlib import Path
import subprocess
import zipfile

from server import VERSION


if __name__=='__main__':
    root=Path(__file__).parent
    names=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
    names=[n for n in names if n]
    if not names:raise SystemExit('Stage reviewed source files first')
    dest=root/'dist';dest.mkdir(exist_ok=True)
    packages=[]
    for label,subset,prefix in [
        ('source',names,''),
        ('skill',[n for n in names if n.startswith('skills/agent-market/')],'skills/')]:
        path=dest/f'agent-market-{label}-{VERSION}.zip'
        with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as archive:
            for name in sorted(subset):
                # Reading the index makes release bytes match the reviewed staged snapshot.
                content=subprocess.check_output(['git','show',':'+name],cwd=root)
                archive.writestr(name.removeprefix(prefix),content)
        packages.append(path)
    (dest/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in packages),encoding='utf-8')
    print('Built source and Skill archives from Git index; checksums saved in dist.')
