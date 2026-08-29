#!/usr/bin/env python3
"""Django management command entrypoint."""

import os
import sys


# [Implementation 0]
# The generated project and app packages become the persistent command and runtime entrypoints.
def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as error:
        raise ImportError(
            "Django is not installed. Create a virtual environment and run "
            "`python -m pip install .`."
        ) from error
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
