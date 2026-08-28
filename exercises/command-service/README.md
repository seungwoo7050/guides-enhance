# Command Service

## 개요

`command_service`는 표준 입력에서 한 줄씩 명령을 읽어 메모리의 key/value 저장소를 조작하는 C++98 프로그램입니다. 값은 `TextBuffer`가 직접 소유하고, 입력 해석·데이터 변경·명령 선택·출력 형식을 서로 다른 타입으로 나눴습니다.

저장 가능한 key 수는 실행할 때 정합니다. 새 key를 추가할 때 용량을 넘거나 이미 같은 key가 있으면 기존 데이터는 바뀌지 않습니다.

## 명령

```text
PUT <key> <value>
GET <key>
DELETE <key>
COUNT
LIST
QUIT
```

응답은 다음과 같습니다.

- `PUT`: `OK`, `CONFLICT`, `FULL`
- `GET`: `VALUE <value>` 또는 `NOT_FOUND`
- `DELETE`: `DELETED` 또는 `NOT_FOUND`
- `COUNT`: `COUNT <n>`
- `LIST`: key 오름차순으로 `key=value` 출력
- `QUIT`: `BYE`
- 잘못된 명령이나 인자 수: `BAD_REQUEST`
- 예상하지 못한 내부 오류: `INTERNAL_ERROR`

## 파일별 역할

- `TextBuffer`: NUL 종료 문자열을 소유하고 깊은 복사를 제공합니다.
- `Store`: key/value와 최대 key 수를 관리합니다.
- `RequestParser`: 한 줄을 읽고 명령과 인자 수를 검사합니다.
- `Handler`: 검증된 명령을 `Store` 연산으로 바꿉니다.
- `Router`: 명령 이름에 맞는 handler를 찾고 handler 메모리를 해제합니다.
- `ResponseFormatter`: `Response` 값을 출력 문자열로 바꿉니다.
- `main`: 입력을 반복해서 읽고 오류를 고정된 응답으로 바꿉니다.

## 빌드와 실행

```sh
make
./command_service [capacity]
```

`capacity`를 생략하면 `1024`를 사용합니다.

```sh
printf 'PUT name seungwoo\nGET name\nCOUNT\nQUIT\n' \
  | ./command_service 16
```

```text
OK
VALUE seungwoo
COUNT 1
BYE
```

## 테스트

```sh
make test
```

단위 테스트와 CLI 테스트에서 다음을 확인합니다.

- `TextBuffer`의 깊은 복사와 자기 대입
- 복사 중 할당 실패가 기존 문자열을 지우지 않는지
- 값 복사가 실패한 `PUT`이 key나 크기를 먼저 반영하지 않는지
- 중복 key와 저장 용량 초과가 다른 응답으로 반환되는지
- 명령별 인자 수 검증
- `LIST` 정렬 순서
- 내부 예외 메시지가 출력으로 노출되지 않는지

## 주요 구현 선택

`Store::putNew()`는 중복 key와 용량을 먼저 확인하고, 저장할 `TextBuffer`를 완성한 뒤 `std::map::insert()`를 호출합니다. 값 복사나 map 노드 할당이 실패하면 기존 저장소는 그대로 남습니다.

`Router`는 C++98 코드이므로 handler를 raw pointer로 보관합니다. 생성 중 하나라도 등록하지 못하면 그 전에 만든 handler를 모두 삭제합니다. 소멸자도 같은 정리 함수를 사용합니다.

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

## 범위

key와 value는 공백이 없는 한 개의 token으로 제한합니다. 파일 저장, 동시 접근, 사용자 인증, 네트워크 전송은 구현하지 않습니다. `LIST` 결과에는 별도의 종료 표식을 붙이지 않습니다.
