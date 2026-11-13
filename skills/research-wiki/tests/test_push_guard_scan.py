import random
import subprocess

from conftest import commit_file, git_run, install_test_hook, write_config
from rwiki.config import load_config
from rwiki.push_guard import SPDX, load_rules, scan

SEED = 20261028
ITERATIONS = 100
HOOK_EVERY = 4
# (规则, 路径模板, 内容)；内容超过 push_guard.max_file_mb 对应的 209 字节即命中 size。
VIOLATIONS = (
    ("private-data", "private-data/e{n}/data.csv", b"private\n"),
    ("abs-path", "docs/路径 {n}.txt", "见 E:\\research-wiki\\证据\n".encode("utf-8")),
    ("abs-path", "qa/home{n}.md", b"run in /Users/alice/x\n"),
    ("size", "data/big{n}.bin", b"x" * 400),
    ("project-data", "课题/wiki-use/_project/t{n}.csv", b"a,b\n1,2\n"),
    ("secret", "src/g{n}.txt", ("-----BEGIN " + "RSA PRIVATE KEY-----\n").encode()),
    ("secret", "vendor/{n}/id_ed25519", b"private-key\n"),
    ("abs-path", "links/s{n}.lnk", b"L\0\0\0binary"),
)


def test_scan_reports_every_violation_ever_added(git_pair, tmp_path):
    """Feature: github-structured-workflow, Property 3: 推送范围扫描完备"""
    work = git_pair.work
    config_path = write_config(tmp_path / "guard-config.json", tmp_path / "no-wiki",
                               push_guard={"max_file_mb": 0.0002})
    rules = load_rules(load_config(config_path), work)
    install_test_hook(work, config_path)
    rng = random.Random(SEED)
    for iteration in range(ITERATIONS):
        branch = f"b{iteration}"
        git_run(work, "checkout", "-q", "-b", branch, "main")
        expected = set()
        live = []
        for step in range(rng.randint(1, 4)):
            choice = rng.random()
            if live and choice < 0.3:
                path = live.pop(rng.randrange(len(live)))
                git_run(work, "rm", "-q", "--", path)
                git_run(work, "commit", "-q", "-m", f"delete {path}")
            elif live and choice < 0.5:
                path = rng.choice(live)
                commit_file(work, path, f"clean {step}\n".encode(), f"rewrite {path}")
            elif choice < 0.65:
                commit_file(work, f"ok/{iteration}-{step}.md", f"clean {step}\n", "clean")
            else:
                rule, template, data = rng.choice(VIOLATIONS)
                path = template.format(n=f"{iteration}-{step}")
                commit_file(work, path, data, f"add {path}")
                expected.add((path, rule))
                live.append(path)
        if not expected:
            rule, template, data = rng.choice(VIOLATIONS)
            path = template.format(n=f"{iteration}-x")
            commit_file(work, path, data, f"add {path}")
            expected.add((path, rule))
        head = git_run(work, "rev-parse", "HEAD").strip()
        found = {(item["path"], item["rule"]) for item in scan(work, f"{head} --not --remotes=origin", rules)}
        assert expected <= found, f"seed={SEED} iteration={iteration} missing={expected - found}"
        if iteration % HOOK_EVERY == 0:
            pushed = subprocess.run(["git", "-C", str(work), "push", "-q", "origin", branch],
                                    capture_output=True, text=True, encoding="utf-8")
            assert pushed.returncode != 0, f"seed={SEED} iteration={iteration}"
            assert git_run(work, "ls-remote", "origin", f"refs/heads/{branch}") == "", \
                f"seed={SEED} iteration={iteration}"
        git_run(work, "checkout", "-q", "main")


def test_clean_push_passes_hook(git_pair, tmp_path):
    work = git_pair.work
    config_path = write_config(tmp_path / "guard-config.json", tmp_path / "no-wiki")
    install_test_hook(work, config_path)
    git_run(work, "checkout", "-q", "-b", "clean")
    commit_file(work, "notes/说明 1.md", "只有相对路径 docs/x\n", "clean")
    git_run(work, "push", "-q", "origin", "clean")
    assert git_run(work, "ls-remote", "origin", "refs/heads/clean").strip()
