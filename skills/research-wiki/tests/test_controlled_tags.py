"""Domain tags use the same severity model as purposes: illegal values are errors."""
import json
import shutil

from fastapi.testclient import TestClient

from conftest import DEV_ROOT, TAXONOMY_SOURCE, commit_count
from rwiki.config import load_config
from rwiki.lint import lint
from rwiki.pages import read_page, write_page
from rwiki.server import create_app
from rwiki.tags import load_vocabulary, tag_errors


BODY = ("# 标题\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n"
        "<!-- user:start -->\n<!-- user:end -->\n")


def _config(tmp_path, taxonomy: str):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "wiki_root": str(tmp_path / "wiki"),
        "gallery_root": str(tmp_path / "gallery"),
        "taxonomy": taxonomy,
        "python_exe": "python",
        "rscript_exe": "Rscript",
        "port": 8765,
    }), encoding="utf-8")
    return load_config(config_path)


def _method(root, mid, tags):
    write_page(root / "methods" / f"{mid}.md", {
        "type": "method", "id": mid, "title": mid, "status": "draft",
        "tags": tags, "inputs": [], "outputs": [],
        "source": {"kind": "written"}, "license": "none", "cite": ["fixture"],
        "favorite": False,
    }, BODY)


def test_vocabulary_is_keys_and_labels_not_aliases(tmp_path):
    taxonomy = tmp_path / "taxonomy.yaml"
    shutil.copyfile(TAXONOMY_SOURCE, taxonomy)
    words = load_vocabulary(_config(tmp_path, str(taxonomy)))
    assert "single-cell" in words and "单细胞分析" in words
    assert "SHAP" not in words and "单细胞" not in words
    assert tag_errors({"type": "recipe", "tags": []}, words) == []
    assert tag_errors({"type": "recipe"}, words) == []
    assert tag_errors({"type": "recipe", "tags": ["single-cell", "单细胞分析"]}, words) == []
    errors = tag_errors({"type": "recipe", "tags": ["SHAP", "组织"]}, words)
    assert errors and "非法领域" in errors[0] and "SHAP" in errors[0] and "组织" in errors[0]
    assert "keywords" in errors[0]
    assert tag_errors({"type": "recipe", "tags": ["单细胞分析", "单细胞分析"]}, words) == ["tags 不得重复"]
    assert tag_errors({"type": "recipe", "tags": "单细胞分析"}, words) == ["tags 必须为字符串列表"]
    padded = tag_errors({"type": "recipe", "tags": [" 单细胞分析 "]}, words)
    assert padded and "非法领域" in padded[0] and "单细胞分析" in padded[0]


def test_missing_taxonomy_file_uses_the_repo_spec(tmp_path):
    words = load_vocabulary(_config(tmp_path, str(tmp_path / "missing.yaml")))
    assert "transcriptomics" in words and "转录组" in words
    assert "SHAP" not in words


def test_lint_rejects_illegal_and_duplicate_tags(wiki_repo):
    config, _, _ = wiki_repo
    shutil.copyfile(TAXONOMY_SOURCE, config.taxonomy)
    root = config.wiki_root
    _method(root, "ok", ["single-cell", "转录组"])
    _method(root, "empty", [])
    write_page(root / "scenarios/clinical.md", {
        "type": "scenario", "id": "clinical", "title": "临床", "picks": [],
        "tags": ["survival-analysis"],
    }, BODY)
    report = "\n".join(lint(config))
    assert "methods/ok.md" not in report or "非法" not in report
    assert "ERROR methods/empty.md" not in report
    assert "scenarios/clinical.md" not in report or "非法" not in report
    _method(root, "bad", ["SHAP"])
    _method(root, "dup", ["单细胞分析", "单细胞分析"])
    report = lint(config)
    assert any(line.startswith("ERROR methods/bad.md:") and "非法领域" in line and "SHAP" in line
               for line in report)
    assert any(line.startswith("ERROR methods/dup.md:") and "不得重复" in line for line in report)
    assert not any(line.startswith("ERROR methods/ok.md:") for line in report)


def test_tags_api_rejects_unknown_and_keeps_vocabulary(wiki_repo):
    config, _, _ = wiki_repo
    shutil.copyfile(TAXONOMY_SOURCE, config.taxonomy)
    page = config.wiki_root / "methods/note.md"
    _method(config.wiki_root, "note", ["单细胞分析"])
    before = commit_count(config.wiki_root)
    with TestClient(create_app(config)) as client:
        rejected = client.post("/api/methods/note/tags", json={"tags": ["转录组", "Seurat"]})
        assert rejected.status_code == 422, rejected.text
        assert "Seurat" in rejected.json()["detail"] and "非法领域" in rejected.json()["detail"]
        assert read_page(page)[0]["tags"] == ["单细胞分析"]
        assert commit_count(config.wiki_root) == before
        accepted = client.post("/api/methods/note/tags",
                               json={"tags": [" 转录组 ", "转录组", "single-cell", ""]})
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["meta"]["tags"] == ["转录组", "single-cell"]
    assert read_page(page)[0]["tags"] == ["转录组", "single-cell"]
    assert commit_count(config.wiki_root) == before + 1
