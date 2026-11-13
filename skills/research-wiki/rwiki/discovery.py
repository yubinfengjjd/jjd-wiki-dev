"""Read-only opportunity discovery across canonical method notes.

``discover_methods`` lists analysis notes with their *unverified* branches and
gaps next to the ready ones — it surfaces research opportunities. It never
changes ``suggest_methods`` semantics and never marks an item executable:
``executable`` is exactly ``ready_for_use``, and library gaps stay
non-executable candidates. Archived, workflow and technical notes are context,
not candidates.
"""
from __future__ import annotations

from .acceptance import ready_for_use
from .config import Config
from .errors import WikiError
from .method_implementations import implementation_status
from .pages import read_page, section_text

SCOPE_NOTE = ('机会清单：列出规范 analysis 笔记（含未验证分支与缺口）；'
              'executable 仅当页面当前 ready_for_use 才为真，机会不是可执行推荐，'
              '执行前仍须逐项核查课题前提、分支收据与环境。')

_STATES = ('verified', 'not_run', 'stale', 'invalid')


def _section(body: str, title: str) -> str:
    try:
        return section_text(body, title)
    except WikiError:
        return ''


def _candidate(config: Config, path, meta: dict, body: str, query: str) -> dict:
    statuses = implementation_status(path, meta)
    by_state = {state: [item['id'] for item in statuses if item['state'] == state]
                for state in _STATES}
    declared = {item['id'] for item in statuses}
    undeclared = [item.get('id', '?') for item in meta.get('implementations', [])
                  if isinstance(item, dict) and item.get('id') not in declared]
    executable = meta.get('status') == 'ready' and ready_for_use(config, path, meta)
    gaps = []
    if not statuses and not meta.get('implementations'):
        gaps.append('未声明任何实现分支')
    if not by_state['verified']:
        gaps.append('无 verified 实现分支')
    for state in ('not_run', 'stale', 'invalid'):
        if by_state[state]:
            gaps.append(f'{state}: {"、".join(by_state[state])}')
    if undeclared:
        gaps.append('实现元数据异常: ' + '、'.join(undeclared))
    if meta.get('status') != 'ready':
        gaps.append(f'页面状态 {meta.get("status")}（非 ready）')
    searchable = '\n'.join([meta.get('title', ''), *(meta.get('tags') or []),
                            _section(body, '适用'), _section(body, '用途'),
                            _section(body, '输入')]).casefold()
    score, reasons = 0, []
    for word in dict.fromkeys(query.casefold().split()):
        if word in searchable:
            score += 1
            reasons.append(f'关键词匹配：{word}')
    return {'id': meta.get('id', path.stem), 'title': meta.get('title', path.stem),
            'page': path.relative_to(config.wiki_root).as_posix(),
            'status': meta.get('status'), 'method_kind': meta.get('method_kind'),
            'tags': meta.get('tags') or [], 'purposes': meta.get('purposes') or [],
            'executable': executable,
            'readiness': {'page_ready': meta.get('status') == 'ready',
                          **by_state, 'undeclared': undeclared},
            'gaps': gaps, 'score': score, 'reasons': reasons,
            'inputs': meta.get('inputs') or [], 'outputs': meta.get('outputs') or [],
            'applicable': _section(body, '适用')}


def discover_methods(config: Config, query: str = '', limit: int = 20) -> dict:
    """Inventory all analysis notes — verified and unverified alike.

    The caller still owes per-branch verification and project review; this list
    is an opportunity surface, not an executable plan.
    """
    if limit < 0:
        raise WikiError('--limit 不能为负数')
    candidates, context_only, archived = [], [], 0
    for path in sorted((config.wiki_root / 'methods').glob('*.md')):
        try:
            meta, body = read_page(path)
        except WikiError:
            continue
        if meta.get('status') == 'archived':
            archived += 1
            continue
        kind = meta.get('method_kind')
        # Only canonical analysis notes are candidates; unclassified notes with
        # implementations are still context, never silently promoted.
        if kind == 'analysis':
            candidates.append(_candidate(config, path, meta, body, query))
        else:
            context_only.append({'id': meta.get('id', path.stem),
                                 'title': meta.get('title', path.stem),
                                 'page': path.relative_to(config.wiki_root).as_posix(),
                                 'status': meta.get('status'), 'method_kind': kind,
                                 'note': 'workflow/technical/未分类资料仅为上下文，不作候选'})
    candidates.sort(key=lambda item: (item['executable'] is not True, -item['score'],
                                      item['title'], item['id']))
    return {'candidates': candidates[:limit],
            'context_only': context_only,
            'excluded': {'archived': archived},
            'scope_note': SCOPE_NOTE}
