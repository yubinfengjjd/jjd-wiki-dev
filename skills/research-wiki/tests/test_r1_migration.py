"""Regression tests for the external, one-time R1 wiki migration."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from rwiki.pages import get_block, read_page, write_page

# 迁移脚本在 codex/（不入库），只在本机检出可运行。
pytestmark = pytest.mark.local


SCRIPT = Path(__file__).resolve().parents[3] / "codex" / "R1-migrate.py"


def load_migration():
    assert SCRIPT.is_file(), "R1 one-time migration script has not been implemented"
    spec = importlib.util.spec_from_file_location("r1_migrate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def legacy_method(root, *, status="pending_confirm", archived_from=None):
    path = root / "methods" / "example.md"
    meta = {"type": "method", "id": "example", "title": "原始模型的科学标题",
            "status": status, "language": "python",
            "scenarios": {"primary": ["known"], "free": ["SHAP"]},
            "source": {"kind": "project", "path": "original-project"},
            "license": "none", "cite": [], "favorite": False}
    if archived_from:
        meta["archived_from"] = archived_from
    body = ("# 原始模型的科学标题\n\n<!-- facts:start -->\nOLD FACTS\n<!-- facts:end -->\n\n"
            "## 用途\n\n科学描述与参数 `n_jobs` 保持原样。\n\n"
            "## 适用\n\n有限数值数据。\n\n## 不适用\n\n不能推断因果。\n\n"
            "## 使用记录\n\n原使用记录。\n\n"
            "<!-- user:start -->\n作者自写。\n## 输入\n这是作者内容，不能充当 agent 节。\n<!-- user:end -->\n")
    write_page(path, meta, body)
    assets = path.with_suffix("")
    (assets / "source").mkdir(parents=True)
    (assets / "source" / "original.py").write_bytes(b"# original\r\nprint('source')\r\n")
    (assets / "code").mkdir()
    (assets / "code" / "run.py").write_bytes(b"# reusable\r\nprint('template')\r\n")
    (assets / "example" / "output").mkdir(parents=True)
    (assets / "example" / "output" / "report.json").write_text("{}", encoding="utf-8")
    (assets / "params.yaml").write_text("old: 1", encoding="utf-8")
    (assets / "method.json").write_text(json.dumps({
        "inputs": {"raw": {"file": "raw.csv"}, "a": {"interface": "values"},
                   "b": {"interface": "values"}, "c": {"interface": "samples"}},
        "outputs": ["values", "samples"], "language": "python"}), encoding="utf-8")
    return path, meta, body


def test_migration_translates_all_legacy_scenarios_and_preserves_existing_tags(tmp_path):
    migration = load_migration()
    for kind in ("templates", "layouts", "methods"):
        write_page(tmp_path / kind / "note.md", {
            "type": kind[:-1], "id": "note", "title": "保持标题", "status": "draft",
            "tags": ["原标签", "已知中文"],
            "scenarios": {"primary": ["known", "unknown"], "secondary": ["second", "known"],
                          "free": ["自由", "原标签"]}},
            "# 保持正文\n\n<!-- user:start -->\n<!-- user:end -->\n")
    for key, title in (("known", "已知中文"), ("second", "次标签")):
        write_page(tmp_path / "scenarios" / f"{key}.md",
                   {"type": "scenario", "key": key, "title": title}, f"# {title}\n")
    migration.migrate_pages(tmp_path)
    for kind in ("templates", "layouts", "methods"):
        meta, _ = read_page(tmp_path / kind / "note.md")
        assert meta["tags"] == ["原标签", "已知中文", "unknown", "次标签", "自由"]
        assert "scenarios" not in meta
    assert not (tmp_path / "scenarios").exists()


@pytest.mark.parametrize("status, previous, expected", [
    ("pending_confirm", None, "draft"), ("ready", None, "ready"),
    ("archived", "pending_confirm", "archived")])
def test_migration_moves_method_interfaces_preserves_text_and_source_bytes(
        tmp_path, status, previous, expected):
    migration = load_migration()
    path, _, body_before = legacy_method(tmp_path, status=status, archived_from=previous)
    protected = {p: p.read_bytes() for name in ("source", "code")
                 for p in (path.with_suffix("") / name).rglob("*") if p.is_file()}
    migration.migrate_pages(tmp_path)
    meta, body = read_page(path)
    assert meta["inputs"] == ["values", "samples"]
    assert meta["outputs"] == ["values", "samples"]
    assert meta["status"] == expected
    if previous:
        assert meta["archived_from"] == "draft"
    assert "language" not in meta
    assert meta["title"] == "原始模型的科学标题"
    assert get_block(body, "user") == get_block(body_before, "user")
    for text in ("科学描述与参数 `n_jobs` 保持原样。", "有限数值数据。", "不能推断因果。", "原使用记录。"):
        assert text in body
    outside_user = body.replace(get_block(body, "user"), "")
    for title in ("用途", "适用", "不适用", "输入", "怎么做", "代码", "输出", "使用记录"):
        assert f"## {title}\n" in outside_user
    assert {p: p.read_bytes() for p in protected} == protected
    assert not (path.with_suffix("") / "method.json").exists()
    assert not (path.with_suffix("") / "params.yaml").exists()
    assert not (path.with_suffix("") / "example").exists()
    once = path.read_bytes()
    migration.migrate_pages(tmp_path)
    assert path.read_bytes() == once


def test_cli_uses_argument_root_rebuilds_facts_commits_and_is_idempotent(tmp_path):
    load_migration()
    # The config points at another root; only the explicit target may change.
    root = tmp_path / "chosen-wiki"
    path, _, _ = legacy_method(root)
    declaration = path.with_suffix("") / "method.json"
    declaration.write_text('{"inputs": {}, "outputs": []}', encoding="utf-8")
    (root / "log.md").write_text("# 操作日志\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "init"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=test", "-c", "user.email=test@local",
                    "commit", "-m", "legacy"], check=True, capture_output=True)
    write_page(root / "scenarios" / "known.md",
               {"type": "scenario", "key": "known", "title": "中文标签"}, "# 中文标签\n")
    taxonomy = tmp_path / "taxonomy-does-not-exist.json"
    other = tmp_path / "untouched-wiki"
    other.mkdir()
    (other / "sentinel").write_bytes(b"unchanged")
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"wiki_root": str(other), "gallery_root": str(tmp_path / "gallery"),
                                 "taxonomy": str(taxonomy), "python_exe": sys.executable,
                                 "rscript_exe": "unused", "port": 8765}), encoding="utf-8")
    command = [sys.executable, "-X", "utf8", "-B", str(SCRIPT), str(root), "--config", str(config)]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stdout + result.stderr
    assert read_page(path)[0]["tags"] == ["中文标签", "SHAP"]
    assert "OLD FACTS" not in path.read_text(encoding="utf-8")
    assert "code/run.py" in path.read_text(encoding="utf-8")
    assert (other / "sentinel").read_bytes() == b"unchanged"
    assert list(other.iterdir()) == [other / "sentinel"]
    head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"])
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stdout + result.stderr
    assert subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"]) == head
    assert subprocess.check_output(["git", "-C", str(root), "status", "--porcelain"]) == b""
