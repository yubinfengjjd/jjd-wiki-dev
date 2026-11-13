"""Offline derivative section BM25 index. Never caches executable/scientific truth.

The index is disposable, outside the vault under config.work_root/search. Only
agent-written knowledge and explicitly requested downloaded source text enter it.
"""
from __future__ import annotations
import hashlib
import json
import math
import re
import tempfile
import os
from collections import Counter
from pathlib import Path
from threading import RLock

from .config import Config
from .errors import WikiError
from .pages import read_page

SCHEMA_VERSION = 1
INDEX_VERSION = 4
LOCK = RLock()
PAGE_DIRS = ("methods", "recipes", "templates", "scenarios", "interfaces", "chart-types", "projects", "sources", "layouts")
SOURCE_EXTENSIONS = {".py", ".r", ".rmd", ".qmd", ".md", ".jl", ".sql", ".sh", ".js", ".ts", ".c", ".cpp", ".h"}
SKIP_DIRS = {"data", "datasets", "raw", "logs", "log", "runs", "rwiki-runs", "outputs", "output", "results", "cache", "__pycache__", "node_modules", "venv", ".venv", "env", "renv", "packrat", "site-packages", "verification", "verify", "gallery_compress"}
MAX_SOURCE_BYTES = 2 * 1024 * 1024
# Domain vocabulary, not query-specific rewrite rules. ASCII aliases always use
# word boundaries: PR must never match coexpression or approximation.
ALIASES = [
    ["差异表达", "差异基因", "differential expression", "DE", "DEG", "FindMarkers"],
    ["细胞类型注释", "细胞注释", "cell type annotation", "cell annotation"],
    ["批次整合", "批次校正", "batch integration", "batch correction"],
    ["双细胞", "doublet"],
    ["质量控制", "质控", "quality control", "QC"],
    ["基因集富集", "通路富集", "gene set enrichment", "pathway enrichment"],
    ["基因集打分", "基因集评分", "gene set scoring", "module score"],
    ["拟时序", "pseudotime"],
    ["轨迹推断", "trajectory inference"],
    ["速度分析", "RNA velocity"],
    ["降维", "dimensionality reduction"],
    ["聚类", "clustering"],
    ["生存曲线", "Kaplan Meier", "KM"],
    ["火山图", "volcano"],
    ["森林图", "forest plot"],
    ["桑基图", "sankey"],
    ["热图", "heatmap"],
    ["小提琴图", "violin plot"],
    ["气泡图", "气泡点图", "dotplot", "bubble plot"],
    ["蜂群图", "beeswarm"],
    ["精确率召回率", "precision recall", "PR"],
    ["共表达", "coexpression", "co-expression"],
]
QUERY_ALIASES = [list(group) for group in ALIASES]
# Broad topic phrases expand queries to the task; documents mentioning a cell
# type do not thereby claim to perform annotation.
QUERY_ALIASES[1] += ["细胞类型", "cell type"]
STOPWORDS = ["请帮我", "每一个", "能不能", "请问", "我想", "我需要", "想要", "如何", "怎么", "怎样",
             "可以", "是否", "能否", "应该", "判断", "每个", "属于", "什么", "哪个", "哪些", "的", "给", "做", "一下"]
RANKING = {"k1": 1.2, "b": .75, "title_weight": 4, "metadata_weight": 2,
           "section_weight": 1, "secondary_cap": .05}
BLOCK = re.compile(r"<!--\s*(user|facts):start\s*-->.*?(?:<!--\s*\1:end\s*-->|\Z)", re.S | re.I)
WORDS = re.compile(r"[a-z0-9]+|[\u3400-\u9fff]+", re.I)


def clean_body(body: str) -> str:
    return BLOCK.sub("", body)


def _alias_present(text: str, alias: str) -> bool:
    if re.search(r"[\u3400-\u9fff]", alias):
        return alias.lower() in text
    return bool(re.search(r"(?<![a-z0-9])" + re.escape(alias.lower()) + r"(?![a-z0-9])", text))


