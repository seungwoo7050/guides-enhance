# POSIX 입출력과 스트림 상태

POSIX의 `read`와 `write`는 요청한 바이트 수를 항상 한 번에 처리하지 않습니다. 파일, 파이프, 터미널과 소켓은 서로 다른 조건에서 일부만 처리하거나 중단될 수 있습니다. 호출 한 번과 논리적인 줄·레코드 하나를 같은 것으로 보면 안 됩니다.

## 파일 디스크립터

파일 디스크립터는 프로세스가 열린 파일이나 파이프를 가리킬 때 사용하는 작은 정수입니다.

```text
0  표준 입력
1  표준 출력
2  표준 오류
```

`open`, `pipe`, `dup` 계열 함수가 반환한 파일 디스크립터는 더 이상 필요하지 않을 때 `close`해야 합니다.

## `read`

```c
ssize_t count = read(fd, buffer, capacity);
```

```text
count > 0   실제로 읽은 바이트 수
count == 0  EOF
count == -1 오류, errno 확인
```

요청한 `capacity`보다 적은 바이트를 읽었다고 EOF라는 뜻은 아닙니다. 현재 읽을 수 있는 데이터가 그만큼뿐일 수 있습니다.

## `write`

성공해도 요청한 길이보다 적게 쓸 수 있습니다. 남은 바이트를 계속 써야 합니다.

```c
int write_all(int fd, const void *data, size_t length) {
    const unsigned char *cursor = data;

    while (length > 0) {
        ssize_t count = write(fd, cursor, length);

        if (count > 0) {
            cursor += (size_t)count;
            length -= (size_t)count;
            continue;
        }
        if (count == -1 && errno == EINTR) {
            continue;
        }
        return -1;
    }
    return 0;
}
```

## `EINTR`

시스템 호출이 시그널 때문에 중단되면 `-1`을 반환하고 `errno == EINTR`일 수 있습니다.

```c
do {
    count = read(fd, buffer, sizeof buffer);
} while (count == -1 && errno == EINTR);
```

모든 오류를 재시도하지 않습니다. `EINTR`처럼 재시도하기로 정한 오류만 다시 호출합니다.

## 바이트 수와 문자열 길이 구분하기

`read`가 반환하는 데이터는 C 문자열이라는 보장이 없습니다.

```c
char buffer[128];
ssize_t count = read(fd, buffer, sizeof buffer);
```

`count`가 양수여도 마지막에 `\0`이 없을 수 있고 데이터 중간에 NUL 바이트가 있을 수 있습니다. 바이트 데이터는 반환 길이를 기준으로 처리합니다.

문자열로 사용할 경우 NUL을 쓸 공간을 따로 남깁니다.

```c
char buffer[129];
ssize_t count = read(fd, buffer, sizeof buffer - 1);
if (count > 0) {
    buffer[count] = '\0';
}
```

## 레코드와 `read` 호출은 일치하지 않습니다

newline으로 끝나는 레코드를 읽는다고 가정합니다.

```text
첫 read:   "alpha\nbe"
둘째 read: "ta\ngamma"
```

한 번의 `read`에 레코드 여러 개가 들어올 수도 있고, 한 레코드가 여러 번의 `read`에 나뉠 수도 있습니다. 다음 호출까지 남은 바이트를 보관해야 합니다.

```c
struct record_reader {
    int fd;
    char *pending;
    size_t length;
    size_t capacity;
    int eof;
    int failed;
};
```

## 상태를 보관하는 읽기 객체의 처리 순서

```text
남은 입력 버퍼에서 delimiter 검색
→ 있으면 한 레코드 반환
→ 없고 EOF이면 마지막 레코드 반환 또는 0 반환
→ 아직 EOF가 아니면 read
→ 읽은 바이트를 pending에 추가
→ 다시 delimiter 검색
```

전역 정적 버퍼 하나를 사용하면 서로 다른 파일 디스크립터의 상태가 섞일 수 있습니다. 읽기 객체마다 별도 남은 입력 버퍼를 둡니다.

## 빈 레코드와 마지막 조각

입력:

```text
alpha\n\nbeta
```

레코드:

```text
"alpha"
""
"beta"
```

연속 newline은 빈 레코드를 만듭니다. 마지막 `beta`는 newline이 없어도 EOF에서 반환할지 정해야 합니다. 빈 파일이나 마지막이 newline으로 끝난 파일에서 추가 빈 레코드를 만들지 여부도 명시합니다.

## 출력 메모리 소유권

읽기 객체가 새 레코드를 할당해 반환한다면 호출자가 해제한다는 규칙을 적습니다.

```c
char *record;
size_t length;
int result = record_reader_next(&reader, &record, &length);

if (result == 1) {
    consume(record, length);
    free(record);
}
```

`0`이나 `-1`에서 출력 매개변수를 변경하지 않으면 호출자가 성공과 실패를 분명히 구분할 수 있습니다.

## 실패 후 상태

내부 남은 입력 버퍼를 늘리는 할당이 실패한 뒤 재시도할지, 읽기 객체를 실패 상태로 고정할지 정해야 합니다.

단순한 구현에서는 복구하지 않는 실패가 명확합니다.

```text
failed == 1이면 이후 호출도 -1
```

불완전하게 읽은 입력을 정상 상태처럼 계속 노출하지 않습니다. 정리 함수는 남은 내부 버퍼를 해제해야 합니다.

## 파일 디스크립터 소유자

```text
빌린 FD:
  호출자가 열어 둠
  읽기 객체는 read만 수행
  destroy는 fd를 닫지 않음

소유한 FD:
  읽기 객체가 열거나 소유권을 넘겨받음
  destroy가 close
```

두 방식을 섞으면 이중 `close`나 누수가 발생합니다.

## Blocking과 non-blocking

blocking FD에서는 데이터가 올 때까지 `read`가 기다릴 수 있습니다. non-blocking FD에서는 현재 읽을 데이터가 없을 때 `EAGAIN` 또는 `EWOULDBLOCK`을 반환할 수 있습니다.

non-blocking 파일 디스크립터를 읽는 객체는 다음 호출 시점, 입출력 가능 알림과 버퍼 상한까지 별도로 정해야 합니다. 단순한 blocking 파일 디스크립터를 읽는 객체와 같은 오류 처리로 묶지 않습니다.

## 테스트할 내용

- 한 번의 `read`보다 긴 레코드
- 한 청크에 여러 레코드
- 연속 newline
- newline 없는 마지막 레코드
- 빈 입력과 반복 EOF
- embedded NUL
- 두 읽기 객체를 번갈아 호출하는 경우
- 내부 할당 실패
- destroy 뒤 빌린 FD가 열려 있는지

## 완료 기준

1. `read`의 짧은 반환과 EOF를 구분합니다.
2. `write`가 남긴 바이트를 반복해서 씁니다.
3. `EINTR`만 선택적으로 재시도합니다.
4. 논리 레코드와 시스템 호출 한 번을 구분합니다.
5. 호출 사이에 남길 바이트를 읽기 객체에 저장합니다.
6. 파일 디스크립터와 반환 레코드의 소유자를 설명합니다.
