import shutil
from pathlib import Path

from .config import Config, load_taxonomy, read_json
from .errors import WikiError
from .pages import read_page, set_block, write_page
from .store import save


def slugify(value: str) -> str:
    return value.lower().replace("_", "-").replace(" ", "-")


def entry_path(config: Config, entry_id: str) -> Path:
    post, separator, figure = entry_id.partition("__")
    if not separator or not post or not figure:
        raise WikiError(f"entry_id 应为 <post>__<fig>: {entry_id}")
    return config.gallery_root / post / "figures" / figure


def thumbnail(entry: Path, gallery_meta: dict) -> Path:
    for path in (entry / "thumb.png", entry / "output/replica.png", entry / gallery_meta["files"]["source_image"]):
        if path.is_file():
            return path
    raise WikiError(f"无可用缩略图: {entry}")


def render_facts(page_meta: dict, gallery_meta: dict, templates: dict) -> str:
    post = gallery_meta["post"]
    charts = " · ".join(f"[[chart-types/{slug}]]" for slug in page_meta["chart_types"])
    tags = "、".join(page_meta["tags"])
    source = "".join(f"- {label}：{post[key]}\n"
                     for key, label in (("title", "来源"), ("account", "公众号"),
                                        ("publish_date", "日期"), ("url", "URL"))
                     if post[key] is not None)
    free_tags = f"- 标签：{tags}\n" if tags else ""
    keywords = "、".join(page_meta.get("keywords", []))
    keyword_line = f"- 关键词：{keywords}\n" if keywords else ""
    letters = list(page_meta["panels"])
    panels = "、".join(letters) if len(letters) < 2 else f"{letters[0]}–{letters[-1]}"
    panel_line = f"尚未拆分（{panels}）"
    if templates:
        panel_line = "；".join(f"[[templates/{tid}|{template['title']}]]"
                               f"（{'、'.join(page_meta['template_panels'][tid])}）"
                               for tid, template in templates.items())
    return (f"\n{source}"
            f"- 画廊条目：{page_meta['gallery_entry']}\n"
            f"- 语言：{page_meta['language']}\n"
            f"- 数据来源：{gallery_meta['data_provenance']}\n"
            f"- 代码来源：{gallery_meta['code_provenance']}\n"
            f"{free_tags}"
            f"{keyword_line}"
            f"- 图型：{charts}\n"
            f"- 面板：{panel_line}\n")


def layout_facts(config: Config, meta: dict) -> str:
    gallery = read_json(config.gallery_root / meta["gallery_entry"] / "meta.json")
    templates = {tid: read_page(config.wiki_root / "templates" / f"{tid}.md")[0]
                 for tid in meta["templates"]}
    return render_facts(meta, gallery, templates)


def ensure_hubs(config: Config, page_meta: dict) -> None:
    for slug in page_meta.get("chart_types", []):
        path = config.wiki_root / "chart-types" / f"{slug}.md"
        if not path.exists():
            write_page(path, {"type": "chart-type", "slug": slug, "title": slug}, f"# {slug}\n")


def new_page(gallery_meta: dict, relative_entry: str, taxonomy: dict) -> tuple[dict, str]:
    # The layout title names the panel, not the post. Post metadata stays in
    # facts; appending it produced long duplicate titles on every source page.
    title = gallery_meta['figure']['label'].strip()
    for prefix in ("单panel：", "单panel:", "单 panel：", "单 panel:"):
        if title.startswith(prefix):
            title = title[len(prefix):].strip()
            break
    entry_id = gallery_meta["id"]
    # A legacy gallery without an explicit approved_version is not proof of
    # approval for a new page; the author must sign the current source version.
    approved = (gallery_meta['status'] == 'approved'
                and gallery_meta.get('approved_version') == gallery_meta['version'])
    tags = list(dict.fromkeys(
        taxonomy.get(key, {'label': key})['label']
        for key in gallery_meta['scenarios']['primary'] + gallery_meta['scenarios'].get('secondary', [])))
    free = [value for value in dict.fromkeys(gallery_meta['scenarios'].get('free', []))
            if value not in tags]
    meta = {
        "type": "layout", "id": entry_id, "title": title,
        "status": "pending_template" if approved else "pending_signoff",
        "gallery_entry": relative_entry, "gallery_version": gallery_meta["version"],
        "signedoff_version": gallery_meta['version'] if approved else None,
        "language": gallery_meta["language"],
        "tags": tags,
        "panels": {letter: slugify(value) for letter, value in gallery_meta["figure"]["panel_map"].items()},
        "chart_types": list(dict.fromkeys(slugify(value) for value in gallery_meta["figure"]["panel_map"].values())),
        "templates": [],
        "template_panels": {},
        "favorite": False,
    }
    if free:
        meta["keywords"] = free
    body = (f"# {title}\n\n![[layouts/{entry_id}/thumb.png]]\n\n"
            "<!-- facts:start -->\n<!-- facts:end -->\n\n"
            "## 适用\n\n## 不适用\n\n## 知识关联检查\n\n"
            "## 使用记录\n\n<!-- user:start -->\n<!-- user:end -->\n")
    return meta, body


