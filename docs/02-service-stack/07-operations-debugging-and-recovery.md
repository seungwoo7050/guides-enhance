# 운영 중 장애를 확인하고 복구하기

앞 장까지는 Nginx, PHP-FPM, MariaDB를 연결하고 반복 실행 가능한 시작 절차를 만들었습니다. 이제 새 기능을 추가하지 않고 정상 구성을 한 가지씩 깨뜨려 원인을 찾습니다.

오류 메시지를 보자마자 여러 설정을 동시에 바꾸면 어떤 변경이 문제를 해결했는지 알 수 없습니다. 먼저 어디까지 정상인지 확인하고, 한 가지 가설만 검사한 뒤, 한 가지 원인만 수정합니다.

```text
증상 확인
→ 어디까지 성공했는지 확인
→ 다음 검사 선택
→ 한 가지 원인 수정
→ 같은 방법으로 복구 확인
```

## 1. “실행 중”과 “정상”은 다릅니다

서비스 상태는 여러 단계로 나눠 확인합니다.

### 컨테이너

- 컨테이너가 생성됐습니까?
- PID 1이 실행 중입니까?
- 종료와 재시작을 반복합니까?

### 프로세스

- 기대한 서버가 PID 1입니까?
- 필요한 워커가 만들어졌습니까?
- 올바른 사용자로 실행됩니까?

### 네트워크

- 서비스 이름이 IP 주소로 해석됩니까?
- 예상 포트에서 연결을 기다립니까?
- 다른 컨테이너에서 TCP 연결이 됩니까?

### 프로토콜

- TLS handshake가 성공합니까?
- Nginx가 HTTP 응답을 반환합니까?
- PHP-FPM이 FastCGI ping에 응답합니까?
- MariaDB가 인증과 읽기 쿼리를 처리합니까?

### 사용자 기능과 데이터

- 실제 API가 응답합니까?
- 필요한 테이블과 데이터가 있습니까?
- 컨테이너를 바꿔도 데이터가 남습니까?
- 백업을 빈 DB에 복원할 수 있습니까?

하위 단계가 실패한 상태에서 상위 기능부터 검사하면 2차 증상만 보게 됩니다.

## 2. 생존 검사, 준비 검사, 사용자 기능 검사를 구분합니다

### 생존 검사

프로세스가 계속 실행될 수 있는지 확인합니다. 실패할 때 재시작이 도움이 되는 검사여야 합니다.

외부 의존성을 지나치게 포함하면 DB의 일시적인 장애 때문에 정상 애플리케이션을 계속 재시작할 수 있습니다.

### 준비 검사

현재 요청을 받을 수 있는지 확인합니다. 초기화가 끝나지 않았거나 워커가 준비되지 않았다면 트래픽을 받아서는 안 됩니다.

### 사용자 기능 검사

외부에서 중요한 요청을 보내 전체 경로를 확인합니다.

```text
HTTPS 요청
→ Nginx
→ FastCGI
→ PHP-FPM
→ MariaDB 읽기
```

이 검사는 실제 기능을 확인하지만 실패 원인이 많습니다. 내부 검사 결과와 함께 사용해야 합니다.

Docker Compose의 `healthcheck` 하나가 이 세 목적을 자동으로 구분해 주지는 않습니다. 각 상태 검사가 무엇을 확인하는지 문서에 적습니다.

## 3. 서비스가 사용하는 프로토콜로 검사합니다

### Nginx

```sh
curl -kfsS https://127.0.0.1:19443/healthz >/dev/null
```

TLS와 HTTP 처리를 확인합니다. 개발용 자체 서명 인증서라서 `-k`를 쓰는 예이며, 공개 환경의 검증에서는 인증서 검사를 끄면 안 됩니다.

### PHP-FPM

```sh
REQUEST_METHOD=GET \
SCRIPT_NAME=/ping \
SCRIPT_FILENAME=/ping \
cgi-fcgi -bind -connect 127.0.0.1:9000 | grep -q pong
```

PHP-FPM은 HTTP 서버가 아니므로 9000 포트에 `curl`을 보내지 않습니다.

### MariaDB

```sh
mariadb-admin \
  --protocol=socket \
  --socket=/run/mysqld/mysqld.sock \
  -uroot -p"..." \
  ping --silent
```

