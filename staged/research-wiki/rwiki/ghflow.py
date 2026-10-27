"""wiki.py gh：git 与 gh CLI 的薄封装、分支树命名、评审与合并门禁。

guard 与 protect-baseline 是纯本地命令，不做 gh 前置检查（D16）；其余子命令先 require_gh。
"""
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from . import push_guard, risk, writer_lock
from .config import read_json
from .errors import WikiError
from .process import run
from .store import git

GH_INSTALL = "https://cli.github.com/"
STAGE = r"P[0-5]|T\d+"
SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
SLUG_MAX = 40
KINDS = ("project", "ingest")
NAME_EXAMPLES = "合法示例：task/scp-wave3-P2-harmony、ingest/scp-wave3"
META_NAME = "rwiki-branches.json"
SHA = r"[0-9a-f]{40}"
REVIEW_MARKER = re.compile(rf"\s*<!-- codex-review: verdict=(pass|changes) sha=({SHA}) -->")
VERDICTS = {"pass": "通过", "changes": "需修改"}
MIGRATED_PREFIX = b"<!-- rwiki-migrated: "
PENDING_CONCLUSION = "（合并时填写：结论、PR、合并 SHA）"
LEGACY_MARKER = re.compile(r"<!-- rwiki-legacy: id=(\S+) -->")
DEFAULT_REPOS = {"dev": "jjd-wiki-dev", "vault": "jjd-wiki"}
LABELS = {"type:project": "1d76db", "type:ingest": "0e8a16", "type:code": "5319e7", "type:legacy": "bfdadc",
          **{f"stage:P{n}": "c5def5" for n in range(6)}, **{f"stage:T{n}": "c5def5" for n in range(1, 10)},
          "stage:legacy": "c5def5",
          "status:进行中": "fbca04", "status:待评审": "0052cc", "status:需修改": "d93f0b", "status:已验收": "0e8a16",
          "blocked:用户决定": "b60205", "blocked:本地验证": "b60205", "blocked:外部依赖": "b60205",
          "blocked:CI": "b60205",
          "risk:low": "c2e0c6", "risk:normal": "fef2c0", "risk:high": "e99695", "owner-approved": "5319e7"}
OWNER_LABEL = "owner-approved"
LABEL_DESCRIPTIONS = {"risk:low": "风险档 low：CI 通过即可合并（finish-task 写入，merge 时重算）",
                      "risk:normal": "风险档 normal：CI + 针对当前 head 的 Codex 评审（finish-task 写入，merge 时重算）",
                      "risk:high": "风险档 high：normal 的要求，按规则可能还需作者确认（finish-task 写入，merge 时重算）",
                      OWNER_LABEL: "只由作者在网页上添加"}
STATUS_LABELS = tuple(name for name in LABELS if name.startswith("status:"))
RISK_LABELS = tuple(f"risk:{tier}" for tier in risk.TIERS)
TIER_LINE = re.compile(r"^- 风险档：.*$", re.M)
ISSUE_FIELDS = "number,title,body,state,url,labels,milestone"
PR_FIELDS = "number,state,url,headRefName,baseRefName,headRefOid,reviews,comments,mergeCommit,labels"
NO_LOCAL_REPORT = "未运行：本 PR 不涉及仅本地运行的检查。"
WIKI_PY = Path(__file__).resolve().parents[1] / "wiki.py"
HOOK_MARK = "# rwiki pre-push hook：由 wiki.py gh install-hook / bootstrap 写入，不入库"
# hook 优先调用部署副本（tools/deploy.py 写入），不随主检出切分支或改坏而变。
DEPLOYED_SKILL = Path.home() / ".agents" / "skills" / "research-wiki"
DEPLOYED_ENV = "RWIKI_DEPLOYED_SKILL"
LEGACY_BRANCH = "legacy/master"
# 目录被占用时 git 自身的重试约几秒；超过这个时间就是挂起，不是慢。
WORKTREE_REMOVE_SECONDS = 120
REPO_FILES = (".gitignore", ".gitattributes", ".push-guard-allow")
DEPLOY_KEY_TITLE = "rwiki-vault-ci"
DEPLOY_SECRET = "DEV_DEPLOY_KEY"
# 远端保护：只要求经 PR 合并；CI 与 Codex 评审由 Merge_Gate（wiki.py gh merge）判定，本地门禁仍保留。
PROTECTION_BODY = {"required_status_checks": None, "enforce_admins": False,
                   "required_pull_request_reviews": {"required_approving_review_count": 0}, "restrictions": None}


# ---- 薄封装 ----

def gh(args: list[str], cwd: Path) -> str:
    # 解析为完整路径：Windows 上 CreateProcess 不按 PATHEXT 查找 gh.cmd。
    return run([shutil.which("gh"), *args], cwd).stdout


def gh_json(args: list[str], cwd: Path) -> object:
    # 真实 gh 在列表为空时（如没有 deploy key）输出空串而不是 []。
    out = gh(args, cwd)
    return json.loads(out) if out.strip() else []


def gh_body(args: list[str], body: str, cwd: Path) -> str:
    """正文经 --body-file 传递（多行与 HTML 注释不进命令行）；含本机绝对路径的正文不写入 GitHub。"""
    found = push_guard.find_abs_paths(body)
    if found:
        raise WikiError(f"正文含本机绝对路径，不能写入 GitHub: {' '.join(sorted(set(found)))}")
    handle, name = tempfile.mkstemp(suffix=".md")
    with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(body)
    try:
        return gh([*args, "--body-file", name], cwd)
    finally:
        os.unlink(name)


def number_of(url: str) -> int:
    return int(url.strip().rsplit("/", 1)[1])


def require_gh(cwd: Path) -> str:
    """gh 可执行且已认证，返回当前认证账号；不安装任何东西。"""
    if shutil.which("gh") is None:
        raise WikiError(f"未找到 gh CLI。请按 {GH_INSTALL} 安装，再运行 `gh auth login`；"
                        "本命令不会自动安装。")
    try:
        gh(["auth", "status"], cwd)
    except WikiError as error:
        raise WikiError(f"gh 未认证：请运行 `gh auth login`（安装说明见 {GH_INSTALL}）。\n{error}") from error
    return gh(["api", "user", "--jq", ".login"], cwd).strip()


def require_private(repo: Path) -> None:
    visibility = gh_json(["repo", "view", "--json", "visibility"], repo)["visibility"]
    if visibility != "PRIVATE":
        raise WikiError(f"远程仓库可见性为 {visibility}，只允许推送到 PRIVATE 仓库；已拒绝推送")


def push(repo: Path, branch: str, rules) -> None:
    """可见性 → Push_Guard 扫描本次范围 → git push -u origin。"""
    require_private(repo)
    local_sha = git(repo, "rev-parse", f"refs/heads/{branch}").strip()
    remote_sha = (git(repo, "for-each-ref", "--format=%(objectname)", f"refs/remotes/origin/{branch}").strip()
                  or "0" * len(local_sha))
    updates = [(f"refs/heads/{branch}", local_sha, f"refs/heads/{branch}", remote_sha)]
    findings = [finding for rev_range in push_guard.push_ranges(repo, "origin", updates)
                for finding in push_guard.scan(repo, rev_range, rules)]
    if findings:
        raise WikiError("Push_Guard 拦截推送：\n" + "\n".join(map(push_guard.format_finding, findings)))
    git(repo, "push", "-u", "origin", branch)


# ---- 命名（纯函数） ----

def _check_slug(value: str, what: str) -> None:
    if len(value) > SLUG_MAX or not re.fullmatch(SLUG, value):
        raise WikiError(f"{what}不合法: {value!r}；只允许小写字母、数字与单个连字符，"
                        f"不超过 {SLUG_MAX} 字符。{NAME_EXAMPLES}")


def long_branch(kind: str, name: str) -> str:
    if kind not in KINDS:
        raise WikiError(f"批次类型不合法: {kind!r}；只能是 project 或 ingest。{NAME_EXAMPLES}")
    _check_slug(name, "批次名")
    return f"{kind}/{name}"


def task_branch(batch: str, stage: str, topic: str) -> str:
    _check_slug(batch, "批次名")
    if not re.fullmatch(STAGE, stage):
        raise WikiError(f"阶段不合法: {stage!r}；只能是 P0–P5 或 T<数字>。{NAME_EXAMPLES}")
    _check_slug(topic, "主题")
    return f"task/{batch}-{stage}-{topic}"


def parse_task_branch(name: str) -> tuple[str, str, str]:
    match = re.fullmatch(rf"task/({SLUG})-({STAGE})-({SLUG})", name)
    if not match:
        raise WikiError(f"任务分支名不合法: {name!r}；格式 task/<批次>-<阶段>-<主题>。{NAME_EXAMPLES}")
    task_branch(*match.groups())
    return match.groups()


