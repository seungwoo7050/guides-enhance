# Compose, 네트워크와 저장소

웹 서비스는 여러 프로세스로 구성되는 경우가 많습니다. 외부 요청을 받는 게이트웨이, 애플리케이션 코드, 데이터베이스는 실행 방법과 데이터 수명이 서로 다릅니다.

Compose는 이 서비스를 한 파일에 선언하고, 필요한 컨테이너·네트워크·볼륨을 같은 프로젝트 이름 아래 관리합니다. 문법보다 먼저 각 서비스가 어떻게 연결되고 어떤 상태를 저장하는지 이해해야 합니다.

## 1. 서비스를 나누는 기준

프로세스를 컨테이너로 나눌 때는 다음을 확인합니다.

- 독립적으로 시작하거나 교체할 필요가 있습니까?
- 사용하는 프로토콜과 포트가 다릅니까?
- 외부 노출과 실행 권한이 다릅니까?
- 저장하는 데이터의 수명이 다릅니까?
- 장애와 자원 사용을 따로 확인해야 합니까?

모든 프로세스를 기계적으로 하나씩 나누면 설정만 복잡해질 수 있습니다. 반대로 Nginx, PHP-FPM, MariaDB처럼 실행 목적과 데이터 수명이 다른 프로세스를 한 컨테이너에 넣으면 종료·재시작·로그와 권한을 분리하기 어렵습니다.

## 2. Compose가 대신하는 수동 작업

두 컨테이너를 직접 연결하려면 네트워크를 만들고, 이름과 포트를 지정하고, 종료 뒤 자원을 직접 지워야 합니다.

```sh
docker network create app-net

docker run -d \
  --name app \
  --network app-net \
  app-image

docker run --rm \
  --network app-net \
  curlimages/curl:8.10.1 \
  -fsS http://app:8080/healthz
```

Compose는 이 상태를 파일로 기록합니다.

```yaml
services:
  app:
    image: app-image
    networks:
      - app-net

  client:
    image: curlimages/curl:8.10.1
    command: ["-fsS", "http://app:8080/healthz"]
    networks:
      - app-net

networks:
  app-net:
```

Compose 파일은 명령 실행 순서를 적은 셸 스크립트가 아닙니다. 필요한 서비스와 자원을 선언하면 `docker compose up`이 현재 상태와 비교해 필요한 항목을 만듭니다.

## 3. 서비스 이름과 내부 DNS

같은 사용자 정의 네트워크에 연결된 서비스는 서비스 이름으로 서로를 찾을 수 있습니다.

```text
app → db:3306
Nginx → app:9000
```

고정 컨테이너 IP를 설정 파일에 넣지 않습니다.

```text
피할 값: 172.19.0.4
사용할 값: db
```

컨테이너를 다시 만들면 IP가 바뀔 수 있지만 서비스 이름은 Compose 설정에 남습니다.

DNS가 새 IP를 반환하더라도 이미 열린 TCP 연결이 자동으로 새 서버에 연결되지는 않습니다. 애플리케이션은 의존 서비스가 재시작될 때 기존 연결 실패를 처리해야 합니다.

## 4. 내부 포트와 공개 포트

같은 Compose 네트워크의 서비스는 컨테이너 내부 포트로 통신합니다.

```text
app:9000
db:3306
```

호스트나 외부 클라이언트에서 접근해야 할 때만 `ports`로 게시합니다.

```yaml
services:
  gateway:
    ports:
      - "127.0.0.1:19443:443"
```

```text
호스트 127.0.0.1:19443 → gateway 컨테이너 443
```

데이터베이스가 컨테이너 안에서 `0.0.0.0:3306`에 바인드되어 있어도 `ports`가 없으면 호스트에 직접 게시되지 않습니다. 애플리케이션은 내부 네트워크에서 `db:3306`으로 연결합니다.

외부에서 사용할 이유가 없는 포트는 게시하지 않습니다. 개발용 포트도 가능하면 `127.0.0.1`에 묶어 LAN 노출을 피합니다.

## 5. 사용자 정의 브리지 네트워크

사용자 정의 브리지 네트워크는 한 Docker 호스트 안에서 컨테이너끼리 통신할 수 있게 합니다.

```text
Docker 호스트
┌───────────────────────────────────┐
│ app-net                           │
│                                   │
│ gateway ──▶ app:9000 ──▶ db:3306 │
└───────────────────────────────────┘
```

공통 네트워크가 없는 서비스는 해당 서비스 이름으로 직접 연결할 수 없습니다. 필요에 따라 게이트웨이와 애플리케이션, 애플리케이션과 데이터베이스 네트워크를 나눌 수도 있습니다.

