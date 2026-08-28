# protocol-inspector

외부 패키지와 원시 소켓 없이 Ethernet, IPv4, TCP, classic PCAP, IPv4 라우팅 테이블, 제한된 TCP 상태 전이를 검사하는 Python 도구입니다. 파서는 필요한 바이트가 실제 입력에 존재하는지 먼저 확인한 뒤 헤더에 기록된 길이와 오프셋을 사용합니다. 지원하지 않는 형식을 다른 프로토콜로 잘못 해석하지 않습니다.

## 주요 기능

- 16비트 인터넷 체크섬 계산
- IPv4 TCP 의사 헤더 체크섬 계산
- Ethernet II와 한 개의 802.1Q 또는 802.1ad VLAN 태그 파싱
- IPv4 헤더 길이, 전체 길이, 체크섬 검사
- TCP Data Offset, 플래그, 옵션, 페이로드, 체크섬 검사
- classic PCAP 2.4의 바이트 순서, 타임스탬프 해상도, 레코드 길이 검사
- IPv4 최장 프리픽스 일치와 metric 비교
- 클라이언트와 서버 역할을 구분하는 제한된 TCP 상태 기계
- text와 JSON을 출력하는 CLI
- 각 기능의 경계 조건을 확인하는 프로젝트 내부 단위 테스트

## 프로젝트 구성

```text
protocol-inspector/
├── README.md
├── fixtures/
│   ├── routes.json
│   └── syn-frame.hex
├── protocol_inspector/
│   ├── __init__.py
│   ├── __main__.py
│   ├── checksum.py
│   ├── cli.py
│   ├── errors.py
│   ├── packet.py
│   ├── pcap.py
│   ├── routing.py
│   └── tcp_state.py
└── tests/
```

## 요구 환경

- Python 3.10 이상
- 외부 패키지 없음

## 실행

프로젝트 루트에서 실행합니다.

인터넷 체크섬:

```sh
python3 -m protocol_inspector checksum 0001f203f4f5f6f7
```

Ethernet → IPv4 → TCP 해석:

```sh
python3 -m protocol_inspector decode fixtures/syn-frame.hex
```

경로 조회:

```sh
python3 -m protocol_inspector route \
  --table fixtures/routes.json \
  --destination 10.20.30.8
```

TCP 상태 전이:

```sh
python3 -m protocol_inspector tcp \
  --role server \
  --events passive-open,receive-syn,receive-ack,receive-fin,app-close,receive-ack
```

Classic PCAP 파싱:

```sh
python3 -m protocol_inspector pcap capture.pcap
```

## 테스트

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q protocol_inspector tests
```

검사는 다음과 같은 잘못된 구현을 찾아냅니다.

- 홀수 바이트 입력을 잘못 처리하는 체크섬
- VLAN 태그 뒤 EtherType 오프셋을 바꾸지 않는 파서
- IPv4 전체 길이가 실제 버퍼보다 큰데도 계속 읽는 파서
- 단편화된 IPv4 패킷을 완전한 TCP 세그먼트로 해석하는 파서
- 잘린 PCAP 레코드를 허용하는 파서
- metric을 프리픽스 길이보다 먼저 비교하는 경로 조회
- 허용되지 않은 TCP 사건 뒤 상태를 바꾸는 상태 기계
- 명령 결과와 다른 CLI 출력이나 종료 상태

## 설계 결정

### 길이 필드를 사용하기 전에 입력 바이트를 확인합니다

Ethernet, IPv4, TCP 파서는 최소 헤더 바이트가 실제로 존재하는지 먼저 확인합니다. 그다음 IHL, Total Length, Data Offset이 입력 버퍼 안에 들어오는지 검사합니다.

### 단편화된 IPv4 패킷은 TCP로 이어서 읽지 않습니다

이 도구는 IP 재조립을 구현하지 않습니다. Fragment Offset이 0이 아니거나 More Fragments 플래그가 설정된 패킷은 완전한 TCP 세그먼트로 해석하지 않습니다.

### 경로 비교 순서를 고정합니다

프리픽스 길이를 먼저 비교하고, 길이가 같을 때만 metric을 비교합니다. 두 값이 모두 같으면 `routes.json`에 먼저 기록된 경로를 마지막 동률 기준으로 사용합니다.

### TCP 상태는 `TCPEndpoint`만 변경합니다

지원하지 않는 사건은 기존 상태를 유지한 채 `InvalidTransition`을 발생시킵니다. reset 처리의 상태별 예외도 같은 클래스 안에서 처리합니다.

### PCAP 형식을 먼저 결정합니다

Magic value에서 바이트 순서와 타임스탬프 해상도를 먼저 정한 뒤 global header와 각 레코드 길이를 읽습니다. 파일 끝을 넘는 레코드는 거부합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ---: | -------------- | -------------- |
| 1 | Internet checksum calculation | `protocol_inspector/checksum.py` |
| 1-1 | IPv4 TCP pseudo-header checksum | `protocol_inspector/checksum.py` |
| 2 | Ethernet and VLAN parsing | `protocol_inspector/packet.py` |
| 2-1 | IPv4 length and checksum validation | `protocol_inspector/packet.py` |
| 2-2 | TCP length and checksum validation | `protocol_inspector/packet.py` |
| 2-3 | Supported packet decoding | `protocol_inspector/packet.py` |
| 3 | Classic PCAP record parsing | `protocol_inspector/pcap.py` |
| 4 | Route input validation | `protocol_inspector/routing.py` |
| 4-1 | Longest-prefix route selection | `protocol_inspector/routing.py` |
| 5 | TCP transition table | `protocol_inspector/tcp_state.py` |
| 5-1 | Endpoint state updates | `protocol_inspector/tcp_state.py` |
| 6 | CLI result conversion | `protocol_inspector/cli.py` |
| 6-1 | Subcommand registration and dispatch | `protocol_inspector/cli.py` |

## 제한 사항

- Ethernet FCS를 검사하지 않으며 VLAN 태그는 하나만 처리합니다.
- IPv4만 지원합니다. IPv6, IP 재조립, 여러 터널의 연속 해석은 처리하지 않습니다.
- TCP 옵션은 세부 형식으로 파싱하지 않고 원시 바이트로 보존합니다.
- Classic PCAP만 지원하며 pcapng는 처리하지 않습니다.
- TCP 상태 기계는 핵심 연결 수명주기만 포함합니다. 모든 동시 열기, 타이머, 재전송, 오류 경로를 구현하지 않습니다.
- 신뢰할 수 없는 운영 트래픽을 직접 처리하는 보안 제품이 아닙니다.
