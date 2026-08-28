# 컴퓨터 네트워크 학습 로드맵

이 문서는 필수 문서와 프로젝트를 실제 의존 순서로 정리합니다. 목표는 네트워크 용어를 폭넓게 암기하는 것이 아니라, 패킷이 전달되는 조건과 실패 지점을 직접 계산하고 검증하는 것입니다.

## 대상 독자

다음 조건을 만족하는 개발자를 대상으로 합니다.

- 하나 이상의 프로그래밍 언어로 작은 프로그램을 실행해 본 경험이 있습니다.
- 터미널에서 명령의 표준 출력, 표준 오류와 종료 상태를 확인할 수 있습니다.
- Python의 조건문, 반복문, 함수와 단위 검사를 읽을 수 있습니다.
- 웹, 서버, 인프라 또는 시스템 프로그램의 연결 문제를 원인 추측이 아니라 관찰 자료로 좁히고 싶습니다.

소켓 API 사용법 자체는 이 과정의 중심이 아닙니다. `socket`, `bind`, `connect`, `accept`, 부분 입출력과 파일 디스크립터 수명은 C 또는 C++ 자료에서 별도로 학습할 수 있습니다.

## 완료 역량

완료 후에는 다음 내용을 설명하거나 재현할 수 있어야 합니다.

1. 애플리케이션 데이터가 Ethernet 프레임까지 캡슐화되는 과정
2. 스위치의 MAC 학습, VLAN 범위와 라우터의 IP 전달 차이
3. 목적지 IP, 경로가 선택한 다음 홉과 ARP·Neighbor Discovery 대상의 차이
4. CIDR 계산과 최장 프리픽스 일치
5. TTL 또는 Hop Limit, MTU, ICMP와 전달 실패
6. NAT 매핑, 연결 추적과 방화벽 판정의 차이
7. 경로 학습, 선택, 설치와 실제 패킷 전달의 차이
8. UDP 데이터그램과 TCP 바이트 스트림의 보장 범위
9. TCP 상태, 순서 번호, ACK, 재전송, RTT와 RTO
10. `rwnd`, `cwnd`, 전송 중 바이트와 애플리케이션 역압의 관계
11. DNS, 주소 선택, 전송, TLS, HTTP와 QUIC의 독립된 성공·실패 단계
12. 마지막 성공 단계와 첫 실패 단계를 원본 관찰값으로 뒷받침하는 진단 방법

## 필수 문서와 프로젝트

### 1단계. 패킷과 링크

필수 문서:

- `docs/01-link-and-path/01-layers-encapsulation-and-path.md`
- `docs/01-link-and-path/02-ethernet-mac-and-switching.md`

확보해야 할 내용:

- 캡슐화와 역다중화
- Ethernet II 프레임의 최소 필드
- MAC 주소가 적용되는 범위
- 스위치 학습과 플러딩
- VLAN이 나누는 브로드캐스트 도메인

이 단계에서는 `protocol-inspector/fixtures/syn-frame.hex`를 열어 Ethernet, IPv4와 TCP가 시작하는 바이트 오프셋을 손으로 계산합니다. 아직 파서 결과를 보지 말고 예상값부터 기록합니다.

### 2단계. 주소, 다음 홉과 전달

필수 문서:

- `docs/02-internetworking/01-ip-addressing-subnets-and-lpm.md`
- `docs/01-link-and-path/03-arp-and-neighbor-discovery.md`
- `docs/02-internetworking/02-ip-forwarding-mtu-and-icmp.md`
- `docs/03-transport/01-udp-and-tcp-service-contracts.md`

확보해야 할 내용:

- CIDR 프리픽스와 서브넷 계산
- 최장 프리픽스 일치와 메트릭 비교 순서
- 직접 연결 목적지와 게이트웨이 목적지의 이웃 조회 대상
- 라우터의 입력 검증, TTL 감소, 경로 선택과 새 프레임 생성
- 경로 MTU, ICMP와 MTU 블랙홀
- UDP 메시지 단위와 TCP 바이트 스트림 프레이밍

이 개념을 확보한 뒤 `exercises/protocol-inspector/`에서 다음 기능을 순서대로 확인합니다.

```text
체크섬
→ Ethernet/VLAN/IPv4/TCP 파서
→ classic PCAP 파서
→ 경로 조회
```

검증 명령:

```sh
cd exercises/protocol-inspector
python3 -m unittest \
  tests.test_checksum \
  tests.test_packet \
  tests.test_pcap \
  tests.test_routing -v
```

### 3단계. NAT와 경로 생성

필수 문서:

- `docs/02-internetworking/03-nat-connection-tracking-and-firewalls.md`
- `docs/02-internetworking/04-routing-algorithms-and-protocols.md`

확보해야 할 내용:

- SNAT와 DNAT가 바꾸는 튜플
- 응답을 원래 튜플로 되돌리는 매핑 상태
- NAT와 방화벽 허용 판정의 차이
- 전달 테이블 조회와 라우팅 프로토콜 계산의 차이
- `distance-vector`, `link-state`, `path-vector`가 교환하는 정보
- 수렴 중 루프와 블랙홀 가능성

개념을 확인한 뒤 격리된 Linux 환경에서 다음 실험을 실행합니다.

```sh
cd exercises/linux-routing-nat
sudo ./scripts/preflight.sh routing
sudo ./scripts/run-routing.sh

sudo ./scripts/preflight.sh nat
sudo ./scripts/run-nat.sh
```

라우팅 실험에서는 TTL 1과 TTL 2, 기본 경로 제거와 복구를 확인합니다. NAT 실험에서는 서버가 관찰한 출발지 주소와 클라이언트가 받은 응답을 함께 확인합니다.

