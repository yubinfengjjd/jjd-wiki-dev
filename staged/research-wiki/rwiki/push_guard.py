"""推送前防泄漏检查：规则、推送范围扫描、GPL 忽略托管块与作者块基准。

规则 id：gallery、project-data、gpl-path、gpl-header、size、abs-path。
仓库根的 `.push-guard-allow` 只能豁免 abs-path 与 size，每条必须写理由。
"""
import codecs
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .config import read_json
from .errors import WikiError
from .store import git

DEFAULT_MAX_MB = 5
DEFAULT_GPL_GLOBS = ("**/SCP-local/**",)
# 标记拆开书写：本文件与测试的文件头不能含完整标记，否则自身会被 gpl-header 拦截。
SPDX = "SPDX-License" + "-Identifier: "
GPL_MARKERS = ("GNU General " + "Public License", SPDX + "GPL", SPDX + "AGPL", SPDX + "LGPL")
ALLOWED_RULES = ("abs-path", "size")
ALLOW_FILE = ".push-guard-allow"
ABS_PATH = (r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]",
            r"(?<![\w.])/(?:Users|home)/[^/\s]+/")
ABS_RE = re.compile("|".join(ABS_PATH))
CODE_SUFFIXES = {".r", ".py", ".c", ".cpp", ".h", ".hpp", ".js", ".ts", ".sh"}
HEAD_BYTES = 4096
GALLERY = "画廊/**"
PROJECT_DATA = "**/wiki-use/_project/**"
GPL_LICENSE = re.compile(r"^(A|L)?GPL")
IGNORE_BEGIN = "# >>> push-guard gpl"
IGNORE_END = "# <<< push-guard gpl"
IGNORE_BLOCK = re.compile(rb"# >>> push-guard gpl\r?\n.*?# <<< push-guard gpl(?:\r?\n)?", re.S)
USER_BLOCK = re.compile(rb"<!-- user:start -->(.*?)<!-- user:end -->", re.S)
BASELINE_FILE = ".protected-hashes.json"


@dataclass(frozen=True)
class Rules:
    max_file_bytes: int
    gpl_globs: tuple[str, ...]
    gpl_markers: tuple[str, ...]
    gpl_dirs: tuple[str, ...]
    allow: tuple[tuple[str, str], ...]


def glob_regex(pattern: str) -> str:
    """gitignore 风格的路径 glob：`**/` 任意层目录，`*` 不跨 `/`。"""
    parts, index = [], 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            parts.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            parts.append(".*")
            index += 2
        elif pattern[index] == "*":
            parts.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            parts.append("[^/]")
            index += 1
        else:
            parts.append(re.escape(pattern[index]))
            index += 1
    return "".join(parts)


def glob_match(path: str, pattern: str) -> bool:
    return re.fullmatch(glob_regex(pattern), path) is not None


def parse_allow(text: str, source: str = ALLOW_FILE) -> tuple[tuple[str, str], ...]:
    entries = []
    for number, line in enumerate(text.splitlines(), 1):
        rule_part, _, reason = line.partition("#")
        if not rule_part.strip():
            continue
        fields = rule_part.split()
        if len(fields) != 2 or fields[0] not in ALLOWED_RULES:
            raise WikiError(f"{source}:{number}: 只接受 `abs-path|size <glob>  # 理由`，"
                            f"画廊、GPL、课题数据不可豁免: {line}")
        if not reason.strip():
            raise WikiError(f"{source}:{number}: 豁免规则缺少理由: {line}")
        entries.append((fields[0], fields[1]))
    return tuple(entries)


def restricted_dirs(wiki_root: Path) -> list[str]:
    """限制性许可页的源码目录（相对 wiki_root，带结尾 `/`），不进 Git、不推送。

    方法页：GPL 系的 code/ 与 source/；v2 配方页：GPL/CC-NC/SA/ND 的 source/；
    派生模板（frontmatter `license` 为上述许可）：code/ 与 example/。
    """
    from .pages import parse_page
    from .sources import restricted_license

    dirs = []
    for kind, folders, test in (("methods", ("code", "source"), lambda value: bool(GPL_LICENSE.match(value))),
                                ("recipes", ("source",), restricted_license),
                                ("templates", ("code", "example"), restricted_license)):
        for page in sorted((wiki_root / kind).glob("*.md")):
            meta, _, error = parse_page(page.read_text(encoding="utf-8"))
            if not error and isinstance(meta.get("license"), str) and test(meta["license"]):
                dirs += [f"{kind}/{page.stem}/{folder}/" for folder in folders]
    return dirs


gpl_method_dirs = restricted_dirs


