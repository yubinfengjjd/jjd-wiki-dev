import json

import pytest

from conftest import commit_count, write_interface
from rwiki.errors import WikiError
from rwiki.spec import check_data, load_spec, requirements_markdown


@pytest.fixture
def valid_spec(tmp_path):
    tmp_path = tmp_path / "templates" / "sample"
    (tmp_path / "code").mkdir(parents=True)
    (tmp_path / "code/render.py").write_text("", encoding="utf-8")
    (tmp_path / "code/__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "code/panel.py").write_text("", encoding="utf-8")
    write_interface(tmp_path.parent.parent, "sample-values", {"value": {"type": "float", "description": "数值"}}, "样本数值")
    spec = {"panel": "code/panel.py", "entry": "code/render.py", "language": "python", "tables": {
        "samples": {"description": "示例数据", "interface": "sample-values"}},
        "style": {"color": "red"}}
    return tmp_path, spec


def write_spec(directory, spec):
    (directory / "spec.json").write_text(json.dumps(spec), encoding="utf-8")


def test_valid_spec_and_requirements(valid_spec):
    directory, spec = valid_spec
    write_spec(directory, spec)
    loaded = load_spec(directory)
    assert loaded["tables"]["samples"]["columns"] == {"value": {"type": "float", "description": "数值"}}
    text = requirements_markdown(loaded)
    for expected in ("### samples", "sample-values.csv", "示例数据", "| value | float | 数值 |", "color", "red",
                     "[[interfaces/sample-values|样本数值]]"):
        assert expected in text
    assert json.loads((directory / "spec.json").read_text(encoding="utf-8"))["tables"]["samples"] == {
        "interface": "sample-values", "description": "示例数据"}
    assert "file" not in loaded["tables"]["samples"]


@pytest.mark.parametrize("field, value, message", [
    ("entry", "code/missing.py", "entry"),
    ("language", "r", "扩展名"),
    ("language", "ruby", "language"),
    ("tables", {}, "tables"),
    ("tables", {"t": []}, "tables.t"),
    ("tables", {"t": {"description": ""}}, "interface"),
    ("tables", {"t": {"interface": "", "description": ""}}, "interface"),
    ("tables", {"t": {"interface": "sample-values"}}, "description"),
    ("tables", {"t": {"interface": "sample-values", "description": 1}}, "description"),
    ("tables", {"t": {"interface": "missing", "description": ""}}, "不存在"),
    ("style", [], "style"),
])
def test_invalid_spec_identifies_item(valid_spec, field, value, message):
    directory, spec = valid_spec
    spec[field] = value
    write_spec(directory, spec)
    with pytest.raises(WikiError, match=message):
        load_spec(directory)


def test_check_data_missing_file_missing_column_and_extra_allowed(valid_spec):
    directory, spec = valid_spec
    write_spec(directory, spec)
    spec = load_spec(directory)
    with pytest.raises(WikiError, match="samples.*不存在"):
        check_data(spec, directory)
    path = directory / "sample-values.csv"
    path.write_text("wrong\n1\n", encoding="utf-8")
    with pytest.raises(WikiError, match="缺列: value"):
        check_data(spec, directory)
    path.write_text("\ufeffvalue,extra\nnot-a-float,anything\n", encoding="utf-8")
    check_data(spec, directory)  # Only the header is checked, never values.


@pytest.mark.parametrize("legacy", [{"file": "sample-values.csv"}, {"columns": {}}])
def test_load_spec_rejects_legacy_table_fields(valid_spec, legacy):
    directory, spec = valid_spec
    spec["tables"]["samples"].update(legacy)
    write_spec(directory, spec)
    with pytest.raises(WikiError, match=next(iter(legacy))):
        load_spec(directory)


def test_check_data_uses_interface_filename_instead_of_table_key(valid_spec):
    directory, spec = valid_spec
    write_spec(directory, spec)
    loaded = load_spec(directory)
    (directory / "samples.csv").write_text("value\n1\n", encoding="utf-8")
    with pytest.raises(WikiError, match=r"sample-values\.csv"):
        check_data(loaded, directory)
    (directory / "sample-values.csv").write_text("value\n1\n", encoding="utf-8")
    check_data(loaded, directory)
    (directory / "samples.csv").unlink()
    check_data(loaded, directory)


def test_add_interface_creates_page_and_saves(workspace, tmp_path):
    from rwiki.interfaces import add_interface, load_interface
    from rwiki.pages import get_block, read_page

    config, _ = workspace
    columns = {"feature": {"type": "str", "description": "特征"},
               "importance": {"type": "float", "description": "重要性"}}
    source = tmp_path / "columns.json"
    source.write_text(json.dumps(columns), encoding="utf-8")
    count = commit_count(config.wiki_root)
    add_interface(config, "feature-importance", "特征重要性", source)
    expected = {"type": "interface", "slug": "feature-importance", "title": "特征重要性", "columns": columns}
    assert load_interface(config.wiki_root, "feature-importance") == expected
    meta, body = read_page(config.wiki_root / "interfaces/feature-importance.md")
    assert meta == expected
    assert "## 含义" in body and get_block(body, "user").strip() == ""
    assert commit_count(config.wiki_root) == count + 1
    with pytest.raises(WikiError, match="已存在"):
        add_interface(config, "feature-importance", "特征重要性", source)


@pytest.mark.parametrize("columns,message", [
    ({}, "非空"), ([], "非空"),
    ({"": {"type": "str", "description": "值"}}, "列名"),
    ({"x": {"type": "number", "description": "值"}}, "type"),
    ({"x": {"type": "str"}}, "description"),
    ({"x": {"type": "str", "description": "  "}}, "description"),
])
def test_interface_columns_reject_invalid_definitions(columns, message):
    from rwiki.interfaces import validate_columns
    with pytest.raises(WikiError, match=message):
        validate_columns(columns)


@pytest.mark.parametrize("slug", ["", "Upper", "with_underscore", "../outside"])
def test_add_interface_rejects_invalid_slug_without_writing(workspace, tmp_path, slug):
    from rwiki.interfaces import add_interface
    config, _ = workspace
    source = tmp_path / "columns.json"
    source.write_text('{"x": {"type": "str", "description": "值"}}', encoding="utf-8")
    count = commit_count(config.wiki_root)
    with pytest.raises(WikiError, match="slug"):
        add_interface(config, slug, "标题", source)
    assert commit_count(config.wiki_root) == count


def test_load_interface_missing_page_is_wiki_error(tmp_path):
    from rwiki.interfaces import load_interface
    with pytest.raises(WikiError, match="不存在"):
        load_interface(tmp_path, "missing")


@pytest.mark.parametrize("field,value,message", [
    ("type", "template", "type"), ("slug", "different", "slug"),
    ("title", " ", "title"), ("columns", {}, "columns"),
])
def test_load_interface_validates_frontmatter(tmp_path, field, value, message):
    from rwiki.interfaces import load_interface
    from rwiki.pages import read_page, write_page

    write_interface(tmp_path, "values", {"value": {"type": "float", "description": "数值"}})
    path = tmp_path / "interfaces/values.md"
    meta, body = read_page(path)
    meta[field] = value
    write_page(path, meta, body)
    with pytest.raises(WikiError, match=message):
        load_interface(tmp_path, "values")


def test_add_interface_invalid_columns_does_not_create_page(workspace, tmp_path):
    from rwiki.interfaces import add_interface

    config, _ = workspace
    source = tmp_path / "columns.json"
    source.write_text('{"value": {"type": "float", "description": ""}}', encoding="utf-8")
    with pytest.raises(WikiError, match="description"):
        add_interface(config, "values", "数值", source)
    assert not (config.wiki_root / "interfaces/values.md").exists()
