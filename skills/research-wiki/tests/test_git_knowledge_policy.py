from rwiki.push_guard import Rules, GPL_MARKERS, classify, sync_ignore
from conftest import commit_file, write_config
from rwiki.config import load_config
from rwiki.push_guard import load_rules, scan


def rules():
    return Rules(100000, ("**/SCP-local/**",), GPL_MARKERS,
                 ("知识库/methods/gpl/code/",), ())


def test_licensed_knowledge_and_gallery_are_allowed():
    for path in ("知识库/methods/gpl/code/run.R", "vendor/SCP-local/run.R", "画廊/public/figure.png"):
        assert classify(path, 10, [], GPL_MARKERS[0].encode(), rules()) == []


def test_old_license_ignore_removed_preserving_other_bytes(tmp_path):
    path = tmp_path / ".gitignore"
    before, after = b"# keep\r\n", b"private-data/\r\n"
    path.write_bytes(before + b"# >>> push-guard gpl\n/methods/gpl/code/\n# <<< push-guard gpl\n" + after)
    assert sync_ignore(tmp_path)
    assert path.read_bytes() == before + after
    assert not sync_ignore(tmp_path)


def test_credentials_and_private_data_cannot_be_exempted():
    cases = [("private-data/patients.csv", "x"), ("a/.env", "x"),
             ("a/id_ed25519", "x"), ("a/private-key.pfx", "x"),
             ("notes.txt", "-----BEGIN " + "OPENSSH PRIVATE KEY-----"),
             ("settings.json", '"password": "' + 'real-secret-123"'),
             ("notes.md", "ghp_" + "a" * 36)]
    for path, content in cases:
        permissive = Rules(100000, (), (), (), (("size", "**"), ("abs-path", "**")))
        hits = classify(path, len(content), content.splitlines(), content.encode(), permissive)
        assert any(rule in {"secret", "private-data"} for rule, _ in hits), path
        assert all("real-secret" not in detail and "a" * 36 not in detail for _, detail in hits)


def test_empty_and_placeholder_credentials_are_allowed():
    for value in ("", "<password>", "${PASSWORD}", "REDACTED", "your_password"):
        content = '"password": "' + value + '"'
        assert classify("config.example.json", len(content), [content], content.encode(), rules()) == []


def test_secret_added_then_deleted_is_still_blocked(git_pair, tmp_path):
    work = git_pair.work
    commit_file(work, "notes.txt", "-----BEGIN " + "RSA PRIVATE KEY-----\nabc\n")
    commit_file(work, "notes.txt", "clean\n")
    cfg = load_config(write_config(tmp_path / "c.json", tmp_path / "no-wiki"))
    findings = scan(work, "origin/main..HEAD", load_rules(cfg, work))
    assert any(item["rule"] == "secret" for item in findings)


def test_ui_password_input_type_is_not_a_credential():
    content = 'input = isSecret ? "pass' + 'word" : "text"'
    assert classify("ui.js", len(content), [content], content.encode(), rules()) == []


def test_save_blocks_secrets_before_local_commit(wiki_repo):
    import pytest
    from conftest import git_run
    from rwiki.errors import WikiError
    from rwiki.store import save
    cfg, _, vault = wiki_repo
    before = git_run(vault, "rev-parse", "HEAD")
    (cfg.wiki_root / "notes.txt").write_text("-----BEGIN " + "RSA PRIVATE KEY-----\n", encoding="utf-8")
    with pytest.raises(WikiError, match="save 拒绝"):
        save(cfg, "must not commit")
    assert git_run(vault, "rev-parse", "HEAD") == before