프로세스 이름만 확인하는 것보다 실제 DB 프로토콜 응답까지 확인합니다.

### 전체 애플리케이션

```sh
curl -kfsS https://127.0.0.1:19443/api/notes >/dev/null
```

게이트웨이, 애플리케이션, 데이터베이스의 읽기 경로를 함께 검사합니다.

## 4. 좋은 상태 검사의 조건

- 짧게 끝납니다.
- 한 번의 실행에 제한 시간이 있습니다.
- 읽기 전용입니다.
- 반복 실행해도 상태를 바꾸지 않습니다.
- 서비스가 실제로 사용하는 프로토콜을 확인합니다.
- 정상으로 판단하는 조건이 명확합니다.
- 실패했을 때 원인을 찾을 수 있는 출력을 남깁니다.

상태 검사에서 대형 통계 쿼리, 외부 인터넷 서비스 호출, 데이터 자동 수정 같은 작업을 수행하지 않습니다.

## 5. 기본 진단 순서

다음 순서를 출발점으로 사용합니다.

```text
1. Compose가 필요한 서비스를 만들었는가?
2. 컨테이너의 PID 1이 실행 중인가?
3. 최초 오류 로그는 무엇인가?
4. 예상 주소와 포트에서 연결을 기다리는가?
5. 서비스 이름이 해석되는가?
6. TCP 연결이 되는가?
7. 실제 프로토콜 요청에 응답하는가?
8. 설정과 비밀값 파일이 올바른가?
9. 파일 경로와 권한이 올바른가?
10. 기대한 볼륨과 데이터가 연결됐는가?
11. 사용자 기능이 정상인가?
```

모든 장애에 이 순서를 기계적으로 끝까지 적용할 필요는 없습니다. 이미 확보한 증거를 기준으로 다음 검사를 선택합니다. 다만 하위 단계가 실패했는데 상위 단계만 반복해서 검사하지는 않습니다.

## 6. Compose 상태와 실제 설정을 확인합니다

```sh
docker compose ps -a
docker compose config --services
docker compose config
```

확인할 내용:

- 기대한 서비스가 있는지
- 컨테이너 상태와 종료 코드
- 상태 검사 결과
- 호스트에 공개한 포트
- 환경변수 보간 결과
- 연결된 네트워크와 볼륨

`docker compose config` 출력에는 민감한 값이 포함될 수 있으므로 외부에 공유하기 전에 확인합니다.

## 7. 로그에서는 최초 오류를 찾습니다

```sh
docker compose logs --timestamps
docker compose logs --tail=100 app
docker compose logs -f gateway app db
```

재시작이 반복되면 같은 마지막 오류가 계속 쌓입니다. 그보다 앞의 첫 번째 설정 오류가 실제 원인일 수 있습니다.

예를 들어 다음 순서로 문제가 퍼질 수 있습니다.

```text
DB 인증 실패
→ 애플리케이션 초기화 실패
→ app 컨테이너 종료
→ Nginx가 app에 연결하지 못함
→ 사용자 요청 502
```

502만 보고 Nginx 설정부터 바꾸면 원인을 놓칩니다.

로그에는 비밀번호, 전체 DSN, `Authorization` 헤더를 남기지 않습니다. 비밀값 처리 중 `set -x`도 사용하지 않습니다.

## 8. 프로세스와 PID 1을 확인합니다

```sh
docker compose top
docker compose exec app ps -o pid,ppid,user,stat,command -ef
```

다음을 확인합니다.

- PID 1이 기대한 서버인지 셸인지
- 워커가 만들어졌는지
- 실행 사용자가 맞는지
- 프로세스가 계속 새 PID로 바뀌는지
- 종료된 자식 프로세스가 누적되는지

컨테이너가 이미 종료됐다면 `docker exec`은 사용할 수 없습니다. 로그와 종료 상태를 확인하거나 시작 명령을 임시로 바꿔 별도의 조사용 컨테이너를 실행합니다.

## 9. 이름 해석과 연결을 따로 검사합니다

서비스 이름 확인:

```sh
docker compose exec gateway getent hosts app
docker compose exec app getent hosts db
```

TCP 연결 확인:

```sh
docker compose exec gateway sh -c 'nc -z app 9000'
```

