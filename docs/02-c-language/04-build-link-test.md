# 빌드·링크·테스트

빌드 도구를 사용하는 목적은 Makefile 문법을 외우는 것이 아닙니다. 핵심은 **어떤 입력으로 어떤 산출물을 만들고, 입력이 바뀌었을 때 어떤 산출물을 다시 만들어야 하는지**를 정확하게 표현하는 것입니다.

C 프로젝트에서는 보통 다음 관계를 관리합니다.

```text
소스 파일(.c) + 포함한 헤더(.h)
  → 오브젝트 파일(.o)

오브젝트 파일(.o)
  → 정적 라이브러리(.a)

오브젝트 파일(.o) + 라이브러리
  → 실행 파일

테스트 소스 + 제품 코드/라이브러리
  → 테스트 실행 파일
  → 테스트 실행
```

Make 같은 빌드 도구는 이 **입력과 결과의 의존 관계(dependency)** 와 파일 수정 시각을 바탕으로 필요한 작업만 다시 실행합니다.

## 직접 명령부터 확인하기

Makefile을 작성하기 전에 실제로 필요한 명령을 직접 실행해 보는 것이 좋습니다.

예:

```sh
cc -Iinclude -std=c11 -Wall -Wextra -Wpedantic \
    -c src/text.c -o build/text.o

ar rcs build/libtext.a build/text.o

cc -Iinclude app/main.c build/libtext.a \
    -o build/text-report

cc -Iinclude tests/test_text.c build/libtext.a \
    -o build/test-text

./build/test-text
```

각 명령에서 무엇이 입력이고 무엇이 결과인지 구분해야 합니다.

첫 번째 명령:

```text
입력:
  src/text.c
  src/text.c가 #include하는 헤더들

결과:
  build/text.o
```

두 번째 명령:

```text
입력:
  build/text.o

결과:
  build/libtext.a
```

세 번째 명령:

```text
입력:
  app/main.c
  app/main.c가 포함하는 헤더들
  build/libtext.a

결과:
  build/text-report
```

네 번째 명령:

```text
입력:
  tests/test_text.c
  테스트가 포함하는 헤더들
  build/libtext.a

결과:
  build/test-text
```

마지막 명령은 파일을 빌드하는 것이 아니라 만들어진 테스트 프로그램을 **실행**합니다.

직접 명령이 정상적으로 동작하는 것을 확인한 뒤 그 관계를 Makefile 규칙으로 옮기면, Makefile 오류와 컴파일·링크 오류를 구분하기 쉬워집니다.

## 빌드는 입력과 결과의 관계

다음 프로젝트를 생각해 봅니다.

```text
include/text.h
src/text.c
app/main.c
```

의존 관계를 단순화하면 다음과 같습니다.

```text
src/text.c + include/text.h
    → build/obj/text.o

build/obj/text.o
    → build/libtext.a

app/main.c + include/text.h + build/libtext.a
    → build/text-report
```

여기에서 `include/text.h`가 바뀌면 그 헤더를 포함하는 `.c` 파일의 번역 단위 내용도 달라질 수 있습니다.

따라서 해당 헤더를 포함하는 오브젝트 파일을 다시 컴파일해야 합니다.

```text
include/text.h 변경
    ↓
build/obj/text.o 재컴파일
    ↓
build/libtext.a 갱신
    ↓
build/text-report 재링크
```

라이브러리의 오브젝트 멤버가 바뀌면 정적 라이브러리를 다시 만들거나 갱신해야 하고, 그 라이브러리를 링크한 실행 파일도 다시 링크해야 합니다.

중요한 점은 **헤더 자체가 링크 입력은 아니지만 번역 단위의 내용에 영향을 주기 때문에 컴파일 의존성이라는 것**입니다.

## Make가 다시 빌드할지 결정하는 기준

일반적인 파일 target에서 Make는 target과 prerequisite의 수정 시각을 비교합니다.

예:

```make
build/obj/text.o: src/text.c include/text.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -c src/text.c -o build/obj/text.o
```

Make는 대략 다음 경우 레시피를 실행합니다.

```text
1. target 파일 build/obj/text.o가 존재하지 않음
2. prerequisite 중 하나가 target보다 새로움
```

따라서

```text
src/text.c가 text.o보다 새로움
```

또는

```text
include/text.h가 text.o보다 새로움
```

이면 `text.o`를 다시 만듭니다.

반대로 target이 존재하고 모든 prerequisite보다 최신이면 해당 레시피를 실행하지 않습니다.

