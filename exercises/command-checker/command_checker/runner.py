"""실행 파일을 선택하고 사례 실행과 결과 출력을 처리합니다."""
from __future__ import annotations
import os
import shutil
from pathlib import Path
from .model import SpecificationError

def validate_executable(command: str) -> str:
    contains_separator = os.sep in command or (os.altsep is not None and os.altsep in command)
    if contains_separator:
        path = Path(command).resolve()
    else:
        selected = shutil.which(command)
        if selected is None:
            raise SpecificationError(f'command not found on PATH: {command}')
        path = Path(selected).resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise SpecificationError(f'command is not executable: {command}')
    return str(path)