DNS가 성공해도 포트에서 연결을 받는다는 뜻은 아닙니다. 반대로 IP로 직접 연결해 성공하더라도 서비스 이름 오타는 남아 있을 수 있습니다.

확인할 항목:

- Compose 서비스 이름 오타
- 공통 네트워크 연결 여부
- 다른 Compose 프로젝트의 자원을 보고 있지 않은지
- 대상 프로세스가 실제 포트에서 listen 중인지

## 10. HTTP와 TLS를 확인합니다

```sh
curl -vk https://127.0.0.1:19443/healthz
```

verbose 출력에서 다음을 구분합니다.

- 연결한 IP와 포트
- TLS handshake와 인증서
- 보낸 요청과 `Host` header
- 받은 HTTP 상태와 header

인증서 검증까지 확인하려면 `-k`를 제거하고 신뢰할 CA 파일을 지정합니다.

```sh
curl --cacert development.crt https://localhost:19443/healthz
```

상세한 인증서 정보는 `openssl s_client`로 확인할 수 있습니다.

```sh
openssl s_client \
  -connect 127.0.0.1:19443 \
  -servername localhost \
  -showcerts </dev/null
```

## 11. FastCGI 문제를 확인합니다

Nginx가 502를 반환하면 PHP-FPM을 직접 검사합니다.

```sh
docker compose exec app sh -c '
  REQUEST_METHOD=GET \
  SCRIPT_NAME=/ping \
  SCRIPT_FILENAME=/ping \
  cgi-fcgi -bind -connect 127.0.0.1:9000
'
```

결과를 다음처럼 해석합니다.

- 연결 자체가 실패하면 FPM 프로세스와 listen 설정을 확인합니다.
- FPM ping은 성공하지만 Nginx가 502를 반환하면 네트워크, DNS, `fastcgi_pass`를 확인합니다.
- FastCGI 연결은 되지만 PHP 파일을 찾지 못하면 `SCRIPT_FILENAME`과 파일 권한을 확인합니다.
- PHP 코드가 실행된 뒤 실패하면 애플리케이션 로그와 DB 오류를 확인합니다.

## 12. 데이터베이스를 단계별로 확인합니다

DB 컨테이너 안의 local socket:

```sh
docker compose exec db mariadb-admin \
  --protocol=socket \
  --socket=/run/mysqld/mysqld.sock \
  ping --silent
```

애플리케이션 컨테이너에서 TCP와 인증:

```sh
docker compose exec app php -r '
$pdo = new PDO(
    "mysql:host=db;port=3306;dbname=appdb;charset=utf8mb4",
    "appuser",
    trim(file_get_contents(getenv("DB_PASSWORD_FILE")))
);
echo $pdo->query("SELECT 1")->fetchColumn(), PHP_EOL;
'
```

비밀번호를 명령에 직접 쓰거나 셸 기록에 남기지 않습니다.

오류 예:

| 오류 | 먼저 확인할 내용 |
|---|---|
| 이름 해석 실패 | 서비스 이름, 네트워크 |
| `Connection refused` | DB 프로세스, 포트, listen 주소 |
| 제한 시간 초과 | 네트워크 단절, 과부하, 긴 쿼리 |
| `Access denied` | 사용자, 비밀번호, 호스트 권한 |
| `Unknown database` | 최초 초기화, DB 이름 |
| 테이블 없음 | 애플리케이션 초기화, 스키마 적용 |

## 13. 파일 경로와 권한을 확인합니다

```sh
id
ls -ld /var /var/www /var/www/html
ls -l /var/www/html/index.php
namei -l /var/www/html/index.php
```

파일 자체뿐 아니라 모든 상위 디렉터리를 통과할 권한이 필요합니다.

확인할 항목:

- 실제 실행 UID/GID
- 파일 소유자와 그룹
- 읽기·쓰기·실행 권한
- bind 마운트가 이미지 안의 파일을 가렸는지
- 읽기 전용 마운트에 쓰고 있는지
- 호스트에서 SELinux label이 필요한지

문제를 임시로 숨기기 위해 `chmod -R 777`을 사용하지 않습니다. 어떤 프로세스가 어느 경로에 어떤 권한이 필요한지 먼저 확인합니다.

## 14. 볼륨과 데이터 위치를 확인합니다

