import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, StrictBool, StrictStr

from .catalog import readable_pages
from .config import Config, read_json
from .errors import WikiError
from .facts import declarations, input_interfaces, table_interfaces
from .interfaces import load_interface
from .links import extract_links, resolve
from .pages import read_page, set_block, write_page
from .methods import confirm_method
from .store import guarded, save
from .deletion import prepare, delete_archived
from .relations import relations_for, all_relations
from .code_assets import code_files, read_code, code_file
from .verification import replay_available
from .workflow import workflow_snapshot


class RejectBody(BaseModel):
    reason: StrictStr = Field(min_length=1, pattern=r"\S")


class TagsBody(BaseModel):
    tags: list[StrictStr]


class FavoriteBody(BaseModel):
    value: StrictBool


class NoteBody(BaseModel):
    text: StrictStr


class DeleteBody(BaseModel):
    confirmed: StrictBool
    revision: StrictStr


# Loopback names only; "testserver" is Starlette TestClient's default Host.
LOCAL_HOSTS = {"127.0.0.1", "localhost", "[::1]", "testserver"}


def _host_name(value: str) -> str:
    value = value.strip().lower()
    if value.startswith("["):
        return value[:value.find("]") + 1]
    return value.rsplit(":", 1)[0] if value.count(":") == 1 else value


def safe_file(root: Path, value: str) -> Path:
    if Path(value).anchor:
        raise HTTPException(404, "文件路径必须相对根目录")
    # Dot entries (.git, .obsidian, ...) are repository internals, never page assets.
    if any(part.startswith(".") for part in Path(value).parts):
        raise HTTPException(404, "文件不存在")
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise HTTPException(404, "文件不存在")
    return path


