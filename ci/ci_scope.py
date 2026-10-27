"""CI 改动范围：决定哪些重步骤要跑。只用标准库，在 pip install 之前运行。

job 本身始终运行并上报检查结果，只用 step 级 if 跳过重步骤。不要改成 workflow 级 paths 过滤：
被跳过的 workflow 不上报检查，PR 会一直停在 Pending，wiki.py gh merge 的门禁因此无法通过。

- schedule / workflow_dispatch：全量。
- push（合入 main）：PR 上已跑过全量，只跑轻量检查。
- pull_request：改到 .github/workflows/ 或 ci/ 时全量；diff 为空或取不到时全量（失败即保守）；
  否则只有改到文档（review/、根目录 *.md）与 frontend/ 之外的文件才跑 pytest，
  改到 frontend/ 才跑前端测试。
"""
import os
import subprocess
import sys
from pathlib import Path

FULL = {"pytest": True, "frontend": True}
LIGHT = {"pytest": False, "frontend": False}
ALWAYS_FULL = (".github/workflows/", "ci/")
# PR/Issue 模板不算文档：test_repo_files 校验它们的小节，与 ghflow 生成的正文对应。
DOC_PREFIXES = ("review/",)
FRONTEND = "frontend/"


def is_doc(path: str) -> bool:
    return path.startswith(DOC_PREFIXES) or ("/" not in path and path.endswith(".md"))


def scope(paths: list[str], event: str) -> dict:
    if event not in ("pull_request", "push"):
        return dict(FULL)
    if event == "push":
        return dict(LIGHT)
    if not paths or any(path.startswith(ALWAYS_FULL) for path in paths):
        return dict(FULL)
    return {"pytest": any(not is_doc(path) and not path.startswith(FRONTEND) for path in paths),
            "frontend": any(path.startswith(FRONTEND) for path in paths)}


def changed_paths(base_ref: str) -> list[str]:
    result = subprocess.run(["git", "-c", "core.quotepath=off", "diff", "--name-only", "-z",
                             f"origin/{base_ref}...HEAD"], capture_output=True)
    if result.returncode:
        print(f"git diff 失败，按全量运行：{result.stderr.decode('utf-8', 'replace').strip()}", file=sys.stderr)
        return []
    return [path for path in result.stdout.decode("utf-8").split("\0") if path]


def write_outputs(result: dict, target: Path) -> None:
    with open(target, "a", encoding="utf-8") as handle:
        for key, value in result.items():
            handle.write(f"{key}={'true' if value else 'false'}\n")


def main() -> None:
    event = os.environ.get("EVENT", "")
    paths = changed_paths(os.environ["BASE_REF"]) if event == "pull_request" else []
    result = scope(paths, event)
    print(f"event={event} 改动文件 {len(paths)} 个 → {result}")
    for path in paths[:50]:
        print(f"  {path}")
    write_outputs(result, Path(os.environ["GITHUB_OUTPUT"]))


if __name__ == "__main__":
    main()
