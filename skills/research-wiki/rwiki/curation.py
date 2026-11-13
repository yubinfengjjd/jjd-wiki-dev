"""Author visual choices, separate from source bytes and scientific acceptance."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from urllib.parse import urlencode

from .config import Config
from .errors import WikiError
from .pages import read_page
from .read_cache import read_session, remember

FILE = 'figureya-curation.json'
STATES = {'pending', 'kept', 'removed', 'later'}
IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
LOCK = RLock()


class StaleDecision(WikiError):
    pass


def state_file(config):
    return config.wiki_root / 'sources' / FILE


def decisions(config):
    def read():
        path = state_file(config)
        if not path.exists():
            return {}
        try:
            value = json.loads(path.read_text(encoding='utf-8'))
            if value.get('schema_version') != 1 or not isinstance(value.get('decisions'), dict):
                raise ValueError('schema')
            result = value['decisions']
            if any(not isinstance(v, dict) or v.get('decision') not in STATES for v in result.values()):
                raise ValueError('decision')
            return result
        except (ValueError, TypeError, AttributeError) as error:
            raise WikiError('FigureYa 筛选记录损坏，请从 Git 历史恢复；未覆盖已有记录') from error
    return remember(('figureya-decisions', config.wiki_root), read)


def revision(config):
    return hashlib.sha256(json.dumps(decisions(config), sort_keys=True).encode()).hexdigest()


def removed_ids(config):
    return {key for key, value in decisions(config).items() if value['decision'] == 'removed'}


def excluded_paths(config):
    def collect():
        removed = removed_ids(config)
        if not removed:
            return set()
        from .catalog import readable_pages
        entries = list(readable_pages(config.wiki_root))
        hidden = set()
        for path, meta in entries:
            source = meta.get('source') or {}
            if meta.get('type') == 'recipe' and f"{source.get('id')}:{source.get('item')}" in removed:
                hidden.add(path.relative_to(config.wiki_root).as_posix())
        for path, meta in entries:
            if meta.get('type') == 'template' and any(
                str(p).removesuffix('.md') + '.md' in hidden for p in meta.get('sources') or []
            ):
                hidden.add(path.relative_to(config.wiki_root).as_posix())
        return hidden
    return remember(('figureya-excluded', config.wiki_root), collect)


def filter_records(config, records):
    removed, hidden = removed_ids(config), excluded_paths(config)
    result = []
    for original in records:
        if original.get('id') in removed or original.get('source') in removed or original.get('page') in hidden:
            continue
        record = dict(original)
        if record.get('kind') == 'scenario':
            record['picks'] = visible_picks(config, record.get('picks', []))
        result.append(record)
    return result


def visible_picks(config, picks):
    hidden = excluded_paths(config)
    blocked = removed_ids(config) | {Path(p).stem for p in hidden} | hidden | {p.removesuffix('.md') for p in hidden}
    return [p for p in picks if (p.get('id') if isinstance(p, dict) else p) not in blocked]


def visible_meta(config, meta):
    if meta.get('type') == 'scenario':
        return {**meta, 'picks': visible_picks(config, meta.get('picks') or [])}
    return meta


def source_items(config):
    from .sources import read_items
    from .catalog import readable_pages
    result = []
    for _, meta in readable_pages(config.wiki_root):
        if meta.get('type') == 'source' and meta.get('adapter') == 'figureya':
            for item in read_items(config, meta['id']):
                if item.get('id') == f"{meta['id']}:{item.get('item')}":
                    result.append((meta, item))
    return result


def image_path(config, identity, relative):
    from .sources import load_source, find_item, snapshot_dir, SOURCE_ID
    sid, name = identity.split(':', 1)
    if not SOURCE_ID.fullmatch(sid):
        raise WikiError('来源 ID 无效')
    meta, _ = load_source(config, sid)
    if meta.get('adapter') != 'figureya' or not config.sources_root:
        raise WikiError('来源不是 FigureYa')
    find_item(config, sid, name)
    base = snapshot_dir(config, meta).resolve()
    value = Path(relative)
    if value.is_absolute() or '..' in value.parts or any(p.startswith('.') for p in value.parts):
        raise WikiError('图片路径无效')
    path = (base / value).resolve()
    module = (base / name).resolve()
    gallery = base / 'gallery_compress'
    if not path.is_relative_to(base) or not path.is_file() or path.suffix.lower() not in IMAGE_EXT:
        raise WikiError('图片不存在')
    if not (path.is_relative_to(module) or (path.parent == gallery and path.stem == name)):
        raise WikiError('图片不属于此模块')
    return path


def local_images(config, source, item):
    from .sources import snapshot_dir
    if not config.sources_root:
        return []
    base = snapshot_dir(config, source)
    module = base / item['item']
    candidates = [base / 'gallery_compress' / (item['item'] + '.webp')]
    if module.is_dir():
        candidates += sorted((p for p in module.rglob('*') if p.is_file() and p.suffix.lower() in IMAGE_EXT
                              and len(p.relative_to(module).parts) <= 4),
                             key=lambda p: (p.stem.lower() != 'example', len(p.parts), p.name))
    images, seen = [], set()
    for path in candidates:
        if not path.is_file() or path in seen:
            continue
        seen.add(path)
        relative = path.relative_to(base).as_posix()
        if (not path.resolve().is_relative_to(base.resolve())
                or any(p.startswith('.') for p in Path(relative).parts)):
            continue
        images.append({'url': '/api/figureya/image?' + urlencode({'id': item['id'], 'path': relative}),
                       'label': '本地来源参考图', 'name': path.name})
    return images


def inventory(config):
    from .finder import _item_record
    from .catalog import readable_pages
    selected, recipes = decisions(config), {}
    for path, meta in readable_pages(config.wiki_root):
        if meta.get('type') == 'recipe':
            source = meta.get('source') or {}
            recipes.setdefault(f"{source.get('id')}:{source.get('item')}", []).append({
                'id': meta['id'], 'title': meta['title'], 'status': meta.get('status'),
                'page': path.relative_to(config.wiki_root).as_posix()})
    records = []
    for source, item in source_items(config):
        record = _item_record(item, source)
        images = local_images(config, source, item)
        if not images and record['thumb']:
            images = [{'url': record['thumb'], 'label': '上游来源参考图', 'name': '上游参考图'}]
        record.update(decision=selected.get(item['id'], {}).get('decision', 'pending'), images=images,
                      recipes=recipes.get(item['id'], []), source_id=source['id'])
        records.append(record)
    def order(record):
        match = re.search(r'FigureYa(\d+)', record['id'])
        return record['source_id'], int(match[1]) if match else 99999, record['id']
    return {'items': sorted(records, key=order), 'revision': revision(config)}


def update(config, ids, decision, expected_revision):
    from .store import guarded, save
    from .catalog import readable_pages
    with LOCK:
        if decision not in STATES or not ids or len(ids) != len(set(ids)):
            raise WikiError('筛选状态或模块列表无效')
        if revision(config) != expected_revision:
            raise StaleDecision('筛选记录已在其他页面更新，请刷新后重试')
        known = {item['id'] for _, item in source_items(config)}
        if set(ids) - known:
            raise WikiError('列表中含不存在的 FigureYa 模块，未保存任何更改')
        data = dict(decisions(config))
        now = datetime.now(timezone.utc).isoformat(timespec='seconds')
        for identity in ids:
            data[identity] = {'decision': decision, 'updated_at': now}
        path = state_file(config)
        path.parent.mkdir(parents=True, exist_ok=True)
        # save refreshes generated facts on other pages before committing. Restore
        # those exact bytes too if a later step fails; author blocks stay intact.
        watched = [p for p, _ in readable_pages(config.wiki_root)]
        with guarded(config, path, config.wiki_root / 'catalog.jsonl',
                     config.wiki_root / '.gitignore', *watched):
            path.write_text(json.dumps({'schema_version': 1, 'decisions': data}, ensure_ascii=False, indent=2) + '\n',
                            encoding='utf-8', newline='\n')
            # Start AFTER writing, so cached filtering sees this new decision.
            # One transaction shares reads; the next click gets a fresh snapshot.
            with read_session():
                save(config, f'FigureYa visual selection: {decision} ({len(ids)} modules)')
        return {'revision': revision(config), 'decisions': {key: data[key]['decision'] for key in ids}}
