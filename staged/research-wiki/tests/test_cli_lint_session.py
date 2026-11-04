import pytest

from rwiki import cli, relations
from rwiki.lint import lint
from rwiki.pages import write_page


@pytest.mark.parametrize("ci", [False, True])
def test_cli_lint_reuses_relations_only_within_one_invocation(wiki_repo, monkeypatch, capsys, ci):
    config, config_path, _ = wiki_repo
    for name in ("first", "second"):
        write_page(config.wiki_root / "methods" / f"{name}.md", {
            "type": "method", "id": name, "title": name, "status": "draft",
            "tags": [], "inputs": [], "outputs": [], "source": {"kind": "written"},
            "license": "none", "cite": ["Official documentation"], "favorite": False,
        }, "# Method\n<!-- user:start --><!-- user:end -->\n"
           "<!-- facts:start --><!-- facts:end -->\n")

    diagnostics = lint(config, ci=ci)
    assert not any(line.startswith("ERROR ") for line in diagnostics)
    expected_output = "\n".join([*diagnostics, "OK", ""])
    original = relations._collect_relations
    collected = []

    def counted(*args, **kwargs):
        collected.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(relations, "_collect_relations", counted)
    args = ["--config", str(config_path), "lint", *(["--ci"] if ci else [])]
    for invocation in (1, 2):
        assert cli.main(args) == 0
        captured = capsys.readouterr()
        assert captured.out == expected_output
        assert captured.err == ""
        assert len(collected) == invocation
