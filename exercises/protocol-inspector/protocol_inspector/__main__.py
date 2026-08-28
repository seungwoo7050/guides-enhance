"""``python -m protocol_inspector`` 실행을 명령행 진입점에 연결합니다."""

from .cli import main

raise SystemExit(main())
