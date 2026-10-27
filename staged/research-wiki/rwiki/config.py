import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from .errors import WikiError


@dataclass(frozen=True)
class Config:
    wiki_root: Path
    gallery_root: Path
    taxonomy: Path
    python_exe: Path
    rscript_exe: Path
    port: int
    function_defaults: dict = field(default_factory=dict)
    single_panel_only: bool = False
    push_guard: dict = field(default_factory=dict)
    github: dict = field(default_factory=dict)
    # v2: upstream snapshots, run work dirs and the Wiki-only R libraries live outside the Wiki.
    sources_root: Path | None = None
    work_root: Path | None = None
    r_libs: tuple[Path, ...] = ()
    cran_mirror: str = "https://cloud.r-project.org/"


def read_json(path: Path) -> dict:
    if not path.is_file():
        raise WikiError(f"JSON 文件不存在: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise WikiError(f"JSON 无法解析 {path}: {error}") from error


def load_config(path: Path, wiki_root: Path | None = None) -> Config:
    """wiki_root 覆盖顺序：参数（--wiki-root）> 环境变量 RWIKI_WIKI_ROOT > 配置文件。"""
    values = read_json(path)
    override = wiki_root or os.environ.get("RWIKI_WIKI_ROOT")
    if override:
        values["wiki_root"] = str(override)
    required = ("wiki_root", "gallery_root", "taxonomy", "python_exe", "rscript_exe")
    missing = [key for key in (*required, "port") if key not in values]
    if missing:
        raise WikiError(f"配置缺少: {', '.join(missing)}")
    single_only = values.get("single_panel_only", False)
    if not isinstance(single_only, bool):
        raise WikiError("single_panel_only 必须是布尔值")
    defaults = values.get("function_defaults", {})
    if not isinstance(defaults, dict) or defaults.keys() - {"sizing"}:
        raise WikiError("function_defaults 只允许 sizing 对象")
    if defaults:
        from .sizing import validate_policy
        try:
            defaults = {"sizing": validate_policy(defaults.get("sizing"))}
        except ValueError as error:
            raise WikiError(str(error)) from error
    libs = values.get("r_libs", [])
    if not isinstance(libs, list) or any(not isinstance(item, str) or not item for item in libs):
        raise WikiError("r_libs 必须是路径字符串列表")
    optional = {key: Path(values[key]).resolve() for key in ("sources_root", "work_root") if values.get(key)}
    return Config(*(Path(values[key]).resolve() for key in required), port=values["port"],
                  function_defaults=defaults, single_panel_only=single_only,
                  push_guard=values.get("push_guard", {}), github=values.get("github", {}),
                  r_libs=tuple(Path(item).resolve() for item in libs),
                  cran_mirror=values.get("cran_mirror", "https://cloud.r-project.org/"), **optional)


def load_taxonomy(path: Path) -> dict:
    return read_json(path)["scenarios"]
