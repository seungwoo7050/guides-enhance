# 컴퓨터 네트워크 기초

이 저장소는 컴퓨터 네트워크의 핵심 개념을 문서와 실행 가능한 프로젝트로 함께 확인하는 학습 과정입니다. 별도의 외부 프로젝트 없이 이 저장소만으로 필수 과정을 마칠 수 있습니다. 필수 문서를 읽고 세 개의 필수 프로젝트를 검증하면 링크 전달부터 응용 프로토콜까지 한 요청이 지나가는 과정을 설명하고, 장애가 처음 발생한 단계를 관찰 자료로 좁힐 수 있어야 합니다.

명령 사용법을 외우는 데 초점을 두지 않습니다. 패킷 필드, 경로 선택, TCP 상태, 손실 복구와 진단 결과가 어떤 입력에서 나오는지 직접 확인합니다.

## 완료 역량

이 과정을 마치면 다음 작업을 수행할 수 있어야 합니다.

1. 애플리케이션 데이터가 Ethernet 프레임까지 캡슐화되는 과정을 설명하고, 라우터를 지날 때 바뀌는 값을 구분합니다.
2. Ethernet 프레임, MAC 주소, VLAN, ARP와 IPv6 Neighbor Discovery가 적용되는 범위를 설명합니다.
3. CIDR 프리픽스를 계산하고 최장 프리픽스 일치로 경로를 선택합니다.
4. IP 전달, TTL 또는 Hop Limit, MTU, ICMP, NAT, 연결 추적과 방화벽 판정을 서로 다른 처리 단계로 구분합니다.
5. 라우팅 데이터 평면과 제어 평면을 구분하고 `distance-vector`, `link-state`, `path-vector`가 교환하는 정보를 설명합니다.
6. UDP 데이터그램과 TCP 바이트 스트림의 차이를 바탕으로 메시지 구분, 순서, 손실과 중복 처리 주체를 정합니다.
7. TCP 핸드셰이크와 종료 상태, 순서 번호, ACK, RTT, RTO, `rwnd`와 `cwnd`를 계산합니다.
8. DNS, 경로, 이웃, MTU, 전송, TLS와 HTTP의 성공 여부를 따로 확인하고 마지막 성공 단계와 첫 실패 단계를 기록합니다.

## 필수 문서

### 1. 링크와 패킷 전달 경로

- [계층, 캡슐화와 종단 경로](docs/01-link-and-path/01-layers-encapsulation-and-path.md)
- [Ethernet, MAC 주소와 스위칭](docs/01-link-and-path/02-ethernet-mac-and-switching.md)

### 2. 주소, 다음 홉과 IP 전달

- [IP 주소, 서브넷과 라우팅 조회](docs/02-internetworking/01-ip-addressing-subnets-and-lpm.md)
- [ARP와 IPv6 Neighbor Discovery](docs/01-link-and-path/03-arp-and-neighbor-discovery.md)
- [IP 전달, MTU와 ICMP](docs/02-internetworking/02-ip-forwarding-mtu-and-icmp.md)

### 3. NAT·방화벽과 경로 생성

- [NAT, 연결 추적과 방화벽](docs/02-internetworking/03-nat-connection-tracking-and-firewalls.md)
- [라우팅 알고리즘과 프로토콜](docs/02-internetworking/04-routing-algorithms-and-protocols.md)

### 4. 전송 계층

- [UDP와 TCP의 서비스 특성](docs/03-transport/01-udp-and-tcp-service-contracts.md)
- [TCP 연결 상태와 순서 번호](docs/03-transport/02-tcp-connection-state-and-sequences.md)
- [재전송, RTT와 슬라이딩 윈도](docs/03-transport/03-retransmission-rtt-and-sliding-windows.md)
- [흐름 제어와 혼잡 제어](docs/03-transport/04-flow-and-congestion-control.md)

### 5. 응용 연결과 장애 진단

- [DNS, HTTP, TLS와 QUIC](docs/04-application-security-and-evidence/01-dns-http-tls-and-quic.md)
- [단계별 네트워크 장애 진단](docs/04-application-security-and-evidence/02-network-failure-localization.md)

정확한 순서와 각 프로젝트를 실행할 시점은 [학습 로드맵](docs/00-roadmap.md)에 정리했습니다.

## 필수 프로젝트

### `exercises/protocol-inspector/`

다음 내용을 고정 입력으로 검증합니다.

- 인터넷 체크섬과 IPv4 TCP 의사 헤더 체크섬
- Ethernet II, VLAN 태그 한 개, IPv4와 TCP 파싱
- classic PCAP 레코드 파싱
- IPv4 최장 프리픽스 일치
- 제한된 TCP 상태 기계

