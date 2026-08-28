"""패킷 파싱과 TCP 상태 변경에서 사용하는 오류를 정의합니다."""


class PacketFormatError(ValueError):
    """입력 바이트가 선언된 프로토콜 형식을 따르지 않을 때 발생합니다."""


class InvalidTransition(ValueError):
    """현재 TCP 상태에서 허용되지 않는 사건을 적용할 때 발생합니다."""
