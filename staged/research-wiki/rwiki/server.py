import json
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, StrictBool, StrictStr

from .catalog import page_paths
from .config import Config, read_json
from .errors import WikiError
from .facts import declarations, input_interfaces, table_interfaces
from .links import extract_links, resolve
from .pages import read_page, set_block, write_page
from .methods import confirm_method
from .store import save


class RejectBody(BaseModel):
    reason: StrictStr = Field(min_length=1, pattern=r"\S")


class TagsBody(BaseModel):
    tags: list[StrictStr]


class FavoriteBody(BaseModel):
    value: StrictBool


class NoteBody(BaseModel):
    text: StrictStr


def safe_file(root: Path, value: str) -> Path:
    if Path(value).anchor:
        raise HTTPException(404, "文件路径必须相对根目录")
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise HTTPException(404, "文件不存在")
    return path


def create_app(config: Config) -> FastAPI:
    app = FastAPI()
    root = config.wiki_root.resolve()

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
        return [path.resolve() for path in page_paths(root)
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

    def response(path: Path) -> dict:
        meta, body = read_page(path)
        backlinks = []
        for other in pages():
            if other == path:
                continue
            other_meta, other_body = read_page(other)
            if path in targets(other_body):
                backlinks.append({"path": other.relative_to(root).as_posix(),
                                  "title": other_meta["title"], "type": other_meta["type"]})
        return {"path": path.relative_to(root).as_posix(), "meta": meta, "body": body,
                "backlinks": sorted(backlinks, key=lambda item: item["title"]),
                "gallery": read_json(gallery_file(meta)) if meta["type"] == "layout" else None}

    def visual(kind: str, entry_id: str) -> tuple[Path, dict, str]:
        if kind not in ("layouts", "templates", "methods"):
            raise HTTPException(404, "页面类型不存在")
        path = page_file(f"{kind}/{entry_id}.md")
        meta, body = read_page(path)
        if meta["type"] != kind[:-1]:
            raise HTTPException(404, "页面类型不符")
        return path, meta, body

    def finish(path: Path, meta: dict, body: str, message: str) -> dict:
        write_page(path, meta, body)
        save(config, message)
        return response(path)

    def update_gallery(meta: dict, status: str) -> None:
        path = gallery_file(meta)
        gallery = read_json(path)
        gallery["status"] = status
        gallery["updated_at"] = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(gallery, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8", newline="\n")

    @app.get("/api/pages")
    def list_pages():
        return [{"path": path.relative_to(root).as_posix(), "meta": read_page(path)[0]}
                for path in pages()]

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
        return {"nodes": nodes, "links": links}

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
        update_gallery(meta, "approved")
        meta["status"] = "pending_template"
        return finish(path, meta, body, f"signoff {entry_id}")

    @app.post("/api/layouts/{entry_id}/reject")
    def reject(entry_id: str, request: RejectBody):
        path, meta, body = visual("layouts", entry_id)
        # Rejecting also withdraws a sign-off; a ready or archived template must not fall back to draft.
        if meta["status"] not in ("pending_signoff", "pending_template"):
            raise HTTPException(409, f"页面为 {meta['status']}，不能退回")
        update_gallery(meta, "draft")
        meta["status"] = "pending_signoff"
        return finish(path, meta, body, f"reject {entry_id}: {request.reason}")

    @app.post("/api/methods/{entry_id}/confirm")
    def confirm(entry_id: str):
        path, meta, _ = visual("methods", entry_id)
        if meta["status"] != "draft":
            raise HTTPException(409, "页面不是 draft")
        confirm_method(config, entry_id)
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
