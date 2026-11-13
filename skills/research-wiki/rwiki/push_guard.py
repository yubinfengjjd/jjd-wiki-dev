"""推送前防泄漏检查与作者块基准（作者 2026-11-02：知识默认入 Git）。

规则 id：private-data、project-data、secret、size、abs-path。
仓库根的 `.push-guard-allow` 只能豁免 abs-path 与 size，每条必须写理由。
"""
import codecs
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from contextlib import ExitStack, contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .config import read_json
from .errors import WikiError
from .process import TIMEOUT_SECONDS
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
                            f"私有数据、课题数据、密码和私钥不可豁免: {line}")
        if not reason.strip():
            raise WikiError(f"{source}:{number}: 豁免规则缺少理由: {line}")
        entries.append((fields[0], fields[1]))
    return tuple(entries)


def restricted_dirs(wiki_root: Path) -> list[str]:
    """限制性许可页的目录分类，仅供旧 worktree 联接兼容，不再用于 Git 排除。

    方法页：GPL 系的 code/ 与 source/；v2 配方页：GPL/CC-NC/SA/ND 的 source/；
    派生模板（frontmatter `license` 为上述许可）：code/ 与 example/。
    """
    from .pages import parse_page

    dirs = []
    for kind in _RESTRICTED_FOLDERS:
        for page in sorted((wiki_root / kind).glob("*.md")):
            meta, _, error = parse_page(page.read_text(encoding="utf-8"))
            if not error:
                dirs += restricted_page_dirs(kind, page.stem, meta)
    return dirs


_RESTRICTED_FOLDERS = {"methods": ("code", "source"), "recipes": ("source",), "templates": ("code", "example")}