def load_rules(cfg, repo: Path) -> Rules:
    settings = cfg.push_guard
    root, repo = cfg.wiki_root.resolve(), repo.resolve()
    gpl_dirs = ()
    if root.is_relative_to(repo):
        relative = root.relative_to(repo).as_posix()
        prefix = "" if relative == "." else relative + "/"
        gpl_dirs = tuple(prefix + d for d in restricted_dirs(root))
    allow_path = repo / ALLOW_FILE
    allow = parse_allow(allow_path.read_text(encoding="utf-8"), str(allow_path)) if allow_path.is_file() else ()
    return Rules(max_file_bytes=int(settings.get("max_file_mb", DEFAULT_MAX_MB) * 2 ** 20),
                 gpl_globs=tuple(settings.get("gpl_globs", DEFAULT_GPL_GLOBS)),
                 gpl_markers=GPL_MARKERS, gpl_dirs=gpl_dirs, allow=allow)


def find_abs_paths(text: str) -> list[str]:
    return [match.group(0) for match in ABS_RE.finditer(text)]


def classify(path: str, size: int, added: list[str], head: bytes, rules: Rules) -> list[tuple[str, str]]:
    hits = []
    name = PurePosixPath(path).name
    if glob_match(path, GALLERY):
        hits.append(("gallery", "画廊内容不推送"))
    if glob_match(path, PROJECT_DATA):
        hits.append(("project-data", "课题数据留在课题目录"))
    if (any(path.startswith(d) for d in rules.gpl_dirs)
            or any(glob_match(path, g) for g in rules.gpl_globs)):
        hits.append(("gpl-path", "GPL 源码目录"))
    if PurePosixPath(path).suffix.lower() in CODE_SUFFIXES or name.upper().startswith("LICENSE"):
        text = head[:HEAD_BYTES].decode("utf-8", "replace")
        marker = next((m for m in rules.gpl_markers if m in text), None)
        if marker:
            hits.append(("gpl-header", marker))
    if size > rules.max_file_bytes:
        hits.append(("size", f"{size} 字节 > {rules.max_file_bytes}"))
    if name.lower().endswith(".lnk"):
        hits.append(("abs-path", "Windows 快捷方式"))
    elif b"\0" not in head[:HEAD_BYTES]:
        found = sorted(set(find_abs_paths("\n".join(added))))
        if found:
            hits.append(("abs-path", " ".join(found[:3])))
    return [(rule, detail) for rule, detail in hits
            if not (rule in ALLOWED_RULES
                    and any(kind == rule and glob_match(path, pattern) for kind, pattern in rules.allow))]


def is_zero(sha: str) -> bool:
    return set(sha) == {"0"}


def push_ranges(repo: Path, remote: str, updates: list[tuple[str, str, str, str]]) -> list[str]:
    ranges = []
    for _, local_sha, _, remote_sha in updates:
        if is_zero(local_sha):
            continue
        ranges.append(f"{local_sha} --not --remotes={remote}" if is_zero(remote_sha)
                      else f"{remote_sha}..{local_sha}")
    return ranges


def _unquote(path: str) -> str:
    if path.startswith('"'):
        return codecs.escape_decode(path[1:-1].encode("utf-8"))[0].decode("utf-8")
    return path


def _cat_file(repo: Path, option: str, shas: list[str]) -> bytes:
    result = subprocess.run(["git", "-C", str(repo), "cat-file", option],
                            input="".join(f"{sha}\n" for sha in shas).encode(), capture_output=True)
    if result.returncode:
        raise WikiError(f"git cat-file {option} 失败: {result.stderr.decode('utf-8', 'replace')}")
    return result.stdout


def _blob_info(repo: Path, sizes_for: set[str], heads_for: set[str]) -> tuple[dict, dict]:
    sizes = {}
    for line in _cat_file(repo, "--batch-check", sorted(sizes_for)).decode().splitlines():
        sha, _, size = line.split()
        sizes[sha] = int(size)
    heads, data, offset = {}, _cat_file(repo, "--batch", sorted(heads_for)), 0
    while offset < len(data):
        end = data.index(b"\n", offset)
        sha, _, size = data[offset:end].decode().split()
        heads[sha] = data[end + 1:end + 1 + min(int(size), HEAD_BYTES)]
        offset = end + 1 + int(size) + 1
    return sizes, heads


def _parse_log(text: str) -> list[dict]:
    """把 `git log --raw -p -U0` 输出拆成逐提交的文件变化。"""
    commits, current, target, in_hunk = [], None, None, False
    for line in text.split("\n"):
        if line.startswith("\x01"):
            current = {"commit": line[1:], "files": {}}
            commits.append(current)
            target, in_hunk = None, False
        elif current is None:
            continue
        elif line.startswith("diff --git "):
            target, in_hunk = None, False
        elif in_hunk:
            if line.startswith("+") and target is not None:
                current["files"][target]["added"].append(line[1:])
        elif line.startswith(":") and "\t" in line:
            fields, path = line.split("\t", 1)
            _, new_mode, _, new_sha, status = fields[1:].split()
            if status != "D" and new_mode != "160000":
                current["files"][_unquote(path)] = {"blob": new_sha, "added": []}
        elif line.startswith("+++ "):
            name = _unquote(line[4:].rstrip("\t"))
            target = name[2:] if name.startswith("b/") and name[2:] in current["files"] else None
        elif line.startswith("@@"):
            in_hunk = True
    return commits


