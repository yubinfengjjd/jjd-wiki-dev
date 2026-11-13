import random

import pytest

from conftest import git_run
from rwiki.errors import WikiError
from rwiki.ghflow import write_meta
from rwiki.store import save
from rwiki.writer_lock import acquire, release

SEED = 20261106
ITERATIONS = 120
BRANCH = "task/scp-wave3-P2-harmony"
AGENTS = ("codex", "claude", "devin")


def test_writer_lock_is_exclusive(wiki_repo, monkeypatch):
    """Feature: github-structured-workflow, Property 9: 写入锁排他"""
    config, _, vault = wiki_repo
    wiki = config.wiki_root
    git_run(vault, "checkout", "-q", "-b", BRANCH)
    write_meta(vault, {"tasks": {BRANCH: {"issue": 7}}})
    rng = random.Random(SEED)
    holder = None
    for iteration in range(ITERATIONS):
        info = f"seed={SEED} iteration={iteration} holder={holder}"
        agent = rng.choice(AGENTS)
        operation = rng.choices(("acquire", "save", "release"), (4, 5, 1))[0]
        if operation == "release":
            release(wiki)
            holder = None
        elif operation == "acquire":
            if holder in (None, agent):
                assert acquire(wiki, agent, BRANCH)["agent"] == agent, info
                holder = agent
            else:
                with pytest.raises(WikiError, match=f"{holder}.*{BRANCH}"):
                    acquire(wiki, agent, BRANCH)
        else:
            monkeypatch.setenv("RWIKI_AGENT", agent)
            (wiki / f"页 {iteration}.md").write_text(f"{agent}\n", encoding="utf-8")
            head = git_run(vault, "rev-parse", "HEAD").strip()
            if holder == agent:
                save(config, f"{agent} {iteration}")
                assert git_run(vault, "rev-parse", "HEAD").strip() != head, info
                assert f"Agent: {agent}" in git_run(vault, "log", "-1", "--format=%B"), info
            else:
                with pytest.raises(WikiError, match=f"{holder}.*{BRANCH}" if holder else "start-task"):
                    save(config, f"{agent} {iteration}")
                assert git_run(vault, "rev-parse", "HEAD").strip() == head, info
