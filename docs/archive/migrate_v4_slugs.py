"""Migrate the 31 v3 long template IDs to v4 short slugs with legacy aliases.

Supports ``--dry-run`` (default) and ``--apply`` modes. Never modifies
``spec.json``, ``wiki/sources/``, ``*/source/``, ``verify/history/``, or
``<!-- user:start -->...<!-- user:end -->`` author blocks, and never fabricates
historical timestamps or environment fields in ``runtime-portability.json``.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from copy import deepcopy
from pathlib import Path

_DEV_ROOT = Path(__file__).resolve().parents[1]
_RWIKI_PARENT = _DEV_ROOT / "skills" / "research-wiki"
if str(_RWIKI_PARENT) not in sys.path:
    sys.path.insert(0, str(_RWIKI_PARENT))

from rwiki.aliases import ALIAS_PATTERN  # noqa: E402
from rwiki.pages import read_page, write_page  # noqa: E402
from rwiki.runtime_contract import closure_hash, read_manifest  # noqa: E402

SLUGS_MAP: dict[str, str] = {
    "2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar": "shap-importance-bar",
    "2026-08-17-shap-feature-mechanism__fig01-shap-a-f--beeswarm": "shap-beeswarm",
    "2026-08-17-shap-feature-mechanism__fig01-shap-a-f--radial-bar": "shap-radial-bar",
    "2026-10-19-regression-stability__fig03-density-panel--density-scatter": "pred-density-scatter",
    "2026-10-19-regression-stability__fig04-boxplot-panel--boxplot": "resampling-metric-box",
    "2026-10-22-glaucoma-scrna__fig01-cns-umap--umap": "scrna-celltype-umap",
    "2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap": "scrna-feature-umap-grid",
    "2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot": "marker-bubble-dotplot",
    "2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow": "cell-prop-flow-bar",
    "2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin": "pathway-stat-violin",
    "2026-10-22-scp-example__fig01-volcano--volcano": "scp-de-volcano",
    "2026-10-22-scp-example__fig02-ring--ring": "scp-comp-ring",
    "2026-10-22-scp-example__fig03-pie--pie": "scp-comp-pie",
    "2026-10-22-scp-example__fig04-rose--rose": "scp-comp-rose",
    "2026-10-22-scp-example__fig05-trend--trend": "scp-comp-trend",
    "2026-10-22-scp-example__fig06-area--area": "scp-comp-area",
    "2026-10-22-scp-example__fig07-dot--dot": "scp-comp-dot",
    "2026-10-22-scp-example__fig08-group-heatmap--heatmap": "scp-group-heatmap",
    "2026-10-22-scp-example__fig09-bar--bar": "scp-count-bar",
    "2026-10-22-scp-example__fig10-sankey--sankey": "scp-flow-sankey",
    "2026-10-22-scp-example__fig11-chord--chord": "scp-flow-chord",
    "2026-10-22-scp-example__fig12-venn--venn": "set-venn",
    "2026-10-22-scp-example__fig13-upset--upset": "set-upset",
    "2026-10-22-scp-example__fig14-feature-heatmap--heatmap": "scp-feature-heatmap",
    "2026-10-22-scp-example__fig15-cell-cor-heatmap--heatmap": "scp-cell-cor-heatmap",
    "2026-10-22-scp-example__fig16-cell-density--ridge": "scp-expr-ridge",
    "2026-10-22-scp-example__fig17-group-heatmap-dot--heatmap": "scp-group-dot-heatmap",
    "figureya-1survivalcurve-update--km-curve": "km-survival-curve",
    "figureya-59volcanov2--volcano": "bulk-de-volcano",
    "figureya-6rhrsv2--forest": "subgroup-hazard-forest",
    "ks-cellchat-circos-multi--circos": "cellchat-circos-multi",
}

_PROTECTED_BLOCK_RE = re.compile(
    r"(<!-- facts:start -->.*?<!-- facts:end -->|<!-- user:start -->.*?<!-- user:end -->)",
    re.S,
)
_REF_DIRS = ("chart-types", "layouts", "methods", "projects", "recipes", "scenarios")


def build_mapping() -> dict[str, str]:
    """Return and validate the exact 31-to-31 old-to-new template slug bijection."""
    if len(SLUGS_MAP) != 31:
        raise ValueError(f"Expected 31 mappings, got {len(SLUGS_MAP)}")
    if len(set(SLUGS_MAP.values())) != 31:
        raise ValueError("New template slugs must be unique")
    if set(SLUGS_MAP.keys()) & set(SLUGS_MAP.values()):
        raise ValueError("Old and new template slug sets must be disjoint")
    for old_id, new_id in SLUGS_MAP.items():
        if not ALIAS_PATTERN.fullmatch(old_id) or not ALIAS_PATTERN.fullmatch(new_id):
            raise ValueError(f"Invalid slug format: {old_id} -> {new_id}")
    return dict(SLUGS_MAP)


def _compile_token_pattern(mapping: dict[str, str]) -> re.Pattern[str]:
    ordered = sorted(mapping.keys(), key=len, reverse=True)
    alternatives = "|".join(re.escape(key) for key in ordered)
    return re.compile(rf"(?<![A-Za-z0-9_-])({alternatives})(?![A-Za-z0-9_-])")


def _replace_outside_protected_blocks(body: str, pattern: re.Pattern[str], mapping: dict[str, str]) -> str:
    parts = _PROTECTED_BLOCK_RE.split(body)
    for idx in range(0, len(parts), 2):
        parts[idx] = pattern.sub(lambda m: mapping[m.group(1)], parts[idx])
    return "".join(parts)


def _rewrite_id_or_path(value: str, mapping: dict[str, str]) -> str:
    if value in mapping:
        return mapping[value]
    if value.startswith("templates/"):
        rest = value[len("templates/"):]
        if rest.endswith(".md") and rest[:-3] in mapping:
            return f"templates/{mapping[rest[:-3]]}.md"
        head, sep, tail = rest.partition("/")
        if head in mapping:
            return f"templates/{mapping[head]}{sep}{tail}"
    return value


def _insert_aliases(meta: dict, old_id: str, new_id: str) -> dict:
    updated: dict = {}
    aliases = list(meta.get("aliases") or [])
    if old_id not in aliases:
        aliases.append(old_id)
    inserted = False
    for key, val in meta.items():
        if key == "aliases":
            continue
        if key == "id":
            updated["id"] = new_id
            updated["aliases"] = aliases
            inserted = True
        else:
            updated[key] = val
    if not inserted:
        updated["id"] = new_id
        updated["aliases"] = aliases
    return updated


def _migrate_page_meta(meta: dict, mapping: dict[str, str]) -> tuple[dict, bool]:
    updated = deepcopy(meta)
    ptype = updated.get("type")

    if ptype == "layout":
        if isinstance(updated.get("templates"), list):
            updated["templates"] = [mapping.get(t, t) for t in updated["templates"]]
        if isinstance(updated.get("template_panels"), dict):
            updated["template_panels"] = {
                mapping.get(k, k): v for k, v in updated["template_panels"].items()
            }
    elif ptype == "method":
        if isinstance(updated.get("figure_relations"), list):
            for rel in updated["figure_relations"]:
                if not isinstance(rel, dict):
                    continue
                if isinstance(rel.get("figure"), str):
                    rel["figure"] = _rewrite_id_or_path(rel["figure"], mapping)
                if isinstance(rel.get("evidence"), list):
                    rel["evidence"] = [
                        _rewrite_id_or_path(item, mapping) if isinstance(item, str) else item
                        for item in rel["evidence"]
                    ]
        if isinstance(updated.get("next_steps"), list):
            for step in updated["next_steps"]:
                if isinstance(step, dict) and isinstance(step.get("viz_templates"), list):
                    step["viz_templates"] = [
                        _rewrite_id_or_path(item, mapping) if isinstance(item, str) else item
                        for item in step["viz_templates"]
                    ]
    elif ptype == "scenario":
        if isinstance(updated.get("picks"), list):
            new_picks = []
            for pick in updated["picks"]:
                if isinstance(pick, dict) and isinstance(pick.get("id"), str):
                    pick["id"] = _rewrite_id_or_path(pick["id"], mapping)
                    new_picks.append(pick)
                elif isinstance(pick, str):
                    new_picks.append(_rewrite_id_or_path(pick, mapping))
                else:
                    new_picks.append(pick)
            updated["picks"] = new_picks
        if isinstance(updated.get("steps"), list):
            for step in updated["steps"]:
                if not isinstance(step, dict):
                    continue
                for key in ("templates", "viz_templates"):
                    if isinstance(step.get(key), list):
                        step[key] = [
                            _rewrite_id_or_path(item, mapping) if isinstance(item, str) else item
                            for item in step[key]
                        ]
    elif ptype == "project":
        if isinstance(updated.get("templates"), list):
            updated["templates"] = [mapping.get(t, t) for t in updated["templates"]]

    return updated, updated != meta


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _migrate_template_assets(
    tdir: Path,
    old_id: str,
    new_id: str,
    mapping: dict[str, str],
    pattern: re.Pattern[str],
    *,
    dry_run: bool,
    report: dict,
) -> None:
    old_md = tdir / f"{old_id}.md"
    old_folder = tdir / old_id
    new_md = tdir / f"{new_id}.md"
    new_folder = tdir / new_id

    if not old_md.is_file() or not old_folder.is_dir():
        raise FileNotFoundError(f"Missing template page or directory for {old_id}")
    if new_md.exists() or new_folder.exists():
        raise FileExistsError(f"Target template already exists: {new_id}")

    meta, body = read_page(old_md)
    new_meta = _insert_aliases(meta, old_id, new_id)
    new_body = _replace_outside_protected_blocks(body, pattern, mapping)

    rt_path = old_folder / "runtime.json"
    rp_path = old_folder / "verify" / "runtime-portability.json"
    vj_path = old_folder / "verify" / "verify.json"
    cm_path = old_folder / "code-manifest.json"
    acc_path = old_folder / "acceptance.json"

    pre_closure = None
    if rt_path.is_file():
        pre_manifest, _ = read_manifest(old_folder, old_id, "template")
        if pre_manifest is not None:
            pre_closure = closure_hash(old_folder, pre_manifest["implementations"][0])

    was_closure_bound = False
    if rp_path.is_file():
        rp_data = json.loads(rp_path.read_text(encoding="utf-8"))
        was_closure_bound = pre_closure is not None and rp_data.get("closure_hash") == pre_closure

    report["templates_migrated"].append({"old": old_id, "new": new_id})
    if rt_path.is_file():
        report["runtime_updated"].append(new_id)
    if rp_path.is_file():
        if was_closure_bound:
            report["portability_updated"].append(new_id)
        else:
            report["portability_preserved_invalid"].append(new_id)
    if vj_path.is_file():
        report["verify_updated"].append(new_id)
    if cm_path.is_file():
        report["code_manifest_updated"].append(new_id)
    if acc_path.is_file():
        report["acceptance_updated"].append(new_id)

    if dry_run:
        return

    shutil.move(str(old_folder), str(new_folder))
    write_page(new_md, new_meta, new_body)
    old_md.unlink()

    new_rt = new_folder / "runtime.json"
    if new_rt.is_file():
        rt_data = json.loads(new_rt.read_text(encoding="utf-8"))
        rt_data["id"] = new_id
        _write_json(new_rt, rt_data)

    new_rp = new_folder / "verify" / "runtime-portability.json"
    if new_rp.is_file():
        rp_data = json.loads(new_rp.read_text(encoding="utf-8"))
        rp_data["implementation"] = new_id
        if was_closure_bound:
            post_manifest, issues = read_manifest(new_folder, new_id, "template")
            if post_manifest is None:
                raise RuntimeError(f"Post-migration runtime.json invalid for {new_id}: {issues}")
            post_closure = closure_hash(new_folder, post_manifest["implementations"][0])
            if post_closure is None:
                raise RuntimeError(f"Failed to compute post-migration closure_hash for {new_id}")
            rp_data["closure_hash"] = post_closure
        _write_json(new_rp, rp_data)

    new_vj = new_folder / "verify" / "verify.json"
    if new_vj.is_file():
        vj_data = json.loads(new_vj.read_text(encoding="utf-8"))
        if isinstance(vj_data.get("inputs"), dict):
            vj_data["inputs"] = {
                _rewrite_id_or_path(k, mapping): v for k, v in vj_data["inputs"].items()
            }
        _write_json(new_vj, vj_data)

    new_cm = new_folder / "code-manifest.json"
    if new_cm.is_file():
        cm_data = json.loads(new_cm.read_text(encoding="utf-8"))
        for entry in cm_data.get("files") or []:
            if not isinstance(entry, dict):
                continue
            ver = entry.get("verification")
            if isinstance(ver, dict) and isinstance(ver.get("evidence"), list):
                ver["evidence"] = [
                    _rewrite_id_or_path(ev, mapping) if isinstance(ev, str) else ev
                    for ev in ver["evidence"]
                ]
        _write_json(new_cm, cm_data)

    new_acc = new_folder / "acceptance.json"
    if new_acc.is_file():
        acc_data = json.loads(new_acc.read_text(encoding="utf-8"))
        acc_data["page"] = f"templates/{new_id}.md"
        _write_json(new_acc, acc_data)


def migrate(
    wiki_root: Path,
    *,
    mapping: dict[str, str] | None = None,
    dry_run: bool = True,
) -> dict:
    """Migrate template IDs, receipts, layout manifests, and markdown backlinks."""
    wiki_root = Path(wiki_root)
    active_map = dict(mapping) if mapping is not None else build_mapping()
    pattern = _compile_token_pattern(active_map)

    report: dict = {
        "dry_run": dry_run,
        "wiki_root": str(wiki_root),
        "templates_migrated": [],
        "runtime_updated": [],
        "portability_updated": [],
        "portability_preserved_invalid": [],
        "verify_updated": [],
        "code_manifest_updated": [],
        "acceptance_updated": [],
        "layouts_json_updated": [],
        "pages_updated": [],
        "protected_hashes_updated": 0,
    }

    tdir = wiki_root / "templates"
    for old_id, new_id in active_map.items():
        _migrate_template_assets(
            tdir, old_id, new_id, active_map, pattern, dry_run=dry_run, report=report
        )

    layouts_dir = wiki_root / "layouts"
    if layouts_dir.is_dir():
        for layout_json in sorted(layouts_dir.glob("*/layout.json")):
            data = json.loads(layout_json.read_text(encoding="utf-8"))
            changed = False
            for panel in data.get("panels") or []:
                if isinstance(panel, dict) and panel.get("template") in active_map:
                    panel["template"] = active_map[panel["template"]]
                    changed = True
            if changed:
                report["layouts_json_updated"].append(layout_json.relative_to(wiki_root).as_posix())
                if not dry_run:
                    _write_json(layout_json, data)

    for folder in _REF_DIRS:
        folder_dir = wiki_root / folder
        if not folder_dir.is_dir():
            continue
        for md_path in sorted(folder_dir.glob("*.md")):
            meta, body = read_page(md_path)
            new_meta, meta_changed = _migrate_page_meta(meta, active_map)
            new_body = _replace_outside_protected_blocks(body, pattern, active_map)
            body_changed = new_body != body
            if meta_changed or body_changed:
                report["pages_updated"].append(md_path.relative_to(wiki_root).as_posix())
                if not dry_run:
                    write_page(md_path, new_meta, new_body)

    protected_path = wiki_root / ".protected-hashes.json"
    if protected_path.is_file():
        pdata = json.loads(protected_path.read_text(encoding="utf-8"))
        files = pdata.get("files")
        if isinstance(files, dict):
            new_files: dict = {}
            renamed = 0
            for key, val in sorted(files.items()):
                new_key = _rewrite_id_or_path(key, active_map)
                if new_key != key:
                    renamed += 1
                new_files[new_key] = val
            report["protected_hashes_updated"] = renamed
            if renamed and not dry_run:
                pdata["files"] = new_files
                _write_json(protected_path, pdata)

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migrate 31 v3 template IDs to v4 short slugs")
    parser.add_argument("--wiki-root", type=Path, default=Path(__file__).resolve().parents[2] / "wiki")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Plan migration without writing files (default)")
    mode.add_argument("--apply", action="store_true", help="Apply migration to wiki_root")
    args = parser.parse_args(argv)

    result = migrate(args.wiki_root, dry_run=not args.apply)
    print(json.dumps({
        "dry_run": result["dry_run"],
        "templates_migrated": len(result["templates_migrated"]),
        "runtime_updated": len(result["runtime_updated"]),
        "portability_updated": len(result["portability_updated"]),
        "portability_preserved_invalid": result["portability_preserved_invalid"],
        "verify_updated": len(result["verify_updated"]),
        "code_manifest_updated": len(result["code_manifest_updated"]),
        "acceptance_updated": len(result["acceptance_updated"]),
        "layouts_json_updated": result["layouts_json_updated"],
        "pages_updated": len(result["pages_updated"]),
        "protected_hashes_updated": result["protected_hashes_updated"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
