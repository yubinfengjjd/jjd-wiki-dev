import random

import pytest

from rwiki.ghflow import OWNER_LABEL, gate_decision, owner_approval, render_review

SEED = 20261101
ITERATIONS = 500
BUCKETS = ("pass", "pass", "pass", "fail", "pending", "skipping", "cancel")


def random_sha(rng) -> str:
    return "".join(rng.choice("0123456789abcdef") for _ in range(40))


def reference(checks, entries, head) -> bool:
    buckets = {check["bucket"] for check in checks}
    if "pass" not in buckets or not buckets <= {"pass", "skipping"}:
        return False
    marked = [entry for entry in entries if entry["marker"]]
    return bool(marked) and marked[-1]["marker"] == ("pass", head)


def test_gate_decision_matches_reference():
    """Feature: github-structured-workflow, Property 12: 合并门禁判定"""
    rng = random.Random(SEED)
    for iteration in range(ITERATIONS):
        head = random_sha(rng)
        stale = [random_sha(rng) for _ in range(2)]
        checks = [{"name": f"job{index}", "bucket": rng.choice(BUCKETS)} for index in range(rng.randint(0, 4))]
        entries = []
        for _ in range(rng.randint(0, 5)):
            kind = rng.random()
            if kind < 0.3:
                entries.append({"body": rng.choice(("LGTM", "<!-- rwiki-gate: blocked -->\n原因", "")),
                                "marker": None})
            else:
                verdict = rng.choice(("pass", "changes"))
                sha = head if rng.random() < 0.7 else rng.choice(stale)
                entries.append({"body": render_review(verdict, sha, ["x"]), "marker": (verdict, sha)})
        ok, reasons = gate_decision(checks, [{"body": e["body"]} for e in entries], head)
        assert ok == reference(checks, entries, head), f"seed={SEED} iteration={iteration}"
        assert ok == (not reasons), f"seed={SEED} iteration={iteration} reasons={reasons}"


HEAD = "a" * 40
PASSED = [{"body": render_review("pass", HEAD, [])}]


@pytest.mark.parametrize("buckets, ok, reason", [
    ([], False, "没有 CI 检查结果"),
    (["skipping"], False, "没有 CI 检查结果"),
    (["skipping", "skipping"], False, "没有 CI 检查结果"),
    (["pass", "skipping"], True, None),
    (["pass"], True, None),
    (["pass", "pending"], False, "CI 检查未全部通过: job1(pending)"),
    (["fail"], False, "CI 检查未全部通过: job0(fail)"),
    (["pass", "cancel", "skipping"], False, "CI 检查未全部通过: job1(cancel)"),
])
def test_gate_decision_skipping_checks(buckets, ok, reason):
    checks = [{"name": f"job{index}", "bucket": bucket} for index, bucket in enumerate(buckets)]
    decided, reasons = gate_decision(checks, PASSED, HEAD)
    assert decided is ok and (reasons == [] if ok else any(item.startswith(reason) for item in reasons)), reasons


def stamp(seconds: int) -> str:
    return f"2026-10-28T{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}Z"


def reference_owner(labeled, committed, forced, head_in_timeline, head_date, has_label, reviews) -> bool:
    """作者确认：PR 现有 owner-approved 标签、已有针对 head 的评审，且最近一次 labeled 晚于
    head 推送时间（提交者时间、强推时间与最早一条针对 head 的评审时间取最晚）。"""
    if not has_label or not labeled or not reviews:
        return False
    pushed = committed + forced + ([] if head_in_timeline else [head_date]) + [min(reviews)]
    return max(labeled) > max(pushed)


