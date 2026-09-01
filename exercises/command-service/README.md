# Command Service

## 개요

`command_service`는 표준 입력에서 **한 줄씩 명령을 읽어**, 메모리 안의 key/value 저장소를 조작하는 C++98 프로그램입니다.

이 프로젝트의 핵심 학습 목표는 단순한 명령 파서 구현보다 다음 책임을 서로 분리하는 데 있습니다.

```text
입력 한 줄 읽기
→ 명령과 인자 검증
→ 저장소 연산 수행
→ 결과 값을 Response로 표현
→ 고정된 출력 형식으로 변환
```

값 문자열은 `TextBuffer`가 직접 소유하며 깊은 복사를 제공합니다. 입력 해석, 데이터 변경, 명령 선택, 출력 형식은 서로 다른 타입으로 분리되어 있습니다.

저장 가능한 **서로 다른 key의 최대 개수**는 프로그램 실행 시 정합니다. 새 key를 추가할 때 이미 같은 key가 존재하거나 용량을 초과하면 기존 저장소는 변경되지 않습니다.

즉 `PUT`은 실패 시 일부 상태만 반영되는 것이 아니라 다음 invariant를 유지해야 합니다.

```text
PUT 성공
→ 새 key/value가 저장됨
→ size가 1 증가

PUT 실패
→ 기존 key/value와 size가 그대로 유지됨
```

## 명령

지원 명령은 다음과 같습니다.

```text
PUT <key> <value>
GET <key>
DELETE <key>
COUNT
LIST
QUIT
```

이 프로젝트의 범위에서는 `key`와 `value`가 모두 **공백이 없는 하나의 token**입니다.

예:

```text
PUT name seungwoo
PUT city seoul
```

다음과 같이 공백이 들어간 value는 하나의 값으로 지원하지 않습니다.

```text
PUT greeting hello world
```

이 입력은 인자 수가 맞지 않으므로 `BAD_REQUEST`가 됩니다.

## 명령별 의미와 응답

### `PUT <key> <value>`

새 key/value를 저장합니다.

응답:

```text
OK
CONFLICT
FULL
```

의미:

```text
OK
→ 새 key가 정상적으로 저장됨

CONFLICT
→ 이미 같은 key가 존재함
→ 기존 값은 변경되지 않음

FULL
→ 현재 key 수가 capacity에 도달함
→ 저장소는 변경되지 않음
```

이 프로젝트의 `PUT`은 기존 key를 덮어쓰는 update 명령이 아닙니다.

### `GET <key>`

key에 대응하는 값을 읽습니다.

응답:

```text
VALUE <value>
NOT_FOUND
```

예:

```text
PUT name seungwoo
GET name
```

출력:

```text
OK
VALUE seungwoo
```

### `DELETE <key>`

key가 존재하면 삭제합니다.

응답:

```text
DELETED
NOT_FOUND
```

삭제에 성공하면 key 수가 하나 줄어듭니다.

### `COUNT`

현재 저장된 key 수를 반환합니다.

```text
COUNT <n>
```

예:

```text
COUNT 2
```

### `LIST`

모든 key/value를 **key 오름차순**으로 출력합니다.

예를 들어 저장 순서가 다음과 같더라도:

```text
PUT zebra 1
PUT apple 2
```

`LIST`는 다음 순서로 출력합니다.

```text
apple=2
zebra=1
```

`LIST` 결과에는 별도의 시작/종료 marker를 붙이지 않습니다. 저장된 항목이 없으면 추가 항목을 출력하지 않습니다.

### `QUIT`

다음을 출력한 뒤 입력 처리를 종료합니다.

```text
BYE
```

### 잘못된 입력

알 수 없는 명령이나 잘못된 인자 수는 다음으로 통일합니다.

```text
BAD_REQUEST
```

예:

```text
GET
PUT only_key
COUNT extra
UNKNOWN
```

### 예상하지 못한 내부 오류

메모리 할당 실패처럼 정상 command 결과로 표현하기 어려운 내부 실패는 외부에 구현 세부 메시지를 그대로 노출하지 않고 다음으로 변환합니다.

