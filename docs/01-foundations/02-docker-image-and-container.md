# Docker 이미지와 컨테이너

이 장에서는 애플리케이션을 이미지로 만들고 컨테이너로 실행할 때 무엇이 고정되고 무엇이 실행 중에 생기는지 구분합니다. Docker 명령을 많이 외우는 것보다 이미지, 컨테이너, 프로세스와 파일 수명을 정확히 이해하는 것이 먼저입니다.

## 1. Docker가 정리해 주는 것

애플리케이션 실행 결과에는 소스 코드 외에도 다음 항목이 영향을 줍니다.

- 운영체제와 CPU 아키텍처
- 언어 런타임과 시스템 라이브러리
- 설치한 패키지
- 설정 파일과 환경변수
- 실행 사용자와 파일 권한
- 시작 명령

Dockerfile은 필요한 파일과 실행 방법을 이미지로 만드는 절차를 기록합니다.

```text
소스 + Dockerfile + 빌드 입력
              ↓
            이미지
              ↓ docker run
           컨테이너
```

Docker를 사용한다고 같은 결과가 자동으로 보장되지는 않습니다. 가변 태그, 빌드 중 외부 다운로드, 고정하지 않은 패키지 저장소는 같은 Dockerfile에서도 다른 이미지를 만들 수 있습니다. 재현성은 입력을 얼마나 명확히 고정했는지에 달려 있습니다.

## 2. 컨테이너는 작은 가상 머신이 아닙니다

가상 머신은 일반적으로 게스트 커널을 포함합니다. Linux 컨테이너는 호스트 커널을 공유하고 프로세스, 네트워크, 마운트와 사용자 관점을 격리합니다.

```text
가상 머신                         컨테이너
┌──────────────┐                 ┌──────────────┐
│ 애플리케이션  │                 │ 애플리케이션  │
│ 라이브러리    │                 │ 라이브러리    │
│ 게스트 OS     │                 │ 이미지 파일   │
│ 게스트 커널   │                 ├──────────────┤
├──────────────┤                 │ 호스트 커널   │
│ 하이퍼바이저  │                 └──────────────┘
└──────────────┘
```

컨테이너 안에서도 결국 호스트 커널 위의 프로세스가 실행됩니다. 이 사실은 PID 1, 시그널, 파일 권한과 네트워크를 이해할 때 중요합니다.

## 3. 이미지와 컨테이너

### 이미지

이미지는 읽기 전용 파일 계층과 실행 설정의 묶음입니다.

- 기본 명령과 entrypoint
- 작업 디렉터리
- 환경변수 기본값
- 실행 사용자
- 애플리케이션 파일과 라이브러리

이미지는 실행 중인 프로세스가 아닙니다.

### 컨테이너

컨테이너는 이미지를 실행한 인스턴스입니다. 이미지의 읽기 전용 계층 위에 컨테이너 전용 쓰기 가능 계층이 생깁니다.

```text
컨테이너 전용 쓰기 계층
──────────────────────
애플리케이션 계층
런타임 계층
기본 이미지 계층
```

같은 이미지로 여러 컨테이너를 만들면 이미지 계층은 공유하지만 프로세스와 쓰기 계층은 서로 다릅니다.

### 컨테이너를 삭제하면

컨테이너의 쓰기 계층도 함께 사라집니다. 마운트하지 않은 경로에 저장한 파일은 새 컨테이너에 남지 않습니다.

- 애플리케이션 코드와 기본 설정: 이미지에 둡니다.
- 잃어도 되는 임시 데이터: 컨테이너 쓰기 계층이나 tmpfs에 둘 수 있습니다.
- 컨테이너를 교체해도 남아야 하는 데이터: 볼륨이나 외부 저장소에 둡니다.
- 로그: 보통 표준 출력과 표준 오류로 보냅니다.

## 4. Dockerfile의 기본 구성

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm
WORKDIR /app
COPY server.py /app/server.py
ENV APP_HOST=0.0.0.0 APP_PORT=8080
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["python", "/app/server.py"]
```

### `FROM`

기본 이미지와 런타임을 선택합니다. 태그는 시간이 지나 다른 이미지 다이제스트를 가리킬 수 있습니다. 같은 바이트를 다시 받아야 한다면 다이제스트 고정을 검토하고, 보안 수정판을 반영할 갱신 절차도 함께 둡니다.

### `RUN`

빌드 중 명령을 실행하고 결과를 이미지에 남깁니다.

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
```

컨테이너 시작 때 실행되는 명령과 구분합니다.