이 규칙이 증분 빌드(incremental build)의 기본입니다.

## 컴파일 옵션과 링크 옵션

Makefile에서는 옵션의 역할을 구분해 두는 것이 좋습니다.

```make
CC ?= cc

CPPFLAGS ?= -Iinclude
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -Werror -O2

LDFLAGS ?=
LDLIBS ?=
```

각 변수의 일반적인 용도는 다음과 같습니다.

| 변수 | 일반적인 용도 |
| --- | --- |
| `CPPFLAGS` | 전처리 옵션: `-I`, `-D` 등 |
| `CFLAGS` | C 컴파일 옵션: 표준, 경고, 최적화, 디버그 옵션 등 |
| `LDFLAGS` | 링크 단계의 동작과 검색 경로를 제어하는 옵션 |
| `LDLIBS` | 링크할 라이브러리 지정 |

예:

```make
CPPFLAGS += -Iinclude -DDEBUG
CFLAGS += -std=c11 -Wall -Wextra -Wpedantic
LDFLAGS += -Lbuild/lib
LDLIBS += -lm
```

링크 명령은 일반적으로 다음 순서로 작성할 수 있습니다.

```make
$(CC) $(LDFLAGS) object-files libraries $(LDLIBS) -o program
```

실제 프로젝트에서는 도구와 플랫폼에 맞게 조정합니다.

### 컴파일과 링크 모두에 필요한 옵션

일부 옵션은 한 단계에만 넣으면 충분하지 않습니다.

예를 들어 많은 Unix 계열 환경에서

```text
-pthread
```

는 컴파일과 링크 모두에 영향을 줄 수 있습니다.

따라서 사용하는 컴파일러의 문서를 확인해 필요한 단계에 모두 전달해야 합니다.

```make
CFLAGS += -pthread
LDLIBS += -pthread
```

또는 프로젝트 정책에 따라 적절한 변수에 둘 수 있습니다.

핵심은 변수 이름 자체보다 **실제로 어느 명령 단계에 옵션이 전달되는가**입니다.

## 기본 규칙

다음 규칙은 하나의 소스 파일을 하나의 오브젝트 파일로 컴파일합니다.

```make
build/obj/text.o: src/text.c include/text.h
	@mkdir -p build/obj
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
```

여기에서 자동 변수의 의미는 다음과 같습니다.

- `$@`: 현재 target 이름
- `$<`: 첫 번째 일반 prerequisite
- `$^`: 중복을 제거한 모든 일반 prerequisite

위 규칙에서는

```text
$@  → build/obj/text.o
$<  → src/text.c
$^  → src/text.c include/text.h
```

입니다.

따라서 실제 컴파일 명령은 다음과 같은 의미가 됩니다.

```sh
cc ... -c src/text.c -o build/obj/text.o
```

Make의 전통적인 recipe 문법에서는 명령 앞에 **탭(tab)** 을 사용합니다.

```make
target: prerequisites
<TAB>command
```

공백 여러 개와 탭은 같은 의미가 아니므로 주의해야 합니다.

## 디렉터리 생성과 order-only prerequisite

오브젝트 디렉터리가 없으면 컴파일 전에 만들어야 합니다.

단순한 방법은 각 recipe에서 다음을 실행하는 것입니다.

```make
@mkdir -p $(dir $@)
```

예:

```make
build/obj/text.o: src/text.c
	@mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
```

프로젝트가 커지면 디렉터리를 별도 target으로 만들 수도 있습니다.

```make
OBJ_DIR := build/obj

$(OBJ_DIR):
	mkdir -p $@
```

그 뒤 **order-only prerequisite**를 사용할 수 있습니다.

```make
build/obj/text.o: src/text.c | $(OBJ_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
```

`|` 뒤의 prerequisite는 target보다 먼저 존재해야 하지만, 디렉터리의 수정 시각이 바뀌었다는 이유만으로 오브젝트를 다시 만들지는 않게 합니다.

디렉터리는 내부 파일이 생기거나 없어질 때 수정 시각이 자주 바뀔 수 있으므로, 일반 prerequisite로 두면 불필요한 재빌드가 발생할 수 있습니다.

작은 프로젝트에서는 recipe 안의 `mkdir -p`만으로도 충분합니다.

## 패턴 규칙

여러 `.c` 파일에 같은 컴파일 규칙을 적용하려면 패턴 규칙을 사용할 수 있습니다.