def ingest_entry(config: Config, entry: Path, entry_id: str, taxonomy: dict) -> None:
    gallery = read_json(entry / "meta.json")
    if gallery["id"] != entry_id:
        raise WikiError(f"画廊 id 与 entry_id 不一致: {entry_id} / {gallery['id']}")
    panel_map = gallery["figure"].get("panel_map")
    if not isinstance(panel_map, dict) or not panel_map or any(
            not isinstance(letter, str) or len(letter) != 1 or not letter.isascii() or not letter.isupper()
            or not isinstance(value, str) or not value.strip() for letter, value in panel_map.items()):
        raise WikiError(f"缺少或非法 figure.panel_map，请用 sci-figure-replica 补上: {entry_id}")
    path = config.wiki_root / "layouts" / f"{entry_id}.md"
    if config.single_panel_only and len(panel_map) != 1:
        # Existing historical records remain untouched, never reactivated by ingest --all.
        if path.exists() and read_page(path)[0]["status"] == "archived":
            return
        raise WikiError("仅收录一个逻辑 panel；请先识别样式、确认代表裁图。整图只保留作溯源。")
    relative_entry = entry.relative_to(config.gallery_root).as_posix()
    if path.exists():
        meta, body = read_page(path)
        # Reading a source version and author approval are independent facts.
        # Legacy accepted pages retain their already recorded approval only.
        # No fallback to gallery_version: a page without an explicit signed
        # version is not proof that the author approved the version it read.
        signed = meta.get('signedoff_version')
        if gallery['status'] == 'approved' and gallery.get('approved_version') == gallery['version']:
            signed = gallery['version']
        meta['signedoff_version'] = signed
        if meta["status"] != "archived":
            if signed != gallery['version'] or gallery["status"] != "approved":
                meta["status"] = "pending_signoff"
            elif meta["status"] == "pending_signoff":
                meta["status"] = "pending_template"
        meta.update(gallery_entry=relative_entry, gallery_version=gallery["version"], language=gallery["language"])
        meta["panels"] = {letter: slugify(value) for letter, value in panel_map.items()}
        meta["chart_types"] = list(dict.fromkeys(meta["panels"].values()))
    else:
        meta, body = new_page(gallery, relative_entry, taxonomy)
    source = thumbnail(entry, gallery)
    templates = {tid: read_page(config.wiki_root / "templates" / f"{tid}.md")[0]
                 for tid in meta["templates"]}
    body = set_block(body, "facts", render_facts(meta, gallery, templates))
    ensure_hubs(config, meta)
    assets = config.wiki_root / "layouts" / entry_id
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, assets / "thumb.png")
    write_page(path, meta, body)


def ingest_figure(config: Config, entry_id: str | None = None) -> None:
    taxonomy = load_taxonomy(config.taxonomy)
    if entry_id is not None:
        ingest_entry(config, entry_path(config, entry_id), entry_id, taxonomy)
        save(config, f"ingest {entry_id}")
    else:
        for path in sorted(config.gallery_root.glob("*/figures/*/meta.json")):
            expected_id = f"{path.parents[2].name}__{path.parent.name}"
            if config.single_panel_only and len(read_json(path)["figure"].get("panel_map", {})) > 1:
                continue
            ingest_entry(config, path.parent, expected_id, taxonomy)
        save(config, "ingest --all")
