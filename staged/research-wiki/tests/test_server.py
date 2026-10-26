import json
import os
import signal
import socket
import subprocess
import sys
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from conftest import ENTRY_ID, SKILL_ROOT, commit_count
from rwiki.pages import get_block, read_page, set_block, write_page
from rwiki.server import create_app


@pytest.fixture
def web(ingested):
    config, config_path = ingested
    with TestClient(create_app(config)) as client:
        yield config, config_path, client


def test_read_routes(web):
    config, _, client = web
    path = f"layouts/{ENTRY_ID}.md"
    meta, body = read_page(config.wiki_root / path)
    listed = client.get("/api/pages").json()
    assert {item["path"] for item in listed} == {
        file.relative_to(config.wiki_root).as_posix()
        for directory in ("layouts", "templates", "methods", "interfaces", "chart-types", "projects")
        for file in (config.wiki_root / directory).glob("*.md")}
    assert next(item["meta"] for item in listed if item["path"] == path) == meta
    page = client.get("/api/page", params={"path": path}).json()
    assert page["meta"] == meta and page["body"] == body
    assert page["gallery"] == json.loads((config.gallery_root / meta["gallery_entry"] / "meta.json").read_text(encoding="utf-8"))
    hub_path = f"chart-types/{meta['chart_types'][0]}.md"
    for slug, title in (("z", "Zebra"), ("a", "Alpha")):
        write_page(config.wiki_root / f"projects/{slug}.md",
                   {"type": "project", "title": title}, f"[[{hub_path[:-3]}]]\n")
    hub = client.get("/api/page", params={"path": hub_path}).json()
    assert hub["gallery"] is None
    assert [item["title"] for item in hub["backlinks"]] == sorted(["Alpha", "Zebra", meta["title"]])
    assert client.get("/api/taxonomy").status_code == 404
    # Entries in the same minute keep append order: the last written comes first.
    with (config.wiki_root / "log.md").open("a", encoding="utf-8") as stream:
        stream.write("\n## [2099-01-01 00:00 UTC] earlier\n## [2099-01-01 00:00 UTC] newest\n")
    logs = client.get("/api/log").json()
    assert [item["message"] for item in logs[:2]] == ["newest", "earlier"]
    assert logs[-1]["message"] == "init"


def test_graph_filters_and_deduplicates(web):
    config, _, client = web
    a, b = "projects/a.md", "projects/b.md"
    write_page(config.wiki_root / a, {"type": "project", "title": "A"},
               "[[projects/b]] [[projects/b|again]] [[projects/a]] ![[projects/picture.png]]")
    write_page(config.wiki_root / b, {"type": "project", "title": "B"}, "[[projects/a]]")
    graph = client.get("/api/graph").json()
    assert any(node["id"] == f"layouts/{ENTRY_ID}.md" and node["type"] == "layout"
               for node in graph["nodes"])
    assert {"source": a, "target": b, "kind": "link"} in graph["links"]
    assert len([edge for edge in graph["links"] if a in edge.values()]) == 1
    assert all(edge["source"] != edge["target"] for edge in graph["links"])
    assert all("picture" not in str(edge) for edge in graph["links"])


def test_panel_template_has_no_gallery_or_signoff_and_supports_common_actions(web):
    config, _, client = web
    tid = ENTRY_ID + "--bar"
    layout, _ = read_page(config.wiki_root / f"layouts/{ENTRY_ID}.md")
    meta = {"type": "template", "id": tid, "title": "bar panel", "status": "draft",
            "layouts": [ENTRY_ID], "panels": ["A", "D"], "chart_types": ["bar"],
            "language": "python", "tags": layout["tags"], "favorite": False}
    body = "# bar\n\n<!-- facts:start -->\n<!-- facts:end -->\n<!-- user:start -->\n<!-- user:end -->\n"
    write_page(config.wiki_root / f"templates/{tid}.md", meta, body)
    assert client.get("/api/page", params={"path": f"templates/{tid}.md"}).json()["gallery"] is None
    for action in ("signoff", "reject"):
        result = client.post(f"/api/templates/{tid}/{action}", json={"reason": "test"})
        assert result.status_code == 404
    for action, payload in (("favorite", {"value": True}), ("note", {"text": "panel note"}),
                             ("tags", {"tags": ["单细胞"]}),
                             ("archive", None), ("restore", None)):
        count = commit_count(config.wiki_root)
        result = client.post(f"/api/templates/{tid}/{action}", json=payload)
        assert result.status_code == 200, result.text
        assert commit_count(config.wiki_root) == count + 1
    page = client.get("/api/page", params={"path": f"templates/{tid}.md"}).json()
    assert page["meta"]["status"] == "draft" and page["meta"]["favorite"]
    assert "panel note" in get_block(page["body"], "user")
    assert f"[[layouts/{ENTRY_ID}|" in get_block(page["body"], "facts")


