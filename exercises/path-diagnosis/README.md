# path-diagnosis

DNS부터 HTTP까지 수집한 관찰값을 순서가 있는 JSON 추적 기록으로 읽고, 마지막 성공 단계와 첫 실패 단계, 진단 코드, 다음 확인 항목을 반환하는 CLI입니다. 실제 네트워크를 변경하거나 외부 종단점에 접속하지 않습니다. 입력 형식과 단계 진행이 올바른지 먼저 확인한 뒤 결과를 계산합니다.

## 처리 순서

```text
dns
→ route
→ neighbor
→ path
→ transport
→ tls
→ http
```

유효한 실패 추적 기록은 다음 조건을 만족해야 합니다.

- 첫 실패 전 단계는 모두 `ok`입니다.
- `failed` 단계는 하나만 존재합니다.
- 첫 실패 뒤 단계는 모두 `not-run`입니다.

이 규칙과 모순되는 입력은 진단 결과를 만들지 않고 `TraceFormatError`로 거부합니다.

## 주요 기능

- 요청 이름, 포트, 전송 프로토콜, 애플리케이션 값 검사
- 일곱 단계의 순서 검사
- 파일 읽기, JSON 문법, 필드 형식 오류를 `TraceFormatError`로 변환
- 마지막 성공 단계와 첫 실패 단계 계산
- `facts`가 뒷받침하는 진단 코드 선택
- 자료가 부족할 때 단계별 일반 코드 반환
- text와 JSON 출력
- 정상, 진단된 실패, 잘못된 입력을 구분하는 종료 상태

## 프로젝트 구성

```text
path-diagnosis/
├── README.md
├── fixtures/
│   ├── dns-nxdomain.json
│   ├── healthy.json
│   ├── http-forbidden.json
│   ├── mtu-black-hole.json
│   ├── neighbor-unresolved.json
│   ├── route-missing.json
│   ├── tls-name-mismatch.json
│   └── transport-timeout.json
├── path_diagnosis/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── diagnose.py
│   └── model.py
└── tests/
    ├── test_cli.py
    ├── test_diagnose.py
    └── test_model.py
```

## 요구 환경

- Python 3.10 이상
- 외부 패키지 없음

## 입력 형식

최상위 JSON 객체는 `request`와 `stages`를 포함합니다.

```json
{
  "request": {
    "name": "api.example.test",
    "port": 443,
    "transport": "tcp",
    "application": "https"
  },
  "stages": [
    {
      "stage": "dns",
      "status": "ok",
      "observation": "The resolver returned an address candidate.",
      "facts": {"rcode": "NOERROR"}
    }
  ]
}
```

실제 입력에는 일곱 단계가 정확한 순서로 모두 있어야 합니다. 진단기는 고정 입력 파일에 적힌 예상 코드를 그대로 반환하지 않습니다. 각 단계의 `facts`를 읽어 결과를 선택합니다.

## 실행

Text 출력:

```sh
python3 -m path_diagnosis fixtures/healthy.json
python3 -m path_diagnosis fixtures/mtu-black-hole.json
```

JSON 출력:

```sh
python3 -m path_diagnosis fixtures/tls-name-mismatch.json --format json
```

종료 상태:

| 상태 | 의미 |
| ---: | --- |
| 0 | 입력이 유효하며 모든 단계가 정상입니다. |
| 1 | 입력이 유효하며 실패를 진단했습니다. |
| 2 | 파일, JSON 또는 추적 기록 형식이 잘못되었습니다. |

## 포함된 고정 입력

| Fixture | 첫 실패 | 진단 코드 |
| --- | --- | --- |
| `healthy.json` | 없음 | `HEALTHY` |
| `dns-nxdomain.json` | `dns` | `DNS_NAME_NOT_FOUND` |
| `route-missing.json` | `route` | `NO_ROUTE` |
| `neighbor-unresolved.json` | `neighbor` | `NEIGHBOR_UNRESOLVED` |
| `mtu-black-hole.json` | `path` | `MTU_BLACK_HOLE` |
| `transport-timeout.json` | `transport` | `TRANSPORT_TIMEOUT` |
| `tls-name-mismatch.json` | `tls` | `TLS_NAME_MISMATCH` |
| `http-forbidden.json` | `http` | `HTTP_FORBIDDEN` |

## 테스트

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q path_diagnosis tests
```

CLI 확인:

```sh
python3 -m path_diagnosis fixtures/healthy.json
python3 -m path_diagnosis fixtures/mtu-black-hole.json --format json
```

## 설계 결정

### 진단 코드보다 실패 단계를 먼저 정합니다

진단 코드를 고르기 전에 `last_success`와 `first_failure`를 계산합니다. 이 순서를 지키면 HTTP 403을 네트워크 경로 실패로 처리하거나, DNS 실패 뒤 실행되지 않은 TLS 단계를 원인으로 표시하는 오류를 막을 수 있습니다.

### 입력의 `facts`가 뒷받침하는 코드만 반환합니다

`path` 단계가 실패했다는 사실만으로 `MTU_BLACK_HOLE`을 반환하지 않습니다. 작은 패킷은 성공하고 큰 패킷은 실패하며 필요한 ICMP가 보이지 않을 때만 해당 코드를 선택합니다. 자료가 부족하면 `PATH_FAILURE`로 남깁니다.

### 외부 입력 오류를 하나의 예외로 전달합니다

파일 접근 오류, 잘못된 JSON, 누락된 필드, 단계 진행 모순을 내부 `KeyError`나 traceback으로 노출하지 않습니다. `TraceFormatError`와 종료 상태 2로 바꿉니다.

### 같은 입력은 같은 결과를 만듭니다

네트워크 명령이나 실제 시계를 사용하지 않습니다. 같은 추적 기록은 항상 같은 결과를 반환하므로 테스트와 장애 검토에 사용할 수 있습니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Request field validation | `path_diagnosis/model.py` |
| 1-1 | Stage record validation | `path_diagnosis/model.py` |
| 1-2 | Trace progression validation | `path_diagnosis/model.py` |
| 1-3 | Trace file loading | `path_diagnosis/model.py` |
| 2 | Diagnosis result model | `path_diagnosis/diagnose.py` |
| 2-1 | First-failure selection | `path_diagnosis/diagnose.py` |
| 2-2 | Stable text rendering | `path_diagnosis/diagnose.py` |
| 2-3 | Fact-based diagnosis selection | `path_diagnosis/diagnose.py` |
| 3 | CLI argument and output handling | `path_diagnosis/cli.py` |
| 3-1 | Exit-status and input-error handling | `path_diagnosis/cli.py` |

## 제한 사항

- 관찰 자료를 직접 수집하지 않습니다.
- 캡처 위치와 입력 `facts`가 잘못되면 결과도 잘못될 수 있습니다.
- 포함된 필드만 해석하며 제품별 오류 전체를 분류하지 않습니다.
- 자동 결과는 조사 시작점입니다. 운영 환경을 변경하기 전에 원본 명령 출력, 관찰 위치, 시각을 다시 확인해야 합니다.
