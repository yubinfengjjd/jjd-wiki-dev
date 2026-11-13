"""Controlled domain tags from ``config.taxonomy``.

Page tags store a scenario key (``single-cell``) or its Chinese label
(``单细胞分析``). Both appear on existing pages: gallery ingest writes labels,
and recipe auto-tags / curation write keys. Aliases and free names (software,
datasets, models) belong in ``keywords``.

Illegal or repeated tags are errors, the same severity as ``purposes``.
An empty list stays readable.
"""
from pathlib import Path

from .config import Config, load_taxonomy
from .errors import WikiError


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def taxonomy_file(config: Config) -> Path:
    """The configured vocabulary, or the copy shipped with this repo.

    Vault CI runs ``wiki.py`` from the vault root with ``taxonomy`` set to
    ``spec/scenario_taxonomy.yaml``. That path is not in the vault; the dev
    checkout (this file's repository, or ``./开发``) holds it. A configured
    file that exists always wins, so a caller's own taxonomy is never replaced.
    """
    configured = config.taxonomy
    if configured.is_file():
        return configured
    dev = Path(__file__).resolve().parents[3]
    candidates = [dev / 'docs' / 'scenario_taxonomy.yaml',
                  dev / "spec" / "scenario_taxonomy.yaml"]
    try:
        relative = configured.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        relative = None
    if relative is not None:
        candidates.append(Path.cwd().resolve() / "开发" / relative)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return configured


def load_vocabulary(config: Config) -> frozenset[str]:
    """Scenario keys and labels. Aliases are not tag values."""
    scenarios = load_taxonomy(taxonomy_file(config))
    if not isinstance(scenarios, dict):
        raise WikiError("受控词表 scenarios 必须为对象")
    values = []
    for key, item in scenarios.items():
        if _text(key):
            values.append(key)
        label = item.get("label") if isinstance(item, dict) else None
        if _text(label):
            values.append(label)
    return frozenset(values)


def normalize_tags(tags: list[str]) -> list[str]:
    """Strip, drop blanks, and dedupe while keeping the first occurrence."""
    return list(dict.fromkeys(tag.strip() for tag in tags if tag.strip()))


def tag_errors(meta: dict, vocabulary: frozenset[str] | None) -> list[str]:
    """Illegal classification is an error; a missing or empty list stays readable."""
    if not isinstance(meta, dict) or "tags" not in meta:
        return []
    tags = meta.get("tags")
    if not isinstance(tags, list) or any(not _text(tag) for tag in tags):
        return ["tags 必须为字符串列表"]
    if vocabulary is None:
        return []
    unknown = [tag for tag in dict.fromkeys(tags) if tag not in vocabulary]
    if unknown:
        return ["tags 含非法领域: " + "、".join(unknown)
                + "；别名、软件、数据集和模型名请写入 keywords"]
    if len(set(tags)) != len(tags):
        return ["tags 不得重复"]
    return []