Docker 네트워크만으로 완전한 보안이 보장되지는 않습니다. 컨테이너 안의 인증, 호스트 방화벽과 Docker 권한도 별도로 관리해야 합니다.

## 6. 컨테이너의 저장 방식

### 쓰기 가능 계층

마운트하지 않은 컨테이너 내부 경로입니다. 컨테이너를 삭제하면 함께 사라집니다. 캐시나 임시 파일처럼 잃어도 되는 데이터에 적합합니다.

### 이름 있는 볼륨

Docker가 관리하는 영속 저장소입니다.

```yaml
services:
  db:
    volumes:
      - db-data:/var/lib/mysql

volumes:
  db-data:
```

볼륨은 특정 컨테이너보다 오래 유지됩니다. 데이터베이스 컨테이너를 다시 만들어도 같은 볼륨을 연결하면 기존 데이터가 남습니다.

### 호스트 경로 마운트

호스트의 구체적인 경로를 컨테이너에 연결합니다.

```yaml
volumes:
  - type: bind
    source: ./public
    target: /var/www/html
    read_only: true
```

개발 중 파일을 바로 반영하기 쉽지만 호스트 경로와 UID/GID에 종속됩니다.

### tmpfs

메모리에만 유지되는 파일 시스템입니다. 컨테이너가 종료되면 사라져야 하는 런타임 비밀값 복사본이나 임시 파일에 사용할 수 있습니다.

```yaml
tmpfs:
  - /run/app-secrets
```

## 7. `down`과 볼륨 삭제

```sh
docker compose down
```

컨테이너와 기본 네트워크를 제거하지만 이름 있는 볼륨은 보통 남깁니다.

```sh
docker compose down -v
```

이름 있는 볼륨도 제거합니다. 데이터베이스를 초기화할 의도가 있을 때만 사용합니다.

다음 상태를 구분해야 합니다.

| 작업 | 컨테이너 | 이름 있는 볼륨 |
|---|---|---|
| `restart` | 유지 | 유지 |
| `up --force-recreate` | 교체 | 유지 |
| `down` 후 `up` | 새로 생성 | 유지 |
| `down -v` 후 `up` | 새로 생성 | 새 빈 볼륨 |

재배포와 데이터 삭제를 같은 작업으로 취급하면 안 됩니다.

## 8. 설정, 비밀값과 데이터

| 종류 | 예 | 전달 방식 | 일반적인 수명 |
|---|---|---|---|
| 설정 | 포트, 로그 수준, 서비스 주소 | 환경변수, 설정 파일 | 배포와 함께 변경 |
| 비밀값 | DB 비밀번호, 개인키 | 제한된 파일, 외부 비밀값 저장소 | 별도 회전 필요 |
| 데이터 | DB 파일, 사용자 업로드 | 볼륨, 외부 저장소 | 컨테이너보다 오래 유지 |

비밀번호를 Dockerfile의 `ENV`, 소스 코드나 Compose 파일에 직접 쓰지 않습니다. 실제 값 파일은 Git에서 제외하고 `.example` 파일이나 생성 절차만 저장합니다.

Compose의 파일 기반 비밀값은 서비스 안에서 일반적으로 `/run/secrets/<name>`으로 보입니다.

```yaml
services:
  app:
    secrets:
      - db_password
    environment:
      DB_PASSWORD_FILE: /run/secrets/db_password

secrets:
  db_password:
    file: ./secrets/db_password.txt
```

이 방식은 이미지와 일반 환경변수에 평문 값을 넣지 않게 해 줍니다. 원본 호스트 파일의 권한, 접근 기록과 회전까지 자동으로 해결해 주지는 않습니다.

## 9. Compose 변수 보간

Compose는 파일을 읽을 때 호스트 환경이나 `.env`의 값을 사용할 수 있습니다.

```yaml
ports:
  - "127.0.0.1:${TLS_PORT:-19443}:443"
```

- `${VAR}`: 변수 값을 사용합니다.
- `${VAR:-default}`: 값이 없거나 비어 있으면 기본값을 사용합니다.
- `${VAR:?message}`: 값이 없으면 Compose가 실패합니다.

`.env`는 Compose 파일을 렌더링할 때 사용되고, `environment`는 컨테이너 프로세스에 값을 전달합니다.

```sh
docker compose config
docker compose config --quiet
```

렌더링 결과에 비밀값이 포함될 수 있으므로 공유 로그에 그대로 남기지 않습니다.

