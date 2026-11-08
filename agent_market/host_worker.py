"""Isolation bootstrap: wait for parent input before starting the trusted host."""
import json
import subprocess
import sys
import tempfile


def main():
    envelope=json.load(sys.stdin)
    config,work=envelope['config'],envelope['work']
    if envelope.get('stdin_null') is True:
        return subprocess.run(config['argv'],cwd=config['cwd'],stdin=subprocess.DEVNULL,shell=False).returncode
    with tempfile.TemporaryFile() as input_file:
        input_file.write(json.dumps(work,ensure_ascii=False).encode('utf-8'));input_file.seek(0)
        return subprocess.run(config['argv'],cwd=config['cwd'],stdin=input_file,shell=False).returncode


if __name__=='__main__':
    try:sys.exit(main())
    except Exception:sys.exit(2) # Never echo private task/config exceptions.
