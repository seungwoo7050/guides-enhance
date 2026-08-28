# linux-routing-nat

세 개의 Linux 네트워크 네임스페이스를 두 쌍의 veth로 연결해 클라이언트, 라우터, 서버를 한 호스트 안에 구성하는 재현 가능한 실험 프로젝트입니다. 호스트의 기본 경로나 외부 인터페이스는 바꾸지 않습니다. 각 실행은 자신이 만든 네임스페이스, 인터페이스, 프로세스, qdisc, 임시 파일만 정리합니다.

## 확인하는 동작

- 서로 다른 서브넷 사이의 IPv4 전달
- TTL 1과 TTL 2의 차이
- 클라이언트 기본 경로 제거와 복구
- SNAT 뒤 서버가 관찰한 출발지 주소
- 연결 추적을 이용한 응답 역변환
- 초기 SYN을 100% 폐기한 뒤 발생하는 재전송과 연결 복구

```text
client:c0 ── r0:router:r1 ── s0:server
```

## 프로젝트 구성

```text
linux-routing-nat/
├── README.md
├── scripts/
│   ├── common.sh
│   ├── preflight.sh
│   ├── run-all.sh
│   ├── run-loss-retransmission.sh
│   ├── run-nat.sh
│   ├── run-routing.sh
│   ├── tcp_probe.py
│   ├── udp_probe.py
│   └── verify_syn_retransmission.py
└── tests/
    └── test_verify_syn_retransmission.py
```

`common.sh`는 실행마다 고유한 네임스페이스와 veth 이름을 만들고 필요한 주소와 경로를 설정합니다. 각 실행 스크립트는 자신이 시작한 프로세스와 추가한 qdisc, 임시 파일을 직접 정리합니다. 기존 네임스페이스나 인터페이스와 이름이 겹치면 삭제하지 않고 즉시 중단합니다.

## 요구 환경

- Linux
- root 권한 또는 네트워크 네임스페이스를 만들 수 있는 동등한 capability
- Python 3.10 이상
- `iproute2`: `ip`, `tc`
- `ping`, `sysctl`, `grep`
- NAT 실험용 `iptables`
- 재전송 실험용 `tcpdump`

Ubuntu 계열에서는 다음 패키지를 설치할 수 있습니다.

```sh
sudo apt-get update
sudo apt-get install -y iproute2 iputils-ping iptables tcpdump
```

필요한 권한과 명령을 먼저 확인합니다.

```sh
sudo ./scripts/preflight.sh all
```

## 실행

### 라우팅, TTL과 경로 복구

```sh
sudo ./scripts/run-routing.sh
```

다음 항목을 확인합니다.

1. 클라이언트와 서버가 라우터를 거쳐 통신합니다.
2. TTL 1 패킷은 라우터에서 만료됩니다.
3. TTL 2 패킷은 서버에 도달합니다.
4. 클라이언트의 기본 경로를 제거하면 통신이 실패합니다.
5. 경로를 다시 추가하면 통신이 복구됩니다.

### SNAT와 응답 역변환

```sh
sudo ./scripts/run-nat.sh
```

클라이언트는 `10.202.1.2`, 라우터의 외부 인터페이스는 `198.18.0.1`, 서버는 `198.18.0.2`를 사용합니다. 서버가 기록한 상대 주소가 라우터의 외부 주소인지 확인하고, 응답이 원래 클라이언트로 돌아오는지 검증합니다.

이 실험은 주소 변환만 확인합니다. 방화벽 필터 규칙이나 애플리케이션 인가는 검증하지 않습니다.

### SYN 손실과 복구

```sh
sudo ./scripts/run-loss-retransmission.sh
```

라우터의 서버 방향 인터페이스에 `netem loss 100%`를 적용합니다. 클라이언트 캡처에서 같은 튜플과 순서 번호를 가진 SYN이 두 번 보이면 qdisc를 제거합니다. 다음 재전송이 서버에 도달하고 애플리케이션 페이로드가 왕복하는지 확인합니다.

