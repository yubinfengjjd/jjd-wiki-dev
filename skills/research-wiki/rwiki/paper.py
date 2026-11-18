"""Literature computational replication workflow (trace -> fetch -> parse -> plan -> publish)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .aliases import resolve_page_ref
from .config import Config
from .dedup import assert_no_high_duplicate, check_duplicates
from .errors import WikiError
from .naming import title_hygiene_issues, validate_new_id
from .pages import write_page
from .store import guarded, save

_DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b")
_PMID_RE = re.compile(r"(?:\bPMID[:\s]*|pubmed\.ncbi\.nlm\.nih\.gov/)(\d{6,9})\b", re.I)
_PMCID_RE = re.compile(r"\b(PMC\d{5,9})\b", re.I)
_REPO_RE = re.compile(
    r"https?://(?:github\.com|gitlab\.com|bitbucket\.org|zenodo\.org|figshare\.com)/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9.-]+[A-Za-z0-9])*",
    re.I,
)
_DATA_ACC_RE = re.compile(r"\b(?:GSE\d{4,8}|GSM\d{5,9}|PRJNA\d{4,8}|E-MTAB-\d{3,7}|TCGA-[A-Z]{2,6})\b")

_WET_LAB_TERMS = (
    "mice", "mouse", "xenograft", "intraperitoneal", "subcutaneous", "euthanized",
    "western blot", "immunoblot", "immunohistochemistry", "ihc", "immunofluorescence",
    "hek293", "dmem", "fetal bovine serum", "fbs", "transfection", "sirna", "shrna",
    "cck-8", "cck8", "transwell", "flow cytometry", "elisa", "animal care", "ethics committee",
    "动物", "小鼠", "裸鼠", "细胞培养", "转染", "免疫组化", "蛋白免疫印迹", "流式细胞", "伦理", "造模",
)
_COMP_TERMS = (
    "seurat", "scanpy", "wgcna", "hdwgcna", "deseq2", "edger", "limma", "gsea", "gsva",
    "cellchat", "nichenet", "monocle", "slingshot", "scvelo", "harmony", "umap", "tsne",
    "pca", "cox", "kaplan-meier", "roc", "auc", "lasso", "xgboost", "random forest",
    "shap", "ggplot2", "igraph", "single-cell", "rna-seq", "transcriptome", "differential",
    "enrichment", "clustering", "regression", "p-value", "fdr", "benjamini",
    "单细胞", "差异表达", "富集", "降维", "聚类", "共表达", "生存分析", "回归", "机器学习",
)

_SECTION_HEADING_RE = re.compile(
    r"^(?:Materials\s+and\s+Methods|Methods|Bioinformatics\s+Analysis|Statistical\s+Analysis|"
    r"Data\s+(?:and\s+Code\s+)?Availability|Code\s+Availability|Data\s+Availability)\b",
    re.I,
)
_CAPTION_RE = re.compile(r"^((?:Supplementary\s+)?Fig(?:ure)?\.?\s*\d+)\s*[.:]\s+([A-Z\u4e00-\u9fff].*)", re.I)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return slug[:64].strip("-") or "paper"


def _papers_root(config: Config) -> Path:
    base = config.sources_root if config.sources_root is not None else (config.work_root / "sources")
    return base / "papers"


def _paper_dir(config: Config, paper_id: str) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", paper_id or ""):
        raise WikiError(f"paper_id 只允许小写字母、数字和连字符: {paper_id}")
    return _papers_root(config) / paper_id


def _load_paper(config: Config, paper_id: str) -> tuple[Path, dict]:
    pdir = _paper_dir(config, paper_id)
    meta_path = pdir / "paper.json"
    if not meta_path.is_file():
        raise WikiError(f"文献工作区不存在: {paper_id}")
    return pdir, json.loads(meta_path.read_text(encoding="utf-8"))


def _save_paper(pdir: Path, payload: dict) -> dict:
    payload["updated_at"] = _now_iso()
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / "paper.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return payload


def extract_identifiers(text: str) -> dict:
    """Extract DOI, PMID, PMCID, open-source repo URLs, and GEO/TCGA accessions from text."""
    clean = text or ""
    dois = [m.rstrip(".,;)]}") for m in _DOI_RE.findall(clean)]
    pmids = list(dict.fromkeys(_PMID_RE.findall(clean)))
    pmcids = list(dict.fromkeys(m.upper() for m in _PMCID_RE.findall(clean)))
    repos = list(dict.fromkeys(m.rstrip(".,;)]}") for m in _REPO_RE.findall(clean)))
    accessions = list(dict.fromkeys(m.upper() for m in _DATA_ACC_RE.findall(clean)))
    return {
        "dois": list(dict.fromkeys(dois)),
        "pmids": pmids,
        "pmcids": pmcids,
        "repo_urls": repos,
        "data_accessions": accessions,
    }


def _http_get_json(url: str, timeout: int = 15) -> dict | None:
    import requests
    try:
        resp = requests.get(url, headers={"User-Agent": "research-wiki/1.0"}, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        return None
    return None


def _lookup_europepmc(query: str) -> dict | None:
    from urllib.parse import quote
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={quote(query)}&resultType=core&format=json&pageSize=3"
    data = _http_get_json(url, timeout=8)
    results = (((data or {}).get("resultList") or {}).get("result")) or []
    return results[0] if results else None


def _lookup_openalex(doi: str) -> dict | None:
    from urllib.parse import quote
    if not doi:
        return None
    url = f"https://api.openalex.org/works/{quote(f'https://doi.org/{doi}', safe='/:')}"
    return _http_get_json(url, timeout=10)


def _lookup_ncbi_idconv(identifier: str) -> dict | None:
    from urllib.parse import quote
    if not identifier:
        return None
    url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids={quote(identifier)}&format=json&tool=research-wiki&email=noreply@example.org"
    data = _http_get_json(url, timeout=10)
    records = (data or {}).get("records") or []
    return records[0] if records and not records[0].get("errmsg") else None


def _lookup_crossref(doi_or_query: str, *, is_doi: bool) -> dict | None:
    from urllib.parse import quote
    if is_doi:
        url = f"https://api.crossref.org/works/{quote(doi_or_query, safe='')}"
        data = _http_get_json(url)
        return (data or {}).get("message")
    url = f"https://api.crossref.org/works?query.bibliographic={quote(doi_or_query)}&rows=2"
    data = _http_get_json(url)
    items = (((data or {}).get("message") or {}).get("items")) or []
    return items[0] if items else None


def trace_paper(
    config: Config,
    *,
    paper_id: str = "",
    query: str = "",
    doi: str = "",
    pmid: str = "",
    pmcid: str = "",
    source_url: str = "",
    source_text_path: Path | None = None,
    repo_url: str = "",
    offline: bool = False,
) -> dict:
    """Trace an original paper from secondary text/identifiers and initialize its local paper workspace."""
    text_chunks = [query, doi, pmid, pmcid, source_url, repo_url]
    if source_text_path is not None:
        if not Path(source_text_path).is_file():
            raise WikiError(f"来源文本不存在: {source_text_path}")
        text_chunks.append(Path(source_text_path).read_text(encoding="utf-8", errors="replace"))
    combined = "\n".join(c for c in text_chunks if c)
    extracted = extract_identifiers(combined)

    resolved_doi = doi.strip() or (extracted["dois"][0] if extracted["dois"] else "")
    resolved_pmid = pmid.strip() or (extracted["pmids"][0] if extracted["pmids"] else "")
    resolved_pmcid = pmcid.strip().upper() or (extracted["pmcids"][0] if extracted["pmcids"] else "")
    title = query.strip() if query.strip() and not resolved_doi else ""
    journal = ""
    year = ""
    abstract = ""
    authors: list[str] = []
    oa_pdf_urls: list[str] = []
    is_oa = False

    if not offline:
        epmc_query = ""
        if resolved_pmcid:
            epmc_query = f"PMCID:{resolved_pmcid}"
        elif resolved_pmid:
            epmc_query = f"EXT_ID:{resolved_pmid}"
        elif resolved_doi:
            epmc_query = f'DOI:"{resolved_doi}"'
        elif query.strip():
            epmc_query = query.strip()

        epmc = _lookup_europepmc(epmc_query) if epmc_query else None
        if epmc:
            title = str(epmc.get("title") or title).strip().rstrip(".")
            resolved_doi = str(epmc.get("doi") or resolved_doi).strip()
            resolved_pmid = str(epmc.get("pmid") or resolved_pmid).strip()
            resolved_pmcid = str(epmc.get("pmcid") or resolved_pmcid).strip().upper()
            journal = str(epmc.get("journalTitle") or "").strip()
            year = str(epmc.get("pubYear") or "").strip()
            abstract = str(epmc.get("abstractText") or "").strip()
            is_oa = str(epmc.get("isOpenAccess") or "").upper() == "Y"
            author_str = str(epmc.get("authorString") or "").strip()
            if author_str:
                authors = [a.strip() for a in author_str.split(",") if a.strip()][:8]
            for ft in ((epmc.get("fullTextUrlList") or {}).get("fullTextUrl") or []):
                if isinstance(ft, dict) and str(ft.get("documentStyle") or "").lower() == "pdf" and ft.get("url"):
                    oa_pdf_urls.append(str(ft["url"]))
            if resolved_pmcid:
                oa_pdf_urls.append(f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={resolved_pmcid}&blobtype=pdf")

        if (not title or not resolved_doi) and (resolved_doi or query.strip()):
            cr = _lookup_crossref(resolved_doi or query.strip(), is_doi=bool(resolved_doi))
            if cr:
                if not resolved_doi and cr.get("DOI"):
                    resolved_doi = str(cr["DOI"]).strip()
                if not title and cr.get("title"):
                    tlist = cr["title"]
                    title = str(tlist[0] if isinstance(tlist, list) else tlist).strip()
                if not journal and cr.get("container-title"):
                    jlist = cr["container-title"]
                    journal = str(jlist[0] if isinstance(jlist, list) else jlist).strip()
                if not year:
                    parts = (((cr.get("published") or {}).get("date-parts")) or [[""]])[0]
                    if parts and parts[0]:
                        year = str(parts[0])
                for link in cr.get("link") or []:
                    if isinstance(link, dict) and "pdf" in str(link.get("content-type") or "").lower() and link.get("URL"):
                        oa_pdf_urls.append(str(link["URL"]))

        if resolved_doi:
            oa_data = _lookup_openalex(resolved_doi)
            if oa_data:
                is_oa = is_oa or bool(((oa_data.get("open_access") or {}).get("is_oa")))
                if not title and oa_data.get("title"):
                    title = str(oa_data["title"]).strip()
                if not year and oa_data.get("publication_year"):
                    year = str(oa_data["publication_year"])
                for loc in oa_data.get("locations") or []:
                    if isinstance(loc, dict) and loc.get("pdf_url"):
                        oa_pdf_urls.append(str(loc["pdf_url"]))
            idrec = _lookup_ncbi_idconv(resolved_doi)
            if idrec:
                if not resolved_pmcid and idrec.get("pmcid"):
                    resolved_pmcid = str(idrec["pmcid"]).upper()
                if not resolved_pmid and idrec.get("pmid"):
                    resolved_pmid = str(idrec["pmid"])
        if resolved_pmcid:
            oa_pdf_urls.extend([
                f"https://pmc.ncbi.nlm.nih.gov/articles/{resolved_pmcid}/pdf/",
                f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={resolved_pmcid}&blobtype=pdf",
            ])

    extra_ids = extract_identifiers(abstract)
    repo_urls = list(dict.fromkeys([*extracted["repo_urls"], *extra_ids["repo_urls"]]))
    data_accs = list(dict.fromkeys([*extracted["data_accessions"], *extra_ids["data_accessions"]]))
    oa_pdf_urls = list(dict.fromkeys(oa_pdf_urls))

    pid = paper_id.strip() if paper_id.strip() else _slugify(
        resolved_pmcid or resolved_pmid or (f"{year}-{title[:32]}" if year and title else title or resolved_doi or "paper")
    )
    pdir = _paper_dir(config, pid)
    payload = {
        "schema_version": 1,
        "paper_id": pid,
        "title": title or pid,
        "doi": resolved_doi,
        "pmid": resolved_pmid,
        "pmcid": resolved_pmcid,
        "journal": journal,
        "year": year,
        "authors": authors,
        "abstract": abstract,
        "source_post_url": source_url,
        "is_open_access": is_oa or bool(oa_pdf_urls),
        "oa_pdf_urls": oa_pdf_urls,
        "repo_urls": repo_urls,
        "data_accessions": data_accs,
        "pdf_path": "",
        "pdf_sha256": "",
        "cloned_repos": [],
        "status": "traced",
        "steps": [],
        "figures": [],
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    _save_paper(pdir, payload)
    return payload


def _clone_author_repo(repo_url: str, dest_dir: Path) -> dict:
    repo_name = _slugify(repo_url.rstrip("/").split("/")[-1].removesuffix(".git"))
    target = dest_dir / repo_name
    if target.exists() and not (target / ".git").exists():
        shutil.rmtree(target, ignore_errors=True)
    if not (target / ".git").exists():
        dest_dir.mkdir(parents=True, exist_ok=True)
        # Use blobless partial clone + sparse-checkout for code/docs to stay fast on large repos
        proc = subprocess.run(
            ["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", repo_url, str(target)],
            capture_output=True,
            text=True,
            timeout=90,
        )
        if proc.returncode != 0:
            shutil.rmtree(target, ignore_errors=True)
            raise WikiError(f"作者开源仓库克隆失败 ({repo_url}): {proc.stderr.strip() or proc.stdout.strip()}")
        subprocess.run(
            ["git", "-C", str(target), "sparse-checkout", "set", "--no-cone",
             "/*.md", "/*.txt", "/LICENSE*", "/DESCRIPTION", "/NAMESPACE",
             "**/*.R", "**/*.r", "**/*.py", "**/*.Rmd", "**/*.ipynb", "**/*.sh"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    commit = subprocess.check_output(["git", "-C", str(target), "rev-parse", "HEAD"], text=True).strip()
    licenses = [p.name for p in target.iterdir() if p.is_file() and p.name.upper().startswith("LICENSE")]
    scripts = sorted(
        p.relative_to(target).as_posix()
        for p in target.rglob("*")
        if p.is_file() and p.suffix.lower() in (".r", ".rmd", ".py", ".ipynb", ".sh") and ".git" not in p.parts
    )
    return {
        "url": repo_url,
        "local_dir": str(target),
        "commit": commit,
        "license_files": licenses,
        "script_count": len(scripts),
        "scripts": scripts[:60],
    }


def fetch_paper(
    config: Config,
    paper_id: str,
    *,
    pdf_path: Path | None = None,
    repo_url: str = "",
    clone_repo: bool = True,
) -> dict:
    """Download OA PDF or register local user-supplied PDF, and optionally shallow-clone author code repos."""
    pdir, meta = _load_paper(config, paper_id)
    pdf_dir = pdir / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    dest_pdf = pdf_dir / "paper.pdf"

    if pdf_path is not None:
        src = Path(pdf_path)
        if not src.is_file():
            raise WikiError(f"提供的本地 PDF 不存在: {src}")
        raw = src.read_bytes()
        if not raw.startswith(b"%PDF-"):
            raise WikiError(f"文件不是有效的 PDF（缺少 %PDF- 文件头）: {src}")
        dest_pdf.write_bytes(raw)
        meta["pdf_path"] = str(dest_pdf)
        meta["pdf_sha256"] = hashlib.sha256(raw).hexdigest()
        meta["pdf_source"] = "local_user_pdf"
        meta["status"] = "fetched"
    else:
        import requests
        downloaded = False
        failures: list[str] = []
        for url in meta.get("oa_pdf_urls") or []:
            try:
                resp = requests.get(url, headers={"User-Agent": "research-wiki/1.0"}, timeout=30, allow_redirects=True)
                if resp.status_code == 200 and resp.content.startswith(b"%PDF-"):
                    dest_pdf.write_bytes(resp.content)
                    meta["pdf_path"] = str(dest_pdf)
                    meta["pdf_sha256"] = hashlib.sha256(resp.content).hexdigest()
                    meta["pdf_source"] = url
                    meta["status"] = "fetched"
                    downloaded = True
                    break
                failures.append(f"{url} -> HTTP {resp.status_code} ({resp.headers.get('Content-Type', '')})")
            except Exception as error:
                failures.append(f"{url} -> {error}")
        if not downloaded:
            meta["status"] = "blocked_paywall"
            meta["fetch_failures"] = failures
            _save_paper(pdir, meta)
            raise WikiError(
                f"无法直接下载公开 OA PDF（可能存在付费墙或反爬验证，按规则不绕过）。请手动下载 PDF 后运行：\n"
                f"rwiki paper fetch {paper_id} --pdf <本地PDF路径>"
            )

    if repo_url.strip() and repo_url.strip() not in (meta.get("repo_urls") or []):
        meta.setdefault("repo_urls", []).append(repo_url.strip())

    if clone_repo and meta.get("repo_urls"):
        cloned: list[dict] = list(meta.get("cloned_repos") or [])
        existing_urls = {c.get("url") for c in cloned}
        for rurl in meta["repo_urls"]:
            if rurl in existing_urls:
                continue
            if any(host in rurl.lower() for host in ("github.com", "gitlab.com", "bitbucket.org")):
                try:
                    cloned.append(_clone_author_repo(rurl, pdir / "repo"))
                except (WikiError, subprocess.TimeoutExpired, OSError) as error:
                    meta.setdefault("repo_errors", []).append(str(error))
        meta["cloned_repos"] = cloned

    return _save_paper(pdir, meta)


def _term_in_text(term: str, low_text: str) -> bool:
    if re.search(r"[\u4e00-\u9fff]", term):
        return term in low_text
    return bool(re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", low_text))


def _classify_paragraph(text: str) -> str:
    low = text.casefold()
    wet_hits = sum(1 for tok in _WET_LAB_TERMS if _term_in_text(tok, low))
    comp_hits = sum(1 for tok in _COMP_TERMS if _term_in_text(tok, low))
    if wet_hits > 0 and comp_hits == 0:
        return "wet_lab"
    if wet_hits >= 2 and wet_hits > comp_hits:
        return "wet_lab"
    return "computational"


def parse_paper_pdf(config: Config, paper_id: str, *, render_pages: bool = True) -> dict:
    """Extract text, Methods, wet-lab exclusions, Figure legends, repos, and page previews via pymupdf."""
    import pymupdf

    pdir, meta = _load_paper(config, paper_id)
    pdf_path = Path(meta.get("pdf_path") or (pdir / "pdf" / "paper.pdf"))
    if not pdf_path.is_file():
        raise WikiError(f"文献尚未下载或提供本地 PDF: {paper_id}")

    ext_dir = pdir / "extracted"
    pages_dir = ext_dir / "pages"
    ext_dir.mkdir(parents=True, exist_ok=True)
    if render_pages:
        pages_dir.mkdir(parents=True, exist_ok=True)

    doc = pymupdf.open(str(pdf_path))
    full_pages: list[str] = []
    rendered_pages: list[str] = []
    for idx, page in enumerate(doc, start=1):
        txt = page.get_text("text") or ""
        full_pages.append(f"## Page {idx}\n\n{txt.strip()}\n")
        if render_pages and idx <= 25:
            out_img = pages_dir / f"page_{idx:02d}.png"
            pix = page.get_pixmap(dpi=150)
            pix.save(str(out_img))
            rendered_pages.append(str(out_img))
    page_count = len(doc)
    doc.close()

    full_text = "\n".join(full_pages)
    (ext_dir / "full_text.md").write_text(full_text, encoding="utf-8", newline="\n")

    # Discover repositories & dataset accessions embedded anywhere in full text
    found_ids = extract_identifiers(full_text)
    meta["repo_urls"] = list(dict.fromkeys([*(meta.get("repo_urls") or []), *found_ids["repo_urls"]]))
    meta["data_accessions"] = list(dict.fromkeys([*(meta.get("data_accessions") or []), *found_ids["data_accessions"]]))

    # Extract paragraphs belonging to Methods / Availability and split wet-lab vs computational
    lines = [line.strip() for line in full_text.splitlines()]
    in_methods = False
    methods_buf: list[str] = []
    captions: list[dict] = []
    for line in lines:
        if not line or line.startswith("## Page "):
            continue
        if _SECTION_HEADING_RE.match(line) and len(line) < 90:
            in_methods = True
            methods_buf.append(f"### {line}")
            continue
        if in_methods and re.match(r"^(?:References|Acknowledgements|Author\s+Contributions|Funding)\b", line, re.I) and len(line) < 60:
            in_methods = False
        if in_methods:
            methods_buf.append(line)
        cmatch = _CAPTION_RE.match(line)
        if cmatch:
            captions.append({"figure": cmatch.group(1).strip(), "text": cmatch.group(0).strip()})

    raw_methods = "\n".join(methods_buf) if methods_buf else full_text
    # Group lines into logical chunks (~sentences/paragraphs)
    chunks = [c.strip() for c in re.split(r"(?:\n\s*\n|(?<=[.。])\s+(?=[A-Z\u4e00-\u9fff]))", raw_methods) if c.strip()]
    comp_chunks: list[str] = []
    wet_chunks: list[str] = []
    for chunk in chunks:
        if _classify_paragraph(chunk) == "wet_lab":
            wet_chunks.append(chunk)
        else:
            comp_chunks.append(chunk)

    (ext_dir / "methods_computational.md").write_text(
        "# Computational & Bioinformatics Methods\n\n" + "\n\n".join(f"- {c}" for c in comp_chunks) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (ext_dir / "excluded_wet_lab.md").write_text(
        "# Excluded Wet-Lab / Animal / Cell Experiments\n\n" + ("\n\n".join(f"- {c}" for c in wet_chunks) or "- 无显式湿实验段落。") + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (ext_dir / "captions.json").write_text(json.dumps(captions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    meta["page_count"] = page_count
    meta["parsed_summary"] = {
        "computational_chunks": len(comp_chunks),
        "excluded_wet_lab_chunks": len(wet_chunks),
        "captions_found": len(captions),
        "rendered_pages": len(rendered_pages),
    }
    meta["status"] = "parsed"
    return _save_paper(pdir, meta)


def _infer_step_hits(text: str) -> list[dict]:
    low = text.casefold()
    step_rules = (
        ("quality-control-preprocessing", "质控与标准化预处理", ("seurat", "qc", "quality control", "mitochondri", "normalize", "preprocessing")),
        ("batch-integration", "多样本整合与批次校正", ("harmony", "integrate", "batch", "mnn")),
        ("dimensionality-reduction-clustering", "降维（PCA/UMAP）与细胞聚类", ("pca", "umap", "tsne", "findclusters", "clustering", "leiden")),
        ("differential-expression", "差异表达分析", ("differential", "deg", "findallmarkers", "deseq2", "limma", "edger", "volcano")),
        ("gene-set-enrichment", "功能通路富集分析（GO/KEGG/GSEA）", ("enrichment", "enrichr", "gsea", "gsva", "pathway", "kegg", "go ")),
        ("coexpression-ppi-network", "共表达网络（WGCNA/hdWGCNA）与互作分析", ("hdwgcna", "wgcna", "co-expression", "coexpression", "ppi", "string")),
        ("cell-cell-communication", "细胞通讯分析", ("cellchat", "cellphonedb", "nichenet", "cell-cell communication", "ligand-receptor")),
        ("trajectory-inference", "拟时序/细胞轨迹分析", ("monocle", "slingshot", "trajectory", "pseudotime", "rna velocity", "scvelo")),
        ("survival-prognosis-analysis", "生存分析与预后建模（KM/Cox/Nomogram）", ("kaplan-meier", "cox", "survival", "hazard ratio", "nomogram", "prognos")),
        ("ml-feature-selection-eval", "机器学习特征筛选与模型评价", ("lasso", "random forest", "xgboost", "svm", "roc", "auc", "shap")),
    )
    steps: list[dict] = []
    for slug, title, kws in step_rules:
        matched = [kw.strip() for kw in kws if _term_in_text(kw.strip(), low)]
        if matched:
            steps.append({
                "step_id": slug,
                "title": title,
                "matched_terms": matched,
                "role": "analysis-subagent",
            })
    return steps


def build_plan(
    config: Config,
    paper_id: str,
    *,
    max_cells: int = 2500,
    max_samples: int = 120,
    include_supp: bool = False,
) -> dict:
    """Generate structured replication plan separating wet-lab exclusions, dedup candidates, and subagent tasks."""
    pdir, meta = _load_paper(config, paper_id)
    comp_path = pdir / "extracted" / "methods_computational.md"
    cap_path = pdir / "extracted" / "captions.json"
    if not comp_path.is_file():
        raise WikiError(f"请先运行 `rwiki paper parse {paper_id}` 解析 PDF")

    comp_text = comp_path.read_text(encoding="utf-8")
    captions = json.loads(cap_path.read_text(encoding="utf-8")) if cap_path.is_file() else []
    detected_steps = _infer_step_hits(comp_text + "\n" + meta.get("abstract", ""))

    enriched_steps: list[dict] = []
    for idx, step in enumerate(detected_steps, start=1):
        dup = check_duplicates(
            config,
            kind="method",
            entry_id=step["step_id"],
            title=step["title"],
            keywords=step["matched_terms"],
            limit=3,
        )
        enriched_steps.append({
            "order": idx,
            **step,
            "existing_methods": [
                {"id": c["id"], "title": c["title"], "score": c["score"], "severity": c["severity"]}
                for c in dup.get("candidates", [])
            ],
        })

    target_figures: list[dict] = []
    for cap in captions:
        fig_name = cap["figure"]
        if not include_supp and "supp" in fig_name.lower():
            continue
        if _classify_paragraph(cap["text"]) == "wet_lab":
            continue
        target_figures.append({
            "figure": fig_name,
            "legend_excerpt": cap["text"][:260],
            "role": "figure-subagent",
            "strategy": "拆解可复用单 panel 入库短 slug 原生模板，并生成 patchwork/matplotlib 组合脚本",
        })

    scale_strategy = {
        "max_cells": max_cells,
        "max_samples": max_samples,
        "priority": [
            "1. 优先从原文公开 GEO/Zenodo/作者仓库抽样小规模真实子集（按分组分层抽样 <= max_cells 或单癌种队列）",
            "2. 若无公开原始数据或受限，停止并由作者决定使用公开同类小样本还是合成视觉近似数据",
        ],
        "seed": 42,
    }

    lines = [
        f"# 文献复刻计划：{meta['title']} (`{paper_id}`)",
        "",
        "## 1. 文献溯源与开源代码资产",
        f"- **DOI**：{meta.get('doi') or '待核'} | **PMID**：{meta.get('pmid') or '无'} | **PMCID**：{meta.get('pmcid') or '无'}",
        f"- **期刊 / 年份**：{meta.get('journal') or '未知'} ({meta.get('year') or '未知'})",
        f"- **数据编号**：{', '.join(meta.get('data_accessions') or []) or '未自动检出'}",
        f"- **作者开源仓库**：{', '.join(meta.get('repo_urls') or []) or '未检测到（将严格按 Methods 重建）'}",
        "",
        "## 2. 边界声明（湿实验剔除 & 小规模算力策略）",
        "- **明确剔除**：动物造模、细胞培养/转染、WB/IHC/CCK-8/流式等湿实验部分不复刻（见 `extracted/excluded_wet_lab.md`）。",
        f"- **算力降维**：单细胞抽样上限 `{max_cells}` cells、队列抽样上限 `{max_samples}` samples，固定随机种子 `{scale_strategy['seed']}`；所有复刻方法页与模板须诚实标注抽样/缩放边界。",
        "",
        "## 3. 生信分析步骤与查重映射（分发 Analysis Subagents）",
    ]
    if enriched_steps:
        for st in enriched_steps:
            reuse = ", ".join(f"{m['id']}(score={m['score']})" for m in st["existing_methods"]) or "无高相似已有方法（评估新建或归并分支）"
            lines.append(f"{st['order']}. **{st['title']}** (`{st['step_id']}`) — 关键词: `{', '.join(st['matched_terms'])}` | 库内查重候选: {reuse}")
    else:
        lines.append("- 未自动匹配到预设生信关键词，请结合 `extracted/methods_computational.md` 手动拆分计算步骤。")

    lines.extend([
        "",
        "## 4. 目标数据图面板计划（分发 Figure Subagents + `sci-figure-replica`）",
    ])
    if target_figures:
        for fg in target_figures:
            lines.append(f"- **{fg['figure']}**：{fg['legend_excerpt']}")
    else:
        lines.append("- 未从文本自动识别出 Main Figure 生物信息图注，请结合 `extracted/pages/` 图像人工选图。")

    lines.extend([
        "",
        "## 5. 主协调者自审验收清单（Coordinator Review Gate）",
        "- [ ] 确认每个计算步骤严格忠于原文 Methods 或作者开源代码（统计口径、参数未静默篡改）",
        "- [ ] 运行 `rwiki check-dup` 确保不产生重复方法家族或冗余同型模板",
        "- [ ] 每张复刻图经过 `sci-figure-replica` 并排视觉对比（`side_by_side.png` + `qa_report.md`）及各单 panel 原生模板 `verify-template`",
        "- [ ] 通过 `rwiki check-entry` 与 `rwiki lint`（0 ERROR）后交作者终审签核 `mark-ready`",
        "",
    ])

    plan_path = pdir / "plan.md"
    plan_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")

    meta["steps"] = enriched_steps
    meta["figures"] = target_figures
    meta["scale_down_strategy"] = scale_strategy
    meta["plan_path"] = str(plan_path)
    meta["status"] = "planned"
    return _save_paper(pdir, meta)


def publish_paper_workflow(
    config: Config,
    paper_id: str,
    *,
    workflow_id: str,
    title: str,
    tags: list[str] | None = None,
    data_domains: list[str] | None = None,
    derived_methods: list[str] | None = None,
    derived_templates: list[str] | None = None,
    scale_down_note: str = "",
    dedup_note: str = "",
    force: bool = False,
) -> str:
    """Publish a literature replication summary as a Wiki `method_kind=workflow` page."""
    id_issues = validate_new_id("method", workflow_id)
    if id_issues:
        raise WikiError("；".join(id_issues))
    t_issues = title_hygiene_issues(title, entry_id=workflow_id, strict_content_name=False)
    if t_issues:
        raise WikiError("；".join(t_issues))

    pdir, meta = _load_paper(config, paper_id)
    target = config.wiki_root / "methods" / f"{workflow_id}.md"
    if target.exists():
        raise WikiError(f"workflow 方法页已存在: {workflow_id}")

    for mid in derived_methods or []:
        if resolve_page_ref(config.wiki_root, mid, expected_type="method") is None:
            raise WikiError(f"引用的分析方法不存在: {mid}")
    for tid in derived_templates or []:
        if resolve_page_ref(config.wiki_root, tid, expected_type="template") is None:
            raise WikiError(f"引用的衍生模板不存在: {tid}")

    assert_no_high_duplicate(
        config,
        kind="method",
        entry_id=workflow_id,
        title=title,
        summary=f"文献复刻流程：{meta.get('title', paper_id)}",
        keywords=[paper_id],
        dedup_note=dedup_note,
        force=force,
    )

    cite_entry = f"{meta.get('title', paper_id)} ({meta.get('journal') or 'Literature'}, {meta.get('year') or 'N/A'})"
    if meta.get("doi"):
        cite_entry += f" DOI: {meta['doi']}"
    repo_list = meta.get("repo_urls") or []
    acc_list = meta.get("data_accessions") or []
    step_lines = "\n".join(
        f"- **步骤 {s.get('order', '?')} · {s.get('title')}**：关键词 `{', '.join(s.get('matched_terms') or [])}`"
        for s in (meta.get("steps") or [])
    ) or "- 详见文献复刻计划。"
    method_links = "、".join(f"[[methods/{m}]]" for m in (derived_methods or [])) or "待补充"
    template_links = "、".join(f"[[templates/{t}]]" for t in (derived_templates or [])) or "待补充"
    scale_text = scale_down_note.strip() or (
        f"受本机算力限制，采用小规模抽样/降维子集验证算法链路与出图模板"
        f"（{json.dumps(meta.get('scale_down_strategy') or {}, ensure_ascii=False)}），不冒充原论文全队列统计检验。"
    )

    page_meta = {
        "type": "method",
        "id": workflow_id,
        "title": title.strip(),
        "status": "draft",
        "method_kind": "workflow",
        "tags": tags or ["single-cell"],
        "data_domains": data_domains or ["single-cell"],
        "inputs": [],
        "outputs": [],
        "source": {"kind": "written"},
        "license": "LicenseRef-Literature-Workflow",
        "cite": [cite_entry],
        "favorite": False,
        "summary": f"文献《{meta.get('title', paper_id)[:40]}》纯生信方法拆解与复刻组合流程（已剔除湿实验，共同分析引用既有家族）。",
        "keywords": ["文献复刻", *(acc_list[:4])],
        "data_contract": {
            "input": f"原始数据/抽样子集（{', '.join(acc_list) or '小规模输入'}）与文献 Methods 流程。",
            "output": f"复用方法分支（{', '.join(derived_methods or []) or '待关联'}）与复刻可视化模板。",
        },
    }
    body = (
        f"# {page_meta['title']}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n"
        f"## 用途\n\n复刻文献《{meta.get('title', paper_id)}》的纯生信分析链路与主要发表级可视化图表；已明确剔除动物/细胞湿实验部分。\n\n"
        f"## 适用\n\n- 原文开源代码仓库：{', '.join(repo_list) or '无（按 Methods 重建）'}\n"
        f"- 关联数据编号：{', '.join(acc_list) or '见原文'}\n\n"
        f"## 不适用\n\n- {scale_text}\n\n"
        f"## 输入\n\n详见各关联分析方法与衍生模板数据契约。\n\n"
        f"## 怎么做\n\n{step_lines}\n\n"
        f"## 代码\n\n- 关联分析家族：{method_links}\n- 衍生可视化模板：{template_links}\n\n"
        f"## 输出\n\n各阶段分析中间表与复刻图表产物。\n\n"
        f"## 知识关联检查\n\n"
        + (f"查重说明：{dedup_note.strip()} " if dedup_note.strip() else "")
        + f"workflow 页仅记录跨方法串联流程，不声明 `figure_relations` 主记录；已挂载衍生方法：{method_links}；衍生模板：{template_links}。\n\n"
        "## 使用记录\n\n<!-- user:start -->\n<!-- user:end -->\n"
    )
    with guarded(config, target):
        write_page(target, page_meta, body)
        save(config, f"publish paper workflow {workflow_id} from {paper_id}")
    meta["published_workflow_id"] = workflow_id
    meta["status"] = "published"
    _save_paper(pdir, meta)
    return workflow_id


def paper_status(config: Config, paper_id: str = "") -> dict:
    """List all tracked paper workspaces or return details of one paper workspace."""
    if paper_id.strip():
        _, meta = _load_paper(config, paper_id.strip())
        return meta
    root = _papers_root(config)
    items: list[dict] = []
    if root.is_dir():
        for pjson in sorted(root.glob("*/paper.json")):
            try:
                m = json.loads(pjson.read_text(encoding="utf-8"))
                items.append({
                    "paper_id": m.get("paper_id"),
                    "title": m.get("title"),
                    "doi": m.get("doi"),
                    "status": m.get("status"),
                    "steps_count": len(m.get("steps") or []),
                    "figures_count": len(m.get("figures") or []),
                    "repo_urls": m.get("repo_urls") or [],
                    "updated_at": m.get("updated_at"),
                })
            except Exception:
                continue
    return {"papers": items, "total": len(items)}