### `exercises/linux-routing-nat/`

실제 Linux 네트워크 스택에서 다음 동작을 재현합니다.

- 네트워크 네임스페이스 사이의 IPv4 전달
- TTL 만료와 경로 제거·복구
- SNAT와 응답 방향의 역변환
- 초기 SYN 손실, 재전송과 연결 복구

이 프로젝트는 Linux 관리자 권한, `iproute2`, `iptables`, `tcpdump`와 `tc`가 필요합니다. 일반 개발 장비나 운영 서버가 아니라 폐기 가능한 VM 또는 격리된 Linux 환경에서 실행합니다.

### `exercises/path-diagnosis/`

DNS부터 HTTP까지의 관찰 결과를 읽어 다음 내용을 검증합니다.

- 단계 순서와 입력 형식
- 마지막 성공 단계와 첫 실패 단계
- 관찰값이 뒷받침하는 진단 코드
- 정상, 진단된 실패와 잘못된 입력을 구분하는 종료 상태

## 선택 자료

- [컴퓨터 네트워크 표준 지도](docs/90-standards-map.md)는 RFC와 IANA 레지스트리를 다시 확인할 때 사용하는 참고 문서입니다.
- [송신 창 모델](examples/window-model/README.md)은 `rwnd`, `cwnd`, RTT, RTO와 Reno 상태 변화를 작은 결정적 모델로 확인합니다.
- [tcpdump-analyzer](exercises/tcpdump-analyzer/README.md)는 `tcpdump -nn -tt` 텍스트를 구조화하고 핸드셰이크와 재전송 후보를 찾는 선택 프로젝트입니다.

선택 자료를 완료하지 않아도 필수 과정은 끝낼 수 있습니다. 다만 TCP 윈도 계산이나 캡처 텍스트 분석이 약한 경우 해당 자료로 되돌아가 보완합니다.

## 권장 학습 순서

```text
학습 로드맵
→ 계층·Ethernet·IP 주소·ARP·IP 전달·UDP/TCP 기본 특성
→ protocol-inspector의 체크섬, 패킷, PCAP와 경로 조회 확인
→ NAT·방화벽·라우팅 제어 평면
→ linux-routing-nat의 라우팅과 NAT 실험
→ TCP 상태와 순서 번호
→ protocol-inspector의 TCP 상태와 CLI 확인
→ 재전송·RTT·흐름 제어·혼잡 제어
→ linux-routing-nat의 손실과 복구 실험
→ DNS·TLS·HTTP·QUIC
→ path-diagnosis의 입력 모델 확인
→ 단계별 장애 진단 문서
→ path-diagnosis 전체 검증
→ 완료 기준 점검
```

문서를 모두 읽은 뒤 프로젝트를 한꺼번에 실행하지 않습니다. 필요한 개념을 확보한 시점에 해당 프로젝트를 바로 확인합니다.

## 실행 환경

고정 입력만 사용하는 Python 프로젝트에는 Python 3.10 이상만 필요합니다.

```sh
cd exercises/protocol-inspector
python3 -m unittest discover -s tests -v

cd ../path-diagnosis
python3 -m unittest discover -s tests -v
```

`tcpdump-analyzer`와 `window-model`도 각 프로젝트 디렉터리에서 `python3 -m unittest`로 검증할 수 있습니다.

Linux 실험은 필요한 명령과 권한을 먼저 확인합니다.

```sh
cd exercises/linux-routing-nat
sudo ./scripts/preflight.sh all
sudo ./scripts/run-all.sh
```

## 완료 기준

다음 조건을 모두 만족하면 필수 과정을 완료한 것으로 봅니다.

- 필수 문서 13개를 읽고 각 문서의 완료 기준을 설명할 수 있습니다.
- `protocol-inspector`와 `path-diagnosis`의 모든 단위 검사가 통과합니다.
- 격리된 Linux 환경에서 `linux-routing-nat`의 라우팅, NAT와 손실 실험이 모두 통과합니다.
- 패킷 파서의 결과와 실제 캡처의 관찰 범위를 구분합니다.
- 임의의 연결 실패 사례에서 관찰 위치, 마지막 성공 단계, 첫 실패 단계와 다음 읽기 전용 검사를 기록합니다.

표준과 구현은 바뀔 수 있습니다. 세부 동작이 중요할 때는 [표준 지도](docs/90-standards-map.md)에서 출발해 현재 RFC 상태와 실제 구현 문서를 다시 확인합니다.
