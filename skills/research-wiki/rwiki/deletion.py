"""Deletion of archived Wiki items, with reference cleanup and an audit record."""
import hashlib
import json
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

from .catalog import page_paths
from .errors import WikiError
from .links import resolve
from .pages import get_block, read_page, write_page
from .store import save


def prepare(config, page):
    root = config.wiki_root.resolve()
    meta, body = read_page(page)
    if meta.get('status') != 'archived':
        raise WikiError('仅已归档条目允许删除')
    assets = page.with_suffix('')
    if page.resolve().parent not in [root / name for name in ('layouts', 'templates', 'methods')]:
        raise WikiError('删除目标不在允许的 Wiki 条目目录')
    if assets.exists() and (assets.resolve() != assets.absolute() or not assets.is_dir()):
        raise WikiError('资产目录包含重定向，不能自动删除')
    asset_files = sorted(p for p in assets.rglob('*') if p.is_file()) if assets.exists() else []
    for p in asset_files:
        if not p.resolve().is_relative_to(assets.resolve()):
            raise WikiError('资产路径越出专属目录，不能自动删除')
    def targets(raw):
        target = resolve(root, raw.split('|', 1)[0].split('#', 1)[0].strip()).resolve()
        return target == page.resolve() or target.is_relative_to(assets.resolve())
    pattern = re.compile(r'(!?)\[\[([^\]\n]+)\]\]')
    def clean(text):
        def replace(m):
            if not targets(m[2]): return m[0]
            label = m[2].split('|', 1)[-1] if '|' in m[2] else meta['title']
            return f'{label}（条目已删除）'
        text = pattern.sub(replace, text)
        def markdown(m):
            raw = unquote(m[3].strip().strip('<>'))
            if raw.startswith('/files/wiki/'): raw = raw[len('/files/wiki/'):]
            if '://' in raw or raw.startswith(('/', '#')): return m[0]
            return f'{m[2]}（条目已删除）' if targets(raw) else m[0]
        return re.sub(r'(!?)\[([^\]\n]*)\]\(([^)\n]+)\)', markdown, text)
    changes, asset_edits, relation_changes = [], [], {}
    def block(text, name):
        return get_block(text, name) if f'<!-- {name}:start -->' in text else ''
    for other in page_paths(root):
        if other == page: continue
        om, ob = read_page(other)
        # A template's provenance is its source layout; never leave a live template without one.
        if (meta['type'] == 'layout' and om.get('type') == 'template' and om.get('status') != 'archived'
                and isinstance(om.get('layouts'), list) and om['layouts'] == [meta['id']]):
            raise WikiError(f'此来源是模板“{om.get("title", other.stem)}”的唯一出处，不能删除；'
                            '删除后模板将无来源。如需删除，请先归档并删除该模板。')
        if clean(block(ob, 'user')) != block(ob, 'user'):
            raise WikiError(f'作者备注引用此条目，请先手动处理：{other.relative_to(root)}')
        original_meta = json.dumps(om, ensure_ascii=False, sort_keys=True)
        if meta['type'] in ('template', 'layout') and isinstance(om.get('figure_relations'), list):
            deleted_figure = page.relative_to(root).with_suffix('').as_posix()
            def kept_relation(record):
                if not isinstance(record, dict) or not isinstance(record.get('figure'), str):
                    return True
                # Canonical records omit .md. Also clean that legacy/malformed spelling
                # so deletion cannot leave a future dangling declaration.
                return record['figure'].removesuffix('.md') != deleted_figure
            previous = om['figure_relations']
            om['figure_relations'] = [record for record in previous if kept_relation(record)]
            removed_count = len(previous) - len(om['figure_relations'])
            if removed_count:
                relation_changes[other] = removed_count
        key = {'template': 'templates', 'layout': 'layouts', 'method': 'methods'}[meta['type']]
        if isinstance(om.get(key), list): om[key] = [x for x in om[key] if x != meta['id']]
        if meta['type'] == 'template' and isinstance(om.get('template_panels'), dict):
            om['template_panels'].pop(meta['id'], None)
        blueprint = other.with_suffix('') / 'layout.json'
        if meta['type'] == 'template' and om['type'] == 'layout' and blueprint.is_file():
            layout = json.loads(blueprint.read_text(encoding='utf-8'))
            removed = {p['letter'] for p in layout['panels'] if p['template'] == meta['id']}
            if removed:
                layout['panels'] = [p for p in layout['panels'] if p['template'] != meta['id']]
                layout['labels'] = [p for p in layout['labels'] if p['text'] not in removed]
                asset_edits.append((blueprint, json.dumps(layout, ensure_ascii=False, indent=2).encode() if layout['panels'] else None))
                if om['status'] == 'ready': om['status'] = 'pending_template'
                if om.get('archived_from') == 'ready': om['archived_from'] = 'pending_template'
        chunks = re.split(r'(<!-- (?:facts|user):start -->.*?<!-- (?:facts|user):end -->)', ob, flags=re.S)
        for i in range(0, len(chunks), 2): chunks[i] = clean(chunks[i])
        cleaned = ''.join(chunks)
        if original_meta != json.dumps(om, ensure_ascii=False, sort_keys=True) or cleaned != ob or clean(block(ob, 'facts')) != block(ob, 'facts'):
            changes.append((other, om, cleaned))
    h = hashlib.sha256()
    # Plan tokens include all pages and target files so a stale UI cannot delete changed content.
    for p in sorted(set(page_paths(root)) | set(asset_files)):
        h.update(str(p.relative_to(root)).encode()); h.update(p.read_bytes())
    for p, _ in asset_edits: h.update(p.read_bytes())
    plan = {'title': meta['title'], 'path': page.relative_to(root).as_posix(),
            'revision': h.hexdigest(), 'asset_files': len(asset_files),
            'affected': [{'path': p.relative_to(root).as_posix(), 'title': m['title'],
                          'figure_relations_removed': relation_changes.get(p, 0)} for p, m, _ in changes],
            'figure_relations_removed': sum(relation_changes.values()),
            'layout_files_updated': [p.relative_to(root).as_posix() for p, _ in asset_edits],
            'gallery_preserved': True}
    return plan, changes, assets, asset_edits


