import json
import os
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from conftest import ENTRY_ID, commit_count, commit_file, git_run, run_wiki, write_config
from rwiki.config import load_config
from rwiki.lint import lint
from rwiki.pages import write_page
from rwiki.server import create_app


def test_wiki_root_override_order(tmp_path, monkeypatch):
    path = write_config(tmp_path / "c.json", tmp_path / "from-file")
    monkeypatch.delenv("RWIKI_WIKI_ROOT", raising=False)
    assert load_config(path).wiki_root == (tmp_path / "from-file").resolve()
    monkeypatch.setenv("RWIKI_WIKI_ROOT", str(tmp_path / "from-env"))
    assert load_config(path).wiki_root == (tmp_path / "from-env").resolve()
    assert load_config(path, tmp_path / "from-flag").wiki_root == (tmp_path / "from-flag").resolve()
    result = run_wiki(tmp_path, "--config", str(path), "--wiki-root", str(tmp_path / "flag-wiki"), "init",
                      env={**os.environ, "RWIKI_WIKI_ROOT": str(tmp_path / "env-wiki")})
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "flag-wiki" / "log.md").is_file() and not (tmp_path / "env-wiki").exists()


def lint_fixture(wiki_repo, extra_link=""):
    config, config_path, vault = wiki_repo
    wiki = config.wiki_root
    (vault / ".gitignore").write_text("/维护记录/\n/画廊/\n", encoding="utf-8")
    with (wiki / ".gitignore").open("a", encoding="utf-8", newline="\n") as stream:
        stream.write("# >>> push-guard gpl\n/methods/scp/code/\n/methods/scp/source/\n# <<< push-guard gpl\n")
    write_page(wiki / "projects/p.md", {"type": "project", "slug": "p", "title": "课题", "templates": []},
               "# 课题\n\n证据 [[../维护记录/2026-10-25-x/回执.json]]，源码 [[methods/scp/code/run.R]]"
               f"{extra_link}\n")
    return config, config_path, vault


def test_lint_ci_reports_ignored_missing_as_local_only(wiki_repo):
    config, config_path, vault = lint_fixture(wiki_repo, "，缺页 [[methods/missing]]")
    plain = lint(config)
    assert sum(line.startswith("ERROR ") for line in plain) == 3
    ci = lint(config, ci=True)
    assert [line for line in ci if line.startswith("ERROR ")] == [
        "ERROR projects/p.md: 断链或嵌入目标不存在: methods/missing"]
    assert sorted(line for line in ci if line.startswith("LOCAL-ONLY ")) == [
        "LOCAL-ONLY projects/p.md: 断链或嵌入目标不存在: ../维护记录/2026-10-25-x/回执.json",
        "LOCAL-ONLY projects/p.md: 断链或嵌入目标不存在: methods/scp/code/run.R"]
    result = run_wiki(vault, "--config", str(config_path), "lint", "--ci")
    assert result.returncode == 1 and "LOCAL-ONLY" in result.stdout


def test_lint_ci_passes_when_only_local_content_is_missing(wiki_repo):
    config, config_path, vault = lint_fixture(wiki_repo)
    assert run_wiki(vault, "--config", str(config_path), "lint").returncode == 1
    result = run_wiki(vault, "--config", str(config_path), "lint", "--ci")
    assert result.returncode == 0, result.stdout
    assert result.stdout.count("LOCAL-ONLY ") == 2 and result.stdout.rstrip().endswith("OK")


def test_guard_range_hit_exits_one(git_pair, tmp_path):
    work = git_pair.work
    config_path = write_config(tmp_path / "c.json", tmp_path / "no-wiki")
    git_run(work, "checkout", "-q", "-b", "task/a-P1-b")
    clean = run_wiki(work, "--config", str(config_path), "gh", "guard", "--range", "origin/main..HEAD")
    assert clean.returncode == 0 and clean.stdout.strip() == "OK", clean.stderr
    sha = commit_file(work, "qa/report.md", "输出在 E:\\research-wiki-env\\tmp\\x\n")
    result = run_wiki(work, "--config", str(config_path), "gh", "guard", "--range", "origin/main..HEAD")
    assert result.returncode == 1
    assert result.stdout.splitlines() == [f"abs-path\tqa/report.md\t{sha}\tE:\\"]
    dry = run_wiki(work, "--config", str(config_path), "gh", "guard")
    assert dry.returncode == 1 and "qa/report.md" in dry.stdout


def path_without_gh(tmp_path) -> str:
    entries = [entry for entry in os.environ["PATH"].split(os.pathsep)
               if entry and not any((Path(entry) / f"gh{ext}").exists() for ext in ("", ".exe", ".cmd", ".bat"))]
    return os.pathsep.join(entries)


def test_guard_and_protect_baseline_run_without_gh(wiki_repo, tmp_path):
    config, config_path, vault = wiki_repo
    env = {**os.environ, "PATH": path_without_gh(tmp_path)}
    assert shutil.which("gh", path=env["PATH"]) is None
    (config.wiki_root / "methods/a.md").write_text("---\ntype: method\n---\n<!-- user:start -->作者\r\n<!-- user:end -->\n",
                                                   encoding="utf-8", newline="")
    git_run(vault, "add", "-A")
    git_run(vault, "commit", "-q", "-m", "page")
    made = run_wiki(vault, "--config", str(config_path), "gh", "protect-baseline", env=env)
    assert made.returncode == 0, made.stderr
    recorded = json.loads((config.wiki_root / ".protected-hashes.json").read_text(encoding="utf-8"))
    assert list(recorded["files"]) == ["methods/a.md"]
    check = run_wiki(vault, "--config", str(config_path), "gh", "protect-baseline", "--check", env=env)
    assert check.returncode == 0 and check.stdout.strip() == "OK", check.stderr
    page = config.wiki_root / "methods/a.md"
    page.write_bytes(page.read_bytes().replace(b"\r\n", b"\n"))
    changed = run_wiki(vault, "--config", str(config_path), "gh", "protect-baseline", "--check", env=env)
    assert changed.returncode == 1 and "methods/a.md" in changed.stdout
    guard = run_wiki(vault, "--config", str(config_path), "gh", "guard", "--range", "HEAD~1..HEAD", env=env)
    assert guard.returncode == 0, guard.stderr
    synced = run_wiki(vault, "--config", str(config_path), "gh", "guard", "--sync-ignore", env=env)
    assert synced.returncode == 0, synced.stderr


def test_server_writes_commit_on_main_and_long_branches(ingested):
    """v2（2026-10-27）：网页写入在 main 与批次分支上直接提交（不再要求先 start-task）。"""
    config, _ = ingested
    root = config.wiki_root
    git_run(root, "branch", "-m", "main")
    with TestClient(create_app(config)) as client:
        for index, branch in enumerate(("main", "ingest/scp-wave3", "project/glaucoma")):
            if branch != "main":
                git_run(root, "checkout", "-q", "-B", branch)
            count = commit_count(root)
            response = client.post(f"/api/layouts/{ENTRY_ID}/favorite", json={"value": index % 2 == 0})
            assert response.status_code == 200, response.text
            assert commit_count(root) == count + 1
            assert git_run(root, "status", "--porcelain").strip() == ""
