from rwiki.links import extract_links, resolve


def test_links_labels_headings_and_embeds():
    assert extract_links("[[one]] [[two|显示]] [[three#节]] ![[img.png]] [[four#节|名]]") == [
        "one", "two", "three", "img.png", "four",
    ]


def test_ignores_fenced_and_inline_code():
    body = """[[yes]] `[[inline]]` ``[[double]] `text` ``
```python
[[fenced]]
```
    ```
[[indented]]
    ```
[[after]]
"""
    assert extract_links(body) == ["yes", "after"]


def test_resolve_is_root_relative_and_adds_markdown_suffix(tmp_path):
    assert resolve(tmp_path, "chart-types/shap") == tmp_path / "chart-types/shap.md"
    assert resolve(tmp_path, "page") == tmp_path / "page.md"
    assert resolve(tmp_path, "templates/id/thumb.png") == tmp_path / "templates/id/thumb.png"


def test_resolve_preserves_extracted_target_characters(tmp_path):
    assert resolve(tmp_path, "page#part|name") == tmp_path / "page#part|name.md"
