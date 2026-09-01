# Notes Stack

Nginx, PHP-FPM, MariaDB를 각각 별도 컨테이너로 실행하는 작은 메모 서비스입니다. 외부 요청은 Nginx의 HTTPS 포트로만 받고, PHP-FPM과 MariaDB는 Docker Compose의 내부 네트워크에서만 통신합니다. MariaDB의 데이터 파일은 이름 있는 볼륨에 저장하므로 `app`, `gateway`, `db` 컨테이너를 다시 만들더라도 볼륨을 삭제하지 않는 한 사용자 데이터가 유지됩니다.

이 프로젝트의 목적은 특정 설정 파일을 그대로 따라 쓰는 것이 아닙니다. 다음 항목이 서로 어떻게 연결되는지 직접 확인하는 통합 실습입니다.

- 외부 HTTPS 요청을 어디서 받고 TLS를 어디서 종료하는가
- Nginx가 PHP 요청을 어떤 프로토콜로 PHP-FPM에 전달하는가
- 애플리케이션이 MariaDB가 준비될 때까지 어떻게 기다리고 초기화하는가
- 컨테이너와 데이터의 수명을 어떻게 분리하는가
- 시작 스크립트를 여러 번 실행해도 왜 데이터가 중복되지 않는가
- 상태 검사와 실제 사용자 기능 검사는 무엇을 각각 확인하는가
- 장애가 발생했을 때 DNS, TCP, TLS, FastCGI, DB 인증을 어떻게 나누어 검사하는가
- 백업 파일이 실제 복구 수단인지 어떻게 확인하는가

전체 요청 경로는 다음과 같습니다.

```text
HTTPS 클라이언트
     │ HTTPS
     ▼
Nginx gateway :443
     │ FastCGI
     ▼
PHP-FPM app :9000
     │ MariaDB 프로토콜
     ▼
MariaDB db :3306
     │
     ▼
이름 있는 볼륨 db-data
```

여기서 `443`, `9000`, `3306`은 각각 같은 종류의 포트가 아닙니다. Nginx의 443은 HTTPS를 받고, PHP-FPM의 9000은 FastCGI를 받고, MariaDB의 3306은 MariaDB 클라이언트 프로토콜을 받습니다. 따라서 각 서비스를 검사할 때도 해당 서비스가 실제로 사용하는 프로토콜을 사용해야 합니다.

## 제공 기능

| 요청/기능 | 처리 범위 | 의미 |
|---|---|---|
| `GET /api/notes` | Nginx → PHP-FPM → MariaDB | 저장된 메모 목록 반환 |
| `POST /api/notes` | Nginx → PHP-FPM → MariaDB | `body`가 1~500바이트인 메모 추가 |
| `GET /health` | Nginx → PHP-FPM → MariaDB 읽기 | 전체 애플리케이션 읽기 경로 확인 |
| `GET /healthz` | Nginx | TLS와 Nginx HTTP 응답 확인 |
| `GET /static.txt` | Nginx | PHP-FPM을 거치지 않는 정적 응답 확인 |

그 밖에 다음 동작을 포함합니다.

- 빈 MariaDB 데이터 디렉터리에서만 시스템 테이블과 애플리케이션 계정을 준비합니다.
- 애플리케이션 시작 시 필요한 테이블과 최초 메모를 반복 실행해도 중복되지 않게 준비합니다.
- 실제 비밀번호는 Git과 이미지에 고정하지 않고 Compose 비밀값으로 주입합니다.
- 논리 백업을 임시 파일에 완전히 만든 뒤 최종 파일로 교체합니다.
- 잘못된 DB 호스트, DB 비밀번호, 비밀값 경로, FastCGI 포트와 healthcheck를 각각 독립적으로 재현합니다.
- 재시작, 컨테이너 재생성, 볼륨 유지와 삭제의 차이를 통합 테스트로 확인합니다.

## 구성 요소

### `gateway`

`gateway`는 Nginx를 실행합니다.

