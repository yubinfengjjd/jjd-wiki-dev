"""L1 配方（v2，2026-10-27）：整个上游模块原字节入库，在 Wiki 专用环境原样运行并留收据。

- 页面 `recipes/<id>.md`；原字节 `recipes/<id>/source/` + `source.json`（哈希）；收据 `runs/<run_id>.json`。
- 运行在 `config.work_root/runs/<id>/<run_id>/` 的副本里进行：install_dependencies.R 换成只检查不安装的
  桩，knitr 直接 knit（不需要 pandoc）。课题副本用 `run --dir` 原地运行，收据写在副本里。
- 收据只证明“在记录的环境里跑通”，不证明统计或科学有效。
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from .adapters import ADAPTERS, BASE_PACKAGES, declared_only, required_packages
from .config import Config
from .errors import WikiError
from .pages import read_page, write_page

HEADINGS = ("用途", "适用", "不适用", "输入", "怎么用", "输出", "知识关联检查")
RUNNER = Path(__file__).resolve().parents[1] / "assets" / "rmd_knit_runner.R"
RUNNER_NAME = "_rwiki_knit.R"
STUB_MARK = "rwiki 检查桩"
SKIP_COPY = (".html",)
HARNESS = {RUNNER_NAME, "rwiki-knit.md", "rwiki-session.json", "rwiki-stdout.txt", "rwiki-stderr.txt",
           "install_dependencies.R", "install_dependencies.R.rwiki-orig", "rwiki-origin.json", "RWIKI-USE.md"}
MISSING = (re.compile(r"there is no package called \W{0,3}([A-Za-z][A-Za-z0-9.]*)"),
           re.compile(r"rwiki: missing packages: ([^\r\n]+)"))
OUTPUT_LIKE = re.compile(r"\.(pdf|png|svg|tiff?|jpe?g|html|md)$", re.I)
_HASH_CACHE: dict = {}
ABS = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/][^\s'\"<>|]*|(?<![\w.])/(?:Users|home)/[^/\s]+/[^\s'\"]*")
KEEP_RECEIPTS = 10
NOTICES = {
    "CC-BY-NC-SA-4.0": "CC BY-NC-SA 4.0：仅限非商业使用；使用时署名并引用来源文献；改编后的代码须以相同许可共享；"
                       "源码与派生代码不进 Git、不推送公开仓库。",
}


def sha256(path: Path) -> str:
    """File digest, memoised per (path, size, mtime) — one save hashes each recipe tree several times."""
    stat = path.stat()
    key = (str(path.resolve()), stat.st_size, stat.st_mtime_ns)
    digest = _HASH_CACHE.get(key)
    if digest is None:
        hasher = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1 << 20), b""):
                hasher.update(block)
        digest = _HASH_CACHE[key] = hasher.hexdigest()
    return digest


def tree_hashes(directory: Path, skip=()) -> dict:
    return {path.relative_to(directory).as_posix(): sha256(path)
            for path in sorted(directory.rglob("*"))
            if path.is_file() and path.relative_to(directory).as_posix() not in skip
            and ".git" not in path.relative_to(directory).parts}


def license_notice(license: str, fallback: str = "") -> str:
    return NOTICES.get(license, fallback or f"许可证：{license}；使用前核对许可条款。")


def recipe_page(config: Config, recipe_id: str) -> Path:
    return config.wiki_root / "recipes" / f"{recipe_id}.md"


def load_recipe(config: Config, recipe_id: str) -> tuple[Path, dict, str]:
    page = recipe_page(config, recipe_id)
    if not page.is_file():
        raise WikiError(f"配方不存在: {recipe_id}")
    meta, body = read_page(page)
    if meta.get("type") != "recipe":
        raise WikiError(f"不是配方页: {recipe_id}")
    return page, meta, body


# ---------------------------------------------------------------- promote (L0 -> L1)

def _related(config: Config, chart_types: list[str]) -> list[str]:
    from .catalog import readable_pages

    hits = []
    for path, meta in readable_pages(config.wiki_root):
        if meta.get("type") == "template" and meta.get("status") != "archived" \
                and set(meta.get("chart_types") or []) & set(chart_types):
            hits.append(f"[[templates/{meta['id']}|{meta['title']}]]")
    return hits


def _upstream(text: str, label: str) -> str:
    return f"{text}（上游“{label}”）" if text else ""


def recipe_body(config: Config, meta: dict, item: dict, notice: str, curated: dict | None = None) -> str:
    curated = curated or {}
    inputs = "\n".join(f"- `{entry['file']}`：{entry['note'] or '见 Rmd“输入文件”节'}" for entry in item["inputs"]) \
        or "- 见 Rmd“输入文件”节（适配器未识别出文件名）。"
    if curated.get("inputs_note"):
        inputs += f"\n\n{curated['inputs_note']}"
    outputs = "\n".join(f"- `{name}`" for name in item["outputs"]) or "- 见 Rmd（适配器未识别出输出文件名）。"
    related = _related(config, meta.get("chart_types") or [])
    today = datetime.now(timezone.utc).date().isoformat()
    check = (f"{today}：查了同图型模板与方法页。"
             + (f"同图型模板：{' · '.join(related)}；画法与输入是否相同未核对，不建立直连关系。" if related
                else "库内暂无同图型模板。")
             + "L1 配方按整模块原样运行，figure_relations 在升级为 L2 模板/方法时再核对。")
    use = curated.get("use") or _upstream(item["requirement"] or item["requirement_en"], "需求描述") or "待补充"
    fit = curated.get("fit") or _upstream(item["scenario"] or item["scenario_en"], "应用场景") or "待补充"
    unfit = curated.get("unfit") or "待补充"
    runtime = f"\n- 运行提示：{curated['runtime_note']}" if curated.get("runtime_note") else ""
    return (f"# {meta['title']}\n\n> {notice}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n"
            f"## 用途\n\n{use}\n\n"
            f"## 适用\n\n{fit}\n\n"
            f"## 不适用\n\n{unfit}\n\n"
            f"## 输入\n\n{inputs}\n\n"
            "## 怎么用\n\n"
            f"- 原样运行（Wiki 专用环境）：`wiki.py run {meta['id']}`\n"
            f"- 用到课题：`wiki.py use {meta['id']} --project <课题目录>`，按“输入”替换同名文件（列格式保持一致），"
            "参数在 Rmd 的“参数设置”段改；然后 `wiki.py run --dir <副本目录>`。\n"
            f"- 改统计逻辑、阈值含义或分组定义前先问作者。{runtime}\n\n"
            f"## 输出\n\n{outputs}\n\n"
            f"## 知识关联检查\n\n{check}\n\n"
            "## 使用记录\n\n<!-- user:start -->\n<!-- user:end -->\n")


CURATION_KEYS = {"title", "chart_types", "tags", "keywords", "use", "fit", "unfit", "inputs_note",
                 "runtime_note", "inputs_ok", "heavy", "note"}


def promote(config: Config, source_id: str, items: list[str], curation: dict | None = None) -> list[str]:
    """Copy upstream items byte-for-byte into draft recipe pages (one save; all or nothing).

    `curation` maps item → {title, chart_types, tags, keywords, use, fit, unfit, inputs_note, runtime_note}:
    the agent's reading of the Rmd (中文名、图型、受控领域、用途/适用/不适用). Without it the upstream
    “需求描述/应用场景” are used and 不适用 stays 待补充 (the page cannot be confirmed yet).
    """
    from .ingest import ensure_hubs
    from .sources import fetch_source, find_item, load_source, snapshot_dir
    from .store import save

    curation = curation or {}
    for name, value in curation.items():
        unknown = set(value) - CURATION_KEYS if isinstance(value, dict) else {"<not an object>"}
        if unknown:
            raise WikiError(f"curation.{name} 含未知字段: {', '.join(sorted(unknown))}")
    source, _ = load_source(config, source_id)
    adapter = ADAPTERS[source["adapter"]]
    for name in items:
        recipe_id = adapter.recipe_id(name)
        if recipe_page(config, recipe_id).exists() or recipe_page(config, recipe_id).with_suffix("").exists():
            raise WikiError(f"配方已存在: {recipe_id}")
        find_item(config, source_id, name)
    fetch_source(config, source_id, items)
    source, _ = load_source(config, source_id)
    snapshot = snapshot_dir(config, source)
    created, hubs_before = [], set((config.wiki_root / "chart-types").glob("*.md"))
    try:
        for name in items:
            created.append(_promote_one(config, source_id, source, adapter, snapshot, name,
                                        curation.get(name) or {}, ensure_hubs))
        save(config, f"promote {source_id}: {', '.join(created)}"[:300])
    except BaseException:
        for recipe_id in created:
            page = recipe_page(config, recipe_id)
            page.unlink(missing_ok=True)
            shutil.rmtree(page.with_suffix(""), ignore_errors=True)
        for hub in set((config.wiki_root / "chart-types").glob("*.md")) - hubs_before:
            hub.unlink(missing_ok=True)
        raise
    return created


def _promote_one(config, source_id, source, adapter, snapshot, name, curated, ensure_hubs) -> str:
    directory = snapshot / name
    if not directory.is_dir() or not adapter.main_rmd(directory):
        raise WikiError(f"快照里没有完整条目目录: {name}")
    # Re-parse with the full directory present (real input/output files now visible).
    item = adapter.parse_item(snapshot, name, source_id, source["commit"], source)
    recipe_id = adapter.recipe_id(name)
    page = recipe_page(config, recipe_id)
    target = page.with_suffix("")
    from .sources import _git
    files = [path for path in sorted(directory.rglob("*"))
             if path.is_file() and path.suffix.lower() not in SKIP_COPY]
    copied = {path.relative_to(directory).as_posix() for path in files}
    # Upstream files left out (rendered .html reports, not checked out): recorded for provenance.
    upstream = [line.removeprefix(f"{name}/") for line in
                _git(snapshot, "-c", "core.quotePath=false", "ls-tree", "-r", "--name-only", "HEAD", "--",
                     name).splitlines() if line.strip()]
    excluded = sorted(set(upstream) - copied)
    for path in files:
        destination = target / "source" / path.relative_to(directory)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    hashes = tree_hashes(target / "source")
    (target / "source.json").write_text(json.dumps({
        "schema_version": 1, "source": source_id, "item": name, "url": source["url"],
        "commit": source["commit"], "license": source["license"], "files": hashes,
        "excluded": excluded, "copied_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    rmd = adapter.main_rmd(target / "source")
    actual = {Path(name).name for name in hashes}
    keywords = list(dict.fromkeys([*(curated.get("keywords") or []), *item["keywords"]]))
    meta = {
        "type": "recipe", "id": recipe_id, "title": curated.get("title") or name, "status": "draft",
        "source": {"id": source_id, "item": name, "commit": source["commit"], "url": source["url"]},
        "license": source["license"], "cite": source.get("cite", []), "language": item.get("language", "r"),
        "runner": "rmd-knit", "entry": f"source/{rmd.name}",
        "inputs": [entry for entry in item["inputs"] if entry["file"] in actual] or item["inputs"],
        "outputs": item["outputs"], "packages": item["packages"],
        "tags": curated.get("tags") or item["tags"], "keywords": keywords[:16],
        "chart_types": curated.get("chart_types") or item["chart_hints"],
        "summary": (curated.get("use") or item["requirement"] or item["requirement_en"])[:80], "favorite": False,
    }
    ensure_hubs(config, meta)
    write_page(page, meta, recipe_body(config, meta, item,
                                       license_notice(source["license"], source.get("license_notice", "")),
                                       curated))
    return recipe_id


# ---------------------------------------------------------------- receipts

def receipts(target: Path) -> list[dict]:
    result = []
    for path in sorted((target / "runs").glob("*.json")):
        try:
            result.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return result


def current_run(config: Config, page: Path) -> dict | None:
    """Latest receipt whose code hashes equal the current source bytes (as-is scope)."""
    target = page.with_suffix("")
    source = target / "source"
    if not source.is_dir():
        return None
    hashes = tree_hashes(source)
    for receipt in reversed(receipts(target)):
        if receipt.get("code") == hashes:
            return receipt
    return None


def integrity_errors(page: Path) -> list[str]:
    target = page.with_suffix("")
    record_path = target / "source.json"
    if not (target / "source").is_dir():
        return ["source/ 目录缺失（原字节副本）"]
    if not record_path.is_file():
        return ["source.json 缺失"]
    recorded = json.loads(record_path.read_text(encoding="utf-8")).get("files", {})
    current = tree_hashes(target / "source")
    if recorded != current:
        changed = sorted(set(recorded) ^ set(current) | {k for k in recorded if current.get(k) != recorded[k]})
        return [f"source/ 与 source.json 记录的原字节不一致：{'、'.join(changed[:5])}"]
    return []


def recipe_errors(config: Config, page: Path, meta: dict) -> list[str]:
    errors = integrity_errors(page)
    if errors:
        return errors
    if not (page.with_suffix("") / meta.get("entry", "")).is_file():
        return [f"入口文件不存在: {meta.get('entry')}"]
    receipt = current_run(config, page)
    if receipt is None:
        return ["缺少当前原字节的运行收据，请 run"]
    if receipt.get("state") != "pass":
        reason = receipt.get("error") or "、".join(receipt.get("missing_packages") or [])
        return [f"最近运行为 {receipt.get('state')}：{reason[:200]}"]
    return []


# ---------------------------------------------------------------- run

def _sanitize(value, config: Config, extra: dict | None = None):
    """Receipts are committed: replace local absolute paths in every string with labels."""
    pairs = [(config.wiki_root, "<wiki>")]
    if config.work_root:
        pairs.append((config.work_root, "<work_root>"))
    if config.sources_root:
        pairs.append((config.sources_root, "<sources_root>"))
    pairs += [(lib, f"<r_lib{index}>") for index, lib in enumerate(config.r_libs)]
    pairs += [(config.rscript_exe.parent.parent, "<R_HOME>"), (Path.home(), "<home>")]
    pairs += list((extra or {}).items())
    ordered = sorted(pairs, key=lambda pair: -len(str(pair[0])))

    def clean(text: str) -> str:
        for path, label in ordered:
            for form in {str(path), str(path).replace("\\", "/")}:
                text = re.sub(re.escape(form), label, text, flags=re.I)
        return ABS.sub("<abs>", text)

    if isinstance(value, dict):
        return {clean(key): _sanitize(item, config, extra) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item, config, extra) for item in value]
    return clean(value) if isinstance(value, str) else value


def check_stub(names: list[str]) -> str:
    vector = ", ".join(json.dumps(name) for name in names)
    return (f"# {STUB_MARK}：原 install_dependencies.R 不在运行时执行（运行不联网装包）。\n"
            f".rwiki_need <- c({vector})\n"
            ".rwiki_missing <- .rwiki_need[!vapply(.rwiki_need, function(p) nzchar(system.file(package = p)), "
            "logical(1))]\n"
            "if (length(.rwiki_missing)) stop(\"rwiki: missing packages: \", "
            "paste(.rwiki_missing, collapse = \", \"), call. = FALSE)\n")


def _r_env(config: Config) -> dict:
    libs = [str(path) for path in config.r_libs if path.is_dir()]
    env = {**os.environ, "LANGUAGE": "en", "R_LIBS": os.pathsep.join(libs)}
    if config.work_root:
        empty = config.work_root / "empty-r-user-lib"
        empty.mkdir(parents=True, exist_ok=True)
        env["R_LIBS_USER"] = str(empty)
    return env


def _execute(config: Config, command: list[str], cwd: Path, timeout: int) -> tuple[int | None, float]:
    start = time.monotonic()
    with open(cwd / "rwiki-stdout.txt", "wb") as out, open(cwd / "rwiki-stderr.txt", "wb") as err:
        process = subprocess.Popen(command, cwd=cwd, stdout=out, stderr=err, env=_r_env(config),
                                   creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
            else:
                process.kill()
            process.wait()
            code = None
    return code, round(time.monotonic() - start, 1)


def _run_in(config: Config, directory: Path, meta: dict, timeout: int, scope: str,
            original: dict, in_place: bool) -> dict:
    """Prepare harness files in `directory`, knit the entry, and describe what happened."""
    entry = Path(meta["entry"]).name
    script = directory / "install_dependencies.R"
    checks = []
    if script.is_file() and STUB_MARK not in script.read_text(encoding="utf-8", errors="replace"):
        if in_place:
            backup = directory / "install_dependencies.R.rwiki-orig"
            if not backup.exists():
                shutil.copy2(script, backup)
        script.write_text(check_stub(required_packages(meta.get("packages") or {})), encoding="utf-8",
                          newline="\n")
        checks.append("install_dependencies.R 以只检查不安装的桩替代")
    shutil.copyfile(RUNNER, directory / RUNNER_NAME)
    before = tree_hashes(directory)
    command = [str(config.rscript_exe), "--vanilla", RUNNER_NAME, entry, "rwiki-knit.md"]
    started = datetime.now(timezone.utc)
    code, duration = _execute(config, command, directory, timeout)
    stderr = (directory / "rwiki-stderr.txt").read_text(encoding="utf-8", errors="replace")
    stdout = (directory / "rwiki-stdout.txt").read_text(encoding="utf-8", errors="replace")
    session = {}
    if (directory / "rwiki-session.json").is_file():
        try:
            session = json.loads((directory / "rwiki-session.json").read_text(encoding="utf-8"))
        except ValueError:
            session = {}
    after = tree_hashes(directory)
    outputs = {name: digest for name, digest in after.items()
               if name not in HARNESS and before.get(name) != digest}
    missing = []
    for pattern in MISSING:
        for match in pattern.findall(stderr + "\n" + stdout):
            for name in re.split(r",\s*", match.strip()):
                if name and name not in missing:
                    missing.append(name)
    errors = [line.split("rwiki-error:", 1)[1].strip() for line in stderr.splitlines() if "rwiki-error:" in line]
    if code is None:
        state, error = "fail", f"超过 {timeout} 秒未结束，已终止"
    elif code == 0 and session.get("status") == "ok":
        state, error = "pass", ""
    elif missing:
        state, error = "not_run", "缺包: " + ", ".join(missing)
    else:
        tail = "\n".join(stderr.strip().splitlines()[-12:])
        state, error = "fail", (errors[-1] if errors else tail)[:1500]
    expected = meta.get("outputs") or []
    present = [name for name in expected if (directory / name).is_file()]
    checks.append(f"knit 退出码 {code}" if code is not None else "knit 超时")
    if expected:
        checks.append(f"预期输出存在 {len(present)}/{len(expected)}")
    figures = sorted((directory / "rwiki-figure").glob("*.png"), key=lambda path: path.stat().st_mtime) \
        if (directory / "rwiki-figure").is_dir() else []
    return {
        "schema_version": 2, "kind": "run", "id": meta["id"],
        "run_id": started.strftime("%Y%m%dT%H%M%SZ"), "scope": scope, "state": state,
        "runner": "rmd-knit", "command": "Rscript --vanilla " + " ".join(command[2:]),
        "started_at": started.isoformat(timespec="seconds"), "duration_s": duration, "exit_code": code,
        "environment": {"r_version": session.get("r_version", ""),
                        "lib_paths": [f"<r_lib{index}>" for index, path in enumerate(config.r_libs)
                                      if path.is_dir()] + ["<R_HOME>/library"],
                        "packages": session.get("packages", {})},
        "code": original, "outputs": outputs, "expected_outputs": expected,
        "missing_outputs": [name for name in expected if name not in present],
        "figures": [path.relative_to(directory).as_posix() for path in figures],
        "missing_packages": missing, "error": error, "checks": checks,
        "runner_sha256": sha256(RUNNER),
        "scope_note": "只证明在记录的环境里跑通；不证明统计或科学有效",
    }


# One line: on Windows `Rscript -e` drops everything after an embedded newline.
PDF_PREVIEW_R = (
    "args <- commandArgs(TRUE); "
    "if (!requireNamespace('pdftools', quietly = TRUE)) stop('rwiki: missing packages: pdftools', call. = FALSE); "
    "invisible(pdftools::pdf_convert(args[1], format = 'png', pages = 1, dpi = 150, filenames = args[2],"
    " verbose = FALSE))")


def pdf_preview(config: Config, pdf: Path, out: Path, timeout: int = 120) -> str:
    """Render page 1 of `pdf` to `out` with pdftools in the Wiki R env; '' on success, else the reason."""
    out.unlink(missing_ok=True)
    try:
        done = subprocess.run([str(config.rscript_exe), "--vanilla", "-e", PDF_PREVIEW_R, str(pdf), str(out)],
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              env=_r_env(config), timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        return str(error)[:300]
    if done.returncode == 0 and out.is_file() and out.stat().st_size > 0:
        return ""
    return (done.stderr.strip().splitlines() or [f"exit {done.returncode}"])[-1][:300]


def _pdf_fallback(config: Config, work: Path, receipt: dict) -> tuple[Path | None, dict | None]:
    """Upstream modules that only call pdf(): preview page 1 of the first declared (else new) PDF output."""
    produced = [name for name in receipt["outputs"] if name.lower().endswith(".pdf")]
    declared = [name for name in receipt["expected_outputs"] if name in produced]
    for name in [*declared, *sorted(set(produced) - set(declared))]:
        out = work / "rwiki-figure" / "_rwiki_pdf_preview.png"
        out.parent.mkdir(exist_ok=True)
        reason = pdf_preview(config, work / name, out)
        if not reason:
            return out, {"from": name, "page": 1, "kind": "pdf"}
        receipt["checks"].append(f"{name} 转预览图失败：{reason}")
    return None, None


def run_recipe(config: Config, recipe_id: str, timeout: int = 1200) -> dict:
    page, meta, _ = load_recipe(config, recipe_id)
    errors = integrity_errors(page)
    if errors:
        raise WikiError("；".join(errors))
    if config.work_root is None:
        raise WikiError("配置缺少 work_root（运行副本目录，不在 Wiki 内）")
    target = page.with_suffix("")
    original = tree_hashes(target / "source")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    work = config.work_root / "runs" / recipe_id / stamp
    shutil.copytree(target / "source", work)
    receipt = _run_in(config, work, meta, timeout, "as-is", original, in_place=False)
    picture = None
    if receipt["state"] == "pass":
        if receipt["figures"]:
            picture = work / receipt["figures"][-1]
            receipt["preview"] = {"from": receipt["figures"][-1], "kind": "png"}
        else:
            picture, receipt["preview"] = _pdf_fallback(config, work, receipt)
    receipt["workdir"] = f"<work_root>/runs/{recipe_id}/{stamp}"
    receipt = _sanitize(receipt, config, {work: "<workdir>"})
    (target / "runs").mkdir(exist_ok=True)
    (target / "runs" / f"{receipt['run_id']}.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for old in sorted((target / "runs").glob("*.json"))[:-KEEP_RECEIPTS]:
        old.unlink()
    if picture is not None:
        shutil.copyfile(picture, target / "preview.png")
    return receipt


def run_recipes(config: Config, recipe_ids: list[str], timeout: int = 1200, jobs: int = 1) -> list[dict]:
    from .store import save

    for recipe_id in recipe_ids:
        load_recipe(config, recipe_id)
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        results = list(pool.map(lambda rid: _safe_run(config, rid, timeout), recipe_ids))
    summary = ", ".join(f"{item['id']}={item['state']}" for item in results)
    save(config, f"run {summary}"[:300])
    return results


def _safe_run(config: Config, recipe_id: str, timeout: int) -> dict:
    try:
        return run_recipe(config, recipe_id, timeout)
    except WikiError as error:
        return {"id": recipe_id, "state": "error", "error": str(error)}


def run_dir(config: Config, directory: Path, timeout: int = 1200) -> dict:
    """Run a project copy made by `use` in place; the receipt stays in the copy."""
    directory = directory.resolve()
    origin_path = directory / "rwiki-origin.json"
    if not origin_path.is_file():
        raise WikiError(f"{directory} 不是 use 生成的副本（缺 rwiki-origin.json）")
    origin = json.loads(origin_path.read_text(encoding="utf-8"))
    meta = {"id": origin["id"], "entry": origin["entry"], "packages": origin.get("packages", {}),
            "outputs": origin.get("outputs", [])}
    current = {name: digest for name, digest in tree_hashes(directory).items()
               if name not in HARNESS and not name.startswith(("rwiki-runs/", "rwiki-figure/"))}
    # Regenerated figures/reports are outputs, not new data: compare inputs and code only.
    outputs = set(origin.get("outputs") or [])
    changed = sorted(name for name, digest in origin["files"].items()
                     if name in current and current[name] != digest
                     and name not in outputs and not OUTPUT_LIKE.search(name))
    scope = "new-data" if changed else "other-dir"
    receipt = _run_in(config, directory, meta, timeout, scope, current, in_place=True)
    receipt["changed_inputs"] = changed
    receipt["workdir"] = "<copy>"
    receipt = _sanitize(receipt, config, {directory: "<copy>"})
    (directory / "rwiki-runs").mkdir(exist_ok=True)
    (directory / "rwiki-runs" / f"{receipt['run_id']}.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return receipt


def restore_source(config: Config, recipe_id: str) -> dict:
    """Bring back git-ignored source/ bytes from the snapshot at the recorded commit; verify hashes."""
    from .sources import fetch_source, load_source, snapshot_dir

    page, meta, _ = load_recipe(config, recipe_id)
    target = page.with_suffix("")
    record = json.loads((target / "source.json").read_text(encoding="utf-8"))
    source, _ = load_source(config, record["source"])
    if source.get("commit") != record["commit"]:
        raise WikiError(f"来源快照 commit 与配方记录不同（{str(source.get('commit'))[:12]} ≠ {record['commit'][:12]}）")
    fetch_source(config, record["source"], [record["item"]])
    staging = target / "source.rwiki-restore"
    if staging.exists():
        shutil.rmtree(staging)
    directory = snapshot_dir(config, source) / record["item"]
    shutil.copytree(directory, staging, ignore=shutil.ignore_patterns(*(f"*{ext}" for ext in SKIP_COPY), ".git"))
    if tree_hashes(staging) != record["files"]:
        shutil.rmtree(staging)
        raise WikiError("快照字节与 source.json 记录不一致，未替换 source/")
    if (target / "source").exists():
        shutil.rmtree(target / "source")
    staging.rename(target / "source")
    return {"id": recipe_id, "restored": len(record["files"]), "commit": record["commit"]}


# ---------------------------------------------------------------- dependencies

def _rscript(config: Config, code: str, timeout: int, log: Path | None = None) -> str:
    if config.work_root is None:
        raise WikiError("配置缺少 work_root")
    config.work_root.mkdir(parents=True, exist_ok=True)
    script = config.work_root / f"rwiki-{os.getpid()}-{time.time_ns()}.R"
    script.write_text(code, encoding="utf-8", newline="\n")
    try:
        result = subprocess.run([str(config.rscript_exe), "--vanilla", str(script)], capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=timeout,
                                env=_r_env(config))
    finally:
        script.unlink(missing_ok=True)
    if log is not None:
        log.write_text(result.stdout + "\n--- stderr ---\n" + result.stderr, encoding="utf-8")
    if result.returncode:
        raise WikiError(f"Rscript 失败: {result.stderr.strip()[-800:]}")
    return result.stdout


def missing_packages(config: Config, names: list[str]) -> list[str]:
    if not names:
        return []
    vector = ", ".join(json.dumps(name) for name in names)
    out = _rscript(config, f"p <- c({vector})\n"
                           "m <- p[!vapply(p, function(x) nzchar(system.file(package = x)), logical(1))]\n"
                           "cat('RWIKI-MISSING:', paste(m, collapse = ','), '\\n', sep = '')\n", 300)
    line = next((line for line in out.splitlines() if line.startswith("RWIKI-MISSING:")), "RWIKI-MISSING:")
    return [name for name in line.split(":", 1)[1].strip().split(",") if name]


def package_plan(config: Config, ids: list[str]) -> dict:
    """{id: packages dict} for recipe ids or `<source>:<item>` catalog ids."""
    from .sources import find_item

    plan = {}
    for entry in ids:
        if ":" in entry:
            source_id, item = entry.split(":", 1)
            plan[entry] = find_item(config, source_id, item)["packages"]
        else:
            plan[entry] = load_recipe(config, entry)[1].get("packages") or {}
    return plan


def deps(config: Config, ids: list[str], install: bool = False, github: bool = False) -> dict:
    plan = package_plan(config, ids)
    needed = {entry: required_packages(packages) for entry, packages in plan.items()}
    union = sorted({name for names in needed.values() for name in names})
    missing = set(missing_packages(config, union))
    report = {"r_libs": [f"<r_lib{index}>" for index, _ in enumerate(config.r_libs)],
              "missing": {entry: [name for name in names if name in missing] for entry, names in needed.items()},
              "union_missing": sorted(missing)}
    ignored = {entry: names for entry, packages in plan.items() if (names := declared_only(packages))}
    if ignored:
        report["declared_not_used"] = ignored
    repos = sorted({repo for packages in plan.values() for repo in packages.get("github", [])
                    if "/" in repo and repo.split("/")[-1] in missing})
    report["github_repos"] = repos
    if not install or not missing:
        return report
    if not config.r_libs:
        raise WikiError("配置缺少 r_libs（Wiki 专用 R 库）；不向课题环境或系统库安装")
    target = config.r_libs[0]
    target.mkdir(parents=True, exist_ok=True)
    github_names = {repo.split("/")[-1] for repo in repos}
    regular = sorted(missing - github_names)
    lib = json.dumps(target.as_posix())
    code = [f"options(repos = c(CRAN = {json.dumps(config.cran_mirror)}))",
            "if (!requireNamespace('BiocManager', quietly = TRUE)) "
            f"install.packages('BiocManager', lib = {lib})"]
    if regular:
        vector = ", ".join(json.dumps(name) for name in regular)
        code.append(f"BiocManager::install(c({vector}), lib = {lib}, update = FALSE, ask = FALSE)")
    if github and repos:
        vector = ", ".join(json.dumps(repo) for repo in repos)
        code.append(f"for (r in c({vector})) tryCatch(remotes::install_github(r, lib = {lib}, upgrade = 'never'),"
                    " error = function(e) message('rwiki: github install failed: ', r, ': ', conditionMessage(e)))")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log = config.work_root / f"deps-install-{stamp}.log"
    _rscript(config, "\n".join(code) + "\n", 6 * 3600, log)
    still = set(missing_packages(config, union))
    report.update(installed=sorted(missing - still), still_missing=sorted(still),
                  log=f"<work_root>/{log.name}")
    return report


# ---------------------------------------------------------------- facts

def recipe_facts(config: Config, meta: dict) -> str:
    page = recipe_page(config, meta["id"])
    target = page.with_suffix("")
    source = meta.get("source") or {}
    source_page = config.wiki_root / "sources" / f"{source.get('id')}.md"
    origin = (f"[[sources/{source['id']}|{read_page(source_page)[0]['title']}]]" if source_page.is_file()
              else str(source.get("id")))
    packages = meta.get("packages") or {}
    deps_line = "；".join(f"{label} {', '.join(packages.get(key) or [])}"
                         for key, label in (("cran", "CRAN"), ("bioc", "Bioconductor"), ("github", "GitHub"))
                         if packages.get(key)) or "未声明（见 Rmd library 调用）"
    receipt = current_run(config, page)
    if receipt:
        run = (f"{receipt['state']}（{receipt['scope']}，{receipt['started_at'][:16].replace('T', ' ')} UTC，"
               f"{receipt['duration_s']} 秒）")
        if receipt.get("missing_packages"):
            run += "；缺包 " + ", ".join(receipt["missing_packages"])
    else:
        run = "尚无当前原字节的运行收据"
    derived = []
    for path in sorted((config.wiki_root / "templates").glob("*.md")):
        try:
            other = read_page(path)[0]
        except WikiError:
            continue
        if f"recipes/{meta['id']}" in (other.get("sources") or []):
            derived.append(f"[[templates/{other['id']}|{other['title']}]]（{other['status']}）")
    lines = [f"\n- 来源：{origin} · 条目 `{source.get('item')}` · commit `{str(source.get('commit'))[:12]}`",
             f"- 许可证：{meta.get('license')}；引用：{'；'.join(meta.get('cite') or []) or '无'}",
             f"- 语言 / 运行：{meta.get('language')} · knitr 原样运行（入口 `{meta.get('entry')}`）",
             f"- 依赖：{deps_line}",
             f"- 最近运行：{run}",
             f"- 派生模板（L2）：{' · '.join(derived) or '暂无'}"]
    if (target / "preview.png").is_file():
        source = (receipt or {}).get("preview") or {}
        how = (f"取自 `{source['from']}` 第 1 页" if source.get("kind") == "pdf"
               else "自动截取最后一张图")
        lines.append(f"- 运行预览（最近一次通过的原样运行，{how}）：\n\n![[recipes/{meta['id']}/preview.png]]")
    return "\n".join(lines) + "\n"
