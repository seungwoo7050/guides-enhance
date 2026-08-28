# 빌드·링크·테스트

빌드 도구를 사용하는 목적은 Makefile 문법을 외우는 것이 아닙니다. 어떤 소스와 헤더로 어떤 파일을 만들며, 입력이 바뀌었을 때 무엇을 다시 만들어야 하는지 정확히 적는 것이 목적입니다.

## 직접 명령부터 확인하기

```sh
cc -Iinclude -std=c11 -Wall -Wextra -Wpedantic \
    -c src/text.c -o build/text.o
ar rcs build/libtext.a build/text.o
cc -Iinclude app/main.c build/libtext.a -o build/text-report
cc -Iinclude tests/test_text.c build/libtext.a -o build/test-text
./build/test-text
```

각 명령의 입력과 결과를 이해한 뒤 Makefile로 옮깁니다.

## 빌드는 입력과 결과의 관계

```text
src/text.c + include/text.h
    → build/obj/text.o

build/obj/text.o
    → build/libtext.a

app/main.c + include/text.h + build/libtext.a
    → build/text-report
```

헤더가 바뀌면 그 헤더를 포함한 번역 단위를 다시 컴파일해야 합니다. 라이브러리 멤버가 바뀌면 라이브러리와 이를 사용하는 실행 파일을 다시 링크해야 합니다.

## 컴파일 옵션과 링크 옵션

```make
CC ?= cc
CPPFLAGS ?= -Iinclude
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -Werror -O2
LDFLAGS ?=
LDLIBS ?=
```

- `CPPFLAGS`: include 경로와 `-D` 같은 전처리 옵션
- `CFLAGS`: C 문법, 경고와 코드 생성 옵션
- `LDFLAGS`: 링커 동작과 라이브러리 검색 경로
- `LDLIBS`: 링크할 라이브러리

`-pthread`처럼 컴파일과 링크 모두에 영향을 줄 수 있는 옵션은 사용 도구의 문서를 확인하고 양쪽에 전달합니다.

## 기본 규칙

```make
build/obj/text.o: src/text.c include/text.h
	@mkdir -p build/obj
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
```

- `$@`: 현재 대상
- `$<`: 첫 번째 선행 조건
- `$^`: 모든 일반 선행 조건

레시피 앞에는 탭을 사용합니다.

## 패턴 규칙과 헤더 의존성

```make
OBJ_DIR := build/obj
SOURCES := src/owned_string.c
OBJECTS := $(SOURCES:src/%.c=$(OBJ_DIR)/%.o)
DEPFLAGS := -MMD -MP

$(OBJ_DIR)/%.o: src/%.c
	@mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(DEPFLAGS) -c $< -o $@

-include $(OBJECTS:.o=.d)
```

작은 프로젝트에서는 헤더를 직접 prerequisite로 적어도 충분합니다. 파일이 많아지면 의존성 파일을 생성해 실제 `#include` 관계를 반영할 수 있습니다.

## 정적 라이브러리

```make
AR ?= ar
ARFLAGS ?= rcs
LIB := build/libowned_string.a

$(LIB): $(OBJECTS)
	@mkdir -p $(dir $@)
	rm -f $@
	$(AR) $(ARFLAGS) $@ $^
```

기존 아카이브에 새 멤버만 넣으면 소스 목록에서 제거한 오래된 오브젝트가 남을 수 있습니다. 깨끗한 멤버 구성을 보장하려면 새로 만들기 전에 기존 아카이브를 지웁니다.

```sh
ar t build/libowned_string.a
nm build/libowned_string.a
```

## 링크 순서

전통적인 Unix 정적 링크에서는 아직 해결되지 않은 심볼을 기준으로 라이브러리 멤버를 선택하는 경우가 많습니다.

```sh
cc build/main.o build/libtext.a -o build/text-report
```

일반적으로 라이브러리를 그 심볼을 사용하는 오브젝트 뒤에 둡니다.

## 재링크 방지

```sh
make
make
```

두 번째 실행이 아무것도 다시 만들지 않는지 확인합니다. 불필요한 재빌드가 발생하면 target 이름, `.PHONY`, 항상 바뀌는 prerequisite와 무조건 실행되는 레시피를 확인합니다.

## 테스트 target

```make
.PHONY: all test sanitize clean fclean re

all: $(LIB)

test: $(TEST_BIN)
	$(TEST_BIN)
```

테스트 실행 파일도 제품 라이브러리와 같은 공개 헤더와 오브젝트를 사용해 링크합니다.

## Sanitizer target

```make
SANITIZE_FLAGS := -fsanitize=address,undefined -fno-omit-frame-pointer -g

sanitize: CFLAGS += $(SANITIZE_FLAGS)
sanitize: LDFLAGS += $(SANITIZE_FLAGS)
sanitize: fclean $(TEST_BIN)
	$(TEST_BIN)
```

Sanitizer용 오브젝트와 일반 오브젝트를 같은 디렉터리에서 섞지 않는 편이 안전합니다. 먼저 정리하거나 별도 디렉터리를 사용합니다.

ThreadSanitizer는 컴파일러와 실행 환경에 따라 지원되지 않을 수 있습니다. 실행 실패를 성공으로 숨기지 말고 지원 여부와 실패 원인을 기록합니다.

## 정리 target

```make
clean:
	rm -rf build/obj

fclean: clean
	rm -rf build

re: fclean all
```

소스와 테스트 fixture는 지우지 않고 Makefile이 만든 산출물만 정리합니다.

## 테스트는 무엇을 확인해야 하는가

정상 출력만 비교하지 않습니다.

- 잘못된 인자
- 최솟값과 최댓값
- overflow 직전과 발생 조건
- 할당 실패 뒤 상태 보존
- 파일 디스크립터 누수
- 자식 프로세스 종료 상태
- timeout과 교착 상태
- 동시 실행 중 유지해야 하는 값

테스트가 실패했을 때 어떤 잘못된 구현을 잡았는지 알 수 있어야 합니다.

## 독립 실행 확인

```sh
cp -R exercises/owned-string /tmp/owned-string
cd /tmp/owned-string
make
make test
```

부모 저장소의 스크립트, 다른 exercise, 숨겨진 파일에 의존하면 독립 프로젝트가 아닙니다.

## 완료 기준

1. source → object → library/executable 관계를 Makefile에 적습니다.
2. 헤더 변경 시 필요한 오브젝트가 다시 컴파일되게 합니다.
3. 컴파일 옵션과 링크 옵션을 구분합니다.
4. 정적 라이브러리에서 오래된 멤버가 남지 않게 합니다.
5. `make test`, `make sanitize`, `make clean`을 제공합니다.
6. 두 번째 `make`에서 불필요한 재빌드가 없는지 확인합니다.
7. 프로젝트 디렉터리만 복사해도 검사할 수 있게 합니다.
