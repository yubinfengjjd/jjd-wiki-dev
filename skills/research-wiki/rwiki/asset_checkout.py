"""Explicit Git asset hydration; sparse absence is separate from evidence quality.

Read helpers never fetch Git objects. Only fetch_assets/set_profile can ask Git
to populate files. A sparse checkout is deliberately read-only for Wiki writes.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from threading import RLock

from .errors import WikiError
from .read_cache import invalidate_cache, remember


PAGE_KINDS = ('methods', 'templates', 'recipes', 'layouts', 'scenarios',
              'interfaces', 'chart-types', 'projects', 'sources')
IDENTITY = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]*\Z')
_THREAD_LOCK = RLock()
_REPO_CACHE: dict[tuple[str, tuple[str, ...]], Path | None] = {}
_PROFILE_CACHE: dict[tuple[str, tuple[tuple[str, int, int], ...] | None], str] = {}


def _stat_file(path: Path) -> tuple[str, int, int] | None:
    try:
        if path.is_file():
            st = path.stat()
            return (str(path), st.st_mtime_ns, st.st_size)
    except OSError:
        return None
    return None


def _resolve_git_dirs(dot_git: Path) -> tuple[Path | None, Path | None]:
    """Return (gitdir, commondir) for both regular repositories and linked worktrees."""
    if dot_git.is_dir():
        return dot_git, dot_git
    if dot_git.is_file():
        try:
            text = dot_git.read_text(encoding='utf-8', errors='replace').strip()
        except OSError:
            return None, None
        for line in text.splitlines():
            if line.lower().startswith('gitdir:'):
                raw = line.split(':', 1)[1].strip()
                gd = Path(raw)
                if not gd.is_absolute():
                    gd = (dot_git.parent / gd).resolve()
                else:
                    gd = gd.resolve()
                commondir_file = gd / 'commondir'
                if commondir_file.is_file():
                    try:
                        cd_raw = commondir_file.read_text(encoding='utf-8', errors='replace').strip()
                        cd = Path(cd_raw)
                        if not cd.is_absolute():
                            cd = (gd / cd).resolve()
                        else:
                            cd = cd.resolve()
                    except OSError:
                        cd = gd
                else:
                    cd = gd
                return gd, cd
    return None, None


def _git_config_stamp(wiki_root: Path) -> tuple[tuple[str, int, int], ...] | None:
    try:
        cur = wiki_root.resolve()
    except OSError:
        return None
    for parent in (cur, *cur.parents):
        dot_git = parent / '.git'
        if not dot_git.exists():
            continue
        stamps: list[tuple[str, int, int]] = []
        if dot_git.is_file():
            dot_st = _stat_file(dot_git)
            if dot_st is not None:
                stamps.append(dot_st)
        gitdir, commondir = _resolve_git_dirs(dot_git)
        candidates: list[Path] = []
        if gitdir is not None:
            candidates.extend([
                gitdir / 'config',
                gitdir / 'config.worktree',
                gitdir / 'info' / 'sparse-checkout',
            ])
        if commondir is not None and commondir != gitdir:
            candidates.extend([
                commondir / 'config',
                commondir / 'info' / 'sparse-checkout',
            ])
        seen: set[Path] = set()
        for cand in candidates:
            if cand in seen:
                continue
            seen.add(cand)
            st = _stat_file(cand)
            if st is not None:
                stamps.append(st)
        if stamps:
            return tuple(stamps)
    return None


@contextmanager
def _mutation_lock(root):
    """Serialize sparse selection read/modify/write across threads and processes."""
    name = Path(_git(root, 'rev-parse', '--git-path', 'rwiki-assets.lock').strip())
    if not name.is_absolute():
        name = root / name
    with _THREAD_LOCK:
        with name.open('a+b') as stream:
            if stream.tell() == 0:
                stream.write(b'\0')
                stream.flush()
            stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                deadline = time.monotonic() + 60
                while True:
                    try:
                        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                        break
                    except OSError:
                        if time.monotonic() >= deadline:
                            raise WikiError('另一个资产操作仍在执行；已有文件保留，请稍后重试。')
                        time.sleep(.05)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                stream.seek(0)
                if os.name == 'nt':
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _git(root: Path, *args: str, input: str | None = None, check: bool = True) -> str:
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0')
    result = subprocess.run(['git', '-C', str(root), *args], input=input,
                            capture_output=True, text=True, encoding='utf-8', env=env)
    if check and result.returncode:
        raise WikiError('Git 资产操作失败；已有文件保留，可重试：' + result.stderr.strip())
    return result.stdout if result.returncode == 0 else ''


def repository(config) -> Path | None:
    wiki_key = os.path.normcase(str(config.wiki_root.resolve()))
    stamp = _git_config_stamp(config.wiki_root)
    cache_key = (wiki_key, tuple(item[0] for item in stamp) if stamp else ())
    with _THREAD_LOCK:
        if cache_key in _REPO_CACHE:
            return _REPO_CACHE[cache_key]
    root_text = _git(config.wiki_root, 'rev-parse', '--show-toplevel', check=False).strip()
    resolved = Path(root_text).resolve() if root_text else None
    with _THREAD_LOCK:
        _REPO_CACHE[cache_key] = resolved
    return resolved


def profile(config, *, fresh: bool = False) -> str:
    wiki_key = os.path.normcase(str(config.wiki_root.resolve()))
    stamp = _git_config_stamp(config.wiki_root)
    cache_key = (wiki_key, stamp)
    if not fresh:
        with _THREAD_LOCK:
            cached = _PROFILE_CACHE.get(cache_key)
            if cached is not None:
                return cached
    root = repository(config)
    if root is None:
        value = 'full'
    else:
        # Actual Git sparsity is authoritative; an interrupted operation must not
        # leave a configuration flag granting writes to an incomplete checkout.
        value = (
            'light'
            if _git(root, 'config', '--bool', '--get', 'core.sparseCheckout', check=False).strip() == 'true'
            else 'full'
        )
    with _THREAD_LOCK:
        _PROFILE_CACHE[cache_key] = value
    return value


def assert_writable(config) -> None:
    if profile(config) == 'light':
        raise WikiError('轻量检出仅供查找和复用；正式维护请先运行 rwiki checkout --profile full。')


def _inventory(root: Path) -> dict[str, str]:
    index_name = _git(root, 'rev-parse', '--git-path', 'index').strip()
    index = Path(index_name)
    if not index.is_absolute():
        index = root / index
    stamp = index.stat() if index.exists() else None
    key = ('checkout-tracked', root, stamp.st_mtime_ns if stamp else None,
           stamp.st_size if stamp else None)
    def read():
        return {row[2:]: row[0] for row in _git(root, 'ls-files', '-t', '-z').split('\0') if row}
    return remember(key, read)


def assets_state(config, page: Path) -> dict:
    page = Path(page).resolve()
    if not page.is_relative_to(config.wiki_root.resolve()):
        raise WikiError('资产页面超出知识库。')
    asset = page.with_suffix('')
    root = repository(config)
    mode = profile(config)
    if root is None:
        return {'state': 'available', 'profile': mode, 'missing': []}
    prefix = asset.relative_to(root).as_posix().rstrip('/') + '/'
    expected = [(name, tag) for name, tag in _inventory(root).items() if name.startswith(prefix)]
    missing = [(name, tag) for name, tag in expected if not (root / name).is_file()]
    state = ('not_downloaded' if missing and all(tag == 'S' for _, tag in missing)
             else 'missing' if missing else 'available')
    return {'state': state, 'profile': mode,
            'missing': [name for name, _ in missing], 'expected_files': len(expected)}


def _base_patterns(config, root: Path) -> list[str]:
    wiki = config.wiki_root.resolve().relative_to(root).as_posix()
    patterns = ['/README.md', '/.gitattributes', '/.gitignore', '/.push-guard-allow',
                '/tools/', '/docs/', '/.github/']
    patterns.extend(f'/{wiki}/{name}' for name in
                    ('AGENTS.md', 'CLAUDE.md', 'catalog.jsonl', 'index.md', 'log.md',
                     '.gitignore', '.protected-hashes.json'))
    # These globs select direct children, not arbitrary nested README/data files.
    for kind in PAGE_KINDS:
        patterns += [f'/{wiki}/{kind}/*.md', f'/{wiki}/{kind}/',
                     f'!/{wiki}/{kind}/*/', f'/{wiki}/{kind}/*.md']
    # Explicit metadata/thumbnail files at asset roots remain small and let a
    # reader report previous evidence without claiming current validation.
    for kind in ('methods', 'templates', 'recipes', 'layouts'):
        patterns += [f'/{wiki}/{kind}/*/runtime.json', f'/{wiki}/{kind}/*/spec.json',
                     f'/{wiki}/{kind}/*/source.json', f'/{wiki}/{kind}/*/acceptance.json',
                     f'/{wiki}/{kind}/*/preview.png']
    patterns += [f'/{wiki}/sources/*/items.jsonl', f'/{wiki}/sources/figureya-curation.json']
    return patterns


def _sparse_path(root: Path) -> Path:
    value = Path(_git(root, 'rev-parse', '--git-path', 'info/sparse-checkout').strip())
    return value if value.is_absolute() else root / value


def set_profile(config, value: str) -> dict:
    root = repository(config)
    if root is None:
        raise WikiError('轻量/完整切换需要 Git 检出。')
    with _mutation_lock(root):
        try:
            return _set_profile(config, value)
        finally:
            invalidate_cache(config.wiki_root)


def _set_profile(config, value: str) -> dict:
    if value not in ('light', 'full'):
        raise WikiError('profile 必须是 light 或 full。')
    root = repository(config)
    if root is None:
        raise WikiError('轻量/完整切换需要 Git 检出。')
    if value == profile(config, fresh=True):
        return {'profile': value, 'changed': False}
    if _git(root, 'status', '--porcelain').strip():
        raise WikiError('切换下载方式前请先保存检出中的修改；未覆盖现有文件。')
    if value == 'full':
        _git(root, 'sparse-checkout', 'disable')
    else:
        _git(root, 'sparse-checkout', 'set', '--no-cone', '--stdin',
             input='\n'.join(_base_patterns(config, root)) + '\n')
    wiki_key = os.path.normcase(str(config.wiki_root.resolve()))
    with _THREAD_LOCK:
        for k in [key for key in _PROFILE_CACHE if key[0] == wiki_key]:
            _PROFILE_CACHE.pop(k, None)
    return {'profile': profile(config, fresh=True), 'changed': True}


def _page(config, entry_id: str) -> Path:
    if not isinstance(entry_id, str) or not IDENTITY.fullmatch(entry_id) or '..' in entry_id:
        raise WikiError('条目 ID 无效；使用页面 ID，不接受路径。')
    from .aliases import DIR_TO_TYPE, resolve_page_ref

    resolved = resolve_page_ref(
        config.wiki_root,
        entry_id,
        expected_types=[DIR_TO_TYPE[kind] for kind in PAGE_KINDS],
    )
    if resolved is not None:
        return resolved
    raise WikiError(f'没有条目 {entry_id}；L0 来源获取继续使用 rwiki use。')


def _closure(config, page: Path) -> list[Path]:
    """Hydrate complete per-entry evidence and declared inter-entry templates."""
    from .pages import read_page
    pending, seen, result = [page], set(), []
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        current = current.resolve()
        if not current.is_relative_to(config.wiki_root.resolve()):
            raise WikiError('依赖页面超出知识库。')
        meta, _ = read_page(current)
        result.extend((current, current.with_suffix('')))
        for target in meta.get('templates') or []:
            pending.append(_page(config, str(target).split('/')[-1].removesuffix('.md')))
        # Interface declarations are tiny pages included by the light profile.
        for slug in (meta.get('inputs') or []) + (meta.get('outputs') or []):
            if isinstance(slug, str) and IDENTITY.fullmatch(slug):
                target = config.wiki_root / 'interfaces' / f'{slug}.md'
                if target.is_file():
                    result.append(target)
    return list(dict.fromkeys(result))


def fetch_assets(config, entry_id: str) -> dict:
    root = repository(config)
    try:
        if root is None:
            return _fetch_assets(config, entry_id)
        with _mutation_lock(root):
            return _fetch_assets(config, entry_id)
    finally:
        invalidate_cache(config.wiki_root)


def _fetch_assets(config, entry_id: str) -> dict:
    page = _page(config, entry_id)
    root = repository(config)
    state = assets_state(config, page)
    paths = _closure(config, page)
    closure_pages = [p for p in paths if p.suffix == '.md' and p.is_file()]
    states = [assets_state(config, p) for p in closure_pages]
    if all(item['state'] == 'available' for item in states):
        return {'id': entry_id, **state, 'changed': False}
    if root is None or profile(config) != 'light' or any(s['state'] == 'missing' for s in states):
        raise WikiError('资产不是稀疏检出省略的内容；请核对缺失文件，不覆盖本地修改。')
    sparse = _sparse_path(root)
    original = sparse.read_bytes()
    current = original.decode('utf-8').splitlines()
    additions = ['/' + item.resolve().relative_to(root).as_posix()
                 + ('/' if item.suffix != '.md' else '') for item in paths]
    # Adding only, never shrinking an existing user's selection. Git itself
    # refuses to overwrite modified files while populating newly included ones.
    patterns = list(dict.fromkeys([*current, *additions]))
    try:
        _git(root, 'sparse-checkout', 'set', '--no-cone', '--stdin', input='\n'.join(patterns) + '\n')
    except WikiError:
        # Retain files already downloaded by Git. Restore selection metadata,
        # but do not reapply it (which would remove partial downloads).
        sparse.write_bytes(original)
        raise
    # A template's layout may name additional entry closures; the current entry
    # itself must be fully available before a caller copies it into a project.
    state = assets_state(config, page)
    if any(assets_state(config, p)['state'] != 'available' for p in closure_pages):
        raise WikiError('资产未完整获取；已有下载保留，请检查网络后重试。')
    return {'id': entry_id, **state, 'changed': True}