- 호스트에 게시된 HTTPS 연결을 받습니다.
- TLS 핸드셰이크와 인증서 처리를 담당합니다.
- `/static.txt`와 `/healthz`는 직접 응답합니다.
- 애플리케이션 요청은 FastCGI로 `app:9000`에 전달합니다.
- 개발용 TLS 파일이 없으면 시작 스크립트가 자체 서명 인증서를 만듭니다.

Nginx는 PHP 코드를 직접 실행하지 않습니다. `SCRIPT_FILENAME` 같은 FastCGI 파라미터를 만들어 PHP-FPM에 전달하고, PHP-FPM이 실제 PHP 파일을 실행합니다.

### `app`

`app`은 PHP 애플리케이션과 PHP-FPM을 실행합니다.

시작 시 다음 순서를 따릅니다.

```text
주입된 비밀값 확인
→ worker가 읽을 수 있는 tmpfs 위치에 제한된 권한으로 복사
→ bootstrap.php 실행
→ DB 연결 재시도
→ 필요한 테이블 준비
→ 최초 데이터 처리
→ php-fpm을 exec
```

`bootstrap.php`가 실패하면 PHP-FPM까지 진행하지 않아야 합니다. 초기화가 끝나지 않았는데 서버 프로세스만 실행하면 컨테이너는 `running`으로 보이면서 실제 요청은 계속 실패하는 상태가 될 수 있기 때문입니다.

`/run/app-secrets`는 tmpfs이므로 컨테이너가 사라지면 비밀값 복사본도 함께 사라집니다. 반대로 영구 보존해야 하는 데이터는 이 경로에 두면 안 됩니다.

### `db`

`db`는 MariaDB를 실행하며, 컨테이너 수명과 데이터 수명을 분리합니다.

최초 실행 흐름은 다음과 같습니다.

```text
/var/lib/mysql/mysql 존재 여부 확인
→ 빈 데이터 디렉터리라면 시스템 테이블 초기화
→ TCP를 끈 임시 MariaDB 실행
→ Unix 소켓으로 초기 SQL 실행
→ 애플리케이션 DB와 계정 준비
→ 임시 서버 정상 종료
→ 최종 mariadbd를 exec
```

초기 설정 중 `--skip-networking`을 사용하는 이유는 계정과 권한이 준비되기 전에 TCP 연결을 받지 않기 위해서입니다. 초기 SQL은 같은 컨테이너의 Unix 소켓을 통해 실행합니다.

`/var/lib/mysql/mysql`이 존재하면 이미 초기화된 데이터 디렉터리로 판단하고 최초 초기화 블록을 건너뜁니다. 따라서 시작 스크립트는 컨테이너가 시작될 때마다 실행되지만 데이터베이스 전체를 매번 새로 만들지는 않습니다.

## 저장 상태와 수명

| 항목 | 저장 위치 | 컨테이너 재생성 후 | `docker compose down -v` 후 |
|---|---|---|---|
| 애플리케이션 코드 | 이미지 | 이미지에 따라 다시 제공 | 이미지에 남음 |
| 기본 설정 | 이미지/Compose 설정 | 다시 제공 | 다시 제공 가능 |
| 주입 전 비밀번호 파일 | 호스트의 비밀값 파일 | 유지 | 유지 |
| `/run/app-secrets` 복사본 | `app`의 tmpfs | 사라짐 | 사라짐 |
| MariaDB 데이터 | `db-data` 볼륨 | 유지 | 삭제 |
| `backups/appdb.sql` | 호스트 파일 | 유지 | Compose 볼륨과 별개 |

이름 있는 볼륨은 **컨테이너 교체로부터 데이터를 분리**하는 기능입니다. 별도 백업은 아닙니다. 볼륨 자체가 삭제되거나 호스트 저장장치가 손상되면 볼륨의 데이터도 잃을 수 있습니다.

## 실행 전 확인

이 실습은 한 호스트에서 Docker Compose로 실행하는 구성을 전제로 합니다.

실행 전에 최소한 다음을 확인합니다.