초기 구간을 모두 폐기하므로 임의 손실률을 사용할 때보다 결과가 일정합니다.

### 전체 실행

```sh
sudo ./scripts/run-all.sh
```

세 실험은 각각 새 토폴로지를 만들고 정리합니다. 앞선 실험의 네임스페이스나 프로세스를 다음 실험에서 재사용하지 않습니다.

## 테스트

root 권한 없이 반복 SYN 판정과 입력 문법을 검사할 수 있습니다.

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts tests
sh -n scripts/*.sh
```

실제 네트워크 동작은 Linux 환경에서 확인합니다.

```sh
sudo ./scripts/run-all.sh
```

비정상 종료 뒤 남은 항목을 확인할 때는 다음 명령을 사용합니다.

```sh
sudo ip netns list
sudo ip link show type veth
```

## 설계 결정

### 기존 이름을 덮어쓰지 않습니다

실행에 사용할 네임스페이스나 인터페이스 이름이 이미 존재하면 중단합니다. 정리 코드는 이번 실행이 생성에 성공했다고 기록한 항목에만 적용합니다. 사용자가 만든 기존 네트워크 자원을 자동으로 삭제하지 않습니다.

### UDP 서버 준비 완료를 파일로 알립니다

UDP 서버는 소켓 바인드가 끝난 뒤 배타적으로 표시 파일을 만듭니다. 실행 스크립트는 이 파일을 확인한 다음 데이터그램을 보냅니다. 고정된 `sleep`만 사용할 때 생길 수 있는 초기 패킷 손실을 피하기 위한 처리입니다.

### 반복 SYN은 필요한 식별값을 모두 확인합니다

검증기는 출발지, 목적지, SYN 플래그, 순서 번호가 같은 패킷이 다시 나타났을 때만 성공합니다. 이 실험은 손실을 직접 만들기 때문에 원인을 알고 있지만, 일반적인 캡처에서는 중복 수집, 미러링, 오프로딩 가능성을 추가로 확인해야 합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Run-scoped namespace and link names | `scripts/common.sh` |
| 1-1 | Existing-name collision check | `scripts/common.sh` |
| 1-2 | Cleanup of created namespaces and links | `scripts/common.sh` |
| 2 | Required privilege and command checks | `scripts/preflight.sh` |
| 2-1 | Network namespace capability probe | `scripts/preflight.sh` |
| 3 | Namespace and veth creation | `scripts/common.sh` |
| 3-1 | Routed topology configuration | `scripts/common.sh` |
| 3-2 | SNAT topology configuration | `scripts/common.sh` |
| 4 | Routing, TTL, and route recovery checks | `scripts/run-routing.sh` |
| 5 | UDP request/reply probe | `scripts/udp_probe.py` |
| 5-1 | NAT-run process and file tracking | `scripts/run-nat.sh` |
| 5-2 | SNAT and reverse-path verification | `scripts/run-nat.sh` |
| 6 | TCP request/reply probe | `scripts/tcp_probe.py` |
| 6-1 | Repeated-SYN verification | `scripts/verify_syn_retransmission.py` |
| 6-2 | Loss-run process, qdisc, and file tracking | `scripts/run-loss-retransmission.sh` |
| 6-3 | Deterministic SYN loss and recovery | `scripts/run-loss-retransmission.sh` |
| 7 | Sequential experiment runner | `scripts/run-all.sh` |

## 제한 사항

- Linux 네트워크 네임스페이스, `iptables`, `tc netem`, `tcpdump`가 필요하므로 일반적인 macOS나 Windows 환경에서는 실행할 수 없습니다.
- IPv4만 다룹니다.
- NAT 실험은 SNAT와 응답 역변환만 확인합니다.
- 손실 실험은 혼잡, 경로 변경, 방화벽 폐기 같은 일반 원인을 분류하지 않습니다.
- 회사 장비나 운영 서버가 아니라 폐기 가능한 Linux VM 또는 격리된 개발 환경에서 실행해야 합니다.
