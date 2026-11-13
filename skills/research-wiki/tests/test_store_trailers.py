import random
import subprocess

from conftest import git_run
from rwiki.ghflow import write_meta
from rwiki.store import save, trailers
from rwiki.writer_lock import acquire, release

SEED = 20261105
ITERATIONS = 100
BRANCH = "task/scp-wave3-P2-harmony"
DIRS = ("methods", "templates", "附件 资料", "课题 笔记/子目录")
WORDS = ("页面", "note", "a b", "图 1", "x-y", "数据")
AGENTS = ("codex", "claude", "devin", "代理 一号")


def parse_trailers(vault) -> dict:
    message = git_run(vault, "log", "-1", "--format=%B")
    parsed = subprocess.run(["git", "-C", str(vault), "interpret-trailers", "--parse"], input=message,
                            capture_output=True, text=True, encoding="utf-8", check=True).stdout
    return dict(line.split(": ", 1) for line in parsed.splitlines())


def expected_pages(names: list[str]) -> str:
    shown = ", ".join(names[:20])
    return shown + (f" … (+{len(names) - 20})" if len(names) > 20 else "")


def test_trailers_round_trip(wiki_repo, monkeypatch):
    """Feature: github-structured-workflow, Property 8: 提交 trailer 往返"""
    config, _, vault = wiki_repo
    wiki = config.wiki_root
    git_run(vault, "checkout", "-q", "-b", BRANCH)
    rng = random.Random(SEED)
    for iteration in range(ITERATIONS):
        info = f"seed={SEED} iteration={iteration}"
        agent, issue = rng.choice(AGENTS), rng.randint(1, 9999)
        monkeypatch.setenv("RWIKI_AGENT", agent)
        write_meta(vault, {"tasks": {BRANCH: {"issue": issue}}})
        release(wiki)
        acquire(wiki, agent, BRANCH)
        count = rng.choice((1, 2, 5, 19, 20, 21, 24))
        for index in range(count):
            target = wiki / rng.choice(DIRS) / f"{rng.choice(WORDS)} {iteration}-{index}.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"{iteration}\n", encoding="utf-8")
        save(config, f"写入 {iteration}")
        staged = [name for name in git_run(vault, "-c", "core.quotePath=false", "diff-tree", "--no-commit-id",
                                           "--name-only", "-r", "-z", "--relative=知识库/", "HEAD").split("\0")
                  if name]
        values = parse_trailers(vault)
        assert values["Issue"] == f"#{issue}", info
        assert values["Agent"] == agent, info
        assert values["Pages"] == expected_pages(staged), f"{info} {values['Pages']!r}"
        assert git_run(vault, "log", "-1", "--format=%s").strip() == f"写入 {iteration}", info


def test_trailers_without_issue_or_agent():
    assert trailers(None, None, ["a.md"]) == "Pages: a.md"
    assert trailers(3, "codex", [f"p{i}.md" for i in range(22)]).splitlines()[-1].endswith("p19.md … (+2)")
