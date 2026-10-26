import argparse

import pytest

from conftest import DEV_ROOT, SKILL_ROOT
from rwiki.cli import parser

VAULT_ROOT = DEV_ROOT.parent
STAGED_DOCS = ("assets/AGENTS.md", "SKILL.md", "references/github-workflow.md")
# (a) 与宿主无关 (b) hook 重新安装 (c) 评审分工 (d) 本地门禁下的唯一合并入口
REQUIRED = {
    "a": ("不依赖 Kiro", "Codex、Claude、Devin、Kiro"),
    "b": ("wiki.py gh install-hook --repo dev|vault", "不入库", "新克隆或新机器"),
    "c": ("非编码 agent", "wiki.py gh review", "编码 agent 不评审自己的 PR"),
    "d": ("403", "本地门禁模式", "wiki.py gh merge", "不在网页上点合并", "不直接运行 `gh pr merge`"),
}
WORKFLOW_TOPICS = ("RWIKI_WIKI_ROOT", "LOCAL-ONLY", "legacy/master", "--local-report", "codex-review", "start-task")
STALE = ("提交到 master", "提交到master", "save 自动提交", "维护文件任务书", "任务书：T1")


def subcommands(command: argparse.ArgumentParser) -> dict:
    return next(action for action in command._actions if isinstance(action, argparse._SubParsersAction)).choices


def gh_subcommands() -> list[str]:
    return sorted(subcommands(subcommands(parser())["gh"]))


def read(path):
    return path.read_text(encoding="utf-8")


def check_rules(text: str) -> None:
    missing = [phrase for phrases in REQUIRED.values() for phrase in phrases if phrase not in text]
    missing += [topic for topic in WORKFLOW_TOPICS if topic not in text]
    assert not missing
    assert not [phrase for phrase in STALE if phrase in text]


def test_gh_subcommand_set_is_documented():
    assert gh_subcommands() == sorted(("preflight", "bootstrap", "install-hook", "start-batch", "start-task",
                                       "finish-task", "review", "merge", "close-batch", "migrate-legacy",
                                       "guard", "protect-baseline"))
    skill = read(SKILL_ROOT / "SKILL.md")
    workflow = read(SKILL_ROOT / "references/github-workflow.md")
    assert [name for name in gh_subcommands() if f"gh {name}" not in skill] == []
    assert [name for name in gh_subcommands() if f"| `{name}` |" not in workflow] == []


@pytest.mark.parametrize("item", sorted(REQUIRED))
@pytest.mark.parametrize("name", STAGED_DOCS)
def test_staged_rule_docs_state_each_requirement(name, item):
    text = read(SKILL_ROOT / name)
    assert [phrase for phrase in REQUIRED[item] if phrase not in text] == []


@pytest.mark.parametrize("name", STAGED_DOCS)
def test_staged_rule_docs(name):
    check_rules(read(SKILL_ROOT / name))


@pytest.mark.local
def test_vault_rule_docs():
    rules = VAULT_ROOT / "知识库/AGENTS.md"
    assert rules.read_bytes() == (SKILL_ROOT / "assets/AGENTS.md").read_bytes()
    check_rules(read(rules))
    readme = read(VAULT_ROOT / "README.md")
    assert not [phrase for phrase in STALE if phrase in readme]
    assert [phrase for phrase in ("research-wiki-dev", "research-wiki-vault", "`main`", "<待 bootstrap 后填写",
                                  "本地门禁", "不推送", "wiki.py gh install-hook")
            if phrase not in readme] == []
    assert "RWIKI_WIKI_ROOT" in read(VAULT_ROOT / "tools/launcher.ps1")