@pytest.mark.parametrize("action,payload", [
    ("signoff", None), ("reject", {"reason": "需要调整"}),
    ("tags", {"tags": [" 自定义 ", "自定义", "新标签"]}), ("favorite", {"value": True}),
    ("note", {"text": "我的备注\n## 标题"}), ("archive", None), ("restore", None),
])
def test_write_success_real_commit(web, action, payload):
    config, _, client = web
    path = config.wiki_root / f"layouts/{ENTRY_ID}.md"
    meta, body = read_page(path)
    if action == "restore":
        assert client.post(f"/api/layouts/{ENTRY_ID}/archive").status_code == 200
        meta, body = read_page(path)
    if action == "reject":
        assert client.post(f"/api/layouts/{ENTRY_ID}/signoff").status_code == 200
        meta, body = read_page(path)
    gallery_path = config.gallery_root / meta["gallery_entry"] / "meta.json"
    gallery_before = json.loads(gallery_path.read_text(encoding="utf-8"))
    count = commit_count(config.wiki_root)
    result = client.post(f"/api/layouts/{ENTRY_ID}/{action}", json=payload)
    assert result.status_code == 200, result.text
    assert commit_count(config.wiki_root) == count + 1
    after, text = read_page(path)
    assert result.json() == client.get("/api/page", params={"path": f"layouts/{ENTRY_ID}.md"}).json()
    if action in ("signoff", "reject"):
        gallery_after = json.loads(gallery_path.read_text(encoding="utf-8"))
        assert set(gallery_after) - {"approved_version"} == set(gallery_before) - {"approved_version"}
        assert {k: v for k, v in gallery_after.items() if k not in ("status", "updated_at", "approved_version")} == {k: v for k, v in gallery_before.items() if k not in ("status", "updated_at", "approved_version")}
        assert gallery_after["status"] == ("approved" if action == "signoff" else "draft")
        # The approved version is an explicit fact, not inferred from the page status.
        assert gallery_after["approved_version"] == (gallery_after["version"] if action == "signoff" else None)
        assert gallery_after["updated_at"].endswith("+00:00")
        assert gallery_path.read_bytes().endswith(b"\n")
        assert gallery_path.read_text(encoding="utf-8") == json.dumps(gallery_after, ensure_ascii=False, indent=2) + "\n"
        assert after["status"] == ("pending_template" if action == "signoff" else "pending_signoff")
    elif action == "tags":
        assert after["tags"] == ["自定义", "新标签"]
        assert "- 标签：自定义、新标签" in get_block(text, "facts")
        assert not (config.wiki_root / "scenarios").exists()
    elif action == "note":
        assert get_block(text, "user") == f"\n{payload['text']}\n"
        assert set_block(text, "user", "") == set_block(body, "user", "")
    elif action == "favorite":
        assert after["favorite"] is True
    elif action == "archive":
        assert after["status"] == "archived" and after["archived_from"] == meta["status"]
    else:
        assert after["status"] == meta["archived_from"] and "archived_from" not in after
    message = subprocess.check_output(["git", "-C", str(config.wiki_root), "log", "-1", "--format=%s"], text=True, encoding="utf-8").strip()
    assert message == f"{action} {ENTRY_ID}" + (": 需要调整" if action == "reject" else "")


def test_errors_are_4xx_without_commits(web):
    config, _, client = web
    count = commit_count(config.wiki_root)
    for action, body in [("reject", {"reason": ""}), ("reject", {"reason": "  "}),
                         ("tags", {"tags": "single-cell"}),
                         ("tags", {"tags": ["valid", 1]}),
                         ("tags", {"tags": None}),
                         ("favorite", {"value": "true"}), ("note", {})]:
        response = client.post(f"/api/layouts/{ENTRY_ID}/{action}", json=body)
        assert response.status_code == 422
        assert isinstance(response.json()["detail"], str)
    assert client.post(f"/api/layouts/{ENTRY_ID}/restore").status_code == 409
    for action in ("signoff", "reject", "tags", "favorite", "note", "archive", "restore"):
        body = {"reject": {"reason": "x"}, "tags": {"tags": ["任意标签"]}, "favorite": {"value": True}, "note": {"text": "x"}}.get(action)
        assert client.post(f"/api/layouts/missing/{action}", json=body).status_code == 404
    for path in ("../config.json", "index.md", "layouts/missing.md", str(config.taxonomy)):
        assert client.get("/api/page", params={"path": path}).status_code == 404
    assert client.get("/api/page", params={"path": str(config.wiki_root / f"layouts/{ENTRY_ID}.md")}).status_code == 404
    assert commit_count(config.wiki_root) == count
    assert client.post(f"/api/layouts/{ENTRY_ID}/signoff").status_code == 200
    assert client.post(f"/api/layouts/{ENTRY_ID}/signoff").status_code == 409
    assert client.post(f"/api/layouts/{ENTRY_ID}/archive").status_code == 200
    assert client.post(f"/api/layouts/{ENTRY_ID}/archive").status_code == 409
    assert client.post(f"/api/layouts/{ENTRY_ID}/reject", json={"reason": "x"}).status_code == 409


