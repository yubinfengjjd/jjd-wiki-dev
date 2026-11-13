"""Real Git regressions for bounded-memory, full-history push scanning."""
import subprocess
import tempfile
import tracemalloc

import pytest

from conftest import commit_file, git_init, git_run
from rwiki import push_guard as guard
from rwiki.errors import WikiError


RULES = guard.Rules(2 ** 30, (), (), (), ())


@pytest.mark.parametrize("change", ["add", "edit"])
def test_scan_memory_is_bounded_by_one_file_not_total_history(tmp_path, change):
    repo = git_init(tmp_path / "repo")
    commit_file(repo, "README.md", "initial\n")
    base = git_run(repo, "rev-parse", "HEAD").strip()
    # Distinct code blobs exercise both the patch reader and cat-file bodies.
    payload = ("# safe padding " + "x" * 1000 + "\n") * 192
    for number in range(48):
        (repo / f"module{number:03}.py").write_text(payload + f"# {number}\n", encoding="utf-8")
    git_run(repo, "add", ".")
    git_run(repo, "commit", "-qm", "many medium code files")
    if change == "edit":
        base = git_run(repo, "rev-parse", "HEAD").strip()
        for number in range(48):
            with (repo / f"module{number:03}.py").open("a", encoding="utf-8") as stream:
                stream.write("# added tail\n")
        git_run(repo, "add", ".")
        git_run(repo, "commit", "-qm", "small patches on large blobs")
    tracemalloc.start()
    try:
        assert guard.scan(repo, f"{base}..HEAD", RULES) == []
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    budget = 16 * len(payload.encode()) + 2 ** 21
    assert peak < budget, f"{change}: peak={peak:,}, one-file budget={budget:,}"


def legacy_findings(repo, rev_range, rules):
    """Small-fixture oracle: original parser plus direct Git blob reads."""
    text = git_run(repo, "-c", "core.quotePath=false", "log", "--format=%x01%H", "--root",
                   "--raw", "-p", "-U0", "--no-color", "--no-renames", "--no-abbrev",
                   "--no-ext-diff", "--no-textconv", *rev_range.split(), "--")
    commits = guard._parse_log(text)
    code_blobs = {info["blob"] for commit in commits for path, info in commit["files"].items()
                  if guard.PurePosixPath(path).suffix.lower() in guard.CODE_SUFFIXES
                  or guard.PurePosixPath(path).name.upper().startswith("LICENSE")}
    result = []
    for commit in commits:
        for path, info in commit["files"].items():
            blob = subprocess.run(["git", "-C", str(repo), "cat-file", "blob", info["blob"]],
                                  check=True, capture_output=True).stdout
            for rule, detail in guard.classify(path, len(blob), info["added"],
                                               blob[:guard.HEAD_BYTES] if info["blob"] in code_blobs
                                               else b"", rules):
                finding = {"rule": rule, "path": path, "commit": commit["commit"], "detail": detail}
                if finding not in result:
                    result.append(finding)
    return result


