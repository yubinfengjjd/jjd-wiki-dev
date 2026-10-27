import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[1]
DEV_ROOT = SKILL_ROOT.parents[1]
ENTRY_ID = "2026-08-17-shap-feature-mechanism__fig01-shap-a-f"
FAKE_GH_DIR = Path(__file__).resolve().parent / "fake_gh"
FAKE_REPO_NAMES = {"dev": "jjd-wiki-dev", "vault": "jjd-wiki"}
sys.path.insert(0, str(SKILL_ROOT))
# 这些夹具复制 DEV_ROOT/test-gallery（受版权的画廊副本，不入库），依赖它的测试只在本机运行。
LOCAL_FIXTURES = {"workspace"}
VAULT_MARKER = Path("知识库/AGENTS.md")


def vault_config_candidates() -> list[Path]:
    """本检出的 config.json，再加主检出的（worktree 中 config.json 被忽略而不存在）。"""
    candidates = [SKILL_ROOT / "config.json"]
    common = subprocess.run(["git", "-C", str(SKILL_ROOT), "rev-parse", "--path-format=absolute",
                             "--git-common-dir"], capture_output=True, text=True, encoding="utf-8")
    if common.returncode == 0 and common.stdout.strip():
        main = Path(common.stdout.strip()).parent / SKILL_ROOT.relative_to(DEV_ROOT) / "config.json"
        if main != candidates[0]:
            candidates.append(main)
    return candidates


def find_vault_root() -> Path | None:
    """vault 根：RWIKI_VAULT_ROOT → config.json 的 github.vault_root → DEV_ROOT.parent；都不是 vault 时返回 None。"""
    explicit = os.environ.get("RWIKI_VAULT_ROOT")
    if explicit:
        if not (Path(explicit) / VAULT_MARKER).is_file():
            pytest.fail(f"RWIKI_VAULT_ROOT={explicit} 下没有 {VAULT_MARKER.as_posix()}")
        return Path(explicit)
    for config in vault_config_candidates():
        try:
            root = json.loads(config.read_text(encoding="utf-8")).get("github", {}).get("vault_root")
        except (OSError, ValueError, AttributeError):
            continue
        if root and (Path(root) / VAULT_MARKER).is_file():
            return Path(root)
    fallback = DEV_ROOT.parent
    return fallback if (fallback / VAULT_MARKER).is_file() else None


@pytest.fixture
def vault_root() -> Path:
    root = find_vault_root()
    if root is None:
        pytest.skip("找不到 vault（设 RWIKI_VAULT_ROOT，或在 config.json 写 github.vault_root）")
    return root


def pytest_collection_modifyitems(items):
    for item in items:
        if LOCAL_FIXTURES & set(item.fixturenames):
            item.add_marker(pytest.mark.local)


def git_run(repo, *args, env=None):
    """测试里的 git 调用：失败直接抛出，返回 stdout。"""
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True, encoding="utf-8", env=env).stdout


def git_init(path, branch="main"):
    path.mkdir(parents=True, exist_ok=True)
    git_run(path, "init", "-q", "-b", branch)
    for key, value in (("user.name", "tester"), ("user.email", "tester@localhost"),
                       ("core.autocrlf", "true")):
        git_run(path, "config", key, value)
    return path


def commit_file(repo, relative, data, message="change"):
    """写入字节并提交该文件，返回新提交 sha。"""
    target = Path(repo) / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
    git_run(repo, "add", "--", relative)
    git_run(repo, "commit", "-q", "-m", message)
    return git_run(repo, "rev-parse", "HEAD").strip()


def fake_repo_entry(visibility="PRIVATE", protection_status=403):
    return {"visibility": visibility, "protection_status": protection_status, "milestones": [],
            "issues": [], "prs": [], "labels": [], "secrets": [], "deploy_keys": []}


@dataclass
class FakeGh:
    state_path: Path
    log_path: Path

    def state(self) -> dict:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def write(self, state: dict) -> None:
        self.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def update(self, **changes) -> None:
        self.write({**self.state(), **changes})

    def calls(self) -> list[list[str]]:
        text = self.log_path.read_text(encoding="utf-8") if self.log_path.is_file() else ""
        return [json.loads(line) for line in text.splitlines() if line]


