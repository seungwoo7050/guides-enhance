"""경기 수용, 서버 배치, 대기열, drain을 결정적으로 재현하는 시뮬레이터입니다."""

from .engine import run_scenario

__all__ = ["run_scenario"]
