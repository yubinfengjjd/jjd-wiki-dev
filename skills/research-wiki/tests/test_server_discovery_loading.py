import json
from collections import Counter

from fastapi.testclient import TestClient

from rwiki import pages, server
from rwiki.pages import write_page
from rwiki.read_cache import read_session


def test_read_session_does_not_share_mutable_meta_and_preserves_crlf(tmp_path):
    target = tmp_path / "page.md"
    original = b"---\r\ntype: project\r\ntitle: before\r\ntags: [one]\r\n---\r\nauthor\r\n"
    target.write_bytes(original)
    with read_session():
        meta, body = pages.read_page(target)
        meta["tags"].append("uncommitted mutation")
        assert pages.read_page(target)[0]["tags"] == ["one"]
        assert body == "author\r\n"
        assert target.read_bytes() == original
        target.write_bytes(original.replace(b"before", b"after-edit"))
        assert pages.read_page(target)[0]["title"] == "after-edit"


def add_page(config, folder, name, **extra):
    meta = {"type": "method" if folder == "methods" else "project", "id": name,
            "title": name, **extra}
    write_page(config.wiki_root / folder / f"{name}.md", meta, f"# {name}\n")


def test_list_parses_each_page_once_and_next_request_sees_edits(wiki_repo, monkeypatch):
    config, _, _ = wiki_repo
    for n in range(4):
        add_page(config, "methods", f"method-{n}", status="draft", method_kind="technical")
    for n in range(8):
        add_page(config, "projects", f"project-{n}")
    original = pages.parse_page
    parsed = Counter()

    def counted(text):
        parsed[text] += 1
        return original(text)

    monkeypatch.setattr(pages, "parse_page", counted)
    with TestClient(server.create_app(config)) as client:
        result = client.get("/api/pages")
        assert result.status_code == 200
        assert max(parsed.values()) == 1, "one request must not reparse the whole library per method"
        add_page(config, "projects", "project-0", title="changed outside the server")
        again = client.get("/api/pages").json()
        assert next(p for p in again if p["path"] == "projects/project-0.md")["meta"]["title"] == "changed outside the server"


def test_light_listing_never_runs_evidence_checks_or_grants_ready(wiki_repo, monkeypatch):
    config, _, _ = wiki_repo
    add_page(config, "templates", "t", type="template", status="ready", tags=[],
             language="python", favorite=False, chart_types=["bar"], sources=[])

    def forbidden(*args, **kwargs):
        raise AssertionError("light listing must defer evidence verification")

    monkeypatch.setattr(server, "workflow_snapshot", forbidden)
    monkeypatch.setattr(server, "replay_available", forbidden)
    with TestClient(server.create_app(config), raise_server_exceptions=False) as client:
        result = client.get("/api/pages?light=true")
        assert result.status_code == 200
        item = next(p for p in result.json() if p["path"] == "templates/t.md")
        assert item["meta"]["status"] == "ready", "stored author status is preserved"
        assert item["workflow"]["stage"] == "checking"
        assert item["workflow"]["queue"] is None
        assert item["implementation_status"] == []
        assert item["preview"]["kind"] != "replay"


def test_source_catalog_is_read_only_and_deduplicates_only_exact_source_item(wiki_repo):
    config, _, _ = wiki_repo
    for source_id in ("figureya", "figureya-archive"):
        write_page(config.wiki_root / "sources" / f"{source_id}.md",
                   {"type": "source", "id": source_id, "title": source_id,
                    "license": "CC-BY-NC-SA-4.0", "trusted": True}, "# source\n")
        target = config.wiki_root / "sources" / source_id / "items.jsonl"
        target.parent.mkdir(parents=True, exist_ok=True)
        items = [{"id": f"{source_id}:FigureYa1", "source": source_id, "item": "FigureYa1",
                  "title": "生存曲线", "recipe": "figureya-1", "inputs": [],
                  "requirement": "比较生存概率", "requires": []}]
        target.write_text("\n".join(map(json.dumps, items)), encoding="utf-8")
    add_page(config, "recipes", "figureya-1", type="recipe", status="draft",
             source={"id": "figureya", "item": "FigureYa1"})
    with TestClient(server.create_app(config)) as client:
        result = client.get("/api/source-items")
        assert result.status_code == 200
        records = result.json()
        assert [r["id"] for r in records] == ["figureya-archive:FigureYa1"]
        assert records[0]["level"] == "L0" and records[0]["usable"] is False
        assert records[0]["run"] == "none"
        assert records[0]["page"] == "sources/figureya-archive.md"
