"""Versioned trusted handoff snapshot. No production data, secrets or network access."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import shutil
from pathlib import Path
import subprocess
import tempfile
import zipfile
import sys

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git', '-c', 'safe.directory=' + ROOT.as_posix(), '-C', str(ROOT), *args], stderr=subprocess.STDOUT).decode('utf-8').strip()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--destination', required=True, help='Backup parent outside source repository')
    p.add_argument('--artifact', action='append', default=[], help='Reviewed release artifact to include; repeat for source/Skill/wheel/checksums')
    args = p.parse_args()
    parent = Path(args.destination).expanduser().resolve()
    if parent == ROOT or ROOT in parent.parents:
        raise SystemExit('Choose a backup parent outside the source repository.')
    if git('status', '--porcelain'):
        raise SystemExit('Commit reviewed work first; no uncommitted changes may be silently omitted.')
    sys.path.insert(0, str(ROOT))
    from server import VERSION
    head = git('rev-parse', 'HEAD')
    created = datetime.now(timezone.utc)
    dest = parent / (VERSION + '-' + created.strftime('%Y%m%dT%H%M%S%fZ'))
    dest.mkdir(parents=True, exist_ok=False)
    for value in args.artifact:
        artifact = Path(value).resolve()
        if not artifact.is_file() or artifact.suffix not in ('.whl', '.zip', '.txt'):
            raise SystemExit('Only reviewed release wheel/zip/checksum artifacts may be added.')
        target = dest / 'artifacts' / artifact.name
        target.parent.mkdir(exist_ok=True)
        if target.exists():raise SystemExit('Duplicate artifact filename.')
        shutil.copyfile(artifact, target)
    git('archive', '--format=zip', '--output=' + str(dest / 'source.zip'), 'HEAD')
    with zipfile.ZipFile(dest / 'source.zip') as archive:
        for name in archive.namelist():
            path = Path(name)
            if path.is_absolute() or '..' in path.parts:
                raise SystemExit('Unsafe archive entry; backup incomplete.')
            low = path.name.lower()
            if low == '.env' or low.endswith(('.db', '.pem', '.key')) or low.endswith('-credentials.json') or low in ('google-desktop.json', 'gmail-token.json'):
                raise SystemExit('Private tracked file detected; backup incomplete.')
        archive.extractall(dest / 'source')
    git('bundle', 'create', str(dest / 'repository.bundle'), '--all')
    validation = git('bundle', 'verify', str(dest / 'repository.bundle'))
    # Recover into a fresh temporary checkout; compare every exported byte.
    with tempfile.TemporaryDirectory(prefix='agent-market-restore-') as temp:
        checkout = Path(temp) / 'repo'
        subprocess.run(['git', 'clone', str(dest / 'repository.bundle'), str(checkout)], check=True, capture_output=True)
        restored = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
        if restored != head:
            raise SystemExit('Offline clone HEAD mismatch; backup incomplete.')
        for path in (dest / 'source').rglob('*'):
            if path.is_file() and path.read_bytes() != (checkout / path.relative_to(dest / 'source')).read_bytes():
                raise SystemExit('Restored file differs; backup incomplete.')
    metadata = dict(version=VERSION, created_at=created.isoformat(), source_head=head,
        source_branch=git('branch', '--show-current'), origin=git('remote', 'get-url', 'origin'),
        deployed_version='not_inspected_by_backup', github_publication='not_inspected_by_backup',
        offline_restore='PASS', source_snapshot='tracked HEAD only', production_data=False,
        historical_secret_audit=False)
    (dest / 'METADATA.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (dest / 'GIT_REFS.txt').write_text(git('show-ref', '--head') + '\n', encoding='utf-8')
    (dest / 'RESTORE_CHECK.txt').write_text(validation + '\nOffline clone HEAD and source bytes: PASS\n', encoding='utf-8')
    (dest / 'START_HERE.md').write_text(f'''# Agent Market {VERSION} 开发交接

UTC时间：{created.isoformat()}。源码commit：{head}。

直接打开 source/；先读 source/AGENTS.md、README.md、docs/release.md、docs/architecture.md 和 docs/cli.md。
当前 Alpha5 验证见 source/docs/validation-alpha5.md；注册与入口见 source/docs/registration.md 和 source/docs/documentation-status.md；后续运行器与V05见 source/docs/waiting-reliability-plan.md。

离线恢复 Git（在本备份目录运行，目标必须不存在）：

```sh
git clone ./repository.bundle ../agent-market-restored
git -C ../agent-market-restored rev-parse HEAD
git -C ../agent-market-restored remote set-url origin https://github.com/jefferysun95-cmyk/agent-market.git
```

HEAD应为 {head}。联网后fetch再核对main，不覆盖别人的开发目录或强推。
新环境在恢复仓库中创建虚拟环境，安装 requirements.txt，运行 unittest discover -s tests -v 和 demo.py。
CLI可单独 pip install .；邮件依赖及授权独立。源码依赖未离线打包，安装依赖需要网络。

这是静态开发备份，包含本地可达Git历史但不含原Git凭证配置、虚拟环境、生产数据库/配置、个人Token、Gmail授权或附件。
Alpha5 生产恢复须另按 source/docs/deploy-alpha5.md 做一致性备份（旧版历史见 deploy-v11.md）。原机器的私密凭证应由持有人安全迁移或重新授权。
本次未检查部署和GitHub状态，不能把本地版本当成线上已升级；历史Git对象未做完整密钥审计，整包只供可信开发交接。

SHA256SUMS.txt覆盖本目录所有其他文件；运行 python VERIFY_BACKUP.py 可复核。原仓库与线上不会被备份程序修改。
每版建立新快照、保留旧备份。建议将核验过的备份另外存到其他磁盘或可信云盘。
''', encoding='utf-8')
    (dest / 'VERIFY_BACKUP.py').write_text('''from pathlib import Path
import hashlib
root = Path(__file__).resolve().parent
lines = (root / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines()
for line in lines:
    expected, name = line.split('  ', 1)
    if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
        raise SystemExit('FAIL: ' + name)
print('PASS: ' + str(len(lines)) + ' files')
''', encoding='utf-8')
    sums = ''.join(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.relative_to(dest).as_posix() + '\n'
                   for path in sorted(dest.rglob('*')) if path.is_file())
    (dest / 'SHA256SUMS.txt').write_text(sums, encoding='utf-8')
    subprocess.run([sys.executable, str(dest / 'VERIFY_BACKUP.py')], check=True)
    if git('status', '--porcelain'):
        raise SystemExit('Source changed during backup; inspect before trusting this snapshot.')
    print(json.dumps(dict(backup=str(dest), offline_restore='PASS', head=head), ensure_ascii=False))


if __name__ == '__main__':
    main()
