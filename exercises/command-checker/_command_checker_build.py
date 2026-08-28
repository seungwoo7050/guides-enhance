"""외부 의존성 없이 command-checker wheel을 만드는 PEP 517 백엔드입니다."""
from __future__ import annotations
import tomllib
from pathlib import Path
from typing import Any
ROOT = Path(__file__).resolve().parent

def _metadata(project: dict[str, Any]) -> dict[str, bytes]:
    dist_info = _dist_info(project)
    metadata = f"Metadata-Version: 2.1\nName: {project['name']}\nVersion: {project['version']}\nSummary: {project['description']}\nRequires-Python: {project['requires-python']}\n\n"
    wheel = 'Wheel-Version: 1.0\nGenerator: command-checker-build\nRoot-Is-Purelib: true\nTag: py3-none-any\n'
    entry_points = '[console_scripts]\ncommand-checker = command_checker.cli:main\n'
    return {f'{dist_info}/METADATA': metadata.encode(), f'{dist_info}/WHEEL': wheel.encode(), f'{dist_info}/entry_points.txt': entry_points.encode()}

def get_requires_for_build_wheel(config_settings: dict[str, Any] | None=None) -> list[str]:
    del config_settings
    return []

def prepare_metadata_for_build_wheel(metadata_directory: str, config_settings: dict[str, Any] | None=None) -> str:
    del config_settings
    project = _project()
    dist_info = _dist_info(project)
    destination = Path(metadata_directory) / dist_info
    destination.mkdir(parents=True, exist_ok=False)
    for relative, data in _metadata(project).items():
        (destination / Path(relative).name).write_bytes(data)
    return dist_info

def _project():
    return tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))['project']

def _dist_info(project):
    return str(project['name']).replace('-', '_') + '-' + str(project['version']) + '.dist-info'