def tokenize(text: str, aliases=None, stopwords=None) -> list[str]:
    text = str(text).lower()
    for word in sorted(STOPWORDS if stopwords is None else stopwords, key=len, reverse=True):
        text = text.replace(word, "")
    tokens = []
    for match in WORDS.finditer(text):
        word = match.group()
        if re.fullmatch(r"[\u3400-\u9fff]+", word):
            tokens.extend(word[i:i+2] for i in range(len(word)-1))
            if len(word) == 1:
                tokens.append(word)
        else:
            tokens.append(word)
    for i, names in enumerate(ALIASES if aliases is None else aliases):
        if any(_alias_present(text, name) for name in names):
            tokens.append(f"@{i}")
    return tokens


def _plain(text: str) -> str:
    # Keep code and tables as text, but remove decorative Markdown punctuation.
    return re.sub(r"\s+", " ", re.sub(r"<!--.*?-->", "", text, flags=re.S)).strip()


def _sections(body: str) -> list[dict]:
    body = clean_body(body)
    result, title, lines = [], "正文", []
    for line in body.splitlines():
        heading = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if heading:
            text = _plain("\n".join(lines))
            if text:
                result.append({"title": title, "text": text})
            title, lines = heading[1], []
        else:
            lines.append(line)
    text = _plain("\n".join(lines))
    if text:
        result.append({"title": title, "text": text})
    return result or [{"title": "正文", "text": ""}]


def _metadata(meta: dict) -> str:
    # Explicit knowledge fields only; no author notes or generated verification facts.
    keys = ("summary", "keywords", "tags", "purposes", "chart_types", "inputs", "outputs", "data_contract")
    return " ".join(json.dumps(meta[k], ensure_ascii=False) for k in keys if meta.get(k))


def _record(path: Path, meta: dict, body: str, config: Config) -> dict:
    kind = meta["type"]
    identity = str(meta.get("id") or meta.get("slug") or path.stem)
    sections = _sections(body)
    section_map = {s["title"]: s["text"] for s in sections}
    source = meta.get("source") or {}
    result = {"id": identity, "kind": kind, "level": {"recipe":"L1", "template":"L2", "method":"note"}.get(kind,"-"),
              "title": meta["title"], "status": meta.get("status"),
              "summary": str(meta.get("summary") or section_map.get("用途") or section_map.get("适用") or section_map.get("什么时候用") or "")[:240],
              "not_for": section_map.get("不适用", "")[:240],
              "page": path.relative_to(config.wiki_root).as_posix(),
              "use": f"wiki.py {'use' if kind in ('recipe','template') else 'show'} {identity}" + (" --project <课题目录>" if kind in ('recipe','template') else ""),
              "license": meta.get("license", ""),
              **{k:meta.get(k) or [] for k in ("chart_types", "tags", "keywords", "purposes", "inputs", "outputs")}}
    if kind == "method":
        result["method_kind"] = meta.get("method_kind")
    if kind == 'layout':
        result['reference_only'] = True
    if kind == "scenario":
        result["picks"] = meta.get("picks") or []
    if kind == "recipe":
        from .adapters import required_packages
        result.update(source=f"{source.get('id')}:{source.get('item')}", language=meta.get("language"),
                      scenario=section_map.get("适用", "")[:240], requires=required_packages(meta.get("packages") or {}),
                      inputs=[entry.get("file", "") for entry in meta.get("inputs") or [] if isinstance(entry,dict)])
    return result


def _document(record: dict, body: str, metadata: str = "") -> dict:
    title_tokens = Counter(tokenize(record["id"] + " " + record["title"]))
    meta_tokens = Counter(tokenize(metadata))
    sections = _sections(body)
    for section in sections:
        tf = Counter({k:v*RANKING["title_weight"] for k,v in title_tokens.items()})
        tf.update({k:v*RANKING["metadata_weight"] for k,v in meta_tokens.items()})
        tf.update(tokenize(section["title"] + " " + section["text"]))
        section.update(tf=dict(tf), length=sum(tf.values()))
    return {"record": record, "sections": sections}


def _cache_path(config: Config, scope: str) -> Path:
    base = config.work_root or (config.wiki_root.parent / ".rwiki-work")
    # Never put a derivative index in the tracked knowledge tree.
    base = Path(base).resolve()
    if base.is_relative_to(config.wiki_root.resolve()):
        raise WikiError("搜索缓存 work_root 必须位于知识库之外")
    return base / "search" / f"{scope}.json"


def _load_cache(path: Path, config: Config) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("version") == INDEX_VERSION and value.get("root") == str(config.wiki_root.resolve()):
            entries = value.get("entries", {})
            return entries if isinstance(entries, dict) else {}
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return {}


