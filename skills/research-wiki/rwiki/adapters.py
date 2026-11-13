"""来源适配器：把上游库的一个条目读成 L0 目录记录。

适配器只读快照，不执行上游代码。新增来源时在 ADAPTERS 注册一个带
BASE_PATTERNS / item_patterns / scan / recipe_id 的对象即可。
"""
import re
from pathlib import Path

CJK = re.compile(r"[\u4e00-\u9fff]")
FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^(#{1,4})\s+(.*?)\s*#*\s*$")
SECTION_KEYS = (
    ("requirement", re.compile(r"需求描述|requirement|demand description", re.I)),
    ("scenario", re.compile(r"应用场景|application scenario", re.I)),
    ("inputs", re.compile(r"输入文件|输入数据|^input", re.I)),
)
DATA_EXT = r"csv|txt|tsv|rds|rdata|rda|xlsx|xls|gmt|maf|gct|cls|bed|bw|bigwig|json|gz|zip|vcf|fa|fasta|seg|mat"
FILE_LITERAL = re.compile(r"""["']([^"'\n]*?\.(?:%s))["']""" % DATA_EXT, re.I)
CALL_LITERAL = re.compile(r"""([A-Za-z_][\w.:]*)\s*\(\s*(?:[\w.]+\s*=\s*)?["']([^"'\n]+)["']""")
READERS = re.compile(r"(^|::)(read[._]\w*|fread|readRDS|load|readLines|import|getGmt|read\.gmt|scan|"
                     r"read_excel|loadRData|data\.table::fread|vroom)$", re.I)
WRITERS = re.compile(r"(^|::)(ggsave|pdf|png|svg|tiff|jpeg|cairo_pdf|svglite|write[._]\w*|fwrite|"
                     r"saveRDS|save|writeLines|ggexport|export|graph2pdf|save_plot|htmlwidgets::saveWidget|saveWidget)$",
                     re.I)
FIGURE_EXT = re.compile(r"\.(pdf|png|svg|tiff?|jpe?g|html)$", re.I)
LIBRARY = re.compile(r"\b(?:library|require|requireNamespace)\(\s*[\"']?([A-Za-z][\w.]*)[\"']?")
NAMESPACED = re.compile(r"(?<![\w.])([A-Za-z][\w.]*[\w]):::?(?=[A-Za-z.])")
PKG_VECTOR = re.compile(r"\b(cran|bioc|required|github)_packages\s*<-\s*c\(([^)]*)\)", re.S)
GITHUB = re.compile(r"install_github\(\s*[\"']([\w.-]+/[\w.-]+)[\"']")
QUOTED = re.compile(r"[\"']([^\"']+)[\"']")
BASE_PACKAGES = {"base", "compiler", "datasets", "graphics", "grDevices", "grid", "methods", "parallel",
                 "splines", "stats", "stats4", "tcltk", "tools", "utils"}
URL = re.compile(r"https?://[^\s)>\]]+")

# Auto tags only steer discovery; recipe pages get curated tags.
TAG_RULES = (
    ("survival-analysis", r"surviv|生存|kaplan|\bkm\b|\bcox\b|hazard|\bhrs?\b|nomogram|列线图|riskscore|risk|"
                          r"风险|prognos|预后|\brms\b|swimmer|mortality|死亡"),
    ("diagnostic-roc", r"\broc\b|auc|calibrat|校准|\bdca\b|决策曲线|diagnos|诊断|c-?index|cindex|logistic"),
    ("transcriptomics", r"volcano|火山|\bdeg\b|差异表达|limma|deseq|edger|gsea|gsva|ssgsea|enrich|富集|kegg|"
                        r"pathway|通路|immun|免疫|\btme\b|expression|表达|lncrna|mirna"),
    ("single-cell", r"single.?cell|单细胞|seurat|umap|tsne|t-sne|monocle|velocity|cellchat|scenic|singler|"
                    r"slingshot|\bmagic\b|空间转录|spatial|scrna"),
    ("machine-learning", r"lasso|\bsvm\b|random.?forest|xgboost|boruta|machine.?learning|机器学习|elastic|"
                         r"\bgbm\b|ranger|\bbart\b|\bnmf\b|consensus|聚类|cluster"),
    ("multi-omics", r"mutat|突变|\bcnv\b|copy.?number|拷贝数|methyl|甲基化|\btmb\b|\bsnv\b|\bmaf\b|oncoprint|"
                    r"oncoplot|chip|atac|peak|motif|chromosome|染色体|multi.?omic|多组学|genome|基因组"),
    ("experimental-statistics", r"box|violin|箱线|小提琴|\bbar\b|柱|correl|相关|pairwise|wilcox|fisher|anova|"
                                r"bland|t-?test|卡方"),
)
CHART_RULES = (
    ("volcano", r"volcano|火山"), ("heatmap", r"heatmap|热图"),
    ("km-curve", r"surviv|kaplan|logrank|\bkm\b|生存曲线|生存分析"),
    ("forest", r"forest|森林|\bhrs?\b|subgroup|亚组"), ("boxplot", r"box|箱线"), ("violin", r"violin|小提琴"),
    ("bar", r"\bbar|柱"), ("pie", r"pie|饼"), ("sankey", r"sankey|桑基|alluvial"), ("circos", r"circos|circ"),
    ("venn", r"venn|韦恩|维恩"), ("roc", r"\broc\b"), ("bubble", r"bubble|气泡"), ("dotplot", r"dot"),
    ("network", r"network|网络|ppi|string|interaction"), ("radar", r"radar|雷达"), ("lollipop", r"lollipop|棒棒糖"),
    ("scatter", r"scatter|cor\b|correlation|相关"), ("pca", r"\bpca\b|pcoa"), ("umap", r"umap"), ("tsne", r"tsne"),
    ("density", r"density|密度|ridge"), ("manhattan", r"manhattan"), ("nomogram", r"nomogram|列线图"),
    ("calibration", r"calibrat|校准"), ("decision-curve", r"\bdca\b|decision"), ("waterfall", r"waterfall|瀑布"),
    ("swimmer", r"swimmer|泳道"), ("ternary", r"ternary|triangle|三元"), ("chord", r"chord|弦"),
    ("oncoprint", r"oncoprint|oncoplot|landscape"), ("gsea-curve", r"gsea"), ("dendrogram", r"dendrogram|tree"),
    ("radial", r"wheel|radial|circular|环形"),
)


def _text_lines(body: str) -> list[tuple[str, bool]]:
    """(line, in_code) pairs after the YAML header."""
    if body.startswith("---"):
        end = body.find("\n---", 3)
        body = body[end + 4:] if end != -1 else body
    result, code = [], False
    for line in body.splitlines():
        if FENCE.match(line):
            code = not code
            result.append((line, True))
            continue
        result.append((line, code))
    return result


def rmd_sections(text: str) -> dict:
    """Prose under the known headings, split into Chinese and English lines."""
    sections = {key: {"zh": [], "en": [], "files": []} for key, _ in SECTION_KEYS}
    current = None
    for line, code in _text_lines(text):
        heading = None if code else HEADING.match(line)
        if heading:
            current = next((key for key, pattern in SECTION_KEYS if pattern.search(heading.group(2))), None)
            continue
        if current is None or code or not line.strip():
            continue
        clean = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", line).strip()
        clean = re.sub(r"\s+", " ", clean.lstrip("-*> ").strip())
        if not clean:
            continue
        bucket = "zh" if CJK.search(clean) else "en"
        sections[current][bucket].append(clean)
        sections[current]["files"].extend(match.group(0) for match in re.finditer(
            r"[\w.\-]+\.(?:%s)\b" % DATA_EXT, clean, re.I))
    return sections


def code_text(text: str) -> str:
    return "\n".join(line for line, code in _text_lines(text) if code and not FENCE.match(line))


def file_calls(code: str) -> tuple[list[str], list[str]]:
    """Literal file names passed to reader / writer calls (in order, unique)."""
    reads, writes = [], []
    for match in CALL_LITERAL.finditer(code):
        function, value = match.group(1), match.group(2).strip()
        if value.startswith(("http://", "https://", "/")) or re.match(r"^[A-Za-z]:[\\/]", value):
            continue
        target = reads if READERS.search(function) else writes if WRITERS.search(function) else None
        if target is not None and value not in target and re.search(r"\.\w{1,6}$", value):
            target.append(value)
    return reads, writes


def packages(script: str, rmd: str) -> dict:
    declared = {"cran": [], "bioc": [], "github": []}
    for kind, values in PKG_VECTOR.findall(script):
        bucket = "github" if kind == "github" else "bioc" if kind == "bioc" else "cran"
        for name in QUOTED.findall(values):
            name = name.split("/")[-1] if bucket == "github" else name
            if name not in declared[bucket]:
                declared[bucket].append(name)
    for repo in GITHUB.findall(script):
        if repo not in declared["github"]:
            declared["github"].append(repo)
    code = code_text(rmd)
    loaded = []
    for name in LIBRARY.findall(code):
        if name not in BASE_PACKAGES and name not in loaded:
            loaded.append(name)
    declared["library"] = loaded
    namespaced = []
    for name in NAMESPACED.findall(code):
        if name not in BASE_PACKAGES and name not in loaded and name not in namespaced:
            namespaced.append(name)
    declared["namespaced"] = namespaced
    return declared


def required_packages(pkgs: dict) -> list[str]:
    """Packages a run needs: what the code loads (library/require/requireNamespace) or calls as `pkg::`.

    Upstream install lists are only hints: some FigureYa install_dependencies.R list colour names or
    data column names ("blueviolet", "phylum") as CRAN packages. A declared package the code never
    touches is not required; if it is an implicit dependency the run reports the exact
    "there is no package called" name as not_run.
    """
    names = []
    for key in ("library", "namespaced"):
        for name in pkgs.get(key, []):
            if name not in BASE_PACKAGES and name not in names:
                names.append(name)
    return names


def declared_only(pkgs: dict) -> list[str]:
    """Declared in the install script but never loaded or `::`-called by the code."""
    used = set(required_packages(pkgs))
    names = []
    for key in ("cran", "bioc", "github"):
        for name in pkgs.get(key, []):
            name = name.split("/")[-1]
            if name not in BASE_PACKAGES and name not in used and name not in names:
                names.append(name)
    return names


def _match_rules(rules, text: str) -> list[str]:
    return [name for name, pattern in rules if re.search(pattern, text, re.I)]


def words(name: str) -> str:
    """Split camelCase / digits / underscores so word-boundary rules see `multipanel ROC`."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])|_", " ", name)


def _short(lines: list[str], limit: int = 280) -> str:
    text = " ".join(line for line in lines if not URL.fullmatch(line) and not line.lower().startswith("from"))
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


class FigureYa:
    """ying-ge/FigureYa：每个目录一个 R Markdown 模块（Rmd + install_dependencies.R + easy_input_*）。"""

    BASE_PATTERNS = ("/*/*.Rmd", "/*/install_dependencies.R", "/gallery_compress/", "/README.md", "/LICENSE*")
    PREFIX = "FigureYa"

    @staticmethod
    def item_patterns(item: str) -> list[str]:
        return [f"/{item}/", f"!/{item}/*.html"]

    @classmethod
    def recipe_id(cls, item: str) -> str:
        """FigureYa59volcanoV2 → figureya-59volcanov2 (lowercase, hyphens; unique across the repo)."""
        rest = item[len(cls.PREFIX):] if item.startswith(cls.PREFIX) else item
        return "figureya-" + re.sub(r"[^a-z0-9]+", "-", rest.lower()).strip("-")

    @staticmethod
    def main_rmd(directory: Path) -> Path | None:
        rmds = sorted(directory.glob("*.Rmd"))
        exact = [path for path in rmds if path.stem == directory.name]
        return (exact or rmds or [None])[0]

    @classmethod
    def parse_item(cls, snapshot: Path, item: str, source_id: str, commit: str, meta: dict) -> dict:
        directory = snapshot / item
        rmd = cls.main_rmd(directory)
        text = rmd.read_text(encoding="utf-8", errors="replace") if rmd else ""
        script_path = directory / "install_dependencies.R"
        script = script_path.read_text(encoding="utf-8", errors="replace") if script_path.is_file() else ""
        sections = rmd_sections(text)
        reads, writes = file_calls(code_text(text))
        inputs, seen = [], set()
        notes = sections["inputs"]["zh"] + sections["inputs"]["en"]
        for name in [*sections["inputs"]["files"], *reads]:
            base = name.replace("\\", "/").split("/")[-1]
            if base in seen or base.lower().startswith("output") or FIGURE_EXT.search(base):
                continue
            seen.add(base)
            note = next((line for line in notes if base in line), "")
            inputs.append({"file": base, "note": note[:200]})
        outputs = [name for name in writes if FIGURE_EXT.search(name) or name.lower().startswith("output")]
        haystack = " ".join([words(item), *sections["requirement"]["zh"], *sections["requirement"]["en"],
                             *sections["scenario"]["zh"], *sections["scenario"]["en"]])
        pkgs = packages(script, text)
        tags = _match_rules(TAG_RULES, haystack)
        # FigureYa names single-cell modules scXxx (scGSVA, scCNV …); "score"/"scatter" must not match.
        if re.search(r"(?<![A-Za-z])sc[A-Z]|\d+sc[A-Z]", item) and "single-cell" not in tags:
            tags.insert(0, "single-cell")
        tags = tags or ["other"]
        keywords = sorted({name for name in pkgs["library"] if name not in ("ggplot2", "dplyr", "tidyr")})
        refs = sorted(set(URL.findall(" ".join(sections["requirement"]["zh"] + sections["requirement"]["en"]))))
        thumb = f"gallery_compress/{item}.webp"
        url = meta.get("url", "").rstrip("/")
        return {
            "id": f"{source_id}:{item}", "source": source_id, "item": item, "commit": commit,
            "title": item, "rmd": f"{item}/{rmd.name}" if rmd else "",
            "requirement": _short(sections["requirement"]["zh"]),
            "requirement_en": _short(sections["requirement"]["en"]),
            "scenario": _short(sections["scenario"]["zh"]), "scenario_en": _short(sections["scenario"]["en"]),
            "inputs": inputs[:12], "outputs": outputs[:20], "packages": pkgs,
            "requires": required_packages(pkgs), "tags": tags[:3], "tags_auto": True,
            "chart_hints": _match_rules(CHART_RULES, words(item.removeprefix(cls.PREFIX)))[:4],
            "keywords": keywords[:12], "refs": refs[:3],
            "thumb_url": (f"{url.replace('github.com', 'raw.githubusercontent.com')}/{commit}/{thumb}"
                          if (snapshot / thumb).is_file() and "github.com" in url else ""),
            "language": "r", "recipe": cls.recipe_id(item),
        }

    @classmethod
    def scan(cls, snapshot: Path, source_id: str, commit: str, meta: dict) -> list[dict]:
        items = [cls.parse_item(snapshot, directory.name, source_id, commit, meta)
                 for directory in sorted(snapshot.iterdir())
                 if directory.is_dir() and directory.name.startswith(cls.PREFIX) and cls.main_rmd(directory)]
        seen = {}
        for item in items:
            if item["recipe"] in seen:
                from .errors import WikiError
                raise WikiError(f"配方 id 冲突: {seen[item['recipe']]} 与 {item['item']} → {item['recipe']}")
            seen[item["recipe"]] = item["item"]
        return items


ADAPTERS = {"figureya": FigureYa}
