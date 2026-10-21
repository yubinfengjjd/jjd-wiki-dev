import json
from dataclasses import dataclass
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


def read_json(path: Path) -> dict:
    if not path.is_file():
        raise WikiError(f"JSON 文件不存在: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise WikiError(f"JSON 无法解析 {path}: {error}") from error


def load_config(path: Path) -> Config:
    values = read_json(path)
    required = ("wiki_root", "gallery_root", "taxonomy", "python_exe", "rscript_exe")
    missing = [key for key in (*required, "port") if key not in values]
    if missing:
        raise WikiError(f"配置缺少: {', '.join(missing)}")
    return Config(*(Path(values[key]).resolve() for key in required), port=values["port"])


def load_taxonomy(path: Path) -> dict:
    return read_json(path)["scenarios"]
