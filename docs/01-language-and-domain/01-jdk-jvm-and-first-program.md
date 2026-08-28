# JDK·JVM과 첫 프로그램

Java 개발의 첫 단계는 많은 문법을 외우는 것이 아니라 다음 과정을 직접 반복할 수 있는 상태입니다.

```text
소스 작성 → 컴파일 → 실행 → 출력과 종료 상태 확인 → 수정
```

이 문서에서는 편집기의 실행 버튼에 기대지 않고 터미널에서 이 과정을 확인합니다.

## 소스, 바이트코드와 JVM

Java 소스는 `.java` 파일에 작성합니다. `javac`는 소스를 `.class` 바이트코드로 컴파일하고, `java`는 지정한 classpath에서 진입 클래스를 찾아 JVM에서 실행합니다.

```text
Hello.java --javac--> Hello.class --java/JVM--> 실행 결과
```

JDK에는 `javac`, `java`, `jcmd`, `jstack`, `jfr`와 표준 라이브러리가 들어 있습니다. JVM은 바이트코드를 실행하고 메모리, 스레드와 런타임 기능을 관리합니다.

현재 환경은 다음 명령으로 확인합니다.

```sh
java -version
javac -version
mvn -version
```

Maven 출력에는 Maven이 실제로 사용하는 Java 경로가 함께 표시됩니다. `java`와 `javac`는 원하는 버전인데 Maven만 다른 JDK를 사용한다면 `JAVA_HOME`과 `PATH`를 확인합니다.

## 첫 소스 작성

임시 디렉터리에 package 경로와 소스를 만듭니다.

```sh
work_dir=$(mktemp -d)
mkdir -p "$work_dir/src/dev/guides/hello"
```

`$work_dir/src/dev/guides/hello/Hello.java`를 다음과 같이 작성합니다.

```java
package dev.guides.hello;

public final class Hello {
  private Hello() {}

  public static void main(String[] arguments) {
    String name = arguments.length == 0 ? "developer" : arguments[0];
    System.out.println("안녕하세요, " + name + "님.");
  }
}
```

컴파일 결과는 소스와 다른 디렉터리에 둡니다.

```sh
mkdir -p "$work_dir/out"
javac --release 17 \
  -d "$work_dir/out" \
  "$work_dir/src/dev/guides/hello/Hello.java"
```

실행할 때는 파일 경로가 아니라 완전한 클래스 이름을 전달합니다.

```sh
java -cp "$work_dir/out" dev.guides.hello.Hello Seungwoo
```

- `-d`는 컴파일 결과를 저장할 루트를 지정합니다.
- `-cp`는 JVM이 클래스를 찾을 루트를 지정합니다.
- `dev.guides.hello.Hello`는 package 이름을 포함한 클래스 이름입니다.

## 진입점과 명령행 인자

일반 Java 애플리케이션의 진입점은 다음 메서드입니다.

```java
public static void main(String[] arguments)
```

명령행에서 전달한 값은 문자열 배열로 들어옵니다. 인자가 필요한 프로그램이라면 개수와 형식을 먼저 검사합니다.

```java
public static void main(String[] arguments) {
  if (arguments.length == 0) {
    System.err.println("이름이 필요합니다.");
    System.exit(2);
  }
  System.out.println(arguments[0]);
}
```

## `stdout`, `stderr`와 종료 상태

정상 결과는 `stdout`, 오류 메시지는 `stderr`에 기록합니다. 자동화 도구는 출력 문구만 보지 않고 종료 상태도 확인합니다.

```sh
java -cp "$work_dir/out" dev.guides.hello.Hello
printf 'exit=%s\n' "$?"
```

일반적으로 종료 상태 `0`은 성공을 뜻하고, `0`이 아닌 값은 실패를 뜻합니다. 어떤 숫자를 사용할지는 프로그램이 정합니다. 중요한 점은 문서와 테스트에서 같은 의미를 유지하는 것입니다.

[Number Report](../../exercises/number-report/README.md)는 계산 로직을 직접 호출할 수 있는 `run` 메서드와 실제 프로세스 종료를 담당하는 `main`을 분리합니다. 이 방식이면 계산과 출력은 빠르게 테스트하고, 별도 JVM 테스트에서는 종료 상태가 올바르게 전달되는지 확인할 수 있습니다.

## 자주 만나는 실패

Java 프로그램을 실행할 때는 실패 시점을 먼저 구분합니다.

### 컴파일 실패

문법이나 타입이 맞지 않으면 `javac`가 `.class` 파일을 만들지 못합니다. 여러 진단이 이어지더라도 첫 오류부터 고치는 편이 좋습니다. 앞의 오류 때문에 뒤의 오류가 연쇄적으로 생길 수 있습니다.

### 클래스 탐색 실패

컴파일한 클래스가 실행 classpath에 없거나 클래스 이름을 잘못 전달하면 다음 오류를 볼 수 있습니다.

- `ClassNotFoundException`
- `NoClassDefFoundError`
- 진입 클래스를 찾을 수 없다는 메시지

이때는 소스 파일 위치보다 컴파일 결과 디렉터리, package 선언과 실행 클래스 이름을 비교합니다.

### 실행 중 실패

프로그램이 시작된 뒤 입력이나 현재 상태 때문에 예외가 발생할 수 있습니다. 스택 추적에서는 예외가 처음 발생한 사용자 코드 위치와 마지막 `Caused by`를 함께 확인합니다.

## 실행 환경 기록

다른 컴퓨터에서만 문제가 생긴다면 다음 정보를 함께 기록합니다.

- `java -version`
- `javac -version`
- `mvn -version`
- 운영체제와 CPU 종류
- 기본 문자 인코딩과 시간대
- 실제 실행 명령과 classpath

비밀번호, token, 사용자 홈 전체 경로처럼 불필요한 정보는 제거합니다.

## 환경이 맞지 않을 때 확인할 순서

1. `pwd`로 현재 디렉터리를 확인합니다.
2. `command -v java`와 `command -v javac`로 실제 실행 파일을 확인합니다.
3. `java -version`, `javac -version`, `mvn -version`을 비교합니다.
4. `JAVA_HOME`이 JDK 루트를 가리키는지 확인합니다.
5. 터미널에서는 성공하지만 편집기에서만 실패한다면 편집기의 프로젝트 SDK와 classpath 설정을 확인합니다.

원인을 모른 채 사용자 홈의 Maven 저장소나 편집기 설정을 전부 삭제하지 않습니다. 관찰한 차이를 하나씩 줄이는 편이 안전합니다.

## 완료 기준

다음을 문서 없이 다시 수행할 수 있으면 다음 단계로 넘어갑니다.

- package가 있는 소스를 직접 컴파일하고 실행합니다.
- `.java`, `.class`, JDK와 JVM의 역할을 설명합니다.
- classpath와 완전한 클래스 이름을 구분합니다.
- `stdout`, `stderr`와 종료 상태를 따로 확인합니다.
- Java, `javac`와 Maven이 어떤 JDK를 사용하는지 확인합니다.

다음 문서는 [Java 언어 기초](02-java-language-foundations.md)입니다.
