import json

from conftest import commit_file, gh_writes, run_wiki
from rwiki.ghflow import preflight


def test_preflight_reports_state_and_blockers_read_only(gh_repos):
    fake = gh_repos.gh
    state = fake.state()
    state["repos"]["tester/research-wiki-vault"]["secrets"] = ["DEV_DEPLOY_KEY"]
    fake.write(state)
    report = preflight(gh_repos.config)
    assert report["gh"]["login"] == "tester" and report["owner"] == "tester"
    assert report["dev_deploy_key"] is True and report["blockers"] == []
    assert report["protection"] == {"dev": "local", "vault": "local"}
    assert report["repos"]["vault"]["local"] == {"branch": "main", "uncommitted": 0, "tracked_changes": 0}
    assert report["repos"]["dev"]["pending"]["mode"] == "incremental"
    commit_file(gh_repos.dev, "qa/x.md", "见 E:\\research-wiki\\x\n")
    state = fake.state()
    state["repos"]["tester/research-wiki-vault"]["visibility"] = "PUBLIC"
    fake.write(state)
    result = run_wiki(gh_repos.vault, "--config", str(gh_repos.config_path), "gh", "preflight")
    assert result.returncode == 1, result.stderr
    report = json.loads(result.stdout)
    assert any("PUBLIC" in line for line in report["blockers"])
    assert any("Push_Guard" in line for line in report["blockers"])
    assert [f["path"] for f in report["repos"]["dev"]["pending"]["guard"]] == ["qa/x.md"]
    assert gh_writes(fake) == []