# ---- 分支元数据：<git-common-dir>/rwiki-branches.json（worktree 共享） ----

def meta_path(repo: Path) -> Path:
    return Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()) / META_NAME


def read_meta(repo: Path) -> dict:
    path = meta_path(repo)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def write_meta(repo: Path, meta: dict) -> None:
    meta_path(repo).write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8", newline="\n")


# ---- 评审与门禁（纯函数） ----

def render_review(verdict: str, sha: str, findings: list[str]) -> str:
    if verdict not in VERDICTS or not re.fullmatch(SHA, sha):
        raise WikiError(f"评审结论只能是 pass|changes，sha 必须是 40 位提交号: {verdict} {sha}")
    items = "".join(f"- {item}\n" for item in findings) or "（无）\n"
    return (f"<!-- codex-review: verdict={verdict} sha={sha} -->\n"
            f"## Codex 评审：{VERDICTS[verdict]}\n\n"
            f"评审提交：`{sha}`\n\n"
            f"### 问题\n\n{items}")


def parse_review_marker(text: str) -> tuple[str, str] | None:
    match = REVIEW_MARKER.match(text)
    return (match.group(1), match.group(2)) if match else None


def _when(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def head_pushed_at(timeline: list[dict], head: str, head_commit_date: str | None) -> datetime | None:
    """当前 head 被推送时间的估计：取 head_ref_force_pushed 的 created_at 与各 committed 事件提交者时间的最晚值。

    REST timeline 不记普通推送的时间，committed 事件只有提交者时间；timeline 里没有 head 的 committed 事件时
    补上 head 提交本身的 committer date。这是保守近似：所有已知时间取最晚（提交时间不晚于推送时间，
    所以它只可能偏早）；偏早的代价是“提交之后、推送之前”打的标签会被当作晚于推送，这类标签可能针对
    上一个 head。评审标记仍必须针对当前 head，不受这段空档影响。
    """
    times = [_when(event["created_at"]) for event in timeline if event.get("event") == "head_ref_force_pushed"]
    commits = [event for event in timeline if event.get("event") == "committed"]
    times += [_when(event["committer"]["date"]) for event in commits]
    if head not in {event.get("sha") for event in commits} and head_commit_date:
        times.append(_when(head_commit_date))
    return max(times, default=None)


def owner_approval(labels: list[str], timeline: list[dict], head: str,
                   head_commit_date: str | None) -> tuple[bool, str]:
    """作者确认：PR 上有 owner-approved 标签，且它最近一次 labeled 事件晚于当前 head 的推送时间。"""
    if OWNER_LABEL not in labels:
        return False, f"high 档需要作者确认：PR 上没有 {OWNER_LABEL} 标签（只由作者在网页上添加）"
    labeled = [_when(event["created_at"]) for event in timeline
               if event.get("event") == "labeled" and (event.get("label") or {}).get("name") == OWNER_LABEL]
    pushed = head_pushed_at(timeline, head, head_commit_date)
    if not labeled or pushed is None:
        return False, f"high 档需要作者确认：取不到 {OWNER_LABEL} 标签或当前 head 的时间，无法判断确认是否针对当前 head"
    if max(labeled) <= pushed:
        return False, (f"high 档需要作者确认：{OWNER_LABEL} 标签（{max(labeled).isoformat()}）不晚于当前 head 推送时间"
                       f"（{pushed.isoformat()}）：作者确认已失效，需作者在网页上移除后重新添加")
    return True, ""


def tier_summary(tier: str, reasons: list[str], limit: int = 3) -> str:
    shown = "；".join(reasons[:limit]) + (f" 等 {len(reasons)} 条" if len(reasons) > limit else "")
    return f"风险档 {tier}" + (f"：{shown}" if shown else "")


def gate_decision(checks: list[dict], entries: list[dict], head: str, tier: str = "normal",
                  tier_reasons: list[str] = (), owner: tuple[bool, str] | None = None) -> tuple[bool, list[str]]:
    """CI 全部 pass 或 skipping（至少一个 pass）；normal/high 还要按时间最新的 codex-review 标记为 pass 并针对
    当前 head；high 在规则要求作者确认时，owner 为 owner_approval() 的结果（None 表示不需要）。
    不通过时第一条原因写档位与命中规则。旧的三参数调用等价于 normal。"""
    if tier not in risk.TIERS:
        raise ValueError(f"风险档只能是 {'|'.join(risk.TIERS)}: {tier!r}")
    reasons = []
    if not checks:
        reasons.append("没有 CI 检查结果")
    elif all(check["bucket"] == "skipping" for check in checks):
        reasons.append("没有 CI 检查结果（全部检查为 skipping）")
    failing = [f"{check['name']}({check['bucket']})" for check in checks
               if check["bucket"] not in ("pass", "skipping")]
    if failing:
        reasons.append("CI 检查未全部通过: " + ", ".join(failing))
    markers = [marker for marker in (parse_review_marker(entry.get("body") or "") for entry in entries) if marker]
    if tier == "low":
        pass
    elif not markers:
        reasons.append("没有 Codex 评审回帖")
    else:
        verdict, sha = markers[-1]
        if sha != head:
            reasons.append(f"最新 Codex 评审针对 {sha}，当前 head 为 {head}：评审已失效")
        elif verdict != "pass":
            reasons.append("最新 Codex 评审结论为需修改")
    if tier == "high" and owner is not None and not owner[0]:
        reasons.append(owner[1])
    if reasons:
        reasons.insert(0, tier_summary(tier, list(tier_reasons)))
    return not reasons, reasons


def open_issues_blocking(issues: list[dict]) -> list[dict]:
    return [issue for issue in issues if issue["state"] != "CLOSED"]


# ---- Issue 正文与迁移标记（纯函数） ----

def task_marker(branch: str, batch: str, stage: str) -> str:
    return f"<!-- rwiki-task: branch={branch} batch={batch} stage={stage} -->"


def render_issue_body(marker: str, goal: str, criteria: list[str], evidence: list[dict],
                      conclusion: str = PENDING_CONCLUSION) -> str:
    """证据只写相对路径与 sha256；正文出现本机绝对路径时拒绝。"""
    rows = []
    for item in evidence:
        path = item["path"].replace("\\", "/")
        if push_guard.find_abs_paths(path) or path.startswith("/") or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
            raise WikiError(f"证据只能写相对路径与 64 位 sha256: {item}")
        rows.append(f"| {path.replace('|', '&#124;')} | {item['sha256']} |\n")
    body = (f"{marker}\n## 目标\n\n{goal}\n\n## 验收标准\n\n"
            + ("".join(f"- [ ] {line}\n" for line in criteria) or "- [ ] 待补\n")
            + "\n## 本地证据\n\n| 相对路径 | sha256 |\n|---|---|\n" + "".join(rows)
            + f"\n## 验收结论\n\n{conclusion}\n")
    found = push_guard.find_abs_paths(body)
    if found:
        raise WikiError(f"Issue 正文含本机绝对路径，不能写入 GitHub: {' '.join(sorted(set(found)))}")
    return body


def add_migrated_marker(data: bytes, url: str) -> bytes:
    if data.startswith(MIGRATED_PREFIX):
        return data
    return f"<!-- rwiki-migrated: issue={url} -->\n> 已迁移，停止维护：{url}\n\n".encode("utf-8") + data


def legacy_marker(item_id: str) -> str:
    return f"<!-- rwiki-legacy: id={item_id} -->"


def render_pr_body(refs: str, summary: list[str], local_report: str, protected: str) -> str:
    """按 .github/pull_request_template.md 的 6 个小节填写。"""
    return (f"## 关联 Issue\n{refs}\n"
            "## 改动摘要\n" + ("".join(f"- {line}\n" for line in summary) or "- 无\n")
            + "## 测试结果（CI）\n见本 PR 的 CI 检查；CI 未覆盖的内容写在下一栏。\n"
            f"## 本地专属验证\n{local_report.strip()}\n"
            f"## 受保护字节核验\n{protected}\n"
            "## 未完成项\n- 无\n")


def render_gate_block(head: str, reasons: list[str], plan: str | None) -> str:
    return (f"<!-- rwiki-gate: blocked sha={head} -->\n## 合并门禁未通过\n\n"
            + "".join(f"- {reason}\n" for reason in reasons)
            + f"\n### 修复计划\n\n{plan or '待补'}\n")


# ---- 仓库、检出与 GitHub 对象（先查后建） ----

def main_checkout(path: Path) -> Path:
    """主检出：worktree 与主检出共享 git-common-dir，其父目录即主检出。"""
    return Path(git(path, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()).parent


def toplevel(path: Path) -> Path:
    return Path(git(path, "rev-parse", "--show-toplevel").strip())


def repo_root(cfg, key: str) -> Path:
    if key == "vault":
        return Path(cfg.github["vault_root"]) if cfg.github.get("vault_root") else main_checkout(cfg.wiki_root)
    if not cfg.github.get("dev_root"):
        raise WikiError("config.json 的 github.dev_root 未设置（开发仓库主检出的路径）")
    return Path(cfg.github["dev_root"])


def configured_repos(cfg) -> list[tuple[str, Path]]:
    return [("vault", repo_root(cfg, "vault"))] + ([("dev", repo_root(cfg, "dev"))] if cfg.github.get("dev_root") else [])


def wiki_prefix(cfg, repo: Path) -> str | None:
    """知识库子树相对检出根的路径；知识库不属于该仓库时为 None。"""
    wiki = cfg.wiki_root.resolve()
    if main_checkout(wiki).resolve() != main_checkout(repo).resolve():
        return None
    return wiki.relative_to(toplevel(wiki).resolve()).as_posix()


def checkout_rules(cfg, checkout: Path) -> push_guard.Rules:
    """按本检出中的知识库推导 GPL 目录（worktree 用自己的知识库副本）。"""
    prefix = wiki_prefix(cfg, checkout)
    local = replace(cfg, wiki_root=checkout / prefix) if prefix is not None else cfg
    return push_guard.load_rules(local, checkout)


def tracked_changes(repo: Path) -> list[str]:
    """相对 HEAD 未提交的已跟踪改动（含已暂存）。"""
    text = git(repo, "-c", "core.quotePath=false", "diff", "HEAD", "--name-only", "--no-renames", "-z")
    return [path for path in text.split("\0") if path]


def branch_exists(repo: Path, branch: str) -> bool:
    return bool(git(repo, "branch", "--list", branch).strip())


def current_branch(repo: Path) -> str:
    return git(repo, "branch", "--show-current").strip()


def find_batch(cfg, batch: str) -> tuple[str, Path, dict]:
    for key, repo in configured_repos(cfg):
        info = read_meta(repo).get("batches", {}).get(batch)
        if info:
            return key, repo, info
    raise WikiError(f"批次 {batch} 不存在：先运行 wiki.py gh start-batch <project|ingest> {batch} --title … --repo …")


def milestones(repo: Path) -> list[dict]:
    return gh_json(["api", "-X", "GET", "repos/{owner}/{repo}/milestones",
                    "-f", "state=all", "-f", "per_page=100"], repo)


def create_milestone(repo: Path, title: str, description: str) -> dict:
    return gh_json(["api", "repos/{owner}/{repo}/milestones",
                    "-f", f"title={title}", "-f", f"description={description}"], repo)


def ensure_milestone(repo: Path, title: str, description: str) -> dict:
    for milestone in milestones(repo):
        if milestone["title"] == title:
            return milestone
    return create_milestone(repo, title, description)


def ensure_labels(repo: Path, names: list[str]) -> None:
    existing = {label["name"] for label in gh_json(["label", "list", "--limit", "500", "--json", "name"], repo)}
    for name in names:
        if name not in existing:
            gh(["label", "create", name, "--color", LABELS.get(name, "c5def5"), *description_args(name), "--force"],
               repo)


def description_args(name: str) -> list[str]:
    return ["--description", LABEL_DESCRIPTIONS[name]] if name in LABEL_DESCRIPTIONS else []


def issue_list(repo: Path, *args: str) -> list[dict]:
    return gh_json(["issue", "list", "--state", "all", "--limit", "1000", "--json", ISSUE_FIELDS, *args], repo)


def label_args(labels: list[str]) -> list[str]:
    return [part for label in labels for part in ("--label", label)]


def set_status(repo: Path, issue: int, status: str) -> None:
    labels = [label["name"] for label in gh_json(["issue", "view", str(issue), "--json", "labels"], repo)["labels"]]
    stale = [name for name in labels if name in STATUS_LABELS and name != status]
    if status in labels and not stale:
        return
    ensure_labels(repo, [status])
    gh(["issue", "edit", str(issue), "--add-label", status,
        *[part for name in stale for part in ("--remove-label", name)]], repo)


def pr_checks(repo: Path, pr: int) -> list[dict]:
    """gh pr checks --json 只导出 JSON 并退出 0（失败与等待中体现在 bucket，退出码 1/8 只用于表格输出）；
    没有检查时报错退出 1、stdout 为空，这里得到 []，由门禁判为“没有 CI 检查结果”。"""
    result = subprocess.run([shutil.which("gh"), "pr", "checks", str(pr), "--json", "name,bucket"], cwd=repo,
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    return json.loads(result.stdout) if result.stdout.strip() else []


def ignored_paths(repo: Path, paths: list[str]) -> set[str]:
    """按忽略规则判定（--no-index：已跟踪的文件同样判定）。"""
    result = subprocess.run(["git", "-C", str(repo), "-c", "core.quotePath=false", "check-ignore", "--no-index",
                             "--stdin", "-z"], input="".join(f"{path}\0" for path in paths).encode("utf-8"),
                            capture_output=True)
    return set(filter(None, result.stdout.decode("utf-8").split("\0")))


# ---- worktree 的 GPL 目录联接（D13） ----

def managed_gpl_dirs(wiki_root: Path) -> list[str]:
    """知识库 .gitignore 中 GPL 托管块列出的目录（相对 wiki_root，无首尾 `/`）。"""
    path = wiki_root / ".gitignore"
    match = push_guard.IGNORE_BLOCK.search(path.read_bytes()) if path.is_file() else None
    if not match:
        return []
    lines = match.group(0).decode("utf-8").splitlines()[1:-1]
    return [line.strip().strip("/") for line in lines if line.strip()]


def is_junction(path: Path) -> bool:
    return os.path.lexists(path) and bool(os.lstat(path).st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def link_gpl_dirs(main: Path, checkout: Path, prefix: str) -> list[str]:
    """为主检出中存在的 GPL 目录在 worktree 里建目录联接，返回联接相对检出根的路径。"""
    linked = []
    for directory in managed_gpl_dirs(main / prefix):
        relative = f"{prefix}/{directory}" if prefix != "." else directory
        target, link = main / relative, checkout / relative
        if target.is_dir() and not os.path.lexists(link):
            link.parent.mkdir(parents=True, exist_ok=True)
            run(["cmd", "/c", "mklink", "/J", str(link), str(target)], link.parent)
        if is_junction(link):
            linked.append(relative)
    return linked


def unlink_gpl_dirs(checkout: Path, junctions: list[str]) -> None:
    """逐个删除联接本身：先确认是 reparse 点，rmdir 不带 /s，联接目标的内容不受影响。"""
    for relative in junctions:
        link = checkout / relative
        if not os.path.lexists(link):
            continue
        if not is_junction(link):
            raise WikiError(f"{link} 不是目录联接，拒绝删除；请人工核对后再移除 worktree")
        run(["cmd", "/c", "rmdir", str(link)], checkout)


def registered_worktree(repo: Path, path: Path) -> bool:
    listed = [Path(line[len("worktree "):]).resolve()
              for line in git(repo, "worktree", "list", "--porcelain").splitlines() if line.startswith("worktree ")]
    return path.resolve() in listed


def live_checkout(main: Path, checkout: Path) -> bool:
    """检出仍是可用的 git 工作树；中断的 worktree remove 可能只留下登记、空目录或残留子目录。"""
    return checkout.is_dir() and (checkout / ".git").exists() and (checkout == main
                                                                  or registered_worktree(main, checkout))


def occupied_error(checkout: Path, pr: int, detail: str) -> WikiError:
    return WikiError(f"worktree 目录 {checkout} 删不掉（多半被终端、编辑器或其他进程占用）：\n{detail}\n"
                     f"请关闭占用该目录的终端或编辑器后重跑 wiki.py gh merge {pr}；本地分支已保留，重跑会补完收尾。")


def remove_worktree(main: Path, checkout: Path, pr: int) -> None:
    """非交互地 git worktree remove：stdin 为空设备，GIT_ASK_YESNO=false 让 Git for Windows 的
    “Should I try again? (y/n)” 直接答 no。失败时不 --force、不递归删除，只报错。"""
    try:
        result = subprocess.run(["git", "-C", str(main), "worktree", "remove", str(checkout)],
                                stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=WORKTREE_REMOVE_SECONDS,
                                env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_ASK_YESNO": "false"})
    except subprocess.TimeoutExpired:
        raise occupied_error(checkout, pr, f"git worktree remove 超过 {WORKTREE_REMOVE_SECONDS} 秒未结束") from None
    if result.returncode == 0:
        return
    if (checkout / ".git").exists():
        # git 在删除前就拒绝了（如有未提交或未跟踪的文件），目录原样保留。
        raise WikiError(f"git 拒绝移除 worktree {checkout}：\n{result.stderr.strip()}\n"
                        f"请提交或移走这些文件后重跑 wiki.py gh merge {pr}；本地分支已保留。")
    raise occupied_error(checkout, pr, result.stderr.strip())


def remove_empty_dirs(path: Path) -> None:
    """自底向上只删空目录（rmdir 不删非空目录）；不进入、不删除目录联接或符号链接。"""
    if path.is_symlink() or is_junction(path) or not path.is_dir():
        return
    for child in path.iterdir():
        remove_empty_dirs(child)
    try:
        path.rmdir()
    except OSError:
        pass


def merged_into(repo: Path, branch: str, sha: str) -> bool:
    return subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", branch, sha],
                          stdin=subprocess.DEVNULL, capture_output=True).returncode == 0


# ---- 子命令 ----

def start_batch(cfg, kind: str, name: str, title: str, repo_key: str) -> dict:
    """从 origin/main 建长期分支 → 同名 Milestone → 推送（经 guard）→ 元数据。"""
    branch = long_branch(kind, name)
    repo = repo_root(cfg, repo_key)
    require_gh(repo)
    git(repo, "fetch", "origin")
    if not branch_exists(repo, branch):
        git(repo, "branch", "--no-track", branch, "origin/main")
    milestone = ensure_milestone(repo, branch, title)
    push(repo, branch, checkout_rules(cfg, repo))
    meta = read_meta(repo)
    meta.setdefault("batches", {})[name] = {**meta.get("batches", {}).get(name, {}), "kind": kind, "branch": branch,
                                            "milestone": milestone["number"], "title": title, "repo": repo_key}
    write_meta(repo, meta)
    return {"batch": name, "branch": branch, "milestone": milestone["title"], "repo": repo_key}


def ensure_task_issue(repo: Path, branch: str, batch: str, stage: str, title: str, milestone: str,
                      labels: list[str]) -> dict:
    marker = task_marker(branch, batch, stage)
    for issue in issue_list(repo):
        if marker in (issue["body"] or ""):
            return issue
    ensure_labels(repo, labels)
    url = gh_body(["issue", "create", "--title", title, "--milestone", milestone, *label_args(labels)],
                  render_issue_body(marker, title, [], []), repo)
    return {"number": number_of(url), "url": url.strip()}


def start_task(cfg, batch: str, stage: str, topic: str, title: str, worktree: bool) -> dict:
    """建 Issue → 主检出 git switch -c（仅知识库改动随行）或 --worktree → 元数据与写入锁。"""
    branch = task_branch(batch, stage, topic)
    agent = os.environ.get("RWIKI_AGENT")
    if not agent:
        raise WikiError("start-task 需要环境变量 RWIKI_AGENT（执行写入的 Agent 名）")
    repo_key, repo, info = find_batch(cfg, batch)
    require_gh(repo)
    prefix = wiki_prefix(cfg, repo)
    on_branch = not worktree and current_branch(repo) == branch
    if not worktree and not on_branch:
        blocked = [path for path in tracked_changes(repo)
                   if prefix is None or not (prefix == "." or path.startswith(prefix + "/"))]
        if blocked:
            raise WikiError("主检出有知识库之外的未提交改动，不能随行到任务分支；请先提交它们或改用 --worktree：\n"
                            + "\n".join(blocked))
    if not worktree:
        writer_lock.acquire(repo, agent, branch)
    labels = ["type:code" if repo_key == "dev" else f"type:{info['kind']}", f"stage:{stage}", "status:进行中"]
    issue = ensure_task_issue(repo, branch, batch, stage, title, info["branch"], labels)
    git(repo, "fetch", "origin")
    base = f"origin/{info['branch']}"
    junctions = []
    if worktree:
        if not cfg.github.get("worktree_root"):
            raise WikiError("config.json 的 github.worktree_root 未设置（--worktree 的存放目录）")
        checkout = Path(cfg.github["worktree_root"]) / branch.replace("/", "__")
        if not registered_worktree(repo, checkout):
            git(repo, "worktree", "add", *([str(checkout), branch] if branch_exists(repo, branch)
                                           else ["--no-track", "-b", branch, str(checkout), base]))
        if prefix is not None:
            junctions = link_gpl_dirs(repo, checkout, prefix)
        writer_lock.acquire(checkout, agent, branch)
    else:
        checkout = repo
        if not on_branch:
            git(repo, "switch", *([branch] if branch_exists(repo, branch) else ["--no-track", "-c", branch, base]))
    meta = read_meta(repo)
    tasks = meta.setdefault("tasks", {})
    tasks[branch] = {**tasks.get(branch, {}), "batch": batch, "stage": stage, "topic": topic, "title": title,
                     "issue": issue["number"], "repo": repo_key, "worktree": str(checkout) if worktree else None,
                     "junctions": junctions}
    write_meta(repo, meta)
    result = {"branch": branch, "issue": issue["number"], "url": issue["url"], "checkout": str(checkout)}
    if worktree and prefix is not None:
        result["RWIKI_WIKI_ROOT"] = str(checkout / prefix)
    return result


def protected_status(cfg, checkout: Path) -> str:
    prefix = wiki_prefix(cfg, checkout)
    if prefix is None or not (checkout / prefix / push_guard.BASELINE_FILE).is_file():
        return "不适用：本仓库没有作者块字节基准。"
    problems = push_guard.check_baseline(checkout / prefix)
    return "`wiki.py gh protect-baseline --check`：" + ("OK" if not problems else "\n" + "\n".join(
        f"- {line}" for line in problems))


def has_commit(repo: Path, sha: str) -> bool:
    return subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{sha}^{{commit}}"],
                          stdin=subprocess.DEVNULL, capture_output=True).returncode == 0


def fetch_head(repo: Path, view: dict) -> str:
    """PR 的 headRefOid 本地可能没有：依次 git fetch origin <head 分支>、git fetch origin <sha>。"""
    head = view["headRefOid"]
    for ref in (view["headRefName"], head):
        if has_commit(repo, head):
            return head
        subprocess.run(["git", "-C", str(repo), "fetch", "-q", "origin", ref], stdin=subprocess.DEVNULL,
                       capture_output=True)
    if not has_commit(repo, head):
        raise WikiError(f"取不到 PR head 提交 {head}（按分支 {view['headRefName']} 与按 sha 取回都失败），不能判风险档")
    return head


def pr_tier(repo: Path, base_branch: str, head: str) -> tuple[str, list[str], dict]:
    """规则读 base 分支当前提交（origin/<base>，调用前已 fetch），PR 改不了；改动范围 origin/<base>...<head>
    （merge-base 语义，与 GitHub PR diff 一致）。"""
    base = f"origin/{base_branch}"
    rules = risk.load_rules(repo, base)
    tier, reasons = risk.risk_tier(risk.changed_paths(repo, f"{base}...{head}"), rules)
    return tier, reasons, rules


def tier_line(tier: str, reasons: list[str], limit: int = 3) -> str:
    more = f" 等 {len(reasons)} 条" if len(reasons) > limit else ""
    return f"风险档：{tier}（{'；'.join(reasons[:limit])}{more}）"


def sync_pr_tier(repo: Path, pr: int, tier: str, line: str) -> None:
    """PR 正文的风险档行与 risk:* 标签对齐当前档位；已一致时不写。标签只供查看，merge 会重算。"""
    view = gh_json(["pr", "view", str(pr), "--json", "body,labels"], repo)
    body = view.get("body") or ""
    updated = TIER_LINE.sub(lambda _: f"- {line}", body, count=1)
    if updated != body:
        gh_body(["pr", "edit", str(pr)], updated, repo)
    labels = {label["name"] for label in view.get("labels") or []}
    wanted = f"risk:{tier}"
    stale = [name for name in RISK_LABELS if name in labels and name != wanted]
    if wanted in labels and not stale:
        return
    ensure_labels(repo, [wanted])
    gh(["pr", "edit", str(pr), "--add-label", wanted, *[part for name in stale for part in ("--remove-label", name)]],
       repo)


def pr_owner_approval(repo: Path, pr: int, view: dict) -> tuple[bool, str]:
    pages = gh_json(["api", f"repos/{{owner}}/{{repo}}/issues/{pr}/timeline?per_page=100", "--paginate", "--slurp"],
                    repo)
    timeline = [event for page in pages for event in page]
    head = view["headRefOid"]
    labels = [label["name"] for label in view.get("labels") or []]
    return owner_approval(labels, timeline, head, git(repo, "show", "-s", "--format=%cI", head).strip())


def finish_task(cfg, checkout: Path, local_report: Path | None) -> dict:
    """拒绝未提交的已跟踪改动 → 推送（经 guard）→ PR（base 为长期分支）→ 风险档标签与正文行 → status:待评审。"""
    branch = current_branch(checkout)
    parse_task_branch(branch)
    meta = read_meta(checkout)
    task = meta.get("tasks", {}).get(branch)
    if task is None:
        raise WikiError(f"任务分支 {branch} 没有分支元数据，请用 wiki.py gh start-task 创建")
    long = meta["batches"][task["batch"]]["branch"]
    require_gh(checkout)
    changes = tracked_changes(checkout)
    if changes:
        raise WikiError("有未提交的已跟踪改动，先提交（知识库经 wiki.py save）再 finish-task：\n" + "\n".join(changes))
    push(checkout, branch, checkout_rules(cfg, checkout))
    git(checkout, "fetch", "origin")
    tier, tier_reasons, _ = pr_tier(checkout, long, branch)
    line = tier_line(tier, tier_reasons)
    live = [pr for pr in gh_json(["pr", "list", "--head", branch, "--state", "all", "--json", "number,state,url"],
                                 checkout) if pr["state"] in ("OPEN", "MERGED")]
    if live:
        pr = live[0]
    else:
        summary = [line, *git(checkout, "log", "--reverse", "--format=%s", f"origin/{long}..{branch}").splitlines()]
        report = local_report.read_text(encoding="utf-8") if local_report else NO_LOCAL_REPORT
        body = render_pr_body(f"Refs #{task['issue']}", summary, report, protected_status(cfg, checkout))
        url = gh_body(["pr", "create", "--base", long, "--head", branch, "--title", task["title"]], body, checkout)
        pr = {"number": number_of(url), "url": url.strip()}
    if pr.get("state") != "MERGED":
        sync_pr_tier(checkout, pr["number"], tier, line)
    set_status(checkout, task["issue"], "status:待评审")
    meta = read_meta(checkout)
    meta["tasks"][branch]["pr"] = pr["number"]
    write_meta(checkout, meta)
    return {"branch": branch, "pr": pr["number"], "url": pr["url"], "issue": task["issue"]}


def review(cfg, checkout: Path, pr: int, verdict: str, findings: Path) -> dict:
    """针对 PR 当前 head 回帖 codex-review 标记（COMMENT 类型 review），并更新 Issue 状态标签。"""
    require_gh(checkout)
    view = gh_json(["pr", "view", str(pr), "--json", "headRefOid,headRefName"], checkout)
    items = [line.strip().removeprefix("- ").strip()
             for line in findings.read_text(encoding="utf-8").splitlines() if line.strip()]
    gh_body(["pr", "review", str(pr), "--comment"], render_review(verdict, view["headRefOid"], items), checkout)
    task = read_meta(checkout).get("tasks", {}).get(view["headRefName"])
    if task:
        set_status(checkout, task["issue"], "status:待评审" if verdict == "pass" else "status:需修改")
    return {"pr": pr, "sha": view["headRefOid"], "verdict": verdict}


def fast_forward_main(main: Path) -> None:
    """快进本地 main 到 origin/main；不用 pull（受 branch.main.merge 等配置影响，曾报“multiple branches”）。"""
    git(main, "fetch", "origin")
    git(main, "merge", "--ff-only", "origin/main")


def after_task_merge(main: Path, meta: dict, branch: str, pr: int, sha: str) -> None:
    task = meta["tasks"][branch]
    issue = gh_json(["issue", "view", str(task["issue"]), "--json", "state,body"], main)
    if issue["state"] != "CLOSED":
        conclusion = f"已验收：合并于 #{pr} （{sha}）"
        if PENDING_CONCLUSION in issue["body"]:
            gh_body(["issue", "edit", str(task["issue"])], issue["body"].replace(PENDING_CONCLUSION, conclusion), main)
        set_status(main, task["issue"], "status:已验收")
        gh(["issue", "close", str(task["issue"]), "--comment", conclusion], main)
    # 每步先查后做：任何一步中断后重跑 merge 都从当前状态补完。
    checkout = Path(task["worktree"]) if task.get("worktree") else main
    if live_checkout(main, checkout):
        if (writer_lock.read_lock(checkout) or {}).get("branch") == branch:
            writer_lock.release(checkout)
        if task.get("worktree"):
            unlink_gpl_dirs(checkout, task.get("junctions", []))
            remove_worktree(main, checkout, pr)
    elif task.get("worktree"):
        # 上次 worktree remove 半途中断：目录已删或已不是 git 工作树。锁随 .git 一起没了；
        # 残留的 GPL 联接仍按 reparse 点逐个 rmdir（不带 /s），再清登记与空目录。
        git(main, "worktree", "prune")
        if checkout.is_dir():
            unlink_gpl_dirs(checkout, task.get("junctions", []))
        remove_empty_dirs(checkout)
        if os.path.lexists(checkout):
            raise occupied_error(checkout, pr, "上次移除 worktree 后目录仍有残留（被占用或非空）；若关闭占用后仍失败，"
                                               "请核对目录内容（其中的目录联接只用不带 /s 的 rmdir 删除）")
    if not task.get("worktree") and current_branch(main) == branch:
        git(main, "switch", "main")
        fast_forward_main(main)
    if branch_exists(main, branch):
        if merged_into(main, branch, sha):
            git(main, "branch", "-D", branch)
        else:
            print(f"提示：本地分支 {branch} 不是合并提交 {sha} 的祖先（有未合并的提交或合并提交未取回），"
                  "未删除；请人工核对后再处理该分支", file=sys.stderr)
    task.update(state="merged", pr=pr, merge_sha=sha)


def after_batch_merge(main: Path, meta: dict, branch: str) -> None:
    for milestone in milestones(main):
        if milestone["title"] == branch and milestone["state"] == "open":
            gh(["api", "-X", "PATCH", f"repos/{{owner}}/{{repo}}/milestones/{milestone['number']}",
                "-f", "state=closed"], main)
    if current_branch(main) == branch:
        git(main, "switch", "main")
    if branch_exists(main, branch):
        git(main, "branch", "-D", branch)
    if current_branch(main) == "main":
        fast_forward_main(main)
    for info in meta.get("batches", {}).values():
        if info["branch"] == branch:
            info["state"] = "merged"


def merge(cfg, checkout: Path, pr: int, plan: str | None) -> dict:
    """按风险档判门禁：low 只要 CI；normal 再要最新 codex-review 针对当前 head 且为 pass；high 再按规则要作者确认。
    通过才合并；已合并时只做合并后步骤（tier 为 None）。"""
    main = main_checkout(checkout)
    require_gh(main)
    view = gh_json(["pr", "view", str(pr), "--json", PR_FIELDS], main)
    if view["state"] not in ("OPEN", "MERGED"):
        raise WikiError(f"PR #{pr} 状态为 {view['state']}，不能合并")
    tier = None
    if view["state"] == "OPEN":
        # 档位按 base 上的规则重算，不信 PR 上的 risk:* 标签。
        git(main, "fetch", "origin")
        head = fetch_head(main, view)
        tier, tier_reasons, rules = pr_tier(main, view["baseRefName"], head)
        owner = pr_owner_approval(main, pr, view) if tier == "high" and rules["high_requires_owner"] else None
        entries = sorted(view["reviews"] + view["comments"],
                         key=lambda entry: entry.get("submittedAt") or entry.get("createdAt") or "")
        passed, reasons = gate_decision(pr_checks(main, pr), entries, head, tier, tier_reasons, owner)
        if not passed:
            body = render_gate_block(head, reasons, plan)
            if not view["comments"] or view["comments"][-1]["body"] != body:
                gh_body(["pr", "comment", str(pr)], body, main)
            raise WikiError(f"PR #{pr} 未通过合并门禁，保持未合并：\n" + "\n".join(f"- {reason}" for reason in reasons))
        # 带 --repo 时 gh 只删远端分支、不动本地检出；本地分支与 worktree 由下面的合并后步骤处理。
        name = gh_json(["repo", "view", "--json", "nameWithOwner"], main)["nameWithOwner"]
        gh(["pr", "merge", str(pr), "--merge", "--match-head-commit", head, "--delete-branch", "--repo", name], main)
        view = gh_json(["pr", "view", str(pr), "--json", PR_FIELDS], main)
    sha = view["mergeCommit"]["oid"]
    branch = view["headRefName"]
    git(main, "fetch", "origin", "--prune")
    meta = read_meta(main)
    if branch in meta.get("tasks", {}):
        after_task_merge(main, meta, branch, pr, sha)
    elif branch.startswith(tuple(f"{kind}/" for kind in KINDS)):
        after_batch_merge(main, meta, branch)
    write_meta(main, meta)
    return {"pr": pr, "merged": True, "merge_sha": sha, "branch": branch, "base": view["baseRefName"], "tier": tier}


def close_batch(cfg, batch: str) -> dict:
    """Milestone 内 Issue 全部关闭才建长期分支 → main 的 PR，正文列出全部 Issue。"""
    _, repo, info = find_batch(cfg, batch)
    require_gh(repo)
    issues = gh_json(["issue", "list", "--milestone", info["branch"], "--state", "all", "--limit", "1000",
                      "--json", "number,title,state"], repo)
    blocking = open_issues_blocking(issues)
    if blocking:
        raise WikiError(f"Milestone {info['branch']} 仍有未关闭 Issue，拒绝创建到 main 的 PR：\n"
                        + "\n".join(f"#{issue['number']} {issue['title']}" for issue in blocking))
    existing = gh_json(["pr", "list", "--head", info["branch"], "--base", "main", "--state", "open",
                        "--json", "number,url"], repo)
    if existing:
        pr = existing[0]
    else:
        refs = f"Milestone {info['branch']}：\n" + "".join(
            f"- #{issue['number']} {issue['title']}\n" for issue in sorted(issues, key=lambda item: item["number"]))
        body = render_pr_body(refs.rstrip("\n"), [f"合并 {info['branch']}（{info['title']}）到 main"], NO_LOCAL_REPORT,
                              protected_status(cfg, repo))
        url = gh_body(["pr", "create", "--base", "main", "--head", info["branch"],
                       "--title", f"{info['branch']}：{info['title']}"], body, repo)
        pr = {"number": number_of(url), "url": url.strip()}
    return {"batch": batch, "pr": pr["number"], "url": pr["url"], "issues": sorted(i["number"] for i in issues)}


def migrate_legacy(cfg, mapping: Path, dry_run: bool) -> dict:
    """按 legacy-map.json 幂等建 Issue（rwiki-legacy 标记去重），状态与映射一致；非 dry-run 时给原文件加迁移标记。"""
    data = read_json(mapping)
    entries = [("item", item) for item in data.get("items", [])] + [("gap", gap) for gap in data.get("gaps", [])]
    repos = {key: repo_root(cfg, key) for key in sorted({entry["repo"] for _, entry in entries})}
    if repos:
        require_gh(next(iter(repos.values())))
    existing = {key: {match.group(1): issue for issue in issue_list(repo)
                      for match in [LEGACY_MARKER.search(issue["body"] or "")] if match}
                for key, repo in repos.items()}
    report = []
    for kind, entry in entries:
        closed = kind == "item" and entry["state"] == "closed"
        issue = existing[entry["repo"]].get(entry["id"])
        if issue is None:
            action = "create"
        elif closed and issue["state"] != "CLOSED":
            action = "close"
        elif not closed and issue["state"] == "CLOSED":
            action = "reopen"
        else:
            action = "none"
        report.append({"id": entry["id"], "repo": entry["repo"], "action": action,
                       "issue": issue["number"] if issue else None, "state": "closed" if closed else "open"})
    if dry_run:
        return {"dry_run": True, "entries": report, "marked": []}
    for key in sorted({line["repo"] for line in report if line["action"] != "none"}):
        ensure_labels(repos[key], ["type:legacy", "stage:legacy", "status:进行中", "status:已验收"])
    titles = {}
    marked = []
    for (kind, entry), line in zip(entries, report):
        repo, action = repos[entry["repo"]], line["action"]
        closed = line["state"] == "closed"
        issue = existing[entry["repo"]].get(entry["id"])
        status = "status:已验收" if closed else "status:进行中"
        if action == "create":
            if kind == "item":
                goal = entry["title"] + "\n\n原任务书：" + "、".join(entry.get("files", []))
                body = render_issue_body(legacy_marker(entry["id"]), goal, [], entry.get("evidence", []),
                                         (entry.get("conclusion") or PENDING_CONCLUSION) if closed
                                         else PENDING_CONCLUSION)
                milestone = []
            else:
                body = render_issue_body(legacy_marker(entry["id"]), entry.get("body", entry["title"]), [],
                                         entry.get("evidence", []))
                known = titles.setdefault(entry["repo"], {item["title"] for item in milestones(repo)})
                if entry["milestone"] not in known:
                    create_milestone(repo, entry["milestone"], "遗留缺口迁移")
                    known.add(entry["milestone"])
                milestone = ["--milestone", entry["milestone"]]
            url = gh_body(["issue", "create", "--title", entry["title"], *milestone,
                           *label_args(["type:legacy", "stage:legacy", status])], body, repo)
            issue = {"number": number_of(url), "url": url.strip()}
            line["issue"] = issue["number"]
            if closed:
                gh(["issue", "close", str(issue["number"])], repo)
        elif action in ("close", "reopen"):
            gh(["issue", action, str(issue["number"])], repo)
            set_status(repo, issue["number"], status)
        if kind == "item":
            for relative in entry.get("files", []):
                path = repo / relative
                original = path.read_bytes()
                updated = add_migrated_marker(original, issue["url"])
                if updated != original:
                    path.write_bytes(updated)
                    marked.append(f"{entry['repo']}:{relative}")
    return {"dry_run": dry_run, "entries": report, "marked": marked}


# ---- preflight ----

def snapshot_files(repo: Path) -> list[str]:
    """过滤后的当前工作区：已跟踪与未忽略的未跟踪文件，去掉命中忽略规则的已跟踪文件。"""
    def listing(*args):
        return set(filter(None, git(repo, "-c", "core.quotePath=false", "ls-files", "-z", *args).split("\0")))

    files = (listing("-c") - listing("-c", "-i", "--exclude-standard")) | listing("-o", "--exclude-standard")
    return sorted(path for path in files if (repo / path).is_file())


def scan_snapshot(repo: Path, files: list[str], rules: push_guard.Rules) -> list[dict]:
    findings = []
    for path in files:
        data = (repo / path).read_bytes()
        lines = data.decode("utf-8", "replace").splitlines()
        for rule, detail in push_guard.classify(path, len(data), lines, data[:push_guard.HEAD_BYTES], rules):
            findings.append({"rule": rule, "path": path, "commit": "（工作区快照）", "detail": detail})
    return findings


def remote_status(repo: Path, name: str) -> dict:
    try:
        visibility = gh_json(["repo", "view", name, "--json", "visibility"], repo)["visibility"]
    except WikiError:
        return {"name": name, "exists": False, "visibility": None, "protection": None}
    try:
        gh(["api", f"repos/{name}/branches/main/protection"], repo)
        protection = "github"
    except WikiError as error:
        # 403：套餐不支持分支保护 → 本地门禁；404：可用但未配置（或 main 尚未推送）。
        protection = "local" if "HTTP 403" in str(error) else "github"
    return {"name": name, "exists": True, "visibility": visibility, "protection": protection}


def pending_push(repo: Path, key: str, rules: push_guard.Rules) -> dict:
    """首推前：dev 列出将重放的提交，vault 统计快照；已有远端时为尚未推送的提交。"""
    remotes = git(repo, "remote").split()
    if "origin" in remotes and git(repo, "for-each-ref", "--format=%(objectname)", "refs/remotes/origin/main").strip():
        rev_range = "HEAD --not --remotes=origin"
        commits = git(repo, "log", "--reverse", "--format=%H %s", *rev_range.split()).splitlines()
        return {"mode": "incremental", "range": rev_range, "commits": commits,
                "guard": push_guard.scan(repo, rev_range, rules)}
    if key == "dev":
        source = "main" if branch_exists(repo, "main") else legacy_source(repo)
        commits = git(repo, "log", "--reverse", "--format=%H %s", source).splitlines()
        findings = push_guard.scan(repo, source, rules)
        dropped = ignored_paths(repo, sorted({finding["path"] for finding in findings}))
        return {"mode": "replay", "source": source, "commits": commits,
                "guard": [finding for finding in findings if finding["path"] not in dropped]}
    files = snapshot_files(repo)
    return {"mode": "snapshot", "files": len(files), "bytes": sum((repo / path).stat().st_size for path in files),
            "guard": scan_snapshot(repo, files, rules)}


def preflight(cfg) -> dict:
    """只读检查：gh、账号、远端仓库与分支保护、本地仓库状态、待推送范围与 guard 干跑、DEV_DEPLOY_KEY。"""
    vault = repo_root(cfg, "vault")
    login = require_gh(vault)
    owner = cfg.github.get("owner") or login
    report = {"gh": {"path": shutil.which("gh"), "version": gh(["--version"], vault).splitlines()[0],
                     "login": login},
              "owner": owner, "repos": {}, "blockers": []}
    for key in ("dev", "vault"):
        root = repo_root(cfg, key)
        remote = remote_status(root, remote_name(cfg, owner, key))
        rules = checkout_rules(cfg, root)
        local = {"branch": current_branch(root),
                 "uncommitted": len([line for line in git(root, "status", "--porcelain").splitlines() if line]),
                 "tracked_changes": len(tracked_changes(root))}
        pending = pending_push(root, key, rules)
        report["repos"][key] = {"remote": remote, "local": local, "pending": pending}
        if remote["exists"] and remote["visibility"] != "PRIVATE":
            report["blockers"].append(f"{remote['name']} 可见性为 {remote['visibility']}，只允许 PRIVATE")
        if pending["guard"]:
            report["blockers"].append(f"{key} 待推送内容有 {len(pending['guard'])} 处 Push_Guard 命中")
        if key == "dev" and local["tracked_changes"]:
            report["blockers"].append(f"dev 有 {local['tracked_changes']} 个未提交的已跟踪改动（V5 分批提交未完成）")
    vault_remote = report["repos"]["vault"]["remote"]
    report["dev_deploy_key"] = (vault_remote["exists"] and "DEV_DEPLOY_KEY" in {
        item["name"] for item in gh_json(["secret", "list", "--repo", vault_remote["name"], "--json", "name"], vault)})
    report["protection"] = {key: value["remote"]["protection"] for key, value in report["repos"].items()}
    return report


# ---- bootstrap 用的历史构造（只用 git 管道命令，D2） ----

def remote_name(cfg, owner: str, key: str) -> str:
    return f"{owner}/{cfg.github.get(f'{key}_repo', DEFAULT_REPOS[key])}"


def legacy_source(repo: Path) -> str:
    """待重放的旧历史：改名前是 master，改名后是 legacy/master。"""
    return "master" if branch_exists(repo, "master") else LEGACY_BRANCH


def git_bytes(repo: Path, args: list[str], data: bytes = b"", env: dict | None = None) -> bytes:
    """字节进出的 git 调用（提交说明与 -z 列表不经文本换行转换）；env 叠加在当前环境上。"""
    result = subprocess.run(["git", "-C", str(repo), *args], input=data, capture_output=True,
                            env={**os.environ, **(env or {})})
    if result.returncode:
        raise WikiError(f"git {' '.join(args)} 失败: {result.stderr.decode('utf-8', 'replace')}")
    return result.stdout


def tracked_files(repo: Path, rev: str | None = None) -> list[str]:
    """rev 为空时取当前索引，否则取该提交的完整树。"""
    args = ["ls-tree", "-r", "-z", "--name-only", "--full-tree", rev] if rev else ["ls-files", "-z"]
    return list(filter(None, git(repo, "-c", "core.quotePath=false", *args).split("\0")))


def scratch_index(repo: Path) -> Path:
    return Path(git(repo, "rev-parse", "--path-format=absolute", "--git-path", "rwiki-bootstrap.index").strip())


def create_branch_ref(repo: Path, branch: str, sha: str) -> None:
    """只新建，不覆盖已有分支（旧值为全 0）。"""
    git(repo, "update-ref", f"refs/heads/{branch}", sha, "0" * len(sha))


def replay_filtered(repo: Path, source: str, target: str, excluded) -> int:
    """逐个重放 source 的提交到新分支 target：excluded(paths) 返回要去掉的路径；保留作者、时间与说明，
    加 Legacy-Commit trailer。用临时 GIT_INDEX_FILE + commit-tree，不动工作区与真实索引。"""
    index = scratch_index(repo)
    env = {"GIT_INDEX_FILE": str(index)}
    commits = git(repo, "rev-list", "--reverse", "--topo-order", source).split()
    mapped = {}
    try:
        for sha in commits:
            records = [record for record in git_bytes(repo, ["ls-tree", "-r", "-z", "--full-tree", sha]).split(b"\0")
                       if record]
            paths = [record.split(b"\t", 1)[1].decode("utf-8") for record in records]
            dropped = excluded(paths)
            kept = b"".join(record + b"\0" for record, path in zip(records, paths) if path not in dropped)
            git_bytes(repo, ["read-tree", "--empty"], env=env)
            git_bytes(repo, ["update-index", "-z", "--index-info"], kept, env)
            tree = git_bytes(repo, ["write-tree"], env=env).decode().strip()
            name, email, date, c_name, c_email, c_date, parents = git(
                repo, "log", "-1", "--date=raw", "--format=%an%x00%ae%x00%ad%x00%cn%x00%ce%x00%cd%x00%P",
                sha).rstrip("\n").split("\0")
            raw = git_bytes(repo, ["cat-file", "commit", sha])
            message = raw.split(b"\n\n", 1)[1] if b"\n\n" in raw else b""
            message = git_bytes(repo, ["interpret-trailers", "--trailer", f"Legacy-Commit: {sha}"], message)
            args = ["commit-tree", tree, *[part for parent in parents.split() for part in ("-p", mapped[parent])]]
            mapped[sha] = git_bytes(repo, args, message, {
                "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email, "GIT_AUTHOR_DATE": date,
                "GIT_COMMITTER_NAME": c_name, "GIT_COMMITTER_EMAIL": c_email,
                "GIT_COMMITTER_DATE": c_date}).decode().strip()
    finally:
        index.unlink(missing_ok=True)
    create_branch_ref(repo, target, mapped[commits[-1]])
    return len(commits)


def snapshot_orphan(repo: Path, target: str) -> str:
    """把过滤后的当前工作区（snapshot_files）写成新分支 target 上唯一的无父提交。"""
    files = snapshot_files(repo)
    index = scratch_index(repo)
    env = {"GIT_INDEX_FILE": str(index)}
    try:
        git_bytes(repo, ["read-tree", "--empty"], env=env)
        git_bytes(repo, ["update-index", "--add", "-z", "--stdin"],
                  b"".join(path.encode("utf-8") + b"\0" for path in files), env)
        tree = git_bytes(repo, ["write-tree"], env=env).decode().strip()
    finally:
        index.unlink(missing_ok=True)
    sha = git_bytes(repo, ["commit-tree", tree], "chore: 初始快照（过滤后的当前工作区）\n".encode("utf-8")).decode().strip()
    create_branch_ref(repo, target, sha)
    return sha


def switch_to_main(repo: Path) -> int:
    """只移动 HEAD 与索引（symbolic-ref + read-tree），不用 switch/checkout：旧分支跟踪而 main 不跟踪的
    忽略文件留在磁盘。核对这些文件切换前后都在，返回其个数。"""
    kept = sorted(ignored_paths(repo, tracked_files(repo)))
    before = [path for path in kept if (repo / path).is_file()]
    git(repo, "symbolic-ref", "HEAD", "refs/heads/main")
    git(repo, "read-tree", "main")
    after = [path for path in kept if (repo / path).is_file()]
    if after != before:
        raise WikiError(f"切换到 main 后原被跟踪的忽略文件数变化：{len(before)} → {len(after)}；请立即人工核对 {repo}")
    return len(after)


def deployed_skill() -> Path:
    """部署副本目录（tools/deploy.py 写入）；RWIKI_DEPLOYED_SKILL 可替换，供测试用。"""
    return Path(os.environ.get(DEPLOYED_ENV) or DEPLOYED_SKILL)


def hook_entry(config_path: Path, deployed: Path | None = None) -> dict:
    """hook 调用的 wiki.py 与 config.json：优先部署副本，缺 wiki.py / config.json 时退回当前检出并警告。"""
    deployed = deployed_skill() if deployed is None else Path(deployed)
    if (deployed / "wiki.py").is_file() and (deployed / "config.json").is_file():
        return {"source": "deployed", "wiki_py": str(deployed / "wiki.py"), "config": str(deployed / "config.json")}
    print(f"警告：未找到完整的部署副本 {deployed}（需要 wiki.py 与 config.json），pre-push hook 将调用当前检出的"
          f" {WIKI_PY}；检出切到旧分支或代码改坏时 hook 也跟着失效。建议先运行 tools/deploy.py 再重装 hook。",
          file=sys.stderr)
    return {"source": "checkout", "wiki_py": str(WIKI_PY), "config": str(config_path.resolve())}


def install_hook(repo: Path, config_path: Path, entry: dict | None = None) -> Path:
    """写 <git-common-dir>/hooks/pre-push：本解释器 + 部署副本（缺失时当前检出）的 gh guard --pre-push
    （hook 不入库，可重复运行）。"""
    entry = entry or hook_entry(config_path)
    hook = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-path", "hooks").strip()) / "pre-push"
    if hook.is_file() and HOOK_MARK not in hook.read_text(encoding="utf-8", errors="replace"):
        raise WikiError(f"{hook} 已存在且不是本工具写入的 hook；请先人工合并或移走它")
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("#!/bin/sh\n" + HOOK_MARK + "\n" + f"# 来源：{entry['source']}\n"
                    f'exec "{Path(sys.executable).as_posix()}" -X utf8 "{Path(entry["wiki_py"]).as_posix()}" '
                    f'--config "{Path(entry["config"]).as_posix()}" gh guard --pre-push "$1" "$2"\n',
                    encoding="utf-8", newline="\n")
    return hook


def install_hook_report(repo: Path, config_path: Path) -> dict:
    """gh install-hook 的输出：hook 路径 + 所用 wiki.py / config.json 及来源。"""
    entry = hook_entry(config_path)
    return {"hook": str(install_hook(repo, config_path, entry)), **entry}


# ---- bootstrap ----

def main_contents(repo: Path, key: str) -> list[str]:
    """将进入新 main 的文件：已有 main 时取其树；dev 为旧历史末端去掉忽略路径；vault 为工作区快照。"""
    if branch_exists(repo, "main"):
        return tracked_files(repo, "main")
    if key == "dev":
        files = tracked_files(repo, legacy_source(repo))
        dropped = ignored_paths(repo, files)
        return [path for path in files if path not in dropped]
    return snapshot_files(repo)


def missing_repo_files(files: list[str]) -> list[str]:
    missing = [name for name in REPO_FILES if name not in files]
    return missing + ([] if any(path.startswith(".github/") for path in files) else [".github/"])


def pending_summary(pending: dict) -> dict:
    size = ({"commits": len(pending["commits"])} if "commits" in pending
            else {"files": pending["files"], "bytes": pending["bytes"]})
    return {"mode": pending["mode"], **size, "guard_findings": len(pending["guard"])}


def bootstrap_local(repo: Path, key: str, config_path: Path) -> dict:
    """master → legacy/master → 构造 main（dev 重放、vault 快照）→ 切到 main → 安装 hook；每步先查后做。"""
    steps = {}
    if branch_exists(repo, "master"):
        git(repo, "branch", "-m", "master", LEGACY_BRANCH)
        steps["renamed"] = LEGACY_BRANCH
    if not branch_exists(repo, "main"):
        if key == "dev":
            steps["replayed"] = replay_filtered(repo, LEGACY_BRANCH, "main", lambda paths: ignored_paths(repo, paths))
        else:
            steps["snapshot"] = snapshot_orphan(repo, "main")
    if current_branch(repo) != "main":
        steps["ignored_kept"] = switch_to_main(repo)
    steps["hook"] = str(install_hook(repo, config_path))
    return steps


def bootstrap_remote(cfg, repo: Path, key: str, name: str) -> dict:
    """私有仓库 → origin → 推送 main（经可见性检查与 guard）→ 全套 Label；每步先查后建。"""
    steps = {}
    if not remote_status(repo, name)["exists"]:
        gh(["repo", "create", name, "--private"], repo)
        steps["created"] = name
    if "origin" not in git(repo, "remote").split():
        url = cfg.github.get(f"{key}_url") or gh_json(["repo", "view", name, "--json", "url"], repo)["url"] + ".git"
        git(repo, "remote", "add", "origin", url)
    previous = os.environ.get("RWIKI_BOOTSTRAP")
    os.environ["RWIKI_BOOTSTRAP"] = "1"
    try:
        push(repo, "main", checkout_rules(cfg, repo))
    finally:
        if previous is None:
            os.environ.pop("RWIKI_BOOTSTRAP")
        else:
            os.environ["RWIKI_BOOTSTRAP"] = previous
    steps["pushed"] = git(repo, "rev-parse", "main").strip()
    colors = {label["name"]: label["color"].lower()
              for label in gh_json(["label", "list", "--limit", "500", "--json", "name,color"], repo)}
    created = [label for label, color in LABELS.items() if colors.get(label) != color]
    for label in created:
        gh(["label", "create", label, "--color", LABELS[label], *description_args(label), "--force"], repo)
    steps["labels"] = len(created)
    return steps


def setup_deploy_key(dev: Path, vault: Path, dev_name: str, vault_name: str) -> str:
    """只读 deploy key 加到 dev、私钥存为 vault 的 DEV_DEPLOY_KEY；临时密钥写在 TEMP 下并在结束时删除。

    gh 2.103 的 deploy-key add 默认只读（没有 --read-only，写权限才需 --allow-write）；deploy-key list --json
    不按字段筛选、原样输出 REST 形状，没有 key 时输出空串（gh_json 得到 []）。"""
    titles = {item["title"] for item in gh_json(["repo", "deploy-key", "list", "--repo", dev_name, "--json", "title"],
                                                dev)}
    secrets = {item["name"] for item in gh_json(["secret", "list", "--repo", vault_name, "--json", "name"], vault)}
    if DEPLOY_KEY_TITLE in titles and DEPLOY_SECRET in secrets:
        return "existing"
    if shutil.which("ssh-keygen") is None:
        raise WikiError("未找到 ssh-keygen（Windows 可选功能 OpenSSH 客户端或 Git 自带），无法生成 deploy key")
    with tempfile.TemporaryDirectory(prefix="rwiki-deploy-key-") as folder:
        key = Path(folder) / "id_ed25519"
        run([shutil.which("ssh-keygen"), "-q", "-t", "ed25519", "-N", "", "-C", DEPLOY_KEY_TITLE, "-f", str(key)], dev)
        gh(["repo", "deploy-key", "add", str(key.with_suffix(".pub")), "--repo", dev_name,
            "--title", DEPLOY_KEY_TITLE], dev)
        result = subprocess.run([shutil.which("gh"), "secret", "set", DEPLOY_SECRET, "--repo", vault_name],
                                cwd=vault, input=key.read_bytes(), capture_output=True)
        if result.returncode:
            raise WikiError(f"gh secret set {DEPLOY_SECRET} 失败: {result.stderr.decode('utf-8', 'replace')}")
    return "created"


def setup_protection(repo: Path, name: str) -> str:
    """探测 main 的分支保护：已配置 → github；403（套餐不支持）→ local；其他（未配置）→ 配置后 github。"""
    endpoint = f"repos/{name}/branches/main/protection"
    try:
        gh(["api", endpoint], repo)
        return "github"
    except WikiError as error:
        if "HTTP 403" in str(error):
            return "local"
    handle, body = tempfile.mkstemp(suffix=".json")
    with os.fdopen(handle, "w", encoding="utf-8") as stream:
        json.dump(PROTECTION_BODY, stream)
    try:
        gh(["api", "-X", "PUT", endpoint, "--input", body], repo)
    finally:
        os.unlink(body)
    return "github"


def bootstrap(cfg, confirm: bool, config_path: Path) -> dict:
    """无 confirm：preflight + 授权摘要，不做任何写操作。confirm：按 D2/D10 构造 main、建私有仓库并首推。"""
    report = preflight(cfg)
    owner = report["owner"]
    names = {key: remote_name(cfg, owner, key) for key in ("dev", "vault")}
    if not confirm:
        return {"confirm": False, "blockers": report["blockers"],
                "authorization": {"account": report["gh"]["login"], "owner": owner, "repos": {
                    key: {"name": names[key], "private": True, "exists": report["repos"][key]["remote"]["exists"],
                          "pending": pending_summary(report["repos"][key]["pending"])} for key in names}},
                "next": "核对账号、仓库名、private 与待推送范围并取得用户明确授权后，运行 wiki.py gh bootstrap --confirm",
                "preflight": report}
    if report["blockers"]:
        raise WikiError("preflight 有阻断项，bootstrap 中止：\n" + "\n".join(f"- {line}" for line in report["blockers"]))
    repos = {key: repo_root(cfg, key) for key in ("dev", "vault")}
    for key, repo in repos.items():
        missing = missing_repo_files(main_contents(repo, key))
        if missing:
            raise WikiError(f"{key} 仓库文件不会进入新 main：{'、'.join(missing)}；"
                            "请先完成第 8 步（dev 须已在 chore(repo) 提交中）")
    result = {"confirm": True, "owner": owner, "repos": {}}
    for key, repo in repos.items():
        result["repos"][key] = {"name": names[key], **bootstrap_local(repo, key, config_path),
                                **bootstrap_remote(cfg, repo, key, names[key])}
    result["deploy_key"] = setup_deploy_key(repos["dev"], repos["vault"], names["dev"], names["vault"])
    for key, repo in repos.items():
        mode = setup_protection(repo, names[key])
        meta = read_meta(repo)
        meta["protection"] = mode
        write_meta(repo, meta)
        result["repos"][key]["protection"] = mode
    return result