def restricted_page_dirs(kind: str, slug: str, meta: dict) -> list[str]:
    """单个页面在 restricted_dirs 中的各项（同样相对 wiki_root、带结尾 `/`）。"""
    from .sources import restricted_license

    test = (lambda value: bool(GPL_LICENSE.match(value))) if kind == "methods" else restricted_license
    license = meta.get("license")
    if kind not in _RESTRICTED_FOLDERS or not isinstance(license, str) or not test(license):
        return []
    return [f"{kind}/{slug}/{folder}/" for folder in _RESTRICTED_FOLDERS[kind]]


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
    if glob_match(path, PROJECT_DATA):
        hits.append(("project-data", "课题数据留在课题目录"))
    lower = path.lower().split("/")
    if set(lower) & {"private-data", "private_data", "私有数据", "隐私数据"}:
        hits.append(("private-data", "私有数据目录"))
    secret_names = {".env", ".npmrc", ".pypirc", "credentials.json", "credentials", "secrets.json",
                    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"}
    if (name.lower() in secret_names or (name.lower().startswith(".env.")
            and name.lower() not in {".env.example", ".env.sample", ".env.template"})
            or PurePosixPath(path).suffix.lower() in {".pfx", ".p12", ".key"}):
        hits.append(("secret", "凭据或私钥文件名（不显示内容）"))
    content = "\n".join(added)
    if b"\0" not in head[:HEAD_BYTES]:
        content += "\n" + head[:HEAD_BYTES].decode("utf-8", "replace")
    if contains_secret(content):
        hits.append(("secret", "检测到密码、访问令牌或私钥（不显示内容）"))
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


def contains_secret(text: str) -> bool:
    """只返回是否命中，不向日志回显秘密；示例占位符可提交。"""
    if re.search(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----", text):
        return True
    if re.search(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,}|AKIA[A-Z0-9]{16})\b", text):
        return True
    pattern = r'''(?i)["']?\b(?:password|passwd|api[_-]?key|access[_-]?token|client[_-]?secret)["']?\s*[:=]\s*["']([^"'\r\n]*)["']'''
    for match in re.finditer(pattern, text):
        if text[:match.start()].rstrip().endswith("?"):
            continue  # JS ternary input type: secret ? "password" : "text"
        value = match.group(1).strip()
        if not value or value.upper() in {"REDACTED", "CHANGEME", "EXAMPLE", "NONE", "NULL"}:
            continue
        if value.startswith(("<", "${", "your_", "YOUR_")):
            continue
        return True
    return False


def assert_no_sensitive_changes(wiki_root: Path) -> None:
    """检查即将由 save 暂存的文件，防止秘密先进入本地 Git 历史。"""
    head = subprocess.run(["git", "-C", str(wiki_root), "rev-parse", "--verify", "-q", "HEAD"],
                          capture_output=True)
    tracked = (git(wiki_root, "diff", "--relative", "--name-only", "--diff-filter=ACMRT", "-z", "HEAD", "--", ".")
               if head.returncode == 0 else git(wiki_root, "ls-files", "--cached", "-z", "--", "."))
    untracked = git(wiki_root, "ls-files", "--others", "--exclude-standard", "-z", "--", ".")
    rules = Rules(sys.maxsize, (), (), (), (("abs-path", "**"), ("size", "**")))
    blocked = []
    for name in sorted(set(filter(None, (tracked + "\0" + untracked).split("\0")))):
        path = wiki_root / name
        if not path.is_file():
            continue
        hits = classify(name, 0, [], b"", rules)
        with path.open("rb") as stream:
            first = stream.read(4096)
            if b"\0" not in first:
                stream.seek(0)
                overlap = ""
                while chunk := stream.read(65536):
                    text = overlap + chunk.decode("utf-8", "replace")
                    if contains_secret(text):
                        hits.append(("secret", "检测到秘密"))
                        break
                    overlap = text[-4096:]
        if hits:
            blocked.append(name)
    if blocked:
        raise WikiError("save 拒绝将私有数据、密码或私钥写入 Git（不显示内容）：" + "、".join(blocked))


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


def _git_error(stderr) -> str:
    stderr.seek(0)
    return stderr.read(65536).decode("utf-8", "replace")


@contextmanager
def _cat_file_batch(repo: Path, option: str):
    """One request at a time avoids pipe deadlocks and whole-body captures."""
    with tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(["git", "-C", str(repo), "cat-file", option],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr)
        try:
            yield process
            process.stdin.close()
            if process.wait():
                raise WikiError(f"git cat-file {option} 失败: {_git_error(stderr)}")
        except OSError as error:
            raise WikiError(f"git cat-file {option} 读取失败") from error
        finally:
            # An interrupted/failed read may leave Git blocked writing a body.
            if process.poll() is None:
                process.kill()
            process.wait()
            with suppress(OSError):
                process.stdin.close()
            with suppress(OSError):
                process.stdout.close()


def _read_blob(process, sha: str, with_head: bool) -> tuple[int, bytes]:
    try:
        process.stdin.write((sha + "\n").encode("ascii"))
        process.stdin.flush()
        header = process.stdout.readline(256)
        fields = header.split()
        if (not header.endswith(b"\n") or len(fields) != 3 or fields[0] != sha.encode("ascii")
                or fields[1] != b"blob" or not fields[2].isdigit()):
            raise WikiError("git cat-file 返回无效或缺失的 blob 元数据")
        size = int(fields[2])
        head = b""
        if with_head:
            remaining = size
            while remaining:
                chunk = process.stdout.read(min(65536, remaining))
                if not chunk:
                    raise WikiError("git cat-file blob 内容不完整")
                if len(head) < HEAD_BYTES:
                    head += chunk[:HEAD_BYTES - len(head)]
                remaining -= len(chunk)
            if process.stdout.read(1) != b"\n":
                raise WikiError("git cat-file blob 结束符无效")
        return size, head
    except (OSError, ValueError) as error:
        raise WikiError("git cat-file 读取失败") from error


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
    # Spool first, so a failed git log can never be mistaken for a clean scan.
    # Both streams go to disk: no subprocess reader thread accumulates a patch.
    with tempfile.TemporaryFile() as patch, tempfile.TemporaryFile() as stderr:
        try:
            result = subprocess.run([
                "git", "-C", str(repo), "-c", "core.quotePath=false", "log", "--format=%x01%H",
                "--root", "--raw", "-p", "-U0", "--no-color", "--no-renames", "--no-abbrev",
                "--no-ext-diff", "--no-textconv", *rev_range.split(), "--"],
                stdout=patch, stderr=stderr, timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as error:
            raise WikiError(f"git log 超过 {TIMEOUT_SECONDS} 秒未结束") from error
        if result.returncode:
            raise WikiError(f"git log 失败: {_git_error(stderr)}")
        patch.seek(0)
        with io.TextIOWrapper(patch, encoding="utf-8", errors="replace") as lines, ExitStack() as stack:
            # Legacy head selection is by blob, across the entire range. A text
            # path sharing a code blob must receive that same head as before.
            code_blobs = set()
            in_commit, in_hunk = False, False
            for line in lines:
                if line.startswith("\x01"):
                    in_commit, in_hunk = True, False
                elif not in_commit:
                    continue
                elif line.startswith("diff --git "):
                    in_hunk = False
                elif in_hunk:
                    continue  # Bare CRs can expose colon/tab text inside a hunk.
                elif line.startswith(":") and "\t" in line:
                    fields, path = line.removesuffix("\n").split("\t", 1)
                    _, new_mode, _, sha, status = fields[1:].split()
                    name = PurePosixPath(_unquote(path))
                    if (status != "D" and new_mode != "160000"
                            and (name.suffix.lower() in CODE_SUFFIXES or name.name.upper().startswith("LICENSE"))):
                        code_blobs.add(sha)
                elif line.startswith("@@"):
                    in_hunk = True
            lines.seek(0)
            batches = {}

            def inspect(path, sha, added):
                code = sha in code_blobs
                option = "--batch" if code else "--batch-check"
                if option not in batches:
                    batches[option] = stack.enter_context(_cat_file_batch(repo, option))
                size, head = _read_blob(batches[option], sha, code)
                return classify(path, size, added, head, rules)

            return _scan_log(lines, inspect)


def _scan_log(lines, inspect) -> list[dict]:
    """Keep raw metadata per commit and added text for only the current file.

    Binary/mode-only changes may have no +++ target. Inspect them at commit end;
    emit findings in raw-entry order, just like the legacy in-memory parser.
    """
    findings = []
    commit, files, hits = None, {}, {}
    target, added, in_hunk = None, [], False

    def finish_file():
        nonlocal target, added, in_hunk
        if target is not None:
            hits[target] = inspect(target, files[target], added)
        target, added, in_hunk = None, [], False

    def finish_commit():
        finish_file()
        for path, sha in files.items():
            path_hits = hits[path] if path in hits else inspect(path, sha, [])
            for rule, detail in path_hits:
                finding = {"rule": rule, "path": path, "commit": commit, "detail": detail}
                if finding not in findings:
                    findings.append(finding)

    for raw_line in lines:
        line = raw_line.removesuffix("\n")
        if line.startswith("\x01"):
            finish_commit()
            commit, files, hits = line[1:], {}, {}
        elif commit is None:
            continue
        elif line.startswith("diff --git "):
            finish_file()
        elif in_hunk:
            if line.startswith("+") and target is not None:
                added.append(line[1:])
        elif line.startswith(":") and "\t" in line:
            fields, path = line.split("\t", 1)
            _, new_mode, _, new_sha, status = fields[1:].split()
            if status != "D" and new_mode != "160000":
                files[_unquote(path)] = new_sha
        elif line.startswith("+++ "):
            name = _unquote(line[4:].rstrip("\t"))
            target = name[2:] if name.startswith("b/") and name[2:] in files else None
        elif line.startswith("@@"):
            in_hunk = True
    finish_commit()
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
    """移除旧 GPL 排除托管块，源码默认入 Git；块外字节不动。"""
    path = wiki_root / ".gitignore"
    data = path.read_bytes() if path.is_file() else b""
    updated = IGNORE_BLOCK.sub(b"", data)
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
