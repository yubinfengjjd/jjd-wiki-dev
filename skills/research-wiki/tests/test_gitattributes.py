import random
import subprocess

from conftest import DEV_ROOT, git_init, git_run

SEED = 20261104
ITERATIONS = 120
PIECES = (b"\xef\xbb\xbf", b"line", b"\xe4\xbd\x9c\xe8\x80\x85", b"\r\n", b"\n", b"\r", b" ", b"\t",
          b"<!-- user:start -->", b"<!-- user:end -->")
SUFFIXES = (".md", ".py", ".json", ".R", ".png", ".rds", ".txt")


def test_bytes_survive_commit_clone_and_checkout(tmp_path):
    """Feature: github-structured-workflow, Property 4: 字节保真"""
    rng = random.Random(SEED)
    work = git_init(tmp_path / "work")
    (work / ".gitattributes").write_bytes((DEV_ROOT / ".gitattributes").read_bytes())
    expected = {}
    for iteration in range(ITERATIONS):
        data = b"".join(rng.choice(PIECES) for _ in range(rng.randint(0, 16)))
        name = f"f{iteration:03d}{rng.choice(SUFFIXES)}"
        (work / name).write_bytes(data)
        expected[name] = data
    git_run(work, "add", "-A")
    git_run(work, "commit", "-q", "-m", "bytes")
    clone = tmp_path / "clone"
    subprocess.run(["git", "-c", "core.autocrlf=true", "clone", "-q", str(work), str(clone)],
                   check=True, capture_output=True)
    git_run(clone, "config", "core.autocrlf", "true")
    for checkout in (work, clone):
        for name in expected:
            (checkout / name).unlink()
        git_run(checkout, "checkout", "--", ".")
        for name, data in expected.items():
            assert (checkout / name).read_bytes() == data, f"seed={SEED} file={name} repo={checkout.name}"
        assert git_run(checkout, "status", "--porcelain") == "", f"seed={SEED}"
