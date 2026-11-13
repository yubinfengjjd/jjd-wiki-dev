"""Project-local state and evidence layer.

Layout under a project directory::

    <project>/wiki-use/_project/
      project.json          single state file: revision, entities, objects,
                            observations, routes, tasks, artifacts, runs,
                            decisions/authorizations, lessons, events
      summary.md            derived hand-off summary (rebuilt on every write)
      project.lock          single-writer lock file
      routes/<id>.md        one readable card per research route
      runs/<run_id>/        immutable run receipts and logs
      lessons/              lesson drafts (filled by later batches)

Rules this module enforces:

- Single writer: an O_EXCL lock plus optimistic ``expected_revision`` checks;
  writes validate the whole state before ``os.replace`` commits them, so a
  failed update never leaves half state.
- Three evidence bases stay separate: ``verified`` / ``author_stated`` /
  ``unknown``. Work status, result freshness, implementation verification and
  scientific interpretation are different axes and never alias each other.
- Paths are project-relative, or absolute only inside a data root the author
  registered. Nothing here writes to or scans the Wiki; no ``save`` is called.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath

from .errors import WikiError

SCHEMA_VERSION = 1
STATE_DIR = Path('wiki-use') / '_project'
STATE_FILE = 'project.json'
SUMMARY_FILE = 'summary.md'
LOCK_FILE = 'project.lock'

BASES = ('verified', 'author_stated', 'unknown')
OBSERVATION_VALUES = ('true', 'false', 'unknown')
WORK_STATUSES = ('planned', 'running', 'completed', 'failed', 'blocked', 'skipped')
RUN_STATUSES = ('running', 'completed', 'failed', 'blocked', 'skipped')
ROLES = ('main', 'exploratory', 'support')
DECISION_KINDS = ('route', 'scope', 'authorization', 'budget', 'other')
FRESHNESS = ('current', 'stale', 'unknown')

_SAFE_ID = re.compile(r'[a-z0-9][a-z0-9_-]*')
_KIND_PREFIXES = ('object', 'entity', 'artifact', 'observation', 'task', 'route',
                  'decision', 'authorization', 'run', 'file', 'external')


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _check_id(value, what='id') -> str:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise WikiError(f'{what} 只允许小写字母/数字/_/- 的安全标识: {value!r}')
    return value


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _require_text(value, what) -> str:
    if not _text(value):
        raise WikiError(f'{what} 必须为非空字符串')
    return value.strip()


_SHA_CHUNK = 1 << 20  # 1 MiB read block


def _sha(path: Path, chunk_size: int = _SHA_CHUNK) -> str:
    """Full-file SHA-256 streamed in bounded chunks.

    Multi-GB models/volumes/MS files are hashed without loading them into RAM;
    the digest is always over the complete file bytes — never a size or
    timestamp shortcut.
    """
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b''):
            digest.update(chunk)
    return digest.hexdigest()


def state_dir(root: Path) -> Path:
    return Path(root) / STATE_DIR


# ---------------------------------------------------------------- paths

def project_path(root: Path, value: str, what='路径') -> Path:
    """Resolve a project-relative path; escaping the project is an error."""
    if not _text(value):
        raise WikiError(f'{what}须为非空字符串')
    if '\\' in value or ':' in value:
        raise WikiError(f'{what}须为正斜杠相对路径: {value}')
    part = PurePosixPath(value)
    if (part.is_absolute() or PureWindowsPath(value).anchor
            or any(p in ('', '.', '..') or p.startswith('.') for p in part.parts)):
        raise WikiError(f'{what}不可越界、重复分隔或指向隐藏段: {value}')
    root_resolved = Path(root).resolve()
    path = root_resolved.joinpath(*part.parts).resolve()
    if not path.is_relative_to(root_resolved):
        raise WikiError(f'{what}越过课题目录: {value}')
    return path


def _registered_roots(state: dict) -> list[Path]:
    return [Path(item['path']).resolve() for item in state.get('data_roots', [])]


def external_path(state: dict, value: str, what='外部路径') -> Path:
    """Absolute paths are allowed only inside an author-registered data root."""
    if not _text(value):
        raise WikiError(f'{what}须为非空字符串')
    raw = Path(value)
    # Reject non-absolute input BEFORE resolve(): a relative string must never be
    # absolutized silently. Drive-relative ('C:foo') and rooted ('/x') both fail.
    if not raw.is_absolute():
        raise WikiError(f'{what}须为绝对路径: {value}')
    if '..' in raw.parts:
        raise WikiError(f'{what}不可含 .. 段: {value}')
    path = raw.resolve()
    roots = _registered_roots(state)
    if not any(path.is_relative_to(item) for item in roots):
        raise WikiError(f'{what}未在任何已登记数据根内: {value}（先 add-data-root 登记）')
    return path


# ---------------------------------------------------------------- schema

def _record(section: str, item: dict, required: tuple[str, ...]) -> list[str]:
    errors = []
    if not isinstance(item, dict):
        return [f'{section} 记录必须为对象']
    if item.get('id') is None:
        errors.append(f'{section} 记录缺少 id')
    for key in required:
        if key not in item:
            errors.append(f'{section}.{item.get("id", "?")} 缺少 {key}')
    return errors


def validate_structure(state: dict) -> list[str]:
    """Structural checks that must hold for the file to load at all."""
    errors = []
    if not isinstance(state, dict):
        return ['project.json 必须为对象']
    if type(state.get('schema_version')) is not int or state['schema_version'] != SCHEMA_VERSION:
        errors.append(f'project.json schema_version 必须为 {SCHEMA_VERSION}')
    if not _text(state.get('project_id')):
        errors.append('project_id 必须为非空字符串')
    if type(state.get('revision')) is not int or state['revision'] < 0:
        errors.append('revision 必须为非负整数')
    if not _text(state.get('project_root')):
        errors.append('project_root 缺失')
    for section in ('data_roots', 'profile_refs', 'events'):
        if not isinstance(state.get(section), list):
            errors.append(f'{section} 必须为列表')
    for section in ('entities', 'objects', 'observations', 'routes', 'tasks',
                    'artifacts', 'runs', 'decisions', 'authorizations', 'lessons'):
        table = state.get(section)
        if not isinstance(table, dict):
            errors.append(f'{section} 必须为对象')
            continue
        for key, item in table.items():
            if not isinstance(item, dict):
                errors.append(f'{section}.{key} 必须为对象记录')
            elif item.get('id') != key:
                errors.append(f'{section}.{key} 的 id 与键不一致')
    if not isinstance(state.get('legacy_contexts'), list):
        errors.append('legacy_contexts 必须为列表')
    return errors


def validate_state(state: dict) -> list[str]:
    """Full write-time validation: structure plus reference integrity."""
    errors = validate_structure(state)
    if errors:
        return errors
    required = {
        'entities': ('kind', 'basis'),
        'objects': ('kind', 'basis'),
        'observations': ('claim', 'value', 'basis'),
        'routes': ('question', 'decision'),
        'tasks': ('role', 'status'),
        'artifacts': ('path', 'produced_by', 'inputs', 'freshness'),
        'runs': ('task', 'status', 'receipt', 'at'),
        'decisions': ('kind', 'text', 'basis'),
        'authorizations': ('scope', 'decided_by'),
        'lessons': ('draft', 'status'),
    }
    for section, keys in required.items():
        for key, item in state[section].items():
            errors.extend(_record(section, item, keys))
    for key, item in state['objects'].items():
        if isinstance(item, dict):
            if item.get('basis') not in BASES:
                errors.append(f'objects.{key}.basis 非法')
            if (item.get('path') is None) == (item.get('external') is None):
                errors.append(f'objects.{key} 必须且只能有 path 或 external 之一')
    for key, item in state['entities'].items():
        if isinstance(item, dict) and item.get('basis') not in BASES:
            errors.append(f'entities.{key}.basis 非法')
    for key, item in state['observations'].items():
        if isinstance(item, dict):
            if item.get('basis') not in BASES:
                errors.append(f'observations.{key}.basis 非法')
            if item.get('value') not in OBSERVATION_VALUES:
                errors.append(f'observations.{key}.value 非法')
    for key, item in state['routes'].items():
        if isinstance(item, dict) and item.get('decision') not in ('pending', 'chosen', 'rejected'):
            errors.append(f'routes.{key}.decision 非法')
    for key, item in state['tasks'].items():
        if isinstance(item, dict):
            if item.get('status') not in WORK_STATUSES:
                errors.append(f'tasks.{key}.status 非法')
            if item.get('role') not in ROLES:
                errors.append(f'tasks.{key}.role 非法')
    for key, item in state['artifacts'].items():
        if isinstance(item, dict):
            if not isinstance(item.get('freshness'), dict) or \
                    item['freshness'].get('state') not in FRESHNESS:
                errors.append(f'artifacts.{key}.freshness 非法')
    for key, item in state['runs'].items():
        if isinstance(item, dict) and item.get('status') not in RUN_STATUSES:
            errors.append(f'runs.{key}.status 非法')
    for key, item in state['lessons'].items():
        if isinstance(item, dict):
            if item.get('status') not in LESSON_STATUSES:
                errors.append(f'lessons.{key}.status 非法')
            draft = item.get('draft')
            if not isinstance(draft, dict) or not _text(draft.get('claim')):
                errors.append(f'lessons.{key}.draft 需要非空 claim')
            elif not draft.get('evidence_refs'):
                errors.append(f'lessons.{key} 草稿必须带证据引用')
    if errors:
        return errors
    # Reference integrity: dangling evidence pointers are concrete errors.
    prefix_of = {'entities': 'entity', 'objects': 'object', 'observations': 'observation',
                 'routes': 'route', 'tasks': 'task', 'artifacts': 'artifact',
                 'decisions': 'decision', 'authorizations': 'authorization'}
    nodes = set()
    for section, prefix in prefix_of.items():
        nodes.update(f'{prefix}:{key}' for key in state[section])
    nodes.update(f'run:{key}' for key in state['runs'])

    def bad_ref(where, ref):
        if not isinstance(ref, str) or ':' not in ref:
            errors.append(f'{where} 引用格式非法（须为 kind:id / file:path / external:path）: {ref}')
            return
        prefix, ident = ref.split(':', 1)
        if prefix == 'file':
            try:
                project_path(state['project_root'], ident)
            except WikiError as error:
                errors.append(f'{where} {error}')
        elif prefix == 'external':
            try:
                external_path(state, ident)
            except WikiError as error:
                errors.append(f'{where} {error}')
        elif prefix in _KIND_PREFIXES:
            if ref not in nodes:
                errors.append(f'{where} 引用了不存在的记录: {ref}')
        else:
            errors.append(f'{where} 引用前缀未知: {prefix}')

    for key, item in state['objects'].items():
        for ref in item.get('entities') or []:
            if not str(ref).startswith('entity:') or f'entity:{ref.split(":",1)[1]}' not in nodes:
                errors.append(f'objects.{key}.entities 引用了不存在的实体: {ref}')
    for key, item in state['observations'].items():
        if item.get('about'):
            bad_ref(f'observations.{key}.about', item['about'])
    for key, item in state['tasks'].items():
        for ref in item.get('inputs') or []:
            bad_ref(f'tasks.{key}.inputs', ref)
        if item.get('authorization'):
            bad_ref(f'tasks.{key}.authorization', item['authorization'])
        for ref in item.get('prerequisite_refs') or []:
            bad_ref(f'tasks.{key}.prerequisite_refs', ref)
    for key, item in state['artifacts'].items():
        for ref in item.get('inputs') or []:
            bad_ref(f'artifacts.{key}.inputs', ref)
        produced_by = item.get('produced_by')
        if produced_by and f'run:{produced_by}' not in nodes:
            errors.append(f'artifacts.{key}.produced_by 引用了不存在的 run: {produced_by}')
    for key, item in state['decisions'].items():
        if item.get('route'):
            bad_ref(f'decisions.{key}.route', item['route'])
        if item.get('supersedes'):
            bad_ref(f'decisions.{key}.supersedes', item['supersedes'])
    for key, item in state['lessons'].items():
        draft = item.get('draft') or {}
        for ref in draft.get('evidence_refs') or []:
            bad_ref(f'lessons.{key}.draft.evidence_refs', ref)
        for ref in draft.get('links') or []:
            if str(ref).startswith('method:'):
                continue  # canonical method ids are annotations, not state refs
            bad_ref(f'lessons.{key}.draft.links', ref)
    if errors:
        return errors
    # Dependency cycles: task -> artifact via declared inputs (artifact: refs and
    # file: aliases of artifact paths), artifact -> task via produced_by -> run.
    artifact_by_path = {a['path']: aid for aid, a in state['artifacts'].items()}
    t2a = {}
    for tid, item in state['tasks'].items():
        targets = set()
        for ref in item.get('inputs') or []:
            if ref.startswith('artifact:'):
                targets.add(ref.split(':', 1)[1])
            elif ref.startswith('file:') and ref[5:] in artifact_by_path:
                targets.add(artifact_by_path[ref[5:]])
        t2a[tid] = targets
    a2t = {}
    for aid, item in state['artifacts'].items():
        run = state['runs'].get(item.get('produced_by') or '')
        if run:
            a2t[aid] = {run['task']}

    def neighbours(node):
        kind, ident = node
        if kind == 'task':
            return {('artifact', a) for a in t2a.get(ident, ()) if a in a2t}
        return {('task', t) for t in a2t.get(ident, ()) if t in t2a}

    WHITE, GREY, BLACK = 0, 1, 2
    color = {}
    for start in [('task', t) for t in t2a] + [('artifact', a) for a in a2t]:
        if color.get(start, WHITE) != WHITE:
            continue
        stack = [(start, iter(sorted(neighbours(start))))]
        color[start] = GREY
        while stack:
            node, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                color[node] = BLACK
                stack.pop()
            elif color.get(nxt, WHITE) == GREY:
                cycle = [f'{k}:{i}' for k, i in [x[0] for x in stack] + [nxt]]
                errors.append('依赖存在环路: ' + ' -> '.join(cycle))
                stack.clear()
            elif color.get(nxt, WHITE) == WHITE:
                color[nxt] = GREY
                stack.append((nxt, iter(sorted(neighbours(nxt)))))
    return errors


# ---------------------------------------------------------------- load/write

def _empty_state(root: Path, project_id: str, title: str) -> dict:
    return {
        'schema_version': SCHEMA_VERSION,
        'project_id': project_id,
        'title': title,
        'revision': 0,
        'created_at': _now(),
        'project_root': str(Path(root).resolve()),
        'data_roots': [],
        'profile_refs': [],
        'entities': {},
        'objects': {},
        'observations': {},
        'routes': {},
        'tasks': {},
        'artifacts': {},
        'runs': {},
        'decisions': {},
        'authorizations': {},
        'lessons': {},
        'legacy_contexts': [],
        'events': [],
    }


def _state_file(root: Path) -> Path:
    return state_dir(root) / STATE_FILE


def _read_state_file(root: Path) -> dict:
    """Parse + structural validation only; used by relocate where the stored
    project_root legitimately differs from the requested directory."""
    path = _state_file(root)
    if not path.is_file():
        raise WikiError(f'课题状态不存在: {path}（先 project init）')
    try:
        state = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise WikiError(f'project.json 无法读取: {error}') from error
    errors = validate_structure(state)
    if errors:
        raise WikiError(f'project.json 结构不合法: ' + '；'.join(errors))
    return state


def load_project(root: Path) -> dict:
    root = Path(root).resolve()
    state = _read_state_file(root)
    stored = Path(state['project_root']).resolve()
    if stored != root:
        raise WikiError(
            f'状态记录的 project_root 为 {stored}，与请求目录 {root} 不一致；'
            '若为复制/移动后的课题请显式 project relocate，不在旧根上静默检查')
    errors = validate_state(state)
    if errors:
        raise WikiError('project.json 校验未通过: ' + '；'.join(errors))
    return state


def relocate_project(root: Path, *, expected_revision=None) -> dict:
    """Rebind a moved/copied project to this directory explicitly."""
    root = Path(root).resolve()
    state = _read_state_file(root)
    old_root = state['project_root']
    if Path(old_root).resolve() == root:
        return state

    def mutate(state):
        state = dict(state)
        state['project_root'] = str(root)
        return state, ('relocate', f'课题根重定位 {old_root} → {root}')

    return update_project(root, mutate, expected_revision=expected_revision,
                          _loader=_read_state_file)


def _route_card_text(route: dict) -> str:
    lines = [f"# {route['question']}", '',
             f"- id: `{route['id']}`",
             f"- 决定: {route['decision']}",
             f"- 依据基础: {route.get('basis', 'unknown')}"]
    if route.get('hypothesis'):
        lines.append(f"- 假设: {route['hypothesis']}")
    if route.get('gaps'):
        lines.append(f"- 缺口: {'；'.join(route['gaps'])}")
    if route.get('evidence_refs'):
        lines.append(f"- 证据: {'、'.join(route['evidence_refs'])}")
    if route.get('note'):
        lines.extend(['', route['note']])
    return '\n'.join(lines) + '\n'


def _write_route_card(root: Path, route: dict) -> None:
    directory = state_dir(root) / 'routes'
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{route['id']}.md").write_text(_route_card_text(route), encoding='utf-8')


def render_summary(state: dict) -> str:
    """Short hand-off summary derived from state; never the source of truth.

    Registered basis/freshness are *declarations at registration time*; this
    view also re-checks file presence/evidence bytes at render time and labels
    each honestly. Nothing here asserts scientific verification.
    """
    root = Path(state['project_root'])
    lines = [f"# {state['title']} — 接手摘要",
             '',
             f"- project_id: `{state['project_id']}`；revision: {state['revision']}",
             f"- project_root: `{state['project_root']}`",
             f"- schema_version: {state['schema_version']}（工具不识别此版本时必须拒绝读取）",
             '']
    if state['profile_refs']:
        lines.append('## 领域配置')
        lines.extend(f"- `{p['id']}@v{p['version']}`" for p in state['profile_refs'])
        lines.append('')
    if state['routes']:
        lines.append('## 主线')
        for route in state['routes'].values():
            lines.append(f"- `{route['id']}` {route['question']}（{route['decision']}）")
        lines.append('')
    if state['tasks']:
        lines.append('## 任务状态')
        for task in state['tasks'].values():
            family = f"（{task['family_id'] or '未绑定家族'}"
            impl = f"/{task['implementation_id']}）" if task.get('implementation_id') else '）'
            stage = f" stage={task['stage']}" if task.get('stage') else ''
            lines.append(f"- `{task['id']}` [{task['status']}] role={task['role']}{stage} {family}{impl}")
        lines.append('')
    rendered_at = _now()
    if state['artifacts']:
        # 登记时的新鲜度与上次核对时间是声明，不是当前结论；此处只实时核对
        # 文件存在性（代价低），指纹/依赖复核以 project check 为准。
        lines.append('## 产物新鲜度（登记时点声明；指纹与依赖复核以 project check 为准）')
        for artifact in state['artifacts'].values():
            freshness = artifact['freshness']
            reason = f"（{freshness['reason']}）" if freshness.get('reason') else ''
            checked = f"核对于 {freshness.get('checked_at', '?')}"
            try:
                path = project_path(root, artifact['path'])
                presence = '存在' if path.is_file() else '缺失'
            except WikiError:
                presence = '路径不可解析'
            lines.append(
                f"- `{artifact['path']}` 登记:{freshness['state']}{reason}（{checked}）；"
                f"当前文件:{presence} ← run `{artifact['produced_by']}`")
        lines.append('')
    declared = {'verified': 0, 'author_stated': 0, 'unknown': 0}
    present = {'resolves': 0, 'none': 0, 'missing': 0, 'stale': 0, 'unhashed': 0}
    for item in state['observations'].values():
        declared[item['basis']] = declared.get(item['basis'], 0) + 1
        state_v = evidence_state(state, root, item.get('evidence'))
        present[state_v] = present.get(state_v, 0) + 1
    lines.append(f"## 观察证据（注册声明 vs 当前复核 @ {rendered_at}）")
    lines.append('')
    lines.append(f"- 声明依据：verified {declared['verified']}；作者自述 {declared['author_stated']}；"
                 f"未知 {declared['unknown']}（注册时填写，非本次核查结论）")
    lines.append(f"- 当前复核（本文件生成时点，仅限注册范围）：证据可核对 {present['resolves']}；"
                 f"无登记证据 {present['none']}；证据缺失 {present['missing']}；"
                 f"证据字节已变化 {present['stale']}；未记录指纹 {present['unhashed']}")
    lines.append('- 声明≠已核查；科学解释与阶段完成需另行审查，不由本摘要授予。')
    lines.append('')
    if state['decisions']:
        lines.append('## 作者决定')
        for item in state['decisions'].values():
            lines.append(f"- `{item['id']}` [{item['kind']}] {item['text']}")
        lines.append('')
    if state['lessons']:
        lines.append('## 经验草稿（课题内提案，未进正式推荐/签核）')
        for item in state['lessons'].values():
            reviewed = (f"；评审 {item['status']} by {item['reviewed_by']}"
                        if item.get('reviewed_by') else f"；{item['status']}")
            lines.append(f"- `{item['id']}` {item['draft'].get('claim', '')[:80]}{reviewed}")
        lines.append('')
    pending = [task['id'] for task in state['tasks'].values() if task['status'] == 'running']
    if pending:
        lines.append('## 曾启动的运行（需核对进程与产物，不代表完成）')
        lines.extend(f"- `{item}`" for item in pending)
        lines.append('')
    if state['events']:
        lines.append('## 最近事件')
        for event in state['events'][-5:]:
            lines.append(f"- r{event['revision']} {event['at']}: {event['summary']}")
        lines.append('')
    lines.append('> 本文件由 project.json 派生，真相以 project.json 与各 run 收据为准。')
    return '\n'.join(lines) + '\n'


def update_project(root: Path, mutate, *, expected_revision: int | None = None,
                   _loader=None, staged=(), warnings_out=None) -> dict:
    """Apply ``mutate(state) -> (new_state, (event_kind, event_summary))`` atomically.

    The lock guarantees a single writer; ``expected_revision`` rejects stale
    reads; the new state is fully validated before any ``os.replace`` commits.

    Commit order inside the critical section:
    1. ``staged`` caller files (e.g. run receipts) — authoritative *inputs* to
       the state, committed with in-memory backups so a later failure restores
       them byte-for-byte;
    2. derived files (summary, route cards) — regenerable, so a rename failure
       here is a *recoverable derived-file gap*: recorded in ``warnings_out``
       and commit continues; it never rolls back authoritative files and never
       reports a false rollback;
    3. ``project.json`` — the authoritative commit point, always last. If its
       rename fails, receipts AND already-published derived views are restored
       byte-for-byte: no future-revision handoff survives an old state.
    """
    root = Path(root)
    directory = state_dir(root)
    if not directory.is_dir():
        raise WikiError(f'课题状态目录不存在: {directory}（先 project init）')
    lock = directory / LOCK_FILE
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        raise WikiError(f'另一写者持有锁: {lock}（若无活动写者，请人工删除该锁文件）') from error
    card_tmps = []
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(str(os.getpid()))
        state = (_loader or load_project)(root)
        if expected_revision is not None and state['revision'] != expected_revision:
            raise WikiError(
                f'修订号冲突: 期望 {expected_revision}，当前 {state["revision"]}；请先重新读取状态')
        new_state, event = mutate(state)
        new_state['revision'] = state['revision'] + 1
        kind, summary = event
        new_state['events'] = [*new_state['events'],
                               {'id': f'ev{new_state["revision"]}', 'revision': new_state['revision'],
                                'at': _now(), 'kind': kind, 'summary': summary}]
        errors = validate_state(new_state)
        if errors:
            raise WikiError('状态校验未通过: ' + '；'.join(errors))
        changed_routes = {rid for rid, route in new_state['routes'].items()
                          if state['routes'].get(rid) != route}
        tmp_state = directory / f'{STATE_FILE}.tmp'
        tmp_summary = directory / f'{SUMMARY_FILE}.tmp'
        tmp_state.write_text(json.dumps(new_state, ensure_ascii=False, indent=2) + '\n',
                             encoding='utf-8')
        tmp_summary.write_text(render_summary(new_state), encoding='utf-8')
        # Stage derived route cards as .tmp; nothing user-visible yet.
        routes_dir = directory / 'routes'
        for rid in changed_routes:
            card_tmp = routes_dir / f'{rid}.md.tmp'
            card_tmp.parent.mkdir(parents=True, exist_ok=True)
            card_tmp.write_text(_route_card_text(new_state['routes'][rid]), encoding='utf-8')
            card_tmps.append(card_tmp)
        # Back up every file this transaction may replace — caller-staged
        # authoritative files (receipts) AND already-published derived views
        # (summary/cards) — so a failed authoritative commit restores bytes
        # exactly and no future-revision handoff view survives an old state.
        backups = []
        for tmp_path, final_path in staged:
            final_path = Path(final_path)
            backups.append((final_path,
                            final_path.read_bytes() if final_path.exists() else None))
        derived_finals = [directory / SUMMARY_FILE] + [
            routes_dir / card_tmp.name[:-4] for card_tmp in card_tmps]
        for final_path in derived_finals:
            backups.append((final_path,
                            final_path.read_bytes() if final_path.exists() else None))
        try:
            # 1. Commit caller-staged authoritative files (run receipts).
            for tmp_path, final_path in staged:
                os.replace(tmp_path, final_path)
            # 2. Derived files: regenerable; a failure is a recoverable gap,
            #    not a reason to roll back authoritative state.
            try:
                os.replace(tmp_summary, directory / SUMMARY_FILE)
            except OSError as error:
                if warnings_out is not None:
                    warnings_out.append(f'派生 summary 写入失败（可重新生成）: {error}')
            for card_tmp in card_tmps:
                try:
                    os.replace(card_tmp, routes_dir / card_tmp.name[:-4])  # .tmp -> .md
                except OSError as error:
                    if warnings_out is not None:
                        warnings_out.append(
                            f'派生路线卡 {card_tmp.name} 写入失败（可重新生成）: {error}')
            # 3. project.json is the authoritative commit point, last.
            os.replace(tmp_state, _state_file(root))
        except BaseException:
            for final_path, old_bytes in backups:
                if old_bytes is None:
                    final_path.unlink(missing_ok=True)
                else:
                    final_path.write_bytes(old_bytes)
            raise
        return new_state
    except BaseException:
        for card_tmp in card_tmps:
            card_tmp.unlink(missing_ok=True)
        raise
    finally:
        # Never leave staging files behind; committed renames are already gone.
        (directory / f'{STATE_FILE}.tmp').unlink(missing_ok=True)
        (directory / f'{SUMMARY_FILE}.tmp').unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def init_project(root: Path, *, project_id: str | None = None, title: str | None = None,
                 data_roots: list[str] | None = None) -> dict:
    root = Path(root).resolve()
    directory = state_dir(root)
    if directory.exists():
        raise WikiError(f'课题状态目录已存在: {directory}；检查版本并提出迁移，不覆盖')
    if not root.is_dir():
        raise WikiError(f'课题目录不存在: {root}')
    legacy = []
    wiki_use = root / 'wiki-use'
    if wiki_use.is_dir():
        for child in sorted(wiki_use.iterdir()):
            if child.is_dir() and child.name != '_project':
                legacy.append({'path': f'wiki-use/{child.name}',
                               'note': '旧 wiki-use 记录，显式引用兼容，不迁移不覆盖'})
    slug = re.sub(r'[^a-z0-9_-]+', '-', root.name.casefold()).strip('-')
    if not slug:
        # Non-Latin root names must not collapse into the same 'project' id.
        slug = 'project-' + hashlib.sha1(str(root).encode()).hexdigest()[:8]
    project_id = _check_id(project_id or slug)
    state = _empty_state(root, project_id, title or root.name)
    state['legacy_contexts'] = legacy
    for sub in ('runs', 'routes', 'lessons'):
        (directory / sub).mkdir(parents=True)
    state['revision'] = 1
    state['events'] = [{'id': 'ev1', 'revision': 1, 'at': _now(),
                        'kind': 'init', 'summary': '课题状态初始化'}]
    errors = validate_state(state)
    if errors:
        raise WikiError('初始状态校验未通过: ' + '；'.join(errors))
    tmp = directory / f'{STATE_FILE}.tmp'
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (directory / SUMMARY_FILE).write_text(render_summary(state), encoding='utf-8')
    os.replace(tmp, _state_file(root))
    if data_roots:
        for item in data_roots:
            add_data_root(root, item)
        state = load_project(root)
    return state


# ---------------------------------------------------------------- references

def resolve_ref(state: dict, ref: str) -> tuple[str, str]:
    """Resolve a reference to a (kind, id) pair. ``file:``/``external:`` are literal."""
    if not _text(ref):
        raise WikiError('引用必须为非空字符串')
    if ':' in ref:
        prefix, rest = ref.split(':', 1)
        if prefix in ('object', 'entity', 'artifact', 'observation', 'task', 'route',
                      'decision', 'authorization', 'run'):
            section = {'object': 'objects', 'entity': 'entities', 'artifact': 'artifacts',
                       'observation': 'observations', 'task': 'tasks', 'route': 'routes',
                       'decision': 'decisions', 'authorization': 'authorizations',
                       'run': 'runs'}[prefix]
            if rest not in state[section]:
                raise WikiError(f'引用了不存在的 {prefix}: {rest}')
            return prefix, rest
        if prefix == 'file':
            return 'file', rest
        if prefix == 'external':
            return 'external', rest
    matches = [section for section in ('objects', 'entities', 'artifacts', 'tasks',
                                       'observations', 'routes', 'decisions', 'authorizations')
               if ref in state[section]]
    if len(matches) > 1:
        raise WikiError(f'引用 {ref} 有歧义，请加前缀: ' + '、'.join(matches))
    if not matches:
        raise WikiError(f'引用了不存在的记录: {ref}')
    return matches[0][:-1] if matches[0] != 'entities' else 'entity', ref


def _ref_fingerprint(state: dict, root: Path, kind: str, ident: str) -> str | None:
    """Current sha256 of the file a ref points at, when it has one."""
    try:
        if kind == 'object':
            item = state['objects'][ident]
            path = (external_path(state, item['external']) if item.get('external')
                    else project_path(root, item['path']))
        elif kind == 'artifact':
            path = project_path(root, state['artifacts'][ident]['path'])
        elif kind == 'file':
            path = project_path(root, ident)
        elif kind == 'external':
            path = external_path(state, ident)
        else:
            return None
        return _sha(path) if path.is_file() else None
    except (WikiError, OSError):
        return None


def _canonical_refs(state: dict, root: Path, refs) -> list[str]:
    """Normalize caller refs into canonical ``kind:id``/``file:``/``external:`` strings."""
    result = []
    for ref in refs:
        kind, ident = resolve_ref(state, ref)
        if kind == 'file':
            project_path(root, ident)  # rejects escapes early
            result.append(f'file:{ident}')
        elif kind == 'external':
            external_path(state, ident)  # must sit under a registered root
            result.append(f'external:{Path(ident).resolve()}')
        else:
            result.append(f'{kind}:{ident}')
    return result


# ---------------------------------------------------------------- mutations

def _mutate_add(section: str, record: dict, kind: str, summary: str):
    def mutate(state):
        if record['id'] in state[section]:
            raise WikiError(f'{section} 已存在: {record["id"]}')
        state = dict(state)
        state[section] = {**state[section], record['id']: record}
        return state, (kind, summary)
    return mutate


def add_data_root(root: Path, path: str, *, root_id: str | None = None,
                  access: str = 'read', expected_revision=None) -> dict:
    resolved = Path(path).resolve()
    if not resolved.is_dir():
        raise WikiError(f'数据根不存在或不是目录: {path}')
    root_id = _check_id(root_id or f'dr-{hashlib.sha1(str(resolved).encode()).hexdigest()[:8]}')
    if access != 'read':
        raise WikiError('数据根只支持 read 访问级别')

    def mutate(state):
        if any(item['id'] == root_id or Path(item['path']).resolve() == resolved
               for item in state['data_roots']):
            raise WikiError(f'数据根已登记: {resolved}')
        state = dict(state)
        state['data_roots'] = [*state['data_roots'],
                               {'id': root_id, 'path': str(resolved), 'access': 'read'}]
        return state, ('data_root', f'登记数据根 {root_id}: {resolved}')
    return update_project(root, mutate, expected_revision=expected_revision)


def add_entity(root: Path, entity_id: str, kind: str, *, count=None, identity=None,
               relations=None, properties=None, basis='author_stated', note=None,
               expected_revision=None) -> dict:
    entity_id = _check_id(entity_id, 'entity id')
    _require_text(kind, 'entity kind')
    if basis not in BASES:
        raise WikiError(f'basis 必须为 {"、".join(BASES)}')
    if count is not None and (type(count) is not int or count < 0):
        raise WikiError('entity count 必须为非负整数')
    for key in (relations or {}):
        _check_id(key, 'relation name')
    record = {'id': entity_id, 'kind': kind.strip(), 'count': count,
              'identity': identity, 'relations': dict(relations or {}),
              'properties': dict(properties or {}), 'basis': basis, 'note': note,
              'registered_at': _now()}
    return update_project(
        root, _mutate_add('entities', record, 'entity', f'登记实体 {entity_id}（{kind}）'),
        expected_revision=expected_revision)


def add_object(root: Path, object_id: str, kind: str, *, path=None, external=None,
               native_type=None, entities=(), properties=None, basis='author_stated',
               inspected: bool = False, adapter=None,
               note=None, expected_revision=None) -> dict:
    """Register a data/model/file object in native form; CSV conversion is never required.

    ``native_type`` is a declaration. ``inspected=True`` means an adapter named
    in ``adapter`` actually opened/parsed the object — accepting a filename is
    never evidence of parsed semantic support.
    """
    object_id = _check_id(object_id, 'object id')
    _require_text(kind, 'object kind')
    if basis not in BASES:
        raise WikiError(f'basis 必须为 {"、".join(BASES)}')
    if type(inspected) is not bool:
        raise WikiError('inspected 必须为布尔值')
    if inspected and not _text(adapter):
        raise WikiError('inspected=True 需要 adapter 名称说明实际解析途径')
    if adapter is not None and not _text(adapter):
        raise WikiError('adapter 须为非空字符串')
    if (path is None) == (external is None):
        raise WikiError('object 必须且只能给 path（课题相对）或 external（已登记数据根内绝对路径）之一')
    state = load_project(root)
    if path is not None:
        resolved = project_path(root, path)
        location = {'path': path, 'external': None}
    else:
        resolved = external_path(state, external)
        location = {'path': None, 'external': str(resolved)}
    exists = resolved.is_file()
    digest = _sha(resolved) if exists else None
    if basis == 'verified' and digest is None:
        raise WikiError(f'basis=verified 需要真实存在的文件以记录指纹: {path or external}')
    for ref in entities:
        kind_r, ident = resolve_ref(state, ref)
        if kind_r != 'entity':
            raise WikiError(f'objects.entities 只接受实体引用: {ref}')
    record = {'id': object_id, 'kind': kind.strip(), 'native_type': native_type,
              **location, 'sha256': digest,
              'fingerprint_scope': ('full-file sha256（分块流式）' if digest else None),
              'bytes': resolved.stat().st_size if exists else None,
              'entities': [f'entity:{resolve_ref(state, ref)[1]}' for ref in entities],
              'properties': dict(properties or {}), 'basis': basis,
              'inspected': inspected, 'adapter': adapter, 'note': note,
              'registered_at': _now()}
    return update_project(
        root, _mutate_add('objects', record, 'object', f'登记对象 {object_id}（{kind}）'),
        expected_revision=expected_revision)


def add_observation(root: Path, obs_id: str, claim: str, *, about=None, value='unknown',
                    basis='unknown', evidence=None, scope=None, stage=None, note=None,
                    expected_revision=None) -> dict:
    """Record a claim about inputs/steps/results with its own basis."""
    obs_id = _check_id(obs_id, 'observation id')
    _require_text(claim, 'claim')
    if basis not in BASES:
        raise WikiError(f'basis 必须为 {"、".join(BASES)}')
    if value not in OBSERVATION_VALUES:
        raise WikiError(f'value 必须为 {"、".join(OBSERVATION_VALUES)}')
    if stage is not None and not _text(stage):
        raise WikiError('stage 须为非空字符串（声明归属的工作阶段，不是完成状态）')
    state = load_project(root)
    about_ref = None
    if about is not None:
        k, i = resolve_ref(state, about)
        if k in ('file', 'external'):
            raise WikiError('observation.about 引用实体/对象/产物/任务记录，不直接引用文件')
        about_ref = f'{k}:{i}'
    ev = None
    if evidence is not None:
        if str(evidence).startswith('external:') or Path(str(evidence)).is_absolute():
            ext = str(evidence)[len('external:'):] if str(evidence).startswith('external:') \
                else str(evidence)
            ev_path = external_path(state, ext, 'evidence 路径')
            ev = {'external': str(ev_path),
                  'sha256': _sha(ev_path) if ev_path.is_file() else None,
                  'bytes': ev_path.stat().st_size if ev_path.is_file() else None,
                  'checked_at': _now()}
        else:
            ev_path = project_path(root, evidence, 'evidence 路径')
            ev = {'path': evidence,
                  'sha256': _sha(ev_path) if ev_path.is_file() else None,
                  'bytes': ev_path.stat().st_size if ev_path.is_file() else None,
                  'checked_at': _now()}
        if basis == 'verified' and ev['sha256'] is None:
            raise WikiError('basis=verified 的观察需要可检查的证据文件')
    record = {'id': obs_id, 'claim': claim.strip(), 'about': about_ref, 'value': value,
              'basis': basis, 'evidence': ev, 'scope': scope, 'stage': stage,
              'note': note, 'registered_at': _now()}
    return update_project(
        root, _mutate_add('observations', record, 'observation',
                          f'登记观察 {obs_id}: {claim}（{basis}/{value}）'),
        expected_revision=expected_revision)


def add_route(root: Path, route_id: str, question: str, *, hypothesis=None,
              evidence_refs=(), gaps=(), decision='pending', basis='unknown',
              note=None, expected_revision=None) -> dict:
    route_id = _check_id(route_id, 'route id')
    _require_text(question, 'route question')
    if decision not in ('pending', 'chosen', 'rejected'):
        raise WikiError('route decision 必须为 pending/chosen/rejected')
    if basis not in BASES:
        raise WikiError(f'basis 必须为 {"、".join(BASES)}')
    state = load_project(root)
    refs = _canonical_refs(state, root, evidence_refs)
    record = {'id': route_id, 'question': question.strip(), 'hypothesis': hypothesis,
              'evidence_refs': refs, 'gaps': list(gaps), 'decision': decision,
              'basis': basis, 'note': note, 'registered_at': _now()}
    return update_project(
        root, _mutate_add('routes', record, 'route', f'登记主线 {route_id}: {question}（{decision}）'),
        expected_revision=expected_revision)


def add_task(root: Path, task_id: str, *, family_id=None, implementation_id=None,
             purpose=None, role='exploratory', inputs=(), params=None,
             authorization=None, stage=None, note=None, status='planned',
             expected_revision=None) -> dict:
    task_id = _check_id(task_id, 'task id')
    if role not in ROLES:
        raise WikiError(f'role 必须为 {"、".join(ROLES)}')
    if status not in WORK_STATUSES:
        raise WikiError(f'status 必须为 {"、".join(WORK_STATUSES)}')
    if stage is not None and not _text(stage):
        raise WikiError('stage 须为非空字符串（声明归属的工作阶段，不是完成状态）')
    state = load_project(root)
    refs = _canonical_refs(state, root, inputs)
    auth = None
    if authorization is not None:
        k, i = resolve_ref(state, authorization)
        if k != 'authorization':
            raise WikiError('authorization 必须引用 authorizations 记录')
        auth = f'authorization:{i}'
    if implementation_id is not None:
        _check_id(implementation_id, 'implementation id')
    if family_id is not None and not _text(family_id):
        raise WikiError('family_id 必须为非空字符串')
    record = {'id': task_id, 'family_id': family_id, 'implementation_id': implementation_id,
              'purpose': purpose, 'role': role, 'status': status, 'inputs': refs,
              'params': dict(params or {}), 'authorization': auth, 'stage': stage,
              'prerequisite_refs': [], 'note': note, 'registered_at': _now()}
    return update_project(
        root, _mutate_add('tasks', record, 'task', f'登记任务 {task_id}（{role}/{status}）'),
        expected_revision=expected_revision)


def add_decision(root: Path, decision_id: str, kind: str, text: str, *, scope=None,
                 route=None, supersedes=None, note=None, expected_revision=None) -> dict:
    """Author decisions only; silence never becomes a decision."""
    decision_id = _check_id(decision_id, 'decision id')
    if kind not in DECISION_KINDS:
        raise WikiError(f'decision kind 必须为 {"、".join(DECISION_KINDS)}')
    _require_text(text, 'decision text')
    state = load_project(root)
    route_ref = None
    if route is not None:
        k, i = resolve_ref(state, route)
        if k != 'route':
            raise WikiError('decision.route 必须引用 routes 记录')
        route_ref = f'route:{i}'
    sup = None
    if supersedes is not None:
        k, i = resolve_ref(state, supersedes)
        if k != 'decision':
            raise WikiError('decision.supersedes 必须引用 decisions 记录')
        sup = f'decision:{i}'
    record = {'id': decision_id, 'kind': kind, 'text': text.strip(), 'scope': scope,
              'route': route_ref, 'supersedes': sup, 'basis': 'author',
              'note': note, 'at': _now()}

    def mutate(state):
        if decision_id in state['decisions']:
            raise WikiError(f'decisions 已存在: {decision_id}')
        state = dict(state)
        state['decisions'] = {**state['decisions'], decision_id: record}
        if route_ref:
            routes = dict(state['routes'])
            target = dict(routes[i])
            target['decision'] = 'chosen' if kind == 'route' else target['decision']
            routes[i] = target
            state['routes'] = routes
        return state, ('decision', f'作者决定 {decision_id}（{kind}）: {text[:60]}')
    return update_project(root, mutate, expected_revision=expected_revision)


def add_authorization(root: Path, auth_id: str, scope: str, *, budget=None,
                      decided_by='author', note=None, expected_revision=None) -> dict:
    """Record the per-project execution agreement; no agreement means no allowance."""
    auth_id = _check_id(auth_id, 'authorization id')
    _require_text(scope, 'authorization scope')
    if not _text(decided_by):
        raise WikiError('decided_by 必须为非空字符串')
    record = {'id': auth_id, 'scope': scope.strip(), 'budget': dict(budget or {}),
              'decided_by': decided_by.strip(), 'note': note, 'at': _now()}
    return update_project(
        root, _mutate_add('authorizations', record, 'authorization',
                          f'执行约定 {auth_id}: {scope[:60]}'),
        expected_revision=expected_revision)


def register_profile(root: Path, profile_id: str, version: int, *,
                     spec_sha256: str | None = None, expected_revision=None) -> dict:
    """Bind the profile spec actually used — version *and* content hash — so a
    later evaluation against a different spec surfaces instead of silently
    passing under the old registration."""
    _check_id(profile_id, 'profile id')
    if type(version) is not int or version < 1:
        raise WikiError('profile version 必须为正整数')
    if spec_sha256 is not None and not (isinstance(spec_sha256, str)
                                        and re.fullmatch(r'[0-9a-f]{64}', spec_sha256)):
        raise WikiError('spec_sha256 须为 64 位十六进制摘要')

    def mutate(state):
        if any(p['id'] == profile_id for p in state['profile_refs']):
            raise WikiError(f'profile 已登记: {profile_id}')
        state = dict(state)
        state['profile_refs'] = [*state['profile_refs'],
                                 {'id': profile_id, 'version': version,
                                  'spec_sha256': spec_sha256}]
        return state, ('profile', f'登记领域配置 {profile_id}@v{version}')
    return update_project(root, mutate, expected_revision=expected_revision)


# ---------------------------------------------------------------- lessons

LESSON_STATUSES = ('pending', 'deferred', 'rejected', 'accepted')


def _lesson_key(claim, applies_to, links) -> str:
    def norm(value) -> str:
        return ' '.join(str(value or '').casefold().split())
    return '|'.join((norm(claim), norm(applies_to), ','.join(sorted(links))))


def add_lesson(root: Path, lesson_id: str, claim: str, *, evidence=(),
               applies_to=None, links=(), basis='author_stated', note=None,
               expected_revision=None) -> dict:
    """Evidence-backed, scoped lesson *draft* — a proposal, never a decision.

    Drafts live only in project state: they do not reach Wiki recommendations,
    verification, or author signoff by existing. A duplicate (same normalized
    claim + scope + links) merges new evidence into the existing proposal and
    returns its id — one lesson, one draft, never a second method family.
    ``links`` accepts state refs (``kind:id``) or canonical method ids, so a
    lesson points at existing knowledge instead of re-describing it.
    """
    lesson_id = _check_id(lesson_id, 'lesson id')
    _require_text(claim, 'lesson claim')
    if basis not in BASES:
        raise WikiError(f'basis 必须为 {"、".join(BASES)}')
    state = load_project(root)
    refs = _canonical_refs(state, root, evidence)
    if not refs:
        raise WikiError('lesson 草稿必须至少引用一条已登记证据'
                        '（run:/observation:/decision:/artifact: 等），不接受无据经验')
    if not _text(applies_to):
        raise WikiError('lesson 草稿必须写 --applies-to 适用范围'
                        '（条件/失效边界）；无界命题不做全局提案')
    link_refs = []
    for link in links or ():
        if ':' in str(link):
            kind_l, ident = resolve_ref(state, link)
            if kind_l in ('file', 'external'):
                raise WikiError('lesson.link 引用已登记记录或方法 id，不直接引用文件')
            link_refs.append(f'{kind_l}:{ident}')
        else:
            link_refs.append(f'method:{_check_id(str(link), "lesson link（方法 id）")}')
    key = _lesson_key(claim, applies_to, link_refs)
    draft = {'claim': claim.strip(), 'evidence_refs': refs,
             'applies_to': applies_to.strip() if applies_to else None,
             'links': link_refs, 'basis': basis, 'note': note}

    def mutate(state):
        state = dict(state)
        lessons = dict(state['lessons'])
        for lid, item in lessons.items():
            if item.get('dedupe_key') == key:
                item = dict(item)
                merged = dict(item['draft'])
                old_refs = list(merged.get('evidence_refs') or [])
                merged['evidence_refs'] = sorted(set(old_refs) | set(refs))
                if merged['evidence_refs'] == old_refs:
                    # Idempotent retry: nothing changed, prior review stands.
                    return state, ('lesson', f'lesson {lid} 草稿去重命中：'
                                             '无新证据，保持原评审状态')
                item['draft'] = merged
                reopened = item.get('status') != 'pending'
                if reopened:
                    # New evidence changes the reviewed content — reopen to
                    # pending and preserve the dated prior review instead of
                    # silently expanding what was approved/rejected/deferred.
                    history = list(item.get('previous_reviews') or [])
                    history.append({
                        'status': item.get('status'),
                        'reviewed_by': item.get('reviewed_by'),
                        'reviewed_at': item.get('reviewed_at'),
                        'review_note': item.get('review_note'),
                        'decision_ref': item.get('decision_ref'),
                        'evidence_refs': old_refs,
                        'reopened_at': _now()})
                    item.update(status='pending', previous_reviews=history,
                                reviewed_by=None, reviewed_at=None,
                                review_note=None, decision_ref=None)
                lessons[lid] = item
                state['lessons'] = lessons
                return state, ('lesson', f'lesson {lid} 草稿去重命中：合并证据'
                                         f'（请求 id {lesson_id}，未新建条目/家族'
                                         + ('；已评审草稿因新证据回到 pending，'
                                            '历史评审已保留' if reopened else '') + '）')
        if lesson_id in lessons:
            raise WikiError(f'lesson id 已存在且内容不同: {lesson_id}')
        lessons[lesson_id] = {'id': lesson_id, 'draft': draft, 'status': 'pending',
                              'dedupe_key': key, 'reviewed_by': None,
                              'reviewed_at': None, 'review_note': None,
                              'registered_at': _now()}
        state['lessons'] = lessons
        return state, ('lesson', f'登记 lesson 草稿 {lesson_id}（pending；'
                                 '不进正式推荐/验证/签核）')

    new_state = update_project(root, mutate, expected_revision=expected_revision)
    winner = next(lid for lid, item in new_state['lessons'].items()
                  if item.get('dedupe_key') == key)
    return {'lesson_id': winner, 'status': new_state['lessons'][winner]['status'],
            'deduplicated': winner != lesson_id, 'revision': new_state['revision'],
            'note': '课题内草稿；正式 Wiki 回写需要真实作者评审，非测试布尔'}


def review_lesson(root: Path, lesson_id: str, review_state: str, *, reviewed_by,
                  note=None, decision=None, expected_revision=None) -> dict:
    """Explicit project-local review disposition on a lesson draft.

    ``reviewed_by`` is required — a review is someone's act, never a bare
    boolean; test reviews must name themselves as isolated fixtures.
    ``accepted`` additionally requires ``decision``: a ``decision:<id>`` ref to
    a decision record already in project state — only an actual registered
    author decision moves a draft toward accepted. Even then it stays a
    project-local disposition pending real Wiki review before any write.
    """
    lesson_id = _check_id(lesson_id, 'lesson id')
    if review_state not in LESSON_STATUSES:
        raise WikiError(f'评审状态必须为 {"、".join(LESSON_STATUSES)}')
    _require_text(reviewed_by, 'reviewed_by（评审必须署名；测试评审需标明隔离夹具）')
    state = load_project(root)
    if lesson_id not in state['lessons']:
        raise WikiError(f'lesson 不存在: {lesson_id}')
    decision_ref = None
    if review_state == 'accepted':
        if not decision:
            raise WikiError('accepted 须附 --decision decision:<id>：'
                            '只有已登记的作者决策能把草稿推向 accepted')
        kind, ident = resolve_ref(state, decision)
        if kind != 'decision':
            raise WikiError(f'--decision 须指向 decision 记录，得到 {kind}:{ident}')
        decision_ref = f'decision:{ident}'
    elif decision:
        raise WikiError('仅 accepted 评审允许附 --decision')

    def mutate(state):
        state = dict(state)
        lessons = dict(state['lessons'])
        item = dict(lessons[lesson_id])
        item.update(status=review_state, reviewed_by=reviewed_by.strip(),
                    reviewed_at=_now(), review_note=note,
                    decision_ref=decision_ref)
        lessons[lesson_id] = item
        state['lessons'] = lessons
        return state, ('lesson', f'lesson {lesson_id} 评审={review_state}'
                                 f'（{reviewed_by.strip()}；课题内处置，不等于正式回写）')
    return update_project(root, mutate, expected_revision=expected_revision)


# ---------------------------------------------------------------- runs

def _artifact_id(run_id: str, path: str) -> str:
    return 'a-' + hashlib.sha1(f'{run_id}:{path}'.encode()).hexdigest()[:12]


def _dedup_fingerprint(task: dict, input_fps: dict, params: dict | None,
                       command: str, environment: dict | None,
                       code_refs: list[str] | None = None) -> str:
    """Identity of the computation: task + bound implementation + resolved input
    fingerprints + params + actual command + declared environment + declared
    code refs. A corrected command/environment/code is a different computation,
    never a silent duplicate."""
    payload = json.dumps({'task': task['id'],
                          'implementation': task.get('implementation_id'),
                          'inputs': input_fps, 'params': params or {},
                          'command': command or '',
                          'environment': dict(environment or {}),
                          'code_refs': list(code_refs or [])},
                         sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def material_state(state: dict, root: Path, *, path: Path | None,
                   recorded_sha: str | None) -> str:
    """Shared current-material resolver: one truth for check/evaluate/reuse.

    ``current``  — file exists and matches the recorded fingerprint.
    ``unhashed`` — material exists but no fingerprint was ever recorded, so
                   unchanged bytes cannot be established — never ``current``.
    ``stale``    — file exists but bytes differ from the recorded fingerprint.
    ``missing``  — path is gone or unresolvable.
    """
    if path is None or not path.exists():
        return 'missing'
    if recorded_sha:
        if not path.is_file() or _sha(path) != recorded_sha:
            return 'stale'
        return 'current'
    return 'unhashed'


def evidence_state(state: dict, root: Path, evidence: dict | None) -> str:
    """Observation evidence freshness, shared by check_project and profiles.

    ``none`` — no evidence recorded; ``resolves`` — inspectable and matching;
    ``stale`` — bytes changed since registration; ``missing`` — path gone.
    """
    if not evidence:
        return 'none'
    try:
        path = (external_path(state, evidence['external']) if evidence.get('external')
                else project_path(root, evidence['path']))
    except (WikiError, KeyError):
        return 'missing'
    result = material_state(state, root, path=path,
                            recorded_sha=evidence.get('sha256'))
    return {'current': 'resolves', 'unhashed': 'resolves',
            'stale': 'stale', 'missing': 'missing'}.get(result, 'missing')


def _artifact_freshness_for(state: dict, root: Path, path: Path,
                            report: dict | None) -> str | None:
    """Worst computed freshness among artifacts sharing ``path`` — same-file
    aliases inherit upstream staleness instead of hiding it behind their own
    unchanged bytes. Returns ``None`` when no artifact occupies the path."""
    worst = None
    order = {'stale': 3, 'unknown': 2, 'unhashed': 1}
    for aid, item in state['artifacts'].items():
        try:
            if project_path(root, item['path']) != path:
                continue
        except (WikiError, KeyError):
            continue
        if report is not None:
            fresh = ((report.get('artifacts') or {}).get(aid) or {}).get('freshness')
        else:
            fresh = None
        if fresh is None:
            fresh = (item.get('freshness') or {}).get('state')
        if order.get(fresh, 0) > order.get(worst, -1):
            worst = fresh
    return worst


def subject_material_state(state: dict, root: Path,
                           about: str | None,
                           report: dict | None = None) -> str | None:
    """Freshness of the material an ``about`` ref points at, when it has bytes.

    Returns ``None`` when the subject carries no material to verify (entity,
    task, route, observation, decision…) or no subject is set; otherwise the
    ``material_state`` vocabulary plus ``'unknown'``: an artifact explicitly
    marked ``stale`` or ``unknown`` reports that recorded state even before
    byte inspection — the recorded invalidation is itself the subject's state.

    Same-path artifacts dominate: an ``object:``/``file:`` subject sharing a
    path with a produced artifact inherits that artifact's computed freshness
    (``report`` when given, else the recorded flag), so upstream-invalidated
    material cannot hide behind an alias whose own bytes are unchanged.
    """
    if not about:
        return None
    try:
        kind, ident = resolve_ref(state, about)
    except WikiError:
        return 'missing'
    path = recorded_sha = None
    if kind == 'object':
        item = state['objects'].get(ident) or {}
        try:
            path = (external_path(state, item['external']) if item.get('external')
                    else project_path(root, item['path']))
        except (WikiError, KeyError):
            return 'missing'
        recorded_sha = item.get('sha256')
    elif kind == 'artifact':
        item = state['artifacts'].get(ident) or {}
        fresh = (item.get('freshness') or {}).get('state')
        if fresh in ('stale', 'unknown'):
            return fresh
        try:
            path = project_path(root, item['path'])
        except (WikiError, KeyError):
            return 'missing'
        recorded_sha = item.get('sha256')
    elif kind in ('file', 'external'):
        path = _ref_path(state, root, f'{kind}:{ident}')
        if path is None:
            return 'missing'
    else:
        return None
    alias = _artifact_freshness_for(state, root, path, report)
    if alias in ('stale', 'unknown', 'unhashed'):
        return alias
    return material_state(state, root, path=path, recorded_sha=recorded_sha)


def _ref_path(state: dict, root: Path, ref: str) -> Path | None:
    """Filesystem path a ref ultimately points at, when it has one."""
    kind, ident = resolve_ref(state, ref)
    try:
        if kind == 'object':
            item = state['objects'][ident]
            return (external_path(state, item['external']) if item.get('external')
                    else project_path(root, item['path']))
        if kind == 'artifact':
            return project_path(root, state['artifacts'][ident]['path'])
        if kind == 'file':
            return project_path(root, ident)
        if kind == 'external':
            return external_path(state, ident)
    except WikiError:
        return None
    return None


def _receipt_structure_ok(receipt, run_id: str, task_id: str, dedup: str) -> bool:
    """A receipt must be a well-formed record of *this* run, not merely JSON."""
    if not isinstance(receipt, dict):
        return False
    if receipt.get('run_id') != run_id or receipt.get('task') != task_id:
        return False
    if receipt.get('status') != 'completed' or receipt.get('dedup') != dedup:
        return False
    if not isinstance(receipt.get('outputs'), list) or not receipt['outputs']:
        return False
    if not all(isinstance(o, dict) and _text(o.get('path')) for o in receipt['outputs']):
        return False
    if not isinstance(receipt.get('inputs'), list):
        return False
    if not isinstance(receipt.get('input_fingerprints'), dict):
        return False
    if not isinstance(receipt.get('checks'), list) or not receipt['checks']:
        return False
    return True


def _reusable_completed_run(state: dict, root: Path, run_id: str, task_id: str,
                            dedup: str) -> bool:
    """A prior completed run only satisfies re-use when every guard holds:

    - the receipt parses AND has the required structure/identity of this run;
    - the run recorded actual code provenance (``code_refs``) — a bound
      implementation_id is a name, not a hash of current local code; the same
      command text never proves the same code bytes (missing identity stays
      conservative, never equivalence);
    - all recorded outputs exist with their recorded fingerprints;
    - all recorded input fingerprints still match;
    - no artifact produced by that run was explicitly marked stale/unknown.
    A matching dedup key alone never counts.
    """
    run = state['runs'].get(run_id)
    if not run or run['status'] != 'completed' or run.get('dedup') != dedup \
            or run['task'] != task_id:
        return False
    receipt_path = state_dir(root) / run['receipt']
    try:
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    if not _receipt_structure_ok(receipt, run_id, task_id, dedup):
        return False
    if not receipt.get('code_refs'):
        # An implementation_id names a branch; it is not a hash of the current
        # local code/manifest/resources. Equivalent-run reuse requires actual
        # recorded code provenance for every task, canonical branches included.
        return False
    artifact_paths = {item['path']: item for item in state['artifacts'].values()
                      if item.get('produced_by') == run_id}
    for item in artifact_paths.values():
        if (item.get('freshness') or {}).get('state') != 'current':
            return False  # explicit stale/unknown mark survives byte equality
    for out in receipt['outputs']:
        artifact = artifact_paths.get(out['path'])
        if artifact is None:
            return False  # receipt output not registered as this run's artifact
        if out.get('sha256') != artifact.get('sha256'):
            return False  # receipt disagrees with the registered artifact record
        try:
            path = project_path(root, out['path'])
        except WikiError:
            return False
        if material_state(state, root, path=path,
                          recorded_sha=out.get('sha256')) != 'current':
            return False
    for ref, fp in receipt['input_fingerprints'].items():
        try:
            kind, ident = resolve_ref(state, ref)
        except WikiError:
            return False
        current = _ref_fingerprint(state, root, kind, ident)
        if fp is None or current != fp:
            return False
    return True


def run_evidence_failures(state: dict, root: Path, run_id: str,
                          report: dict | None = None) -> list[str]:
    """Authoritative current-evidence failures for a completed run — one shared
    provenance check for use-registration/reuse/reporting instead of per-caller
    ad-hoc guards. An empty list means the run's recorded evidence still holds
    against current bytes; ``report`` (a ``check_project`` report) supplies
    computed artifact freshness when given, else recorded flags are used.

    Guarded facts: receipt structure+identity, actual code provenance
    (``code_refs`` — a bound implementation_id is a name, not a hash), receipt
    output hashes agreeing with both the registered artifact record and the
    current file bytes, every recorded material input fingerprint, and no
    produced artifact marked stale/unknown (recorded or computed).
    """
    failures = []
    run = state['runs'].get(run_id)
    if run is None:
        return [f'run 未登记: {run_id}']
    if run['status'] != 'completed':
        return [f'run {run_id} 登记状态为 {run["status"]}；非完成运行']
    receipt_path = state_dir(root) / run['receipt']
    try:
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [f'run {run_id} 收据缺失或不可读: {error}']
    if not _receipt_structure_ok(receipt, run_id, run['task'], run.get('dedup')):
        return [f'run {run_id} 收据结构不完整或与本 run 不一致']
    if receipt.get('status') != 'completed':
        failures.append(f'收据状态为 {receipt.get("status")}；非完成运行')
    if not receipt.get('code_refs'):
        failures.append('未登记实际代码来源（code_refs）；'
                        'implementation_id 是分支名不是当前代码哈希')
    by_path = {}
    for aid, item in state['artifacts'].items():
        if item.get('produced_by') != run_id:
            continue
        by_path[item['path']] = (aid, item)
        if report is not None:
            fresh = ((report.get('artifacts') or {}).get(aid) or {}).get('freshness')
        else:
            fresh = None
        if fresh is None:
            fresh = (item.get('freshness') or {}).get('state')
        if fresh != 'current':
            failures.append(f'产物 {item["path"]} 新鲜度为 {fresh or "不可核查"}；'
                            'stale/unknown/不可核对的产物不作证据')
    for out in receipt['outputs']:
        found = by_path.get(out['path'])
        if found is None:
            failures.append(f'收据输出 {out["path"]} 未登记为本 run 产物')
            continue
        aid, item = found
        out_sha = out.get('sha256')
        if not out_sha:
            failures.append(f'收据输出 {out["path"]} 无指纹记录')
        elif out_sha != item.get('sha256'):
            failures.append(f'收据输出 {out["path"]} 指纹与登记产物不一致')
        try:
            path = project_path(root, item['path'])
        except (WikiError, KeyError):
            failures.append(f'产物 {out["path"]} 路径不可解析')
            continue
        material = material_state(state, root, path=path,
                                  recorded_sha=item.get('sha256'))
        if material != 'current':
            failures.append(f'产物 {out["path"]} 文件状态 {material}')
    for ref, fp in (receipt.get('input_fingerprints') or {}).items():
        try:
            kind, ident = resolve_ref(state, ref)
        except WikiError as error:
            failures.append(f'输入 {ref} 当前不可解析: {error}')
            continue
        if kind not in ('object', 'artifact', 'file', 'external'):
            continue  # non-material refs carry no bytes to verify
        if kind in ('object', 'artifact'):
            # Registry refs need a registered baseline — a receipt fingerprint
            # snapshotted at run time is not a baseline when the object itself
            # was registered unhashed.
            item = (state['objects'] if kind == 'object'
                    else state['artifacts']).get(ident) or {}
            base_sha = item.get('sha256')
            if not base_sha:
                failures.append(f'输入 {ref} 登记记录无基线指纹；'
                                'unhashed 输入不能证明现行')
            elif fp != base_sha:
                failures.append(f'输入 {ref} 收据指纹与登记基线不一致')
            elif _ref_fingerprint(state, root, kind, ident) != base_sha:
                failures.append(f'输入 {ref} 当前字节与登记基线不一致')
            continue
        current = _ref_fingerprint(state, root, kind, ident)
        if fp is None:
            failures.append(f'输入 {ref} 无指纹记录；'
                            'unhashed 输入不能证明现行')
        elif current != fp:
            failures.append(f'输入 {ref} 指纹已变化；该运行不再代表当前输入状态')
    return failures


def record_run(root: Path, run_id: str, task_id: str, *, status: str,
               command: str = '', inputs=None, outputs=(), checks=(),
               params=None, environment=None, code=(), note=None,
               expected_revision=None) -> dict:
    """Register a run the agent already performed; never executes anything.

    ``completed`` requires evidence: a command, at least one existing output
    file (fingerprinted into an artifact) and at least one check the caller
    actually verified. A bare status flag can never mark scientific or
    algorithm verification — those axes are not writable here.

    ``inputs=None`` defaults to the task's declared inputs; an explicit list
    must contain every declared input (extra code/resource/weight refs are
    welcome). ``params=None`` defaults to the task's declared params; explicit
    params must agree with declared keys. ``code`` lists the actual
    code/manifest/resource refs the run used — joined into inputs for
    fingerprinting and into the dedup identity; without any recorded code
    provenance (``code`` or a bound implementation) a later identical-looking
    run is never silently reused.
    """
    run_id = _check_id(run_id, 'run id')
    if status not in RUN_STATUSES:
        raise WikiError(f'status 必须为 {"、".join(RUN_STATUSES)}')
    root = Path(root)
    state = load_project(root)
    if task_id not in state['tasks']:
        raise WikiError(f'任务未登记: {task_id}（先 add-task）')
    task = state['tasks'][task_id]
    existing = state['runs'].get(run_id)
    if existing is not None:
        if existing['status'] != 'running' or status == 'running':
            raise WikiError(f'run {run_id} 已存在且为 {existing["status"]}；运行记录不可覆盖')
    declared = list(task.get('inputs') or [])
    if inputs is None:
        inputs = declared
    else:
        missing = sorted(set(declared) - set(_canonical_refs(state, root, inputs)))
        if missing:
            raise WikiError(f'运行输入缺少任务已声明的依赖: {"、".join(missing)}'
                            '；不可静默丢弃声明依赖')
    inputs = _canonical_refs(state, root, inputs)
    code_refs = _canonical_refs(state, root, code or ())
    # Code refs join the recorded dependency set for fingerprinting/impact;
    # the receipt keeps them visible separately as provenance.
    for ref in code_refs:
        if ref not in inputs:
            inputs.append(ref)
    declared_params = dict(task.get('params') or {})
    if params is None:
        params = declared_params
    else:
        disagree = sorted(k for k, v in declared_params.items()
                          if k in params and params[k] != v)
        if disagree:
            raise WikiError(f'运行参数与任务声明不一致: {"、".join(disagree)}')
        params = {**declared_params, **dict(params)}
    input_fps = {ref: _ref_fingerprint(state, root, *resolve_ref(state, ref))
                 for ref in inputs}
    dedup = _dedup_fingerprint(task, input_fps, params, command, environment,
                               code_refs)
    if status == 'completed':
        for rid, run in state['runs'].items():
            if rid != run_id and run['task'] == task_id \
                    and _reusable_completed_run(state, root, rid, task_id, dedup):
                return {'run_id': run_id, 'status': status, 'duplicate_of': rid}
        if not _text(command):
            raise WikiError('completed 运行必须记录实际命令')
        if not outputs:
            raise WikiError('completed 运行必须列出至少一个输出文件')
        if not checks or any(not _text(item) for item in checks):
            raise WikiError('completed 运行必须列出实际检查项')
    out_records = []
    out_paths = []
    for output in outputs:
        path = project_path(root, output, '输出路径')
        if path in out_paths:
            raise WikiError(f'输出路径重复: {output}')
        out_paths.append(path)
        if status == 'completed' and not path.is_file():
            raise WikiError(f'输出文件不存在: {output}；不以文件存在认定完成，但完成运行须有产物')
        out_records.append({'path': output,
                            'sha256': _sha(path) if path.is_file() else None,
                            'bytes': path.stat().st_size if path.is_file() else None})
    for ref in inputs:
        path = _ref_path(state, root, ref)
        if path is not None and path in out_paths:
            raise WikiError(f'输出与输入指向同一文件: {ref}（不可把声明输入写成产物）')
    receipt = {'schema_version': 1, 'run_id': run_id, 'task': task_id, 'status': status,
               'command': command, 'inputs': inputs, 'input_fingerprints': input_fps,
               'code_refs': code_refs,
               'outputs': out_records, 'checks': list(checks),
               'params': dict(params or {}), 'environment': dict(environment or {}),
               'dedup': dedup, 'note': note, 'at': _now(),
               'scope': '工作状态记录；不授予算法或科学验证，解释范围另行审查'}
    run_dir = state_dir(root) / 'runs' / run_id
    receipt_path = run_dir / 'receipt.json'

    def mutate(state):
        # Authoritative checks under the lock (the earlier read may be stale).
        prev = state['runs'].get(run_id)
        if prev is not None and (prev['status'] != 'running' or status == 'running'):
            raise WikiError(f'run {run_id} 已存在且为 {prev["status"]}；运行记录不可覆盖')
        if status == 'completed':
            for rid, run in state['runs'].items():
                if rid != run_id and run['task'] == task_id \
                        and run.get('dedup') == dedup \
                        and _reusable_completed_run(state, root, rid, task_id, dedup):
                    raise WikiError(f'重复运行: 与已完成 run {rid} 指纹一致，不重复登记')
        state = dict(state)
        runs = dict(state['runs'])
        tasks = dict(state['tasks'])
        artifacts = dict(state['artifacts'])
        runs[run_id] = {'id': run_id, 'task': task_id, 'status': status,
                        'receipt': f'runs/{run_id}/receipt.json', 'at': receipt['at'],
                        'dedup': dedup}
        task_now = dict(tasks[task_id])
        task_now['status'] = 'completed' if status == 'completed' else (
            'running' if status == 'running' else 'failed' if status == 'failed'
            else task_now['status'])
        tasks[task_id] = task_now
        if status == 'completed':
            for out in out_records:
                for aid, item in artifacts.items():
                    if item['path'] == out['path'] and item['produced_by'] != run_id:
                        item = dict(item)
                        item['freshness'] = {'state': 'stale', 'checked_at': _now(),
                                             'reason': f'产物路径被 run {run_id} 覆盖'}
                        artifacts[aid] = item
                aid = _artifact_id(run_id, out['path'])
                artifacts[aid] = {'id': aid, 'path': out['path'], 'kind': 'file',
                                  'sha256': out['sha256'], 'bytes': out.get('bytes'),
                                  'produced_by': run_id,
                                  'inputs': inputs,
                                  'freshness': {'state': 'current', 'checked_at': receipt['at'],
                                                'reason': ''}}
        state.update(runs=runs, tasks=tasks, artifacts=artifacts)
        return state, ('run', f'登记运行 {run_id}（{task_id}/{status}）')

    run_dir.mkdir(parents=True, exist_ok=True)
    # Stage the receipt as .tmp; update_project commits it inside the locked
    # transaction — before project.json, after revision/validation — so state
    # and receipt can never disagree at any failure boundary. A rejected
    # revision check leaves the existing receipt untouched.
    receipt_tmp = run_dir / 'receipt.json.tmp'
    if existing is None or existing['status'] == 'running':
        receipt_tmp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n',
                               encoding='utf-8')
    warnings = []
    try:
        update_project(root, mutate, expected_revision=expected_revision,
                       staged=[(receipt_tmp, receipt_path)], warnings_out=warnings)
    except BaseException:
        receipt_tmp.unlink(missing_ok=True)
        if existing is None:
            try:
                run_dir.rmdir()
            except OSError:
                pass
        raise
    result = {'run_id': run_id, 'status': status, 'duplicate_of': None}
    if warnings:
        result['derived_warnings'] = warnings
    return result


# ---------------------------------------------------------------- read views

def project_status(root: Path) -> dict:
    root = Path(root)
    state = load_project(root)
    tasks_by_status: dict[str, int] = {}
    for task in state['tasks'].values():
        tasks_by_status[task['status']] = tasks_by_status.get(task['status'], 0) + 1
    artifacts_by_freshness: dict[str, int] = {}
    for artifact in state['artifacts'].values():
        st = artifact['freshness']['state']
        artifacts_by_freshness[st] = artifacts_by_freshness.get(st, 0) + 1
    obs_by_basis: dict[str, int] = {}
    for obs in state['observations'].values():
        obs_by_basis[obs['basis']] = obs_by_basis.get(obs['basis'], 0) + 1
    return {
        'project_id': state['project_id'], 'title': state['title'],
        'revision': state['revision'], 'schema_version': state['schema_version'],
        'project_root': state['project_root'],
        'profiles': state['profile_refs'],
        'counts': {
            'entities': len(state['entities']), 'objects': len(state['objects']),
            'observations': obs_by_basis, 'routes': len(state['routes']),
            'tasks': tasks_by_status, 'artifacts': artifacts_by_freshness,
            'runs': len(state['runs']), 'decisions': len(state['decisions']),
            'authorizations': len(state['authorizations']),
            'lessons': {s: sum(1 for i in state['lessons'].values() if i['status'] == s)
                        for s in LESSON_STATUSES},
        },
        'routes': [{'id': r['id'], 'question': r['question'], 'decision': r['decision']}
                   for r in state['routes'].values()],
        'tasks': [{'id': t['id'], 'status': t['status'], 'role': t['role'],
                   'family_id': t['family_id'], 'implementation_id': t['implementation_id']}
                  for t in state['tasks'].values()],
        'pending': {
            'routes_undecided': [r['id'] for r in state['routes'].values()
                                 if r['decision'] == 'pending'],
            'tasks_running': [t['id'] for t in state['tasks'].values()
                              if t['status'] == 'running'],
            'tasks_blocked': [t['id'] for t in state['tasks'].values()
                              if t['status'] == 'blocked'],
            'stale_artifacts': [a['id'] for a in state['artifacts'].values()
                                if a['freshness']['state'] == 'stale'],
        },
        'legacy_contexts': state['legacy_contexts'],
        'recent_events': state['events'][-5:],
        'note': 'completed 是工作状态；算法验证与科学解释为独立轴，不由状态授予。',
    }


def check_project(root: Path, config=None) -> dict:
    """Read-only integrity and freshness report; unknown prerequisites stay unknown."""
    root = Path(root)
    state = load_project(root)
    errors = validate_state(state)
    objects = {}
    for oid, item in state['objects'].items():
        try:
            path = (external_path(state, item['external']) if item.get('external')
                    else project_path(root, item['path']))
        except WikiError:
            objects[oid] = {'state': 'unknown', 'reason': '路径无法解析或数据根已移除'}
            continue
        result = material_state(state, root, path=path, recorded_sha=item.get('sha256'))
        objects[oid] = {'state': result,
                        'path': item.get('path') or item.get('external')}
        if result == 'unhashed':
            objects[oid]['reason'] = '登记时未记录指纹'
    artifacts = {}
    for aid, item in state['artifacts'].items():
        run = state['runs'].get(item['produced_by'])
        reasons, stale = [], False
        if run is None:
            reasons.append('产出 run 未登记')
            artifacts[aid] = {'freshness': 'unknown', 'reasons': reasons, 'path': item['path']}
            continue
        receipt_path = state_dir(root) / run['receipt']
        receipt = None
        if receipt_path.is_file():
            try:
                receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError):
                pass
        if receipt is None:
            artifacts[aid] = {'freshness': 'unknown',
                              'reasons': ['run 收据缺失或不可读'], 'path': item['path']}
            continue
        recorded = receipt.get('input_fingerprints') or {}
        for ref in item.get('inputs') or []:
            if ref.startswith('artifact:'):
                continue  # freshness propagates through the dependency pass below
            try:
                kind, ident = resolve_ref(state, ref)
            except WikiError:
                reasons.append(f'输入 {ref} 不可解析')
                continue
            current = _ref_fingerprint(state, root, kind, ident)
            old = recorded.get(ref)
            if current is None:
                reasons.append(f'输入 {ref} 当前无法核对')
            elif old is not None and current != old:
                stale = True
                reasons.append(f'输入 {ref} 指纹已变化')
        path = project_path(root, item['path'])
        material = material_state(state, root, path=path,
                                  recorded_sha=item.get('sha256'))
        if material == 'missing':
            stale = True
            reasons.append('产物文件缺失')
        elif material == 'stale':
            stale = True
            reasons.append('产物文件指纹已变化')
        elif material == 'unhashed':
            reasons.append('产物存在但未记录指纹，无法证明字节未变')
        artifacts[aid] = {'freshness': 'stale' if stale else ('unknown' if reasons else 'current'),
                          'reasons': reasons, 'path': item['path']}
    # Transitive freshness propagation through declared artifact dependencies:
    # a stale/unknown upstream artifact contaminates consumers even when the
    # intermediate file bytes have not changed. ``file:<artifact-path>`` and
    # ``artifact:<id>`` are aliases of the same declared dependency. Bounded
    # fixpoint, so cycles terminate; cycles are rejected at write time anyway.
    artifact_by_path = {item['path']: aid for aid, item in state['artifacts'].items()}
    for _ in range(len(artifacts)):
        changed_any = False
        for aid, item in state['artifacts'].items():
            entry = artifacts.get(aid)
            if entry is None:
                continue
            for ref in item.get('inputs') or []:
                if ref.startswith('artifact:'):
                    dep = ref.split(':', 1)[1]
                elif ref.startswith('file:'):
                    dep = artifact_by_path.get(ref[5:])
                    if dep is None or dep == aid:
                        continue
                else:
                    continue
                dep_entry = artifacts.get(dep)
                if dep_entry is None:
                    if entry['freshness'] == 'current':
                        entry['freshness'] = 'unknown'
                        entry['reasons'].append(f'上游产物 {ref} 无法核查')
                        changed_any = True
                    continue
                if dep_entry['freshness'] == 'stale' and entry['freshness'] != 'stale':
                    entry['freshness'] = 'stale'
                    entry['reasons'].append(f'上游产物 {ref} 已 stale')
                    changed_any = True
                elif dep_entry['freshness'] == 'unknown' and entry['freshness'] == 'current':
                    entry['freshness'] = 'unknown'
                    entry['reasons'].append(f'上游产物 {ref} 新鲜度 unknown')
                    changed_any = True
        if not changed_any:
            break
    observations = {}
    for oid, item in state['observations'].items():
        # Subject freshness is the *computed* one: an observation about an
        # artifact sees propagated upstream staleness, not just the artifact's
        # own unchanged bytes or recorded flag.
        about = item.get('about')
        subject = None
        if isinstance(about, str) and about.startswith('artifact:'):
            aid = about.split(':', 1)[1]
            entry = artifacts.get(aid)
            if entry is not None:
                subject = entry['freshness']
        if subject is None:
            # object:/file: subjects sharing a path with a produced artifact
            # inherit its computed freshness — same truth as evaluate.
            subject = subject_material_state(state, root, about,
                                             report={'artifacts': artifacts})
        observations[oid] = {'basis': item['basis'], 'value': item['value'],
                             'evidence': evidence_state(state, root, item.get('evidence')),
                             'subject': subject}
    tasks = {}
    for tid, item in state['tasks'].items():
        deps = list(item.get('inputs') or [])
        via, bad, unsure = [], [], []
        for ref in deps:
            try:
                kind, ident = resolve_ref(state, ref)
            except WikiError:
                unsure.append(ref)
                continue
            if kind == 'artifact' and artifacts.get(ident, {}).get('freshness') in ('stale',):
                bad.append(ref)
            elif kind == 'artifact' and artifacts.get(ident, {}).get('freshness') == 'unknown':
                unsure.append(ref)
            elif kind == 'object' and objects.get(ident, {}).get('state') in ('missing', 'stale'):
                bad.append(ref)
            elif kind == 'object' and objects.get(ident, {}).get('state') in ('unknown', 'unhashed'):
                unsure.append(ref)
            elif kind in ('file', 'external'):
                path = _ref_path(state, root, ref)
                if path is None or not path.exists():
                    unsure.append(ref)
            via.append(ref)
        state_v = 'at_risk' if bad else ('uncertain' if unsure or not deps else 'ok')
        tasks[tid] = {'state': state_v, 'via': via,
                      'reason': ('依赖已失效: ' + '、'.join(bad)) if bad else
                                ('依赖不可核查' if (unsure or not deps) else '')}
    runs = {rid: {'receipt': 'present' if (state_dir(root) / run['receipt']).is_file() else 'missing',
                  'status': run['status'], 'task': run['task']}
            for rid, run in state['runs'].items()}
    wiki_refs = {}
    if config is not None:
        try:
            from .method_implementations import implementation_status
            wiki_root = Path(config.wiki_root)
            for task in state['tasks'].values():
                family = task.get('family_id')
                if not family:
                    continue
                page = wiki_root / 'methods' / f'{family}.md'
                entry = {'page': 'found' if page.is_file() else 'missing'}
                iid = task.get('implementation_id')
                if page.is_file() and iid:
                    try:
                        statuses = implementation_status(page)
                        match = next((s for s in statuses if s['id'] == iid), None)
                        entry['implementation'] = match['state'] if match else 'missing'
                    except Exception:
                        entry['implementation'] = 'unknown'
                wiki_refs[family] = entry
        except Exception:
            wiki_refs = {'_error': 'wiki 引用核查失败，按 unknown 处理'}
    return {'schema_ok': not errors, 'errors': errors,
            'objects': objects, 'observations': observations,
            'artifacts': artifacts, 'runs': runs, 'tasks': tasks,
            'wiki_refs': wiki_refs,
            'note': '未核查的前提保持 unknown；退出码不代表科学验证。'}


# ---------------------------------------------------------------- impact

def _impact_nodes(state: dict) -> dict:
    """Dependency graph: consumers -> the refs they consume."""
    consumers = {}
    for aid, item in state['artifacts'].items():
        consumers[f'artifact:{aid}'] = {'inputs': list(item.get('inputs') or []),
                                        'path': item['path'], 'kind': 'artifact'}
    for tid, item in state['tasks'].items():
        consumers[f'task:{tid}'] = {'inputs': list(item.get('inputs') or []),
                                    'path': None, 'kind': 'task'}
    return consumers


def _changed_refs(state: dict, root: Path, changed) -> set[str]:
    refs = set()
    for ref in changed:
        kind, ident = resolve_ref(state, ref)
        if kind == 'file':
            project_path(root, ident)
            target = f'file:{ident}'
        elif kind == 'external':
            external_path(state, ident)
            target = f'external:{Path(ident).resolve()}'
        else:
            target = f'{kind}:{ident}'
        refs.add(target)
    return refs


def _change_class(state: dict, ref: str) -> str:
    """Classify a changed ref from its registered record.

    ``properties.role`` on objects (e.g. ``data``, ``style``, ``weights``,
    ``roi``, ``resource``) is a declared label; file/external refs inherit the
    owning object/artifact's label via path alias. Unregistered refs are
    ``unspecified`` — never guessed from names.
    """
    kind, _, ident = ref.partition(':')
    item = None
    if kind == 'object':
        item = state['objects'].get(ident)
    elif kind in ('file', 'external'):
        for obj in state['objects'].values():
            if obj.get('path') == ident or (
                    obj.get('external') and
                    str(Path(obj['external']).resolve()) == ident):
                item = obj
                break
    role = ((item or {}).get('properties') or {}).get('role')
    return role.strip() if _text(role) else 'unspecified'


def impact_analysis(root: Path, changed) -> dict:
    """Actual dependency impact: direct consumers, transitive, tasks, unknown.

    Only registered edges decide. An artifact and the file it produced are the
    same node: ``file:<path>`` and ``artifact:<id>`` match either way. Anything
    with unresolved or undeclared inputs is listed under ``unknown`` — never
    silently skipped.

    Each changed ref carries a declared ``change_class`` (e.g. ``style`` vs
    data/weights/roi/resource). The class propagates along affected edges: a
    node is ``style_only`` when *every* change reaching it is style-class —
    style-only changes call for re-render, not re-analysis. Data-class or
    mixed changes are ``compute``.
    """
    root = Path(root)
    state = load_project(root)
    changed_refs = _changed_refs(state, root, changed)
    class_of = {ref: _change_class(state, ref) for ref in changed_refs}
    consumers = _impact_nodes(state)
    # Real-path aliases in both directions: a changed file reaches consumers of
    # the object/artifact registered on it, and vice versa.
    path_index = {f"file:{item['path']}": f'artifact:{aid}'
                  for aid, item in state['artifacts'].items()}
    object_index = {}
    for oid, item in state['objects'].items():
        if item.get('path'):
            object_index[f"file:{item['path']}"] = f'object:{oid}'
        if item.get('external'):
            object_index[f"external:{Path(item['external']).resolve()}"] = f'object:{oid}'
    object_back = {v: k for k, v in object_index.items()}

    def aliases(ref):
        out = {ref}
        if ref in path_index:
            out.add(path_index[ref])
        if ref in object_index:
            out.add(object_index[ref])
        if ref in object_back:
            out.add(object_back[ref])
        if ref.startswith('artifact:'):
            artifact = state['artifacts'].get(ref.split(':', 1)[1])
            if artifact:
                out.add(f"file:{artifact['path']}")
        if ref.startswith('object:'):
            item = state['objects'].get(ref.split(':', 1)[1])
            if item is not None:
                if item.get('path'):
                    out.add(f"file:{item['path']}")
                if item.get('external'):
                    out.add(f"external:{Path(item['external']).resolve()}")
        return out

    for ref in list(changed_refs):
        for alias in aliases(ref):
            changed_refs.add(alias)
            class_of.setdefault(alias, class_of[ref])

    def expanded(inputs):
        match = set()
        for ref in inputs:
            match |= aliases(ref)
        return match

    affected = set(changed_refs)
    direct, seen = [], set()
    unknown = []
    for node, item in consumers.items():
        inputs = item['inputs']
        resolvable = True
        for ref in inputs:
            try:
                resolve_ref(state, ref)
            except WikiError:
                resolvable = False
        if not resolvable or (not inputs and item['kind'] == 'task'):
            unknown.append({'id': node.split(':', 1)[1], 'kind': item['kind'],
                            'path': item['path'],
                            'reason': '依赖未登记或不可解析，不能精确判断'})
            continue
        hit = sorted(expanded(inputs) & changed_refs)
        if hit:
            direct.append({'id': node.split(':', 1)[1], 'kind': item['kind'],
                           'path': item['path'], 'via': hit})
            seen.add(node)
            affected.add(node)
    # Transitive: consumers of already-affected artifacts.
    indirect = []
    frontier = set(seen)
    while frontier:
        new = set()
        for node, item in consumers.items():
            if node in affected or node in {f"task:{u['id']}" for u in unknown}:
                continue
            hit = sorted(expanded(item['inputs']) & frontier)
            if hit:
                indirect.append({'id': node.split(':', 1)[1], 'kind': item['kind'],
                                 'path': item['path'], 'via': hit})
                new.add(node)
                affected.add(node)
        frontier = new
    # Change-class fixpoint in dependency order: a node is 'style' only when
    # *every* input that is changed or affected carries the style class —
    # a single data/weights/roi/resource or unspecified upstream makes it
    # 'compute'. Nodes that never become classable (e.g. a dependency cycle
    # that slipped past write-time checks) stay conservative 'compute'.
    node_class = {}
    for _ in range(len(consumers) + 1):
        progressed = False
        for node, item in consumers.items():
            if node not in affected or node in node_class:
                continue
            relevant = [r for r in expanded(item['inputs'])
                        if r in changed_refs or r in affected]
            if any(r in affected and r not in class_of for r in relevant):
                continue  # upstream not classed yet; retry next round
            cls = ('style' if relevant and
                   all(class_of.get(r) == 'style' for r in relevant)
                   else 'compute')
            node_class[node] = cls
            class_of[node] = cls
            for alias in aliases(node):
                class_of[alias] = cls
            progressed = True
        if not progressed:
            break

    def classify(entry):
        entry = dict(entry)
        entry['change_class'] = node_class.get(f"{entry['kind']}:{entry['id']}",
                                               'compute')
        return entry

    direct = [classify(item) for item in direct]
    indirect = [classify(item) for item in indirect]
    tasks = []
    for item in [*direct, *indirect]:
        if item['kind'] == 'task':
            item = dict(item)
            item['effect'] = 'style_only' if item.get('change_class') == 'style' else 'compute'
            tasks.append(item)
    return {'changed': sorted(changed_refs),
            'direct': [item for item in direct if item['kind'] == 'artifact'],
            'indirect': [item for item in indirect if item['kind'] == 'artifact'],
            'tasks': tasks, 'unknown': unknown,
            'note': '影响判断只基于已登记依赖；未登记项列入 unknown，不伪称精确跳过。'}


def _pid_liveness(pid) -> str | None:
    """Read-only process-liveness query: 'live', 'dead', or None (unknown).

    NEVER signals: on Windows ``os.kill(pid, 0)`` is GenerateConsoleCtrlEvent,
    an actual CTRL_C delivery to a process *group* — not the POSIX read probe.
    Nonpositive or unparseable pids return unknown without touching any API.
    Permission errors and unreadable handles mean unknown — never proof of
    absence. Pid reuse means even 'dead' is scoped to the recorded pid only.
    """
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return None
    if pid <= 0:
        return None
    if sys.platform == 'win32':
        try:
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            # HANDLE is pointer-sized: default c_int restype truncates on Win64
            # and can turn a valid handle into a false unknown/leaked handle.
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL,
                                             wintypes.DWORD]
            kernel32.GetExitCodeProcess.restype = wintypes.BOOL
            kernel32.GetExitCodeProcess.argtypes = [
                wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            kernel32.CloseHandle.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            handle = kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
            if not handle:
                error = ctypes.get_last_error()
                if error == 5:    # ERROR_ACCESS_DENIED -> exists, unverifiable
                    return 'live'
                if error == 87:   # ERROR_INVALID_PARAMETER -> positive pid absent
                    return 'dead'
                return None
            try:
                code = wintypes.DWORD()
                if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                    return None
                return 'live' if code.value == 259 else 'dead'  # STILL_ACTIVE
            finally:
                kernel32.CloseHandle(handle)
        except (OSError, AttributeError):
            return None
    else:
        # POSIX: signal 0 is the documented read-only existence probe there.
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return 'dead'
        except PermissionError:
            return 'live'
        except OSError:
            return None
        return 'live'


def _inside_state_dir(directory: Path, target: Path) -> bool:
    """True only when target resolves inside the state dir and is no link."""
    try:
        resolved = target.resolve(strict=False)
        if not resolved.is_relative_to(directory.resolve()):
            return False
        if target.is_symlink():
            return False
        if hasattr(target, 'is_junction') and target.is_junction():
            return False
    except OSError:
        return False
    return True


def recover_project(root: Path, *, release_lock=False, clean_staging=False,
                    clean_orphans=False) -> dict:
    """Inspectable interruption recovery; read-only unless repairs are explicit.

    Reports (never guesses): writer lock presence/pid/liveness, ``running``
    runs and their receipts, uncommitted ``.tmp`` staging files, orphan run
    dirs not referenced by *the current committed state* (the check scope is
    exactly that — earlier revisions are not scanned), and a missing derived
    summary.

    Repairs fail closed and are serialized: ``release_lock`` unlinks a lock
    only when the recorded pid is verifiably dead AND a same-bytes identity
    re-check passes immediately beforehand — live, unknown, malformed,
    nonpositive-pid, or replaced locks are refused. ``clean_staging`` /
    ``clean_orphans`` first acquire the writer lock themselves (a held lock
    means an active writer — never clean underneath one), refuse while any
    run is ``running`` (unresolved state), and *quarantine* rather than
    delete: targets are moved under ``_quarantine/`` inside the state dir so
    transaction evidence stays inspectable. Targets must resolve inside the
    state directory; symlinks/junctions are refused, never followed.
    """
    root = Path(root)
    state = load_project(root)
    directory = state_dir(root)
    report = {'lock': {'present': False}, 'running_runs': [], 'staging_tmps': [],
              'orphan_receipts': [],
              'summary_present': (directory / SUMMARY_FILE).is_file(),
              'actions': [], 'cautions': []}
    lock = directory / LOCK_FILE
    lock_alive = None
    lock_identity = None  # (raw bytes, ino, mtime_ns, size) captured pre-probe
    if lock.is_file():
        entry = {'present': True, 'path': str(lock)}
        raw = None
        try:
            stat0 = lock.stat()
            raw = lock.read_bytes()
            lock_identity = (raw, getattr(stat0, 'st_ino', None),
                             stat0.st_mtime_ns, stat0.st_size)
            entry['pid'] = int(raw.decode('utf-8', 'replace').strip())
        except (OSError, ValueError):
            entry['note'] = '锁内容不可读或 pid 非法；按 unknown 处理'
        lock_alive = _pid_liveness(entry.get('pid'))
        entry['liveness'] = lock_alive or 'unknown'
        if lock_alive == 'live':
            entry['note'] = 'pid 可达且仍活动（存在 pid 复用可能）；按活动处理'
        elif lock_alive == 'dead':
            entry['note'] = '记录的 pid 已不存在；仍仅限该 pid，须再核对锁未被替换'
        else:
            entry['note'] = '写者状态无法核实（含 pid 复用/权限/非法内容）；按 unknown 保守处理'
        report['lock'] = entry

    def running_entries(st):
        entries = []
        for rid, run in st['runs'].items():
            if run['status'] != 'running':
                continue
            receipt = directory / run['receipt']
            entries.append(
                {'run': rid, 'task': run['task'],
                 'receipt_present': receipt.is_file(),
                 'note': '登记为 running；是否仍在执行须人工核对，不自动判失败'})
        return entries

    report['running_runs'] = running_entries(state)

    def scan(st):
        tmps, orphans = [], []
        for tmp in sorted(directory.rglob('*.tmp')):
            rel = tmp.relative_to(directory)
            if '_quarantine' in rel.parts:
                continue  # retained evidence is not active staging
            tmps.append(str(rel))
        runs_dir = directory / 'runs'
        if runs_dir.is_dir():
            for child in sorted(runs_dir.iterdir()):
                if child.is_dir() and child.name != '_quarantine' \
                        and child.name not in st['runs']:
                    orphans.append(
                        {'dir': str(child.relative_to(directory)),
                         'receipt_present': (child / 'receipt.json').is_file(),
                         'note': '收据存在但未被当前已提交状态引用（中断事务遗留；'
                                 '核查范围仅限当前状态）'})
        return tmps, orphans

    report['staging_tmps'], report['orphan_receipts'] = scan(state)
    mutations = release_lock or clean_staging or clean_orphans
    # Mutating repairs require an unresolved-free project: a registered
    # 'running' run means state itself is undecided — fail closed, humans
    # decide via record-run --status failed first.
    if mutations and report['running_runs']:
        report['cautions'].append(
            '存在 running 运行，未决状态下拒绝任何恢复性写动作；'
            '先人工核对并显式 record-run --status failed')
        mutations = False
        release_lock = clean_staging = clean_orphans = False
    if release_lock and lock.is_file():
        if lock_alive != 'dead':
            report['cautions'].append(
                f'拒绝释放锁：写者活性为 {lock_alive or "unknown"}（仅可释放证实无主的锁）')
        else:
            # Identity re-check against the ORIGINAL pre-probe bytes/stat: the
            # 'dead' verdict scoped to the recorded pid — a lock replaced during
            # recovery belongs to a different owner and fails closed.
            same = False
            before = None
            try:
                stat1 = lock.stat()
                raw1 = lock.read_bytes()
                same = (lock_identity is not None
                        and raw1 == lock_identity[0]
                        and getattr(stat1, 'st_ino', None) == lock_identity[1]
                        and stat1.st_mtime_ns == lock_identity[2]
                        and stat1.st_size == lock_identity[3])
                before = raw1
            except OSError:
                same = False
            if same:
                try:
                    lock.unlink()
                    report['actions'].append(
                        f'已释放锁 {lock.name}（记录 pid 不可达且锁内容与探测前'
                        f'同一文件同一字节；被释放锁内容长度 {len(before or b"")}）')
                except OSError as error:
                    report['cautions'].append(f'锁释放失败: {error}')
            else:
                report['cautions'].append('锁在复核期间被替换或不可读；拒绝释放')
    if clean_staging or clean_orphans:
        # Serialize with real writers: a held lock proves an active writer —
        # never clean underneath one. Acquire our own; refuse if held.
        held_fd = None
        if lock.is_file():
            report['cautions'].append('锁文件仍存在，拒绝清理（可能有活动写者；先核实并释放）')
        else:
            try:
                held_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                report['cautions'].append('无法取得恢复序列化锁（另一写者活跃？）；拒绝清理')
            except OSError as error:
                report['cautions'].append(f'无法创建恢复锁: {error}')
        if held_fd is not None:
            try:
                os.write(held_fd, str(os.getpid()).encode())
                # Reload and re-validate UNDER the held lock: the initial state
                # may predate runs committed in the meantime — a receipt that
                # became referenced must never be classified orphan.
                locked_state = load_project(root)
                locked_running = running_entries(locked_state)
                if locked_running:
                    report['cautions'].append(
                        '恢复锁内重读状态发现 running 运行；拒绝清理，先人工核对')
                else:
                    quarantine = directory / '_quarantine' / \
                        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
                    moved_t, moved_o = 0, 0
                    tmps, orphans = scan(locked_state)
                    if clean_staging:
                        for rel in tmps:
                            target = directory / rel
                            if not _inside_state_dir(directory, target):
                                report['cautions'].append(
                                    f'暂存目标越界或为链接，跳过: {rel}')
                                continue
                            dest = quarantine / 'staging' / rel
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            shutil.move(str(target), str(dest))
                            moved_t += 1
                    if clean_orphans:
                        for item in orphans:
                            target = directory / item['dir']
                            if not _inside_state_dir(directory, target):
                                report['cautions'].append(
                                    f'孤儿目标越界或为链接，跳过: {item["dir"]}')
                                continue
                            dest = quarantine / 'orphans' / target.name
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            shutil.move(str(target), str(dest))
                            moved_o += 1
                    if moved_t:
                        report['actions'].append(
                            f'隔离保留未提交暂存 {moved_t} 个至 {quarantine.relative_to(directory)}/staging/（未删除）')
                    if moved_o:
                        report['actions'].append(
                            f'隔离保留孤儿收据目录 {moved_o} 个至 {quarantine.relative_to(directory)}/orphans/（未删除）')
            finally:
                os.close(held_fd)
                lock.unlink(missing_ok=True)
    report['staging_tmps'], report['orphan_receipts'] = scan(state)
    if report['running_runs']:
        report['cautions'].append('running 运行未自动改判；确认失败后显式 record-run --status failed')
    if report['staging_tmps']:
        report['cautions'].append('存在未提交 .tmp 暂存；--clean-staging 可隔离保留（不删除）')
    if report['lock']['present'] and not any('释放锁' in a for a in report['actions']):
        report['cautions'].append('锁仍在：写者活性无法证实时不会释放；先人工核实')
    if report['orphan_receipts'] and not clean_orphans:
        report['cautions'].append('孤儿收据目录未被当前状态引用；确认后 --clean-orphans 隔离保留')
    if not report['summary_present']:
        report['cautions'].append('summary.md 缺失；为派生文件，下次任意状态写入会重新生成')
    report['note'] = ('恢复仅处理状态目录内部事务边界；不发信号、不重启进程、'
                      '不删除原始输出、隔离而非销毁证据、不声称跨文件断电原子性。')
    return report


def mark_stale(root: Path, report: dict, *, reason: str = '', expected_revision=None) -> dict:
    """Apply an impact report to artifact freshness. Direct+indirect -> stale;
    unknown-scope items -> unknown. Nothing is recomputed or deleted."""
    stale_ids = {f"artifact:{item['id']}" for item in
                 [*report.get('direct', []), *report.get('indirect', [])]
                 if item['kind'] == 'artifact'}
    unknown_ids = {item['id'] for item in report.get('unknown', [])
                   if item['kind'] == 'artifact'}
    if not stale_ids and not unknown_ids:
        return load_project(root)

    class_map = {f"artifact:{item['id']}": item.get('change_class')
                 for item in [*report.get('direct', []), *report.get('indirect', [])]
                 if item['kind'] == 'artifact'}

    def mutate(state):
        state = dict(state)
        artifacts = {}
        for aid, item in state['artifacts'].items():
            item = dict(item)
            if f'artifact:{aid}' in stale_ids:
                cls = class_map.get(f'artifact:{aid}')
                default = ('样式类输入已变化（重渲染类影响，不等同数据重算）'
                           if cls == 'style' else '上游输入已变化')
                item['freshness'] = {'state': 'stale', 'checked_at': _now(),
                                     'reason': reason or default}
            elif aid in unknown_ids:
                item['freshness'] = {'state': 'unknown', 'checked_at': _now(),
                                     'reason': reason or '依赖未登记，影响范围未知'}
            artifacts[aid] = item
        state['artifacts'] = artifacts
        return state, ('impact', f'标记受影响产物: {reason or "依赖变化"}')
    return update_project(root, mutate, expected_revision=expected_revision)
