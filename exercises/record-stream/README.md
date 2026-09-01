# record-stream

`record-stream`은 blocking 파일 디스크립터에서 줄바꿈 문자(`'\n'`)로 구분된 레코드를 한 개씩 반환하는 C 라이브러리입니다.

중요한 점은 다음과 같습니다.

```text
read() 한 번 == 레코드 한 개
```

라고 가정하지 않습니다.

한 레코드가 여러 `read()`에 나뉘어 들어올 수도 있고, 반대로 한 번의 `read()`에 여러 레코드가 함께 들어올 수도 있습니다. 라이브러리는 아직 반환하지 않은 바이트를 내부 pending buffer에 보관해 이 차이를 처리합니다.

또한 레코드 안의 NUL 바이트를 일반 데이터로 보존하므로 반환값은 C 문자열이 아니라 **포인터와 명시적인 길이의 조합**으로 다뤄야 합니다.

## 반환값

```text
1   레코드 하나를 반환함
0   EOF이고 남은 레코드가 없음
-1  잘못된 인자, 입출력 오류 또는 메모리 오류
```

`1`을 반환하면:

```text
*out_record
    새로 할당한 레코드 메모리

*out_length
    반환된 레코드의 바이트 길이
```

이며 `*out_record`는 호출자가 `free`해야 합니다.

`0`이나 `-1`을 반환할 때는 출력 매개변수를 변경하지 않습니다.

따라서 호출자는 반환값이 `1`일 때만 새 출력값을 사용합니다.

## 레코드 경계

줄바꿈 문자 `'\n'`은 레코드를 끝내는 **구분자**이며 반환되는 레코드 내용에는 포함하지 않습니다.

예를 들어 입력 바이트가:

```text
alpha\nbeta\n
```

라면 순서대로 다음 두 레코드를 반환합니다.

```text
"alpha" length=5
"beta"  length=4
```

연속된 줄바꿈 문자는 그 사이에 데이터가 없다는 뜻이므로 길이 0인 레코드를 만듭니다.

예:

```text
\n\n
```

은 두 개의 빈 레코드 경계를 나타냅니다.

줄바꿈 없이 파일이 끝났다면 마지막에 남아 있는 **비어 있지 않은 바이트**를 마지막 레코드로 한 번 반환합니다.

## NUL 바이트

레코드 중간의 NUL 바이트도 그대로 보존합니다.

예:

```text
'a' '\0' 'b' '\n'
```

은 길이 3인 레코드입니다.

```text
61 00 62
```

따라서 다음처럼 `strlen()`에 의존하면 안 됩니다.

```c
strlen(record)
```

`strlen`은 첫 NUL에서 문자열이 끝났다고 판단하기 때문입니다.

대신 반드시 라이브러리가 반환한 길이를 사용합니다.

```c
consume(record, length);
```

또한 문서가 NUL 종료 문자열을 보장하지 않는 한 `printf("%s", record)`처럼 C 문자열 API에 직접 넘기지 않습니다.

## 제공 기능

- 여러 `read`에 나뉜 긴 레코드 처리
- 한 번의 `read`에 여러 레코드가 들어온 경우 처리
- 연속된 줄바꿈 문자를 길이 0인 레코드로 반환
- 줄바꿈 문자 없이 끝난 마지막 비어 있지 않은 레코드 반환
- 데이터 중간의 NUL 바이트 보존
- 반복 호출해도 계속 `0`을 반환하는 EOF 상태
- allocator callback으로 남은 입력 버퍼의 확장 실패 재현
- 호출자가 소유한 파일 디스크립터를 닫지 않는 정리 함수

## 빌드

```sh
make
```

정적 라이브러리는 다음 위치에 생성됩니다.

```text
build/librecord_stream.a
```

## 사용 예시

```c
#include "record_stream.h"

#include <stdlib.h>

struct record_reader reader;
char *record;
size_t length;

record_reader_init(&reader, fd, NULL);

while (record_reader_next(&reader, &record, &length) == 1) {
    consume(record, length);
    free(record);
}

record_reader_destroy(&reader);
```

이 예제에서 `fd`의 소유자는 reader가 아니라 호출자입니다.

```text
caller:
    fd를 열거나 전달받음
    reader에 빌려줌
    reader_destroy 호출
    필요할 때 fd를 직접 close
```

`record_reader_destroy`는 내부 pending buffer만 해제하며 `fd`를 닫지 않습니다.

## 주요 구현 결정

### reader마다 독립적인 pending buffer

각 `record_reader`는 아직 반환하지 않은 입력 바이트를 자신의 상태에 보관합니다.

따라서 두 reader를 동시에 사용해도 다음 상태가 서로 섞이면 안 됩니다.

```text
reader A:
    fd A의 미처리 바이트

reader B:
    fd B의 미처리 바이트
```

