# Notes Stack

Nginx, PHP-FPM, MariaDB를 각각 별도 컨테이너로 실행하는 작은 메모 서비스입니다. 외부 요청은 Nginx의 HTTPS 포트로만 받고, PHP-FPM과 MariaDB는 Compose 내부 네트워크에서만 통신합니다. 데이터베이스 파일은 이름 있는 볼륨에 저장하므로 무상태 컨테이너를 교체해도 사용자 데이터가 남습니다.

이 프로젝트는 특정 설정 파일을 따라 쓰는 예제가 아닙니다. 서버 프로세스, 내부 통신, 데이터 보존, 시작 순서와 실패 처리를 한 번에 다시 설계할 수 있는지 확인하는 통합 실습입니다.

## 제공 기능

- `GET /api/notes`: 저장된 메모 목록을 반환합니다.
- `POST /api/notes`: 1~500바이트의 메모를 추가합니다.
- `GET /health`: PHP-FPM에서 MariaDB 읽기까지 확인합니다.
- `GET /healthz`: Nginx 자체의 HTTPS 응답만 확인합니다.
- `GET /static.txt`: PHP-FPM을 거치지 않고 Nginx가 직접 응답합니다.
- 빈 MariaDB 데이터 디렉터리에서만 시스템 테이블과 애플리케이션 계정을 만듭니다.
- 애플리케이션 시작 시 필요한 테이블과 최초 메모를 중복 없이 준비합니다.
- 실제 비밀번호는 Git에 넣지 않고 Compose 비밀값으로 주입합니다.
- 논리 백업을 임시 파일에 완성한 뒤 최종 파일로 교체합니다.
- 잘못된 DB 호스트, 비밀번호, 비밀값 경로, FastCGI 포트와 상태 검사를 각각 재현합니다.

## 구성

```text
HTTPS 클라이언트
     │
     ▼
Nginx 게이트웨이 :443
     │ FastCGI
     ▼
PHP-FPM 애플리케이션 :9000
     │ MariaDB 프로토콜
     ▼
MariaDB 데이터베이스 :3306
     │
     ▼
이름 있는 볼륨: db-data
```

### `gateway`

Nginx가 TLS 연결과 HTTP 요청을 받습니다. `/static.txt`와 `/healthz`는 직접 처리하고, 나머지 요청은 `app:9000`으로 FastCGI 요청을 보냅니다. 개발용 인증서가 없으면 컨테이너 시작 시 자체 서명 인증서를 만듭니다.

### `app`

시작 스크립트가 주입된 DB 비밀번호를 `/run/app-secrets`의 tmpfs 파일로 복사합니다. PHP-FPM 워커는 이 복사본을 읽을 수 있지만 수정할 수 없습니다. `bootstrap.php`가 DB 연결, 테이블 생성과 최초 데이터 입력을 마친 뒤에만 PHP-FPM을 PID 1로 실행합니다.

### `db`

`/var/lib/mysql/mysql`이 없을 때만 데이터 디렉터리를 초기화합니다. 초기 설정 중에는 TCP를 끈 임시 MariaDB를 Unix 소켓으로 실행해 관리자 비밀번호, 애플리케이션 DB와 사용자를 만듭니다. 설정이 끝나면 임시 서버를 정상 종료하고 최종 `mariadbd`를 PID 1로 실행합니다.

### 저장 상태

- 애플리케이션 코드와 기본 설정은 이미지에 들어갑니다.
- 실제 비밀번호 파일과 백업은 Git에서 제외합니다.
- MariaDB 파일은 `db-data` 볼륨에 저장합니다.
- `/run/app-secrets`는 tmpfs이므로 `app` 컨테이너가 사라지면 함께 사라집니다.

## 실행

필요한 비밀번호 파일을 예시 파일에서 만듭니다.

```sh
./prepare-secrets.sh
```

서비스를 빌드하고 시작합니다.

```sh
docker compose up -d --build
```

상태와 로그를 확인합니다.

```sh
docker compose ps
docker compose logs -f gateway app db
```

요청 예:

```sh
curl -kfsS https://127.0.0.1:19443/health
curl -kfsS https://127.0.0.1:19443/api/notes
curl -kfsS \
  -H 'Content-Type: application/json' \
  -d '{"body":"new note"}' \
  https://127.0.0.1:19443/api/notes
```

포함된 인증서는 로컬 실행을 위한 자체 서명 인증서입니다. `curl -k`는 인증서 검증을 끄므로 공개 서비스의 TLS 검증에 사용하면 안 됩니다.

종료할 때 볼륨을 남기려면 다음 명령을 사용합니다.

```sh
docker compose down
```

DB 볼륨까지 삭제하려면 명시적으로 `-v`를 붙입니다. 이 명령은 사용자 데이터를 제거합니다.

```sh
docker compose down -v
```

## 백업과 복원

현재 `appdb`의 일관된 논리 백업을 만듭니다.

```sh
./backup.sh
```

기본 결과는 `backups/appdb.sql`입니다. `mariadb-dump --single-transaction`이 성공한 뒤에만 임시 파일을 최종 경로로 바꾸므로 실패한 덤프가 기존 백업을 덮어쓰지 않습니다.

지정한 SQL 파일을 현재 `appdb`에 적용합니다.

```sh
./restore.sh backups/appdb.sql
```

`restore.sh`는 기존 데이터를 자동으로 지우지 않습니다. 복구 훈련에서는 별도의 빈 DB를 준비하고, 복원 후 테이블·행과 실제 API를 확인해야 합니다.

## 검사

Docker 없이 셸, PHP와 YAML 문법을 검사합니다.

```sh
./tests/static.sh
```