```make
OBJ_DIR := build/obj

SOURCES := \
	src/owned_string.c \
	src/text.c

OBJECTS := $(SOURCES:src/%.c=$(OBJ_DIR)/%.o)

$(OBJ_DIR)/%.o: src/%.c
	@mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
```

예를 들어

```text
src/text.c
```

는 패턴에 따라

```text
build/obj/text.o
```

에 대응합니다.

패턴 규칙은 컴파일 명령의 중복을 줄이지만, 헤더 의존성을 별도로 관리해야 합니다.

## 헤더 의존성

다음 규칙만 있다고 가정합니다.

```make
$(OBJ_DIR)/%.o: src/%.c
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
```

이 규칙은 `.c` 파일이 바뀌면 다시 컴파일한다는 사실은 알지만, 그 `.c` 파일이 어떤 헤더를 포함하는지는 Make가 자동으로 알지 못합니다.

예를 들어

```c
#include "text.h"
```

가 있어도 Makefile에 의존 관계가 없으면 `text.h` 변경 후 오브젝트를 다시 만들지 않을 수 있습니다.

작은 프로젝트에서는 직접 적을 수 있습니다.

```make
build/obj/text.o: src/text.c include/text.h
```

파일 수가 많아지면 이런 목록을 사람이 계속 유지하기 어렵습니다.

## 자동 의존성 파일

GCC와 Clang 계열 컴파일러에서는 다음 옵션을 사용해 헤더 의존성 파일을 생성하는 방식을 자주 사용합니다.

```make
DEPFLAGS := -MMD -MP
```

컴파일 규칙:

```make
$(OBJ_DIR)/%.o: src/%.c
	@mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(DEPFLAGS) -c $< -o $@
```

예를 들어

```text
build/obj/text.o
```

를 만들 때 보통 함께

```text
build/obj/text.d
```

같은 의존성 파일이 만들어집니다.

그 파일에는 개념적으로 다음과 같은 관계가 들어갑니다.

```make
build/obj/text.o: src/text.c include/text.h
```

Makefile에서 이를 다시 읽습니다.

```make
-include $(OBJECTS:.o=.d)
```

앞의 `-`는 `.d` 파일이 아직 존재하지 않는 첫 빌드에서도 오류로 중단하지 않도록 합니다.

### `-MMD`

보통 사용자 프로젝트의 헤더 의존성을 `.d` 파일에 기록하도록 합니다. 시스템 헤더까지 모두 의존성에 넣는 것을 피하는 데 유용합니다.

### `-MP`

헤더가 삭제되거나 이름이 바뀌었을 때 오래된 `.d` 파일 때문에 Make가 곧바로

```text
No rule to make target ...
```

형태로 실패하는 문제를 완화하기 위한 가짜 target을 함께 생성합니다.

이 옵션들의 정확한 동작은 사용하는 컴파일러 문서를 확인해야 하지만, GCC/Clang 계열에서는 흔히 사용하는 조합입니다.

## 정적 라이브러리

정적 라이브러리는 보통 여러 오브젝트 파일을 하나의 아카이브로 묶은 파일입니다.

```make
AR ?= ar
ARFLAGS ?= rcs

LIB := build/libowned_string.a
```

예:

```make
$(LIB): $(OBJECTS)
	@mkdir -p $(dir $@)
	rm -f $@
	$(AR) $(ARFLAGS) $@ $^
```

`ar`의 일반적인 역할은 오브젝트 파일을 아카이브에 저장하는 것입니다.

```sh
ar rcs build/libowned_string.a \
    build/obj/owned_string.o \
    build/obj/text.o
```

### 왜 기존 아카이브를 지울 수 있는가

다음 빌드에서 소스 목록에서 `text.o`가 제거되었다고 가정합니다.

예전 라이브러리:

```text
owned_string.o
text.o
```

새로 원하는 라이브러리:

```text
owned_string.o
```

기존 `.a` 파일에 단순히 새 멤버를 갱신하는 방식만 사용하면, 명령에 더 이상 등장하지 않는 오래된 `text.o`가 아카이브 안에 남을 수 있습니다.

따라서 멤버 목록을 소스 목록과 정확히 일치시키고 싶다면 다음처럼 새로 만들기 전에 기존 아카이브를 제거하는 방식이 단순합니다.

```make
rm -f $@
$(AR) $(ARFLAGS) $@ $^
```

프로젝트와 `ar` 사용 방식에 따라 다른 방법도 가능하지만, 중요한 것은 **소스 목록에서 제거된 오브젝트가 라이브러리에 계속 남지 않도록 하는 것**입니다.