def test_tiered_gate_matches_reference():
    """Feature: lite-gh, Property: 合并门禁按风险档判定"""
    seed = 20261028
    rng = random.Random(seed)
    for iteration in range(300):
        head = random_sha(rng)
        tier = rng.choice(("low", "normal", "high"))
        owner_required = rng.random() < 0.5
        checks = [{"name": f"job{index}", "bucket": rng.choice(BUCKETS)} for index in range(rng.randint(0, 3))]
        entries = []
        for _ in range(rng.randint(0, 3)):
            verdict = rng.choice(("pass", "changes"))
            sha = head if rng.random() < 0.7 else random_sha(rng)
            entries.append({"body": render_review(verdict, sha, []), "marker": (verdict, sha)})
        labeled = [rng.randint(0, 100) for _ in range(rng.randint(0, 2))]
        committed = [rng.randint(0, 100) for _ in range(rng.randint(0, 2))]
        forced = [rng.randint(0, 100) for _ in range(rng.randint(0, 1))]
        head_in_timeline = bool(committed) and rng.random() < 0.7
        head_date = rng.randint(0, 100)
        reviews = [rng.randint(0, 100) for _ in range(rng.randint(0, 2))]
        has_label = rng.random() < 0.7
        timeline = ([{"event": "labeled", "label": {"name": OWNER_LABEL}, "created_at": stamp(t)} for t in labeled]
                    + [{"event": "labeled", "label": {"name": "risk:low"}, "created_at": stamp(200)}]
                    + [{"event": "committed", "sha": head if head_in_timeline and index == 0 else random_sha(rng),
                        "committer": {"date": stamp(t)}} for index, t in enumerate(committed)]
                    + [{"event": "head_ref_force_pushed", "created_at": stamp(t)} for t in forced])
        rng.shuffle(timeline)
        labels = [OWNER_LABEL] if has_label else []
        owner = (owner_approval(labels, timeline, head, stamp(head_date), [stamp(t) for t in reviews])
                 if tier == "high" and owner_required else None)
        ok, reasons = gate_decision(checks, [{"body": e["body"]} for e in entries], head, tier, ["命中 x"], owner)
        expected = reference(checks, entries, head) if tier != "low" else reference(checks, [{"marker": ("pass", head)}], head)
        if tier == "high" and owner_required:
            expected = expected and reference_owner(labeled, committed, forced, head_in_timeline, head_date,
                                                    has_label, reviews)
        assert ok == expected, f"seed={seed} iteration={iteration} tier={tier} reasons={reasons}"
        assert ok == (not reasons), f"seed={seed} iteration={iteration} reasons={reasons}"
        if reasons:
            assert reasons[0].startswith(f"风险档 {tier}"), f"seed={seed} iteration={iteration} reasons={reasons}"


def test_low_tier_needs_no_review_but_ci():
    assert gate_decision([{"name": "ci", "bucket": "pass"}], [], HEAD, "low") == (True, [])
    ok, reasons = gate_decision([{"name": "ci", "bucket": "fail"}], [], HEAD, "low", ["全部命中低风险规则"])
    assert not ok and reasons[0] == "风险档 low：全部命中低风险规则" and "没有 Codex 评审回帖" not in reasons


def test_owner_approval_reasons():
    head = "b" * 40
    commit = {"event": "committed", "sha": head, "committer": {"date": "2026-10-28T10:00:00+08:00"}}
    label = {"event": "labeled", "label": {"name": OWNER_LABEL}, "created_at": "2026-10-28T03:00:00Z"}
    early = ["2026-10-28T02:30:00Z"]
    assert owner_approval([], [commit, label], head, None, early)[0] is False
    assert "没有 owner-approved 标签" in owner_approval([], [commit, label], head, None, early)[1]
    ok, reason = owner_approval([OWNER_LABEL], [label, commit], head, None, early)
    assert ok and reason == ""
    stale = {**label, "created_at": "2026-10-28T01:59:59Z"}
    ok, reason = owner_approval([OWNER_LABEL], [stale, commit], head, None, early)
    assert not ok and "已失效" in reason
    # timeline 没有 head 的 committed 事件：用 head 提交的 committer date。
    assert owner_approval([OWNER_LABEL], [label], head, "2026-10-28T04:00:00Z", early)[0] is False
    assert owner_approval([OWNER_LABEL], [label], head, "2026-10-28T02:00:00Z", early)[0] is True
    forced = {"event": "head_ref_force_pushed", "created_at": "2026-10-28T03:00:01Z"}
    assert owner_approval([OWNER_LABEL], [label, commit, forced], head, None, early)[0] is False
    # 没有针对 head 的评审：无法确定推送时间，判不通过。
    ok, reason = owner_approval([OWNER_LABEL], [label, commit], head, None, [])
    assert not ok and "还没有针对当前 head" in reason


def test_old_label_cannot_approve_new_head_with_backdated_commit():
    """评审复现：旧 head 10:00，作者 10:05 打标签，新 head 提交者时间伪造为 10:02、10:05 后才推送并评审。"""
    head = "c" * 40
    commit = {"event": "committed", "sha": head, "committer": {"date": "2026-10-28T10:02:00Z"}}
    label = {"event": "labeled", "label": {"name": OWNER_LABEL}, "created_at": "2026-10-28T10:05:00Z"}
    ok, reason = owner_approval([OWNER_LABEL], [label, commit], head, None, ["2026-10-28T10:07:00Z"])
    assert not ok and "已失效" in reason


def test_gate_decision_rejects_unknown_tier():
    with pytest.raises(ValueError):
        gate_decision([], [], HEAD, "medium")