@pytest.mark.parametrize("tags,expected", [([], []), (["任意未登记标签"], ["任意未登记标签"]),
                                          ([" a ", "a", " b"], ["a", "b"])])
def test_tags_are_free_strings_and_allow_empty_list(web, tags, expected):
    config, _, client = web
    response = client.post(f"/api/layouts/{ENTRY_ID}/tags", json={"tags": tags})
    assert response.status_code == 200, response.text
    assert response.json()["meta"]["tags"] == expected
    assert read_page(config.wiki_root / f"layouts/{ENTRY_ID}.md")[0]["tags"] == expected
    assert client.post(f"/api/layouts/{ENTRY_ID}/scenarios", json={"primary": [], "free": []}).status_code in (404, 405)


def test_wiki_error_reaches_client_as_detail(web):
    config, _, client = web
    (config.wiki_root / ".git").rename(config.wiki_root / "removed-git")
    response = client.post(f"/api/layouts/{ENTRY_ID}/favorite", json={"value": True})
    assert response.status_code == 500
    assert "git" in response.json()["detail"]


def test_files_and_spa(web):
    config, _, client = web
    assert client.get("/files/wiki/AGENTS.md").content == (config.wiki_root / "AGENTS.md").read_bytes()
    gallery_file = next(config.gallery_root.rglob("meta.json"))
    assert client.get("/files/gallery/" + gallery_file.relative_to(config.gallery_root).as_posix()).content == gallery_file.read_bytes()
    for namespace in ("wiki", "gallery"):
        for value in ("../config.json", "%2e%2e/config.json", "%2e%2e%5cconfig.json", str(config.taxonomy).replace("\\", "/"), "/outside", "missing"):
            assert client.get(f"/files/{namespace}/{value}").status_code == 404
        absolute = config.wiki_root / "AGENTS.md" if namespace == "wiki" else gallery_file
        assert client.get(f"/files/{namespace}/" + absolute.as_posix()).status_code == 404
    for url in ("/api", "/api/missing", "/files", "/files/missing"):
        assert client.get(url).status_code == 404
    index = (SKILL_ROOT / "app/index.html").read_bytes()
    for url in ("/", "/missing", "/%2e%2e/config.json"):
        assert client.get(url).content == index
    asset = next((SKILL_ROOT / "app/assets").iterdir())
    assert client.get("/assets/" + asset.name).content == asset.read_bytes()


def test_cli_serve_loopback(web):
    config, config_path, _ = web
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    values = json.loads(config_path.read_text(encoding="utf-8"))
    values["port"] = port
    config_path.write_text(json.dumps(values), encoding="utf-8")
    process = subprocess.Popen([sys.executable, "-X", "utf8", str(SKILL_ROOT / "wiki.py"), "--config", str(config_path), "serve", "--no-browser"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
    listener_pid = None
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if process.poll() is not None:
                pytest.fail(process.communicate()[1])
            try:
                response = httpx.get(f"http://127.0.0.1:{port}/api/pages", timeout=1, trust_env=False)
            except (httpx.ConnectError, httpx.ConnectTimeout):
                time.sleep(0.05)
                continue
            assert response.status_code == 200 and response.json()
            break
        else:
            pytest.fail("serve did not become ready")
        # netstat is localized; only its ASCII address/state columns are parsed.
        listeners = subprocess.check_output(["netstat", "-ano", "-p", "tcp"], text=True, errors="replace")
        assert any(f"127.0.0.1:{port}" in line and "LISTENING" in line for line in listeners.splitlines())
        listener_pid = int(next(line.split()[-1] for line in listeners.splitlines()
                                if f"127.0.0.1:{port}" in line and "LISTENING" in line))
        assert not any(f"0.0.0.0:{port}" in line and "LISTENING" in line for line in listeners.splitlines())
    finally:
        if listener_pid is not None and listener_pid != process.pid:
            os.kill(listener_pid, signal.SIGTERM)
        if process.poll() is None:
            process.terminate()
        process.communicate(timeout=10)
    with pytest.raises((httpx.ConnectError, httpx.ConnectTimeout)):
        httpx.get(f"http://127.0.0.1:{port}/api/pages", timeout=1, trust_env=False)


def test_discover_methods_limit_is_validated_as_4xx(web):
    """A malformed caller limit is a 4xx client error, never a 500."""
    _, _, client = web
    assert client.get("/api/discover-methods", params={"limit": -1}).status_code == 422
    ok = client.get("/api/discover-methods", params={"limit": 5})
    assert ok.status_code == 200
    assert 'candidates' in ok.json()
