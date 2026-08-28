"""단계별 관찰 결과에서 첫 실패와 다음 확인 항목을 결정합니다."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .model import StageEvidence, Trace


# [Implementation 2] Diagnosis result model
# 명령행과 자동화 코드가 같은 진단 코드, 근거와 다음 확인 항목을 사용합니다.
@dataclass(frozen=True)
class Diagnosis:
    """진단 코드, 실패 단계, 근거와 다음 확인 항목을 보관합니다."""

    code: str
    layer: str | None
    last_success: str | None
    first_failure: str | None
    summary: str
    evidence: tuple[str, ...]
    next_checks: tuple[str, ...]

    @property
    def healthy(self) -> bool:
        return self.code == "HEALTHY"

    def to_mapping(self) -> dict[str, object]:
        return {
            "code": self.code,
            "healthy": self.healthy,
            "layer": self.layer,
            "last_success": self.last_success,
            "first_failure": self.first_failure,
            "summary": self.summary,
            "evidence": list(self.evidence),
            "next_checks": list(self.next_checks),
        }


Classifier = Callable[[StageEvidence], tuple[str, str, tuple[str, ...]]]


# [Implementation 2-1] First-failure selection
# 추적 기록의 첫 실패만 분류하고 이후 ``not-run`` 단계는 원인 추정에 사용하지 않습니다.
def diagnose(trace: Trace) -> Diagnosis:
    """첫 실패 단계와 ``facts``에 근거해 진단 결과를 만듭니다."""

    failure = trace.first_failure
    if failure is None:
        return Diagnosis(
            code="HEALTHY",
            layer=None,
            last_success=trace.stages[-1].stage,
            first_failure=None,
            summary="All recorded layers succeeded.",
            evidence=tuple(stage.observation for stage in trace.stages),
            next_checks=(
                "Confirm that latency and the returned result satisfy the request contract.",
                "For intermittent failures, collect the same layer evidence at failure time.",
            ),
        )

    classifiers: dict[str, Classifier] = {
        "dns": _classify_dns,
        "route": _classify_route,
        "neighbor": _classify_neighbor,
        "path": _classify_path,
        "transport": _classify_transport,
        "tls": _classify_tls,
        "http": _classify_http,
    }
    code, summary, next_checks = classifiers[failure.stage](failure)
    last_success = trace.last_success
    return Diagnosis(
        code=code,
        layer=failure.stage,
        last_success=last_success.stage if last_success else None,
        first_failure=failure.stage,
        summary=summary,
        evidence=_evidence_lines(failure),
        next_checks=next_checks,
    )


# [Implementation 2-2] Stable text rendering
# 필드 순서를 고정해 사람이 읽는 출력도 반복 실행에서 비교할 수 있게 합니다.
def render_text(diagnosis: Diagnosis) -> str:
    """진단 결과를 필드 순서가 고정된 텍스트로 변환합니다."""

    lines = [
        f"code: {diagnosis.code}",
        f"healthy: {'yes' if diagnosis.healthy else 'no'}",
        f"last_success: {diagnosis.last_success or '-'}",
        f"first_failure: {diagnosis.first_failure or '-'}",
        f"summary: {diagnosis.summary}",
        "evidence:",
    ]
    lines.extend(f"- {item}" for item in diagnosis.evidence)
    lines.append("next_checks:")
    lines.extend(f"- {item}" for item in diagnosis.next_checks)
    return "\n".join(lines)


# [Implementation 2-3] Fact-based diagnosis selection
# 특정 진단 코드는 필요한 ``facts``가 실제로 있을 때만 선택하고 나머지는 일반 실패로 남깁니다.
def _classify_dns(stage: StageEvidence) -> tuple[str, str, tuple[str, ...]]:
    rcode = _text(stage.facts, "rcode").upper()
    if rcode == "NXDOMAIN":
        return (
            "DNS_NAME_NOT_FOUND",
            "The resolver reported that the queried name does not exist.",
            (
                "Verify the queried name and any applied search domain.",
                "Compare the recursive resolver response with the authoritative server.",
                "Retry after the negative-cache TTL expires.",
            ),
        )
    return (
        "DNS_FAILURE",
        "DNS failed before an address candidate was available.",
        (
            "Record the resolver and the exact response code.",
            "Distinguish timeout, SERVFAIL, policy blocking, and delegation errors.",
        ),
    )


def _classify_route(stage: StageEvidence) -> tuple[str, str, tuple[str, ...]]:
    selected = stage.facts.get("selected")
    error = _text(stage.facts, "error")
    if selected is False or error == "no-route":
        return (
            "NO_ROUTE",
            "No local route could be selected for the destination address.",
            (
                "Inspect the effective route lookup for the actual destination.",
                "Check policy rules, VPNs, namespaces, and source-address selection.",
                "Record the final destination-specific result, not only the default route.",
            ),
        )
    return (
        "ROUTE_FAILURE",
        "Local route selection failed.",
        (
            "Inspect the selected table, prefix, next hop, and output interface.",
            "Check whether a selected route points to an unusable interface.",
        ),
    )


def _classify_neighbor(stage: StageEvidence) -> tuple[str, str, tuple[str, ...]]:
    state = _text(stage.facts, "state").upper()
    if state in {"FAILED", "INCOMPLETE", "UNRESOLVED"}:
        return (
            "NEIGHBOR_UNRESOLVED",
            "The link-layer address of the selected next hop could not be resolved.",
            (
                "Verify that ARP Requests or Neighbor Solicitations leave the interface.",
                "Inspect replies, VLAN membership, link state, and duplicate addresses.",
                "Investigate the current-link next hop rather than the remote server.",
            ),
        )
    return (
        "NEIGHBOR_FAILURE",
        "Communication failed before reaching the next hop on the current link.",
        (
            "Inspect neighbor-cache transitions and interface error counters.",
            "Check switch-port, VLAN, and wireless isolation boundaries.",
        ),
    )


def _classify_path(stage: StageEvidence) -> tuple[str, str, tuple[str, ...]]:
    small_ok = stage.facts.get("small_packet_ok") is True
    large_ok = stage.facts.get("large_packet_ok") is True
    too_big_seen = stage.facts.get("icmp_too_big_seen") is True
    if small_ok and not large_ok and not too_big_seen:
        return (
            "MTU_BLACK_HOLE",
            "Small packets pass while larger packets disappear without the required ICMP response.",
            (
                "Inspect the effective MTU across output interfaces and tunnels.",
                "Check whether ICMP Packet Too Big or fragmentation-needed is blocked.",
                "Vary payload size to reproduce the failure boundary.",
            ),
        )
    return (
        "PATH_FAILURE",
        "Forwarding failed after the local neighbor and before the transport exchange.",
        (
            "Inspect hop-limited probes, ICMP, and interface drop counters.",
            "Separate small versus large packets and IPv4 versus IPv6 results.",
        ),
    )


def _classify_transport(stage: StageEvidence) -> tuple[str, str, tuple[str, ...]]:
    if stage.facts.get("rst_received") is True:
        return (
            "CONNECTION_REFUSED",
            "The path responded, but the transport endpoint rejected the connection.",
            (
                "Verify that a process is listening on the selected address and port.",
                "Determine whether the endpoint or an intermediate policy device sent the RST.",
            ),
        )
    syn_sent = stage.facts.get("syn_sent")
    syn_ack = stage.facts.get("syn_ack_received")
    if (
        isinstance(syn_sent, int)
        and not isinstance(syn_sent, bool)
        and syn_sent > 0
        and syn_ack is False
    ):
        return (
            "TRANSPORT_TIMEOUT",
            "Connection attempts were sent without a response before the deadline.",
            (
                "Compare the same SYN tuple at the client and server boundaries.",
                "Inspect firewalls, asymmetric routing, NAT state, and server listening state.",
                "Separate retransmission intervals from the application deadline.",
            ),
        )
    return (
        "TRANSPORT_FAILURE",
        "The transport connection or datagram exchange failed.",
        (
            "Inspect TCP flags and sequence numbers or UDP request-response tuples.",
            "Distinguish EOF, RST, ICMP errors, and timeout.",
        ),
    )


def _classify_tls(stage: StageEvidence) -> tuple[str, str, tuple[str, ...]]:
    if stage.facts.get("certificate_name_match") is False:
        return (
            "TLS_NAME_MISMATCH",
            "The server certificate does not match the requested name.",
            (
                "Verify the requested name and the SNI sent by the client.",
                "Compare the selected IP and virtual host with certificate SAN entries.",
                "Correct DNS or proxy configuration instead of disabling name validation.",
            ),
        )
    return (
        "TLS_HANDSHAKE_FAILED",
        "TLS negotiation or authentication failed after the transport connection.",
        (
            "Inspect TLS alerts, certificate chains, trust stores, and system time.",
            "Check SNI, protocol versions, cipher suites, and ALPN negotiation.",
        ),
    )


def _classify_http(stage: StageEvidence) -> tuple[str, str, tuple[str, ...]]:
    status = stage.facts.get("status")
    if status == 403:
        return (
            "HTTP_FORBIDDEN",
            "Network and TLS succeeded, but HTTP authorization rejected the request.",
            (
                "Separate authentication success from the caller's authorization.",
                "Identify whether the proxy or application generated the 403 response.",
                "Do not bypass application authorization by changing network rules.",
            ),
        )
    if status == 401:
        return (
            "HTTP_UNAUTHORIZED",
            "The HTTP endpoint was reached, but valid authentication is required.",
            (
                "Inspect authorization headers, cookies, and session expiration.",
                "Distinguish TLS client authentication from HTTP authentication.",
            ),
        )
    return (
        "HTTP_FAILURE",
        "The HTTP layer did not satisfy the successful response contract.",
        (
            "Inspect status, redirects, response origin, and body framing.",
            "Record transport success separately from application success.",
        ),
    )


def _evidence_lines(stage: StageEvidence) -> tuple[str, ...]:
    facts = ", ".join(
        f"{key}={_display(value)}" for key, value in sorted(stage.facts.items())
    )
    return (stage.observation, facts) if facts else (stage.observation,)


def _text(facts: Mapping[str, Any], key: str) -> str:
    value = facts.get(key)
    return value.strip() if isinstance(value, str) else ""


def _display(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, list):
        return "[" + ", ".join(_display(item) for item in value) + "]"
    return str(value)
