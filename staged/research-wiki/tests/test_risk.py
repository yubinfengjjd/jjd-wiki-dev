import json
import random
from fnmatch import fnmatchcase

import pytest

from conftest import DEV_ROOT, commit_file, git_run, run_wiki, write_config
from rwiki.errors import WikiError
from rwiki.risk import changed_paths, glob_match, load_rules, risk_tier

SEED = 20261102
ITERATIONS = 300
SEGMENTS = ("a", "b", "中文", "说明.md", "x.md", ".gitignore", "ci.yml", "知识库")
PATTERN_SEGMENTS = ("a", "b", "中文", "*", "*.md", "**", "?", ".gitignore", "知识库", "x.*")
VAULT_RULES = {
    "high": [".github/**", ".gitignore", "**/.gitignore", ".gitattributes", ".push-guard-allow", "tools/deploy.py",
             "tools/launcher.ps1", "知识库/AGENTS.md", "知识库/.protected-hashes.json"],
    "low": ["知识库/log.md", "文档/**", "*.md", ".kiro/specs/**"],
}


def reference_match(pattern: str, path: str) -> bool:
    """参考模型：按 / 分段，`**` 段匹配零到多段，其余段用 fnmatchcase（段内 * 不跨 /）。"""
    def walk(parts, names):
        if not parts:
            return not names
        if parts[0] == "**":
            return any(walk(parts[1:], names[index:]) for index in range(len(names) + 1))
        return bool(names) and fnmatchcase(names[0], parts[0]) and walk(parts[1:], names[1:])
    return walk(pattern.split("/"), path.split("/"))


def reference_tier(paths, rules) -> str:
    hit = lambda path, kind: any(reference_match(pattern, path) for pattern in rules.get(kind, []))
    if any(hit(path, "high") for path in paths):
        return "high"
    return "low" if paths and all(hit(path, "low") for path in paths) else "normal"


def random_path(rng) -> str:
    return "/".join(rng.choice(SEGMENTS) for _ in range(rng.randint(1, 4)))


def random_pattern(rng) -> str:
    return "/".join(rng.choice(PATTERN_SEGMENTS) for _ in range(rng.randint(1, 3)))


def test_risk_tier_matches_reference():
    """Feature: lite-gh, Property: 风险档与参考模型一致"""
    rng = random.Random(SEED)
    for iteration in range(ITERATIONS):
        rules = {kind: [random_pattern(rng) for _ in range(rng.randint(0, 3))] for kind in ("high", "low")}
        paths = [random_path(rng) for _ in range(rng.randint(0, 5))]
        for path in paths:
            for pattern in rules["high"] + rules["low"]:
                assert glob_match(pattern, path) == reference_match(pattern, path), \
                    f"seed={SEED} iteration={iteration} pattern={pattern} path={path}"
        tier, reasons = risk_tier(paths, rules)
        assert tier == reference_tier(paths, rules), f"seed={SEED} iteration={iteration} {rules} {paths}"
        assert reasons, f"seed={SEED} iteration={iteration}"


DEV_TABLE = [
    ([], "normal"),
    (["README.md"], "low"),
    (["AGENTS.md", "review/2026/中文评审.md"], "low"),
    (["staged/research-wiki/README.md"], "normal"),
    (["README.md", "staged/research-wiki/rwiki/lint.py"], "normal"),
    (["文档/说明.md"], "normal"),
    ([".gitignore"], "high"),
    (["staged/research-wiki/知识库/.gitignore"], "high"),
    (["README.md", "staged/research-wiki/rwiki/ghflow.py"], "high"),
    ([".github/workflows/ci.yml"], "high"),
    (["ci/ci_scope.py"], "high"),
    (["staged/research-wiki/rwiki/risk.py"], "high"),
    (["staged/research-wiki/assets/AGENTS.md"], "high"),
]
VAULT_TABLE = [
    (["知识库/log.md", "文档/方案/计划.md", "README.md"], "low"),
    ([".kiro/specs/lite/tasks.md"], "low"),
    (["知识库/methods/中文方法.md"], "normal"),
    (["知识库/AGENTS.md"], "high"),
    (["知识库/methods/scp/.gitignore"], "high"),
    (["tools/deploy.py", "README.md"], "high"),
]


@pytest.mark.parametrize("paths, expected", DEV_TABLE)
def test_dev_rule_table(paths, expected):
    assert risk_tier(paths, load_rules(DEV_ROOT))[0] == expected