def _signature(path: Path) -> list[int]:
    stat = path.stat()
    return [stat.st_mtime_ns, stat.st_size]


def _write_cache(path: Path, config: Config, entries: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    value = {"version": INDEX_VERSION, "root": str(config.wiki_root.resolve()), "entries": entries}
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=path.stem+"-", suffix=".tmp", delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(value, stream, ensure_ascii=False, separators=(",", ":"))
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _page_entries(config: Config, cache: dict, scope: str):
    from .curation import excluded_paths, removed_ids
    blocked, removed = excluded_paths(config), removed_ids(config)
    entries, pages, coverage = {}, [], {"pages":0, "catalog_items":0, "source_files":0, "excluded":0, "unreadable":0, "not_downloaded":0}
    reused = updated = 0
    for folder in PAGE_DIRS:
        for path in sorted((config.wiki_root / folder).glob("*.md")):
            relative = path.relative_to(config.wiki_root).as_posix()
            if relative in blocked or not path.resolve().is_relative_to(config.wiki_root.resolve()):
                coverage["excluded"] += 1
                continue
            try:
                sig = _signature(path)
                old = cache.get(relative)
                if old and old.get("signature") == sig:
                    entry = old
                    reused += 1
                else:
                    meta, body = read_page(path)
                    if meta.get("status") == "archived" or not isinstance(meta.get("title"),str) or meta.get("type") not in {"method","recipe","template","scenario","interface","chart-type","project","source","layout"}:
                        coverage["excluded"] += 1
                        continue
                    record = _record(path, meta, clean_body(body), config)
                    entry = {"signature":sig, "document":_document(record,body,_metadata(meta))}
                    updated += 1
                record = entry["document"]["record"]
                if record["id"] in removed or record.get("source") in removed:
                    coverage["excluded"] += 1
                    continue
                pages.append((path, record))
                if scope == "knowledge":
                    entries[relative] = entry
                    coverage["pages"] += 1
            except (WikiError, OSError, ValueError, TypeError, KeyError, UnicodeError):
                coverage["unreadable"] += 1
    return entries, pages, coverage, reused, updated


def _catalog_entries(config: Config, entries: dict, cache: dict, coverage: dict):
    # L0 follows the fresh source inventory; promoted entries are represented by
    # their recipe page instead. Catalog statuses are not executable evidence.
    from .finder import _item_record
    from .sources import read_items
    from .curation import removed_ids
    promoted = {v["document"]["record"].get("source") for v in entries.values()}
    removed = removed_ids(config)
    for key, entry in list(entries.items()):
        record = entry["document"]["record"]
        if record["kind"] != "source":
            continue
        try:
            meta = read_page(config.wiki_root / record["page"])[0]
            for item in read_items(config, record["id"]):
                if item["id"] in promoted or item["id"] in removed:
                    continue
                rec = _item_record(item,meta)
                for field in ("usable","run","missing_packages"):
                    rec.pop(field,None)
                signature = hashlib.sha256(json.dumps(item,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
                cache_key = "item:"+rec["id"]
                old = cache.get(cache_key)
                entries[cache_key] = old if old and old.get("signature")==signature else {
                    "signature":signature, "document":_document(rec,rec["summary"]+"\n"+rec.get("scenario", ""),_metadata(item))}
                coverage["catalog_items"] += 1
        except (WikiError,OSError,TypeError,ValueError,KeyError):
            coverage["unreadable"] += 1


def _source_entries(config: Config, pages: list, cache: dict, coverage: dict):
    from .sources import snapshot_dir
    entries, seen = {}, set()
    for page_path, record in pages:
        roots = [page_path.with_suffix("") / folder for folder in ("source", "code")]
        if record["kind"] == "source" and config.sources_root:
            try:
                roots.append(snapshot_dir(config,read_page(page_path)[0]))
            except (WikiError,KeyError,TypeError):
                pass
        if not any(root.is_dir() for root in roots):
            coverage["not_downloaded"] += 1
        for root in roots:
            if not root.is_dir():
                continue
            base = root.resolve()
            # Prune data/cache trees before traversal, not only after reading.
            for walk_root, dirs, names in os.walk(root, followlinks=False):
                dirs[:] = sorted(d for d in dirs if d.lower() not in SKIP_DIRS and not d.startswith("."))
                for name in sorted(names):
                    path = Path(walk_root) / name
                    relative = path.relative_to(root).as_posix()
                    if (path.suffix.lower() not in SOURCE_EXTENSIONS or name.startswith(".") or
                            not path.resolve().is_relative_to(base) or path.stat().st_size > MAX_SOURCE_BYTES):
                        continue
                    key = str(path.resolve())
                    if key in seen:
                        continue
                    seen.add(key)
                    try:
                        signature = _signature(path)
                        old = cache.get(key)
                        source_path = (record["page"].removesuffix(".md")+"/"+root.name+"/"+relative if root.parent==page_path.with_suffix("") else record["id"]+"/"+relative)
                        source_record = {**record,"source_path":source_path,"source_scope":True}
                        source_record["id"] = record["id"] + "::" + source_path
                        source_record["parent_id"] = record["id"]
                        source_record["asset_id"] = record["id"]
                        if old and old.get("signature")==signature and old["document"]["record"]==source_record:
                            entry=old
                        else:
                            text=path.read_text(encoding="utf-8-sig")
                            if "\x00" in text:
                                continue
                            entry={"signature":signature,"document":_document(source_record,text,source_path)}
                        entries[key]=entry
                        coverage["source_files"]+=1
                    except (OSError,UnicodeError):
                        coverage["unreadable"]+=1
    return entries


def _index(config: Config, scope: str) -> dict:
    if scope not in ("knowledge","source"):
        raise WikiError("scope 必须是 knowledge 或 source")
    path = _cache_path(config, scope)
    with LOCK:
        cache = _load_cache(path,config)
        # Source cache keys are files; page metadata uses the knowledge cache.
        page_cache = cache if scope=="knowledge" else _load_cache(_cache_path(config,"knowledge"),config)
        entries,pages,coverage,reused,updated = _page_entries(config,page_cache,scope)
        if scope=="knowledge":
            _catalog_entries(config,entries,cache,coverage)
        else:
            entries=_source_entries(config,pages,cache,coverage)
            reused=sum(1 for k,v in entries.items() if cache.get(k)==v)
            updated=len(entries)-reused
        if entries != cache:
            _write_cache(path,config,entries)
    documents=[v["document"] for _,v in sorted(entries.items())]
    frequencies=Counter()
    lengths=[]
    for doc in documents:
        for section in doc["sections"]:
            frequencies.update(section["tf"].keys())
            lengths.append(section["length"])
    return {"schema_version":SCHEMA_VERSION,
            "tokenizer":{"version":2,"aliases":QUERY_ALIASES,"alias_scope":"query","stopwords":STOPWORDS,"cjk_ngrams":[2],"english_pattern":"[a-z0-9]+"},
            "ranking":RANKING,"documents":documents,
            "statistics":{"document_count":len(lengths),"average_length":sum(lengths)/max(1,len(lengths)),"df":dict(frequencies)},
            "coverage":{**coverage,"scope":scope,"source_search":"downloaded-code-only" if scope=="source" else "explicit-source-scope-required"},
            "index":{"version":INDEX_VERSION,"scope":scope,"reused":reused,"updated":updated,"documents":len(documents),"cache":"derivative"}}


def _snippet(text: str, tokens: set[str]) -> str:
    text=_plain(text)
    positions=[text.lower().find(t) for t in tokens if not t.startswith("@") and t in text.lower()]
    start=max(0,min(positions)-60) if positions else 0
    return ("…" if start else "")+text[start:start+220]+("…" if len(text)>start+220 else "")


def rank_export(index: dict, query: str, kind=None, level=None, runnable=False, limit=10, scope="knowledge") -> list[dict]:
    """Pure ranking contract shared with the static JavaScript frontend.

    Static `usable`/`run` flags, if supplied by export_index, are dated snapshots.
    Live search always rechecks current files before applying runnable filtering.
    """
    if not str(query).strip() or index.get("coverage",{}).get("scope","knowledge")!=scope:
        return []
    tokens=set(tokenize(query,index.get("tokenizer",{}).get("aliases",ALIASES),index.get("tokenizer",{}).get("stopwords",[])))
    stats=index["statistics"]
    n,avg=stats["document_count"],max(1,stats["average_length"])
    k1,b=index["ranking"]["k1"],index["ranking"]["b"]
    results=[]
    for doc in index["documents"]:
        record=doc["record"]
        if (kind and record["kind"]!=kind) or (level and record["level"]!=level):
            continue
        if runnable and not (record.get("usable") or record.get("run")=="pass"):
            continue
        best_score,best=0.0,None
        for section in doc["sections"]:
            score=0.0
            for token in sorted(tokens):
                tf=section["tf"].get(token,0)
                if not tf:
                    continue
                df=stats["df"].get(token,0)
                idf=math.log(1+(n-df+.5)/(df+.5))
                score+=idf*tf*(k1+1)/(tf+k1*(1-b+b*section["length"]/avg))
            if score>best_score:
                best_score,best=score,section
        if best is not None:
            results.append({**record,"score":round(best_score,6),"why":["正文 BM25 · "+best["title"]],
                            "match_section":best["title"],"snippet":_snippet(best["text"],tokens)})
    results.sort(key=lambda r:(-r["score"],r["id"]))
    return results[:max(0,min(int(limit),1000))]


def _availability(config: Config, page_path: Path) -> dict:
    try:
        from .asset_checkout import assets_state
        return assets_state(config,page_path)
    except ImportError:
        return {"state":"available" if page_path.with_suffix("").is_dir() else "not_downloaded",
                "profile":"full","missing":[]}


def _fresh(config: Config, record: dict) -> dict | None:
    from .finder import _recipe_record,_template_record,_method_record
    path=config.wiki_root / record["page"]
    try:
        meta,body=read_page(path)
        if meta.get("status")=="archived":
            return None
        current={**record}
        kind=record["kind"]
        builder={"recipe":_recipe_record,"template":_template_record,"method":_method_record}.get(kind)
        if builder:
            current.update(builder(config,path,meta,body))
            if kind == "recipe" and current.get("run_scope") != "as-is":
                current["run"] = "none"
            if record.get("source_scope"):
                current.update(id=record["id"],parent_id=record["parent_id"])
        elif kind=="item":
            current.update(usable=False,run="none")
        elif kind == 'layout':
            current.update(usable=False, run='none', reference_only=True)
        availability=_availability(config,path)
        current["asset_availability"]=availability.get("state", "missing")
        current["asset_details"]=availability
        if availability.get("state")!="available":
            current["usable"]=False
            if kind=="recipe":
                current["run"]="none"
        current["evidence_state"]=("current" if current.get("usable") or current.get("run")=="pass" else
                                   "not_downloaded" if availability.get("state")=="not_downloaded" else "unverified")
        return current
    except (WikiError,OSError,ValueError,TypeError,KeyError):
        return None


def search(config: Config, query: str, kind=None, level=None, runnable=False, limit=10, scope="knowledge") -> dict:
    from .read_cache import read_session
    if not str(query).strip():
        raise WikiError("给出关键词，例如：find 差异表达")
    # read_session is request-local: no verification/status survives a new query.
    with read_session():
        index=_index(config,scope)
        ranked=rank_export(index,query,kind=kind,limit=1000,scope=scope)
        results=[]
        if int(limit) <= 0:
            return {"results": [], "coverage": index["coverage"], "index": index["index"]}
        for record in ranked:
            fresh=_fresh(config,record)
            if fresh is None or (level and fresh["level"]!=level):
                continue
            if runnable and not (fresh.get("usable") or fresh.get("run")=="pass"):
                continue
            results.append(fresh)
            if len(results)>=max(0,min(int(limit),1000)):
                break
        return {"results":results,"coverage":index["coverage"],"index":index["index"]}


def export_index(config: Config) -> dict:
    """Export knowledge text/tokens and explicitly dated evidence snapshots.

    No raw code is copied into static search; source scope is online/CLI only.
    """
    from datetime import datetime,timezone
    from .read_cache import read_session
    with read_session():
        index=_index(config,"knowledge")
        # Copy before adding evidence: never mutate the persistent derivative cache.
        index=json.loads(json.dumps(index,ensure_ascii=False))
        for doc in index["documents"]:
            fresh=_fresh(config,doc["record"])
            if fresh:
                doc["record"]=fresh
        index["coverage"].update(evidence="export_snapshot",source_available=False,
                                  exported_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        return index