```text
INTERNAL_ERROR
```

예를 들어 `std::bad_alloc::what()` 문자열이나 내부 exception 메시지를 CLI protocol에 직접 노출하지 않습니다.

그렇게 해야 compiler 또는 standard library에 따라 달라질 수 있는 내부 문자열이 외부 protocol이 되는 것을 막을 수 있습니다.

## 파일별 역할

### `TextBuffer`

NUL 종료 문자열을 직접 소유하는 값 타입입니다.

책임:

```text
heap allocation
문자열 복사
destruction
copy construction
copy assignment
self-assignment 처리
```

복사본끼리는 같은 heap buffer를 공유하지 않는 **깊은 복사**를 제공해야 합니다.

### `Store`

key/value와 최대 key 수를 관리합니다.

책임:

```text
중복 key 검사
capacity 검사
새 key/value 삽입
조회
삭제
개수 조회
정렬된 순회
```

### `RequestParser`

입력 한 줄을 command와 argument로 분해하고 명령별 인자 수를 검사합니다.

Parser는 잘못된 요청과 정상 요청을 구분하지만 실제 저장소를 변경하지 않습니다.

### `Handler`

이미 검증된 request를 `Store` 연산으로 변환합니다.

즉 parsing과 storage mutation 사이의 경계입니다.

### `Router`

명령 이름에 맞는 handler를 선택합니다.

C++98 코드이므로 handler를 raw pointer로 소유하며, 자신이 소유한 handler를 정확히 한 번 해제해야 합니다.

### `ResponseFormatter`

`Response` 값과 출력 문자열 형식을 분리합니다.

예를 들어 저장소 연산은 `"OK\n"` 문자열 자체를 생성하기보다 성공 결과를 `Response`로 표현하고 formatter가 문자열로 바꿉니다.

### `main`

다음 orchestration만 담당합니다.

```text
입력 읽기
→ parse
→ route
→ handle
→ format
→ 출력
```

예외가 최상위까지 올라오면 고정된 `INTERNAL_ERROR` 응답으로 변환합니다.

## 빌드와 실행

```sh
make
./command_service [capacity]
```

`capacity`를 생략하면 기본값 `1024`를 사용합니다.

예:

```sh
printf 'PUT name seungwoo\nGET name\nCOUNT\nQUIT\n' \
  | ./command_service 16
```

출력:

```text
OK
VALUE seungwoo
COUNT 1
BYE
```

`capacity`는 저장 가능한 서로 다른 key 개수의 최대값입니다.

예를 들어 capacity가 `1`이라면:

```text
PUT a one
PUT b two
```

응답은 다음과 같습니다.

```text
OK
FULL
```

첫 번째 데이터는 그대로 유지됩니다.

## 예외 안전성과 상태 변경 순서

`Store::putNew()`는 상태를 먼저 변경한 뒤 위험한 복사를 수행하면 안 됩니다.

잘못된 순서:

```text
size 증가
→ key 등록
→ value 복사
→ value 복사 중 예외
```

이 경우 실패했는데도 일부 상태가 이미 변경될 수 있습니다.

대신 다음 순서를 사용합니다.

```text
중복 key 확인
→ capacity 확인
→ 저장할 TextBuffer 완성
→ map insert 시도
→ 성공한 뒤 새 상태가 관찰됨
```

`TextBuffer` 복사나 map node allocation 중 예외가 발생하면 기존 저장소는 그대로 남아야 합니다.

이것은 `PUT`이 제공하려는 **strong exception guarantee**에 해당합니다.

```text
성공
→ 전체 변경 반영

실패
→ 호출 전 상태 유지
```

## `TextBuffer` copy assignment

`TextBuffer`가 heap memory를 직접 소유한다면 다음과 같은 단순 대입은 위험합니다.

```text
기존 buffer 삭제
→ 새 buffer allocation
→ allocation 실패
```

allocation이 실패하면 기존 문자열까지 이미 사라집니다.

따라서 새 내용을 먼저 준비한 뒤 기존 상태를 교체하는 순서가 필요합니다.