Docker가 있는 환경에서는 시작, 재시작, 컨테이너 교체, 백업과 복원을 검사합니다.

```sh
./tests/integration.sh
```

오류를 한 가지씩 주입해 예상한 증상이 나타나는지 확인합니다.

```sh
./tests/fault-injection.sh all
```

개별 시나리오도 실행할 수 있습니다.

```sh
./tests/fault-injection.sh wrong-db-host
./tests/fault-injection.sh wrong-db-password
./tests/fault-injection.sh missing-secret
./tests/fault-injection.sh wrong-fcgi-port
./tests/fault-injection.sh broken-healthcheck
./tests/fault-injection.sh data-loss
```

## 주요 설계 선택

### 최초 데이터 마커와 메모를 같은 트랜잭션에서 처리합니다

테이블에 `IF NOT EXISTS`를 사용해도 최초 메모 삽입은 별도로 중복될 수 있습니다. `app_meta.seed_v1`을 실제로 추가한 트랜잭션만 최초 메모를 넣습니다. 메모 삽입이 실패하면 마커도 롤백되므로 다음 시작에서 다시 시도할 수 있습니다.

### MariaDB 초기 설정 중에는 TCP를 열지 않습니다

관리자 비밀번호와 애플리케이션 계정이 준비되기 전에는 `--skip-networking`으로 외부 연결을 받지 않습니다. 초기 SQL은 같은 컨테이너의 Unix 소켓으로만 실행합니다.

### Nginx만 호스트 포트를 공개합니다

PHP-FPM과 MariaDB는 `app-net` 안에서 각각 `app:9000`, `db:3306`으로 접근합니다. 외부 클라이언트가 직접 연결할 이유가 없는 포트는 호스트에 공개하지 않습니다.

### 상태 검사와 사용자 기능 검사를 구분합니다

Nginx의 `/healthz`는 게이트웨이 자체만 확인합니다. `/health`는 PHP-FPM과 DB 읽기까지 확인합니다. 게이트웨이 상태 검사가 성공해도 잘못된 FastCGI 포트 때문에 사용자 요청이 502가 될 수 있습니다.

## Implementation Order

아래 순서는 파일 배치 순서가 아니라, 완성된 프로젝트를 처음부터 구성할 때 필요한 개발 순서입니다. 표의 영문 설명은 소스 주석과 정확히 일치합니다.

| Order | Responsibility | Primary anchor |
| ---: | --- | --- |
| 1 | MariaDB runtime settings | `db/50-server.cnf` |
| 2 | Validate secret sources and SQL identifiers | `db/docker-entrypoint.sh` |
| 2-1 | Initialize an empty MariaDB data directory | `db/docker-entrypoint.sh` |
| 2-2 | Start a socket-only bootstrap server and wait for it | `db/docker-entrypoint.sh` |
| 2-3 | Create accounts, stop bootstrap server, and exec the final server | `db/docker-entrypoint.sh` |
| 3 | Assemble the MariaDB runtime image | `db/Dockerfile` |
| 4 | Validate bootstrap settings and the secret file | `app/bin/bootstrap.php` |
| 4-1 | Retry the PDO connection within a fixed limit | `app/bin/bootstrap.php` |
| 4-2 | Create the application tables when absent | `app/bin/bootstrap.php` |
| 4-3 | Insert the seed marker and note in one transaction | `app/bin/bootstrap.php` |
| 5 | Copy the injected secret to a worker-readable tmpfs file | `app/docker-entrypoint.sh` |
| 5-1 | Run bootstrap before replacing the shell with PHP-FPM | `app/docker-entrypoint.sh` |
| 6 | Reuse one PDO connection in each PHP-FPM worker | `app/public/index.php` |
| 6-1 | Route note requests and validate request bodies | `app/public/index.php` |
| 7 | Assemble the PHP-FPM application image | `app/Dockerfile` |
| 8 | Create missing local TLS files | `gateway/docker-entrypoint.sh` |
| 8-1 | Serve static content and forward application requests to FastCGI | `gateway/default.conf.template` |
| 8-2 | Assemble the Nginx gateway image | `gateway/Dockerfile` |
| 9 | Define the database, application, and gateway services | `compose.yaml` |
| 9-1 | Wait for healthy dependencies before starting downstream services | `compose.yaml` |
| 9-2 | Isolate internal traffic and persist database files | `compose.yaml` |
| 10 | Write a consistent logical backup and publish it by rename | `backup.sh` |
| 10-1 | Restore the selected SQL backup into appdb | `restore.sh` |
| 11 | Create fixed rows and compare EXPLAIN before and after indexing | `sql/index-demo.sql` |
| 12 | Verify restart, recreation, backup, and restore end to end | `tests/integration.sh` |
| 12-1 | Inject one fault at a time and check its expected symptom | `tests/fault-injection.sh` |
| 12-2 | Check source and configuration syntax without Docker | `tests/static.sh` |

## 범위와 제한

- 한 호스트에서 실행하는 Docker Compose 구성을 다룹니다.
- 개발용 인증서만 만들며 공인 인증서 발급과 자동 갱신은 포함하지 않습니다.
- 백업을 다른 호스트나 객체 저장소로 전송하지 않습니다.
- 백업 암호화, 보존 기간과 자동 실행은 포함하지 않습니다.
- 일반적인 마이그레이션 도구는 포함하지 않습니다. 현재 `bootstrap.php`는 최초 테이블을 추가하는 범위만 다룹니다.
- PHP-FPM 워커가 만든 PDO 연결이 실행 중 DB 재시작으로 끊어졌을 때 자동으로 새 연결을 만드는 기능은 포함하지 않습니다.
