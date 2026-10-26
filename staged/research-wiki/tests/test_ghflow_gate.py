import random

from rwiki.ghflow import gate_decision, render_review

SEED = 20261101
ITERATIONS = 500
BUCKETS = ("pass", "pass", "pass", "fail", "pending", "skipping", "cancel")


def random_sha(rng) -> str:
    return "".join(rng.choice("0123456789abcdef") for _ in range(40))


def reference(checks, entries, head) -> bool:
    if not checks or any(check["bucket"] != "pass" for check in checks):
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