```sh
docker volume ls
docker volume inspect PROJECT_db-data
docker inspect container-name --format '{{json .Mounts}}'
```

데이터가 사라진 것처럼 보이면 기존 볼륨을 먼저 삭제하지 않습니다. 다음을 확인합니다.

- Compose 프로젝트 이름이 달라 새 볼륨이 생겼는지
- 기대한 볼륨 이름인지
- `/var/lib/mysql`에 연결됐는지
- 빈 호스트 directory가 이미지 파일을 가렸는지
- `docker compose down -v`를 실행했는지

새 빈 볼륨을 연결한 상태는 기존 데이터가 삭제된 상태와 다를 수 있습니다. 기존 볼륨 목록과 마운트를 먼저 확인합니다.

## 15. 재시작 반복을 멈추고 원인을 확인합니다

재시작 설정은 잘못된 설정을 고치지 않습니다.

```text
시작
→ 설정 오류
→ 종료
→ 자동 재시작
→ 같은 오류 반복
```

```sh
docker inspect container-name --format '{{.RestartCount}}'
docker compose logs --tail=200 app
```

조사 중에는 반복을 멈추고 최초 오류를 보존합니다. 재시작하기 전에 현재 로그, 종료 코드와 마운트 상태를 기록합니다.

## 16. SIGTERM과 정상 종료를 확인합니다

```sh
docker compose kill -s TERM app
docker compose logs app
```

정상적인 종료는 다음 순서를 따릅니다.

```text
Docker가 PID 1에 SIGTERM 전달
→ 서버가 새 작업 수락 중단
→ 진행 중 작업 정리
→ 종료 상태 반환
```

시작 셸이 PID 1로 남고 서버를 자식 프로세스로 실행하면 signal 전달과 종료 상태가 달라질 수 있습니다. 시작 스크립트 마지막의 `exec "$@"`가 필요한 이유입니다.

## 17. 한 가지 오류만 주입해 검사합니다

`notes-stack`의 fault test는 정상 구성에 한 가지 변경만 더합니다.

### 잘못된 DB 호스트

- DB는 정상입니다.
- 애플리케이션은 이름 해석 또는 연결에서 실패합니다.
- Nginx 설정을 바꾸지 않고 app 로그와 DNS를 확인합니다.

### 잘못된 DB 비밀번호

- `db:3306`까지는 도달합니다.
- 인증에서 실패합니다.
- 연결 실패와 자격 증명 실패를 구분합니다.

### 존재하지 않는 비밀값 파일

- 애플리케이션은 DB 연결 전에 종료합니다.
- 로그에는 실제 비밀값이 아니라 읽을 수 없는 경로만 표시됩니다.

### 잘못된 FastCGI 포트

- Nginx 자체 상태 검사는 성공할 수 있습니다.
- 정적 파일도 응답할 수 있습니다.
- PHP 요청만 502를 반환합니다.

### 고장 난 상태 검사

- 외부 요청은 성공합니다.
- Docker의 상태 검사만 실패합니다.
- 서비스가 고장 난 것인지 검사 명령이 고장 난 것인지 구분합니다.

### DB 볼륨 삭제

- 무상태 컨테이너를 바꿀 때는 데이터가 남습니다.
- 볼륨을 삭제하면 사용자가 추가한 데이터가 사라집니다.
- 빈 DB의 재초기화는 삭제된 데이터의 복구가 아닙니다.

## 18. 백업은 복원으로 검증합니다

백업 파일이 만들어졌다는 사실만으로는 충분하지 않습니다.

```text
별도 빈 DB 준비
→ 백업 복원
→ 테이블과 행 확인
→ 애플리케이션 연결
→ 사용자 기능 검사
```

복원에 필요한 비밀번호, 스키마 버전, 실행 순서와 걸린 시간을 기록합니다. 운영 사고가 발생한 뒤 처음으로 복원 명령을 작성하지 않습니다.

## 19. 증상별 출발점