전역 버퍼 하나를 공유하는 방식은 두 스트림의 상태를 섞을 수 있으므로 사용하지 않습니다.

### 먼저 pending buffer에서 줄바꿈을 찾음

`record_reader_next`의 기본 흐름은 다음과 같습니다.

```text
현재 pending buffer에서 '\n' 검색
        │
        ├─ 찾음
        │    → 그 앞의 바이트를 한 레코드로 반환
        │    → '\n'까지 내부 입력에서 소비
        │
        └─ 없음
             → EOF인지 확인
             → 아직 읽을 수 있으면 read()
             → 새 바이트를 pending buffer에 추가
             → 다시 검색
```

이 구조 때문에 한 번의 `read()` 호출 크기와 레코드 크기가 일치할 필요가 없습니다.

### 레코드 메모리를 먼저 확보

줄바꿈을 발견했다고 바로 pending buffer에서 바이트를 제거하면 안 됩니다.

예를 들어 반환용 allocation이 그 다음에 실패하면 이미 소비한 레코드를 호출자에게 돌려줄 수도 없고 다시 시도할 수도 없습니다.

따라서 순서는 다음과 같습니다.

```text
레코드 경계 발견
→ 반환용 메모리 확보
→ 필요한 바이트 복사
→ 성공한 뒤 pending buffer에서 해당 레코드와 delimiter 소비
```

이렇게 하면 반환용 메모리 확보에 실패하더라도 아직 반환하지 못한 입력 자체를 먼저 버리는 오류를 피할 수 있습니다.

### pending buffer 확장 실패

새로운 `read()` 결과를 저장하기 위해 내부 pending buffer를 확장해야 할 수 있습니다.

이 확장에 실패하면 reader는 정상적인 입력 진행을 계속할 수 없는 실패 상태가 됩니다. 이후 호출도 `-1`을 반환하도록 상태를 고정하면 "일부 내부 상태만 갱신된 reader를 계속 사용"하는 문제를 피할 수 있습니다.

출력 매개변수는 이런 실패에서도 변경하지 않습니다.

### EOF 상태

EOF에 도달했더라도 pending buffer에 아직 줄바꿈 없는 비어 있지 않은 데이터가 남았다면 그 데이터를 마지막 레코드로 한 번 반환합니다.

그 데이터까지 반환한 뒤에는:

```text
record_reader_next(...) == 0
```

이 되고, 다시 호출해도 계속 `0`을 반환합니다.

즉 EOF는 반복 호출 가능한 안정된 종료 상태입니다.

## blocking FD 전제

이 라이브러리는 blocking 파일 디스크립터를 대상으로 합니다.

따라서 non-blocking FD에서 `read()`가 `EAGAIN` 또는 `EWOULDBLOCK`을 반환하는 상황을 "잠시 데이터가 없음" 상태로 관리하는 기능은 제공하지 않습니다.

non-blocking 스트림을 처리하려면 별도의 재시도 정책이나 `poll`/`select`/`epoll` 같은 준비 상태 관리가 필요합니다.

## 테스트

```sh
make test
make sanitize
```

테스트는 다음을 확인합니다.

- 여러 조각으로 나뉜 레코드
- 빈 레코드와 마지막 줄바꿈 문자
- 줄바꿈 문자 없는 마지막 레코드
- NUL 바이트가 포함된 데이터
- 두 reader의 상태가 섞이지 않는지
- 반복 EOF
- allocator 실패 뒤 출력값 보존과 복구하지 않는 실패 상태
- 잘못된 인자
- `destroy`가 빌린 파일 디스크립터를 닫지 않는지

NUL 바이트 테스트에서는 문자열 함수로 결과를 비교하지 않고 반환된 길이와 바이트 내용을 함께 확인해야 합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Reader state and borrowed file descriptor | `include/record_stream.h` |
| 2 | Pending-buffer growth without state loss | `src/record_stream.c` |
| 3 | Newline search | `src/record_stream.c` |
| 4 | Record allocation before consuming input | `src/record_stream.c` |
| 5 | Read, EOF, and terminal-error handling | `src/record_stream.c` |
| 6 | Internal-buffer cleanup without closing fd | `src/record_stream.c` |

## 범위

다음만 지원합니다.

```text
blocking 파일 디스크립터
구분자 '\n'
길이 기반의 바이트 레코드
```

다음 기능은 제공하지 않습니다.

- non-blocking 재시도
- 구분자 변경
- 문자 인코딩 해석
- 자동 `close`
- 여러 FD를 동시에 기다리는 event loop

즉 이 라이브러리는 **하나의 blocking 바이트 스트림을 줄바꿈 경계로 안정적으로 잘라 반환하는 역할**에 집중합니다.