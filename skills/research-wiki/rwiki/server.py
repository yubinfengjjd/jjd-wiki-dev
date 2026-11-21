import hashlib
import json
import os
import re
import stat
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from contextlib import nullcontext
from urllib.parse import quote, urlsplit

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field, StrictBool, StrictStr

from .aliases import resolve_asset_subpath, resolve_page_ref
from .catalog import PAGE_DIRS, readable_pages
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
from .workflow import workflow_for_page, workflow_snapshot
from .read_cache import backlinks_index, cached_vault_value, invalidate_cache, read_session, remember
from . import curation


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
    allow_active: StrictBool = False


class BatchConfirmBody(BaseModel):
    ids: list[StrictStr] = Field(min_length=1, max_length=500)
    confirmed: StrictBool


class CurationBody(BaseModel):
    ids: list[StrictStr] = Field(min_length=1, max_length=1000)
    decision: StrictStr
    revision: StrictStr


class AssetFetchBody(BaseModel):
    id: StrictStr = Field(min_length=1, max_length=240)


class SniffBody(BaseModel):
    path: str = Field(min_length=1)


class StudioUploadBody(BaseModel):
    filename: StrictStr = Field(min_length=1, max_length=240)
    content_base64: str = ""
    content_text: str = ""


class StudioLoadExampleBody(BaseModel):
    id: StrictStr = Field(min_length=1, max_length=240)


class StudioRenderBody(BaseModel):
    id: StrictStr = Field(min_length=1, max_length=240)
    project_dir: str = ""
    data_file: str = ""
    bindings: dict[str, str] = Field(default_factory=dict)
    parameters: dict[str, object] = Field(default_factory=dict)


class StudioExecuteBody(StudioRenderBody):
    code: str | None = None


class ProjectStepBody(BaseModel):
    title: StrictStr = Field(min_length=1)
    templates: str = ""
    observation: str = ""
    next_branch: str = ""


