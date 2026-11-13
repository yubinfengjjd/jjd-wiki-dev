import random

import pytest

from rwiki.errors import WikiError
from rwiki.ghflow import parse_review_marker, render_review

SEED = 20261031
ITERATIONS = 300
WORDS = ("缺少测试", "路径 a/b.md 未更新", "--> 注释结尾", "`code`", "line\nbreak", "**粗体**", "ok")


def test_review_marker_round_trip():
    """Feature: github-structured-workflow, Property 11: 评审标记往返"""
    rng = random.Random(SEED)
    for iteration in range(ITERATIONS):
        verdict = rng.choice(("pass", "changes"))
        sha = "".join(rng.choice("0123456789abcdef") for _ in range(40))
        findings = [" ".join(rng.sample(WORDS, rng.randint(1, 3))) for _ in range(rng.randint(0, 5))]
        body = render_review(verdict, sha, findings)
        assert parse_review_marker(body) == (verdict, sha), f"seed={SEED} iteration={iteration}"
        assert body.splitlines()[0] == f"<!-- codex-review: verdict={verdict} sha={sha} -->"
        assert all(item in body for item in findings), f"seed={SEED} iteration={iteration}"
        assert sha in body.split("\n", 1)[1], f"seed={SEED} iteration={iteration}"


def test_invalid_review_inputs_and_unmarked_text():
    with pytest.raises(WikiError):
        render_review("approve", "a" * 40, [])
    with pytest.raises(WikiError):
        render_review("pass", "abc", [])
    assert parse_review_marker("普通评论 <!-- codex-review: verdict=pass sha=" + "a" * 40 + " -->") is None
    assert parse_review_marker("<!-- codex-review: verdict=pass sha=" + "A" * 40 + " -->") is None
