import subprocess
from pathlib import Path

from .errors import WikiError

# A plotting run that has not finished in this time is hung, not slow.
TIMEOUT_SECONDS = 1800


def run(command: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    try:
        # Rscript on a Chinese Windows locale may print GBK; never fail on decoding the log.
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, env=env,
                                encoding="utf-8", errors="replace", timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as error:
        raise WikiError(f"命令超过 {TIMEOUT_SECONDS} 秒未结束: {subprocess.list2cmdline(command)}") from error
    if result.returncode:
        tail = "\n".join(result.stderr.splitlines()[-20:])
        raise WikiError(f"命令: {subprocess.list2cmdline(command)}\n退出码: {result.returncode}\nstderr 最后 20 行:\n{tail}")
    return result