- Docker와 `docker compose` 명령을 사용할 수 있습니다.
- 호스트의 `127.0.0.1:19443` 포트를 다른 프로세스가 사용하지 않습니다.
- 비밀값 파일을 만들 수 있는 쓰기 가능한 프로젝트 디렉터리에서 작업합니다.
- 기존 `db-data` 볼륨을 유지할지 새로 시작할지 의도적으로 결정합니다.

특히 이전 실행의 데이터가 필요하다면 문제 해결 과정에서 먼저 `docker compose down -v`를 실행하지 않습니다. `-v`는 단순한 컨테이너 초기화가 아니라 데이터 볼륨 삭제입니다.

## 실행

필요한 비밀번호 파일을 예시 파일에서 준비합니다.

```sh
./prepare-secrets.sh
```

이 단계에서 생성되는 실제 비밀번호 파일은 Git에 커밋하지 않습니다.

서비스를 빌드하고 시작합니다.

```sh
docker compose up -d --build
```

시작 시 의존 관계는 개념적으로 다음과 같습니다.

```text
db 준비
   ↓
app bootstrap 및 PHP-FPM 준비
   ↓
gateway가 app으로 FastCGI 요청 전달
```

Compose의 `depends_on`과 healthcheck는 **시작 시점의 순서와 준비 상태를 조정**하는 데 사용합니다. 실행 중 DB가 다시 시작되거나 네트워크가 일시적으로 끊어지는 상황까지 자동으로 해결하는 기능은 아닙니다.

상태와 로그를 확인합니다.

```sh
docker compose ps
docker compose logs -f gateway app db
```

`docker compose ps`에서 컨테이너가 `running`이라는 사실만으로 전체 서비스가 정상이라고 판단하지 않습니다. `/healthz`, `/health`, 실제 API처럼 서로 다른 범위의 검사를 함께 사용합니다.

## 요청 확인

### Nginx 자체 확인

```sh
curl -kfsS https://127.0.0.1:19443/healthz
```

성공하면 최소한 다음 경로가 동작합니다.

```text
호스트 TCP 연결
→ TLS
→ Nginx
→ HTTP 응답
```

PHP-FPM과 MariaDB까지 정상이라는 뜻은 아닙니다.

### 전체 읽기 경로 확인

```sh
curl -kfsS https://127.0.0.1:19443/health
```

이 요청은 PHP-FPM과 MariaDB 읽기까지 포함합니다. `/healthz`는 성공하지만 `/health`가 실패한다면 Nginx 이후의 FastCGI 또는 DB 경로를 확인합니다.

### 메모 목록 확인

```sh
curl -kfsS https://127.0.0.1:19443/api/notes
```

### 메모 추가

```sh
curl -kfsS \
  -H 'Content-Type: application/json' \
  -d '{"body":"new note"}' \
  https://127.0.0.1:19443/api/notes
```

`POST /api/notes`는 요청의 `body`를 검증합니다. 잘못된 요청과 서버 내부 오류를 같은 문제로 취급하지 말고 HTTP 상태와 애플리케이션 로그를 함께 확인합니다.

## 개발용 TLS 인증서

개발용 TLS 파일이 없으면 `gateway` 시작 시 자체 서명 인증서를 만듭니다. 자체 서명 인증서는 연결을 암호화할 수 있지만 일반 클라이언트의 공개 CA 신뢰 체인에 포함되어 있지 않습니다.

그래서 간단한 로컬 요청 예에서는 다음처럼 `-k`를 사용합니다.

```sh
curl -kfsS https://127.0.0.1:19443/healthz
```

`-k`는 인증서 검증을 끕니다. 즉 이 명령의 성공은 **TLS 연결과 HTTP 응답이 가능했다는 증거**이지, 인증서의 신뢰성·호스트 이름·인증서 체인이 올바르다는 증거는 아닙니다.

개발용 인증서를 신뢰 대상으로 직접 지정해 검증하려면 인증서 경로와 인증서에 포함된 호스트 이름을 맞춰 다음과 같이 확인할 수 있습니다.

```sh
curl --cacert development.crt \
  https://localhost:19443/healthz
```

공개 서비스에서는 자체 서명 인증서 생성 방식 대신 신뢰 가능한 인증서 발급과 갱신 절차가 필요합니다.

