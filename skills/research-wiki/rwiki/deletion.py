"""Deletion of archived Wiki items, with reference cleanup and an audit record."""
import hashlib
import json
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

import yaml

_YAML_LOADER = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)

from .catalog import build_index, page_paths
from .errors import WikiError
from .links import resolve
from .pages import get_block, parse_page, write_page
from .read_cache import invalidate_cache
from .store import head_revision, incremental_save_scope, save, staged_paths, unstage_new, vault_write_lock


def _parse_bytes(path: Path, data: bytes) -> tuple[dict, str]:
    """Parse a page from an already captured byte snapshot (same rules as read_page)."""
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError as error:
        raise WikiError(f'{path}: 不是 UTF-8 文本') from error
    meta, body, error = parse_page(text)
    if error:
        raise WikiError(f'{path}: {error}')
    return meta, body


def _slot_rank(meta: dict, fallback_id: str) -> tuple:
    """Same ordering as the Gallery's slotItemRank: default, unset, variant; ready first; id."""
    tier = meta.get('style_tier')
    tier_rank = 0 if tier == 'default' else (1 if tier != 'variant' else 2)
    status_rank = 0 if meta.get('status') == 'ready' else 1
    sid = str(meta.get('id') or fallback_id)
    return (tier_rank, status_rank, sid.casefold(), sid)


def _first_chart(meta: dict) -> str:
    charts = meta.get('chart_types')
    if isinstance(charts, list) and charts and charts[0] is not None:
        return str(charts[0]).strip()
    return ''


def prepare(config, page, allow_active: bool = False):
    plan, changes, assets, asset_edits, _ = _prepare(config, page, allow_active=allow_active)
    return plan, changes, assets, asset_edits


