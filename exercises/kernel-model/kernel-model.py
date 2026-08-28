#!/usr/bin/env python3
"""kernel-model 명령을 실행하고 종료 상태를 운영체제에 반환합니다."""

# [Implementation 9-3] CLI process 진입점
from kernel_model.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
