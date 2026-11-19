"""Bio-Template Studio backend engine: playbooks DAG, data sniffing, code rendering, dispatch, and local run."""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import Config, read_json
from .errors import WikiError
from .esquisse_codegen import (
    generate_ggplot2_code,
    generate_python_viz_code,
    load_ggsci_palettes,
    resolve_palette,
    sniff_csv_columns,
)
from .pages import read_page
from .template_renderer import build_parameter_header, render_template_code
from .template_spec import load_unified_spec

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".svg", ".pdf"}


def _studio_outputs_root(config: Config) -> Path:
    base = config.work_root or (Path(tempfile.gettempdir()) / "rwiki-studio-work")
    out = Path(base).resolve() / "studio_outputs"
    out.mkdir(parents=True, exist_ok=True)
    return out


def studio_output_file(config: Config, run_id: str, filename: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        raise WikiError("无效的试跑 ID")
    if Path(filename).is_absolute() or ".." in Path(filename).parts:
        raise WikiError("非法的输出文件路径")
    base = (_studio_outputs_root(config) / run_id).resolve()
    target = (base / filename).resolve()
    if not target.is_relative_to(base) or not target.is_file():
        raise WikiError("输出预览文件不存在")
    return target


# ------------------------------------------------------------------ playbooks & DAG

def _resolve_typed_ref(raw: str, default_kind: str = "template") -> tuple[str, str, str]:
    """Resolve a typed or bare wiki ref like 'templates/foo', 'methods/bar', 'recipes/baz' without double-prefixing."""
    text = str(raw or "").strip().removesuffix(".md")
    prefix_map = {
        "templates/": ("template", "templates"),
        "methods/": ("method", "methods"),
        "recipes/": ("recipe", "recipes"),
        "scenarios/": ("scenario", "scenarios"),
        "interfaces/": ("interface", "interfaces"),
    }
    for prefix, (kind, folder) in prefix_map.items():
        if text.startswith(prefix):
            slug = text[len(prefix):]
            return slug, kind, f"{folder}/{slug}.md"
    folder_map = {
        "template": "templates",
        "method": "methods",
        "recipe": "recipes",
        "scenario": "scenarios",
        "interface": "interfaces",
    }
    folder = folder_map.get(default_kind, "templates")
    return text, default_kind, f"{folder}/{text}.md"


def _synthesize_steps(meta: dict) -> list[dict[str, Any]]:
    raw_steps = meta.get("steps")
    if isinstance(raw_steps, list) and raw_steps:
        steps = []
        for idx, item in enumerate(raw_steps):
            if not isinstance(item, dict):
                continue
            step_id = str(item.get("id") or item.get("method_id") or f"step-{idx + 1}")
            has_explicit_next = ("next" in item) or ("next_steps" in item)
            raw_next = item.get("next") if "next" in item else item.get("next_steps")
            steps.append({
                "id": step_id,
                "title": str(item.get("title") or item.get("direction") or step_id),
                "method_id": str(item.get("method_id") or item.get("id") or ""),
                "description": str(item.get("description") or item.get("when") or ""),
                "templates": list(item.get("templates") or item.get("viz_templates") or []),
                "interface": str(item.get("interface") or item.get("intermediate_interface") or ""),
                "inputs": list(item.get("inputs") or []),
                "outputs": list(item.get("outputs") or []),
                "requires": list(item.get("requires") or []),
                "subtree": str(item.get("subtree") or ""),
                "next": list(raw_next or []),
                "_has_explicit_next": has_explicit_next,
            })
        return steps

    steps = []
    for idx, pick in enumerate(meta.get("picks") or []):
        pid = pick.get("id") if isinstance(pick, dict) else str(pick)
        note = pick.get("note", "") if isinstance(pick, dict) else ""
        clean_id = str(pid).split("/", 1)[-1].removesuffix(".md")
        steps.append({
            "id": clean_id,
            "title": clean_id,
            "method_id": clean_id,
            "description": note,
            "templates": [],
            "interface": "",
            "inputs": [],
            "outputs": [],
            "requires": [],
            "subtree": "",
            "next": [],
            "_has_explicit_next": False,
        })
    return steps


def get_playbooks(config: Config) -> dict[str, Any]:
    """Return all playbook/scenario pages plus a synthesized stepwise transition DAG."""
    from .catalog import readable_pages
    from .facts import declarations, table_interfaces

    root = config.wiki_root
    scenarios: list[dict[str, Any]] = []
    playbooks: list[dict[str, Any]] = []

    for path, meta in readable_pages(root):
        if meta.get("type") != "scenario" or meta.get("status") == "archived":
            continue
        _, body = read_page(path)
        item = {
            "id": meta.get("id", path.stem),
            "title": meta.get("title", path.stem),
            "path": path.relative_to(root).as_posix(),
            "summary": meta.get("summary", ""),
            "tags": list(meta.get("tags") or []),
            "picks": list(meta.get("picks") or []),
            "steps": _synthesize_steps(meta),
        }
        scenarios.append(item)
        if "playbook" in item["id"].lower() or meta.get("steps"):
            playbooks.append(item)

    if not playbooks:
        playbooks = list(scenarios)

    playbooks.sort(key=lambda x: (0 if "playbook" in x["id"] else 1, x["id"]))
    scenarios.sort(key=lambda x: x["id"])

    nodes_map: dict[str, dict[str, Any]] = {}
    edges_set: set[tuple[str, str, str]] = set()

    def add_node(nid: str, label: str, kind: str, page_path: str = "") -> None:
        if nid and nid not in nodes_map:
            nodes_map[nid] = {"id": nid, "label": label or nid, "kind": kind, "path": page_path}

    for pb in playbooks:
        pb_steps = pb.get("steps") or []
        for idx, st in enumerate(pb_steps):
            sid = st["id"]
            has_explicit_next = bool(st.pop("_has_explicit_next", False))
            add_node(sid, st["title"], "step", f"methods/{st['method_id']}.md" if st.get("method_id") else "")
            if st.get("interface"):
                add_node(st["interface"], st["interface"], "interface", f"interfaces/{st['interface']}.md")
                edges_set.add((sid, st["interface"], "produces"))
            for raw_ref in st.get("templates") or []:
                ref_id, ref_kind, ref_path = _resolve_typed_ref(raw_ref, default_kind="template")
                if not ref_id:
                    continue
                add_node(ref_id, ref_id, ref_kind, ref_path)
                if ref_kind == "method":
                    edges_set.add((sid, ref_id, "uses_method"))
                else:
                    src = st["interface"] or sid
                    edges_set.add((src, ref_id, "visualizes"))
            if st.get("subtree"):
                sub_id, sub_kind, sub_path = _resolve_typed_ref(st["subtree"], default_kind="scenario")
                if sub_id:
                    add_node(sub_id, sub_id, sub_kind, sub_path)
                    edges_set.add((sid, sub_id, "subtree"))
            if st.get("next"):
                for nxt in st["next"]:
                    edges_set.add((sid, nxt, "next"))
            elif not has_explicit_next and idx + 1 < len(pb_steps):
                edges_set.add((sid, pb_steps[idx + 1]["id"], "next"))
    for sc in scenarios:
        for st in sc.get("steps") or []:
            st.pop("_has_explicit_next", None)

    for mid, (mm, _) in declarations(root, "methods").items():
        if mm.get("status") == "archived":
            continue
        add_node(mid, mm.get("title", mid), "method", f"methods/{mid}.md")
        for ns in mm.get("next_steps") or []:
            if not isinstance(ns, dict):
                continue
            iface = str(ns.get("intermediate_interface") or "")
            label = str(ns.get("direction") or "next")
            if iface:
                add_node(iface, iface, "interface", f"interfaces/{iface}.md")
                edges_set.add((mid, iface, label))
            for tid in ns.get("viz_templates") or []:
                ref_id, ref_kind, ref_path = _resolve_typed_ref(str(tid), default_kind="template")
                if ref_id:
                    add_node(ref_id, ref_id, ref_kind, ref_path)
                    edges_set.add((iface or mid, ref_id, label))
            for amid in ns.get("analysis_templates") or []:
                ref_id, ref_kind, ref_path = _resolve_typed_ref(str(amid), default_kind="method")
                if ref_id:
                    add_node(ref_id, ref_id, ref_kind, ref_path)
                    edges_set.add((mid, ref_id, label))

    for tid, (tm, spec) in declarations(root, "templates").items():
        if tm.get("status") == "archived":
            continue
        for iface in table_interfaces(spec):
            if iface in nodes_map:
                add_node(tid, tm.get("title", tid), "template", f"templates/{tid}.md")
                edges_set.add((iface, tid, "feeds"))

    return {
        "playbooks": playbooks,
        "scenarios": scenarios,
        "graph": {
            "nodes": list(nodes_map.values()),
            "edges": [{"source": s, "target": t, "label": lbl} for s, t, lbl in sorted(edges_set)],
        },
    }


# ------------------------------------------------------------------ data sniffer

def sniff_data(config: Config, path_str: str) -> dict[str, Any]:
    """Inspect a local CSV/TSV/TXT/RDS file and return column metadata + preview rows."""
    raw = str(path_str or "").strip()
    if not raw:
        raise WikiError("请提供本地数据文件路径")
    path = Path(raw).expanduser()
    if not path.is_file():
        raise WikiError(f"数据文件不存在: {path}")

    suffix = path.suffix.lower()
    if suffix in (".rds", ".rdata", ".rda"):
        size_mb = round(path.stat().st_size / (1024 * 1024), 3)
        if suffix == ".rds" and config.rscript_exe and config.rscript_exe.is_file():
            r_expr = (
                "obj <- readRDS(Sys.getenv('RWIKI_SNIFF_RDS')); "
                "if (inherits(obj, 'Seurat')) { "
                "  md <- obj@meta.data; "
                "  cat(jsonlite::toJSON(list(kind='Seurat', cols=colnames(md), nrow=ncol(obj)), auto_unbox=TRUE)); "
                "} else if (is.data.frame(obj)) { "
                "  cat(jsonlite::toJSON(list(kind='data.frame', cols=colnames(obj), nrow=nrow(obj)), auto_unbox=TRUE)); "
                "} else { "
                "  cat(jsonlite::toJSON(list(kind=class(obj)[1], cols=character(0), nrow=0), auto_unbox=TRUE)); "
                "}"
            )
            env = {**os.environ, "RWIKI_SNIFF_RDS": str(path)}
            if config.r_libs:
                env["R_LIBS_USER"] = os.pathsep.join(str(p) for p in config.r_libs)
            try:
                res = subprocess.run(
                    [str(config.rscript_exe), "--vanilla", "-e", r_expr],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                    timeout=8, env=env,
                )
                if res.returncode == 0 and res.stdout.strip():
                    info = json.loads(res.stdout.strip().splitlines()[-1])
                    cols = [{"name": c, "type": "unknown", "samples": []} for c in (info.get("cols") or [])]
                    return {
                        "path": str(path),
                        "columns": cols,
                        "row_count_estimate": int(info.get("nrow") or 0),
                        "preview_rows": [],
                        "note": f"RDS 对象类型：{info.get('kind', 'R object')}（{size_mb} MB）",
                    }
            except (OSError, subprocess.TimeoutExpired, ValueError):
                pass
        return {
            "path": str(path),
            "columns": [
                {"name": "rds_object", "type": "rds", "samples": [f"{path.name} ({size_mb} MB)"]},
            ],
            "row_count_estimate": 0,
            "preview_rows": [],
            "note": f"R 二进制数据文件（{size_mb} MB）；可直接传入 RWIKI_DATA_FILE 在 R 脚本中 readRDS()。",
        }

    try:
        return sniff_csv_columns(path)
    except (OSError, UnicodeDecodeError) as exc:
        raise WikiError(f"读取数据表头失败: {exc}") from exc


def _studio_uploads_root(config: Config) -> Path:
    base = config.work_root or (Path(tempfile.gettempdir()) / "rwiki-studio-work")
    out = Path(base).resolve() / "studio_uploads"
    out.mkdir(parents=True, exist_ok=True)
    return out


def upload_studio_data(
    config: Config,
    *,
    filename: str,
    content_base64: str = "",
    content_text: str = "",
) -> dict[str, Any]:
    """Persist an uploaded CSV/TSV/TXT/RDS table into studio_uploads and sniff its schema."""
    raw_name = Path(str(filename or "upload.csv")).name
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", raw_name).strip("._") or "upload.csv"
    if len(safe_name) > 120:
        safe_name = safe_name[-120:]
    dest = _studio_uploads_root(config) / f"{uuid.uuid4().hex[:8]}_{safe_name}"
    if content_base64:
        try:
            payload = base64.b64decode(content_base64, validate=False)
        except (ValueError, TypeError) as exc:
            raise WikiError(f"上传文件内容解码失败: {exc}") from exc
        if len(payload) > 50 * 1024 * 1024:
            raise WikiError("上传文件超过 50 MB 限制，请改用本地绝对路径嗅探")
        dest.write_bytes(payload)
    elif content_text:
        dest.write_text(content_text, encoding="utf-8", newline="\n")
    else:
        raise WikiError("上传文件内容为空")

    sniffed = sniff_data(config, str(dest))
    return {
        "ok": True,
        "filename": safe_name,
        "path": str(dest),
        "sniff": sniffed,
    }


def _auto_bind_columns(spec: dict[str, Any], sniffed: dict[str, Any]) -> dict[str, str]:
    col_names = [str(c.get("name", "")) for c in (sniffed.get("columns") or []) if c.get("name")]
    if not col_names:
        return {}
    suggested: dict[str, str] = {}
    for tdef in (spec.get("tables") or {}).values():
        cols = tdef.get("columns") or {}
        for expected in cols:
            if expected in suggested:
                continue
            exact = next((c for c in col_names if c == expected), None)
            icase = exact or next((c for c in col_names if c.lower() == expected.lower()), None)
            if icase:
                suggested[expected] = icase
    return suggested


def load_example_data(config: Config, entry_id: str) -> dict[str, Any]:
    """Locate built-in example/source tables for a template/recipe/method and sniff them."""
    spec = load_unified_spec(config, entry_id)
    asset_dir = Path(spec["asset_dir"])
    data_exts = {".csv", ".tsv", ".txt", ".rds"}
    candidates: list[Path] = []
    for folder in ("example", "source"):
        sub = asset_dir / folder
        if sub.is_dir():
            for p in sorted(sub.rglob("*")):
                if p.is_file() and p.suffix.lower() in data_exts:
                    candidates.append(p)
    if not candidates:
        raise WikiError(f"条目 {entry_id} 暂未附带内置示例数据文件（可手动选择本地文件路径或拖拽上传 CSV/TSV）")

    files_out: list[dict[str, Any]] = []
    for p in candidates[:8]:
        try:
            sniffed = sniff_data(config, str(p))
        except WikiError:
            continue
        files_out.append({
            "name": p.name,
            "path": str(p),
            "sniff": sniffed,
        })
    if not files_out:
        raise WikiError(f"条目 {entry_id} 的示例文件无法解析表头")

    primary = files_out[0]
    suggested = _auto_bind_columns(spec, primary["sniff"])
    return {
        "ok": True,
        "id": spec["id"],
        "requested_id": entry_id,
        "primary_file": primary["path"],
        "files": files_out,
        "sniff": primary["sniff"],
        "suggested_bindings": suggested,
    }


# ------------------------------------------------------------------ code rendering

def _load_source_script(spec: dict[str, Any], data_file: str, bindings: dict[str, str], params: dict[str, Any]) -> str:
    asset_dir = Path(spec["asset_dir"])
    entry_rel = spec.get("entry") or ""
    if spec.get("kind") == "template" and spec.get("language") == "Python" and spec.get("panel"):
        panel_path = asset_dir / str(spec["panel"])
        if panel_path.is_file():
            return panel_path.read_text(encoding="utf-8", errors="replace")
    if entry_rel:
        candidate = asset_dir / entry_rel
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8", errors="replace")

    if spec.get("language") == "Python":
        return generate_python_viz_code(
            mapping=bindings,
            params=params,
            palette=str(params.get("palette") or "NPG"),
            data_file=data_file or None,
            output_file="output_preview.png",
        )
    return generate_ggplot2_code(
        mapping=bindings,
        palette=str(params.get("palette") or "NPG"),
        labs={"title": str(params.get("title") or spec.get("title") or "")},
        data_file=data_file or None,
        output_file="output_preview.png",
        width=float(params.get("width") or 8.0),
        height=float(params.get("height") or 6.0),
    )


def _wrap_rmd_driver(rmd_rel: str, rmd_text: str, header: str) -> str:
    """For Tier 2 .Rmd recipes, keep full Rmd visible as comments/source or knit driver."""
    preview_lines = "\n".join(f"# {line}" for line in rmd_text.splitlines()[:40])
    return (
        header
        + f'cat("Running Tier 2 Rmd recipe: {rmd_rel}\\n")\n'
        + f'if (file.exists({json.dumps(rmd_rel)})) {{\n'
        + f'  knitr::knit({json.dumps(rmd_rel)}, output = "rwiki-knit.md")\n'
        + f'}} else if (file.exists({json.dumps(Path(rmd_rel).name)})) {{\n'
        + f'  knitr::knit({json.dumps(Path(rmd_rel).name)}, output = "rwiki-knit.md")\n'
        + "}\n\n"
        + "# --- Original Rmd Preview (first 40 lines) ---\n"
        + preview_lines
        + "\n"
    )


def _build_bindings_json(spec: dict[str, Any], data_file: str, bindings: dict[str, str]) -> dict[str, Any]:
    tables_out: dict[str, Any] = {}
    for tname, tdef in (spec.get("tables") or {}).items():
        cols = tdef.get("columns") or {}
        mapped = {col: bindings.get(col, col) for col in cols}
        tables_out[tname] = {
            "file": data_file or tdef.get("filename") or (f"{tdef['interface']}.csv" if tdef.get("interface") else f"{tname}.csv"),
            "columns": mapped,
        }
    return {
        "id": spec["id"],
        "data_file": data_file,
        "tables": tables_out,
        "columns": dict(bindings),
    }


def render_studio_code(
    config: Config,
    *,
    entry_id: str,
    project_dir: str = "",
    data_file: str = "",
    bindings: dict[str, str] | None = None,
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    spec = load_unified_spec(config, entry_id)
    bindings_dict = {str(k): str(v) for k, v in (bindings or {}).items() if v is not None}
    params_dict = dict(parameters or {})
    language = spec["language"]

    source_text = _load_source_script(spec, data_file, bindings_dict, params_dict)
    is_rmd = str(spec.get("entry") or "").lower().endswith((".rmd", ".qmd"))

    palettes_db = load_ggsci_palettes()
    palette_entry = resolve_palette(str(params_dict.get("palette") or "NPG"), palettes_db)
    palette_colors = list(palette_entry.get("colors", []))

    if is_rmd:
        header = build_parameter_header(
            "R",
            data_file=data_file,
            bindings=bindings_dict,
            parameters=params_dict,
            palette_colors=palette_colors,
        )
        code = _wrap_rmd_driver(str(spec.get("entry") or ""), source_text, header)
    else:
        rendered = render_template_code(
            source_text,
            language=language,
            spec=spec,
            parameters=params_dict,
            bindings=bindings_dict,
            data_file=data_file,
            project_dir=project_dir,
            template_root=Path(spec["asset_dir"]),
            inject_header=True,
        )
        code = rendered["code"]
        header = build_parameter_header(
            language,
            data_file=data_file,
            bindings=bindings_dict,
            parameters=rendered["parameters"],
            palette_colors=palette_colors,
        )

    bindings_json = _build_bindings_json(spec, data_file, bindings_dict)
    return {
        "id": spec["id"],
        "requested_id": entry_id,
        "code": code,
        "language": language,
        "bindings_json": bindings_json,
        "spec": spec,
        "parameter_header": header,
    }


# ------------------------------------------------------------------ dispatch & local run

def _validate_project_dir(config: Config, project_dir: str) -> Path:
    raw = str(project_dir or "").strip()
    if not raw:
        raise WikiError("请指定目标课题目录 (project_dir)")
    path = Path(raw).expanduser().resolve()
    wiki_resolved = config.wiki_root.resolve()
    if path == wiki_resolved or path.is_relative_to(wiki_resolved):
        raise WikiError("课题目录不能在知识库内；课题数据与成图留在课题目录")
    if not path.is_dir():
        raise WikiError(f"课题目录不存在: {path}")
    return path


def _copy_minimal_assets(spec: dict[str, Any], dest: Path) -> list[str]:
    asset_dir = Path(spec["asset_dir"])
    written: list[str] = []
    dest.mkdir(parents=True, exist_ok=True)
    for folder in ("code", "example", "repair", "source"):
        src = asset_dir / folder
        if src.is_dir():
            dst = dest / folder
            shutil.copytree(
                src, dst, dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".git"),
            )
            for p in sorted(dst.rglob("*")):
                if p.is_file():
                    written.append(p.relative_to(dest).as_posix())
    for filename in ("spec.json", "runtime.json"):
        src_file = asset_dir / filename
        if src_file.is_file():
            shutil.copyfile(src_file, dest / filename)
            written.append(filename)
    return written


def dispatch_studio(
    config: Config,
    *,
    entry_id: str,
    project_dir: str,
    data_file: str = "",
    bindings: dict[str, str] | None = None,
    parameters: dict[str, Any] | None = None,
    code: str | None = None,
) -> dict[str, Any]:
    project_path = _validate_project_dir(config, project_dir)
    rendered = render_studio_code(
        config,
        entry_id=entry_id,
        project_dir=str(project_path),
        data_file=data_file,
        bindings=bindings,
        parameters=parameters,
    )
    spec = rendered["spec"]
    canonical_id = spec["id"]
    dest = project_path / "wiki-use" / canonical_id
    written = _copy_minimal_assets(spec, dest)

    script_name = "run_studio.py" if rendered["language"] == "Python" else "run_studio.R"
    final_code = code if (code is not None and code.strip()) else rendered["code"]
    (dest / script_name).write_text(final_code, encoding="utf-8", newline="\n")
    written.append(script_name)

    (dest / "bindings.json").write_text(
        json.dumps(rendered["bindings_json"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    written.append("bindings.json")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    use_md = (
        f"# {spec['title']}（Studio 派发副本）\n\n"
        f"- 来源条目：`{entry_id}`（{spec['kind']} · Tier {spec['tier']}）\n"
        f"- 派发时间：{now}\n"
        f"- 数据文件：`{data_file or '未指定'}`\n"
        f"- 运行脚本：`{script_name}`\n"
        f"- 列映射文件：`bindings.json`\n"
    )
    (dest / "RWIKI-USE.md").write_text(use_md, encoding="utf-8", newline="\n")
    written.append("RWIKI-USE.md")

    return {
        "ok": True,
        "output_dir": str(dest),
        "files": sorted(dict.fromkeys(written)),
        "message": f"已派发至 {dest}",
    }


def _resolve_python_exe(config: Config) -> str:
    if config.python_exe and config.python_exe.is_file():
        return str(config.python_exe)
    return sys.executable


def _resolve_rscript_exe(config: Config) -> str:
    if config.rscript_exe and config.rscript_exe.is_file():
        return str(config.rscript_exe)
    found = shutil.which("Rscript")
    if found:
        return found
    raise WikiError(f"Rscript 不存在: {config.rscript_exe}")


def _prepare_cli_template_inputs(
    workdir: Path,
    spec: dict[str, Any],
    data_file: str,
    bindings: dict[str, str] | None,
    parameters: dict[str, Any] | None,
) -> tuple[Path, Path]:
    """Prepare normalized CSV data dir and style JSON override for L2 `--data/--out` renderers."""
    import csv

    data_dir = workdir / "_studio_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    example_dir = workdir / "example"
    if example_dir.is_dir():
        for src in example_dir.iterdir():
            if src.is_file():
                shutil.copyfile(src, data_dir / src.name)

    tables = spec.get("tables") or {}
    primary_filename = None
    for tname, tdef in tables.items():
        if isinstance(tdef, dict):
            candidate = tdef.get("filename") or (f"{tdef['interface']}.csv" if tdef.get("interface") else f"{tname}.csv")
            if primary_filename is None or tdef.get("required", True):
                primary_filename = str(candidate)
                if tdef.get("required", True):
                    break

    raw_df = Path(str(data_file or "").strip()).expanduser()
    if raw_df.is_file() and primary_filename and raw_df.suffix.lower() in (".csv", ".tsv", ".txt"):
        target_csv = data_dir / primary_filename
        sep = "\t" if raw_df.suffix.lower() == ".tsv" else ","
        if sep == ",":
            sample = raw_df.read_text(encoding="utf-8", errors="replace")[:4096]
            if "\t" in sample and "," not in sample.splitlines()[0]:
                sep = "\t"
        reverse_map = {str(v): str(k) for k, v in (bindings or {}).items() if v}
        with raw_df.open("r", encoding="utf-8-sig", errors="replace", newline="") as fin:
            reader = list(csv.reader(fin, delimiter=sep))
        if reader:
            header = reader[0]
            mapped_header = [reverse_map.get(col, col) for col in header]
            with target_csv.open("w", encoding="utf-8", newline="") as fout:
                writer = csv.writer(fout)
                writer.writerow(mapped_header)
                writer.writerows(reader[1:])

    style_spec = spec.get("style") or {}
    param_spec = spec.get("parameters") or {}
    pal_param = param_spec.get("palette") if isinstance(param_spec, dict) else None
    pal_choices = set(pal_param.get("choices") or []) if isinstance(pal_param, dict) else set()

    style_payload: dict[str, Any] = {}
    palettes_db = load_ggsci_palettes()
    for k, v in (parameters or {}).items():
        if v is None or v == "":
            continue
        ks = str(k)
        if ks == "palette":
            pal_entry = resolve_palette(str(v), palettes_db)
            if pal_choices and str(v) not in pal_choices and "palcolor" in style_spec:
                # SCP templates expect SCP palette names in `palette`, arbitrary hex lists in `palcolor`.
                if pal_entry.get("colors"):
                    style_payload["palcolor"] = list(pal_entry["colors"])
                continue
            if "palcolor" in style_spec and str(v) not in {str(style_spec.get("palette", "")), "Paired", "RdBu", "Set1"} and pal_entry.get("colors"):
                style_payload["palcolor"] = list(pal_entry["colors"])
                continue
        style_payload[ks] = v

    pal_name = str((parameters or {}).get("palette") or "NPG")
    pal_entry = resolve_palette(pal_name, palettes_db)
    if pal_entry.get("colors"):
        style_payload["palette_colors"] = list(pal_entry["colors"])

    style_path = workdir / "_studio_style.json"
    style_path.write_text(json.dumps(style_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data_dir, style_path


def run_studio(
    config: Config,
    *,
    entry_id: str,
    project_dir: str = "",
    data_file: str = "",
    bindings: dict[str, str] | None = None,
    parameters: dict[str, Any] | None = None,
    code: str | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    rendered = render_studio_code(
        config,
        entry_id=entry_id,
        project_dir=project_dir,
        data_file=data_file,
        bindings=bindings,
        parameters=parameters,
    )
    spec = rendered["spec"]
    canonical_id = spec["id"]
    run_id = f"{re.sub(r'[^A-Za-z0-9_-]', '_', canonical_id)}_{uuid.uuid4().hex[:8]}"

    if str(project_dir or "").strip():
        project_path = _validate_project_dir(config, project_dir)
        workdir = project_path / "wiki-use" / canonical_id
        _copy_minimal_assets(spec, workdir)
    else:
        workdir = _studio_outputs_root(config) / run_id / "workspace"
        _copy_minimal_assets(spec, workdir)

    script_name = "run_studio.py" if rendered["language"] == "Python" else "run_studio.R"
    final_code = code if (code is not None and code.strip()) else rendered["code"]
    script_path = workdir / script_name
    script_path.write_text(final_code, encoding="utf-8", newline="\n")
    (workdir / "bindings.json").write_text(
        json.dumps(rendered["bindings_json"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )

    before_mtimes = {
        p.resolve(): p.stat().st_mtime_ns
        for p in workdir.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
    }

    env = {
        **os.environ,
        "PYTHONUTF8": "1",
        "RWIKI_DATA_FILE": data_file or "",
        "RWIKI_BINDINGS_JSON": json.dumps(bindings or {}, ensure_ascii=False),
        "RWIKI_PARAMS_JSON": json.dumps(parameters or {}, ensure_ascii=False),
        "RWIKI_OUTPUT_DIR": str(workdir),
    }
    if config.r_libs:
        env["R_LIBS_USER"] = os.pathsep.join(str(p) for p in config.r_libs)

    if rendered["language"] == "Python":
        cmd = [_resolve_python_exe(config), "-X", "utf8", str(script_path)]
    else:
        cmd = [_resolve_rscript_exe(config), "--vanilla", str(script_path)]

    if "--data" in final_code and "--out" in final_code and (workdir / "code").is_dir():
        exec_script = workdir / "code" / script_name
        exec_script.write_text(final_code, encoding="utf-8", newline="\n")
        cli_data_dir, cli_style_path = _prepare_cli_template_inputs(workdir, spec, data_file, bindings, parameters)
        cli_out_dir = workdir / "studio_out"
        cli_out_dir.mkdir(parents=True, exist_ok=True)
        exe = _resolve_python_exe(config) if rendered["language"] == "Python" else _resolve_rscript_exe(config)
        flag_args = ["--data", str(cli_data_dir), "--out", str(cli_out_dir)]
        if "--style" in final_code:
            flag_args.extend(["--style", str(cli_style_path)])
        prefix = ["-X", "utf8"] if rendered["language"] == "Python" else ["--vanilla"]
        cmd = [exe, *prefix, str(exec_script), *flag_args]

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(workdir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
        )
        exit_code = proc.returncode
        stdout, stderr = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = f"执行超时（>{timeout}s）"
    except WikiError as exc:
        return {
            "ok": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": str(exc),
            "output_files": [],
            "preview_url": None,
        }

    produced: list[Path] = []
    for p in sorted(workdir.rglob("*")):
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES:
            old_mtime = before_mtimes.get(p.resolve())
            if old_mtime is None or p.stat().st_mtime_ns > old_mtime:
                produced.append(p)
    if not produced:
        produced = [
            p for p in sorted(workdir.rglob("*"))
            if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
            and "example" not in p.parts
        ]

    out_dir = _studio_outputs_root(config) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    output_files: list[str] = []
    raster_preview: str | None = None
    fallback_preview: str | None = None
    for p in produced:
        rel = p.relative_to(workdir).as_posix()
        target = out_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
        output_files.append(rel)
        suffix = p.suffix.lower()
        url = f"/api/studio/output/{run_id}/{rel}"
        if raster_preview is None and suffix in (".png", ".jpg", ".jpeg", ".svg"):
            raster_preview = url
        elif fallback_preview is None and suffix == ".pdf":
            fallback_preview = url
    preview_url = raster_preview or fallback_preview

    return {
        "ok": exit_code == 0,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "run_id": run_id,
        "output_files": output_files,
        "preview_url": preview_url,
    }