@pytest.mark.parametrize("paths, expected", VAULT_TABLE)
def test_vault_rule_table(paths, expected):
    assert risk_tier(paths, VAULT_RULES)[0] == expected


def test_glob_double_star_semantics():
    assert glob_match("**/.gitignore", ".gitignore") and glob_match("**/.gitignore", "a/中文/.gitignore")
    assert glob_match("a/**/b", "a/b") and glob_match("a/**/b", "a/x/y/b")
    # `**` 匹配零到多段，所以 `.github/**` 也匹配 `.github` 本身。
    assert glob_match(".github/**", ".github/workflows/ci.yml") and glob_match(".github/**", ".github")
    assert not glob_match(".github/**", ".githubx/a") and not glob_match("a?", "a/")
    assert glob_match("*.md", "说明.md") and not glob_match("*.md", "review/说明.md")


def test_load_rules_missing_file_is_empty(tmp_path):
    assert load_rules(tmp_path) == {"high": [], "low": []}
    assert risk_tier(["README.md"], load_rules(tmp_path))[0] == "normal"


def tier_of(work, config, rev_range="origin/main..HEAD"):
    result = run_wiki(work, "--config", str(config), "gh", "tier", "--range", rev_range)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.fixture
def ruled_repo(git_pair, tmp_path):
    """main 上已有规则：ghflow.py 为 high，review/** 为 low。"""
    work = git_pair.work
    rules = {"high": ["src/ghflow.py", ".github/**"], "low": ["review/**"]}
    commit_file(work, ".github/risk-tiers.json", json.dumps(rules), "rules")
    commit_file(work, "src/ghflow.py", "x = 1\n", "high file")
    git_run(work, "push", "-q", "origin", "main")
    return work, write_config(tmp_path / "c.json", tmp_path / "wiki")


def test_rename_of_high_file_stays_high(ruled_repo):
    work, config = ruled_repo
    (work / "review").mkdir(exist_ok=True)
    git_run(work, "mv", "src/ghflow.py", "review/ghflow.md")
    git_run(work, "commit", "-q", "-m", "move away")
    assert "src/ghflow.py" in changed_paths(work, "origin/main..HEAD")
    assert tier_of(work, config)["tier"] == "high"


def test_pr_cannot_lower_tier_by_editing_or_deleting_rules(ruled_repo):
    work, config = ruled_repo
    commit_file(work, ".github/risk-tiers.json", json.dumps({"high": [], "low": ["**"]}), "lower rules")
    commit_file(work, "src/ghflow.py", "x = 2\n", "change high file")
    report = tier_of(work, config)
    assert report["tier"] == "high" and report["rules_ref"] == "origin/main"
    git_run(work, "rm", "-q", ".github/risk-tiers.json")
    git_run(work, "commit", "-q", "-m", "drop rules")
    assert tier_of(work, config)["tier"] == "high"
    assert tier_of(work, config, "origin/main...HEAD")["tier"] == "high"


def test_rules_ref_missing_file_is_empty_and_bad_ref_is_error(ruled_repo):
    work, _ = ruled_repo
    first = git_run(work, "rev-list", "--max-parents=0", "HEAD").strip()
    assert load_rules(work, first) == {"high": [], "low": []}
    with pytest.raises(WikiError, match="不是有效提交"):
        load_rules(work, "no-such-ref")


def test_gh_tier_end_to_end(git_pair, tmp_path):
    work = git_pair.work
    rules = {"high": ["**/.gitignore"], "low": ["review/**", "*.md"]}
    commit_file(work, ".github/risk-tiers.json", json.dumps(rules), "rules")
    git_run(work, "push", "-q", "origin", "main")
    commit_file(work, "review/中文评审.md", "评审\n", "review")
    config = write_config(tmp_path / "c.json", tmp_path / "wiki")
    assert changed_paths(work, "origin/main..HEAD") == ["review/中文评审.md"]
    result = run_wiki(work, "--config", str(config), "gh", "tier", "--range", "origin/main..HEAD")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["tier"] == "low" and json.loads(result.stdout)["paths"] == 1
    commit_file(work, "子目录/.gitignore", "*.tmp\n", "ignore")
    result = run_wiki(work, "--config", str(config), "gh", "tier", "--range", "origin/main..HEAD")
    report = json.loads(result.stdout)
    assert result.returncode == 0 and report["tier"] == "high" and report["paths"] == 2
    assert any("子目录/.gitignore" in reason for reason in report["reasons"])
