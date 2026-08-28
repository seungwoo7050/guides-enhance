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


def write_manifest(path: Path, entries: list[dict[str, str]]) -> None:
    path.write_text(
        json.dumps({"repositories": entries}, indent=2) + "\n",
        encoding="utf-8",
    )


def entry(name: str, repo: Path, commit: str) -> dict[str, str]:
    return {
        "name": name,
        "path": str(repo.resolve()),
        "remote": f"https://example.invalid/{name}.git",
        "tag": "v1.0.0",
        "commit": commit,
    }


def expect(
    implementation: Path,
    manifest: Path,
    success: bool,
    fragment: str | None = None,
) -> None:
    process = run(
        sys.executable,
        str(implementation),
        str(manifest),
        check=False,
    )
    if success and process.returncode != 0:
        raise AssertionError(
            "valid manifest was rejected\n"
            f"stdout:\n{process.stdout}\nstderr:\n{process.stderr}"
        )
    if not success and process.returncode == 0:
        detail = fragment or "rejection"
        raise AssertionError(f"invalid manifest was accepted (expected {detail})")
    if fragment is not None:
        combined = process.stdout + process.stderr
        if fragment not in combined:
            raise AssertionError(
                f"expected error fragment {fragment!r}\noutput:\n{combined}"
            )


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: test_manifest_check.py IMPLEMENTATION.py", file=sys.stderr)
        return 2
    implementation = Path(argv[1]).resolve()

    with tempfile.TemporaryDirectory(prefix="release-manifest-test-") as temporary:
        root = Path(temporary)
        manifest = root / "manifest.json"

        repo_a, commit_a = create_repository(root, "contracts")
        repo_b, commit_b = create_repository(root, "service")
        valid_entries = [
            entry("contracts", repo_a, commit_a),
            entry("service", repo_b, commit_b),
        ]

        write_manifest(manifest, valid_entries)
        expect(implementation, manifest, True)

        write_manifest(manifest, [valid_entries[0], dict(valid_entries[0])])
        expect(implementation, manifest, False, "duplicate")

        duplicate_path = [dict(valid_entries[0]), dict(valid_entries[1])]
        duplicate_path[1]["path"] = duplicate_path[0]["path"]
        write_manifest(manifest, duplicate_path)
        expect(implementation, manifest, False, "duplicate")

        wrong_remote = [dict(valid_entries[0]), dict(valid_entries[1])]
        wrong_remote[0]["remote"] = "https://example.invalid/wrong.git"
        write_manifest(manifest, wrong_remote)
        expect(implementation, manifest, False, "remote")

        write_manifest(manifest, valid_entries)
        (repo_a / "untracked.txt").write_text("dirty\n", encoding="utf-8")
        expect(implementation, manifest, False, "clean")
        (repo_a / "untracked.txt").unlink()

        run("git", "checkout", "-q", "main", cwd=repo_a)
        expect(implementation, manifest, False, "detached")
        run("git", "checkout", "-q", "--detach", commit_a, cwd=repo_a)

        wrong_commit = [dict(valid_entries[0]), dict(valid_entries[1])]
        wrong_commit[0]["commit"] = "0" * 40
        write_manifest(manifest, wrong_commit)
        expect(implementation, manifest, False, "HEAD")

        repo_c, commit_c = create_repository(root, "lightweight", annotated=False)
        write_manifest(manifest, [entry("lightweight", repo_c, commit_c)])
        expect(implementation, manifest, False, "annotated")

    print("release-manifest tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
