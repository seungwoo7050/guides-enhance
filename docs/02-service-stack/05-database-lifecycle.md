# 데이터베이스 생명주기

MariaDB도 컨테이너 안에서 실행되는 서버 프로세스입니다. 다만 게이트웨이나 애플리케이션과 달리 프로세스를 교체해도 사용자 데이터는 남아야 합니다.

이 장에서는 다음 과정을 다룹니다.

```text
빈 볼륨
→ 데이터 디렉터리 초기화
→ TCP를 끈 임시 MariaDB 실행
→ 데이터베이스와 사용자 생성
→ 임시 서버 정상 종료
→ 최종 MariaDB를 PID 1로 실행
→ 재시작과 재생성
→ 백업과 복원
```

## 1. 프로세스와 데이터의 수명을 나눕니다

MariaDB 컨테이너는 필요할 때 다시 만들 수 있어야 합니다. 데이터베이스 파일은 이름 있는 볼륨에 둡니다.

```text
MariaDB 컨테이너     교체 가능
        │
        ▼
/var/lib/mysql 볼륨  명시적으로 지우기 전까지 유지
```

데이터 파일을 컨테이너의 쓰기 계층에 두면 컨테이너 삭제와 함께 사라집니다. 이미지 업데이트와 데이터 보존을 함께 처리하기도 어려워집니다.

## 2. 데이터 디렉터리

MariaDB의 기본 데이터 디렉터리는 보통 `/var/lib/mysql`입니다. 이곳에는 다음 항목이 저장됩니다.

- 인증과 권한을 관리하는 시스템 데이터베이스
- 애플리케이션 테이블과 인덱스
- InnoDB 데이터와 로그
- 서버가 다시 시작할 때 필요한 내부 상태

이 디렉터리는 SQL 파일 모음이 아닙니다. MariaDB 버전과 저장 엔진이 해석하는 내부 형식입니다.

```yaml
services:
  db:
    volumes:
      - db-data:/var/lib/mysql

volumes:
  db-data:
```

## 3. 빈 디렉터리 초기화

완전히 빈 데이터 디렉터리에는 인증과 권한을 관리할 시스템 테이블이 없습니다. 먼저 `mariadb-install-db`를 실행합니다.

```sh
mariadb-install-db \
  --user=mysql \
  --datadir=/var/lib/mysql \
  --skip-test-db \
  --auth-root-authentication-method=socket
```

- `--user=mysql`: 생성 파일의 소유자를 MariaDB 실행 사용자로 맞춥니다.
- `--datadir`: 최종 서버가 사용할 데이터 디렉터리와 같아야 합니다.
- `--skip-test-db`: 불필요한 테스트 데이터베이스를 만들지 않습니다.

초기화는 빈 볼륨에서만 실행합니다.

```sh
if [ ! -d "$datadir/mysql" ]; then
    mariadb-install-db ...
fi
```

`$datadir/mysql`은 시스템 데이터베이스 디렉터리입니다. 존재하면 이전 초기화 결과가 있다고 판단합니다.

디렉터리 존재만으로 초기화가 완전히 끝났다고 보장할 수는 없습니다. 중간 실패가 발생하면 일부 파일만 남을 수 있습니다. 작은 단일 호스트 구성에서는 시작 실패를 명확히 남기고 볼륨 상태를 확인한 뒤 복구합니다. 더 큰 시스템에서는 임시 디렉터리, 완료 표시와 별도 복원 절차를 사용할 수 있습니다.

## 4. 디렉터리와 권한

서버를 시작하기 전에 런타임 소켓과 데이터 디렉터리를 준비합니다.

```sh
install -d -m 0755 -o mysql -g mysql /run/mysqld /var/lib/mysql
```

- `/run/mysqld`: 소켓과 PID 파일처럼 컨테이너 종료 시 사라져도 되는 파일
- `/var/lib/mysql`: 볼륨에 남아야 하는 데이터

대용량 데이터 디렉터리에 매번 재귀 `chown`을 실행하면 시작 시간이 길어집니다. 실제로 소유권을 바꿔야 하는 경로만 처리합니다.

