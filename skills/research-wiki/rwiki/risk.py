"""按改动路径计算 PR 风险档（low|normal|high），规则在仓库内 `.github/risk-tiers.json`。

glob 语义（路径一律为 posix、相对仓库根，整串匹配，区分大小写）：
- `*` 匹配一段内任意字符（不跨 `/`），`?` 匹配一段内单个字符；
- 独占一段的 `**` 匹配零到多段：`**/.gitignore` 命中任意层级（含根目录）的 `.gitignore`，
  `.github/**` 命中 `.github` 下的一切；
- 不带 `/` 的模式只匹配根目录：`*.md` 命中 `README.md`，不命中 `review/x.md`；
- 其余字符（含 `[`、中文）按字面匹配。
"""
import json
import re
import subprocess
from functools import lru_cache
from pathlib import Path

from .errors import WikiError
from .store import git

RULES_FILE = ".github/risk-tiers.json"
TIERS = ("low", "normal", "high")


def _segment(part: str) -> str:
    return "".join("[^/]*" if token.startswith("*") else "[^/]" if token == "?" else re.escape(token)
                   for token in re.findall(r"\*+|\?|[^*?]+", part))


@lru_cache(maxsize=None)
def _compile(pattern: str) -> re.Pattern:
    parts = []
    for part in pattern.split("/"):
        if not (part == "**" and parts and parts[-1] == "**"):  # 连续的 `**` 等价于一个
            parts.append(part)
    regex = ""
    for index, part in enumerate(parts):
        last = index == len(parts) - 1
        if part != "**":
            regex += _segment(part) + ("" if last else "/")
        elif not last:
            regex += "(?:[^/]+/)*"
        elif index:
            regex = regex[:-1] + "(?:/[^/]+)*"  # 去掉前一段的 /：`a/**` 也命中 `a`
        else:
            regex = "[^/]+(?:/[^/]+)*"
    return re.compile(regex)


def glob_match(pattern: str, path: str) -> bool:
    return _compile(pattern).fullmatch(path) is not None


def _rules_text(repo: Path, ref: str | None) -> str | None:
    if ref is None:
        path = Path(repo) / RULES_FILE
        return path.read_text(encoding="utf-8") if path.is_file() else None
    result = subprocess.run(["git", "-C", str(repo), "show", f"{ref}:{RULES_FILE}"], capture_output=True)
    if result.returncode:
        if subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "-q", f"{ref}^{{commit}}"],
                          capture_output=True).returncode:
            raise WikiError(f"规则来源 {ref} 不是有效提交")
        return None
    return result.stdout.decode("utf-8")


def load_rules(repo: Path, ref: str | None = None) -> dict:
    """读 `.github/risk-tiers.json`；ref 为 None 读工作树，否则读该提交上的版本。文件缺失时返回空规则（全部归 normal）。

    判 PR 档位时必须用 base 上的规则（ref），否则 PR 可以改/删规则文件给自己降档。
    可选键 `high_requires_owner`（布尔，缺省 true）：high 档合并是否还要作者确认（owner-approved 标签）。
    """
    text = _rules_text(repo, ref)
    if text is None:
        return {"high": [], "low": [], "high_requires_owner": True}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise WikiError(f"{RULES_FILE} 不是合法 JSON: {error}") from error
    if not isinstance(data, dict) or not all(isinstance(data.get(kind, []), list) for kind in ("high", "low")):
        raise WikiError(f"{RULES_FILE} 格式应为 {{\"high\": [glob...], \"low\": [glob...]}}")
    owner = data.get("high_requires_owner", True)
    if not isinstance(owner, bool):
        raise WikiError(f"{RULES_FILE} 的 high_requires_owner 必须是 true 或 false: {owner!r}")
    return {**{kind: [str(item) for item in data.get(kind, [])] for kind in ("high", "low")},
            "high_requires_owner": owner}


def _first_hit(path: str, patterns: list[str]) -> str | None:
    return next((pattern for pattern in patterns if glob_match(pattern, path)), None)


def risk_tier(paths: list[str], rules: dict) -> tuple[str, list[str]]:
    """任一路径命中 high → high；全部命中 low 且非空 → low；否则 normal（空列表保守归 normal）。"""
    high = [(path, hit) for path in paths if (hit := _first_hit(path, rules.get("high", [])))]
    if high:
        return "high", [f"{path} 命中高风险规则 {hit}" for path, hit in high]
    if not paths:
        return "normal", ["没有改动路径，保守归 normal"]
    rest = [path for path in paths if _first_hit(path, rules.get("low", [])) is None]
    if not rest:
        return "low", [f"全部 {len(paths)} 个路径命中低风险规则"]
    return "normal", [f"{path} 未命中低风险规则" for path in rest]


def changed_paths(repo: Path, rev_range: str) -> list[str]:
    """改动路径；--no-renames 让改名拆成“旧路径删除 + 新路径新增”，两边都参与判档（移走高风险文件仍为 high）。"""
    out = git(Path(repo), "-c", "core.quotepath=off", "diff", "--no-renames", "--name-only", "-z", rev_range)
    return [path for path in out.split("\0") if path]


def range_base(repo: Path, rev_range: str) -> str:
    """规则来源：`A...B` 取 merge-base，`A..B` 取 A；单个提交按 `<提交>..工作树` 取该提交。"""
    if "..." in rev_range:
        left, right = rev_range.split("...", 1)
        return git(Path(repo), "merge-base", left or "HEAD", right or "HEAD").strip()
    if ".." in rev_range:
        return rev_range.split("..", 1)[0] or "HEAD"
    return rev_range


def tier_report(repo: Path, rev_range: str, rules_ref: str | None = None) -> dict:
    paths = changed_paths(repo, rev_range)
    ref = rules_ref or range_base(repo, rev_range)
    tier, reasons = risk_tier(paths, load_rules(repo, ref))
    return {"tier": tier, "reasons": reasons, "paths": len(paths), "rules_ref": ref}