개념적으로:

```text
새 buffer allocation
→ 문자열 복사 성공
→ 기존 buffer 삭제
→ 새 buffer를 owner로 채택
```

이렇게 하면 새 allocation이 실패해도 기존 값은 유지됩니다.

자기 대입도 안전해야 합니다.

```cpp
buffer = buffer;
```

이 호출이 기존 데이터를 지우거나 dangling pointer를 만들면 안 됩니다.

## `Router`의 raw pointer 소유권

C++98에는 `std::unique_ptr`가 없으므로 `Router`가 handler를 raw pointer로 보관할 수 있습니다.

이때 중요한 것은 pointer 자체가 아니라 **소유권 규칙**입니다.

```text
Router가 등록한 handler의 유일한 owner
Router 소멸
→ 모든 handler delete
```

생성 중 일부 handler만 등록된 뒤 다음 등록이 실패할 수도 있습니다.

예:

```text
handler A 생성 성공
handler B 생성 성공
handler C 생성 또는 등록 실패
```

이 경우 다음 순서로 정리해야 합니다.

```text
B 삭제
→ A 삭제
→ 예외 재전파 또는 생성 실패 처리
```

따라서 constructor 실패 경로와 destructor가 같은 cleanup helper를 공유하면 중복 코드를 줄일 수 있습니다.

중요한 점은 constructor가 끝나기 전에 예외가 발생하면 `Router`의 destructor가 자동으로 호출된다고 기대할 수 없다는 것입니다. 완전히 생성되지 않은 객체의 destructor는 호출되지 않으므로 constructor 내부에서 확보한 raw resource는 직접 정리해야 합니다.

## 테스트

```sh
make test
```

단위 테스트와 CLI 테스트에서 다음을 확인합니다.

- `TextBuffer` 깊은 복사
- `TextBuffer` 자기 대입
- 복사 중 allocation 실패가 기존 문자열을 지우지 않는지
- 값 복사가 실패한 `PUT`이 key나 size를 먼저 반영하지 않는지
- 중복 key와 저장 용량 초과가 서로 다른 응답인지
- 명령별 인자 수 검증
- `LIST` 정렬 순서
- 내부 exception 메시지가 출력 protocol에 노출되지 않는지

추가로 상태 변경 실패를 검사할 때는 **응답만 확인하지 말고 저장소 상태도 확인**해야 합니다.

예:

```text
PUT 실패 발생
→ COUNT가 이전과 같은가
→ 기존 GET 결과가 같은가
→ LIST 결과가 같은가
```

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Failure types for parse, conflict, and capacity errors | `include/Errors.hpp` |
| 2 | Heap-backed text ownership | `include/TextBuffer.hpp` |
| 2-1 | Allocation and string lifetime | `src/TextBuffer.cpp` |
| 2-2 | Copy assignment with rollback | `src/TextBuffer.cpp` |
| 3 | Bounded ordered key/value storage | `include/Store.hpp` |
| 3-1 | Validate before inserting | `src/Store.cpp` |
| 3-2 | Read, erase, count, and sorted listing | `src/Store.cpp` |
| 4 | Whole-line command parsing | `src/RequestParser.cpp` |
| 5 | Response values independent of text formatting | `include/Response.hpp` |
| 6 | Command handler base class and implementations | `include/Handler.hpp` |
| 6-1 | Map valid requests to store operations | `src/Handler.cpp` |
| 7 | Own handlers and select by command | `src/Router.cpp` |
| 8 | Read commands, print responses, and map failures | `src/main.cpp` |

이 순서는 먼저 값과 실패 규칙을 정의하고, 그 위에 저장소와 command dispatch를 쌓도록 구성되어 있습니다.

## 범위

다음은 이 프로젝트의 의도적인 제한입니다.

```text
key: 공백 없는 단일 token
value: 공백 없는 단일 token
storage: memory only
concurrency: 없음
authentication: 없음
network transport: 없음
LIST 종료 marker: 없음
```

파일 저장, 동시 접근, 사용자 인증, 네트워크 전송은 구현하지 않습니다.