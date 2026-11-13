"""Export the same immutable full-text corpus used by the local search API."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path


def engine_root() -> Path:
    for relative in ("skills/research-wiki", "staged/research-wiki"):
        for parent in Path(__file__).resolve().parents:
            candidate = parent / relative
            if (candidate / "rwiki" / "config.py").is_file():
                return candidate
    raise RuntimeError("Cannot locate rwiki engine; pass --engine explicitly")


def export(config: Path, out: Path, engine: Path | None = None) -> dict:
    sys.path.insert(0, str(engine or engine_root()))
    from rwiki.config import load_config
    from rwiki.search import export_index
    index = export_index(load_config(config))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--engine", type=Path)
    parser.add_argument("--out", type=Path, default=Path(__file__).with_name("full-search-index.json"))
    args = parser.parse_args()
    index = export(args.config, args.out, args.engine)
    print(json.dumps({"out": str(args.out), "coverage": index["coverage"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
