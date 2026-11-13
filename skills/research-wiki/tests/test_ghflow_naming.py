import random
import string

import pytest

from rwiki.errors import WikiError
from rwiki.ghflow import long_branch, parse_task_branch, task_branch

SEED = 20261030
ITERATIONS = 300
EXAMPLES = ("task/scp-wave3-P2-harmony", "ingest/scp-wave3")
ALPHABET = string.ascii_lowercase + string.digits


def slug(rng) -> str:
    parts = ["".join(rng.choice(ALPHABET) for _ in range(rng.randint(1, 8))) for _ in range(rng.randint(1, 4))]
    return "-".join(parts)[:40].strip("-") or "a"


def stage(rng) -> str:
    return rng.choice([f"P{rng.randint(0, 5)}", f"T{rng.randint(0, 120)}"])


def assert_rejected(call, *args, seed_info):
    with pytest.raises(WikiError) as error:
        call(*args)
    assert all(example in str(error.value) for example in EXAMPLES), seed_info


def test_task_branch_round_trip():
    """Feature: github-structured-workflow, Property 1: 分支命名往返与拒绝"""
    rng = random.Random(SEED)
    for iteration in range(ITERATIONS):
        batch, phase, topic = slug(rng), stage(rng), slug(rng)
        name = task_branch(batch, phase, topic)
        assert parse_task_branch(name) == (batch, phase, topic), f"seed={SEED} iteration={iteration} {name}"
        kind = rng.choice(("project", "ingest"))
        assert long_branch(kind, batch) == f"{kind}/{batch}", f"seed={SEED} iteration={iteration}"


def broken_slug(rng, good: str) -> str:
    position = rng.randrange(len(good) + 1)
    breakage = rng.choice(("upper", "space", "chinese", "underscore", "double", "edge", "long", "empty"))
    if breakage == "upper":
        return good[:position] + rng.choice(string.ascii_uppercase) + good[position:]
    if breakage == "space":
        return good[:position] + " " + good[position:]
    if breakage == "chinese":
        return good[:position] + "课题" + good[position:]
    if breakage == "underscore":
        return good[:position] + "_" + good[position:]
    if breakage == "double":
        return good + "--x"
    if breakage == "edge":
        return rng.choice(("-", "")) + good + "-"
    if breakage == "long":
        return "a" * 41
    return ""


def test_illegal_names_are_rejected_with_examples():
    """Feature: github-structured-workflow, Property 1: 分支命名往返与拒绝"""
    rng = random.Random(SEED + 1)
    for iteration in range(ITERATIONS):
        info = f"seed={SEED + 1} iteration={iteration}"
        good_batch, good_topic, good_stage = slug(rng), slug(rng), stage(rng)
        bad = broken_slug(rng, good_batch)
        bad_stage = rng.choice(("P6", "P", "p2", "T", "Px", "P2a", "t3", "阶段", ""))
        assert_rejected(long_branch, rng.choice(("project", "ingest")), bad, seed_info=info)
        assert_rejected(long_branch, rng.choice(("task", "Project", "feature", "")), good_batch, seed_info=info)
        assert_rejected(task_branch, bad, good_stage, good_topic, seed_info=info)
        assert_rejected(task_branch, good_batch, good_stage, broken_slug(rng, good_topic), seed_info=info)
        assert_rejected(task_branch, good_batch, bad_stage, good_topic, seed_info=info)
        malformed = rng.choice((
            f"task/{good_batch}-{good_stage}",                     # 缺主题
            f"task/{good_batch}-{bad_stage}-{good_topic}",          # 阶段越界
            f"task/{bad}-{good_stage}-{good_topic}",                # 非法批次
            f"{good_batch}-{good_stage}-{good_topic}",              # 缺 task/ 前缀
            f"task/{good_batch}-{good_stage}-{good_topic} ",        # 末尾空格
            f"task/{good_batch}-{good_stage}-{'a' * 41}",           # 超长主题
        ))
        assert_rejected(parse_task_branch, malformed, seed_info=f"{info} {malformed!r}")
