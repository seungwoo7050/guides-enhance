from __future__ import annotations
import re
import subprocess
from pathlib import Path
from typing import Any
SHA_PATTERN = re.compile('^[0-9a-f]{40}$')

class ManifestError(RuntimeError):
    """릴리스 명세의 입력이나 Git 상태가 유효하지 않을 때 사용합니다."""

def git(repo: Path, *args: str, check: bool=True) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(['git', '-C', str(repo), *args], check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and process.returncode != 0:
        detail = process.stderr.strip() or process.stdout.strip()
        raise ManifestError(f"git {' '.join(args)} failed for {repo}: {detail}")
    return process

def normalize_remote(value: str) -> str:
    normalized = value.strip().rstrip('/')
    if normalized.endswith('.git'):
        normalized = normalized[:-4]
    return normalized

def require_string(entry: dict[str, Any], field: str) -> str:
    value = entry.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f'{field} must be a non-empty string')
    return value

def verify_repository(entry: dict[str, Any]) -> None:
    name = require_string(entry, 'name')
    repo = Path(require_string(entry, 'path')).expanduser()
    remote = require_string(entry, 'remote')
    tag = require_string(entry, 'tag')
    commit = require_string(entry, 'commit').lower()
    if not SHA_PATTERN.fullmatch(commit):
        raise ManifestError(f'{name}: commit must be a full 40-character SHA')
    if not repo.is_absolute():
        raise ManifestError(f'{name}: path must be absolute')
    if not repo.is_dir():
        raise ManifestError(f'{name}: repository path does not exist: {repo}')
    inside = git(repo, 'rev-parse', '--is-inside-work-tree').stdout.strip()
    if inside != 'true':
        raise ManifestError(f'{name}: path is not a Git worktree')
    actual_remote = git(repo, 'remote', 'get-url', 'origin', check=False)
    if actual_remote.returncode != 0:
        raise ManifestError(f'{name}: origin remote is missing')
    if normalize_remote(actual_remote.stdout) != normalize_remote(remote):
        raise ManifestError(f'{name}: origin remote does not match manifest')
    status = git(repo, 'status', '--porcelain=v1', '--untracked-files=all').stdout
    if status.strip():
        raise ManifestError(f'{name}: worktree is not clean')
    symbolic = git(repo, 'symbolic-ref', '-q', 'HEAD', check=False)
    if symbolic.returncode == 0:
        raise ManifestError(f'{name}: HEAD must be detached')
    head = git(repo, 'rev-parse', 'HEAD').stdout.strip().lower()
    if head != commit:
        raise ManifestError(f'{name}: HEAD does not match manifest commit')
    tag_ref = f'refs/tags/{tag}'
    tag_type = git(repo, 'cat-file', '-t', tag_ref, check=False)
    if tag_type.returncode != 0:
        raise ManifestError(f'{name}: tag does not exist: {tag}')
    if tag_type.stdout.strip() != 'tag':
        raise ManifestError(f'{name}: tag must be annotated: {tag}')
    peeled = git(repo, 'rev-parse', f'{tag_ref}^{{}}').stdout.strip().lower()
    if peeled != commit:
        raise ManifestError(f'{name}: annotated tag does not peel to manifest commit')