# Loopback names only; "testserver" is Starlette TestClient's default Host.
LOCAL_HOSTS = {"127.0.0.1", "localhost", "[::1]", "testserver"}
_THUMB_MAX_DECODE_PIXELS = 40_000_000
_THUMB_MAX_HEIGHT = 2400
_THUMB_MAX_FILES = 500
_THUMB_MAX_BYTES = 150 * 1024 * 1024
_THUMB_SEMAPHORE = threading.Semaphore(4)
_THUMB_LOCKS_GUARD = threading.Lock()
_THUMB_KEY_LOCKS: dict[str, threading.Lock] = {}


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
    resolved_root = root.resolve()
    path = (root / value).resolve()
    if path.is_relative_to(resolved_root) and path.is_file():
        return path
    aliased = resolve_page_ref(resolved_root, value) or resolve_asset_subpath(resolved_root, value)
    if aliased is not None:
        resolved = aliased.resolve()
        if resolved.is_relative_to(resolved_root) and resolved.is_file():
            return resolved
    raise HTTPException(404, "文件不存在")


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
            from .asset_checkout import profile
            if (request.url.path != '/api/assets/fetch'
                    and not request.url.path.startswith('/api/studio/')
                    and profile(config, fresh=True) == 'light'):
                return JSONResponse(status_code=409, content={
                    'detail': '轻量检出不修改正式知识；请先运行 rwiki checkout --profile full。'})
        with read_session() if request.method == "GET" else nullcontext():
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

    @app.get("/api/search")
    def search_knowledge(q: str, kind: str | None = None, scope: str = "knowledge",
                         limit: int = 10, runnable: bool = False):
        from .search import search
        if not q.strip():
            raise HTTPException(422, "q 不能为空")
        if scope not in ("knowledge", "source"):
            raise HTTPException(422, "scope 必须是 knowledge 或 source")
        if not 1 <= limit <= 100:
            raise HTTPException(422, "limit 必须在 1–100 之间")
        with read_session():
            return search(config, q, kind=kind, scope=scope, limit=limit, runnable=runnable)

    @app.post('/api/assets/fetch')
    def get_assets(request: AssetFetchBody):
        from .asset_checkout import fetch_assets
        try:
            return fetch_assets(config, request.id)
        except WikiError as error:
            raise HTTPException(409, str(error)) from error

    def pages() -> list[Path]:
        # An unreadable page is reported by lint; it must not take the whole UI down.
        return remember(("allowed-pages", root), lambda: [path.resolve() for path, _ in readable_pages(root)
                        if path.resolve().is_relative_to(root)])

    def page_file(value: str) -> Path:
        path = safe_file(root, value)
        if path.parent.parent != root or path.parent.name not in PAGE_DIRS or path.suffix != ".md":
            raise HTTPException(404, "页面不存在")
        try:
            read_page(path)
        except WikiError as error:
            raise HTTPException(404, "页面不存在") from error
        return path

    def gallery_file(meta: dict) -> Path:
        return safe_file(config.gallery_root, meta["gallery_entry"] + "/meta.json")

    def targets(body: str) -> set[Path]:
        return {resolve(root, target).resolve() for target in extract_links(body)}

    def figure_refs(meta: dict, body: str) -> list[str]:
        if meta["type"] != "method":
            return []
        refs: list[str] = []
        for target in targets(body):
            if (target.is_relative_to(root) and target.parent.parent == root
                    and target.parent.name in ("layouts", "templates")
                    and target.suffix == ".md" and target.is_file()):
                try:
                    if read_page(target)[0].get("type") in ("layout", "template"):
                        refs.append(target.relative_to(root).as_posix())
                except WikiError:
                    continue
        return sorted(refs)

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
        from .asset_checkout import profile
        if profile(config) == 'light' and meta['type'] in ('method', 'template', 'recipe', 'layout'):
            saved = root / (meta['type'] + 's') / meta['id'] / (
                'thumb.png' if meta['type'] == 'layout' else 'preview.png')
            return {'url': '/files/wiki/' + quote(saved.relative_to(root).as_posix()) if saved.is_file() else None,
                    'kind': 'pending', 'label': '已保存预览；轻量检出不核对完整回放证据'}
        if meta["type"] == "recipe":
            path = root / "recipes" / meta["id"] / "preview.png"
            return ({"url": "/files/wiki/" + quote(path.relative_to(root).as_posix()), "kind": "replay",
                     "label": "原样运行图（最近一次通过）"} if path.is_file()
                    else {"url": None, "kind": "none", "label": "暂无运行图"})
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
            for value in meta.get("sources") or []:
                if str(value).startswith("recipes/"):
                    candidates.append((root / str(value).removesuffix(".md") / "preview.png", "source",
                                       "来源配方的原样运行图 · 模板尚无回放"))
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
        from .asset_checkout import assets_state, profile
        sparse = profile(config) == 'light'
        transport = assets_state(config, path)
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
                elif isinstance(table, dict) and isinstance(table.get("columns"), dict):
                    columns = [{"name": name, "type": col.get("type", "str"),
                                "description": col.get("description", ""),
                                "required": col.get("required", True)}
                               for name, col in table["columns"].items() if isinstance(col, dict)]
                tables.append({"key": key, "interface": slug if isinstance(slug, str) else "",
                               "filename": table.get("filename", "") if isinstance(table, dict) else "",
                               "description": table.get("description", "") if isinstance(table, dict) else "",
                               "required": table.get("required", True) if isinstance(table, dict) else True,
                               "columns": columns})
            input_contract = {"bindings": True, "tables": tables}
        rel_path = path.relative_to(root).as_posix()
        backlinks = list(backlinks_index(root).get(rel_path, []))
        from .method_implementations import implementation_status
        from .papers_api import paper_origins_by_template
        from .runtime_contract import runtime_facts
        runtime = None
        if meta['type'] == 'template' and not sparse:
            runtime = runtime_facts(path.with_suffix(''), meta['id'], 'template')
        paper_origins = (
            paper_origins_by_template(config).get(meta['id'], [])
            if meta.get('type') == 'template' else []
        )
        if sparse:
            page_workflow = {'stage': 'checking', 'queue': None, 'label': '轻量检出 · 未核对完整证据',
                             'reason': '请获取资产或切换 full；不据部分下载判断验证失败。', 'templates': []}
            page_relations = []
        else:
            if meta.get("type") == "layout" and meta.get("status") != "archived":
                page_workflow = cached_vault_value(
                    root,
                    "api_workflow_snapshot",
                    lambda: workflow_snapshot(config),
                    extra_key=profile(config),
                    gallery_root=config.gallery_root,
                    copy_result=False,
                ).get(rel_path)
            else:
                page_workflow = workflow_for_page(config, rel_path, meta)
            cached_rels = cached_vault_value(
                root,
                "api_all_relations",
                lambda: all_relations(config),
                extra_key=True,
                copy_result=False,
            )
            page_relations = [rec for rec in cached_rels if rel_path in (rec["method"], rec["figure"])]
        return {"path": rel_path, "meta": curation.visible_meta(config, meta), "body": body,
                "implementation_status": implementation_status(path, meta) if meta['type'] == 'method' and not sparse else [],
                "runtime": runtime if not sparse else None,
                "paper_origins": paper_origins,
                "backlinks": backlinks,
                "gallery": read_json(gallery_file(meta)) if meta["type"] == "layout" and not sparse else None,
                "reuse": reuse, "input_contract": input_contract,
                "figure_refs": figure_refs(meta, body), "preview": preview(meta),
                "workflow": page_workflow,
                "asset_availability": transport['state'], 'asset_id': meta.get('id'),
                "relations": page_relations}

    def visual(kind: str, entry_id: str) -> tuple[Path, dict, str]:
        if kind not in ("layouts", "templates", "methods", "recipes"):
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
        invalidate_cache(root)
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

        raw = cached_vault_value(
            root,
            "api_method_taxonomy_json",
            lambda: json.dumps(taxonomy(root), ensure_ascii=False).encode("utf-8"),
            copy_result=False,
        )
        return Response(content=raw, media_type="application/json")

    @app.get("/api/method-hubs")
    def method_hubs(domain: str = "", purpose: str = "", q: str = ""):
        from .asset_checkout import profile
        from .method_hub import list_method_hubs

        if not domain and not purpose and not q:
            raw = cached_vault_value(
                root,
                "api_method_hubs_json",
                lambda: json.dumps(list_method_hubs(config), ensure_ascii=False).encode("utf-8"),
                extra_key=profile(config),
                copy_result=False,
            )
            return Response(content=raw, media_type="application/json")
        return list_method_hubs(config, domain=domain, purpose=purpose, q=q)

    @app.get("/api/methods/{method_id}/hub")
    def method_hub_detail(method_id: str):
        from .method_hub import build_method_hub
        from .suggest import suggest_next_steps

        try:
            with read_session():
                hub = build_method_hub(config, method_id)
                hub["next"] = suggest_next_steps(config, hub["id"])
                return hub
        except WikiError as error:
            raise HTTPException(404, str(error)) from error

    @app.get("/api/pages")
    def list_pages(light: bool = False):
        from .asset_checkout import profile
        from .method_implementations import implementation_status
        from .papers_api import paper_origins_by_template
        from .runtime_contract import runtime_facts

        effective_light = light or profile(config) == 'light'

        def build():
            with read_session():
                records = []
                workflow = {} if effective_light else workflow_snapshot(config)
                relations = [] if effective_light else all_relations(config)
                relations_by_page: dict[str, list[dict]] = {}
                if not effective_light:
                    for rel in relations:
                        relations_by_page.setdefault(rel["method"], []).append(rel)
                        if rel["figure"] != rel["method"]:
                            relations_by_page.setdefault(rel["figure"], []).append(rel)
                origins_map = paper_origins_by_template(config)
                hidden = curation.excluded_paths(config)
                for path in pages():
                    page = path.relative_to(root).as_posix()
                    if page in hidden:
                        continue
                    meta, body = read_page(path)
                    meta = curation.visible_meta(config, meta)
                    if effective_light:
                        pending = ({"stage": "archived", "queue": None, "label": "已归档", "reason": "已归档。", "templates": []}
                                   if meta.get("status") == "archived" else
                                   {"stage": "checking", "queue": None, "label": "正在核对证据",
                                    "reason": "运行与验收证据尚未核对完成，不能据此推荐执行。", "templates": []})
                        image = None
                        if meta["type"] in ("template", "recipe", "layout"):
                            name = "thumb.png" if meta["type"] == "layout" else "preview.png"
                            saved = path.with_suffix("") / name
                            image = {"url": "/files/wiki/" + quote(saved.relative_to(root).as_posix()) if saved.is_file() else None,
                                     "kind": "pending", "label": "已保存预览 · 当前证据核对中"}
                    entry = {
                        "path": page,
                        "meta": meta,
                        "implementation_status": [] if effective_light else (implementation_status(path, meta) if meta['type'] == 'method' else []),
                        "runtime": None if effective_light else (runtime_facts(path.with_suffix(''), meta['id'], 'template') if meta['type'] == 'template' else None),
                        "figure_refs": [] if effective_light else figure_refs(meta, body),
                        "preview": image if effective_light else preview(meta),
                        "workflow": (pending if meta["type"] in ("layout", "template", "method", "recipe") else None) if effective_light else workflow.get(page),
                        "relations": [] if effective_light else relations_by_page.get(page, []),
                    }
                    if meta.get("type") == "template":
                        if meta.get("style_tier"):
                            entry["style_tier"] = meta["style_tier"]
                        if meta.get("journal_style"):
                            entry["journal_style"] = meta["journal_style"]
                        origins = origins_map.get(meta.get("id", ""), [])
                        if origins:
                            entry["paper_origins"] = origins
                    records.append(entry)
                return records

        raw = cached_vault_value(
            root,
            "api_pages_json",
            lambda: json.dumps(build(), ensure_ascii=False).encode("utf-8"),
            extra_key=effective_light,
            gallery_root=config.gallery_root,
            copy_result=False,
        )
        return Response(content=raw, media_type="application/json")

    @app.get("/api/source-items")
    def source_items():
        from .finder import _item_record
        from .sources import read_items, SOURCE_ID

        metadata = [read_page(path)[0] for path in pages()]
        promoted = {f"{source.get('id')}:{source.get('item')}" for meta in metadata
                    if meta.get("type") == "recipe" and meta.get("status") != "archived"
                    for source in [meta.get("source") or {}]}
        records = []
        for meta in metadata:
            sid = meta.get("id", "")
            if meta.get("type") != "source" or not isinstance(sid, str) or not SOURCE_ID.fullmatch(sid):
                continue
            page = root / "sources" / f"{sid}.md"
            if page not in pages():
                continue
            item_file = f"sources/{sid}/items.jsonl"
            if not (root / item_file).is_file():
                continue
            safe_file(root, item_file)
            for item in read_items(config, sid):
                identity = f"{sid}:{item.get('item', '')}"
                if item.get("id") == identity and identity not in promoted:
                    records.append(_item_record(item, meta))
        return sorted(curation.filter_records(config, records), key=lambda record: record["id"])

    @app.get("/api/figureya/curation")
    def figureya_curation():
        return curation.inventory(config)

    @app.post("/api/figureya/curation")
    def figureya_decision(request: CurationBody):
        try:
            return curation.update(config, request.ids, request.decision, request.revision)
        except curation.StaleDecision as error:
            raise HTTPException(409, str(error)) from error
        except WikiError as error:
            raise HTTPException(422, str(error)) from error

    @app.get("/api/figureya/image")
    def figureya_image(id: str, path: str):
        try:
            return FileResponse(curation.image_path(config, id, path))
        except (WikiError, ValueError, OSError, KeyError) as error:
            raise HTTPException(404, "此模块的本地图片不存在") from error

    @app.get("/api/page")
    def get_page(path: str):
        with read_session():
            return response(page_file(path))

    @app.get("/api/graph")
    def graph():
        from .asset_checkout import profile

        current_profile = profile(config)

        def build():
            with read_session():
                hidden = curation.excluded_paths(config)
                paths = [p for p in pages() if p.relative_to(root).as_posix() not in hidden]
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
                semantic = [] if current_profile == 'light' else all_relations(config)
                links.extend({"source": item["method"], "target": item["figure"], "kind": "relation",
                              "compatibility": item["compatibility"], "verification": item["verification"],
                              "active": item["active"]}
                             for item in semantic if item["method"] in ids and item["figure"] in ids)
                return {"nodes": nodes, "links": links}

        raw = cached_vault_value(
            root,
            "api_graph_json",
            lambda: json.dumps(build(), ensure_ascii=False).encode("utf-8"),
            extra_key=current_profile,
            gallery_root=config.gallery_root,
            copy_result=False,
        )
        return Response(content=raw, media_type="application/json")

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
        from .asset_checkout import profile
        if profile(config) == 'light':
            return []
        if path is not None:
            resolved = page_file(path)
            return relations_for(config, resolved.relative_to(root).as_posix())
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
                confirm_method(config, meta["id"])
            except WikiError as error:
                raise HTTPException(409, str(error)) from error
            save(config, f"confirm {meta['id']}")
        invalidate_cache(root)
        return response(path)

    @app.post("/api/recipes/{entry_id}/confirm")
    def confirm_recipe(entry_id: str):
        """v2: author confirmation of an L1 recipe; same gate as `wiki.py mark-ready`."""
        path, meta, _ = visual("recipes", entry_id)
        if meta["status"] != "draft":
            raise HTTPException(409, "配方不是 draft")
        from .templates import mark_ready
        mark_ready(config, meta["id"])
        invalidate_cache(root)
        return response(path)

    @app.post("/api/templates/{entry_id}/confirm")
    def confirm_template(entry_id: str):
        """v5.1: author confirmation of an L2 template; same gate as `wiki.py mark-ready`."""
        path, meta, _ = visual("templates", entry_id)
        if meta["status"] != "draft":
            raise HTTPException(409, "模板不是 draft")
        from .templates import mark_ready
        try:
            mark_ready(config, meta["id"])
        except WikiError as error:
            raise HTTPException(409, str(error)) from error
        invalidate_cache(root)
        return response(path)

    @app.post("/api/templates/batch-confirm")
    def batch_confirm_templates(request: BatchConfirmBody):
        """v5.1: atomic batch confirmation restricted strictly to template pages."""
        if not request.confirmed:
            raise HTTPException(422, "请明确确认批量发布模板")
        if not request.ids:
            raise HTTPException(422, "模板 ID 列表不能为空")
        from .aliases import resolve_page_ref
        from .pages import read_page
        from .templates import mark_ready_many

        canonical_ids: list[str] = []
        seen_paths: set[Path] = set()
        for raw_id in request.ids:
            target = resolve_page_ref(config.wiki_root, str(raw_id), expected_type="template")
            if target is None:
                raise HTTPException(400, f"仅允许批量确认绘图模板（templates/），非模板或不存在: {raw_id}")
            if target in seen_paths:
                continue
            seen_paths.add(target)
            meta, _ = read_page(target)
            canonical_ids.append(str(meta.get("id") or target.stem))
        try:
            confirmed_ids = mark_ready_many(config, canonical_ids)
        except WikiError as error:
            raise HTTPException(409, str(error)) from error
        invalidate_cache(root)
        return {"confirmed": confirmed_ids, "count": len(confirmed_ids)}

    @app.post("/api/methods/{entry_id}/return")
    def return_method(entry_id: str, request: RejectBody):
        path, meta, body = visual("methods", entry_id)
        if meta["status"] != "ready":
            raise HTTPException(409, f"页面为 {meta['status']}，不能退回")
        meta["status"] = "draft"
        return finish(path, meta, body, f"return {entry_id}: {request.reason}")

    @app.post("/api/{kind}/{entry_id}/tags")
    def tags(kind: str, entry_id: str, request: TagsBody):
        from .tags import load_vocabulary, normalize_tags, tag_errors

        path, meta, body = visual(kind, entry_id)
        meta["tags"] = normalize_tags(request.tags)
        findings = tag_errors(meta, load_vocabulary(config))
        if findings:
            raise HTTPException(422, "；".join(findings))
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
    def deletion_plan(kind: str, entry_id: str, allow_active: bool = False):
        path, _, _ = visual(kind, entry_id)
        try:
            return prepare(config, path, allow_active=allow_active)[0]
        except WikiError as error:
            raise HTTPException(409, str(error)) from error

    @app.post("/api/{kind}/{entry_id}/delete")
    def delete_item(kind: str, entry_id: str, request: DeleteBody):
        if not request.confirmed:
            raise HTTPException(422, "请明确确认永久删除")
        path, _, _ = visual(kind, entry_id)
        try:
            result = delete_archived(config, path, request.revision, allow_active=request.allow_active)
            invalidate_cache(root)
            return result
        except WikiError as error:
            raise HTTPException(409, str(error)) from error

    @app.post("/api/templates/{entry_id}/signoff")
    @app.post("/api/templates/{entry_id}/reject")
    def no_template_signoff(entry_id: str):
        raise HTTPException(404, "签核和退回只适用于版式")

    @app.get("/api/playbooks")
    def playbooks():
        from .studio import get_playbooks
        raw = cached_vault_value(
            root,
            "api_playbooks_json",
            lambda: json.dumps(get_playbooks(config), ensure_ascii=False).encode("utf-8"),
            copy_result=False,
        )
        return Response(content=raw, media_type="application/json")

    @app.get("/api/next/{node_id}")
    def next_steps_api(node_id: str, q: str = ""):
        from .suggest import suggest_next_steps
        try:
            return suggest_next_steps(config, node_id, query=q)
        except WikiError as error:
            raise HTTPException(404, str(error)) from error

    @app.post("/api/studio/sniff")
    def studio_sniff(request: SniffBody):
        from .studio import sniff_data
        try:
            return sniff_data(config, request.path)
        except WikiError as error:
            raise HTTPException(400, str(error)) from error

    @app.post("/api/studio/upload")
    def studio_upload(request: StudioUploadBody):
        from .studio import upload_studio_data
        try:
            return upload_studio_data(
                config,
                filename=request.filename,
                content_base64=request.content_base64,
                content_text=request.content_text,
            )
        except WikiError as error:
            raise HTTPException(400, str(error)) from error

    @app.post("/api/studio/load-example")
    def studio_load_example(request: StudioLoadExampleBody):
        from .studio import load_example_data
        try:
            return load_example_data(config, request.id)
        except WikiError as error:
            raise HTTPException(404, str(error)) from error

    @app.post("/api/studio/render-code")
    def studio_render_code(request: StudioRenderBody):
        from .studio import render_studio_code
        try:
            return render_studio_code(
                config,
                entry_id=request.id,
                project_dir=request.project_dir,
                data_file=request.data_file,
                bindings=request.bindings,
                parameters=request.parameters,
            )
        except WikiError as error:
            raise HTTPException(404, str(error)) from error

    @app.post("/api/studio/dispatch")
    def studio_dispatch(request: StudioExecuteBody):
        from .studio import dispatch_studio
        try:
            return dispatch_studio(
                config,
                entry_id=request.id,
                project_dir=request.project_dir,
                data_file=request.data_file,
                bindings=request.bindings,
                parameters=request.parameters,
                code=request.code,
            )
        except WikiError as error:
            raise HTTPException(400, str(error)) from error

    @app.post("/api/studio/run")
    def studio_run(request: StudioExecuteBody):
        from .studio import run_studio
        try:
            return run_studio(
                config,
                entry_id=request.id,
                project_dir=request.project_dir,
                data_file=request.data_file,
                bindings=request.bindings,
                parameters=request.parameters,
                code=request.code,
            )
        except WikiError as error:
            raise HTTPException(400, str(error)) from error

    @app.get("/api/studio/output/{run_id}/{filename:path}")
    def studio_output(run_id: str, filename: str):
        from .studio import studio_output_file
        try:
            return FileResponse(studio_output_file(config, run_id, filename))
        except WikiError as error:
            raise HTTPException(404, str(error)) from error

    @app.get("/api/projects")
    def api_projects():
        from .project_tracker import list_projects
        return {"projects": list_projects(config)}

    @app.get("/api/papers")
    def api_papers():
        from .papers_api import list_papers
        raw = cached_vault_value(
            root,
            "api_papers_json",
            lambda: json.dumps({"papers": list_papers(config)}, ensure_ascii=False).encode("utf-8"),
            gallery_root=config.gallery_root,
            copy_result=False,
        )
        return Response(content=raw, media_type="application/json")

    @app.get("/api/papers/{workflow_id}")
    def api_paper_detail(workflow_id: str):
        from .papers_api import get_paper_detail
        with read_session():
            detail = get_paper_detail(config, workflow_id)
            if detail is None:
                raise HTTPException(404, "未找到已复刻论文")
            return detail

    @app.get("/api/papers/{workflow_id}/panel-code")
    def api_paper_panel_code(workflow_id: str, path: str):
        from .papers_api import read_paper_panel_code
        try:
            return read_paper_panel_code(config, workflow_id, path)
        except WikiError as error:
            raise HTTPException(404, str(error)) from error

    @app.post("/api/projects/{project_id}/step")
    def api_add_project_step(project_id: str, request: ProjectStepBody):
        from .project_tracker import add_project_step
        try:
            return add_project_step(
                config,
                project_id,
                title=request.title,
                templates=request.templates,
                observation=request.observation,
                next_branch=request.next_branch,
                commit=True,
            )
        except WikiError as error:
            raise HTTPException(422, str(error)) from error

    def _thumb_cache_dir() -> Path:
        env_dir = os.environ.get("RWIKI_THUMB_DIR", "").strip()
        return Path(env_dir) if env_dir else (Path(tempfile.gettempdir()) / "rwiki-thumbs")

    def _is_safe_regular_file(p: Path) -> bool:
        try:
            if os.path.islink(p) or (hasattr(os.path, "isjunction") and os.path.isjunction(p)):
                return False
            st = os.lstat(p)
            return stat.S_ISREG(st.st_mode)
        except OSError:
            return False

    def _prune_thumb_cache(thumb_dir: Path, keep: Path | None = None) -> None:
        entries: list[tuple[int, int, str]] = []
        total_files = 0
        total_bytes = 0
        keep_str = os.path.normcase(str(keep)) if keep is not None else ""
        try:
            with os.scandir(thumb_dir) as it:
                for entry in it:
                    if not entry.name.endswith(".webp") or entry.is_symlink():
                        continue
                    try:
                        st = entry.stat(follow_symlinks=False)
                    except OSError:
                        continue
                    if not stat.S_ISREG(st.st_mode):
                        continue
                    total_files += 1
                    total_bytes += st.st_size
                    if os.path.normcase(entry.path) != keep_str:
                        entries.append((st.st_mtime_ns, st.st_size, entry.path))
        except OSError:
            return
        if total_files <= _THUMB_MAX_FILES and total_bytes <= _THUMB_MAX_BYTES:
            return
        entries.sort()
        for _, size, victim in entries:
            if total_files <= _THUMB_MAX_FILES and total_bytes <= _THUMB_MAX_BYTES:
                break
            try:
                os.unlink(victim)
                total_files -= 1
                total_bytes -= size
            except OSError:
                pass

    def _etag_matches(header_value: str | None, etag: str) -> bool:
        if not header_value:
            return False
        target = etag.removeprefix("W/").strip()
        for raw_part in header_value.split(","):
            part = raw_part.strip()
            if part == "*" or part.removeprefix("W/").strip() == target:
                return True
        return False

    def _serve_file_or_thumb(path: Path, request: Request, w: int | None = None, *, base_root: Path | None = None):
        st = path.stat()
        is_raster = path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
        etag = (
            f'"{st.st_mtime_ns:x}-{st.st_size:x}-w{w}-v2"'
            if (w is not None and is_raster)
            else f'"{st.st_mtime_ns:x}-{st.st_size:x}"'
        )
        headers = {"ETag": etag, "Cache-Control": "public, max-age=60, must-revalidate"}
        if _etag_matches(request.headers.get("if-none-match"), etag):
            return Response(status_code=304, headers=headers)
        if w is not None and is_raster:
            from PIL import Image

            thumb_dir = _thumb_cache_dir()
            if os.path.lexists(thumb_dir) and (
                os.path.islink(thumb_dir) or (hasattr(os.path, "isjunction") and os.path.isjunction(thumb_dir))
            ):
                raise HTTPException(500, "缩略图缓存目录不能为符号链接")
            rel_key = str(path.resolve())
            if base_root is not None:
                try:
                    rel_key = path.resolve().relative_to(base_root.resolve()).as_posix()
                except ValueError:
                    pass
            key_hash = hashlib.sha256(rel_key.encode("utf-8")).hexdigest()[:24]
            cache_name = f"{key_hash}_{st.st_mtime_ns}_{st.st_size}_w{w}_v2.webp"
            thumb_path = thumb_dir / cache_name
            with _THUMB_LOCKS_GUARD:
                key_lock = _THUMB_KEY_LOCKS.get(cache_name)
                if key_lock is None:
                    if len(_THUMB_KEY_LOCKS) > 2048:
                        for stale_k in [k for k, lk in _THUMB_KEY_LOCKS.items() if not lk.locked()]:
                            _THUMB_KEY_LOCKS.pop(stale_k, None)
                    key_lock = _THUMB_KEY_LOCKS[cache_name] = threading.Lock()
            with key_lock:
                if os.path.lexists(thumb_path) and not _is_safe_regular_file(thumb_path):
                    if os.path.islink(thumb_path):
                        thumb_path.unlink(missing_ok=True)
                    else:
                        raise HTTPException(500, "缩略图缓存条目异常")
                if not _is_safe_regular_file(thumb_path):
                    thumb_dir.mkdir(parents=True, exist_ok=True)
                    with _THUMB_SEMAPHORE:
                        try:
                            with Image.open(path) as im:
                                if im.width * im.height > _THUMB_MAX_DECODE_PIXELS:
                                    raise HTTPException(413, "源图分辨率过大，超出缩略图解码上限")
                                scale = min(w / im.width, _THUMB_MAX_HEIGHT / im.height, 1.0)
                                target_w = max(1, round(im.width * scale))
                                target_h = max(1, round(im.height * scale))
                                if (target_w, target_h) != (im.width, im.height):
                                    im = im.resize((target_w, target_h), Image.Resampling.LANCZOS)
                                has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
                                converted = im.convert("RGBA" if has_alpha else "RGB")
                        except Image.DecompressionBombError as error:
                            raise HTTPException(413, "源图分辨率过大，超出缩略图解码上限") from error
                        fd, tmp_name = tempfile.mkstemp(dir=thumb_dir, suffix=".webp")
                        os.close(fd)
                        try:
                            converted.save(tmp_name, format="WEBP", quality=82, method=4)
                            os.replace(tmp_name, thumb_path)
                        except BaseException:
                            Path(tmp_name).unlink(missing_ok=True)
                            raise
                        _prune_thumb_cache(thumb_dir, keep=thumb_path)
            if not _is_safe_regular_file(thumb_path):
                raise HTTPException(500, "缩略图缓存文件无效")
            return FileResponse(thumb_path, media_type="image/webp", headers=headers)
        return FileResponse(path, headers=headers)

    @app.get("/files/wiki/{path:path}")
    def wiki_file(path: str, request: Request, w: int | None = Query(default=None, ge=120, le=1600)):
        return _serve_file_or_thumb(safe_file(root, path), request, w=w, base_root=root)

    @app.get("/files/gallery/{path:path}")
    def gallery_asset(path: str, request: Request, w: int | None = Query(default=None, ge=120, le=1600)):
        return _serve_file_or_thumb(
            safe_file(config.gallery_root, path), request, w=w, base_root=config.gallery_root.resolve()
        )

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