### 4단계. TCP 상태와 손실 복구

필수 문서:

- `docs/03-transport/02-tcp-connection-state-and-sequences.md`
- `docs/03-transport/03-retransmission-rtt-and-sliding-windows.md`
- `docs/03-transport/04-flow-and-congestion-control.md`

확보해야 할 내용:

- 능동 열기와 수동 열기의 상태 차이
- SYN, FIN과 페이로드가 소비하는 순서 번호 범위
- 누적 ACK, 중복 ACK와 SACK의 의미
- RTT 표본, RTO와 제한 시간 백오프
- `rwnd`, `cwnd`, 유효 윈도와 전송 중 바이트
- 흐름 제어, 혼잡 제어와 애플리케이션 큐의 차이

TCP 상태 문서를 읽은 뒤 `protocol-inspector`의 상태 기계와 CLI를 검증합니다.

```sh
cd exercises/protocol-inspector
python3 -m unittest tests.test_tcp_state tests.test_cli -v
```

그다음 재전송 문서를 읽고 Linux 손실 실험을 실행합니다.

```sh
cd exercises/linux-routing-nat
sudo ./scripts/preflight.sh loss
sudo ./scripts/run-loss-retransmission.sh
```

동일한 SYN이 다시 관찰된 사실은 이 실험에서 손실을 직접 만들었기 때문에 재전송 근거가 됩니다. 일반 캡처에서는 중복 수집, 미러링과 오프로딩 가능성을 별도로 확인해야 합니다.

`rwnd`, `cwnd`와 RTO 계산이 약하면 선택 자료인 `examples/window-model/`을 실행합니다.

### 5단계. 응용 연결과 진단

필수 문서:

- `docs/04-application-security-and-evidence/01-dns-http-tls-and-quic.md`
- `docs/04-application-security-and-evidence/02-network-failure-localization.md`

확보해야 할 내용:

- DNS 응답과 실제 연결 주소 선택의 차이
- TCP 또는 QUIC 연결, TLS 인증과 HTTP 응답의 차이
- IPv6에서 IPv4로, HTTP/3에서 HTTP/2로 대체한 사실을 기록하는 방법
- 관찰, 해석, 가설과 변경을 분리하는 방법
- 마지막 성공 단계와 첫 실패 단계

먼저 `path-diagnosis`의 입력 형식과 고정 입력 파일을 확인합니다.

```text
dns
→ route
→ neighbor
→ path
→ transport
→ tls
→ http
```

그다음 전체 단위 검사를 실행합니다.

```sh
cd exercises/path-diagnosis
python3 -m unittest discover -s tests -v
```

정상 추적 기록과 각 실패 고정 입력에서 `last_success`, `first_failure`, 진단 코드와 다음 확인 항목이 원본 `facts`에 근거하는지 확인합니다.

## 필수 학습 순서

```text
로드맵
→ 계층과 Ethernet
→ IP 주소, ARP/ND, IP 전달, UDP/TCP 기본 특성
→ protocol-inspector: 체크섬, 패킷, PCAP, 경로 조회
→ NAT와 라우팅 제어 평면
→ linux-routing-nat: 라우팅, NAT
→ TCP 상태
→ protocol-inspector: TCP 상태, CLI
→ 재전송, RTT, 흐름 제어, 혼잡 제어
→ linux-routing-nat: 손실, 재전송, 복구
→ DNS, TLS, HTTP, QUIC
→ path-diagnosis 입력 모델
→ 장애 진단 방법
→ path-diagnosis 전체 검증
→ 선택적 보완
→ 완료 기준 점검
```

## 선택 자료

### `docs/90-standards-map.md`

본문 설명이나 캡처가 모호할 때 현재 RFC와 레지스트리를 찾는 출발점입니다. 필수 문서의 내용을 대체하지 않습니다.

### `examples/window-model/`

다음을 결정적인 숫자로 다시 확인합니다.

- `in_flight = next_sequence - send_base`
- `effective_window = min(rwnd, cwnd)`
- RTT 평활화와 RTO 백오프
- Reno 느린 시작, 혼잡 회피와 빠른 복구

### `exercises/tcpdump-analyzer/`

`tcpdump -nn -tt` 텍스트를 파싱하고 순서 번호까지 확인해 핸드셰이크와 재전송 후보를 찾습니다. 바이너리 PCAP 파싱이나 일반적인 손실 원인 판정은 다루지 않습니다.

## 완료 기준

다음 항목을 모두 만족해야 합니다.

- 필수 문서 13개의 완료 기준을 자신의 말로 설명할 수 있습니다.
- `protocol-inspector`와 `path-diagnosis`의 단위 검사가 모두 통과합니다.
- 격리된 Linux 환경에서 라우팅, NAT와 손실 실험이 모두 통과합니다.
- 임의의 목적지에 대해 경로와 다음 홉을 계산할 수 있습니다.
- 주어진 TCP 순서 번호와 ACK에서 확인된 바이트 범위를 계산할 수 있습니다.
- 동일한 패킷이 반복된 사실과 실제 손실 원인 확정을 구분합니다.
- 연결 실패 사례에 대해 실행 위치, 관찰 시각, 마지막 성공 단계, 첫 실패 단계와 다음 읽기 전용 검사를 작성합니다.

이 조건을 만족하면 특정 장비나 프로토콜 구현의 세부 사항은 실제 문제를 만났을 때 다시 찾아볼 수 있습니다. 기본 개념과 검증 방법을 처음부터 반복할 필요는 없습니다.