def test_streaming_preserves_history_added_lines_and_finding_order(tmp_path):
    repo = git_init(tmp_path / "repo")
    commit_file(repo, "README.md", "initial\n")
    base = git_run(repo, "rev-parse", "HEAD").strip()
    secret = 'api_key =\n "actual-fixture-value"\n'
    mode_secret = ("pass" + 'word = "fixture-mode-value"\n').encode()
    paths = {
        "a-binary.py": b"\0" + secret.encode(),
        "b-mode.py": mode_secret,
        "b-mode.txt": mode_secret,
        "private-data/资料 空格.md": b"private\r\n",
        "docs/变化 空格.txt": ("safe\n" * 1000 + secret + "path Q:/fixture\n").encode(),
        "z-secret.py": ("# safe\n" * 1000 + secret).encode(),
        "z-no-final-newline.md": b"path /home/tester/final",
    }
    for name, data in paths.items():
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    git_run(repo, "add", ".")
    git_run(repo, "commit", "-qm", "mixed changes")
    first = git_run(repo, "rev-parse", "HEAD").strip()
    git_run(repo, "update-index", "--chmod=+x", "b-mode.py", "b-mode.txt")
    git_run(repo, "commit", "-qm", "mode only")
    mode = git_run(repo, "rev-parse", "HEAD").strip()
    commit_file(repo, "docs/变化 空格.txt", "clean replacement\n", "remove old violations")
    git_run(repo, "rm", "-q", "--", "z-secret.py", "private-data/资料 空格.md")
    git_run(repo, "commit", "-qm", "delete violations")
    # Existing abs paths in unchanged lines must not become newly added hits.
    commit_file(repo, "z-no-final-newline.md", "path /home/tester/final\nclean extra\n")
    found = guard.scan(repo, f"{base}..HEAD", RULES)
    assert found == legacy_findings(repo, f"{base}..HEAD", RULES)
    assert ("secret", "docs/变化 空格.txt", first) in {
        (hit["rule"], hit["path"], hit["commit"]) for hit in found}
    assert ("secret", "b-mode.py", mode) in {
        (hit["rule"], hit["path"], hit["commit"]) for hit in found}
    assert ("secret", "b-mode.txt", mode) in {
        (hit["rule"], hit["path"], hit["commit"]) for hit in found}
    assert not any(hit["path"] == "a-binary.py" for hit in found)


def test_invalid_range_fails_closed(tmp_path):
    repo = git_init(tmp_path / "repo")
    commit_file(repo, "README.md", "initial\n")
    with pytest.raises(WikiError):
        guard.scan(repo, "missing-revision..HEAD", RULES)


def test_bare_cr_hunk_text_is_not_raw_metadata(tmp_path):
    repo = git_init(tmp_path / "repo")
    git_run(repo, "config", "core.autocrlf", "false")
    commit_file(repo, "notes.md", b"safe\r:\ttext\n")
    expected = legacy_findings(repo, "HEAD", RULES)
    assert expected == []
    assert guard.scan(repo, "HEAD", RULES) == expected


@pytest.mark.parametrize("failure", [None, "log", "cat-file", "inspect"])
def test_scan_closes_tempfiles_and_reaps_processes(tmp_path, monkeypatch, failure):
    repo = git_init(tmp_path / "repo")
    commit_file(repo, "source.py", "# safe\n" * 10000)
    commit_file(repo, "notes.md", "safe\n")
    processes, streams = [], []
    original_popen, original_tempfile = subprocess.Popen, tempfile.TemporaryFile

    def popen(command, *args, **kwargs):
        if failure == "cat-file" and "cat-file" in command:
            command = [*command[:3], "cat-file", "--invalid-test-option"]
        process = original_popen(command, *args, **kwargs)
        processes.append(process)
        if failure == "cat-file" and "cat-file" in command:
            process.wait()  # Exercise a broken stdin pipe, not only an EOF header.
        return process

    def temporary_file(*args, **kwargs):
        stream = original_tempfile(*args, **kwargs)
        streams.append(stream)
        return stream

    def fail_inspect(*args, **kwargs):
        raise RuntimeError("injected classification failure")

    monkeypatch.setattr(subprocess, "Popen", popen)
    monkeypatch.setattr(tempfile, "TemporaryFile", temporary_file)
    if failure == "inspect":
        monkeypatch.setattr(guard, "classify", fail_inspect)
    if failure is None:
        assert guard.scan(repo, "HEAD", RULES) == []
    else:
        expected = RuntimeError if failure == "inspect" else WikiError
        with pytest.raises(expected):
            guard.scan(repo, "missing-revision" if failure == "log" else "HEAD", RULES)
    assert all(stream.closed for stream in streams)
    assert all(process.poll() is not None for process in processes)
    assert all(process.stdout is None or process.stdout.closed for process in processes)
    assert all(process.stdin is None or process.stdin.closed for process in processes)