## 정적 라이브러리 내용 확인

아카이브 안에 어떤 멤버가 들어 있는지 확인할 수 있습니다.

```sh
ar t build/libowned_string.a
```

예:

```text
owned_string.o
text.o
```

심볼을 확인하려면 다음을 사용할 수 있습니다.

```sh
nm build/libowned_string.a
```

이를 통해 다음을 확인할 수 있습니다.

- 어떤 오브젝트 멤버가 들어 있는가
- 어떤 함수나 전역 객체 심볼이 정의되어 있는가
- 어떤 외부 심볼을 아직 참조하고 있는가

헤더에 함수 선언이 있다는 사실과 실제 정의가 정적 라이브러리 안에 들어 있다는 사실은 서로 다른 문제입니다.

## 링크 규칙

실행 파일은 필요한 오브젝트와 라이브러리를 링크해서 만듭니다.

예:

```make
APP := build/text-report

$(APP): build/obj/main.o $(LIB)
	$(CC) $(LDFLAGS) build/obj/main.o $(LIB) $(LDLIBS) -o $@
```

여기에서

```text
build/obj/main.o
```

나

```text
$(LIB)
```

가 바뀌면 실행 파일을 다시 링크합니다.

중요한 점은 헤더가 직접 실행 파일의 링크 입력은 아니라는 것입니다.

헤더 변경은 먼저 관련 오브젝트의 재컴파일을 일으키고, 바뀐 오브젝트나 라이브러리가 다시 실행 파일의 재링크를 일으키는 식으로 의존 관계가 이어집니다.

## 링크 순서

전통적인 Unix 정적 링크에서는 라이브러리 아카이브를 처리할 때 **현재까지 해결되지 않은 심볼**을 기준으로 필요한 멤버를 선택하는 경우가 많습니다.

따라서 일반적으로 심볼을 사용하는 오브젝트를 먼저 두고, 그 심볼의 정의를 제공하는 정적 라이브러리를 뒤에 둡니다.

```sh
cc build/main.o build/libtext.a \
    -o build/text-report
```

예를 들어 `main.o`가 `text_length`를 참조하고 `libtext.a`가 이를 정의한다면 이 순서가 자연스럽습니다.

반대 순서:

```sh
cc build/libtext.a build/main.o \
    -o build/text-report
```

는 사용하는 링커와 옵션에 따라 필요한 라이브러리 멤버가 선택되지 않아 링크 오류가 발생할 수 있습니다.

따라서 정적 라이브러리는 보통 **그 라이브러리의 심볼을 필요로 하는 오브젝트 뒤에 둔다**고 기억할 수 있습니다.

### 라이브러리끼리 서로 의존하는 경우

정적 라이브러리 A와 B가 서로의 심볼을 필요로 하면 단순한 한 번의 왼쪽→오른쪽 처리로 해결되지 않을 수 있습니다.

이 경우 링커가 제공하는 그룹 옵션이나 라이브러리 순서 조정이 필요할 수 있습니다.

정확한 방법은 사용하는 링커의 문서를 확인해야 합니다.

핵심은 링크 순서가 단순한 미관상의 문제가 아니라 **정적 라이브러리에서 어떤 멤버를 추출할지에 영향을 줄 수 있다**는 점입니다.

## `.PHONY`

다음과 같은 target은 실제 파일을 만드는 목적이 아니라 명령 묶음의 이름으로 사용하는 경우가 많습니다.

```make
all
test
clean
fclean
re
sanitize
```

이런 target은 `.PHONY`로 선언합니다.

```make
.PHONY: all test sanitize clean fclean re
```

예를 들어 프로젝트 디렉터리에 우연히 `clean`이라는 파일이 존재하면, `.PHONY`가 없는 경우 Make가

```text
clean이라는 target 파일이 이미 존재하고 최신이다
```

라고 판단하여 정리 명령을 실행하지 않을 수 있습니다.

`.PHONY`는 해당 이름을 실제 파일 target이 아니라 항상 실행 가능한 논리적 target으로 취급하게 합니다.

따라서 **실제 산출물 파일을 `.PHONY`로 선언하면 안 됩니다.**

예를 들어 다음 파일 target은 보통 phony가 아닙니다.

```text
build/text-report
build/libtext.a
build/obj/text.o
```

이를 phony로 만들면 Make가 매번 다시 만드는 원인이 됩니다.

## 재링크와 재빌드 방지

