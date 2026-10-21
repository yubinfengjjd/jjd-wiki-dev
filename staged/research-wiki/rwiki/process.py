import subprocess
from pathlib import Path

from .errors import WikiError


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        tail = "\n".join(result.stderr.splitlines()[-20:])
        raise WikiError(f"命令: {subprocess.list2cmdline(command)}\n退出码: {result.returncode}\nstderr 最后 20 行:\n{tail}")
    return result