def _prepare(config, page, allow_active: bool = False):
    """Plan a deletion from ONE byte snapshot: the revision and every edit derive from it."""
    root = config.wiki_root.resolve()
    page_resolved = page.resolve()
    if page_resolved.parent not in [root / name for name in ('layouts', 'templates', 'methods')]:
        raise WikiError('删除目标不在允许的 Wiki 条目目录')
    assets = page.with_suffix('')
    if assets.exists() and (assets.resolve() != assets.absolute() or not assets.is_dir()):
        raise WikiError('资产目录包含重定向，不能自动删除')
    asset_files = sorted(p for p in assets.rglob('*') if p.is_file()) if assets.exists() else []
    assets_resolved = assets.resolve()
    for p in asset_files:
        if not p.resolve().is_relative_to(assets_resolved):
            raise WikiError('资产路径越出专属目录，不能自动删除')

    all_pages = page_paths(root)
    # Capture every byte the plan depends on exactly once.
    snapshot: dict[Path, bytes] = {}
    for p in sorted(set(all_pages) | set(asset_files)):
        snapshot[p] = p.read_bytes()
    page_bytes = next((data for p, data in snapshot.items() if p.resolve() == page_resolved), None)
    if page_bytes is None:
        page_bytes = page.read_bytes()
    meta, _body = _parse_bytes(page, page_bytes)
    parsed = {p: (meta, _body) if p.resolve() == page_resolved else None for p in all_pages}

    def page_data(p: Path) -> tuple[dict, str]:
        cached = parsed.get(p)
        if cached is None:
            cached = _parse_bytes(p, snapshot[p])
            parsed[p] = cached
        # Callers mutate metadata; never share the parsed object.
        return json.loads(json.dumps(cached[0], ensure_ascii=False, default=str)) if False else _deep(cached[0]), cached[1]

    is_active_template = allow_active and meta.get('type') == 'template' and page_resolved.parent == (root / 'templates')
    if meta.get('status') != 'archived' and not is_active_template:
        raise WikiError('仅已归档条目允许删除')

    deleted_names = {meta['id'], *(a for a in (meta.get('aliases') or []) if isinstance(a, str))}
    kind_dir = page.parent.name
    typed_deleted = {f"{kind_dir}/{name}" for name in deleted_names}
    needle_strs = tuple(sorted({n.lower() for n in deleted_names if n} | {page.stem.lower()}))
    needle_bytes = tuple(n.encode('utf-8') for n in needle_strs)

    def matches_ref(value) -> bool:
        if not isinstance(value, str):
            return False
        norm = value.strip().removesuffix('.md')
        return norm in deleted_names or norm in typed_deleted

    def hits(candidate: Path) -> bool:
        try:
            target = candidate.resolve()
        except (OSError, RuntimeError):
            return False
        return target == page_resolved or target.is_relative_to(assets_resolved)

    def targets(raw: str, base: Path | None = None) -> bool:
        """One typed resolver for wiki links, Markdown destinations and author blocks."""
        raw = raw.split('|', 1)[0].split('#', 1)[0].split('?', 1)[0].strip()
        if not raw:
            return False
        raw_low = raw.lower()
        if not any(n in raw_low for n in needle_strs):
            return False
        candidates = [resolve(root, raw)]
        if base is not None:
            relative = base / raw
            candidates.append(relative)
            if not Path(raw).suffix:
                candidates.append(relative.with_suffix('.md'))
        return any(hits(c) for c in candidates)

    pattern = re.compile(r'(!?)\[\[([^\]\n]+)\]\]')
    bare_names_re = '|'.join(re.escape(n) for n in sorted(deleted_names, key=len, reverse=True))
    bare_pattern = re.compile(
        rf'(?<![A-Za-z0-9_/\-\[(]){re.escape(kind_dir)}/(?:{bare_names_re})(?:/[^\s`\'"\)\]\}}>，,、；;]+)?(?:\.md)?(?=$|[\s`\'"\)\]\}}>.,，、；;])'
    )
    destination = re.compile(r'^(\S+?)(?:\s+(?:"[^"]*"|\'[^\']*\'|\([^)]*\)))?$')

    def clean(text, base: Path | None = None):
        if not text:
            return text
        text_low = text.lower()
        if '%' not in text and not any(n in text_low for n in needle_strs):
            return text
        def replace(m):
            if not targets(m[2], base):
                return m[0]
            label = m[2].split('|', 1)[-1] if '|' in m[2] else meta['title']
            return f'{label}（条目已删除）'
        text = pattern.sub(replace, text)

        def markdown(m):
            raw = m[3].strip()
            if raw.startswith('<') and '>' in raw:
                raw = raw[1:raw.index('>')]
            else:
                found = destination.match(raw)
                raw = found[1] if found else raw
            raw = unquote(raw.strip())
            if raw.startswith('/files/wiki/'):
                raw = raw[len('/files/wiki/'):]
            if '://' in raw or raw.startswith(('/', '#', 'mailto:')):
                return m[0]
            return f'{m[2]}（条目已删除）' if targets(raw, base) else m[0]
        text = re.sub(r'(!?)\[([^\]\n]*)\]\(([^)\n]+)\)', markdown, text)
        return bare_pattern.sub(f"{meta['title']}（条目已删除）", text)

    changes, asset_edits, relation_changes = [], [], {}
    extra_bytes: dict[Path, bytes] = {}

    def block(text, name):
        return get_block(text, name) if f'<!-- {name}:start -->' in text else ''

    for other in all_pages:
        if other == page or other.resolve() == page_resolved:
            continue
        raw_other = snapshot[other]
        raw_other_low = raw_other.lower()
        may_ref_page = (b'%' in raw_other) or any(nb in raw_other_low for nb in needle_bytes)
        blueprint = other.with_suffix('') / 'layout.json'
        may_ref_layout = meta['type'] == 'template' and other.parent.name == 'layouts' and blueprint.is_file()
        if not may_ref_page and not may_ref_layout:
            continue
        om, ob = page_data(other)
        base = other.parent
        # A template's provenance is its source layout; never leave a live template without one.
        if (meta['type'] == 'layout' and om.get('type') == 'template' and om.get('status') != 'archived'
                and isinstance(om.get('layouts'), list)):
            referenced = [x for x in om['layouts'] if matches_ref(x)]
            remaining = [x for x in om['layouts'] if not matches_ref(x)
                         and isinstance(x, str) and x.strip()]
            if referenced and not remaining:
                raise WikiError(f'此来源是模板“{om.get("title", other.stem)}”的唯一出处，不能删除；'
                                '删除后模板将无来源。如需删除，请先归档并删除该模板。')
        if clean(block(ob, 'user'), base) != block(ob, 'user'):
            raise WikiError(f'作者备注引用此条目，请先手动处理：{other.relative_to(root)}')
        original_meta = json.dumps(om, ensure_ascii=False, sort_keys=True, default=str)
        if meta['type'] in ('template', 'layout') and isinstance(om.get('figure_relations'), list):
            deleted_figures = {f"{kind_dir}/{name}" for name in deleted_names}

            def kept_relation(record):
                if not isinstance(record, dict) or not isinstance(record.get('figure'), str):
                    return True
                # Canonical records omit .md. Also clean that legacy/malformed spelling
                # so deletion cannot leave a future dangling declaration.
                return record['figure'].strip().removesuffix('.md') not in deleted_figures

            previous = om['figure_relations']
            om['figure_relations'] = [record for record in previous if kept_relation(record)]
            removed_count = len(previous) - len(om['figure_relations'])
            if removed_count:
                relation_changes[other] = removed_count

        key = {'template': 'templates', 'layout': 'layouts', 'method': 'methods'}[meta['type']]
        if isinstance(om.get(key), list):
            om[key] = [x for x in om[key] if not matches_ref(x)]
        if meta['type'] == 'template' and isinstance(om.get('template_panels'), dict):
            for name in list(om['template_panels']):
                if matches_ref(name):
                    om['template_panels'].pop(name, None)
        if isinstance(om.get('sources'), list):
            om['sources'] = [x for x in om['sources'] if not matches_ref(x)]
        if meta['type'] == 'method' and matches_ref(om.get('primary_method')):
            om.pop('primary_method', None)

        # Nested next_steps cleanup (including the legacy `methods` list).
        if isinstance(om.get('next_steps'), list):
            for step in om['next_steps']:
                if not isinstance(step, dict):
                    continue
                list_keys = (('viz_templates', 'templates') if meta['type'] == 'template'
                             else ('analysis_templates', 'methods') if meta['type'] == 'method' else ())
                for list_key in list_keys:
                    if isinstance(step.get(list_key), list):
                        step[list_key] = [x for x in step[list_key] if not matches_ref(x)]
                if meta['type'] == 'method' and matches_ref(step.get('method_id')):
                    step['method_id'] = ''

        # Nested scenario.picks and scenario.steps cleanup
        if om.get('type') == 'scenario':
            if isinstance(om.get('picks'), list):
                cleaned_picks = []
                for pick in om['picks']:
                    pid = pick.get('id') if isinstance(pick, dict) else pick
                    if not matches_ref(pid):
                        cleaned_picks.append(pick)
                om['picks'] = cleaned_picks
            if isinstance(om.get('steps'), list):
                for step in om['steps']:
                    if not isinstance(step, dict):
                        continue
                    for list_key in ('templates', 'viz_templates'):
                        if isinstance(step.get(list_key), list):
                            step[list_key] = [x for x in step[list_key] if not matches_ref(x)]
                    if meta['type'] == 'method' and isinstance(step.get('methods'), list):
                        step['methods'] = [x for x in step['methods'] if not matches_ref(x)]
                    if meta['type'] == 'method' and matches_ref(step.get('method_id')):
                        step['method_id'] = ''

        blueprint = other.with_suffix('') / 'layout.json'
        if meta['type'] == 'template' and om['type'] == 'layout' and blueprint.is_file():
            raw_blueprint = blueprint.read_bytes()
            layout = json.loads(raw_blueprint.decode('utf-8'))
            removed = {p['letter'] for p in layout['panels'] if matches_ref(p.get('template'))}
            if removed:
                extra_bytes[blueprint] = raw_blueprint
                layout['panels'] = [p for p in layout['panels'] if not matches_ref(p.get('template'))]
                layout['labels'] = [p for p in layout['labels'] if p['text'] not in removed]
                asset_edits.append((blueprint, json.dumps(layout, ensure_ascii=False, indent=2).encode() if layout['panels'] else None))
                if om['status'] == 'ready':
                    om['status'] = 'pending_template'
                if om.get('archived_from') == 'ready':
                    om['archived_from'] = 'pending_template'

        chunks = re.split(r'(<!-- (?:facts|user):start -->.*?<!-- (?:facts|user):end -->)', ob, flags=re.S)
        for i in range(0, len(chunks), 2):
            chunks[i] = clean(chunks[i], base)
        cleaned = ''.join(chunks)
        if (original_meta != json.dumps(om, ensure_ascii=False, sort_keys=True, default=str) or cleaned != ob
                or clean(block(ob, 'facts'), base) != block(ob, 'facts')):
            changes.append((other, om, cleaned))

    # Clean panel-manifest.yaml references (template_id -> null, extra_templates / methods filtered)
    if meta['type'] in ('template', 'method') and (root / 'methods').is_dir():
        for manifest_path in sorted((root / 'methods').glob('*/panel-manifest.yaml')):
            if manifest_path.is_relative_to(assets):
                continue
            try:
                raw_manifest = manifest_path.read_bytes()
                if not any(nb in raw_manifest.lower() for nb in needle_bytes):
                    continue
                manifest_data = yaml.load(raw_manifest.decode('utf-8'), Loader=_YAML_LOADER)
            except (OSError, UnicodeDecodeError, yaml.YAMLError):
                continue
            if not isinstance(manifest_data, dict) or not isinstance(manifest_data.get('panels'), list):
                continue
            manifest_changed = False
            for item in manifest_data['panels']:
                if not isinstance(item, dict):
                    continue
                if meta['type'] == 'template':
                    if matches_ref(item.get('template_id')):
                        item['template_id'] = None
                        manifest_changed = True
                    if isinstance(item.get('extra_templates'), list):
                        filtered = [x for x in item['extra_templates'] if not matches_ref(x)]
                        if filtered != item['extra_templates']:
                            item['extra_templates'] = filtered
                            manifest_changed = True
                elif meta['type'] == 'method' and isinstance(item.get('methods'), list):
                    filtered = [x for x in item['methods'] if not matches_ref(x)]
                    if filtered != item['methods']:
                        item['methods'] = filtered
                        manifest_changed = True
            if manifest_changed:
                extra_bytes[manifest_path] = raw_manifest
                dumped = yaml.safe_dump(manifest_data, allow_unicode=True, sort_keys=False).encode('utf-8')
                asset_edits.append((manifest_path, dumped))

    h = hashlib.sha256()
    # Plan tokens include all pages and target files so a stale UI cannot delete changed content.
    for p in sorted(snapshot):
        h.update(str(p.relative_to(root)).encode())
        h.update(snapshot[p])
    for p, _ in asset_edits:
        h.update(extra_bytes[p])
    snapshot.update(extra_bytes)

    slot_default_warning = None
    if meta.get('type') == 'template' and meta.get('style_tier') == 'default':
        pm = str(meta.get('primary_method') or '').strip()
        primary_chart = _first_chart(meta)
        # A slot exists only when both halves of the key are present (same rule as the Gallery).
        if pm and primary_chart:
            siblings = []
            pm_bytes = pm.encode('utf-8')
            for other in all_pages:
                if other == page or other.resolve() == page_resolved or other.parent.name != 'templates':
                    continue
                if pm_bytes not in snapshot[other]:
                    continue
                try:
                    om, _ = page_data(other)
                except WikiError:
                    continue
                if om.get('type') != 'template' or om.get('status') == 'archived':
                    continue
                if str(om.get('primary_method') or '').strip() != pm:
                    continue
                if _first_chart(om) == primary_chart:
                    siblings.append((_slot_rank(om, other.stem), str(om.get('id') or other.stem)))
            if siblings:
                siblings.sort()
                remaining_ids = [sid for _, sid in siblings]
                recommended = remaining_ids[0]
                slot_default_warning = {
                    'primary_method': pm,
                    'chart_type': primary_chart,
                    'recommended_successor': recommended,
                    'remaining_variants': remaining_ids,
                    'message': (
                        f"该模板当前为输出槽位 ({pm} × {primary_chart}) 的主推默认（style_tier: default），"
                        f"删除后同槽位仍有 {len(remaining_ids)} 个活跃变体；建议将 {recommended} 设为新的 default。"
                    ),
                }

    plan = {'title': meta['title'], 'path': page.relative_to(root).as_posix() if page.is_relative_to(root) else page_resolved.relative_to(root).as_posix(),
            'revision': h.hexdigest(), 'asset_files': len(asset_files),
            'affected': [{'path': p.relative_to(root).as_posix(), 'title': m['title'],
                          'figure_relations_removed': relation_changes.get(p, 0)} for p, m, _ in changes],
            'figure_relations_removed': sum(relation_changes.values()),
            'layout_files_updated': [p.relative_to(root).as_posix() for p, _ in asset_edits],
            'slot_default_warning': slot_default_warning,
            'gallery_preserved': True}
    return plan, changes, assets, asset_edits, snapshot