증분 빌드가 제대로 구성되었는지 확인하려면 연속해서 Make를 실행합니다.

```sh
make
make
```

첫 번째 `make`가 필요한 파일을 모두 만들었다면, 아무 입력도 바뀌지 않은 두 번째 `make`에서는 일반적으로 다시 컴파일하거나 링크할 작업이 없어야 합니다.

예:

```text
첫 번째 make:
  text.c 컴파일
  library 생성
  executable 링크

두 번째 make:
  아무 작업 없음
```

두 번째 실행에서도 계속 다시 빌드한다면 다음을 확인합니다.

- 실제 파일 target을 `.PHONY`로 선언했는가
- target 이름과 recipe가 실제로 만드는 파일 이름이 다른가
- 항상 새로 수정되는 파일을 prerequisite로 두었는가
- recipe가 prerequisite의 timestamp를 계속 바꾸고 있는가
- 디렉터리를 일반 prerequisite로 두어 수정 시각 때문에 계속 재빌드되는가
- `FORCE` 같은 항상 갱신되는 target에 의존하고 있는가

Makefile의 목표는 모든 것을 매번 다시 만드는 것이 아니라 **필요한 것만 다시 만드는 것**입니다.

## 기본 target과 `all`

Make는 명령행에서 target을 지정하지 않으면 기본 목표를 빌드합니다.

보통 다음처럼 `all`을 첫 번째 주요 target으로 둡니다.

```make
.PHONY: all

all: $(LIB) $(APP)
```

이 경우

```sh
make
```

는 보통 `all`을 빌드하고, `all` 자체는 실제 파일을 만들지 않고 필요한 산출물에 의존합니다.

```text
all
 ├─ library
 └─ application
```

## 테스트 target

테스트 실행 파일도 일반 프로그램과 마찬가지로 의존 관계를 가진 산출물입니다.

예:

```make
TEST_BIN := build/test-text

$(TEST_BIN): build/obj/test_text.o $(LIB)
	$(CC) $(LDFLAGS) \
	    build/obj/test_text.o $(LIB) $(LDLIBS) \
	    -o $@
```

실행 target은 다음처럼 둘 수 있습니다.

```make
.PHONY: test

test: $(TEST_BIN)
	$(TEST_BIN)
```

이 구조에서는

```sh
make test
```

가 먼저 테스트 실행 파일을 최신 상태로 만든 뒤 실행합니다.

테스트 실행 파일도 제품 코드가 실제로 사용하는 것과 같은 공개 헤더와 제품 오브젝트 또는 라이브러리를 통해 링크하는 것이 좋습니다.

그렇게 해야 테스트만을 위한 별도 구현을 우연히 검사하는 일을 줄일 수 있습니다.

## 테스트와 빌드 실패를 구분하기

`make test`는 적어도 두 단계에서 실패할 수 있습니다.

```text
1. 테스트 프로그램을 빌드하지 못함
2. 테스트 프로그램은 빌드했지만 실행 결과가 실패함
```

예:

```make
test: $(TEST_BIN)
	$(TEST_BIN)
```

테스트 프로그램이 0이 아닌 종료 상태를 반환하면 일반적인 Make는 recipe 실패로 처리합니다.

테스트 실패를 다음처럼 숨기면 안 됩니다.

```make
test: $(TEST_BIN)
	-$(TEST_BIN)
```

명령 앞의 `-`는 실패를 무시하라는 의미가 될 수 있으므로 실제 테스트 실패가 성공처럼 보일 수 있습니다.

CI나 자동 채점 환경에서는 특히 **실패가 0이 아닌 종료 상태로 전달되도록 유지하는 것**이 중요합니다.

## Sanitizer target

AddressSanitizer와 UndefinedBehaviorSanitizer를 사용할 수 있는 환경에서는 다음과 같은 플래그를 사용할 수 있습니다.

```make
SANITIZE_FLAGS := \
	-fsanitize=address,undefined \
	-fno-omit-frame-pointer \
	-g
```

예:

```make
sanitize: CFLAGS += $(SANITIZE_FLAGS)
sanitize: LDFLAGS += $(SANITIZE_FLAGS)

sanitize: fclean $(TEST_BIN)
	$(TEST_BIN)
```

Sanitizer instrumentation은 컴파일 단계와 링크 단계 모두에 영향을 줄 수 있으므로 필요한 플래그를 양쪽에 전달해야 합니다.

### 일반 오브젝트와 sanitizer 오브젝트

다음 상황을 생각해 봅니다.