## 5. 비밀값과 식별자 검증

데이터베이스 이름과 사용자 이름을 SQL 식별자로 사용할 때는 허용 문자를 제한합니다.

```sh
case "$MARIADB_DATABASE" in
    ''|*[!A-Za-z0-9_]*)
        echo "MARIADB_DATABASE에는 영문자, 숫자와 밑줄만 사용할 수 있습니다." >&2
        exit 1
        ;;
esac
```

비밀번호는 일반 환경변수와 파일 중 하나에서 읽을 수 있게 만들 수 있습니다. 둘 다 설정된 경우에는 어떤 값을 사용할지 임의로 고르지 않고 실패시킵니다.

```text
MARIADB_PASSWORD
MARIADB_PASSWORD_FILE
```

비밀번호를 SQL 문자열에 넣어야 한다면 작은따옴표와 역슬래시를 SQL 규칙에 맞게 처리하고, 로그에는 값을 출력하지 않습니다.

애플리케이션은 root 계정을 사용하지 않습니다. 필요한 데이터베이스에만 접근할 별도 사용자를 만듭니다.

## 6. 초기 설정용 임시 서버

시스템 테이블을 만든 뒤 SQL로 데이터베이스와 사용자를 생성해야 합니다. SQL을 실행하려면 MariaDB가 잠시 실행 중이어야 합니다.

```sh
mariadbd \
  --user=mysql \
  --datadir="$datadir" \
  --skip-networking \
  --socket="$socket" &
temp_pid=$!
```

`--skip-networking`은 초기 root 인증과 사용자 설정이 끝나기 전에 TCP 연결을 받지 않게 합니다. 같은 컨테이너의 Unix 소켓만 사용합니다.

임시 서버는 시작 스크립트가 초기 SQL을 계속 실행해야 하므로 백그라운드에서 실행합니다. 최종 MariaDB 실행 방식과는 다릅니다.

## 7. 준비될 때까지 제한적으로 기다립니다

프로세스를 시작했다고 소켓이 즉시 준비되는 것은 아닙니다.

```sh
ready=0
attempt=0
while [ "$attempt" -lt 60 ]; do
    attempt=$((attempt + 1))
    if mariadb-admin \
        --protocol=socket \
        --socket="$socket" \
        ping --silent >/dev/null 2>&1
    then
        ready=1
        break
    fi
    sleep 1
done

[ "$ready" -eq 1 ] || exit 1
```

재시도에는 횟수나 전체 시간 제한이 있어야 합니다. 한 번의 연결 시도에도 제한 시간이 필요할 수 있습니다. 무한 대기는 실패를 숨기고 배포 전체를 멈춥니다.

`mariadb-admin ping` 성공은 서버가 프로토콜 요청에 응답한다는 뜻입니다. 애플리케이션 사용자의 인증과 실제 쿼리 성공까지 확인하지는 않습니다.

## 8. 데이터베이스와 사용자 생성

임시 서버의 Unix 소켓으로 초기 SQL을 실행합니다.

```sql
CREATE DATABASE IF NOT EXISTS `appdb`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'appuser'@'%'
  IDENTIFIED BY '...';

ALTER USER 'appuser'@'%'
  IDENTIFIED BY '...';

GRANT ALL PRIVILEGES ON `appdb`.* TO 'appuser'@'%';
FLUSH PRIVILEGES;
```

실제 스크립트에서는 데이터베이스 이름과 사용자 이름을 먼저 검증하고 비밀번호를 이스케이프합니다.

`'appuser'@'%'`는 모든 원격 호스트 패턴을 허용하지만, Compose에서 DB 포트를 호스트에 게시하지 않고 내부 네트워크로만 연결 범위를 제한합니다. 네트워크 제한이 인증을 대신하지는 않습니다.

## 9. 임시 서버 종료와 최종 서버 실행

초기 SQL이 끝나면 임시 서버를 정상 종료합니다.

```sh
mariadb-admin \
  --protocol=socket \
  --socket="$socket" \
  -uroot \
  -p"$MARIADB_ROOT_PASSWORD" \
  shutdown

wait "$temp_pid"
```