def delete_archived(config, page, revision):
    plan, changes, assets, asset_edits = prepare(config, page)
    if plan['revision'] != revision:
        raise WikiError('内容或关联已变化，请重新查看删除范围后确认')
    root = config.wiki_root.resolve()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    audit = root / 'deletion-records' / f'{stamp}-{page.stem}.json'
    with tempfile.TemporaryDirectory(prefix='wiki-delete-') as tmp:
        backup = Path(tmp)
        shutil.copy2(page, backup / 'page.md')
        if assets.exists(): shutil.copytree(assets, backup / 'assets')
        originals = {p: p.read_bytes() for p, _, _ in changes}
        asset_originals = {p: p.read_bytes() for p, _ in asset_edits}
        try:
            for p, meta, body in changes: write_page(p, meta, body)
            for p, content in asset_edits:
                if content is None: p.unlink()
                else: p.write_bytes(content)
            page.unlink()
            if assets.exists(): shutil.rmtree(assets)
            from .facts import refresh_facts
            refresh_facts(config)
            audit.parent.mkdir(exist_ok=True)
            audit.write_text(json.dumps({**plan, 'deleted_at': stamp,
                'changed_pages': [{'path': p.relative_to(root).as_posix(),
                    'before_sha256': hashlib.sha256(originals[p]).hexdigest(),
                    'after_sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p, _, _ in changes],
                'changed_layout_files': [{'path': p.relative_to(root).as_posix(),
                    'before_sha256': hashlib.sha256(content).hexdigest(),
                    'after_sha256': hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None} for p, content in asset_originals.items()]},
                ensure_ascii=False, indent=2), encoding='utf-8')
            save(config, f"delete archived {page.stem}; cleaned {len(changes)} references")
        except Exception:
            shutil.copy2(backup / 'page.md', page)
            if (backup / 'assets').exists(): shutil.copytree(backup / 'assets', assets, dirs_exist_ok=True)
            for p, content in originals.items(): p.write_bytes(content)
            for p, content in asset_originals.items(): p.write_bytes(content)
            audit.unlink(missing_ok=True)
            raise
    return {**plan, 'deleted': True, 'audit': audit.relative_to(root).as_posix()}