def scan(repo: Path, rev_range: str, rules: Rules) -> list[dict]:
    """逐提交检查推送范围；被后续提交删除或改写的违规同样报告。"""
    text = git(repo, "-c", "core.quotePath=false", "log", "--format=%x01%H", "--root", "--raw", "-p",
               "-U0", "--no-color", "--no-renames", "--no-abbrev", "--no-ext-diff", "--no-textconv",
               *rev_range.split(), "--")
    commits = _parse_log(text)
    blobs = {info["blob"] for commit in commits for info in commit["files"].values()}
    code = {info["blob"] for commit in commits for path, info in commit["files"].items()
            if PurePosixPath(path).suffix.lower() in CODE_SUFFIXES
            or PurePosixPath(path).name.upper().startswith("LICENSE")}
    sizes, heads = _blob_info(repo, blobs, code) if blobs else ({}, {})
    findings = []
    for commit in commits:
        for path, info in commit["files"].items():
            for rule, detail in classify(path, sizes[info["blob"]], info["added"],
                                         heads.get(info["blob"], b""), rules):
                finding = {"rule": rule, "path": path, "commit": commit["commit"], "detail": detail}
                if finding not in findings:
                    findings.append(finding)
    return findings


def format_finding(finding: dict) -> str:
    return "\t".join((finding["rule"], finding["path"], finding["commit"], finding["detail"]))


def pre_push(repo: Path, remote: str, stdin: str, rules: Rules) -> int:
    """pre-push hook 入口：legacy/* 永不推送；其余分支（v2 起含 main）只做内容扫描。"""
    updates = [tuple(line.split()) for line in stdin.splitlines() if line.strip()]
    refused = []
    for local_ref, local_sha, remote_ref, remote_sha in updates:
        name = remote_ref.removeprefix("refs/heads/")
        if name.startswith("legacy/") or local_ref.removeprefix("refs/heads/").startswith("legacy/"):
            refused.append(f"拒绝推送 {name}：legacy/* 只保留在本地")
    for message in refused:
        print(message, file=sys.stderr)
    if refused:
        return 1
    findings = [finding for rev_range in push_ranges(repo, remote, updates)
                for finding in scan(repo, rev_range, rules)]
    for finding in findings:
        print(format_finding(finding), file=sys.stderr)
    return 1 if findings else 0


def sync_ignore(wiki_root: Path) -> bool:
    """重写知识库 .gitignore 的 GPL 托管块；块外字节不动；内容变化时返回 True。"""
    path = wiki_root / ".gitignore"
    data = path.read_bytes() if path.is_file() else b""
    dirs = restricted_dirs(wiki_root)
    block = (IGNORE_BEGIN + "\n" + "".join(f"/{d}\n" for d in dirs) + IGNORE_END + "\n").encode("utf-8")
    match = IGNORE_BLOCK.search(data)
    if match:
        updated = data[:match.start()] + block + data[match.end():]
    elif dirs:
        updated = data + (b"" if not data or data.endswith(b"\n") else b"\n") + block
    else:
        return False
    if updated == data:
        return False
    path.write_bytes(updated)
    return True


def user_blocks(data: bytes) -> list[bytes]:
    return [match.group(0) for match in USER_BLOCK.finditer(data)]


def baseline(wiki_root: Path) -> dict:
    """每个已跟踪 .md 的每个作者块的 SHA-256（含标记与行尾字节）。"""
    files = {}
    names = git(wiki_root, "-c", "core.quotePath=false", "ls-files", "-z", "--", "*.md").split("\0")
    for name in sorted(filter(None, names)):
        path = wiki_root / name
        if not path.is_file():
            continue
        blocks = user_blocks(path.read_bytes())
        if blocks:
            files[name] = [hashlib.sha256(block).hexdigest() for block in blocks]
    return {"version": 1, "files": files}


def write_baseline(wiki_root: Path) -> dict:
    data = baseline(wiki_root)
    (wiki_root / BASELINE_FILE).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                                           encoding="utf-8", newline="\n")
    return data


def check_baseline(wiki_root: Path) -> list[str]:
    recorded = read_json(wiki_root / BASELINE_FILE)["files"]
    current = baseline(wiki_root)["files"]
    problems = []
    for name, hashes in sorted(recorded.items()):
        if name not in current:
            problems.append(f"{name}: 作者块缺失（文件或作者块已删除）")
        elif current[name] != hashes:
            problems.append(f"{name}: 作者块字节与基准不一致")
    return problems
