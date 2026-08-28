"""외부 의존성 없이 command-checker wheel을 만드는 PEP 517 백엔드입니다."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import re
import tomllib
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


# [Implementation 10-4] Validate build metadata and the console script target.
def _project() -> dict[str, Any]:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    if project.get("name") != "command-checker":
        raise ValueError("project.name must be command-checker")
    if project.get("scripts") != {"command-checker": "command_checker.cli:main"}:
        raise ValueError("the command-checker console script contract changed")
    return project


def _dist_info(project: dict[str, Any]) -> str:
    name = re.sub(r"[-_.]+", "_", str(project["name"]))
    version = str(project["version"])
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)*", version):
        raise ValueError(f"unsupported version: {version}")
    return f"{name}-{version}.dist-info"


def _metadata(project: dict[str, Any]) -> dict[str, bytes]:
    dist_info = _dist_info(project)
    metadata = (
        "Metadata-Version: 2.1\n"
        f"Name: {project['name']}\n"
        f"Version: {project['version']}\n"
        f"Summary: {project['description']}\n"
        f"Requires-Python: {project['requires-python']}\n"
        "\n"
    )
    wheel = (
        "Wheel-Version: 1.0\n"
        "Generator: command-checker-build\n"
        "Root-Is-Purelib: true\n"
        "Tag: py3-none-any\n"
    )
    entry_points = "[console_scripts]\ncommand-checker = command_checker.cli:main\n"
    return {
        f"{dist_info}/METADATA": metadata.encode(),
        f"{dist_info}/WHEEL": wheel.encode(),
        f"{dist_info}/entry_points.txt": entry_points.encode(),
    }


def _record_line(path: str, data: bytes) -> tuple[str, str, str]:
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
    return path, f"sha256={digest}", str(len(data))


def _zip_info(path: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    return info


def get_requires_for_build_wheel(config_settings: dict[str, Any] | None = None) -> list[str]:
    del config_settings
    return []


def prepare_metadata_for_build_wheel(
    metadata_directory: str,
    config_settings: dict[str, Any] | None = None,
) -> str:
    del config_settings
    project = _project()
    dist_info = _dist_info(project)
    destination = Path(metadata_directory) / dist_info
    destination.mkdir(parents=True, exist_ok=False)
    for relative, data in _metadata(project).items():
        (destination / Path(relative).name).write_bytes(data)
    return dist_info


# [Implementation 10-5] Build a deterministic wheel and generate RECORD entries.
def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    del config_settings, metadata_directory
    project = _project()
    filename = (
        f"{re.sub(r'[-_.]+', '_', str(project['name']))}-"
        f"{project['version']}-py3-none-any.whl"
    )
    destination = Path(wheel_directory) / filename
    files: dict[str, bytes] = {}
    package = ROOT / "command_checker"
    for path in sorted(package.iterdir()):
        if path.is_file() and (path.suffix == ".py" or path.name == "py.typed"):
            files[f"command_checker/{path.name}"] = path.read_bytes()
    files.update(_metadata(project))

    rows = [_record_line(path, data) for path, data in sorted(files.items())]
    record_path = f"{_dist_info(project)}/RECORD"
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerows([*rows, (record_path, "", "")])
    files[record_path] = buffer.getvalue().encode()

    with zipfile.ZipFile(destination, "w") as archive:
        for relative, data in sorted(files.items()):
            archive.writestr(_zip_info(relative), data)
    return filename