### `COPY`

빌드 입력에 포함된 파일을 이미지에 복사합니다.

```dockerfile
COPY app/ /app/
```

### `WORKDIR`

이후 명령의 기본 작업 디렉터리를 지정합니다.

### `ENV`

실행 시 사용할 기본 환경변수를 지정합니다. 비밀번호를 넣으면 이미지 설정과 검사 결과에 남을 수 있으므로 사용하지 않습니다.

### `USER`

서비스가 관리자 권한을 필요로 하지 않으면 비특권 사용자로 실행합니다. UID와 GID가 볼륨 파일 권한과 맞는지 확인해야 합니다.

### `EXPOSE`

이미지가 어느 포트를 사용할 예정인지 설명하는 메타데이터입니다. 호스트 포트를 실제로 열지는 않습니다.

### `ENTRYPOINT`와 `CMD`

기본 실행 파일과 기본 인자를 정합니다.

```dockerfile
ENTRYPOINT ["python", "/app/server.py"]
CMD ["--verbose"]
```

실제 명령은 `python /app/server.py --verbose`가 됩니다. 실행 시 전달한 인자는 일반적으로 `CMD`를 교체합니다.

## 5. 빌드 입력과 `.dockerignore`

다음 명령의 마지막 `.`은 빌더가 읽을 수 있는 디렉터리 범위입니다.

```sh
docker build -t example .
```

Dockerfile의 `COPY`와 `ADD`는 이 범위 밖의 파일을 읽을 수 없습니다.

`.dockerignore`는 빌더에 전달하지 않을 파일을 정합니다.

```text
.git
.env
*.log
__pycache__
backups
```

효과는 다음과 같습니다.

- 전송할 파일을 줄입니다.
- 무관한 파일 변경 때문에 빌드 캐시가 깨지는 일을 줄입니다.
- 비밀 파일과 로컬 산출물이 이미지에 들어갈 가능성을 낮춥니다.

민감 파일은 가능하면 빌드 입력 밖에 두고, `.dockerignore`만 보안 수단으로 믿지 않습니다.

## 6. 이미지 계층과 캐시

파일을 변경하는 Dockerfile 단계는 대체로 새 계층을 만듭니다. 아래 계층에 추가한 파일을 다음 계층에서 지워도 이미지 전체 바이트가 줄지 않을 수 있습니다.

```dockerfile
RUN apt-get install -y build-essential
RUN apt-get remove -y build-essential
```

임시 파일은 만든 단계에서 함께 지웁니다. 빌드 도구와 실행 파일을 완전히 나누려면 다중 단계 빌드를 사용합니다.

```dockerfile
FROM golang:1.24-bookworm AS build
WORKDIR /src
COPY . .
RUN CGO_ENABLED=0 go build -o /out/app ./cmd/app

FROM scratch
COPY --from=build /out/app /app
ENTRYPOINT ["/app"]
```

캐시를 잘 사용하려면 자주 바뀌지 않는 의존성 파일을 먼저 복사합니다.

```dockerfile
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app/
```

소스만 바뀌면 의존성 설치 결과를 재사용할 수 있습니다.

## 7. Debian 패키지 설치

Debian 계열 이미지에서는 업데이트, 설치와 패키지 목록 제거를 같은 `RUN`에 둡니다.

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*
```

`apt-get update`는 패키지 인덱스를 내려받습니다. 프로그램을 업그레이드하는 명령이 아닙니다. 별도 계층으로 분리하면 오래된 인덱스가 캐시되어 설치가 실패할 수 있습니다.

`--no-install-recommends`는 추천 패키지를 자동으로 설치하지 않습니다. 실제로 필요한 패키지는 명시적으로 추가합니다.

## 8. 배열 형식과 PID 1

다음 배열 형식은 셸을 거치지 않고 프로그램을 직접 실행합니다.

```dockerfile
ENTRYPOINT ["python", "/app/server.py"]
```

셸 형식은 `/bin/sh -c`가 먼저 실행될 수 있습니다.

```dockerfile
ENTRYPOINT python /app/server.py
```

```text
PID 1: /bin/sh -c python /app/server.py
└─ 실제 서버
```

셸이 시그널을 전달하지 않으면 `docker stop`의 SIGTERM이 서버에 도달하지 않을 수 있습니다. 특별한 이유가 없다면 `ENTRYPOINT`와 `CMD`는 배열 형식을 사용합니다.

시작 스크립트가 필요하다면 마지막에 서버를 `exec`합니다.

```sh
#!/bin/sh
set -eu

