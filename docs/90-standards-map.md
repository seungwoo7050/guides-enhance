# 컴퓨터 네트워크 표준 지도

이 문서는 본문에서 다룬 프로토콜의 기준 RFC와 레지스트리를 찾기 위한 참고 자료입니다. 표준 번호를 외우는 것이 목적은 아닙니다. 구현 동작이나 패킷 캡처가 모호할 때 현재 기준 문서와 갱신·폐기 관계를 확인하는 출발점으로 사용합니다.

RFC와 레지스트리는 바뀔 수 있습니다. 아래 목록은 이 저장소를 작성할 때 사용한 기준이며, 실제 구현 전에는 RFC Editor와 IANA에서 현재 상태와 정오표를 다시 확인해야 합니다.

## 사용하는 순서

```text
관찰한 필드, 상태, 오류를 고정
→ 관련 프로토콜의 현재 기본 RFC 확인
→ Updates와 Obsoletes 관계 확인
→ 실제 구현이 협상한 옵션과 버전 확인
→ 이 저장소에서 생략한 범위와 비교
```

패킷 하나만 보고 프로토콜 전체가 표준을 준수하거나 위반한다고 결론 내려서는 안 됩니다.

## 링크 계층과 인터넷 계층

| 주제 | 기준 문서 |
|---|---|
| ARP | [RFC 826](https://www.rfc-editor.org/rfc/rfc826) |
| IPv4 라우터 요구사항 | [RFC 1812](https://www.rfc-editor.org/rfc/rfc1812) |
| IPv6 | [RFC 8200](https://www.rfc-editor.org/rfc/rfc8200) |
| IPv6 Neighbor Discovery | [RFC 4861](https://www.rfc-editor.org/rfc/rfc4861) |
| IPv6 Path MTU Discovery | [RFC 8201](https://www.rfc-editor.org/rfc/rfc8201) |
| Datagram PLPMTUD | [RFC 8899](https://www.rfc-editor.org/rfc/rfc8899) |
| ICMPv4 | [RFC 792](https://www.rfc-editor.org/rfc/rfc792)와 후속 갱신 문서 |
| ICMPv6 | [RFC 4443](https://www.rfc-editor.org/rfc/rfc4443) |
| 인터넷 체크섬 | [RFC 1071](https://www.rfc-editor.org/rfc/rfc1071) |

Ethernet과 VLAN의 전체 표준은 IEEE 802.3과 802.1Q에서 관리합니다. EtherType과 IP Protocol Number는 IANA 레지스트리의 현재 값을 확인합니다.

## NAT와 라우팅

| 주제 | 기준 문서 |
|---|---|
| UDP NAT 동작 | [RFC 4787](https://www.rfc-editor.org/rfc/rfc4787) |
| TCP NAT 동작 | [RFC 5382](https://www.rfc-editor.org/rfc/rfc5382) |
| Carrier-grade NAT | [RFC 6888](https://www.rfc-editor.org/rfc/rfc6888) |
| OSPFv2 | [RFC 2328](https://www.rfc-editor.org/rfc/rfc2328) |
| BGP-4 | [RFC 4271](https://www.rfc-editor.org/rfc/rfc4271)과 후속 갱신 문서 |

NAT 매핑, 필터링, traversal 동작은 여러 RFC에 나뉩니다. 한 문서의 권고를 모든 장비가 그대로 구현한다고 가정해서는 안 됩니다. 라우팅 프로토콜도 기본 RFC 외에 보안, 주소 체계 확장, 운영 지침을 함께 확인해야 합니다.

## 전송 계층

| 주제 | 기준 문서 |
|---|---|
| UDP | [RFC 768](https://www.rfc-editor.org/rfc/rfc768)과 호스트 요구사항 갱신 문서 |
| TCP 기본 규격 | [RFC 9293](https://www.rfc-editor.org/rfc/rfc9293) |
| TCP 혼잡 제어 | [RFC 5681](https://www.rfc-editor.org/rfc/rfc5681) |
| TCP 재전송 타이머 | [RFC 6298](https://www.rfc-editor.org/rfc/rfc6298) |
| TCP SACK | [RFC 2018](https://www.rfc-editor.org/rfc/rfc2018) |
| SACK 기반 손실 복구 | [RFC 6675](https://www.rfc-editor.org/rfc/rfc6675) |
| CUBIC | [RFC 9438](https://www.rfc-editor.org/rfc/rfc9438) |
| QUIC 전송 | [RFC 9000](https://www.rfc-editor.org/rfc/rfc9000) |
| QUIC 손실 탐지와 혼잡 제어 | [RFC 9002](https://www.rfc-editor.org/rfc/rfc9002) |

실제 TCP 구현은 ECN, 타임스탬프, 윈도 확장, pacing, 추가 손실 복구 알고리즘을 사용할 수 있습니다. 캡처를 해석할 때는 협상한 옵션, 운영체제, 커널 버전, 혼잡 제어 구현을 함께 기록합니다.

## DNS, HTTP와 TLS

| 주제 | 기준 문서 |
|---|---|
| DNS 개념과 구현 | [RFC 1034](https://www.rfc-editor.org/rfc/rfc1034), [RFC 1035](https://www.rfc-editor.org/rfc/rfc1035)와 후속 갱신 문서 |
| DNS 용어 | [RFC 9499](https://www.rfc-editor.org/rfc/rfc9499) |
| SVCB와 HTTPS 레코드 | [RFC 9460](https://www.rfc-editor.org/rfc/rfc9460) |
| HTTP 의미 | [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110) |
| HTTP/1.1 | [RFC 9112](https://www.rfc-editor.org/rfc/rfc9112) |
| HTTP/2 | [RFC 9113](https://www.rfc-editor.org/rfc/rfc9113) |
| HTTP/3 | [RFC 9114](https://www.rfc-editor.org/rfc/rfc9114) |
| TLS 1.3 기준 문서 | [RFC 9846](https://www.rfc-editor.org/rfc/rfc9846) |

기존 자료가 RFC 8446을 참조한다면 RFC 9846의 현재 상태, 대체 관계, 정오표를 다시 확인합니다.

## IANA 레지스트리

- [Protocol Numbers](https://www.iana.org/assignments/protocol-numbers/protocol-numbers.xhtml)
- [Service Name and Transport Protocol Port Number Registry](https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml)
- [TLS Parameters](https://www.iana.org/assignments/tls-parameters/tls-parameters.xhtml)
- [QUIC Registries](https://www.iana.org/assignments/quic/quic.xhtml)

레지스트리 값을 코드에 복사한 뒤 영구 상수라고 가정해서는 안 됩니다. 지원 범위를 명시하고, 알 수 없는 값을 다른 프로토콜로 억지 해석하지 않아야 합니다.

## 이 저장소의 구현 범위

`protocol-inspector`와 다른 프로젝트는 다음 내용을 의도적으로 생략합니다.

- 모든 Ethernet, IPv4, TCP 옵션
- IPv6 확장 헤더와 IP 재조립
- TCP의 모든 타이머, 예외 전이, 최신 손실 복구
- 동적 라우팅 프로토콜의 전송 형식과 전체 수렴 과정
- TLS와 QUIC 암호 구현
- HTTP/2와 HTTP/3 프레임 파서

프로젝트 검사가 통과했다는 사실은 해당 RFC 전체를 구현했다는 뜻이 아닙니다. 각 README가 명시한 입력, 출력, 지원 범위만 보장합니다.
