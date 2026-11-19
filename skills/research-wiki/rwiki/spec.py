import csv
import json
from pathlib import Path

from .confine import confined
from .config import read_json
from .errors import WikiError
from .interfaces import load_interface


def _inside(template_dir: Path, value) -> bool:
    """A spec file reference must stay inside the template's own asset folder."""
    return (isinstance(value, str) and not Path(value).anchor
            and confined(template_dir / value, template_dir, template_dir.parent.parent)
            and (template_dir / value).is_file())


def load_spec(template_dir: Path) -> dict:
    spec = read_json(template_dir / "spec.json")
    if not isinstance(spec, dict):
        raise WikiError("spec 必须是对象")
    entry = spec.get("entry")
    if not _inside(template_dir, entry):
        raise WikiError(f"spec.entry 文件不存在或越出模板目录: {entry}")
    language = spec.get("language")
    if language not in ("python", "r"):
        raise WikiError(f"spec.language 非法: {language}")
    extension = ".py" if language == "python" else ".r"
    if Path(entry).suffix.lower() != extension:
        raise WikiError(f"spec.language 与 entry 扩展名不一致: {language} / {entry}")
    if language == "python":
        panel = spec.get("panel")
        if not _inside(template_dir, panel):
            raise WikiError(f"spec.panel 文件不存在或越出模板目录: {panel}")
        if not (template_dir / "code/__init__.py").is_file():
            raise WikiError("Python code 必须为包，缺少 code/__init__.py")
    elif "panel" in spec:
        raise WikiError("R spec 不得有 panel")
    tables = spec.get("tables")
    if not isinstance(tables, dict) or not tables:
        raise WikiError("spec.tables 必须为非空对象")
    for name, table in tables.items():
        if not isinstance(table, dict):
            raise WikiError(f"tables.{name} 必须为对象")
        slug = table.get("interface")
        if slug is not None and not isinstance(slug, str):
            raise WikiError(f"tables.{name}.interface 必须为字符串")
        slug = (slug or "").strip()
        allowed_keys = ({"interface", "description", "required", "required_any_of"} if slug
                        else {"interface", "description", "required", "filename", "columns", "required_any_of"})
        unknown = table.keys() - allowed_keys
        if unknown:
            raise WikiError(f"tables.{name} 不支持字段: {', '.join(sorted(unknown))}；"
                            + ("只允许 interface、description、required 和 required_any_of" if slug
                               else "只允许 interface、description、required、filename、columns 和 required_any_of"))
        if "required_any_of" in table:
            raw_groups = table["required_any_of"]
            if (not isinstance(raw_groups, list) or not raw_groups
                    or any(not isinstance(g, list) or not g or any(not isinstance(c, str) or not c.strip() for c in g)
                           for g in raw_groups)):
                raise WikiError(f"tables.{name}.required_any_of 必须为非空列名列表的列表")
        if "required" in table and not isinstance(table["required"], bool):
            raise WikiError(f"tables.{name}.required 必须为布尔值")
        if not isinstance(table.get("description"), str):
            raise WikiError(f"tables.{name}.description 必须为字符串")
        filename = table.get("filename") if not slug else None
        if filename is not None and (not isinstance(filename, str) or not filename.strip()
                                     or Path(filename).anchor or "/" in filename or "\\" in filename):
            raise WikiError(f"tables.{name}.filename 必须为表目录下纯文件名: {filename}")
        if slug:
            interface = load_interface(template_dir.parent.parent, slug)
            table["columns"] = interface["columns"]
            table["interface_title"] = interface["title"]
            table["filename"] = filename.strip() if filename else f"{slug}.csv"
        else:
            inline_cols = table.get("columns")
            if inline_cols is None:
                inline_cols = {}
            if not isinstance(inline_cols, dict):
                raise WikiError(f"tables.{name}.columns 必须为对象")
            for col_name, col_def in inline_cols.items():
                if not isinstance(col_def, dict) or not isinstance(col_def.get("type"), str):
                    raise WikiError(f"tables.{name}.columns.{col_name} 须含 type 字符串")
            if not filename and "columns" not in table:
                raise WikiError(f"tables.{name} 缺少 interface 或 inline filename/columns")
            table["interface"] = ""
            table["columns"] = inline_cols
            table["interface_title"] = table.get("description") or name
            table["filename"] = filename.strip() if filename else f"{name}.csv"
    if not isinstance(spec.get("style"), dict):
        raise WikiError("spec.style 必须为对象")
    return spec


