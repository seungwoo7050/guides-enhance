# Unix 텍스트 출력 검사

작은 CLI는 stdout, stderr와 종료 상태가 외부에서 관찰할 수 있는 결과입니다. 셸 도구를 사용하면 이 세 가지를 분리해서 검사하고, 공백·줄바꿈 문자·바이트 차이를 정확히 확인할 수 있습니다.

## stdout, stderr와 종료 상태 저장하기

```sh
set +e
./program arg1 arg2 >"$tmp/out" 2>"$tmp/err"
status=$?
set -e
```

`set -e`를 사용하는 스크립트에서는 실패 상태를 직접 검사하려고 잠시 해제해야 합니다.

```sh
[ "$status" -eq 2 ] || fail "종료 상태: 기대=2 실제=$status"
```

## 예상 출력 만들기

`echo`는 구현마다 escape와 옵션 처리가 다를 수 있으므로 정확한 출력에는 `printf`를 사용합니다.

```sh
printf 'count=2\nsum=7\n' >"$tmp/expected"
diff -u "$tmp/expected" "$tmp/out"
```

여러 줄은 here-document가 읽기 쉽습니다.

```sh
cat >"$tmp/expected" <<'EXPECTED'
count=2
sum=7
EXPECTED
```

delimiter를 작은따옴표로 감싸면 본문의 `$`, backtick과 backslash가 셸에서 확장되지 않습니다.

## 빈 출력 확인

```sh
[ ! -s "$tmp/err" ] || fail '정상 입력이 stderr를 출력했습니다.'
```

파일이 존재하고 크기가 0인지 확인합니다. 오류 시 stdout이 비어 있어야 한다는 규칙도 같은 방식으로 검사합니다.

## 부분 문자열과 정확한 줄

진단 접두어만 확인할 때:

```sh
grep -F '오류:' "$tmp/err" >/dev/null
```

정확히 한 줄이 있는지 확인할 때:

```sh
grep -Fx 'sum=7' "$tmp/out" >/dev/null
```

- `-F`: 정규식이 아니라 고정 문자열로 찾습니다.
- `-x`: 줄 전체가 일치해야 합니다.

프로그램이 보장하는 최소 형식만 검사할지, 전체 문장을 고정할지 정합니다. 사람이 읽는 설명을 자주 고칠 수 있다면 안정적인 접두어나 키/값 형식만 고정하는 편이 낫습니다.

## 공백과 보이지 않는 문자 확인

```sh
sed -n 'l' "$tmp/out"
od -An -tx1 -c "$tmp/out"
```

다음을 찾을 때 유용합니다.

- 마지막 줄바꿈 문자 누락
- 예상하지 않은 carriage return
- 탭과 공백 차이
- NUL 바이트
- UTF-8 바이트 차이

임의 바이트 데이터는 `grep`이나 `%s`만으로 검사하지 않고 길이와 `cmp`를 사용합니다.

```sh
cmp -s "$tmp/expected.bin" "$tmp/out.bin"
```

## 임시 디렉터리 정리

```sh
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
```

고정 파일 이름을 현재 디렉터리에 만들면 동시에 실행한 테스트가 충돌할 수 있습니다. 각 실행마다 별도 임시 디렉터리를 사용합니다.

## 실패 함수

```sh
fail() {
    printf '검사 실패: %s\n' "$1" >&2
    exit 1
}
```

실패 메시지는 어떤 입력과 어떤 값이 달랐는지 알려야 합니다.

## 종료 상태 실행 함수

```sh
run_status() {
    expected=$1
    shift

    set +e
    "$program" "$@" >"$tmp/out" 2>"$tmp/err"
    actual=$?
    set -e

    [ "$actual" -eq "$expected" ] ||
        fail "종료 상태: 기대=$expected 실제=$actual 인자=$*"
}
```

인자에 공백이 있을 수 있으므로 `"$@"`로 전달합니다.

## Timeout

프로세스나 동시성 테스트는 멈춘 프로그램을 검출해야 합니다. 시스템의 `timeout` 명령은 환경마다 없을 수 있으므로 Python `subprocess`를 사용할 수도 있습니다.

```python
subprocess.run(
    [program, *args],
    capture_output=True,
    text=True,
    timeout=5.0,
    check=False,
)
```

timeout 뒤 자식 프로세스까지 남을 수 있다면 새 process group을 만들고 그룹 전체를 종료합니다.

## 순서에 의존하지 않는 검사

동시성이나 시그널 테스트에서 운영체제가 보장하지 않는 순서를 기대하지 않습니다.

예를 들어 서로 다른 표준 시그널의 전달 순서는 고정되지 않을 수 있습니다. 검사 대상이 “최소 한 번 관찰”인지, “정확한 횟수”인지 먼저 정합니다.

텍스트 줄 순서가 의미가 없을 때는 정렬 후 비교할 수 있지만, 실제 프로그램이 순서를 보장해야 하는 경우에는 원래 출력 그대로 비교합니다.

## 알려진 잘못된 구현 검출하기

테스트를 작성한 뒤 다음 질문을 확인합니다.

- 마지막 줄바꿈 문자을 빼도 테스트가 실패합니까?
- stdout과 stderr를 바꿔도 실패합니까?
- 종료 상태를 항상 0으로 반환해도 실패합니까?
- 입력 하나를 무시해도 실패합니까?
- FD를 닫지 않아도 반복 검사에서 실패합니까?
- 결과 순서를 뒤집어도 실패합니까?

테스트 주석은 “이 명령을 실행합니다”보다 “어떤 잘못된 구현을 잡는가”를 설명하는 편이 낫습니다.

## 이식성

다음 도구와 옵션은 플랫폼마다 차이가 있을 수 있습니다.

- `mktemp`
- `timeout`
- `sed -n l`
- `stat`
- `/proc`
- `grep` 확장 옵션

POSIX shell만 요구할지, GNU 도구나 Python을 허용할지 README에 적습니다.

## 완료 기준

1. stdout, stderr와 종료 상태를 따로 저장합니다.
2. `printf`, here-document와 `diff -u`로 정확한 출력을 비교합니다.
3. 빈 출력과 정확한 한 줄을 구분해 검사합니다.
4. 임의 바이트 데이터는 `cmp`와 길이로 확인합니다.
5. 임시 파일을 `trap`으로 정리합니다.
6. timeout과 남은 자식 프로세스를 처리합니다.
7. 운영체제가 보장하지 않는 순서를 테스트에 넣지 않습니다.
8. 테스트가 실제로 잘못된 구현을 검출하는지 확인합니다.