@pytest.fixture
def fake_gh(tmp_path, monkeypatch):
    """假 gh 置于 PATH 最前；场景状态与调用日志都在 tmp_path 下。"""
    state_path, log_path = tmp_path / "fake-gh-state.json", tmp_path / "fake-gh-log.jsonl"
    fake = FakeGh(state_path, log_path)
    fake.write({"login": "tester", "authenticated": True, "default_repo": "tester/jjd-wiki",
                "clock": 0, "remote_map": {},
                "repos": {"tester/jjd-wiki": fake_repo_entry(),
                          "tester/jjd-wiki-dev": fake_repo_entry()}})
    monkeypatch.setenv("PATH", str(FAKE_GH_DIR) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("FAKE_GH_STATE", str(state_path))
    monkeypatch.setenv("FAKE_GH_LOG", str(log_path))
    monkeypatch.setenv("FAKE_GH_PYTHON", sys.executable)
    return fake


@dataclass
class GitPair:
    work: Path
    remote: Path


@pytest.fixture
def git_pair(tmp_path):
    """工作仓库 + --bare 远端（origin），core.autocrlf=true，main 已推送。"""
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    work = git_init(tmp_path / "work")
    git_run(work, "remote", "add", "origin", str(remote))
    commit_file(work, "README.md", "# 测试仓库\n", "init")
    git_run(work, "push", "-q", "-u", "origin", "main")
    return GitPair(work, remote)


def write_config(path, wiki_root, **extra):
    """最小配置文件；extra 可带 push_guard、github 等新字段。"""
    path.write_text(json.dumps({
        "wiki_root": str(wiki_root), "gallery_root": str(path.parent / "gallery"),
        "taxonomy": str(path.parent / "taxonomy.yaml"), "python_exe": sys.executable,
        "rscript_exe": "D:/R-4.5.0/bin/Rscript.exe", "port": 8765, **extra,
    }, ensure_ascii=False), encoding="utf-8", newline="\n")
    return path


def install_test_hook(work, config_path):
    """与 bootstrap 的 install_hook 同形：sh 脚本调用本解释器与本 wiki.py 的 gh guard --pre-push。"""
    hook = Path(work) / ".git" / "hooks" / "pre-push"
    hook.write_text("#!/bin/sh\n"
                    f'exec "{Path(sys.executable).as_posix()}" -X utf8 "{(SKILL_ROOT / "wiki.py").as_posix()}" '
                    f'--config "{Path(config_path).as_posix()}" gh guard --pre-push "$1" "$2"\n',
                    encoding="utf-8", newline="\n")
    return hook


def run_wiki(cwd, *args, env=None):
    """在指定目录运行 wiki.py（gh guard 以 cwd 所在仓库为准）。"""
    return subprocess.run([sys.executable, "-X", "utf8", str(SKILL_ROOT / "wiki.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8", env=env)


@pytest.fixture
def wiki_repo(tmp_path):
    """最小 vault：根仓库在 main 上，知识库/ 是其中的子树；返回 (config, config_path, vault)。"""
    from rwiki.config import load_config

    vault = git_init(tmp_path / "vault")
    wiki = vault / "知识库"
    for directory in ("layouts", "templates", "methods", "interfaces", "chart-types", "projects"):
        (wiki / directory).mkdir(parents=True)
    (wiki / ".gitignore").write_text("**/__pycache__/\n", encoding="utf-8", newline="\n")
    (wiki / "log.md").write_text("# 操作日志\n", encoding="utf-8", newline="\n")
    (vault / "文档").mkdir()
    (vault / "文档/说明.md").write_text("# 说明\n", encoding="utf-8", newline="\n")
    git_run(vault, "add", "-A")
    git_run(vault, "commit", "-q", "-m", "init vault")
    (tmp_path / "gallery").mkdir()
    config_path = write_config(tmp_path / "config.json", wiki)
    return load_config(config_path), config_path, vault


@dataclass
class GhRepos:
    config: object
    config_path: Path
    vault: Path
    dev: Path
    worktrees: Path
    gh: FakeGh

    def reload(self):
        from rwiki.config import load_config
        self.config = load_config(self.config_path)
        return self.config


@pytest.fixture
def gh_repos(wiki_repo, fake_gh, tmp_path, monkeypatch):
    """vault（含 知识库/）与 dev 两个工作仓库，各带 --bare 远端且 main 已推送；假 gh 按 origin 地址映射仓库。"""
    from rwiki.config import load_config

    monkeypatch.delenv("RWIKI_WIKI_ROOT", raising=False)
    monkeypatch.delenv("RWIKI_AGENT", raising=False)
    config, config_path, vault = wiki_repo
    dev = git_init(tmp_path / "dev")
    commit_file(dev, "README.md", "# dev\n", "init")
    remote_map = {}
    for key, repo in (("vault", vault), ("dev", dev)):
        remote = tmp_path / f"{key}.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
        git_run(repo, "remote", "add", "origin", str(remote))
        git_run(repo, "push", "-q", "-u", "origin", "main")
        remote_map[str(remote)] = f"tester/{FAKE_REPO_NAMES[key]}"
    fake_gh.update(remote_map=remote_map)
    worktrees = tmp_path / "worktrees"
    write_config(config_path, config.wiki_root, github={
        "owner": "tester", "dev_root": str(dev), "vault_root": str(vault), "worktree_root": str(worktrees)})
    return GhRepos(load_config(config_path), config_path, vault, dev, worktrees, fake_gh)


def gh_writes(fake) -> list[list[str]]:
    """假 gh 日志中的写操作（只读调用：auth status、view、list、checks、GET api）。"""
    reads = {"status", "view", "list", "checks"}
    writes = []
    for call in fake.calls():
        if call[:1] == ["--version"] or (len(call) > 1 and call[1] in reads):
            continue
        if call[0] == "api" and ("-X" not in call or call[call.index("-X") + 1] == "GET") and "-f" not in call:
            continue
        if call[0] == "api" and "-X" in call and call[call.index("-X") + 1] == "GET":
            continue
        writes.append(call)
    return writes


def run_cli(config_path, *args):
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(SKILL_ROOT / "wiki.py"),
         "--config", str(config_path), *args],
        capture_output=True, text=True, encoding="utf-8",
    )


def commit_count(wiki_root):
    return int(subprocess.check_output(
        ["git", "-C", str(wiki_root), "rev-list", "--count", "HEAD"],
        text=True, encoding="utf-8",
    ))


def update_gallery(config, **changes):
    path = config.gallery_root / "2026-08-17-shap-feature-mechanism/figures/fig01-shap-a-f/meta.json"
    meta = json.loads(path.read_text(encoding="utf-8"))
    meta.update(changes)
    if changes.get('status') == 'approved':
        meta['approved_version'] = meta['version']
    path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8", newline="\n")


def complete_sections(path):
    """Finish a software fixture, without pretending it is scientific evidence."""
    from rwiki.pages import read_page, section_text, write_page
    from rwiki.acceptance import HEADINGS
    from rwiki.errors import WikiError
    meta, body = read_page(path)
    for heading in HEADINGS.get(meta['type'], ()):
        try:
            content = section_text(body, heading)
        except WikiError:
            content = ''
        if not content:
            note = '隔离软件夹具的说明；不代表科学有效或真实课题结果。'
            if heading == '知识关联检查':
                note = ('检查范围：本隔离夹具已有方法与图样；按各测试声明关系，无其他科学关联。'
                        '无图原因：夹具未提供对应模板时不配图。')
            marker = f'## {heading}\n'
            if marker in body:
                body = body.replace(marker, marker + '\n' + note + '\n', 1)
            else:
                body = body.replace('<!-- user:start -->', f'## {heading}\n\n{note}\n\n<!-- user:start -->', 1)
    write_page(path, meta, body)


def seal_replay(target):
    """Synthetic receipts isolate metadata tests; execution is tested separately."""
    from rwiki.verification import record_preview
    (target / 'verify').mkdir(exist_ok=True)
    raw = (target / 'preview.png').read_bytes()
    for ext in ('png', 'pdf', 'svg'):
        (target / f'verify/figure.{ext}').write_bytes(raw)
    record_preview(target)


def record_ready_receipt(config, page):
    """A fixture page written as ready gets the receipt mark-ready would have recorded."""
    from rwiki.acceptance import record_acceptance
    record_acceptance(config, page)


def record_implementation_receipt(page, implementation_id='run', **changes):
    """Seal the current fixture code; never evidence of a scientific analysis."""
    from rwiki.pages import read_page
    meta, _ = read_page(page)
    branch = next(item for item in meta['implementations'] if item['id'] == implementation_id)
    asset = page.with_suffix('')
    data = {
        'schema_version': 1, 'implementation': implementation_id, 'state': 'passed',
        'scope': 'Isolated software fixture only; no scientific result.',
        'command': 'python fixture.py', 'checks': ['Fixture entrypoint is present and sealed'],
        'environment': {'python': sys.executable},
        'files': {path.relative_to(asset).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in sorted((asset / 'code').rglob('*'))
                  if path.is_file() and '__pycache__' not in path.parts
                  and path.suffix.lower() not in ('.pyc', '.pyo')},
    }
    data.update(changes)
    target = asset / (branch.get('verification') or f'verification/{implementation_id}.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')


def write_interface(root, slug, columns, title="数值接口"):
    from rwiki.pages import write_page

    write_page(root / "interfaces" / f"{slug}.md", {
        "type": "interface", "slug": slug, "title": title, "columns": columns},
        f"# {title}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n## 含义\n\n"
        "一行代表一个测试单位；仅用于软件夹具，不代表科学能力。\n\n"
        "<!-- user:start -->\n<!-- user:end -->\n")


@pytest.fixture
def workspace(tmp_path):
    from rwiki.config import load_config
    from rwiki.store import init

    gallery = tmp_path / "gallery"
    # Every test copies the gallery; skip the article page, comparison sheet and vector exports
    # (~17 MB of the 20 MB) that no test reads.
    shutil.copytree(DEV_ROOT / "test-gallery", gallery, ignore=shutil.ignore_patterns(
        "article_images", "*.html", "compare", "source_crop", "__pycache__", "*.svg", "*.pdf"))
    path = gallery / "2026-08-17-shap-feature-mechanism/figures/fig01-shap-a-f/meta.json"
    meta = json.loads(path.read_text(encoding="utf-8"))
    meta["figure"]["panel_map"] = {"A": "bar", "B": "beeswarm", "C": "radial_bar",
                                   "D": "bar", "E": "beeswarm", "F": "radial_bar"}
    path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8", newline="\n")
    taxonomy = tmp_path / "taxonomy.yaml"
    shutil.copyfile(DEV_ROOT / "spec/scenario_taxonomy.yaml", taxonomy)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "wiki_root": str(tmp_path / "wiki"),
        "gallery_root": str(gallery),
        "taxonomy": str(taxonomy),
        "python_exe": sys.executable,
        "rscript_exe": "D:/R-4.5.0/bin/Rscript.exe",
        "port": 8765,
    }), encoding="utf-8", newline="\n")
    config = load_config(config_path)
    init(config)
    return config, config_path