```text
일반 build:
  CFLAGS = -O2

sanitize build:
  CFLAGS = -O2 -fsanitize=address,undefined
```

이미 일반 옵션으로 컴파일한 오브젝트가 남아 있는데 Make가 이를 최신이라고 판단하면 sanitizer target에서 일부 파일이 sanitizer 없이 재사용될 수 있습니다.

따라서 다음 중 하나를 선택하는 것이 안전합니다.

```text
1. sanitizer 빌드 전에 기존 산출물을 정리
2. sanitizer 전용 build 디렉터리 사용
```

별도 디렉터리를 사용하면 더 명확합니다.

```text
build/normal/...
build/sanitize/...
```

이렇게 하면 서로 다른 컴파일 옵션으로 만든 오브젝트가 섞이지 않습니다.

## target별 변수와 의존성 주의

다음과 같은 target별 변수 추가는 편리합니다.

```make
sanitize: CFLAGS += $(SANITIZE_FLAGS)
sanitize: LDFLAGS += $(SANITIZE_FLAGS)
```

하지만 Make가 파일의 수정 시각만 보고 최신 여부를 판단하는 일반적인 구성에서는 **컴파일 옵션이 바뀌었다는 사실 자체를 자동으로 파일 의존성으로 추적하지는 않습니다.**

즉, 평소 빌드한 `.o` 파일이 이미 존재한다면 단순히 `CFLAGS` 값만 바꿔도 반드시 재컴파일된다고 가정하면 안 됩니다.

그래서 sanitizer처럼 빌드 성격이 크게 다른 경우에는 다음이 중요합니다.

- 먼저 정리한다.
- 또는 별도 출력 디렉터리를 사용한다.

이 원리는 Debug/Release 빌드에도 동일하게 적용됩니다.

## ThreadSanitizer

ThreadSanitizer는 데이터 경합 같은 동시성 문제를 탐지하는 데 사용할 수 있지만 모든 컴파일러와 실행 환경에서 정상적으로 지원되는 것은 아닙니다.

따라서 실행 환경에서 지원되지 않는다면 단순히 성공으로 처리해서는 안 됩니다.

다음을 구분해 기록해야 합니다.

```text
테스트가 통과함
sanitizer가 실제 오류를 찾음
sanitizer 자체가 환경 문제로 실행되지 못함
```

지원되지 않는 환경이라면 그 사실과 실패 원인을 명확히 남기는 것이 좋습니다.

## 정리 target

빌드 시스템이 만든 산출물만 제거하도록 정리 target을 구성합니다.

```make
.PHONY: clean fclean re

clean:
	rm -rf build/obj

fclean: clean
	rm -rf build

re: fclean all
```

프로젝트 규칙에 따라 `clean`과 `fclean`의 의미는 달라질 수 있지만, 흔히 다음처럼 구분합니다.

```text
clean:
  중간 산출물 제거

fclean:
  중간 산출물 + 최종 산출물 제거

re:
  완전 정리 후 다시 빌드
```

중요한 것은 정리 명령이 다음을 지우지 않아야 한다는 것입니다.

- 소스 코드
- 공개 헤더
- 테스트 소스
- 테스트 fixture
- 프로젝트에 원래 포함된 입력 데이터

즉, **Makefile이 생성한 산출물만 제거한다**는 기준이 안전합니다.

## 테스트는 무엇을 확인해야 하는가

테스트는 정상 입력에서 예상 출력이 나오는지만 확인해서는 부족합니다.

테스트마다 다음 질문에 답할 수 있어야 합니다.

```text
이 테스트는 어떤 잘못된 구현을 잡는가?
```

### 잘못된 인자

예:

```text
NULL 포인터
범위를 벗어난 index
잘못된 옵션 조합
```

함수가 이런 입력을 지원 가능한 오류로 처리하도록 설계되었다면 반환값과 상태를 검사합니다.

### 경계값

예:

```text
빈 입력
원소 1개
최솟값
최댓값
capacity 경계
buffer 마지막 위치
```

일반적인 중간값만 테스트하면 `0`, `1`, 마지막 원소 같은 경계 오류를 놓치기 쉽습니다.

### overflow

예:

```text
overflow 직전 값
overflow가 발생할 조건
```

실제로 거대한 메모리를 할당하지 않고도 allocator 주입이나 크기 계산 함수를 분리하여 검사할 수 있습니다.

### 할당 실패

할당 실패 후 다음을 확인합니다.

