# record-stream

`record-stream`은 파일 디스크립터에서 줄바꿈 문자로 구분된 레코드를 한 개씩 반환하는 C 라이브러리입니다. 한 번의 `read`와 레코드 하나가 일치하지 않는 경우를 내부의 남은 입력 버퍼로 처리하며, 데이터 중간의 NUL 바이트도 길이와 함께 보존합니다.

## 반환값

```text
1   레코드 하나를 반환함
0   EOF이고 남은 레코드가 없음
-1  잘못된 인자, 입출력 오류 또는 메모리 오류
```

`1`을 반환하면 `*out_record`는 새로 할당한 메모리이며 호출자가 `free`해야 합니다. `0`이나 `-1`을 반환할 때는 출력 매개변수를 변경하지 않습니다.

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

정적 라이브러리는 `build/librecord_stream.a`에 생성됩니다.

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

`record_reader_destroy`는 내부 버퍼만 해제합니다. `fd`는 초기화한 쪽에서 닫아야 합니다.

## 주요 구현 결정

`record_reader_next`는 먼저 남은 입력 버퍼에서 줄바꿈 문자를 찾습니다. 없으면 EOF 여부를 확인하고, 아직 읽을 수 있다면 `read`를 호출해 버퍼에 추가합니다.

레코드를 반환할 새 메모리를 먼저 확보한 뒤 남은 입력 버퍼에서 해당 바이트를 제거합니다. 할당이 실패하면 아직 소비하지 않은 입력이 그대로 남습니다. 내부 버퍼 확장에 실패하면 reader를 복구하지 않는 실패 상태로 바꾸고 이후 호출도 `-1`을 반환합니다.

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

blocking 파일 디스크립터와 줄바꿈 문자만 지원합니다. non-blocking 재시도, 구분자 변경, 문자 인코딩 해석과 자동 `close`는 제공하지 않습니다.