`wait`는 임시 서버가 데이터 파일 사용을 끝낼 때까지 기다립니다. 임시 서버가 남아 있는 상태에서 최종 서버를 시작하면 파일 잠금이나 복구 충돌이 생길 수 있습니다.

마지막에는 Dockerfile의 CMD를 `exec`합니다.

```sh
exec "$@"
```

```dockerfile
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["mariadbd", "--user=mysql", "--console"]
```

최종 `mariadbd`가 PID 1이 되어 Docker의 종료 신호를 직접 받습니다.

## 10. MariaDB 설정

```ini
[mariadbd]
bind-address = 0.0.0.0
port = 3306
datadir = /var/lib/mysql
socket = /run/mysqld/mysqld.sock
pid-file = /run/mysqld/mysqld.pid
skip-name-resolve
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
innodb-buffer-pool-size = 128M
max-connections = 80
```

### `bind-address`

애플리케이션이 다른 컨테이너에 있으므로 MariaDB가 컨테이너 네트워크 인터페이스에서 연결을 받아야 합니다. `0.0.0.0`에 바인드해도 Compose에 `ports`가 없으면 호스트에 직접 게시되지 않습니다.

### `skip-name-resolve`

클라이언트 IP의 역방향 DNS 조회를 끕니다. MariaDB 권한의 호스트 부분에 DNS 이름을 사용하지 않는 구성이 필요합니다.

### `utf8mb4`

보조 평면 문자와 이모지를 포함한 전체 UTF-8 범위를 저장할 수 있습니다. 서버 기본값을 바꿔도 기존 테이블이 자동으로 변환되지는 않습니다.

### `innodb-buffer-pool-size`

InnoDB 데이터와 인덱스 페이지를 메모리에 캐시합니다. 같은 호스트에서 다른 컨테이너도 메모리를 사용하므로 무작정 크게 잡지 않습니다.

### `max-connections`

동시 연결 수의 상한입니다. 애플리케이션 연결 풀, 관리용 여유와 연결당 메모리를 함께 고려합니다. 값만 키우면 느린 쿼리나 과도한 연결 풀이 만드는 문제를 악화할 수 있습니다.

## 11. 상태 검사

데이터베이스 컨테이너 안에서는 Unix 소켓으로 확인할 수 있습니다.

```sh
mariadb-admin \
  --protocol=socket \
  --socket=/run/mysqld/mysqld.sock \
  -uroot -p"..." \
  ping --silent
```

애플리케이션 컨테이너에서 `db:3306`으로 작은 쿼리를 실행하면 서비스 이름, 네트워크, TCP, 인증과 쿼리까지 더 깊게 확인할 수 있습니다.

상태 검사는 읽기 전용이어야 합니다. 주기적으로 스키마를 만들거나 데이터를 삽입하면 안 됩니다.

## 12. 재시작, 재생성과 삭제

```sh
docker compose restart db
docker compose up -d --force-recreate db
docker compose down
docker compose down -v
```

- 재시작: 같은 컨테이너와 볼륨을 사용합니다.
- 재생성: 새 컨테이너가 같은 볼륨을 사용합니다.
- `down`: 컨테이너를 지우지만 볼륨은 남깁니다.
- `down -v`: 데이터 볼륨까지 지웁니다.

시작 스크립트는 매번 실행되지만 기존 시스템 데이터베이스가 있으면 최초 초기화 블록을 건너뛰어야 합니다.

비밀값 파일만 바꾸면 기존 MariaDB 계정의 비밀번호가 자동으로 바뀌지 않습니다. 이미 초기화된 볼륨에서는 `ALTER USER`, 비밀값 교체와 의존 서비스 재시작을 순서대로 수행해야 합니다.

## 13. 백업과 복원

볼륨은 컨테이너 삭제와 데이터 수명을 분리할 뿐 별도 백업이 아닙니다. 호스트 디스크 손상, 잘못된 SQL과 볼륨 삭제에 대비하려면 별도 사본이 필요합니다.