def _table_filename(name: str, table: dict) -> str:
    if isinstance(table.get("filename"), str) and table["filename"].strip():
        return table["filename"].strip()
    if isinstance(table.get("interface"), str) and table["interface"].strip():
        return f"{table['interface'].strip()}.csv"
    return f"{name}.csv"


def check_data(spec: dict, data_dir: Path) -> None:
    for name, table in spec["tables"].items():
        check_table_data(name, table, data_dir / _table_filename(name, table))


def check_table_data(name: str, table: dict, path: Path) -> None:
    if not path.is_file():
        if table.get("required", True):
            raise WikiError(f"tables.{name} 数据文件不存在: {path}")
        return
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as stream:
        first_line = stream.readline()
    delimiter = "\t" if (path.suffix.lower() in (".tsv", ".txt") and "\t" in first_line) else ","
    header = [col.strip() for col in next(csv.reader([first_line], delimiter=delimiter), [])]
    # Only the columns the implementation really reads are required; an optional
    # column is declared by the interface and handled by the template's own default.
    required = [column for column, definition in (table.get("columns") or {}).items()
                if isinstance(definition, dict) and definition.get("required", True)]
    missing = [column for column in required if column not in header]
    if missing:
        raise WikiError(f"tables.{name} 缺列: {', '.join(missing)} ({path})")
    any_of = table.get("required_any_of")
    if isinstance(any_of, list) and any_of:
        groups = [[str(col).strip() for col in grp if str(col).strip()] for grp in any_of if isinstance(grp, list)]
        groups = [grp for grp in groups if grp]
        if groups and not any(all(col in header for col in grp) for grp in groups):
            desc = " 或 ".join("+".join(grp) for grp in groups)
            raise WikiError(f"tables.{name} 缺必选列组（需满足其一）: {desc} ({path})")


def requirements_markdown(spec: dict) -> str:
    lines = []
    for name, table in spec["tables"].items():
        slug = (table.get("interface") or "").strip()
        filename = _table_filename(name, table)
        link = f"[[interfaces/{slug}|{table['interface_title']}]]" if slug else "（模板内联表结构）"
        optional = "" if table.get("required", True) else "（可选表）"
        columns = table.get("columns") or {}
        # Keep the historical three-column table until a template really has an
        # optional table/column; then the required/optional distinction is explicit.
        has_optional = (not table.get("required", True)
                        or any(not definition.get("required", True) for definition in columns.values()))
        lines.extend([f"### {name}（{filename}）{optional}：{table['description']} {link}", ""])
        if not columns:
            lines.append("- 矩阵/自由列结构，按模板示例表格式提供输入。")
        elif has_optional:
            lines.extend(["| 列 | 类型 | 必需 | 含义 |", "|---|---|---|---|"])
            for column, definition in columns.items():
                required = "必需" if definition.get("required", True) else "可选"
                lines.append(f"| {column} | {definition['type']} | {required} | {definition.get('description', '')} |")
        else:
            lines.extend(["| 列 | 类型 | 含义 |", "|---|---|---|"])
            for column, definition in columns.items():
                lines.append(f"| {column} | {definition['type']} | {definition.get('description', '')} |")
        any_of = table.get("required_any_of")
        if isinstance(any_of, list) and any_of:
            groups = [[str(col).strip() for col in grp if str(col).strip()] for grp in any_of if isinstance(grp, list)]
            groups = [grp for grp in groups if grp]
            if groups:
                lines.append("")
                lines.append("- 必选列组（需满足其一）：" + " 或 ".join("`" + " + ".join(grp) + "`" for grp in groups))
        lines.append("")
    lines.extend(["### 可覆盖的 style", ""])
    for key, value in spec["style"].items():
        lines.append(f"- `{key}`：`{json.dumps(value, ensure_ascii=False)}`")
    return "\n".join(lines).rstrip() + "\n"
