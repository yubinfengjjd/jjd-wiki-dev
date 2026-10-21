import csv
import json
from pathlib import Path

from .config import read_json
from .errors import WikiError
from .interfaces import load_interface


def load_spec(template_dir: Path) -> dict:
    spec = read_json(template_dir / "spec.json")
    if not isinstance(spec, dict):
        raise WikiError("spec 必须是对象")
    entry = spec.get("entry")
    if not isinstance(entry, str) or not (template_dir / entry).is_file():
        raise WikiError(f"spec.entry 文件不存在: {entry}")
    language = spec.get("language")
    if language not in ("python", "r"):
        raise WikiError(f"spec.language 非法: {language}")
    extension = ".py" if language == "python" else ".r"
    if Path(entry).suffix.lower() != extension:
        raise WikiError(f"spec.language 与 entry 扩展名不一致: {language} / {entry}")
    if language == "python":
        panel = spec.get("panel")
        if not isinstance(panel, str) or not (template_dir / panel).is_file():
            raise WikiError(f"spec.panel 文件不存在: {panel}")
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
        unknown = table.keys() - {"interface", "description"}
        if unknown:
            raise WikiError(f"tables.{name} 不支持字段: {', '.join(sorted(unknown))}；只允许 interface 和 description")
        slug = table.get("interface")
        if not isinstance(slug, str) or not slug.strip():
            raise WikiError(f"tables.{name}.interface 必须为非空字符串")
        if not isinstance(table.get("description"), str):
            raise WikiError(f"tables.{name}.description 必须为字符串")
        interface = load_interface(template_dir.parent.parent, slug)
        table["columns"] = interface["columns"]
        table["interface_title"] = interface["title"]
    if not isinstance(spec.get("style"), dict):
        raise WikiError("spec.style 必须为对象")
    return spec


def check_data(spec: dict, data_dir: Path) -> None:
    for name, table in spec["tables"].items():
        check_table_data(name, table, data_dir / f"{table['interface']}.csv")


def check_table_data(name: str, table: dict, path: Path) -> None:
    if not path.is_file():
        raise WikiError(f"tables.{name} 数据文件不存在: {path}")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        header = next(csv.reader(stream), [])
    missing = [column for column in table["columns"] if column not in header]
    if missing:
        raise WikiError(f"tables.{name} 缺列: {', '.join(missing)} ({path})")


def requirements_markdown(spec: dict) -> str:
    lines = []
    for name, table in spec["tables"].items():
        link = f"[[interfaces/{table['interface']}|{table['interface_title']}]]"
        lines.extend([f"### {name}（{table['interface']}.csv）：{table['description']} {link}", "",
                      "| 列 | 类型 | 含义 |", "|---|---|---|"])
        for column, definition in table["columns"].items():
            lines.append(f"| {column} | {definition['type']} | {definition.get('description', '')} |")
        lines.append("")
    lines.extend(["### 可覆盖的 style", ""])
    for key, value in spec["style"].items():
        lines.append(f"- `{key}`：`{json.dumps(value, ensure_ascii=False)}`")
    return "\n".join(lines).rstrip() + "\n"
