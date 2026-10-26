import json
import random

from conftest import gh_writes
from rwiki.ghflow import LEGACY_MARKER, MIGRATED_PREFIX, legacy_marker, migrate_legacy

SEED = 20261110
ITERATIONS = 100
REPOS = {"dev": "tester/research-wiki-dev", "vault": "tester/research-wiki-vault"}
MILESTONES = ("legacy/SCP持续入库与新规则", "legacy/review")


def random_bytes(rng) -> bytes:
    lines = [rng.choice(("# 任务书", "状态：完成", "- [x] 验收", "证据见维护记录")) for _ in range(rng.randint(0, 4))]
    text = rng.choice(("\n", "\r\n")).join(lines) + rng.choice(("", "\n", "\r\n"))
    return (b"\xef\xbb\xbf" if rng.random() < 0.3 else b"") + text.encode("utf-8")


def random_map(rng, iteration, dev) -> tuple[dict, dict]:
    items, originals = [], {}
    for number in range(rng.randint(0, 3)):
        relative = f"review/T{iteration}-{number}.md"
        data = random_bytes(rng)
        (dev / "review").mkdir(exist_ok=True)
        (dev / relative).write_bytes(data)
        originals[relative] = data
        items.append({"id": f"T{iteration}-{number}", "repo": "dev", "title": f"任务书 {iteration}-{number}",
                      "files": [relative], "state": rng.choice(("open", "closed")), "conclusion": "已验收，见评审记录",
                      "evidence": [{"path": f"维护记录/2026-10-2{number}/回执.json", "sha256": f"{number:x}" * 64}]})
    gaps = [{"id": f"gap-{iteration}-{number}", "repo": rng.choice(("dev", "vault")),
             "milestone": rng.choice(MILESTONES), "title": f"缺口 {iteration}-{number}", "body": "补齐复核"}
            for number in range(rng.randint(0, 2))]
    return {"items": items, "gaps": gaps}, originals


def seed_existing(rng, state, mapping):
    """部分映射项预先存在、且状态与映射相反（模拟上次中途失败或手工改动）。"""
    for kind, entry in [("item", item) for item in mapping["items"]] + [("gap", gap) for gap in mapping["gaps"]]:
        if rng.random() < 0.3:
            closed = kind == "item" and entry["state"] == "closed"
            repo = state["repos"][REPOS[entry["repo"]]]
            number = 1 + max([issue["number"] for issue in repo["issues"]] or [0])
            repo["issues"].append({"number": number, "title": entry["title"], "labels": [], "comments": [],
                                   "body": legacy_marker(entry["id"]) + "\n旧正文\n",
                                   "state": "OPEN" if closed else "CLOSED",
                                   "milestone": entry.get("milestone"),
                                   "url": f"https://github.com/{REPOS[entry['repo']]}/issues/{number}"})


def test_migrate_legacy_is_idempotent(gh_repos, tmp_path):
    """Feature: github-structured-workflow, Property 14: 遗留迁移幂等"""
    config, fake = gh_repos.config, gh_repos.gh
    rng = random.Random(SEED)
    for iteration in range(ITERATIONS):
        info = f"seed={SEED} iteration={iteration}"
        mapping, originals = random_map(rng, iteration, gh_repos.dev)
        state = fake.state()
        for name in REPOS.values():
            state["repos"][name]["issues"] = []
        seed_existing(rng, state, mapping)
        fake.write(state)
        path = tmp_path / "legacy-map.json"
        path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
        migrate_legacy(config, path, False)
        second = migrate_legacy(config, path, False)
        assert all(entry["action"] == "none" for entry in second["entries"]), info
        assert second["marked"] == [], info
        state = fake.state()
        for kind, entry in [("item", item) for item in mapping["items"]] + [("gap", gap) for gap in mapping["gaps"]]:
            issues = [issue for issue in state["repos"][REPOS[entry["repo"]]]["issues"]
                      if (match := LEGACY_MARKER.search(issue["body"])) and match.group(1) == entry["id"]]
            assert len(issues) == 1, f"{info} {entry['id']}"
            expected = "CLOSED" if kind == "item" and entry["state"] == "closed" else "OPEN"
            assert issues[0]["state"] == expected, f"{info} {entry['id']}"
            if kind == "gap" and "旧正文" not in issues[0]["body"]:
                assert issues[0]["milestone"] == entry["milestone"], f"{info} {entry['id']}"
        for relative, data in originals.items():
            marked = (gh_repos.dev / relative).read_bytes()
            assert marked.count(MIGRATED_PREFIX) == 1 and marked.startswith(MIGRATED_PREFIX), info
            assert marked.split(b"\n\n", 1)[1] == data, info


def test_dry_run_writes_nothing_and_evidence_stays_relative(gh_repos, tmp_path):
    config, fake = gh_repos.config, gh_repos.gh
    (gh_repos.dev / "review").mkdir()
    (gh_repos.dev / "review/T3-review.md").write_bytes(b"# T3\r\n")
    mapping = {"items": [{"id": "T3", "repo": "dev", "title": "T3 评审", "files": ["review/T3-review.md"],
                          "state": "closed", "conclusion": "通过",
                          "evidence": [{"path": "维护记录/2026-10-21/x.json", "sha256": "ab" * 32}]}],
               "gaps": [{"id": "gap-1", "repo": "vault", "milestone": MILESTONES[0], "title": "缺口一", "body": "补齐"}]}
    path = tmp_path / "legacy-map.json"
    path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
    plan = migrate_legacy(config, path, True)
    assert [(entry["id"], entry["action"], entry["state"]) for entry in plan["entries"]] == [
        ("T3", "create", "closed"), ("gap-1", "create", "open")]
    assert gh_writes(fake) == [] and (gh_repos.dev / "review/T3-review.md").read_bytes() == b"# T3\r\n"
    done = migrate_legacy(config, path, False)
    assert done["marked"] == ["dev:review/T3-review.md"]
    issue = fake.state()["repos"][REPOS["dev"]]["issues"][0]
    assert issue["state"] == "CLOSED" and "| 维护记录/2026-10-21/x.json | " + "ab" * 32 + " |" in issue["body"]
    assert "通过" in issue["body"] and set(issue["labels"]) == {"type:legacy", "stage:legacy", "status:已验收"}
    gap = fake.state()["repos"][REPOS["vault"]]["issues"][0]
    assert gap["state"] == "OPEN" and gap["milestone"] == MILESTONES[0]
    assert (gh_repos.dev / "review/T3-review.md").read_bytes().endswith(b"\n\n# T3\r\n")
