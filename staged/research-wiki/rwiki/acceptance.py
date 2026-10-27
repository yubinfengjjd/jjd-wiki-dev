"""Shared mechanical gates; semantic review and author approval stay distinct."""
import hashlib
import json
import re
from datetime import datetime, timezone

from .errors import WikiError
from .pages import read_page, section_bounds, section_text, set_block
from .verification import replay_available

HEADINGS = {
    'method': ('用途', '适用', '不适用', '输入', '怎么做', '代码', '输出', '知识关联检查'),
    'template': ('适用', '不适用', '知识关联检查'),
    'layout': ('适用', '不适用', '知识关联检查'),
    'recipe': ('用途', '适用', '不适用', '输入', '怎么用', '输出', '知识关联检查'),
}

# A section whose first meaningful line is a placeholder is still unfinished,
# even when an explanation follows (e.g. "TODO：补充数据").
_PLACEHOLDER = re.compile(
    r'^(?:TODO|TBD|待(?:补充|完善|作者确认)|模板化后生成)(?:[ \t]*[:：]|[。.!！]|$)',
    re.I,
)


def _is_placeholder(content: str) -> bool:
    text = content.strip()
    if not text:
        return True
    first = next((line.strip() for line in text.splitlines() if line.strip()), '')
    return bool(_PLACEHOLDER.match(first))


def entry_errors(config, path, *, replay=True) -> list[str]:
    from .lint import metadata_errors
    from .relations import relation_errors
    from .interfaces import load_interface
    from .spec import load_spec
    try:
        meta, body = read_page(path)
        errors = metadata_errors(meta)
        for heading in HEADINGS.get(meta.get('type'), ()):
            try:
                content = section_text(body, heading).strip()
            except WikiError:
                content = ''
            if _is_placeholder(content):
                errors.append(f'{heading}节尚未完成')
        if meta.get('type') == 'method':
            errors.extend(relation_errors(config, meta))
            for slug in meta.get('inputs', []) + meta.get('outputs', []):
                load_interface(config.wiki_root, slug)
        if meta.get('type') == 'template':
            load_spec(path.with_suffix(''))
            if replay and not replay_available(path.with_suffix('')):
                errors.append('缺少当前版本的完整成功回放，请 verify-template')
        if meta.get('type') == 'recipe':
            from .recipes import integrity_errors, recipe_errors
            errors.extend(recipe_errors(config, path, meta) if replay else integrity_errors(path))
        return errors
    except (WikiError, OSError, ValueError, KeyError, TypeError) as error:
        return [str(error)]


def _without_usage_links(body: str) -> str:
    """Ignore generated record-use links; they are logs, not note content.

    The stored receipt must stay valid when the author records a use.  Removing
    the exact line that ``record_use`` appends (plus its separating blank line)
    restores the pre-use body byte for byte.
    """
    try:
        start, end = section_bounds(body, '使用记录')
    except WikiError:
        return body
    content = body[start:end]
    content = re.sub(r'(?m)^- \d{4}-\d{2}-\d{2} \[\[projects/[^\]]+\]\][ \t]*\r?\n(?:[ \t]*\r?\n)?',
                     '', content)
    return body[:start] + content + body[end:]


def snapshot(path) -> str:
    meta, body = read_page(path)
    # Preference edits and author notes are not agent content or execution input.
    meta = {k: v for k, v in meta.items() if k not in ('status', 'favorite', 'tags', 'archived_from')}
    for block in ('facts', 'user'):
        body = set_block(body, block, '')
    # A usage link appended by record-use must not stale the acceptance receipt.
    body = _without_usage_links(body)
    content = {'meta': meta, 'body': body}
    # Method approval covers knowledge, while per-implementation receipts cover code.
    for folder in (('source',) if meta.get('type') == 'method' else ('source', 'code')):
        content[folder] = {p.relative_to(path.with_suffix('')).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted((path.with_suffix('') / folder).rglob('*'))
                           if p.is_file() and p.resolve().is_relative_to(path.with_suffix('').resolve())
                           and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')}
    return hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def record_acceptance(config, path) -> dict:
    errors = entry_errors(config, path)
    if errors:
        raise WikiError('入库验收未通过：' + '；'.join(errors))
    meta, _ = read_page(path)
    record = {'schema_version': 1, 'checked_at': datetime.now(timezone.utc).isoformat(),
              'page': path.relative_to(config.wiki_root).as_posix(), 'snapshot': snapshot(path),
              'checks': {heading: 'present_nonplaceholder' for heading in HEADINGS[meta['type']]},
              'replay': 'current_inputs_outputs' if meta['type'] == 'template' else 'not_required',
              'scope': '结构、笔记完整性和已声明关联检查；不替代科学语义审查、作者确认或真实课题验证'}
    target = path.with_suffix('') / 'acceptance.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return record


def acceptance_stale(path) -> bool:
    """For a ready page: True when its receipt is missing, unreadable or no longer matches."""
    target = path.with_suffix('') / 'acceptance.json'
    if not target.is_file():
        # Every ready entry now carries a receipt; a missing one is lost evidence, not a pass.
        return True
    try:
        return json.loads(target.read_text(encoding='utf-8')).get('snapshot') != snapshot(path)
    except (WikiError, OSError, ValueError, KeyError, TypeError):
        return True


def ready_for_use(config, path, meta=None) -> bool:
    if meta is None:
        meta, _ = read_page(path)
    if (meta.get('status') != 'ready' or entry_errors(config, path)
            or acceptance_stale(path)):
        return False
    if meta['type'] == 'method':
        from .method_implementations import verified_implementations
        return meta.get('method_kind') == 'analysis' and bool(verified_implementations(path, meta))
    if meta['type'] == 'layout':
        from .templates import layout_ready_errors
        if layout_ready_errors(config, meta):
            return False
        for tid in meta.get('templates', []):
            template_path = config.wiki_root / 'templates' / f'{tid}.md'
            try:
                template, _ = read_page(template_path)
            except (WikiError, OSError):
                return False
            if not ready_for_use(config, template_path, template):
                return False
    return True