| 증상 | 먼저 확인 | 다음 확인 |
|---|---|---|
| 호스트 이름 해석 실패 | 서비스 이름, 네트워크 | 컨테이너 상태 |
| 연결 거부 | 프로세스, listen 포트 | address, 네트워크 |
| TLS 인증서 오류 | SAN, 신뢰 CA, 유효기간 | server name, chain |
| HTTP 404 | Nginx `location`, `root`, `try_files` | 파일과 route |
| HTTP 403 | 파일과 디렉터리 권한 | 실행 사용자, 마운트 |
| HTTP 500 | 애플리케이션/FPM 로그 | DB, 코드, 설정 |
| HTTP 502 | app/FPM 실행, FastCGI 포트 | DNS, `SCRIPT_FILENAME` |
| DB 접근 거부 | 사용자, 비밀번호, 호스트 권한 | 비밀값 출처, 초기 SQL |
| DB나 테이블 없음 | 최초 초기화, 스키마 적용 | DB 이름, 볼륨 |
| 데이터가 초기화됨 | 볼륨 이름과 마운트 | 프로젝트 이름, `down -v` |
| 재시작 반복 | 최초 종료 로그 | 설정, restart 값 |
| `unhealthy`인데 요청 성공 | 상태 검사 명령 | 도구, 경로, 권한 |

이 표는 원인을 확정하지 않습니다. 첫 검사를 선택하는 데만 사용합니다.

## 20. 피해야 할 습관

### “재시작하면 해결될 것입니다”

일시적인 오류에는 도움이 될 수 있지만 잘못된 설정과 데이터 손상은 그대로입니다. 먼저 증거를 남깁니다.

### “로그 마지막 줄이 원인입니다”

마지막 줄은 연쇄적으로 생긴 2차 오류일 수 있습니다. 시간순으로 최초 오류를 찾습니다.

### “상태 검사가 실패했으니 서비스도 고장 났습니다”

검사 명령 자체가 틀릴 수 있습니다. 컨테이너 안에서 같은 명령을 직접 실행합니다.

### “관리자 권한과 777로 바꾸면 원인을 찾기 쉽습니다”

증상을 바꾸고 원인을 숨길 수 있습니다. 실제 실행 사용자와 필요한 권한을 확인합니다.

### “백업 파일이 있으니 복구할 수 있습니다”

빈 환경에 복원하고 사용자 기능까지 검사해야 합니다.

## 21. 확인 질문

1. 컨테이너가 `running`인데도 서비스가 준비되지 않을 수 있는 이유는 무엇입니까?
2. 502 응답이 발생했을 때 DB 인증 실패까지 어떻게 연결해 확인하시겠습니까?
3. DNS 성공과 TCP 연결 성공은 어떤 점이 다릅니까?
4. PHP-FPM을 `curl`로 검사하면 안 되는 이유는 무엇입니까?
5. 외부 요청은 성공하지만 상태 검사만 실패할 때 무엇부터 확인하시겠습니까?
6. 데이터가 사라진 것처럼 보일 때 기존 볼륨을 삭제하면 안 되는 이유는 무엇입니까?
7. 재시작 전에 어떤 증거를 보존해야 합니까?
8. 백업이 실제 복구 수단임을 어떻게 확인하시겠습니까?

## 정리

- 컨테이너, 프로세스, 네트워크, protocol, 사용자 기능, 데이터 상태를 따로 확인합니다.
- 생존 검사, 준비 검사, 사용자 기능 검사의 목적을 구분합니다.
- 서비스가 실제로 사용하는 프로토콜로 상태를 확인합니다.
- 가장 먼저 나타난 오류와 뒤따른 오류를 구분합니다.
- 한 번에 한 가지 원인만 수정하고 같은 검사로 복구를 확인합니다.
- DNS, TCP, TLS, HTTP, FastCGI, DB 인증을 순서대로 나눠 검사합니다.
- restart 설정은 잘못된 설정을 고치지 않습니다.
- 기존 볼륨을 삭제하기 전에 실제 마운트와 프로젝트 이름을 확인합니다.
- 백업은 빈 환경에 복원해 검증합니다.

## 공식 문서

- Compose 서비스와 상태 검사: https://docs.docker.com/reference/compose-file/services/
- Compose 시작 순서: https://docs.docker.com/compose/how-tos/startup-order/
- Docker 로그: https://docs.docker.com/reference/cli/docker/컨테이너/logs/
- Docker inspect: https://docs.docker.com/reference/cli/docker/inspect/
- MariaDB 백업과 복원: https://mariadb.com/docs/server/server-usage/백업-and-복원
