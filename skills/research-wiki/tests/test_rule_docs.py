import argparse

import pytest

from conftest import SKILL_ROOT
from rwiki.cli import parser

# v2（2026-10-27）规则文档的要点：每份文档必须写到的短语。
REQUIRED = {
    "assets/AGENTS.md": (
        "catalog.jsonl", "find → show → use", "L0", "L1", "L2", "画廊是来源之一", "四步", "mark-ready",
        "deps --install", "按批次批准", "not_run", "收据只证明", "不进 Git", "<!-- user:start -->",
        "<!-- facts:start -->", "内部字段 → 作者列", "figure_relations", "只查结构", "legacy/master",
        "references/", "sources-and-recipes.md", "github-workflow.md"),
    "SKILL.md": (
        "name: research-wiki", "sci-figure-replica", "medfig-render", "medpaper-pipeline", "rwiki", "wiki.py",
        "$env:TEMP", "AGENTS.md", "catalog.jsonl", "find → show → use", "RWIKI-USE.md", "run --dir",
        "record-use", "source add", "source fetch", "source scan", "promote", "deps --install", "按批次批准",
        "mark-ready", "--from-recipe", "ingest-figure", "verify-template", "画廊是来源之一", "L0", "L1", "L2",
        "不进 Git", "<!-- user:start -->", "legacy/master", "references/sources-and-recipes.md",
        "references/github-workflow.md"),
    "references/sources-and-recipes.md": (
        "items.jsonl", "catalog.jsonl", "source.json", "rwiki-origin.json", "RWIKI-USE.md",
        "bindings.draft.json", "schema_version", "as-is", "new-data", "other-dir", "not_run", "trusted",
        "sources_root", "work_root", "r_libs", "cran_mirror", "deps --install", "按批次批准", "restore",
        "# >>> push-guard gpl", "不进 Git", "figureya", "--curation", "--update", "L0", "L1", "L2"),
    "references/github-workflow.md": (
        "可选", "`jjd-wiki-dev`", "`jjd-wiki`", "`main`", "wiki.py gh install-hook --repo dev|vault", "不入库",
        "不依赖 Kiro", "非编码 agent", "编码 agent 不评审自己的 PR", "`protection: local`", "legacy/*",
        "legacy/master", "RWIKI_WIKI_ROOT", "LOCAL-ONLY", "--local-report", "codex-review", "start-task",
        ".kiro"),
}
README_REQUIRED = ("`jjd-wiki-dev`", "`jjd-wiki`", "`main`", "github.com/", "不推送", "wiki.py gh install-hook",
                   "catalog.jsonl", "rwiki", ".kiro", "限制性许可", "可选", "legacy/master")
# 已被 v2 取代的说法与改名前的仓库名，不能再出现在任何规则文档里。
STALE = ("提交到 master", "提交到master", "save 自动提交", "维护文件任务书", "任务书：T1",
         "research-wiki-dev", "research-wiki-vault",
         "请先 start-task", "save 与网页写入都被拒", "只在 `task/*` 任务分支上", "合并只能经", "唯一合并入口",
         "拒绝直接推送 `main`",
         "不安装依赖", "本轮不安装包", "不在 Wiki 装包", "不安装、不伪造", "不安装、不换环境",
         "不要改用知识库的解释器", "Wiki 环境代跑课题",
         "画廊条目只由 sci-figure-replica 复刻产生", "不得为没有复刻过的图写页面",
         "panel 模板只能从已签核的版式拆出", "模板必须记录至少一个来源 `layouts`",
         "入库八步", "逐一授权", "五处", "5 处",
         # GitHub Flow 之前：批次建长期分支，close-batch 开批次 PR 到 main 是必经步骤。
         "从 `origin/main` 建长期分支", "开 PR 到所属长期分支", "全部关闭后开长期分支到 `main` 的 PR",
         "旧批次改为开长期分支到 `main` 的 PR", "长期分支：`project/<课题>`")
# GitHub Flow 与三档风险门禁：三份规则文档都要写到。
FLOW_DOCS = ("assets/AGENTS.md", "SKILL.md", "references/github-workflow.md")
FLOW_REQUIRED = ("risk:low", "risk:normal", "risk:high", "owner-approved", "high_requires_owner", "gh tier",
                 "origin/main", "gh finish-task", "gh merge")
RULE_DOCS = ("assets/AGENTS.md", "SKILL.md",
             *sorted(f"references/{path.name}" for path in (SKILL_ROOT / "references").glob("*.md")))


def subcommands(command: argparse.ArgumentParser) -> dict:
    return next(action for action in command._actions if isinstance(action, argparse._SubParsersAction)).choices


def gh_subcommands() -> list[str]:
    return sorted(subcommands(subcommands(parser())["gh"]))


def read(path):
    return path.read_text(encoding="utf-8")


def missing(text: str, phrases) -> list[str]:
    return [phrase for phrase in phrases if phrase not in text]


def stale(text: str) -> list[str]:
    return [phrase for phrase in STALE if phrase in text]


def test_gh_subcommand_set_is_documented():
    assert gh_subcommands() == sorted(("preflight", "bootstrap", "install-hook", "start-batch", "start-task",
                                       "finish-task", "review", "merge", "close-batch", "migrate-legacy",
                                       "guard", "protect-baseline", "tier"))
    workflow = read(SKILL_ROOT / "references/github-workflow.md")
    assert [name for name in gh_subcommands() if f"| `{name}` |" not in workflow] == []


@pytest.mark.parametrize("name", sorted(REQUIRED))
def test_rule_doc_states_v2_points(name):
    assert missing(read(SKILL_ROOT / name), REQUIRED[name]) == []


@pytest.mark.parametrize("name", FLOW_DOCS)
def test_rule_doc_states_github_flow_and_tiers(name):
    assert missing(read(SKILL_ROOT / name), FLOW_REQUIRED) == []


def test_workflow_doc_states_gate_details():
    workflow = read(SKILL_ROOT / "references/github-workflow.md")
    assert missing(workflow, ("agent 禁止添加", "只是约定", "PR 未包含最新 main", "批次 PR", "判定时刻",
                              "每周全量 CI", "只看本机元数据", "path_prepend", "部署后才对 hook 生效",
                              "跳过 pytest", "--no-renames", "--repo dev|vault")) == []


@pytest.mark.parametrize("name", RULE_DOCS)
def test_rule_doc_has_no_superseded_rules(name):
    assert stale(read(SKILL_ROOT / name)) == []


@pytest.mark.local
def test_vault_rule_docs(vault_root):
    readme = read(vault_root / "README.md")
    assert stale(readme) == []
    assert missing(readme, README_REQUIRED) == []
    assert "RWIKI_WIKI_ROOT" in read(vault_root / "tools/launcher.ps1")
    # 知识库里的规则由 `wiki.py init` 从 assets 同步，必须逐字节相同。
    assert (vault_root / "知识库/AGENTS.md").read_bytes() == (SKILL_ROOT / "assets/AGENTS.md").read_bytes()
