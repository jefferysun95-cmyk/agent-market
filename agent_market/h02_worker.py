"""H02 child/exit observer. Only owns its one deterministic CLI child."""
from pathlib import Path
import json
import os
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from agent_market.cli import main


def write_record(path,body):
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as file:
        json.dump(body,file);file.flush();os.fsync(file.fileno())


def observe():
    exit_file,process_file,wall_seconds=sys.argv[2:5]
    if sys.argv[5]!='--':raise ValueError('Invalid observer arguments')
    options={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),*sys.argv[6:]],
                           stdin=subprocess.DEVNULL,close_fds=True,**options)
    try:
        write_record(process_file,dict(observer_pid=os.getpid(),child_pid=child.pid))
        hard_timeout=False
        try:code=child.wait(timeout=int(wall_seconds))
        except subprocess.TimeoutExpired:
            hard_timeout=True;child.kill();code=child.wait(timeout=10)
        write_record(exit_file,dict(observer_pid=os.getpid(),child_pid=child.pid,
                                   business_exit_code=code,hard_timeout_triggered=hard_timeout))
        return 124 if hard_timeout else (0 if code==0 else 7)
    finally:
        if child.poll() is None:child.kill();child.wait(timeout=10)


if __name__=='__main__':
    sys.exit(observe() if len(sys.argv)>1 and sys.argv[1]=='--observe' else main())
