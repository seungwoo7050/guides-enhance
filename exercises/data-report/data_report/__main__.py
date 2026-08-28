# [Implementation 1-1] Delegate module execution to the installed CLI entry point.
from .cli import main

raise SystemExit(main())