```text
기존 포인터가 보존되는가
기존 원소가 보존되는가
size/capacity가 이전 상태인가
누수가 발생하지 않는가
```

### 파일 디스크립터

파일이나 파이프를 사용하는 코드에서는 성공 경로뿐 아니라 오류 경로에서도 descriptor를 닫는지 확인합니다.

```text
open 성공
중간 단계 실패
cleanup 수행
```

같은 경로를 테스트해야 합니다.

### 자식 프로세스 종료 상태

프로세스를 생성하는 코드는 단순히 `wait`가 성공했는지만 보는 것으로 부족할 수 있습니다.

다음을 구분해야 할 수 있습니다.

```text
정상 종료했는가
exit status가 무엇인가
signal로 종료되었는가
```

### timeout과 교착 상태

동시성이나 IPC 테스트는 잘못된 구현이 무한히 멈출 수 있습니다.

따라서 테스트 harness 수준에서 timeout을 두어

```text
정상 완료
명시적 실패
시간 초과
```

를 구분할 수 있어야 합니다.

### 동시 실행

여러 실행 흐름이 같은 상태를 공유한다면 단순히 “프로그램이 종료되었다”만 검사하지 않습니다.

예를 들어 다음을 확인해야 할 수 있습니다.

```text
최종 카운터 값
모든 작업이 정확히 한 번 처리되었는가
중복 또는 누락이 없는가
```

## 테스트 자체도 재현 가능해야 합니다

테스트가 실행될 때마다 무관한 외부 상태에 따라 결과가 달라지면 실패 원인을 찾기 어렵습니다.

가능하면 다음을 통제합니다.

- 테스트 입력 파일
- 임시 디렉터리
- 환경 변수
- 랜덤 seed가 필요한 경우 그 값
- 외부 프로세스의 종료 상태
- timeout

테스트가 임시 파일을 만든다면 성공과 실패 양쪽에서 정리되도록 구성합니다.

## 독립 실행 확인

프로젝트가 상위 저장소의 우연한 환경에 의존하지 않는지 확인하려면 프로젝트 디렉터리만 별도 위치로 복사해서 빌드합니다.

```sh
cp -R exercises/owned-string /tmp/owned-string
cd /tmp/owned-string

make
make test
```

필요하다면 다음도 실행합니다.

```sh
make sanitize
make clean
make
```

이 검사의 목적은 다음과 같은 숨은 의존성을 찾는 것입니다.

- 부모 디렉터리의 헤더
- 부모 저장소의 공용 오브젝트
- 부모 디렉터리에만 존재하는 스크립트
- 개발자 컴퓨터에 우연히 남아 있는 생성 파일
- 다른 exercise의 코드
- 저장소에는 포함되지 않은 테스트 fixture

독립 프로젝트라면 문서화된 도구와 프로젝트 디렉터리의 파일만으로 빌드하고 테스트할 수 있어야 합니다.

## 예시 Makefile

앞의 개념을 작은 프로젝트에 합치면 다음과 같은 형태가 될 수 있습니다.

```make
CC ?= cc
AR ?= ar

CPPFLAGS ?= -Iinclude
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic
LDFLAGS ?=
LDLIBS ?=

ARFLAGS ?= rcs
DEPFLAGS := -MMD -MP

OBJ_DIR := build/obj

LIB := build/libtext.a
APP := build/text-report
TEST_BIN := build/test-text

LIB_SOURCES := src/text.c
LIB_OBJECTS := $(LIB_SOURCES:src/%.c=$(OBJ_DIR)/%.o)

APP_OBJECT := $(OBJ_DIR)/app/main.o
TEST_OBJECT := $(OBJ_DIR)/tests/test_text.o

OBJECTS := $(LIB_OBJECTS) $(APP_OBJECT) $(TEST_OBJECT)
DEPS := $(OBJECTS:.o=.d)

.PHONY: all test clean fclean re

all: $(LIB) $(APP)

$(OBJ_DIR)/%.o: src/%.c
	@mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(DEPFLAGS) -c $< -o $@

$(OBJ_DIR)/app/%.o: app/%.c
	@mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(DEPFLAGS) -c $< -o $@

$(OBJ_DIR)/tests/%.o: tests/%.c
	@mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(DEPFLAGS) -c $< -o $@

$(LIB): $(LIB_OBJECTS)
	@mkdir -p $(dir $@)
	rm -f $@
	$(AR) $(ARFLAGS) $@ $^

$(APP): $(APP_OBJECT) $(LIB)
	$(CC) $(LDFLAGS) $(APP_OBJECT) $(LIB) $(LDLIBS) -o $@

$(TEST_BIN): $(TEST_OBJECT) $(LIB)
	$(CC) $(LDFLAGS) $(TEST_OBJECT) $(LIB) $(LDLIBS) -o $@

test: $(TEST_BIN)
	$(TEST_BIN)

clean:
	rm -rf $(OBJ_DIR)

fclean: clean
	rm -f $(LIB) $(APP) $(TEST_BIN)

re: fclean all

-include $(DEPS)
```

