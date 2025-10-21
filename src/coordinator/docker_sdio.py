# src/coordinator/docker_stdio.py
from __future__ import annotations
import subprocess, threading, queue, os, sys
from typing import Optional, List, Dict, Tuple, IO

class StdioProcess:
    def __init__(self, popen: subprocess.Popen):
        self.p = popen

    @property
    def stdin(self) -> IO[bytes]:
        assert self.p.stdin
        return self.p.stdin

    @property
    def stdout(self) -> IO[bytes]:
        assert self.p.stdout
        return self.p.stdout

    def terminate(self):
        try:
            self.p.terminate()
        except Exception:
            pass

def spawn_docker_stdio(cmd: str, args: List[str], env: Dict[str, str]) -> StdioProcess:
    # Merge env onto current environment (so DOCKER_* etc. still pass through)
    proc_env = os.environ.copy()
    proc_env.update(env or {})

    popen = subprocess.Popen(
        [cmd] + args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=proc_env,
        bufsize=0,
    )
    return StdioProcess(popen)