def _deep(value):
    import copy
    return copy.deepcopy(value)


def delete_archived(config, page, revision, allow_active: bool = False):
    root = config.wiki_root.resolve()
    # Hold the vault write lock from planning through commit: no in-process writer
    # can land between the revision check and the writes.
    with vault_write_lock(root):
        plan, changes, assets, asset_edits, snapshot = _prepare(config, page, allow_active=allow_active)
        if plan['revision'] != revision:
            raise WikiError('内容或关联已变化，请重新查看删除范围后确认')
        # Recheck the affected bytes right before writing (another process may have written).
        for p in [page, *(p for p, _, _ in changes), *(p for p, _ in asset_edits)]:
            expected = snapshot.get(p)
            if expected is None:
                expected = next((data for q, data in snapshot.items() if q.resolve() == p.resolve()), None)
            if expected is None or not p.is_file() or p.read_bytes() != expected:
                raise WikiError('内容或关联已变化，请重新查看删除范围后确认')
        return _apply_deletion(config, root, page, plan, changes, assets, asset_edits, snapshot, allow_active)


def _apply_deletion(config, root, page, plan, changes, assets, asset_edits, snapshot, allow_active):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    audit = root / 'deletion-records' / f'{stamp}-{page.stem}.json'
    index_path = root / 'index.md'
    catalog_path = root / 'catalog.jsonl'
    log_path = root / 'log.md'
    staged_before = staged_paths(root)
    head_before = head_revision(root) if staged_before is not None else None
    with tempfile.TemporaryDirectory(prefix='wiki-delete-') as tmp:
        backup = Path(tmp)
        shutil.copy2(page, backup / 'page.md')
        if assets.exists():
            shutil.copytree(assets, backup / 'assets')
        originals = {p: p.read_bytes() for p, _, _ in changes}
        asset_originals = {p: p.read_bytes() for p, _ in asset_edits}
        # Facts refresh may rewrite pages outside the planned set: journal all of them.
        page_originals = {p: data for p, data in snapshot.items() if p.suffix == '.md' and p.parent.parent == root}
        derived_originals = {p: (p.read_bytes() if p.is_file() else None)
                             for p in (index_path, catalog_path, log_path)}
        try:
            for p, meta, body in changes:
                write_page(p, meta, body)
            for p, content in asset_edits:
                if content is None:
                    p.unlink()
                else:
                    p.write_bytes(content)
            page.unlink()
            if assets.exists():
                shutil.rmtree(assets)
            audit.parent.mkdir(exist_ok=True)
            audit.write_text(json.dumps({**plan, 'deleted_at': stamp,
                'changed_pages': [{'path': p.relative_to(root).as_posix(),
                    'before_sha256': hashlib.sha256(originals[p]).hexdigest(),
                    'after_sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p, _, _ in changes],
                'changed_layout_files': [{'path': p.relative_to(root).as_posix(),
                    'before_sha256': hashlib.sha256(content).hexdigest(),
                    'after_sha256': hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None} for p, content in asset_originals.items()]},
                ensure_ascii=False, indent=2), encoding='utf-8')
            # Incremental save: refresh facts & catalog only for the affected pages + deleted entry.
            affected_paths = {p for p, _, _ in changes}
            with incremental_save_scope(affected_paths, {plan['path']}):
                save(config, f"delete {'template' if allow_active else 'archived'} {page.stem}; cleaned {len(changes)} references")
            invalidate_cache(root)
        except BaseException:
            committed = staged_before is not None and head_revision(root) != head_before
            if not committed:
                _rollback(root, page, assets, backup, page_originals, originals, asset_originals,
                          derived_originals, audit)
                unstage_new(root, staged_before)
            invalidate_cache(root)
            raise
    return {**plan, 'deleted': True, 'audit': audit.relative_to(root).as_posix()}


def _rollback(root, page, assets, backup, page_originals, originals, asset_originals, derived_originals, audit):
    shutil.copy2(backup / 'page.md', page)
    if (backup / 'assets').exists():
        shutil.copytree(backup / 'assets', assets, dirs_exist_ok=True)
    for p, content in {**page_originals, **originals}.items():
        try:
            if not p.is_file() or p.read_bytes() != content:
                p.write_bytes(content)
        except OSError:
            p.write_bytes(content)
    for p, content in asset_originals.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
    for p, content in derived_originals.items():
        if content is None:
            p.unlink(missing_ok=True)
        else:
            p.write_bytes(content)
    audit.unlink(missing_ok=True)