### 논리 백업

```sh
docker compose exec -T db \
  mariadb-dump \
  -uappuser -p"..." \
  --single-transaction \
  --routines --triggers \
  appdb > appdb.sql
```

`--single-transaction`은 InnoDB 테이블을 일관된 시점에서 읽는 데 사용합니다. 큰 DB나 비트랜잭션 테이블은 별도 조건을 검토해야 합니다.

백업 파일은 임시 파일에 완전히 쓴 뒤 이름을 바꾸어 공개하면 중간 실패로 기존 백업을 부분 파일로 덮는 일을 줄일 수 있습니다.

### 복원

```sh
docker compose exec -T db \
  mariadb -uappuser -p"..." appdb < appdb.sql
```

복원 명령이 끝났다는 사실만으로 성공을 판단하지 않습니다. 별도 빈 환경에 복원하고 행 수, 제약 조건과 애플리케이션 요청을 확인합니다.

> 복원해 보지 않은 백업은 복구 수단으로 검증된 것이 아닙니다.

## 14. 인덱스와 `EXPLAIN`

인덱스가 없으면 조건에 맞는 행을 찾기 위해 많은 행을 읽을 수 있습니다.

```sql
EXPLAIN
SELECT id, display_name
FROM index_demo
WHERE email = 'user0500@users.local.test';
```

인덱스를 만든 뒤 같은 실행 계획을 비교합니다.

```sql
CREATE UNIQUE INDEX idx_index_demo_email
ON index_demo (email);
```

확인할 항목은 실행 시간 하나가 아닙니다.

- 실제 선택한 인덱스
- 예상 읽기 행 수
- 전체 테이블 스캔 여부
- 추가 정렬이나 임시 작업 여부

인덱스는 디스크 공간과 쓰기 비용도 사용합니다. 실제 쿼리와 데이터 분포를 보고 추가합니다.

## 15. 자주 생기는 오해

### `bind-address = 0.0.0.0`이면 인터넷에 공개됩니다

컨테이너 안의 모든 IPv4 인터페이스에서 연결을 받는다는 뜻입니다. 호스트 공개 여부는 Compose `ports`와 호스트 방화벽이 결정합니다.

### 볼륨이 있으므로 백업은 필요 없습니다

볼륨과 호스트가 함께 손상되거나 운영자가 볼륨을 삭제하면 데이터도 사라집니다.

### 연결 수를 늘리면 DB 문제가 해결됩니다

느린 쿼리와 과도한 연결 풀이 원인이라면 메모리 고갈을 늦추거나 오히려 악화할 수 있습니다.

### 인덱스는 많을수록 좋습니다

조회 성능과 함께 쓰기 비용, 저장 공간과 백업 시간을 고려해야 합니다.

## 확인 문제

1. 빈 데이터 디렉터리에 `mariadb-install-db`가 필요한 이유는 무엇입니까?
2. 초기 설정용 MariaDB에서 `--skip-networking`을 사용하는 이유는 무엇입니까?
3. 임시 서버를 종료한 뒤 `wait`해야 하는 이유는 무엇입니까?
4. 컨테이너 재생성과 볼륨 삭제는 데이터 결과가 어떻게 다릅니까?
5. 비밀값 파일만 바꿔도 기존 사용자 비밀번호가 바뀌지 않는 이유는 무엇입니까?
6. 이름 있는 볼륨과 논리 백업은 각각 어떤 문제를 해결합니까?

## 참고 문서

- `mariadb-install-db`: https://mariadb.com/docs/server/clients-and-utilities/deployment-tools/mariadb-install-db
- MariaDB 공식 이미지: https://hub.docker.com/_/mariadb
- MariaDB `EXPLAIN`: https://mariadb.com/docs/server/reference/sql-statements/administrative-sql-statements/analyze-and-explain-statements/explain
- MariaDB 인덱스: https://mariadb.com/docs/server/ha-and-performance/optimization-and-tuning/optimization-and-indexes
- Docker 볼륨: https://docs.docker.com/engine/storage/volumes/
