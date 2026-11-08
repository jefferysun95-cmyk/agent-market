"""Explicitly configured local host adapter. Task text is stdin, never argv/code."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time


class HostError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def validate_host(value):
    if not isinstance(value, dict) or set(value) != {'argv', 'cwd', 'timeout_seconds'}:
        raise HostError('invalid_host_config')
    argv = value['argv']
    if not isinstance(argv,list) or not 1 <= len(argv) <= 20 or any(not isinstance(a,str) or not a or '\x00' in a for a in argv):
        raise HostError('invalid_host_config')
    if not Path(argv[0]).is_absolute() or not Path(value['cwd']).is_absolute():
        raise HostError('host_paths_must_be_absolute')
    if Path(argv[0]).suffix.lower() in ('.cmd','.bat','.ps1','.sh'):
        raise HostError('shell_wrappers_not_supported')
    if type(value['timeout_seconds']) is not int or not 1 <= value['timeout_seconds'] <= 300:
        raise HostError('invalid_host_timeout')
    return value


class ProcessTree:
    """Own one process group/job, never enumerate or kill unrelated interpreters."""
    def __init__(self, process):
        self.process = process
        self.job = None
        if os.name=='nt':
            import ctypes
            from ctypes import wintypes as w
            class Basic(ctypes.Structure):
                _fields_=[('PerProcessUserTimeLimit',ctypes.c_int64),('PerJobUserTimeLimit',ctypes.c_int64),
                    ('LimitFlags',w.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),('MaximumWorkingSetSize',ctypes.c_size_t),
                    ('ActiveProcessLimit',w.DWORD),('Affinity',ctypes.c_size_t),('PriorityClass',w.DWORD),('SchedulingClass',w.DWORD)]
            class IO(ctypes.Structure):
                _fields_=[(name,ctypes.c_uint64) for name in ('ReadOperationCount','WriteOperationCount',
                    'OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]
            class Extended(ctypes.Structure):
                _fields_=[('BasicLimitInformation',Basic),('IoInfo',IO),('ProcessMemoryLimit',ctypes.c_size_t),
                    ('JobMemoryLimit',ctypes.c_size_t),('PeakProcessMemoryUsed',ctypes.c_size_t),('PeakJobMemoryUsed',ctypes.c_size_t)]
            class Accounting(ctypes.Structure):
                _fields_=[(name,ctypes.c_int64) for name in ('TotalUserTime','TotalKernelTime','ThisPeriodTotalUserTime','ThisPeriodTotalKernelTime')]+[
                    ('TotalPageFaultCount',w.DWORD),('TotalProcesses',w.DWORD),('ActiveProcesses',w.DWORD),('TotalTerminatedProcesses',w.DWORD)]
            kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            kernel.CreateJobObjectW.argtypes=[ctypes.c_void_p,w.LPCWSTR];kernel.CreateJobObjectW.restype=w.HANDLE
            kernel.SetInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD]
            kernel.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE]
            kernel.TerminateJobObject.argtypes=[w.HANDLE,w.UINT]
            kernel.QueryInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD,ctypes.c_void_p]
            kernel.CloseHandle.argtypes=[w.HANDLE]
            self.kernel=kernel
            self.accounting_type=Accounting
            self.ctypes=ctypes
            self.job=kernel.CreateJobObjectW(None,None)
            info=Extended();info.BasicLimitInformation.LimitFlags=0x2000 # KILL_ON_JOB_CLOSE
            if not self.job or not kernel.SetInformationJobObject(self.job,9,ctypes.byref(info),ctypes.sizeof(info)) or not kernel.AssignProcessToJobObject(self.job,int(process._handle)):
                if self.job:kernel.CloseHandle(self.job)
                self.job=None
                process.kill();process.wait(timeout=5)
                raise HostError('host_process_isolation_unavailable')

    def close(self):
        if os.name=='nt':
            if self.job:
                try:
                    # Closing a KILL_ON_JOB_CLOSE handle requests termination but
                    # does not wait for descendants to release their file handles.
                    if not self.kernel.TerminateJobObject(self.job,1):
                        raise HostError('host_cleanup_uncertain')
                    end=time.monotonic()+5
                    while True:
                        info=self.accounting_type()
                        if not self.kernel.QueryInformationJobObject(self.job,1,self.ctypes.byref(info),self.ctypes.sizeof(info),None):
                            raise HostError('host_cleanup_uncertain')
                        if info.ActiveProcesses==0:break
                        if time.monotonic()>=end:raise HostError('host_cleanup_uncertain')
                        time.sleep(0.02)
                finally:
                    self.kernel.CloseHandle(self.job);self.job=None
        else:
            try:os.killpg(self.process.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:self.process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:pass
            try:os.killpg(self.process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
        try:self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:raise HostError('host_cleanup_uncertain') from None


def invoke_host(config, work, should_stop=lambda:False, deadline=None):
    """Bounded subprocess protocol. No stdout/stderr is echoed or checkpointed."""
    validate_host(config)
    if should_stop(): raise HostError('stopped')
    payload=json.dumps(dict(config=config,work=work),ensure_ascii=False,allow_nan=False).encode('utf-8')
    if len(payload)>2*1024*1024:raise HostError('host_input_limit')
    if deadline is not None and time.time()>=deadline:raise HostError('timed_out')
    end=min(time.time()+config['timeout_seconds'], deadline if deadline is not None else float('inf'))
    # Private temporary files prevent pipe deadlocks and bound output before parse.
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        # This package-owned bootstrap blocks on stdin until job/group isolation
        # succeeds. No trusted host or its descendants can run before assignment.
        process=subprocess.Popen([sys.executable,str(Path(__file__).with_name('host_worker.py'))],
            stdin=subprocess.PIPE,stdout=output,stderr=errors,
            shell=False,start_new_session=os.name!='nt',
            creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW) if os.name=='nt' else 0)
        try:tree=ProcessTree(process)
        except Exception:
            if process.stdin:process.stdin.close()
            raise
        try:
            first=True
            while process.poll() is None:
                if should_stop():raise HostError('stopped')
                if time.time()>=end:raise HostError('host_timeout')
                if os.fstat(output.fileno()).st_size>65536 or os.fstat(errors.fileno()).st_size>65536:
                    raise HostError('host_output_limit')
                try:
                    process.communicate(input=payload if first else None,timeout=0.05)
                except subprocess.TimeoutExpired:pass
                first=False
            if process.returncode:raise HostError('host_failed')
            output.seek(0);raw=output.read(65537)
            if len(raw)>65536:raise HostError('host_output_limit')
            try:reply=json.loads(raw)
            except (UnicodeError,ValueError):raise HostError('invalid_host_reply') from None
            if not isinstance(reply,dict) or set(reply)!={'schema_version','work_id','outcome'} or type(reply['schema_version']) is not int or reply['schema_version']!=1 or reply['work_id']!=work['work_id']:
                raise HostError('invalid_host_reply')
            if reply['outcome'] not in ('completed','pending','provider_402','handler_failed','mail_auth_failed',
                    'mail_validation_failed','mail_dependencies_missing','send_uncertain','mail_service_failed'):
                raise HostError('invalid_host_reply')
            return reply['outcome']
        finally:
            tree.close()
            if process.stdin:process.stdin.close()