## 종료와 데이터 보존

컨테이너와 네트워크를 내리되 DB 볼륨을 유지하려면 다음 명령을 사용합니다.

```sh
docker compose down
```

다시 `docker compose up`을 실행하면 새 컨테이너가 기존 `db-data` 볼륨을 다시 사용할 수 있습니다.

DB 볼륨까지 삭제하려면 명시적으로 `-v`를 붙입니다.

```sh
docker compose down -v
```

이 명령은 사용자 데이터가 저장된 Compose 볼륨을 삭제합니다. 새 빈 DB가 다시 초기화될 수는 있지만, 그것은 삭제된 사용자 데이터의 복구가 아닙니다.

## 백업과 복원

### 논리 백업 만들기

현재 `appdb`의 논리 백업을 만듭니다.

```sh
./backup.sh
```

기본 결과는 다음 파일입니다.

```text
backups/appdb.sql
```

백업 스크립트는 `mariadb-dump --single-transaction`으로 덤프를 임시 파일에 먼저 완성하고, 명령이 성공한 뒤에만 최종 파일명으로 교체합니다.

```text
덤프 시작
→ 임시 파일에 기록
→ 덤프 성공
→ 최종 appdb.sql로 rename
```

이 구조는 실패한 덤프가 기존 정상 백업 파일을 부분적으로 덮어쓰는 위험을 줄입니다. 다만 파일이 존재한다는 사실만으로 복구 가능성이 검증되지는 않습니다.

### 복원

지정한 SQL 파일을 현재 `appdb`에 적용합니다.

```sh
./restore.sh backups/appdb.sql
```

`restore.sh`는 기존 데이터를 자동으로 지우고 빈 데이터베이스를 만드는 도구가 아닙니다. 현재 DB에 SQL을 적용하므로 기존 데이터와 충돌할 수 있습니다.

복구 훈련에서는 별도의 빈 DB를 준비해 다음 순서로 검증합니다.

```text
빈 DB 준비
→ 백업 복원
→ 테이블 확인
→ 기대한 행 확인
→ app 연결
→ 실제 API 요청 확인
```

**복원해 보지 않은 백업은 실제 복구 수단으로 검증된 것이 아닙니다.**

## 검사

### 정적 검사

Docker 없이 셸, PHP와 YAML 등 프로젝트 파일의 정적 검사를 실행합니다.

```sh
./tests/static.sh
```

이 검사는 컨테이너 네트워크나 실제 DB 연결을 실행하지 않습니다. 문법 검사가 성공해도 통합 구성이 정상이라는 뜻은 아닙니다.

### 통합 검사

Docker가 있는 환경에서는 시작, 재시작, 컨테이너 교체, 데이터 유지, 백업과 복원을 함께 검사합니다.

```sh
./tests/integration.sh
```

이 검사의 핵심은 단순히 최초 `up`이 성공하는지가 아니라 **재실행과 상태 변화 이후에도 설계한 불변 조건이 유지되는지** 확인하는 것입니다.

예를 들면 다음과 같습니다.

- 컨테이너를 재시작해도 최초 메모가 중복되지 않습니다.
- `db` 컨테이너를 다시 만들어도 기존 볼륨의 데이터가 남습니다.
- 백업을 만들고 복원한 뒤 기대한 데이터를 읽을 수 있습니다.

### 오류 주입 검사

정상 구성에서 한 가지 조건만 바꾸어 예상한 증상이 발생하는지 확인합니다.

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

각 시나리오는 다음처럼 **실패 지점이 서로 다르다**는 점을 확인하기 위한 것입니다.

| 시나리오 | 예상되는 첫 실패 영역 |
|---|---|
| `wrong-db-host` | 서비스 이름 해석 또는 DB 연결 |
| `wrong-db-password` | DB 인증 |
| `missing-secret` | 애플리케이션 초기 설정 검사 |
| `wrong-fcgi-port` | Nginx → PHP-FPM FastCGI 연결 |
| `broken-healthcheck` | healthcheck 명령 자체 |
| `data-loss` | 볼륨 삭제와 재초기화 뒤 데이터 상태 |

