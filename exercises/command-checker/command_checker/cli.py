"""Inspect a JSON case specification."""
from __future__ import annotations
import argparse
from pathlib import Path
from typing import Sequence
from .specification import load_cases

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a command case specification")
    parser.add_argument("--cases", type=Path, required=True)
    arguments = parser.parse_args(argv)
    cases = load_cases(arguments.cases)
    print(f"Validated {len(cases)} cases")
    return 0
