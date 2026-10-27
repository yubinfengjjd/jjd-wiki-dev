"""dev CI 按改动路径跳过重步骤，但检查必须始终上报（Feature: lite-ci）。"""
import importlib.util
import random

import yaml

from conftest import DEV_ROOT

CI = DEV_ROOT / ".github/workflows/ci.yml"
spec = importlib.util.spec_from_file_location("ci_scope", DEV_ROOT / "ci/ci_scope.py")
ci_scope = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci_scope)


def workflow():
    data = yaml.safe_load(CI.read_text(encoding="utf-8"))
    return data, data.get("on", data.get(True))  # YAML 1.1 把 on 解析成 True


def steps():
    data, _ = workflow()
    return data["jobs"]["test"]["steps"]


def step(name):
    return next(s for s in steps() if s.get("name") == name)


def test_no_workflow_level_path_filter():
    # workflow 级 paths 过滤会让检查停在 Pending 并卡住合并门禁。
    _, triggers = workflow()
    for event, conf in triggers.items():
        assert not (isinstance(conf, dict) and ({"paths", "paths-ignore"} & set(conf))), event


def test_full_run_triggers_exist():
    _, triggers = workflow()
    assert "schedule" in triggers and "workflow_dispatch" in triggers
    assert {"pull_request", "push"} <= set(triggers)


def test_job_has_no_condition():
    data, _ = workflow()
    assert "if" not in data["jobs"]["test"]


def test_heavy_steps_gated_and_guard_not():
    names = [s.get("name") for s in steps()]
    assert names.index("改动范围") < names.index("pytest")
    assert "steps.scope.outputs.pytest == 'true'" in step("pytest")["if"]
    assert "steps.scope.outputs.frontend == 'true'" in step("前端测试")["if"]
    assert "steps.scope" not in step("推送防泄漏检查").get("if", "")


def reference(paths, event):
    if event not in ("pull_request", "push"):
        return {"pytest": True, "frontend": True}
    if event == "push":
        return {"pytest": False, "frontend": False}
    if not paths or any(p.startswith((".github/workflows/", "ci/")) for p in paths):
        return {"pytest": True, "frontend": True}
    docs = lambda p: (p.startswith(("review/", ".github/ISSUE_TEMPLATE/")) or p == ".github/pull_request_template.md"
                      or ("/" not in p and p.endswith(".md")))
    front = lambda p: p.startswith("frontend/")
    return {"pytest": any(not docs(p) and not front(p) for p in paths), "frontend": any(front(p) for p in paths)}


POOL = ["review/a.md", "review/子目录/记录.md", "README.md", "NOTES.md", ".github/ISSUE_TEMPLATE/task.md",
        ".github/pull_request_template.md", ".github/workflows/ci.yml", "ci/config.ci.json", "ci/ci_scope.py",
        "frontend/src/App.tsx", "frontend/package.json", "staged/research-wiki/rwiki/ghflow.py",
        "staged/research-wiki/SKILL.md", "spec/scenario_taxonomy.yaml", "qa/cdp.mjs", "obsidian-neural-view/a.js",
        ".gitignore", ".push-guard-allow", "staged/research-wiki/requirements.lock.txt", "docs/x.md"]


def test_property_scope_matches_reference():
    """Feature: lite-ci, Property: 改动范围分类与参考模型一致"""
    for seed in range(300):
        rng = random.Random(seed)
        paths = rng.sample(POOL, rng.randint(0, 5))
        event = rng.choice(["pull_request", "push", "schedule", "workflow_dispatch"])
        assert ci_scope.scope(paths, event) == reference(paths, event), f"seed={seed} {event} {paths}"


def test_docs_only_pr_skips_heavy_steps():
    assert ci_scope.scope(["review/x.md", "README.md"], "pull_request") == {"pytest": False, "frontend": False}


def test_empty_pr_diff_is_fail_safe():
    assert ci_scope.scope([], "pull_request") == {"pytest": True, "frontend": True}


def test_outputs_written(tmp_path):
    out = tmp_path / "out.txt"
    ci_scope.write_outputs({"pytest": True, "frontend": False}, out)
    assert out.read_text(encoding="utf-8").splitlines() == ["pytest=true", "frontend=false"]
