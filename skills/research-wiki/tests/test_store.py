from pathlib import Path

from conftest import commit_count, run_cli
from rwiki.pages import write_page
from rwiki.store import git, init, save


def test_init_creates_rules_layout_log_and_commit(workspace):
    config, _ = workspace
    root = config.wiki_root
    for directory in ("layouts", "templates", "methods", "interfaces", "chart-types", "projects"):
        assert (root / directory).is_dir()
    source = Path(__file__).resolve().parents[1] / "assets/AGENTS.md"
    assert (root / "AGENTS.md").read_bytes() == source.read_bytes()
    assert (root / "CLAUDE.md").read_bytes() == b"@AGENTS.md\n"
    assert (root / "log.md").read_text(encoding="utf-8").startswith("# 操作日志\n")
    assert "UTC] init" in (root / "log.md").read_text(encoding="utf-8")
    assert commit_count(root) == 1


def test_save_without_changes_does_not_touch_log_or_commit(workspace):
    config, _ = workspace
    log = (config.wiki_root / "log.md").read_bytes()
    save(config, "no change")
    assert commit_count(config.wiki_root) == 1
    assert (config.wiki_root / "log.md").read_bytes() == log


def test_init_updates_existing_rules_preserving_content_and_commits_once(workspace):
    config, config_path = workspace
    root = config.wiki_root
    (root / "author.txt").write_bytes(b"author content\n")
    (root / "AGENTS.md").write_text("old rules\n", encoding="utf-8")
    (root / "CLAUDE.md").write_text("old claude\n", encoding="utf-8")
    save(config, "author snapshot")
    before = {p.relative_to(root).as_posix(): p.read_bytes()
              for p in root.rglob('*') if p.is_file() and '.git' not in p.parts}
    count = commit_count(root)
    result = run_cli(config_path, "init")
    assert result.returncode == 0, result.stderr
    assets = Path(__file__).resolve().parents[1] / "assets"
    for filename in ("AGENTS.md", "CLAUDE.md"):
        assert (root / filename).read_bytes() == (assets / filename).read_bytes()
    assert commit_count(root) == count + 1
    assert git(root, "log", "-1", "--format=%s").strip() == "update rules"
    changed = {name for name, data in before.items() if (root / name).read_bytes() != data}
    assert changed == {"AGENTS.md", "CLAUDE.md", "log.md"}
    assert git(root, "status", "--porcelain").strip() == ""

    after = {p.relative_to(root).as_posix(): p.read_bytes()
             for p in root.rglob('*') if p.is_file() and '.git' not in p.parts}
    again = run_cli(config_path, "init")
    assert again.returncode == 0, again.stderr
    assert commit_count(root) == count + 1
    assert after == {p.relative_to(root).as_posix(): p.read_bytes()
                     for p in root.rglob('*') if p.is_file() and '.git' not in p.parts}


def test_save_git_failure_reports_stderr(workspace):
    config, config_path = workspace
    (config.wiki_root / ".git").rename(config.wiki_root / "removed-git")
    result = run_cli(config_path, "save", "failure")
    assert result.returncode == 1
    assert "not a git repository" in result.stderr
    assert "Traceback" not in result.stderr


def test_index_groups_and_sorts_all_page_types(workspace):
    config, _ = workspace
    root = config.wiki_root
    for page_id, title, status in (("a", "Z title", "ready"), ("b", "A title", "ready"),
                                   ("c", "C title", "archived")):
        write_page(root / f"templates/{page_id}.md",
                   {"type": "template", "id": page_id, "title": title, "status": status,
                    "layouts": [], "panels": [], "language": "python", "chart_types": [],
                    "tags": [], "favorite": False},
                   "<!-- facts:start -->\n<!-- facts:end -->\n<!-- user:start -->\n<!-- user:end -->\n")
    write_page(root / "chart-types/bar.md", {"type": "chart-type", "slug": "bar", "title": "bar"}, "")
    write_page(root / "projects/p.md", {"type": "project", "slug": "p", "title": "课题", "templates": []}, "")
    save(config, "add pages")
    index = (root / "index.md").read_text(encoding="utf-8")
    assert index.startswith("<!-- 由 wiki.py 生成，不要手改 -->\n")
    ready = index.split("## 模板\n", 1)[1].split("### ready\n", 1)[1].split("### archived\n", 1)[0]
    assert ready.strip().splitlines() == ["- [[templates/b|A title]]", "- [[templates/a|Z title]]"]
    for expected in ("- [[templates/c|C title]]",
                     "## 图型\n\n- [[chart-types/bar|bar]]", "## 课题\n\n- [[projects/p|课题]]"):
        assert expected in index
    assert commit_count(root) == 2
