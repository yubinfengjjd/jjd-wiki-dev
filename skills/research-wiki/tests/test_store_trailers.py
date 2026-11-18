import subprocess

from conftest import git_run
from rwiki.store import save, trailers


def parse_trailers(vault) -> dict:
    message = git_run(vault, "log", "-1", "--format=%B")
    parsed = subprocess.run(["git", "-C", str(vault), "interpret-trailers", "--parse"], input=message,
                            capture_output=True, text=True, encoding="utf-8", check=True).stdout
    return dict(line.split(": ", 1) for line in parsed.splitlines() if ": " in line)


def test_trailers_round_trip(wiki_repo, monkeypatch):
    config, _, vault = wiki_repo
    wiki = config.wiki_root
    monkeypatch.setenv("RWIKI_AGENT", "backend-engine")
    (wiki / "methods").mkdir(parents=True, exist_ok=True)
    (wiki / "methods/a.md").write_text("x\n", encoding="utf-8")
    save(config, "写入 a")
    values = parse_trailers(vault)
    assert values["Agent"] == "backend-engine"
    assert "methods/a.md" in values["Pages"]
    assert git_run(vault, "log", "-1", "--format=%s").strip() == "写入 a"


def test_trailers_without_issue_or_agent():
    assert trailers(None, None, ["a.md"]) == "Pages: a.md"
    assert trailers(3, "codex", [f"p{i}.md" for i in range(22)]).splitlines()[-1].endswith("p19.md … (+2)")