## 10. 실행 중과 준비 완료

컨테이너가 `running`이라는 것은 PID 1이 종료되지 않았다는 뜻입니다. 서비스가 요청을 처리할 준비가 됐다는 뜻은 아닙니다.

```yaml
healthcheck:
  test: ["CMD", "python", "/app/healthcheck.py"]
  interval: 5s
  timeout: 2s
  retries: 10
  start_period: 5s
```

좋은 상태 검사는 다음 조건을 만족합니다.

- 짧은 시간 안에 끝납니다.
- 제한 시간이 있습니다.
- 반복해도 데이터를 바꾸지 않습니다.
- 서비스가 실제 사용하는 프로토콜을 확인합니다.
- 무엇을 확인하는지 범위가 분명합니다.

프로세스 이름만 확인하면 포트나 프로토콜이 고장 난 상태를 놓칠 수 있습니다. 반대로 상태 검사에 무거운 쿼리나 외부 인터넷 요청을 넣으면 정상 서비스까지 비정상으로 판정할 수 있습니다.

## 11. `depends_on`

짧은 형식은 서비스 시작 순서를 나타냅니다.

```yaml
depends_on:
  - db
```

데이터베이스가 실제로 준비될 때까지 기다리려면 상태 검사와 `service_healthy`를 함께 사용합니다.

```yaml
depends_on:
  db:
    condition: service_healthy
```

이 설정이 해결하지 않는 문제도 있습니다.

- 실행 중 데이터베이스가 재시작된 경우
- 기존 연결이 끊어진 경우
- 잘못된 비밀번호처럼 재시도로 해결되지 않는 설정 오류
- 외부 서비스 장애

시작 순서와 실행 중 복구는 별개입니다. 애플리케이션은 제한된 재시도와 오류 처리를 가져야 합니다.

## 12. 재시작 설정

```yaml
restart: unless-stopped
```

재시작 설정은 일시적인 프로세스 종료에 도움이 될 수 있지만 설정 오류를 수정하지는 않습니다. 잘못된 비밀번호로 즉시 종료하는 컨테이너를 계속 재시작하면 같은 오류가 반복되고 최초 로그를 찾기 어려워집니다.

## 13. 주요 명령

```sh
docker compose config --quiet
docker compose build
docker compose up -d
docker compose ps -a
docker compose logs -f app
docker compose exec app ps -ef
docker compose stop
docker compose down
docker compose down -v
```

`stop`은 컨테이너를 남기고 프로세스만 멈춥니다. `down`은 컨테이너와 기본 네트워크를 제거합니다. `down -v`는 영속 데이터까지 삭제할 수 있습니다.

## 14. 자주 생기는 오해

### 같은 Compose 파일의 서비스는 항상 서로 통신할 수 있습니다

서비스가 공통 네트워크에 연결되어 있어야 합니다. 네트워크를 나누면 공통 네트워크가 없는 서비스는 직접 연결할 수 없습니다.

### `depends_on`이면 데이터베이스 쿼리가 반드시 성공합니다

짧은 형식은 시작 순서만 정합니다. `service_healthy`도 실행 중 재연결까지 처리하지 않습니다.

### `down`은 모든 데이터를 지웁니다

기본 `down`은 이름 있는 볼륨을 보존합니다. `-v`를 지정해야 제거합니다.

### 비밀값 파일을 쓰면 비밀 관리가 끝납니다

이미지와 일반 환경변수에서 값을 분리하는 방법입니다. 호스트 파일의 보호와 회전은 따로 관리해야 합니다.

## 확인 문제

1. `gateway:443`과 `127.0.0.1:19443`은 어느 관점의 주소입니까?
2. 데이터베이스 컨테이너가 바뀌어도 데이터가 남는 이유는 무엇입니까?
3. 서비스 이름을 고정 IP보다 우선해야 하는 이유는 무엇입니까?
4. `running`과 `healthy`는 어떻게 다릅니까?
5. `depends_on`이 실행 중 데이터베이스 재시작을 해결하지 못하는 이유는 무엇입니까?
6. 설정, 비밀값과 사용자 데이터를 같은 방식으로 저장하면 어떤 문제가 생깁니까?

## 참고 문서

- Compose 파일: https://docs.docker.com/reference/compose-file/
- 서비스 정의: https://docs.docker.com/reference/compose-file/services/
- 시작 순서: https://docs.docker.com/compose/how-tos/startup-order/
- Docker 볼륨: https://docs.docker.com/engine/storage/volumes/
- Docker 네트워크: https://docs.docker.com/engine/네트워크/
