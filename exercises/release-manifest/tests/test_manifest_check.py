#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run(
    *args: str,
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        list(args),
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and process.returncode != 0:
        raise AssertionError(
            f"command failed: {' '.join(args)}\n"
            f"stdout:\n{process.stdout}\nstderr:\n{process.stderr}"
        )
    return process


def create_repository(
    root: Path,
    name: str,
    *,
    annotated: bool = True,
) -> tuple[Path, str]:
    repo = root / name
    repo.mkdir()
    run("git", "init", "-q", "-b", "main", cwd=repo)
    run("git", "config", "user.name", "Manifest Test", cwd=repo)
    run("git", "config", "user.email", "manifest@example.invalid", cwd=repo)
    (repo / "content.txt").write_text(f"{name}\n", encoding="utf-8")
    run("git", "add", "content.txt", cwd=repo)
    run("git", "commit", "-q", "-m", "initial", cwd=repo)
    commit = run("git", "rev-parse", "HEAD", cwd=repo).stdout.strip()
    run(
        "git",
        "remote",
        "add",
        "origin",
        f"https://example.invalid/{name}.git",
        cwd=repo,
    )
    if annotated:
        run("git", "tag", "-a", "v1.0.0", "-m", "release v1.0.0", cwd=repo)
    else:
        run("git", "tag", "v1.0.0", cwd=repo)
    run("git", "checkout", "-q", "--detach", commit, cwd=repo)
    return repo, commit


def entry(name: str, repo: Path, commit: str) -> dict[str, str]:
    return {
        "name": name,
        "path": str(repo.resolve()),
        "remote": f"https://example.invalid/{name}.git",
        "tag": "v1.0.0",
        "commit": commit,
    }


def main(argv):
    import importlib.util
    spec = importlib.util.spec_from_file_location("subject", Path(argv[1]).resolve())
    subject = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(subject)
    with tempfile.TemporaryDirectory(prefix="repository-check-") as directory:
        root = Path(directory)
        repo, commit = create_repository(root, "app")
        valid = entry("app", repo, commit)
        subject.verify_repository(valid)
        for field, value in (("remote", "https://example.invalid/wrong.git"), ("commit", "0" * 40)):
            invalid = dict(valid, **{field: value})
            try: subject.verify_repository(invalid)
            except subject.ManifestError: pass
            else: raise AssertionError(field)
        (repo / "dirty.txt").write_text("untracked")
        try: subject.verify_repository(valid)
        except subject.ManifestError: pass
        else: raise AssertionError("dirty repository accepted")
    print("repository validation passed")
    return 0

if __name__ == "__main__": raise SystemExit(main(sys.argv))