이 예시는 모든 프로젝트의 정답이라기보다 다음 관계를 한곳에 보여 주기 위한 예입니다.

```text
source/header
   ↓
object
   ↓
library
   ↓
application/test binary
   ↓
test execution
```

프로젝트가 커지면 소스 그룹, 빌드 모드, 외부 라이브러리, 생성 파일 등에 따라 구조를 더 나눌 수 있습니다.

## 빌드 파일을 읽을 때 확인할 사항

- 각 target이 실제로 어떤 파일을 만드는가?
- prerequisite가 실제 입력 파일을 모두 표현하는가?
- 헤더 변경이 관련 오브젝트 재컴파일로 이어지는가?
- 오브젝트 변경이 라이브러리 갱신으로 이어지는가?
- 라이브러리 변경이 실행 파일 재링크로 이어지는가?
- `CPPFLAGS`, `CFLAGS`, `LDFLAGS`, `LDLIBS`가 역할에 맞게 사용되는가?
- 정적 라이브러리에서 제거된 소스의 오래된 멤버가 남을 수 있는가?
- 정적 라이브러리의 링크 순서가 의존 관계에 맞는가?
- 실제 파일 target을 실수로 `.PHONY`로 만들지 않았는가?
- 두 번째 `make`에서 아무 입력 변화가 없는데도 다시 빌드되는가?
- 빌드 옵션이 다른 오브젝트를 같은 디렉터리에서 섞고 있지 않은가?
- 테스트 실패가 Make에서 성공처럼 숨겨지지 않는가?
- `clean`이 생성 산출물만 삭제하는가?
- 프로젝트 디렉터리만 복사해도 빌드와 테스트가 가능한가?

## 완료 기준

1. source/header → object → library/executable 관계를 Makefile의 prerequisite로 표현합니다.
2. Make가 target과 prerequisite의 수정 시각을 이용해 재빌드 여부를 결정한다는 점을 설명합니다.
3. 헤더 변경 시 그 헤더를 포함한 번역 단위의 오브젝트가 다시 컴파일되게 합니다.
4. `CPPFLAGS`, `CFLAGS`, `LDFLAGS`, `LDLIBS`의 역할을 구분합니다.
5. `$@`, `$<`, `$^`의 의미를 실제 규칙에서 설명합니다.
6. 패턴 규칙과 자동 `.d` 파일을 사용해 헤더 의존성을 관리할 수 있습니다.
7. 정적 라이브러리에서 소스 목록에서 제거된 오래된 멤버가 남지 않게 합니다.
8. `ar t`와 `nm`으로 정적 라이브러리의 멤버와 심볼을 확인합니다.
9. 정적 라이브러리를 일반적으로 그 심볼을 필요로 하는 오브젝트 뒤에 두는 이유를 설명합니다.
10. 실제 산출물 target과 `.PHONY` target을 구분합니다.
11. 아무 입력도 바뀌지 않은 두 번째 `make`에서 불필요한 재컴파일·재링크가 없는지 확인합니다.
12. `make test`가 테스트 바이너리를 최신 상태로 만든 뒤 실행하도록 구성합니다.
13. 테스트 실패를 무시하지 않고 0이 아닌 종료 상태로 빌드 시스템에 전달합니다.
14. sanitizer 플래그가 필요한 컴파일·링크 단계에 모두 적용되도록 합니다.
15. 일반 빌드와 sanitizer 빌드의 오브젝트가 잘못 섞이지 않게 합니다.
16. `make clean`, `make fclean`, `make re`의 정리 범위를 명확히 합니다.
17. 테스트가 정상 경로뿐 아니라 잘못된 인자, 경계값, overflow, 할당 실패, descriptor 정리, 프로세스 상태, timeout, 동시성 불변식까지 필요한 범위에서 검증합니다.
18. 프로젝트 디렉터리만 별도 위치로 복사해도 `make`와 `make test`를 실행할 수 있게 합니다.
