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


def load_rules(repo: Path) -> dict:
    """读 `.github/risk-tiers.json`；文件缺失时返回空规则（全部归 normal）。"""
    path = Path(repo) / RULES_FILE
    if not path.is_file():
        return {"high": [], "low": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise WikiError(f"{RULES_FILE} 不是合法 JSON: {error}") from error
    if not isinstance(data, dict) or not all(isinstance(data.get(kind, []), list) for kind in ("high", "low")):
        raise WikiError(f"{RULES_FILE} 格式应为 {{\"high\": [glob...], \"low\": [glob...]}}")
    return {kind: [str(item) for item in data.get(kind, [])] for kind in ("high", "low")}


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
    out = git(Path(repo), "-c", "core.quotepath=off", "diff", "--name-only", "-z", rev_range)
    return [path for path in out.split("\0") if path]


def tier_report(repo: Path, rev_range: str) -> dict:
    paths = changed_paths(repo, rev_range)
    tier, reasons = risk_tier(paths, load_rules(repo))
    return {"tier": tier, "reasons": reasons, "paths": len(paths)}