하나의 오류를 관찰할 때 여러 설정을 동시에 수정하지 않습니다. 먼저 어디까지 성공했는지 확인한 뒤 실패 경계의 바로 다음 단계를 검사합니다.

## 주요 설계 선택

### 최초 데이터 마커와 메모를 같은 트랜잭션에서 처리합니다

`CREATE TABLE IF NOT EXISTS`는 테이블 중복 생성을 막는 데 도움을 주지만 최초 데이터 행의 중복 삽입까지 막지는 않습니다.

이 프로젝트는 `app_meta.seed_v1` 같은 고유 마커로 최초 데이터 적용 여부를 기록합니다. 마커를 실제로 획득한 트랜잭션만 최초 메모를 추가합니다.

```text
트랜잭션 시작
→ seed_v1 마커 획득
→ 최초 메모 삽입
→ 둘 다 성공하면 commit
```

메모 삽입이 실패하면 마커도 롤백되므로 다음 시작에서 다시 시도할 수 있습니다. 마커와 실제 데이터를 따로 커밋하면 `마커는 있는데 데이터는 없는 상태`가 남아 재실행을 막을 수 있습니다.

### MariaDB 초기 설정 중에는 TCP를 열지 않습니다

관리자 설정과 애플리케이션 계정 준비가 끝나기 전에 외부 TCP 연결을 받을 필요가 없습니다. 따라서 초기 설정용 `mariadbd`는 `--skip-networking`으로 실행하고 같은 컨테이너의 Unix 소켓으로만 초기 SQL을 적용합니다.

초기 설정을 끝낸 뒤 임시 서버를 정상 종료하고, 데이터 파일 사용이 끝난 것을 확인한 후 최종 `mariadbd`를 실행합니다.

### Nginx만 호스트 포트를 공개합니다

외부 클라이언트는 Nginx에만 접속합니다.

```text
호스트에서 접근 가능
127.0.0.1:19443 → gateway:443

Compose 내부에서만 사용
app:9000
 db:3306
```

PHP-FPM과 MariaDB는 `app-net` 내부에서 서비스 이름으로 접근합니다. `app:9000`과 `db:3306`을 호스트에 게시하지 않아도 컨테이너끼리 통신할 수 있습니다.

### 상태 검사와 사용자 기능 검사를 구분합니다

검사는 깊이에 따라 확인 범위가 다릅니다.

```text
/healthz
Nginx 자체

/health
Nginx → PHP-FPM → DB 읽기

/api/notes
실제 애플리케이션 기능
```

예를 들어 `/healthz`가 성공해도 `fastcgi_pass`가 잘못되어 있으면 PHP 요청은 502가 될 수 있습니다. 반대로 실제 요청은 성공하는데 healthcheck 명령 자체의 경로나 도구가 잘못되어 컨테이너만 `unhealthy`로 표시될 수도 있습니다.

Compose의 healthcheck 하나가 생존 검사, 준비 검사, 사용자 기능 검사를 자동으로 구분하는 것은 아닙니다. 어떤 검사가 어디까지 확인하는지 알고 결과를 해석해야 합니다.

### 최종 서버는 `exec`로 실행합니다

DB와 app의 시작 스크립트는 초기 준비 작업을 끝낸 뒤 최종 서버를 `exec`합니다.

```text
entrypoint shell
→ 초기화
→ exec 최종 서버
→ 최종 서버가 PID 1
```

이렇게 해야 Docker가 보내는 종료 신호가 최종 서버에 직접 전달되고, 종료 상태도 불필요한 중간 셸 없이 컨테이너 상태에 반영됩니다.

## 장애를 확인하는 기본 순서

문제가 생기면 최종 HTTP 상태만 보고 원인을 단정하지 않습니다. 다음처럼 계층을 나누어 확인합니다.

```text
컨테이너 상태
→ PID 1과 프로세스
→ 서비스 이름 해석
→ TCP 연결
→ TLS / HTTP / FastCGI / MariaDB 프로토콜
→ 인증과 설정
→ 파일 경로와 권한
→ 볼륨과 데이터
→ 실제 사용자 기능
```

