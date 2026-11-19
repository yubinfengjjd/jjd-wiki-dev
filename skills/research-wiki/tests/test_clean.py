"""Tests for rwiki clean safe workspace cleanup."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from rwiki.clean import clean_workspace
from rwiki.cli import main as cli_main
from rwiki.config import Config
from rwiki.store import init


def test_clean_dry_run_and_apply_protects_runtime_and_sources(tmp_path: Path):
    env_root = tmp_path / "env"
    wiki = tmp_path / "wiki"
    gallery = tmp_path / "gallery"
    gallery.mkdir()
    taxonomy = tmp_path / "taxonomy.json"
    taxonomy.write_text(json.dumps({"scenarios": {"single-cell": "单细胞"}}), encoding="utf-8")

    work_rwiki = env_root / "work" / "rwiki"
    work_rwiki.mkdir(parents=True)
    sources = env_root / "sources"
    sources.mkdir(parents=True)
    config = Config(
        wiki,
        gallery,
        taxonomy,
        Path(sys.executable),
        Path("Rscript"),
        8765,
        sources_root=sources,
        work_root=work_rwiki,
    )
    init(config)

    # Protected dirs that must NEVER be touched
    rlib = env_root / "R-lib" / "pkg"
    rlib.mkdir(parents=True)
    (rlib / "x.R").write_text("1", encoding="utf-8")
    paper = sources / "papers" / "2026-test" / "src"
    paper.mkdir(parents=True)
    (paper / "01_step.R").write_text("1", encoding="utf-8")
    studio = work_rwiki / "studio_outputs"
    studio.mkdir()
    (studio / "keep.txt").write_text("keep", encoding="utf-8")

    # Disposable clutter
    tmp_sub = env_root / "tmp" / "scratch"
    tmp_sub.mkdir(parents=True)
    (tmp_sub / "chk.R").write_text("1", encoding="utf-8")
    ui_dir = env_root / "t06-ui-abc"
    ui_dir.mkdir()
    (ui_dir / "lock").write_text("x", encoding="utf-8")
    probe = env_root / "work" / "codex-scp-probe"
    probe.mkdir()
    (probe / "p.txt").write_text("x", encoding="utf-8")
    retired_rwiki = work_rwiki / "local-omics-reuse-20261102"
    retired_rwiki.mkdir()
    backup_dir = env_root / "skill-backup"
    backup_dir.mkdir()

    dry = clean_workspace(config, apply=False)
    assert dry["mode"] == "dry_run"
    assert dry["total_candidates"] == 4
    assert tmp_sub.exists() and ui_dir.exists() and probe.exists()

    applied = clean_workspace(config, apply=True)
    assert applied["mode"] == "apply"
    assert applied["removed_count"] == 4
    assert not tmp_sub.exists()
    assert not ui_dir.exists()
    assert not probe.exists()
    assert not retired_rwiki.exists()

    # Protected & backup (without include_backups) remain untouched
    assert (rlib / "x.R").is_file()
    assert (paper / "01_step.R").is_file()
    assert (studio / "keep.txt").is_file()
    assert backup_dir.is_dir()

    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps(
            {
                "wiki_root": str(wiki),
                "gallery_root": str(gallery),
                "taxonomy": str(taxonomy),
                "python_exe": sys.executable,
                "rscript_exe": "Rscript",
                "port": 8765,
                "sources_root": str(sources),
                "work_root": str(work_rwiki),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assert cli_main(["--config", str(cfg_path), "clean", "--include-backups", "--apply", "--json"]) == 0
    assert not backup_dir.exists()
