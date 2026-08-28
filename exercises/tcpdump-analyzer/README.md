# tcpdump-analyzer

`tcpdump -nn -tt` 형식의 TCP 텍스트를 읽어 패킷 목록, 3단계 핸드셰이크 완료 여부, 반복 세그먼트 후보를 JSON으로 출력하는 작은 분석 도구입니다. 실제 캡처 권한이 없는 환경에서도 검증할 수 있도록 고정 입력 파일과 단위 테스트를 포함합니다.

## 출력하는 정보

- 파싱에 성공한 TCP 패킷 목록
- SYN → SYN/ACK → ACK의 순서 번호와 ACK 관계가 맞는지 여부
- 방향, 플래그, 순서 번호 범위가 같은 반복 세그먼트 후보
- 첫 관찰 시각, 반복 관찰 시각, 두 시각의 차이

같은 모양의 패킷이 두 번 보였다는 사실만으로 네트워크 손실을 확정하지 않습니다. 패킷 미러링, 중복 캡처, 오프로딩, 순서 뒤바뀜도 같은 결과를 만들 수 있으므로 출력 이름을 `retransmission_candidates`로 유지합니다.

## 프로젝트 구성

```text
tcpdump-analyzer/
├── README.md
├── capture-loopback.sh
├── fixtures/
│   ├── handshake.txt
│   └── retransmission.txt
├── tcpdump_analyzer.py
└── tests/
    └── test_tcpdump_analyzer.py
```

## 요구 환경

저장된 추적 기록 분석과 단위 테스트:

- Python 3.10 이상

실제 loopback 캡처:

- Linux 또는 macOS
- `tcpdump`
- 패킷 캡처 권한

## 저장된 추적 기록 분석

```sh
python3 tcpdump_analyzer.py fixtures/handshake.txt
python3 tcpdump_analyzer.py fixtures/retransmission.txt
```

JSON 출력은 다음 필드를 포함합니다.

```text
packet_count
handshake_complete
retransmission_candidates
packets
```

지원하지 않는 줄은 무시합니다. 바이너리 PCAP이나 PCAPNG를 직접 읽지는 않습니다.

## Loopback 캡처

```sh
sudo ./capture-loopback.sh
```

스크립트는 임시 HTTP 서버를 시작하고 loopback 인터페이스에서 지정한 포트의 TCP 트래픽만 캡처한 뒤 분석기를 실행합니다. 기본 출력 경로는 현재 디렉터리의 `capture.txt`입니다.

```sh
sudo PORT=28080 OUTPUT=/tmp/loopback-tcp.txt ./capture-loopback.sh
```

기존 출력 파일은 덮어쓰지 않습니다. 캡처에는 로컬 프로세스의 주소와 시각 정보가 포함될 수 있으므로 외부에 공유하기 전에 내용을 확인해야 합니다.

## 테스트

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q tcpdump_analyzer.py tests
sh -n capture-loopback.sh
```

실제 캡처는 별도로 실행합니다.

```sh
sudo ./capture-loopback.sh
```

## 설계 결정

### 지원하는 줄 형식을 제한합니다

파서는 모든 tcpdump 출력 형식을 추측하지 않습니다. 타임스탬프, `IP` 또는 `IP6`, 종단점 방향, `Flags`, 선택적인 `seq`, `ack`, `length`가 있는 줄만 패킷 레코드로 바꿉니다.

### 순서 번호와 ACK를 함께 확인합니다

방향만 맞는 패킷 세 개를 핸드셰이크로 판정하지 않습니다. SYN이 순서 번호 공간을 1 사용한다는 규칙을 적용해 SYN/ACK와 마지막 ACK의 ACK 값도 확인합니다.

### 반복 세그먼트는 원인이 아니라 후보입니다

동일한 식별값이 반복되었다는 사실만 출력합니다. 원인을 판단하려면 캡처 위치, 오프로딩 설정, 시각 정보, 양쪽 종단점의 패킷을 추가로 확인해야 합니다.

### 시작한 프로세스만 종료합니다

캡처 스크립트는 자신이 시작한 HTTP 서버와 tcpdump 프로세스, 내부 임시 로그만 정리합니다. 사용자가 지정한 출력 파일은 자동으로 삭제하지 않습니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Supported tcpdump line grammar | `tcpdump_analyzer.py` |
| 1-1 | Parsed TCP packet model | `tcpdump_analyzer.py` |
| 1-2 | Trace normalization | `tcpdump_analyzer.py` |
| 2 | Sequence-aware handshake validation | `tcpdump_analyzer.py` |
| 3 | Repeated-segment candidate detection | `tcpdump_analyzer.py` |
| 4 | Report assembly | `tcpdump_analyzer.py` |
| 4-1 | Trace-file CLI handling | `tcpdump_analyzer.py` |
| 5 | Capture argument validation | `capture-loopback.sh` |
| 5-1 | Started-process cleanup | `capture-loopback.sh` |
| 5-2 | Loopback capture execution | `capture-loopback.sh` |

## 제한 사항

- 바이너리 PCAP과 PCAPNG를 직접 읽지 않습니다.
- 모든 tcpdump 버전과 옵션 조합을 지원하지 않습니다.
- TCP 옵션, 윈도 확장, SACK, RTT, 혼잡 제어는 분석하지 않습니다.
- 반복 패킷의 원인을 확정하지 않습니다.
- 캡처 스크립트는 loopback TCP 트래픽만 생성합니다.
