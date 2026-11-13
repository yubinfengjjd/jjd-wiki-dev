"""资产目录的路径约束：链接不能把外部文件带进快照或当作入口。

唯一例外：`gh start-task --worktree` 把被忽略的限制性许可目录（push_guard.restricted_dirs）
建成指向主检出的目录联接；它们的内容就是本页资产，不算越出。
"""
import os
from pathlib import Path


def _link(path: Path) -> bool:
    return os.path.islink(path) or os.path.isjunction(path)


def _restricted_link(link: Path, wiki_root: Path) -> bool:
    """联接/目录符号链接位于 restricted_dirs 的一项，且指向另一检出中的同一相对路径。"""
    from .pages import parse_page
    from .push_guard import restricted_page_dirs

    if not (os.path.isjunction(link) or (os.path.islink(link) and link.is_dir())):
        return False
    try:
        parts = link.relative_to(wiki_root).parts
    except ValueError:
        return False
    if len(parts) != 3:
        return False
    kind, slug, folder = parts
    page = wiki_root / kind / f"{slug}.md"
    try:
        meta, _, error = parse_page(page.read_text(encoding="utf-8"))
    except OSError:
        return False
    if error or f"{kind}/{slug}/{folder}/" not in restricted_page_dirs(kind, slug, meta):
        return False
    target = Path(os.path.realpath(link))
    if [p.casefold() for p in target.parts[-3:]] != [p.casefold() for p in parts]:
        return False
    other = target.parents[2]
    # 另一检出：不是本 wiki_root，且那里有同一页面。
    return other != wiki_root.resolve() and (other / kind / f"{slug}.md").is_file()


def confined(path: Path, root: Path, wiki_root: Path) -> bool:
    """path 是否在 root 内：解析后仍在 root 内，或只经过限制性目录的检出间联接。"""
    try:
        if Path(path).resolve().is_relative_to(Path(root).resolve()):
            return True
        base = Path(os.path.abspath(root))
        current = Path(os.path.abspath(path))
        wiki_root = Path(os.path.abspath(wiki_root))
        if not current.is_relative_to(base):
            return False
        step = base
        for part in current.relative_to(base).parts:
            step = step / part
            if _link(step) and not _restricted_link(step, wiki_root):
                return False
        return True
    except (OSError, RuntimeError, ValueError):
        return False