# 시작 준비 작업
exec "$@"
```

`exec`는 셸을 최종 서버로 교체합니다. 서버가 PID 1이 되어 종료 신호와 종료 상태를 직접 처리합니다.

잘못된 예는 주 서버를 백그라운드로 보내고 시작 스크립트가 끝나는 경우입니다.

```sh
python /app/server.py &
exit 0
```

PID 1이 끝났으므로 서버 자식 프로세스가 잠시 남더라도 컨테이너는 종료됩니다.

## 9. 포트 게시

컨테이너 안에서 서버가 `0.0.0.0:8080`에 바인드해도 호스트에 자동으로 공개되지 않습니다.

```sh
docker run -p 127.0.0.1:18080:8080 image
```

```text
호스트 127.0.0.1:18080 → 컨테이너 8080
```

호스트와 컨테이너는 서로 다른 네트워크 네임스페이스를 사용합니다. `EXPOSE 8080`만으로는 포트가 게시되지 않습니다.

## 10. 비특권 실행과 파일 권한

서비스가 80번이나 443번 같은 낮은 포트를 컨테이너 안에서 직접 열 필요가 없다면 비특권 사용자로 실행하기 쉽습니다. 게이트웨이가 높은 내부 포트를 사용하고 호스트 포트 전달을 활용할 수도 있습니다.

이미지를 비특권 사용자로 실행할 때는 다음을 확인합니다.

- 코드와 설정 파일을 읽을 수 있습니다.
- 필요한 쓰기 디렉터리만 쓸 수 있습니다.
- 볼륨의 UID/GID가 실행 사용자와 맞습니다.
- 시작 시 관리자 권한으로 준비한 뒤 권한을 낮추는 경우 최종 서버가 관리자로 남지 않습니다.

전체 디렉터리에 무조건 `chmod -R 777`을 사용하지 않습니다. 실제로 쓰기가 필요한 경로와 사용자를 확인합니다.

## 11. 기본 진단 명령

```sh
docker image ls
docker image inspect image-name
docker image history image-name

docker ps -a
docker inspect container-name
docker logs container-name
docker exec container-name ps -ef
```

`docker exec`으로 설치하거나 수정한 내용은 현재 컨테이너의 쓰기 계층에만 남습니다. 영구 변경은 Dockerfile과 빌드 입력에 반영합니다.

```sh
docker stop container-name
docker kill container-name
```

`stop`은 SIGTERM을 보낸 뒤 유예 시간이 지나면 SIGKILL을 사용합니다. `kill`은 기본적으로 즉시 SIGKILL을 보냅니다.

## 12. 자주 생기는 오해

### 이미지를 실행하면 이미지가 바뀝니다

컨테이너의 쓰기 계층이 바뀝니다. 원본 이미지는 바뀌지 않습니다.

### `EXPOSE`가 방화벽을 열어 줍니다

`EXPOSE`는 설명용 메타데이터입니다. 실제 게시에는 `-p`나 Compose의 `ports`가 필요합니다.

### 컨테이너 안에서 패키지를 설치하면 수정이 완료됩니다

현재 컨테이너에만 남는 변경입니다. 새 컨테이너에서도 필요하면 Dockerfile을 수정해야 합니다.

### `latest`는 항상 최신 안전 버전을 뜻합니다

특별한 규칙이 있는 값이 아니라 단순한 태그 이름입니다. 언제든 다른 다이제스트를 가리킬 수 있습니다.

## 확인 문제

1. 이미지와 컨테이너는 각각 어떤 상태를 가집니까?
2. 컨테이너를 삭제했을 때 마운트하지 않은 파일이 사라지는 이유는 무엇입니까?
3. 시작 스크립트 마지막에 `exec "$@"`를 사용하는 이유는 무엇입니까?
4. `EXPOSE 8080`과 `-p 18080:8080`은 어떻게 다릅니까?
5. Dockerfile에서 의존성 파일을 소스보다 먼저 복사하면 어떤 캐시 효과가 있습니까?
6. 비특권 사용자로 실행할 때 볼륨 권한을 따로 확인해야 하는 이유는 무엇입니까?

## 참고 문서

- Dockerfile reference: https://docs.docker.com/reference/dockerfile/
- Build best practices: https://docs.docker.com/build/building/best-practices/
- `docker run`: https://docs.docker.com/reference/cli/docker/컨테이너/run/
- Multi-stage builds: https://docs.docker.com/build/building/multi-stage/
