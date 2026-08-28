"""IPv4 라우팅 테이블에서 최장 프리픽스 일치를 수행합니다."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress


# [Implementation 4] Route input validation
# 문자열 입력을 네트워크, 다음 홉과 metric으로 변환하며 잘못된 값을 즉시 거부합니다.
@dataclass(frozen=True)
class Route:
    network: ipaddress.IPv4Network
    interface: str
    next_hop: ipaddress.IPv4Address | None = None
    metric: int = 0

    @classmethod
    def from_strings(
        cls,
        network: str,
        interface: str,
        *,
        next_hop: str | None = None,
        metric: int = 0,
    ) -> "Route":
        if not interface:
            raise ValueError("An interface name cannot be empty")
        if metric < 0:
            raise ValueError("A route metric cannot be negative")
        return cls(
            network=ipaddress.IPv4Network(network, strict=False),
            interface=interface,
            next_hop=ipaddress.IPv4Address(next_hop) if next_hop else None,
            metric=metric,
        )


class RoutingTable:
    """프리픽스가 같으면 낮은 metric, 먼저 추가된 경로 순으로 선택합니다."""

    def __init__(self, routes: list[Route] | None = None) -> None:
        self._routes: list[Route] = list(routes or [])

    def add(self, route: Route) -> None:
        self._routes.append(route)

    # [Implementation 4-1] Longest-prefix route selection
    # 프리픽스 길이를 먼저 비교하고 metric과 입력 순서는 동률일 때만 사용합니다.
    def lookup(self, destination: str | ipaddress.IPv4Address) -> Route | None:
        address = ipaddress.IPv4Address(destination)
        candidates = [
            (route.network.prefixlen, -route.metric, -index, route)
            for index, route in enumerate(self._routes)
            if address in route.network
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda item: item[:3])[3]

    def routes(self) -> tuple[Route, ...]:
        return tuple(self._routes)
