"""Unified Pydantic template/recipe/method contract validator (inspired by nf-core/modules meta.yml)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from .config import Config, read_json
from .errors import WikiError
from .interfaces import load_interface
from .pages import read_page
from .template_renderer import spec_parameters_to_questions

DEFAULT_GGSCI_PALETTES = ["NPG", "Nature", "Lancet", "NEJM", "JAMA", "AAAS", "JCO", "Cell"]

DEFAULT_STUDIO_PARAMETERS: dict[str, dict[str, Any]] = {
    "palette": {
        "label": "顶刊配色 (ggsci)",
        "type": "select",
        "default": "NPG",
        "choices": DEFAULT_GGSCI_PALETTES,
        "help": "选择 Nature / Lancet / NEJM / JAMA / Cell 等期刊离散配色方案",
    },
    "title": {
        "label": "图表标题",
        "type": "str",
        "default": "",
        "help": "主图标题，留空使用模版默认标题",
    },
    "width": {
        "label": "图宽 (inch)",
        "type": "float",
        "default": 8.0,
        "min": 2.0,
        "max": 24.0,
        "help": "输出图像宽度（英寸）",
    },
    "height": {
        "label": "图高 (inch)",
        "type": "float",
        "default": 6.0,
        "min": 2.0,
        "max": 24.0,
        "help": "输出图像高度（英寸）",
    },
    "font_size": {
        "label": "基础字号 (pt)",
        "type": "float",
        "default": 11.0,
        "min": 6.0,
        "max": 24.0,
        "help": "坐标轴与图例字体大小",
    },
    "p_cutoff": {
        "label": "显著性阈值 (P / padj)",
        "type": "float",
        "default": 0.05,
        "min": 0.0,
        "max": 1.0,
        "help": "统计显著性截断阈值",
    },
    "log2fc_cutoff": {
        "label": "差异倍数阈值 (|log2FC|)",
        "type": "float",
        "default": 1.0,
        "min": 0.0,
        "max": 10.0,
        "help": "差异表达或富集幅度截断值",
    },
}


class ParameterField(BaseModel):
    name: str
    label: str = ""
    type: str = "str"
    default: Any = None
    choices: list[Any] | dict[str, Any] = Field(default_factory=list)
    multiselect: bool = False
    min: float | None = None
    max: float | None = None
    step: float | None = None
    help: str = ""
    placeholder: str = ""
    validator: str = ""
    when: str | bool = True


class TableContract(BaseModel):
    interface: str = ""
    description: str = ""
    required: bool = True
    columns: dict[str, Any] = Field(default_factory=dict)


class TemplateSpec(BaseModel):
    id: str
    kind: str = "template"
    tier: int = 1
    title: str = ""
    language: str = "R"
    entry: str = ""
    panel: str | None = None
    tables: dict[str, TableContract] = Field(default_factory=dict)
    style: dict[str, Any] = Field(default_factory=dict)
    parameters: dict[str, ParameterField] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)


def normalize_parameters(raw_params: Any, *, include_defaults: bool = True) -> dict[str, dict[str, Any]]:
    """Normalize `spec.parameters` (dict or list) into a Studio-ready schema mapping."""
    result: dict[str, dict[str, Any]] = {}
    if isinstance(raw_params, dict):
        items = raw_params
    elif isinstance(raw_params, list):
        items = {
            str(item.get("name") or item.get("var_name")): item
            for item in raw_params
            if isinstance(item, dict) and (item.get("name") or item.get("var_name"))
        }
    else:
        items = {}

    for q in spec_parameters_to_questions(items):
        raw = items.get(q.var_name, {}) if isinstance(items, dict) else {}
        field_type = q.type
        if q.choices and field_type in ("str", "string", ""):
            field_type = "select"
        result[q.var_name] = {
            "name": q.var_name,
            "label": q.label or q.var_name,
            "type": field_type,
            "default": q.default,
            "choices": q.choices,
            "multiselect": q.multiselect,
            "min": q.min_value,
            "max": q.max_value,
            "step": raw.get("step") if isinstance(raw, dict) else None,
            "help": q.help,
            "placeholder": q.placeholder,
            "validator": q.validator,
            "when": q.when,
        }

    if include_defaults and not result:
        for name, cfg in DEFAULT_STUDIO_PARAMETERS.items():
            result[name] = {"name": name, **cfg}
    elif include_defaults and "palette" not in result:
        result["palette"] = {"name": "palette", **DEFAULT_STUDIO_PARAMETERS["palette"]}
    return result


def validate_spec_model(raw: dict[str, Any]) -> TemplateSpec:
    """Validate a spec payload with Pydantic (`nf-core/modules` single-contract style)."""
    try:
        params = normalize_parameters(raw.get("parameters"), include_defaults=False)
        payload = {
            "id": raw.get("id", ""),
            "kind": raw.get("kind", "template"),
            "tier": raw.get("tier", 1),
            "title": raw.get("title", ""),
            "language": raw.get("language", "R"),
            "entry": raw.get("entry", ""),
            "panel": raw.get("panel"),
            "tables": raw.get("tables") or {},
            "style": raw.get("style") or {},
            "parameters": params,
            "dependencies": raw.get("dependencies") or [],
        }
        return TemplateSpec.model_validate(payload)
    except ValidationError as exc:
        raise WikiError(f"spec schema 校验失败: {exc}") from exc


def _display_language(value: str | None) -> str:
    low = (value or "r").strip().lower()
    if low in ("py", "python"):
        return "Python"
    return "R"


def _pick_recipe_script(asset_dir: Path, declared_entry: str) -> tuple[str, Path | None]:
    """Find best script file for a Tier 2 recipe (prefer repair/, then source/)."""
    entry_name = Path(declared_entry).name if declared_entry else ""
    for folder_name in ("repair", "source"):
        folder = asset_dir / folder_name
        if not folder.is_dir():
            continue
        if entry_name and (folder / entry_name).is_file():
            return f"{folder_name}/{entry_name}", folder / entry_name
        candidates = sorted(
            p for p in folder.rglob("*")
            if p.is_file() and p.suffix.lower() in (".rmd", ".r", ".py", ".qmd")
            and p.name.lower() != "install_dependencies.r"
        )
        if candidates:
            rel = candidates[0].relative_to(asset_dir).as_posix()
            return rel, candidates[0]
    return declared_entry, None


def load_unified_spec(config: Config, entry_id: str) -> dict[str, Any]:
    """Load unified Tier 1 (template) or Tier 2 (recipe/method) spec for Studio & MCP."""
    root = config.wiki_root
    for kind, folder in (("template", "templates"), ("recipe", "recipes"), ("method", "methods")):
        page_path = root / folder / f"{entry_id}.md"
        if page_path.is_file():
            break
    else:
        raise WikiError(f"未找到模板、配方或方法: {entry_id}")

    meta, _ = read_page(page_path)
    asset_dir = page_path.with_suffix("")

    if kind == "template":
        spec_path = asset_dir / "spec.json"
        raw = read_json(spec_path) if spec_path.is_file() else {}
        tables_out: dict[str, Any] = {}
        for tname, tdef in (raw.get("tables") or {}).items():
            if not isinstance(tdef, dict):
                continue
            slug = str(tdef.get("interface") or "")
            cols: dict[str, Any] = {}
            iface_title = slug
            if slug:
                try:
                    iface = load_interface(root, slug)
                    cols = iface.get("columns") or {}
                    iface_title = iface.get("title") or slug
                except WikiError:
                    cols = {}
            tables_out[tname] = {
                "interface": slug,
                "interface_title": iface_title,
                "description": tdef.get("description", ""),
                "required": tdef.get("required", True),
                "columns": cols,
            }
        style = raw.get("style") if isinstance(raw.get("style"), dict) else {}
        params = normalize_parameters(raw.get("parameters"), include_defaults=True)
        # Seed defaults from style if matching keys exist
        for skey, pkey in (("width_in", "width"), ("height_in", "height"), ("dpi", "dpi")):
            if skey in style and pkey in params and isinstance(style[skey], (int, float)):
                params[pkey]["default"] = style[skey]
        return {
            "id": entry_id,
            "kind": "template",
            "tier": 1,
            "title": meta.get("title", entry_id),
            "status": meta.get("status", "draft"),
            "language": _display_language(raw.get("language") or meta.get("language")),
            "entry": raw.get("entry", ""),
            "panel": raw.get("panel"),
            "tables": tables_out,
            "style": style,
            "parameters": params,
            "dependencies": [],
            "asset_dir": str(asset_dir),
            "page": f"templates/{entry_id}.md",
        }

    if kind == "recipe":
        rel_entry, script_path = _pick_recipe_script(asset_dir, str(meta.get("entry") or ""))
        tables_out = {}
        inputs = meta.get("inputs") or []
        if inputs:
            cols = {
                Path(str(item.get("file", f"input_{i}"))).stem: {
                    "type": "file",
                    "required": True,
                    "description": str(item.get("note") or item.get("file") or ""),
                }
                for i, item in enumerate(inputs) if isinstance(item, dict)
            }
            tables_out["input"] = {
                "interface": "recipe-input",
                "interface_title": "配方输入文件",
                "description": "对应配方原脚本输入文件；可通过 data_file 覆盖",
                "required": False,
                "columns": cols,
            }
        pkgs = meta.get("packages") or {}
        deps: list[str] = []
        if isinstance(pkgs, dict):
            for group in pkgs.values():
                if isinstance(group, list):
                    deps.extend(str(p) for p in group)
        return {
            "id": entry_id,
            "kind": "recipe",
            "tier": 2,
            "title": meta.get("title", entry_id),
            "status": meta.get("status", "draft"),
            "language": _display_language(meta.get("language")),
            "entry": rel_entry,
            "script_path": str(script_path) if script_path else "",
            "panel": None,
            "tables": tables_out,
            "style": {},
            "parameters": normalize_parameters(meta.get("parameters"), include_defaults=True),
            "dependencies": list(dict.fromkeys(deps)),
            "asset_dir": str(asset_dir),
            "page": f"recipes/{entry_id}.md",
        }

    # method (Tier 2 analysis method)
    tables_out = {}
    for slug in meta.get("inputs") or []:
        if not isinstance(slug, str) or not slug:
            continue
        try:
            iface = load_interface(root, slug)
            cols = iface.get("columns") or {}
            iface_title = iface.get("title") or slug
        except WikiError:
            cols, iface_title = {}, slug
        tables_out[slug] = {
            "interface": slug,
            "interface_title": iface_title,
            "description": f"输入接口 {iface_title}",
            "required": False,
            "columns": cols,
        }
    impls = [item for item in (meta.get("implementations") or []) if isinstance(item, dict)]
    entry_rel = ""
    lang = "R"
    deps = []
    if impls:
        ep = str(impls[0].get("entrypoint") or "")
        entry_rel = ep.partition(":")[0]
        lang = _display_language(impls[0].get("language"))
        deps = [str(d) for d in (impls[0].get("dependencies") or [])]
    if not entry_rel and (asset_dir / "code").is_dir():
        cands = sorted(p for p in (asset_dir / "code").rglob("*")
                       if p.is_file() and p.suffix.lower() in (".r", ".py", ".rmd"))
        if cands:
            entry_rel = cands[0].relative_to(asset_dir).as_posix()
            lang = "Python" if cands[0].suffix.lower() == ".py" else "R"
    return {
        "id": entry_id,
        "kind": "method",
        "tier": 2,
        "title": meta.get("title", entry_id),
        "status": meta.get("status", "draft"),
        "language": lang,
        "entry": entry_rel,
        "panel": None,
        "tables": tables_out,
        "style": {},
        "parameters": normalize_parameters(meta.get("parameters"), include_defaults=True),
        "dependencies": deps,
        "outputs": list(meta.get("outputs") or []),
        "next_steps": list(meta.get("next_steps") or []),
        "asset_dir": str(asset_dir),
        "page": f"methods/{entry_id}.md",
    }