예를 들어 브라우저에서 502가 보인다고 해서 반드시 Nginx 설정이 원인은 아닙니다.

```text
DB 인증 실패
→ app bootstrap 실패
→ app 종료
→ gateway가 app:9000에 연결하지 못함
→ 외부 요청 502
```

따라서 로그에서는 마지막에 나타난 오류뿐 아니라 **시간순으로 가장 먼저 발생한 실패**를 찾습니다.

기본 확인 명령은 다음과 같습니다.

```sh
docker compose ps -a
docker compose logs --timestamps gateway app db
docker compose config
```

민감한 환경변수나 비밀값이 출력될 수 있는 명령 결과는 외부에 공유하기 전에 확인합니다.

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

이 프로젝트가 다루는 범위를 명확히 구분합니다.

- 한 호스트에서 실행하는 Docker Compose 구성을 다룹니다.
- 개발용 자체 서명 인증서만 만들며 공인 인증서 발급과 자동 갱신은 포함하지 않습니다.
- Nginx만 호스트 포트를 공개하고 PHP-FPM과 MariaDB는 Compose 내부 네트워크에서 사용합니다.
- MariaDB의 이름 있는 볼륨으로 컨테이너와 데이터의 수명을 분리합니다.
- 백업을 다른 호스트나 객체 저장소로 자동 전송하지 않습니다.
- 백업 암호화, 보존 기간, 예약 실행과 원격 복제는 포함하지 않습니다.
- 일반적인 스키마 마이그레이션 도구는 포함하지 않습니다. 현재 `bootstrap.php`는 최초 테이블을 준비하는 범위만 다룹니다.
- `CREATE TABLE IF NOT EXISTS`는 기존 테이블을 새 정의로 자동 변경하지 않습니다. 이후 스키마 변경은 별도 마이그레이션 문제입니다.
- PHP-FPM 워커가 사용하는 DB 연결이 실행 중 MariaDB 재시작 등으로 끊어졌을 때 자동으로 새 연결을 만드는 복구 기능은 포함하지 않습니다.
- 이름 있는 볼륨은 백업을 대신하지 않습니다. 복구 가능성은 별도 백업을 실제로 복원해 검증해야 합니다.
- Compose의 healthcheck와 `depends_on`은 애플리케이션의 모든 런타임 장애 처리를 대신하지 않습니다.

## 학습할 때 확인할 질문

프로젝트를 실행한 뒤 명령이 성공하는지만 보지 말고 다음 질문에 답할 수 있는지 확인합니다.

1. 왜 외부에는 Nginx 포트만 공개하고 `app:9000`, `db:3306`은 공개하지 않아도 됩니까?
2. Nginx가 PHP-FPM에 보내는 것은 HTTP가 아니라 어떤 프로토콜입니까?
3. `/healthz`가 성공해도 `/health`와 `/api/notes`가 실패할 수 있는 이유는 무엇입니까?
4. 컨테이너 재생성과 `docker compose down -v`는 MariaDB 데이터에 어떤 차이를 만듭니까?
5. 시작 스크립트가 컨테이너 시작 때마다 실행되어도 최초 메모가 중복되지 않아야 하는 이유는 무엇입니까?
6. 마커와 최초 메모를 같은 트랜잭션에서 처리하지 않으면 어떤 부분 실패 상태가 남을 수 있습니까?
7. MariaDB 최초 초기화 중 TCP를 끄고 Unix 소켓을 사용하는 이유는 무엇입니까?
8. 자체 서명 인증서에서 `curl -k`가 성공했다는 사실이 인증서 신뢰성 검증이 될 수 없는 이유는 무엇입니까?
9. 이름 있는 볼륨이 있는데도 별도 백업과 복원 검증이 필요한 이유는 무엇입니까?
10. 외부에서 502가 보일 때 Nginx 설정만 수정하기 전에 어떤 하위 단계를 확인해야 합니까?

이 질문에 요청 경로와 데이터 수명을 따라 답할 수 있다면, 개별 설정 지시어를 외운 것이 아니라 프로젝트의 구조를 이해한 것입니다.