def create_app(config: Config) -> FastAPI:
    app = FastAPI()
    root = config.wiki_root.resolve()

    # Any web page can send requests to localhost: reject foreign Host (DNS rebinding)
    # and cross-site writes (a body-less POST needs no CORS preflight).
    @app.middleware("http")
    async def local_only(request, call_next):
        if _host_name(request.headers.get("host", "")) not in LOCAL_HOSTS:
            return JSONResponse(status_code=403, content={"detail": "只接受本机地址访问"})
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin")
            foreign = origin is not None and (
                origin == "null" or _host_name(urlsplit(origin).netloc) not in LOCAL_HOSTS)
            if foreign or request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse(status_code=403, content={"detail": "拒绝跨站写请求"})
        return await call_next(request)

    # Same boundary as cli.main: a WikiError reaches the page as its message, not "Internal Server Error".
    @app.exception_handler(WikiError)
    async def wiki_error(request, error: WikiError):
        return JSONResponse(status_code=500, content={"detail": str(error)})

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error: RequestValidationError):
        detail = "; ".join(f"{'.'.join(map(str, item['loc']))}: {item['msg']}"
                           for item in error.errors())
        return JSONResponse(status_code=422, content={"detail": detail})

    def pages() -> list[Path]:
        # An unreadable page is reported by lint; it must not take the whole UI down.
        return [path.resolve() for path, _ in readable_pages(root)
                if path.resolve().is_relative_to(root)]

    def page_file(value: str) -> Path:
        path = safe_file(root, value)
        if path not in pages():
            raise HTTPException(404, "页面不存在")
        return path

    def gallery_file(meta: dict) -> Path:
        return safe_file(config.gallery_root, meta["gallery_entry"] + "/meta.json")

    def targets(body: str) -> set[Path]:
        return {resolve(root, target).resolve() for target in extract_links(body)}

    def figure_refs(meta: dict, body: str) -> list[str]:
        if meta["type"] != "method":
            return []
        allowed = set(pages())
        return sorted(target.relative_to(root).as_posix() for target in targets(body)
                      if target in allowed and read_page(target)[0]["type"] in ("layout", "template"))

    def gallery_source(origin: dict, label: str) -> dict | None:
        """The selected source panel stays read-only in the gallery; preview it in place."""
        entry = origin.get("gallery_entry")
        if not isinstance(entry, str) or not entry:
            return None
        meta_path = config.gallery_root / entry / "meta.json"
        if not meta_path.is_file():
            return None
        try:
            gallery = read_json(meta_path)
        except (WikiError, OSError):
            return None
        source = (gallery.get("files") or {}).get("source_image")
        if not isinstance(source, str) or not source:
            return None
        try:
            resolved = safe_file(config.gallery_root, f"{entry}/{source}")
        except (HTTPException, WikiError, OSError):
            return None
        relative = resolved.relative_to(config.gallery_root.resolve()).as_posix()
        return {"url": "/files/gallery/" + quote(relative, safe="/"),
                "kind": "source", "label": label}

    def preview(meta: dict) -> dict | None:
        if meta["type"] not in ("layout", "template"):
            return None
        candidates = []
        if meta["type"] == "template":
            target = root / "templates" / meta["id"]
            # A preview left from an older code/spec/example is not evidence for the current version.
            if replay_available(target):
                candidates.append((target / "preview.png", "replay", "模板回放"))
            else:
                candidates.append((target / "preview.png", "stale", "旧回放 · 当前版本尚未重新回放"))
            for lid in meta.get("layouts") or []:
                origin = root / "layouts" / f"{lid}.md"
                try:
                    origin_meta = read_page(origin)[0]
                except WikiError:
                    continue
                if len(origin_meta.get("panels") or {}) == 1:
                    source = gallery_source(origin_meta, "来源 panel · 模板尚无回放")
                    if source:
                        candidates.append(source)
                    candidates.append((root / "layouts" / lid / "thumb.png", "source",
                                       "来源版式的复刻缩略图 · 模板尚无回放"))
        else:
            source = gallery_source(meta, "来源 panel · 只读溯源")
            if source:
                candidates.append(source)
            candidates.append((root / "layouts" / meta["id"] / "thumb.png", "source", "复刻缩略图"))
        for candidate in candidates:
            if isinstance(candidate, dict):
                return candidate
            path, kind, label = candidate
            resolved = path.resolve()
            if resolved.is_relative_to(root) and resolved.is_file():
                return {"url": "/files/wiki/" + quote(resolved.relative_to(root).as_posix()),
                        "kind": kind, "label": label}
        return {"url": None, "kind": "none", "label": "暂无预览图"}

    def response(path: Path) -> dict:
        meta, body = read_page(path)
        reuse = None
        input_contract = None
        if meta["type"] == "template":
            spec_path = path.with_suffix("") / "spec.json"
            spec = read_json(spec_path) if spec_path.is_file() else {}
            sizing = spec.get("style", {}).get("sizing")
            reuse = {"sizing_declared": isinstance(sizing, dict),
                     "mode": sizing.get("mode") if isinstance(sizing, dict) else None,
                     "profile": sizing.get("profile") if isinstance(sizing, dict) else None}
            tables = []
            for key, table in (spec.get("tables") or {}).items():
                slug = table.get("interface") if isinstance(table, dict) else None
                columns = []
                if isinstance(slug, str) and slug:
                    try:
                        definition = load_interface(root, slug)
                    except WikiError:
                        definition = None
                    if definition:
                        columns = [{"name": name, "type": column["type"],
                                    "description": column["description"],
                                    "required": column.get("required", True)}
                                   for name, column in definition["columns"].items()]
                tables.append({"key": key, "interface": slug if isinstance(slug, str) else "",
                               "description": table.get("description", "") if isinstance(table, dict) else "",
                               "required": table.get("required", True) if isinstance(table, dict) else True,
                               "columns": columns})
            input_contract = {"bindings": True, "tables": tables}
        backlinks = []
        for other in pages():
            if other == path:
                continue
            other_meta, other_body = read_page(other)
            if path in targets(other_body):
                backlinks.append({"path": other.relative_to(root).as_posix(),
                                  "title": other_meta["title"], "type": other_meta["type"]})
        from .method_implementations import implementation_status
        from .runtime_contract import runtime_facts
        runtime = None
        if meta['type'] == 'template':
            runtime = runtime_facts(path.with_suffix(''), meta['id'], 'template')
        return {"path": path.relative_to(root).as_posix(), "meta": meta, "body": body,
                "implementation_status": implementation_status(path, meta) if meta['type'] == 'method' else [],
                "runtime": runtime,
                "backlinks": sorted(backlinks, key=lambda item: item["title"]),
                "gallery": read_json(gallery_file(meta)) if meta["type"] == "layout" else None,
                "reuse": reuse, "input_contract": input_contract,
                "figure_refs": figure_refs(meta, body), "preview": preview(meta),
                "workflow": workflow_snapshot(config).get(path.relative_to(root).as_posix()),
                "relations": relations_for(config, path.relative_to(root).as_posix())}

    def visual(kind: str, entry_id: str) -> tuple[Path, dict, str]:
        if kind not in ("layouts", "templates", "methods"):
            raise HTTPException(404, "页面类型不存在")
        path = page_file(f"{kind}/{entry_id}.md")
        meta, body = read_page(path)
        if meta["type"] != kind[:-1]:
            raise HTTPException(404, "页面类型不符")
        return path, meta, body

    def finish(path: Path, meta: dict, body: str, message: str, before=None, also=()) -> dict:
        """Write, save and commit as one step; on any failure the touched files are restored."""
        with guarded(config, path, *also):
            if before is not None:
                before()
            write_page(path, meta, body)
            save(config, message)
        return response(path)

    def update_gallery(meta: dict, status: str) -> None:
        path = gallery_file(meta)
        gallery = read_json(path)
        gallery["status"] = status
        gallery['approved_version'] = gallery['version'] if status == 'approved' else None
        gallery["updated_at"] = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(gallery, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8", newline="\n")

    @app.get("/api/method-taxonomy")
    def method_taxonomy():
        from .method_taxonomy import taxonomy

        return taxonomy(root)

    @app.get("/api/pages")
    def list_pages():
        records = []
        workflow = workflow_snapshot(config)
        relations = all_relations(config)
        for path in pages():
            meta, body = read_page(path)
            page = path.relative_to(root).as_posix()
            from .method_implementations import implementation_status
            from .runtime_contract import runtime_facts
            records.append({"path": page, "meta": meta,
                            "implementation_status": implementation_status(path, meta) if meta['type'] == 'method' else [],
                            "runtime": runtime_facts(path.with_suffix(''), meta['id'], 'template') if meta['type'] == 'template' else None,
                            "figure_refs": figure_refs(meta, body), "preview": preview(meta),
                            "workflow": workflow.get(page),
                            "relations": [r for r in relations if page in (r["method"], r["figure"])]})
        return records

    @app.get("/api/page")
    def get_page(path: str):
        return response(page_file(path))

    @app.get("/api/graph")
    def graph():
        paths = pages()
        nodes, edges, feeds = [], set(), set()
        for path in paths:
            meta, body = read_page(path)
            source = path.relative_to(root).as_posix()
            nodes.append({"id": source, "type": meta["type"], "title": meta["title"],
                          "status": meta.get("status")})
            for target in targets(body):
                if target in paths and target != path:
                    edges.add(tuple(sorted((source, target.relative_to(root).as_posix()))))
        for mid, (_, method) in declarations(root, "methods").items():
            for slug in method["outputs"]:
                feeds.add((f"methods/{mid}.md", f"interfaces/{slug}.md"))
            for slug in input_interfaces(method):
                feeds.add((f"interfaces/{slug}.md", f"methods/{mid}.md"))
        for tid, (_, spec) in declarations(root, "templates").items():
            for slug in table_interfaces(spec):
                feeds.add((f"interfaces/{slug}.md", f"templates/{tid}.md"))
        ids = {node["id"] for node in nodes}
        feeds = {(a, b) for a, b in feeds if a in ids and b in ids and a != b}
        feed_pairs = {tuple(sorted((a, b))) for a, b in feeds}
        links = [{"source": a, "target": b, "kind": "feeds"} for a, b in sorted(feeds)]
        links.extend({"source": a, "target": b, "kind": "link"} for a, b in sorted(edges - feed_pairs))
        links.extend({"source": item["method"], "target": item["figure"], "kind": "relation",
                      "compatibility": item["compatibility"], "verification": item["verification"],
                      "active": item["active"]}
                     for item in all_relations(config) if item["method"] in ids and item["figure"] in ids)
        return {"nodes": nodes, "links": links}

    @app.get("/api/discover-methods")
    def discover_methods_api(q: str = "", limit: int = 20):
        """Read-only opportunity list; executable stays gated by ready_for_use."""
        from .discovery import discover_methods
        try:
            return discover_methods(config, q, limit)
        except WikiError as error:
            raise HTTPException(422, str(error)) from error

    @app.get("/api/relations")
    def semantic_relations(path: str | None = None):
        if path is not None:
            page_file(path)
            return relations_for(config, path)
        return all_relations(config)

    def code_page(kind: str, entry_id: str) -> str:
        path, _, _ = visual(kind, entry_id)
        return path.relative_to(root).as_posix()

    @app.get("/api/{kind}/{entry_id}/code-files")
    def list_code(kind: str, entry_id: str):
        try:
            return code_files(config, code_page(kind, entry_id))
        except WikiError as error:
            raise HTTPException(404, str(error)) from error

    @app.get("/api/{kind}/{entry_id}/code")
    def get_code(kind: str, entry_id: str, variant: str, path: str):
        try:
            return read_code(config, code_page(kind, entry_id), variant, path)
        except WikiError as error:
            raise HTTPException(404, str(error)) from error

    @app.get("/api/{kind}/{entry_id}/code-download")
    def download_code(kind: str, entry_id: str, variant: str, path: str):
        try:
            target = code_file(config, code_page(kind, entry_id), variant, path)
        except WikiError as error:
            raise HTTPException(404, str(error)) from error
        return FileResponse(target, filename=target.name, media_type="application/octet-stream",
                            headers={"X-Content-Type-Options": "nosniff"})

    @app.get("/api/log")
    def log():
        entries = [{"time": time, "message": message} for time, message in
                   re.findall(r"^## \[([^\]\n]+)\] (.*)$",
                              (root / "log.md").read_text(encoding="utf-8"), re.M)]
        # log.md is append-only, so file order is time order even within the same minute.
        return entries[::-1]

    @app.post("/api/layouts/{entry_id}/signoff")
    def signoff(entry_id: str):
        path, meta, body = visual("layouts", entry_id)
        if meta["status"] != "pending_signoff":
            raise HTTPException(409, "页面不是 pending_signoff")
        current_gallery = read_json(gallery_file(meta))
        if current_gallery['version'] != meta['gallery_version']:
            raise HTTPException(409, '来源版本已变化，请重新收录并核对后签核')
        meta['gallery_version'] = current_gallery['version']
        meta['signedoff_version'] = current_gallery['version']
        meta["status"] = "pending_template"
        return finish(path, meta, body, f"signoff {entry_id}",
                      before=lambda: update_gallery(meta, "approved"), also=[gallery_file(meta)])

    @app.post("/api/layouts/{entry_id}/reject")
    def reject(entry_id: str, request: RejectBody):
        path, meta, body = visual("layouts", entry_id)
        # Rejecting also withdraws a sign-off; a ready or archived template must not fall back to draft.
        if meta["status"] not in ("pending_signoff", "pending_template"):
            raise HTTPException(409, f"页面为 {meta['status']}，不能退回")
        meta["status"] = "pending_signoff"
        return finish(path, meta, body, f"reject {entry_id}: {request.reason}",
                      before=lambda: update_gallery(meta, "draft"), also=[gallery_file(meta)])

    @app.post("/api/methods/{entry_id}/confirm")
    def confirm(entry_id: str):
        path, meta, _ = visual("methods", entry_id)
        if meta["status"] != "draft":
            raise HTTPException(409, "页面不是 draft")
        with guarded(config, path, path.with_suffix("") / "acceptance.json"):
            try:
                confirm_method(config, entry_id)
            except WikiError as error:
                raise HTTPException(409, str(error)) from error
            save(config, f"confirm {entry_id}")
        return response(path)

    @app.post("/api/methods/{entry_id}/return")
    def return_method(entry_id: str, request: RejectBody):
        path, meta, body = visual("methods", entry_id)
        if meta["status"] != "ready":
            raise HTTPException(409, f"页面为 {meta['status']}，不能退回")
        meta["status"] = "draft"
        return finish(path, meta, body, f"return {entry_id}: {request.reason}")

    @app.post("/api/{kind}/{entry_id}/tags")
    def tags(kind: str, entry_id: str, request: TagsBody):
        path, meta, body = visual(kind, entry_id)
        meta["tags"] = list(dict.fromkeys(tag.strip() for tag in request.tags if tag.strip()))
        return finish(path, meta, body, f"tags {entry_id}")

    @app.post("/api/{kind}/{entry_id}/favorite")
    def favorite(kind: str, entry_id: str, request: FavoriteBody):
        path, meta, body = visual(kind, entry_id)
        meta["favorite"] = request.value
        return finish(path, meta, body, f"favorite {entry_id}")

    @app.post("/api/{kind}/{entry_id}/note")
    def note(kind: str, entry_id: str, request: NoteBody):
        path, meta, body = visual(kind, entry_id)
        body = set_block(body, "user", f"\n{request.text}\n")
        return finish(path, meta, body, f"note {entry_id}")

    @app.post("/api/{kind}/{entry_id}/archive")
    def archive(kind: str, entry_id: str):
        path, meta, body = visual(kind, entry_id)
        if meta["status"] == "archived":
            raise HTTPException(409, "页面已归档")
        meta["archived_from"], meta["status"] = meta["status"], "archived"
        return finish(path, meta, body, f"archive {entry_id}")

    @app.post("/api/{kind}/{entry_id}/restore")
    def restore(kind: str, entry_id: str):
        path, meta, body = visual(kind, entry_id)
        if meta["status"] != "archived":
            raise HTTPException(409, "页面未归档")
        meta["status"] = meta.pop("archived_from")
        return finish(path, meta, body, f"restore {entry_id}")

    @app.get("/api/{kind}/{entry_id}/delete-plan")
    def deletion_plan(kind: str, entry_id: str):
        path, _, _ = visual(kind, entry_id)
        try:
            return prepare(config, path)[0]
        except WikiError as error:
            raise HTTPException(409, str(error)) from error

    @app.post("/api/{kind}/{entry_id}/delete")
    def delete_item(kind: str, entry_id: str, request: DeleteBody):
        if not request.confirmed:
            raise HTTPException(422, "请明确确认永久删除")
        path, _, _ = visual(kind, entry_id)
        try:
            return delete_archived(config, path, request.revision)
        except WikiError as error:
            raise HTTPException(409, str(error)) from error

    @app.post("/api/templates/{entry_id}/signoff")
    @app.post("/api/templates/{entry_id}/reject")
    def no_template_signoff(entry_id: str):
        raise HTTPException(404, "签核和退回只适用于版式")

    @app.get("/files/wiki/{path:path}")
    def wiki_file(path: str):
        return FileResponse(safe_file(root, path))

    @app.get("/files/gallery/{path:path}")
    def gallery_asset(path: str):
        return FileResponse(safe_file(config.gallery_root, path))

    @app.get("/{path:path}")
    def frontend(path: str):
        if path.split("/", 1)[0] in ("api", "files"):
            raise HTTPException(404, "接口不存在")
        app_root = Path(__file__).resolve().parents[1] / "app"
        candidate = (app_root / path).resolve()
        if candidate.is_relative_to(app_root) and candidate.is_file():
            return FileResponse(candidate)
        # The shell must be re-fetched after every rebuild; its assets carry content hashes and may be cached.
        return FileResponse(app_root / "index.html", headers={"Cache-Control": "no-store"})

    return app