@pytest.fixture
def ingested(workspace):
    from rwiki.ingest import ingest_figure

    config, config_path = workspace
    ingest_figure(config, ENTRY_ID)
    return config, config_path


@pytest.fixture
def layout_workspace(workspace):
    from PIL import Image
    from rwiki.ingest import ingest_figure
    from rwiki.pages import read_page, write_page

    config, config_path = workspace
    update_gallery(config, status="approved")
    ingest_figure(config, ENTRY_ID)
    root = config.wiki_root
    page = root / f"layouts/{ENTRY_ID}.md"
    meta, body = read_page(page)
    meta["panels"] = {"A": "bar", "B": "dot"}
    meta["chart_types"] = ["bar", "dot"]
    meta["templates"] = [f"{ENTRY_ID}--bar", f"{ENTRY_ID}--dot"]
    meta["template_panels"] = {meta["templates"][0]: ["A"], meta["templates"][1]: ["B"]}
    write_page(page, meta, body)
    write_interface(root, "values", {"value": {"type": "int", "description": "计数"}})
    for chart, color in (("bar", "red"), ("dot", "blue")):
        tid = f"{ENTRY_ID}--{chart}"
        target = root / "templates" / tid
        (target / "code").mkdir(parents=True)
        (target / "example").mkdir()
        (target / "code/__init__.py").write_text("", encoding="utf-8")
        # Same module name, distinct content: a global 'helper' import would collide.
        (target / "code/helper.py").write_text(f"COLOR = '{color}'\n", encoding="utf-8")
        (target / "code/panel.py").write_text('''from .helper import COLOR
def draw(fig, rect, tables, style):
    assert list(tables['values']['value']) == [2]
    ax = fig.add_axes(rect)
    ax.set_facecolor(style['color'] or COLOR)
    ax.set_xticks([])
    ax.set_yticks([])
''', encoding="utf-8")
        (target / "code/render.py").write_text('''import argparse
import importlib.util
import json
import sys
from pathlib import Path
from uuid import uuid4
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
p = argparse.ArgumentParser()
for flag in ('data', 'out'):
    p.add_argument('--' + flag, type=Path, required=True)
p.add_argument('--style', type=Path)
a = p.parse_args()
spec = json.loads(Path('spec.json').read_text(encoding='utf-8'))
style = spec['style']
if a.style:
    style.update(json.loads(a.style.read_text(encoding='utf-8')))
name = 'standalone_' + uuid4().hex
package_spec = importlib.util.spec_from_file_location(name, 'code/__init__.py', submodule_search_locations=[str(Path('code').resolve())])
package = importlib.util.module_from_spec(package_spec)
sys.modules[name] = package
package_spec.loader.exec_module(package)
panel_spec = importlib.util.spec_from_file_location(name + '.panel', spec['panel'])
panel = importlib.util.module_from_spec(panel_spec)
panel_spec.loader.exec_module(panel)
tables = {key: pd.read_csv(a.data / f"{value['interface']}.csv") for key, value in spec['tables'].items()}
fig = plt.figure(figsize=(style['width_in'], style['height_in']), dpi=style['dpi'])
panel.draw(fig, [0.1, 0.1, 0.8, 0.8], tables, style)
a.out.mkdir(parents=True, exist_ok=True)
for ext in ('png', 'pdf', 'svg'):
    fig.savefig(a.out / ('figure.' + ext))
plt.close(fig)
''', encoding="utf-8", newline="\n")
        spec = {"entry": "code/render.py", "panel": "code/panel.py", "language": "python",
                "tables": {"values": {"interface": "values", "description": "计数"}},
                "style": {"color": None, "width_in": 2, "height_in": 2, "dpi": 50}}
        (target / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
        (target / "example/values.csv").write_text("value\n2\n", encoding="utf-8")
        write_page(root / f"templates/{tid}.md", {
            "type": "template", "id": tid, "title": chart, "status": "ready", "layouts": [ENTRY_ID],
            "panels": ["A" if chart == "bar" else "B"], "language": "python", "tags": meta["tags"],
            "chart_types": [chart], "favorite": False},
            f"# {chart}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n## 适用\n\n说明\n\n"
            "## 不适用\n\n## 数据要求\n\n## 使用记录\n\n<!-- user:start -->\n<!-- user:end -->\n")
        Image.new("RGB", (8, 8), color).save(target / "preview.png")
        complete_sections(target.with_suffix('.md'))
        seal_replay(target)
        record_ready_receipt(config, target.with_suffix('.md'))
    target = root / "layouts" / ENTRY_ID
    (target / "example").mkdir()
    (target / "example/values.csv").write_text("value\n2\n", encoding="utf-8")
    layout = {"canvas": {"width_in": 4, "height_in": 2, "dpi": 50}, "panels": [
        {"letter": "A", "template": meta["templates"][0], "rect": [0.05, 0.1, 0.4, 0.8],
         "tables": {"values": "values.csv"}, "style": {}},
        {"letter": "B", "template": meta["templates"][1], "rect": [0.55, 0.1, 0.4, 0.8],
         "tables": {"values": "values.csv"}, "style": {}}],
        "labels": [{"text": "A", "x": 0.01, "y": 0.96, "size": 8,
                    "weight": "bold", "family": "Arial"}]}
    (target / "layout.json").write_text(json.dumps(layout), encoding="utf-8")
    complete_sections(page)
    return config, config_path, target, layout


