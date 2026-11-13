import random

import pytest

from rwiki.errors import WikiError
from rwiki.ghflow import render_issue_body, task_marker
from rwiki.push_guard import find_abs_paths

SEED = 20261102
ITERATIONS = 300
ROOTS = ("维护记录/2026-10-25-SCP全库入库", "画廊/2026-10-22-scp-example/figures", "知识库/methods/scp-local-source/source",
         "课题/wiki-use/_project", "review")
NAMES = ("回执.json", "report v2.md", "a|b.csv", "x.png", "LICENSE.md")


def test_evidence_only_relative_paths_and_hashes():
    """Feature: github-structured-workflow, Property 10: 证据只以相对路径与哈希出现"""
    rng = random.Random(SEED)
    for iteration in range(ITERATIONS):
        evidence = []
        for index in range(rng.randint(0, 6)):
            separator = rng.choice(("/", "\\"))
            path = separator.join([*rng.choice(ROOTS).split("/"), f"{index}-{rng.choice(NAMES)}"])
            evidence.append({"path": path, "sha256": "".join(rng.choice("0123456789abcdef") for _ in range(64))})
        body = render_issue_body(task_marker("task/scp-wave3-P2-harmony", "scp-wave3", "P2"), "整合 harmony",
                                 ["lint 通过", "复核回执一致"], evidence)
        assert body.startswith("<!-- rwiki-task: branch=task/scp-wave3-P2-harmony batch=scp-wave3 stage=P2 -->\n")
        for item in evidence:
            shown = item["path"].replace("\\", "/").replace("|", "&#124;")
            assert f"| {shown} | {item['sha256']} |" in body, f"seed={SEED} iteration={iteration}"
        assert find_abs_paths(body) == [], f"seed={SEED} iteration={iteration}"
        for heading in ("## 目标", "## 验收标准", "## 本地证据", "## 验收结论"):
            assert heading in body


@pytest.mark.parametrize("path", [r"E:\research-wiki\维护记录\x.json", "C:/Users/me/x", "/Users/me/x",
                                  "/home/me/x", "/abs/x"])
def test_absolute_evidence_is_rejected(path):
    with pytest.raises(WikiError):
        render_issue_body(task_marker("task/a-P1-b", "a", "P1"), "目标", [], [{"path": path, "sha256": "0" * 64}])


def test_absolute_path_in_goal_is_rejected():
    with pytest.raises(WikiError, match="绝对路径"):
        render_issue_body(task_marker("task/a-P1-b", "a", "P1"), r"读取 E:\data", [], [])
