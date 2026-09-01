# 데이터베이스 생명주기

MariaDB도 컨테이너 안에서 실행되는 서버 프로세스입니다. 다만 게이트웨이나 애플리케이션과 달리 **프로세스의 수명과 데이터의 수명을 분리**해야 합니다. 컨테이너는 이미지 교체나 설정 변경 때문에 다시 만들 수 있지만, 사용자 데이터는 명시적으로 삭제하거나 복원하지 않는 한 유지되어야 합니다.

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

핵심은 시작 스크립트를 단순히 "MariaDB를 실행하는 스크립트"로 보지 않고 다음 두 상태를 구분하는 것입니다.

```text
최초 시작
  데이터 파일 없음
  → 시스템 테이블 생성
  → 초기 SQL 실행
  → 정상 서버 실행

이후 시작
  기존 데이터 파일 있음
  → 초기화 생략
  → 기존 데이터로 정상 서버 실행
```

## 1. 프로세스와 데이터의 수명을 나눕니다

MariaDB 컨테이너는 필요할 때 다시 만들 수 있어야 합니다. 데이터베이스 파일은 이름 있는 볼륨(named volume)에 둡니다.

```text
MariaDB 컨테이너     교체 가능
        │
        ▼
/var/lib/mysql 볼륨  명시적으로 삭제하기 전까지 유지
```

데이터 파일을 컨테이너의 쓰기 계층에만 두면 컨테이너를 삭제할 때 함께 사라집니다. 반대로 볼륨을 사용하면 다음 두 작업을 분리할 수 있습니다.

```text
새 이미지로 컨테이너 교체
        │
        └─ 기존 볼륨 재사용 → 데이터 유지

볼륨까지 명시적으로 삭제
        │
        └─ 데이터 삭제
```

볼륨은 **컨테이너보다 오래 사는 저장소**이지 백업은 아닙니다. 같은 호스트의 디스크가 손상되거나 볼륨을 잘못 삭제하면 데이터도 함께 사라질 수 있습니다.

## 2. 데이터 디렉터리

MariaDB의 기본 데이터 디렉터리는 일반적으로 `/var/lib/mysql`입니다. 이곳에는 다음과 같은 서버 내부 파일이 저장됩니다.

- 인증과 권한을 관리하는 시스템 데이터베이스
- 애플리케이션 테이블과 인덱스
- InnoDB 데이터 파일과 redo/undo 관련 파일
- 서버 재시작과 복구에 필요한 내부 상태

이 디렉터리는 SQL 파일 모음이 아닙니다. MariaDB 서버와 저장 엔진이 해석하는 내부 형식이므로 일반 파일처럼 일부만 복사하거나 수정해서는 안 됩니다.

```yaml
services:
  db:
    volumes:
      - db-data:/var/lib/mysql

volumes:
  db-data:
```

또한 **데이터 디렉터리를 유지한 채 MariaDB 버전을 변경하는 일은 단순한 컨테이너 교체와 다릅니다.** 버전 조합에 따라 업그레이드 절차가 필요할 수 있으므로, 이미지 버전을 올릴 때는 해당 MariaDB 버전의 업그레이드 지침과 백업·복원 절차를 함께 확인해야 합니다.

## 3. 빈 데이터 디렉터리 초기화

완전히 빈 데이터 디렉터리에는 인증과 권한을 관리할 시스템 테이블이 없습니다. 이런 상태에서는 일반 서버를 바로 실행하는 대신 `mariadb-install-db`로 시스템 테이블을 먼저 만듭니다.

```sh
mariadb-install-db \
  --user=mysql \
  --datadir=/var/lib/mysql \
  --skip-test-db \
  --auth-root-authentication-method=socket
```

각 옵션의 의미는 다음과 같습니다.

- `--user=mysql`: 초기화 과정에서 생성되는 파일을 최종 MariaDB 서버가 사용하는 OS 사용자와 맞춥니다.
- `--datadir=/var/lib/mysql`: 최종 서버가 사용할 데이터 디렉터리를 초기화합니다.
- `--skip-test-db`: 기본 테스트 데이터베이스를 만들지 않습니다.
- `--auth-root-authentication-method=socket`: 로컬 Unix 소켓에서 OS 계정 정보를 이용해 관리 계정을 인증할 수 있게 합니다.

`socket` 방식에서는 `root@localhost`가 로컬 Unix 소켓 인증을 사용할 수 있습니다. 따라서 초기 부트스트랩 단계에서 root 비밀번호를 아직 설정하지 않았더라도, 적절한 OS 사용자로 실행 중인 초기화 스크립트는 로컬 소켓을 통해 관리 SQL을 실행할 수 있습니다.

### 단순한 디렉터리 존재 검사는 완전하지 않습니다

다음과 같은 검사는 작은 구성에서 흔히 사용됩니다.

```sh
if [ ! -d "$datadir/mysql" ]; then
    mariadb-install-db ...
fi
```

`$datadir/mysql`은 시스템 데이터베이스가 저장되는 디렉터리이므로 일반적인 최초 실행 여부를 구분하는 데 사용할 수 있습니다. 하지만 **디렉터리가 존재한다고 해서 초기화가 완전히 성공했다는 뜻은 아닙니다.**

예를 들어 다음 순서로 실패할 수 있습니다.

```text
mariadb-install-db 시작
→ 일부 시스템 파일 생성
→ 컨테이너 강제 종료
→ mysql/ 디렉터리는 남음
→ 다음 시작에서 "이미 초기화됨"으로 오판
```

따라서 시작 스크립트는 최소한 다음 원칙을 가져야 합니다.

1. 실제 초기화 전에는 데이터 디렉터리가 비어 있는지 확인합니다.
2. 시스템 테이블 생성과 필수 초기 SQL이 모두 성공해야 초기화 완료로 봅니다.
3. 초기화 도중 실패한 흔적이 있으면 조용히 계속하지 말고 명확하게 실패시킵니다.
4. 운영 환경에서는 초기화 완료 표시, 복원 절차 또는 공식 이미지의 검증된 초기화 로직을 사용하는 편이 안전합니다.

초기화는 데이터 손실 가능성이 있는 작업이므로 "이상해 보이면 다시 초기화"하는 식으로 자동 복구해서는 안 됩니다.

## 4. 디렉터리와 권한

MariaDB를 시작하기 전에 런타임 디렉터리와 데이터 디렉터리를 구분해서 준비합니다.

```sh
install -d -m 0755 -o mysql -g mysql /run/mysqld
install -d -m 0755 -o mysql -g mysql /var/lib/mysql
```

두 경로의 성격은 다릅니다.

```text
/run/mysqld
  ├─ Unix 소켓
  └─ PID 파일
     → 컨테이너 종료 후 사라져도 됨

/var/lib/mysql
  ├─ 시스템 테이블
  ├─ 사용자 데이터
  └─ InnoDB 내부 파일
     → 볼륨에 남아야 함
```

MariaDB 프로세스가 `mysql` 사용자로 실행된다면 필요한 파일과 디렉터리를 해당 사용자가 읽고 쓸 수 있어야 합니다.

대용량 데이터 디렉터리에 시작할 때마다 다음과 같은 재귀 소유권 변경을 실행하면 비용이 커질 수 있습니다.

```sh
chown -R mysql:mysql /var/lib/mysql
```

수십~수백 GB의 데이터와 많은 파일이 있으면 모든 inode를 순회해야 하기 때문입니다. 이미지 빌드 단계와 볼륨 생성 단계에서 가능한 권한을 미리 맞추고, 런타임에는 실제로 필요한 경로만 변경하는 편이 좋습니다.

## 5. 비밀값과 SQL 입력을 구분합니다

초기화 스크립트는 일반적으로 다음과 같은 외부 입력을 받습니다.

```text
MARIADB_DATABASE
MARIADB_USER
MARIADB_PASSWORD
MARIADB_PASSWORD_FILE
```

이 값들은 모두 문자열이지만 SQL에서 사용되는 위치가 서로 다릅니다.

```text
데이터베이스 이름
→ SQL 식별자(identifier)

사용자 이름과 호스트
→ MariaDB 계정 이름의 구성 요소

비밀번호
→ SQL 문자열 값
```

따라서 같은 이스케이프 규칙을 적용해서는 안 됩니다.

### 데이터베이스 이름과 사용자 이름

사용 가능한 문자를 제한하면 SQL 생성이 단순해지고 잘못된 입력도 일찍 발견할 수 있습니다.

```sh
case "$MARIADB_DATABASE" in
    ''|*[!A-Za-z0-9_]*)
        echo "MARIADB_DATABASE에는 영문자, 숫자와 밑줄만 사용할 수 있습니다." >&2
        exit 1
        ;;
esac

case "$MARIADB_USER" in
    ''|*[!A-Za-z0-9_]*)
        echo "MARIADB_USER에는 영문자, 숫자와 밑줄만 사용할 수 있습니다." >&2
        exit 1
        ;;
esac
```

이 제한은 MariaDB가 허용하는 모든 이름을 표현하기 위한 것이 아니라 **초기화 스크립트가 안전하게 다룰 수 있는 입력 범위를 의도적으로 좁히는 정책**입니다.

### 비밀번호와 `_FILE`

비밀번호는 일반 환경변수나 파일 중 하나에서 읽게 만들 수 있습니다.

```text
MARIADB_PASSWORD
MARIADB_PASSWORD_FILE
```

둘 다 설정되었는데 임의로 하나를 우선하면 운영자가 어떤 값이 적용됐는지 오해할 수 있습니다. 따라서 다음처럼 모호한 입력은 실패시키는 편이 안전합니다.

```text
둘 다 없음     → 정책에 따라 실패
둘 중 하나만 있음 → 사용
둘 다 있음     → 실패
```

비밀번호를 로그에 출력해서는 안 됩니다. 또한 임의 비밀번호를 SQL에 직접 문자열 연결할 때는 따옴표와 역슬래시 등의 해석 규칙을 정확히 처리해야 합니다. 단순히 다음처럼 삽입하면 안전하지 않습니다.

```sh
# 잘못된 예
sql="CREATE USER '$MARIADB_USER'@'%' IDENTIFIED BY '$MARIADB_PASSWORD';"
```

가능하면 검증된 초기화 도구나 검증된 SQL 이스케이프 함수를 사용하고, 비밀값을 명령행 인자나 디버그 로그에 남기지 않습니다.

애플리케이션은 관리용 root 계정을 사용하지 않고 필요한 데이터베이스에 필요한 권한만 가진 별도 계정을 사용합니다.

## 6. 초기 설정용 임시 서버

시스템 테이블을 만든 뒤에는 SQL로 애플리케이션 데이터베이스와 사용자를 생성해야 합니다. SQL을 실행하려면 MariaDB 서버가 잠시 실행 중이어야 합니다.

초기화 도중에는 외부 TCP 연결을 받을 필요가 없습니다.

```sh
datadir=/var/lib/mysql
socket=/run/mysqld/mysqld.sock

mariadbd \
  --user=mysql \
  --datadir="$datadir" \
  --skip-networking \
  --socket="$socket" &
temp_pid=$!
```

`--skip-networking`을 사용하면 TCP/IP 연결을 받지 않고 Unix 소켓을 통한 로컬 연결만 허용합니다.

이 단계의 목적은 다음과 같습니다.

```text
시스템 테이블은 이미 존재
        │
        ▼
임시 mariadbd 시작
        │  TCP는 비활성화
        ▼
로컬 Unix 소켓으로 초기 SQL 실행
        │
        ▼
임시 서버 정상 종료
```

임시 서버는 시작 스크립트가 계속해서 SQL을 실행해야 하므로 백그라운드로 띄웁니다. 반대로 최종 서버는 컨테이너의 주 프로세스가 되어야 하므로 마지막에 포그라운드로 실행합니다.

## 7. 준비될 때까지 제한적으로 기다립니다

`mariadbd` 프로세스가 생성되었다고 해서 Unix 소켓이 즉시 요청을 받을 수 있는 것은 아닙니다. 서버 초기화가 끝날 때까지 기다려야 합니다.

```sh
ready=0
attempt=0

while [ "$attempt" -lt 60 ]; do
    attempt=$((attempt + 1))

    # 서버 프로세스가 이미 죽었다면 60초를 모두 기다리지 않습니다.
    if ! kill -0 "$temp_pid" 2>/dev/null; then
        echo "초기화용 MariaDB가 준비되기 전에 종료되었습니다." >&2
        wait "$temp_pid" || true
        exit 1
    fi

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

if [ "$ready" -ne 1 ]; then
    echo "MariaDB 준비 대기 시간이 초과되었습니다." >&2
    exit 1
fi
```

재시도에는 반드시 횟수나 전체 시간 제한이 있어야 합니다. 무한 대기는 실제 실패를 숨기고 배포 전체를 멈추게 만듭니다.

여기서 `mariadb-admin ping`은 **서버 프로세스의 생존 및 응답 가능 여부를 보는 용도**입니다. 인증 실패가 발생해도 서버가 살아 있으면 성공 종료 코드를 반환할 수 있으므로, 애플리케이션 사용자의 인증 성공을 검증하는 도구로 사용해서는 안 됩니다.

```text
mariadb-admin ping 성공
≠ 애플리케이션 사용자 로그인 성공
≠ SELECT 쿼리 성공
≠ 애플리케이션 스키마 준비 완료
```

## 8. 데이터베이스와 사용자 생성

임시 서버가 준비되면 Unix 소켓을 통해 초기 SQL을 실행합니다.

개념적인 SQL은 다음과 같습니다.

```sql
CREATE DATABASE IF NOT EXISTS `appdb`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'appuser'@'%'
  IDENTIFIED BY '...';

ALTER USER 'appuser'@'%'
  IDENTIFIED BY '...';

GRANT ALL PRIVILEGES ON `appdb`.* TO 'appuser'@'%';
```

`CREATE USER IF NOT EXISTS`는 최초 실행에서 계정을 만들고, `ALTER USER`는 이미 존재하는 경우에도 원하는 인증 정보를 맞추는 역할을 합니다. 실제 스크립트에서는 데이터베이스 이름과 사용자 이름을 먼저 검증하고, 비밀번호는 SQL 문자열 규칙에 맞게 안전하게 처리해야 합니다.

`CREATE USER`, `ALTER USER`, `GRANT` 같은 계정 관리 SQL은 권한 테이블 변경을 서버에 즉시 반영하므로 일반적으로 뒤에 `FLUSH PRIVILEGES`를 붙일 필요가 없습니다. `FLUSH PRIVILEGES`는 시스템 권한 테이블을 직접 수정한 경우에 필요하며, 그런 직접 수정 자체를 일반 초기화 코드에서는 피하는 편이 좋습니다.

### `'appuser'@'%'`의 의미

MariaDB 계정은 사용자 이름만으로 결정되지 않습니다.

```text
'appuser'@'localhost'
'appuser'@'10.0.0.%'
'appuser'@'%'
```

이들은 서로 다른 계정으로 취급될 수 있습니다.

`'appuser'@'%'`의 `%`는 넓은 호스트 패턴을 허용합니다. Compose에서 데이터베이스 포트를 호스트에 게시하지 않고 내부 네트워크에서만 접근하도록 제한하면 실제 접속 범위를 줄일 수 있습니다.

그러나 다음 두 제어는 서로 다른 계층입니다.

```text
Compose 네트워크
→ 어디에서 TCP 연결을 시도할 수 있는가

MariaDB 계정과 권한
→ 연결한 클라이언트가 누구이며 무엇을 할 수 있는가
```

네트워크 격리가 데이터베이스 인증과 권한 검사를 대신하지는 않습니다.

## 9. 임시 서버 종료와 최종 서버 실행

초기 SQL이 모두 성공하면 임시 서버를 정상 종료합니다.

`--auth-root-authentication-method=socket`으로 초기화했고 엔트리포인트가 OS root로 실행되고 있다면 로컬 Unix 소켓의 `root@localhost` 계정을 사용할 수 있습니다.

```sh
mariadb-admin \
  --protocol=socket \
  --socket="$socket" \
  -uroot \
  shutdown
```

그다음 임시 서버 프로세스가 실제로 끝날 때까지 기다립니다.

```sh
wait "$temp_pid"
```

`shutdown` 명령이 반환되었다고 해서 시작 스크립트가 즉시 다음 서버를 실행해도 된다고 가정하지 않습니다. `wait`로 임시 서버가 종료되고 데이터 파일 사용을 마쳤음을 확인합니다.

```text
초기 SQL 완료
→ 정상 shutdown 요청
→ wait
→ 임시 mariadbd 종료 확인
→ 최종 mariadbd 실행
```

임시 서버가 남아 있는 상태에서 같은 데이터 디렉터리를 사용하는 두 번째 서버를 시작하면 파일 잠금 충돌이나 복구 문제가 발생할 수 있습니다.

마지막에는 Dockerfile의 `CMD`를 `exec`합니다.

```sh
exec "$@"
```

```dockerfile
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["mariadbd", "--user=mysql", "--console"]
```

`exec`는 셸 프로세스를 최종 `mariadbd`로 교체합니다. 그러면 MariaDB가 컨테이너의 PID 1이 되어 Docker가 보내는 `SIGTERM` 같은 종료 신호를 직접 받을 수 있습니다.

## 10. MariaDB 설정

예시 설정은 다음과 같습니다.

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

애플리케이션이 다른 컨테이너에 있다면 MariaDB가 컨테이너 네트워크 인터페이스에서 TCP 연결을 받아야 합니다.

```ini
bind-address = 0.0.0.0
```

이 값은 **컨테이너 내부의 모든 IPv4 인터페이스에서 수신한다**는 뜻입니다. 이것만으로 호스트나 인터넷에 포트가 공개되는 것은 아닙니다.

```yaml
services:
  db:
    # ports: 없음
```

Compose에 `ports`가 없다면 일반적으로 다른 컨테이너는 같은 Docker 네트워크를 통해 `db:3306`으로 접근하고, 호스트에는 직접 게시하지 않습니다.

### `skip-name-resolve`

이 옵션을 켜면 클라이언트 IP 주소의 DNS 이름을 역조회하지 않습니다.

```ini
skip-name-resolve
```

따라서 권한의 host 부분도 DNS 이름에 의존하지 않는 형태로 설계해야 합니다. IP 주소, IP 패턴, `%`, `localhost`처럼 이름 해석 없이 평가할 수 있는 구성을 사용합니다.

### `utf8mb4`

```ini
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
```

`utf8mb4`는 BMP 밖의 문자와 이모지를 포함한 전체 UTF-8 범위를 저장할 수 있습니다.

서버 기본값은 **새로 만드는 데이터베이스나 테이블의 기본값에 영향을 주는 설정**입니다. 기존 테이블의 문자 집합과 collation이 자동으로 변환되지는 않습니다. 기존 스키마를 바꾸려면 별도의 `ALTER DATABASE`나 `ALTER TABLE` 등의 마이그레이션이 필요합니다.

### `innodb-buffer-pool-size`

InnoDB buffer pool은 자주 사용하는 데이터와 인덱스 페이지를 메모리에 캐시합니다.

값이 너무 작으면 디스크 읽기가 늘 수 있지만, 컨테이너 메모리 한도에 가깝게 지나치게 크게 설정하면 다음 메모리를 위한 여유가 사라집니다.

```text
buffer pool
+ 연결별 메모리
+ 정렬/임시 버퍼
+ 서버 자체 메모리
+ 같은 컨테이너의 기타 프로세스
```

따라서 호스트 전체 메모리만 보지 말고 **MariaDB 컨테이너에 실제로 허용된 메모리와 워크로드**를 기준으로 조정합니다.

### `max-connections`

`max-connections`는 동시에 유지할 수 있는 클라이언트 연결 수의 상한입니다.

값을 정할 때는 다음을 함께 봅니다.

```text
애플리케이션 인스턴스 수
× 인스턴스당 연결 풀 최대 크기
+ 관리자/점검 연결 여유
≤ MariaDB가 감당할 연결 수
```

연결 하나마다 항상 같은 양의 메모리를 사용하는 것은 아니지만, 연결 수가 많아지면 스레드와 연결별 버퍼 등의 비용도 증가합니다. 느린 쿼리나 과도한 연결 풀이 원인인데 `max-connections`만 키우면 장애가 늦게 나타나거나 메모리 압박이 더 커질 수 있습니다.

## 11. 상태 검사는 깊이를 구분합니다

데이터베이스 상태 검사는 무엇을 확인하려는지에 따라 나눠야 합니다.

### 1단계: 서버 프로세스와 프로토콜 응답 확인

데이터베이스 컨테이너 안에서 다음처럼 확인할 수 있습니다.

```sh
mariadb-admin \
  --protocol=socket \
  --socket=/run/mysqld/mysqld.sock \
  ping --silent
```

이 검사는 MariaDB가 요청에 응답할 수 있는지를 확인합니다.

중요한 점은 `mariadb-admin ping`이 **인증 실패가 발생해도 서버가 살아 있으면 성공으로 끝날 수 있다는 것**입니다. 따라서 사용자 이름과 비밀번호를 붙였다고 해서 인증 상태 검사로 바뀌는 것은 아닙니다.

### 2단계: 실제 인증과 쿼리 확인

애플리케이션이 사용하는 것과 같은 연결 경로와 계정으로 작은 읽기 쿼리를 실행합니다.

```sh
mariadb \
  --host=db \
  --port=3306 \
  --user=appuser \
  --password \
  --database=appdb \
  --execute='SELECT 1;'
```

실제 자동화에서는 대화형 `--password` 입력 대신 권한이 제한된 client option file이나 secret 파일 등으로 비밀번호를 전달합니다.

이 검사는 다음 요소를 함께 확인합니다.

```text
서비스 이름 해석
→ Docker 네트워크
→ TCP 3306
→ MariaDB 프로토콜
→ 사용자 인증
→ 데이터베이스 접근 권한
→ 간단한 SQL 실행
```

애플리케이션의 전체 기능을 확인하려면 여기에 필요한 테이블의 읽기까지 추가할 수 있지만, 상태 검사는 가능한 한 빠르고 읽기 전용이어야 합니다. 주기적인 healthcheck가 스키마를 만들거나 행을 삽입해서는 안 됩니다.

## 12. 재시작, 재생성과 삭제

다음 명령들은 데이터에 미치는 영향이 서로 다릅니다.

```sh
docker compose restart db
docker compose up -d --force-recreate db
docker compose down
docker compose down -v
```

### `restart`

기존 컨테이너를 중지했다가 다시 시작합니다.

```text
같은 컨테이너
+ 같은 볼륨
→ 데이터 유지
```

### `--force-recreate`

서비스 컨테이너를 새로 만들지만 Compose 설정이 같은 이름 있는 볼륨을 연결한다면 데이터는 그대로 사용합니다.

```text
새 컨테이너
+ 기존 named volume
→ 데이터 유지
```

### `docker compose down`

기본적으로 서비스 컨테이너와 Compose 네트워크를 제거하지만 이름 있는 볼륨은 남깁니다.

```text
컨테이너 제거
볼륨 유지
→ 다음 up에서 다시 사용 가능
```

### `docker compose down -v`

Compose 파일에 선언된 이름 있는 볼륨과 연결된 익명 볼륨까지 제거할 수 있습니다.

```text
컨테이너 제거
+ 데이터 볼륨 제거
→ 데이터 삭제
```

`external: true`로 관리되는 외부 볼륨은 Compose 프로젝트가 소유하는 볼륨과 수명 규칙이 다르므로 별도로 관리해야 합니다.

### 기존 볼륨에서 초기화 환경변수를 바꿨을 때

시작 스크립트는 컨테이너가 시작될 때마다 실행되더라도, 이미 초기화된 데이터 디렉터리에서는 **최초 초기화 SQL을 다시 실행하지 않는 설계**가 일반적입니다.

따라서 다음처럼 secret 파일만 바꿔도 기존 DB 계정의 비밀번호가 자동 변경된다고 가정해서는 안 됩니다.

```text
기존 볼륨
+ MARIADB_PASSWORD_FILE 내용 변경
≠ 기존 MariaDB 계정 비밀번호 자동 변경
```

이미 초기화된 환경에서 비밀번호를 회전하려면 명시적인 운영 절차가 필요합니다.

```text
새 비밀값 준비
→ ALTER USER로 DB 계정 변경
→ 애플리케이션이 새 비밀값 사용
→ 연결 재수립/서비스 재시작
→ 이전 비밀값 폐기
```

실제 순서는 애플리케이션이 동시 두 비밀번호를 지원하는지, 무중단 교체가 필요한지에 따라 달라질 수 있습니다.

## 13. 백업과 복원

이름 있는 볼륨은 **컨테이너 교체로부터 데이터 수명을 분리**할 뿐입니다.

다음 상황에는 별도 백업이 필요합니다.

- 호스트 디스크 손상
- 실수로 `DROP TABLE` 실행
- 잘못된 애플리케이션 마이그레이션
- 볼륨 삭제
- 랜섬웨어나 파일 손상
- 잘못된 버전 업그레이드

### 논리 백업

InnoDB 중심 데이터베이스의 예시는 다음과 같습니다.

```sh
docker compose exec -T db \
  mariadb-dump \
  -uappuser \
  --single-transaction \
  --quick \
  --routines \
  --events \
  --triggers \
  appdb > appdb.sql
```

비밀번호는 명령행에 직접 적기보다 권한을 제한한 option file이나 secret 전달 방식을 사용합니다. 명령행 인자는 프로세스 목록, 셸 기록 또는 진단 로그에 노출될 수 있기 때문입니다.

각 옵션의 의미는 다음과 같습니다.

- `--single-transaction`: InnoDB 같은 트랜잭션 테이블을 일관된 스냅샷에서 읽습니다.
- `--quick`: 큰 테이블의 모든 행을 클라이언트 메모리에 한꺼번에 적재하지 않고 순차적으로 읽는 데 유용합니다.
- `--routines`: 저장 프로시저와 함수를 포함합니다.
- `--events`: 이벤트 스케줄러 이벤트를 포함합니다.
- `--triggers`: 트리거를 포함합니다.

`--single-transaction`이 모든 상황에서 완전한 일관성을 보장하는 것은 아닙니다.

```text
InnoDB 등 트랜잭션 테이블
→ 일관된 스냅샷 가능

MyISAM/MEMORY 등 비트랜잭션 테이블
→ 같은 보장 없음

덤프 도중 ALTER TABLE / DROP TABLE / RENAME TABLE 등 DDL
→ 덤프 실패 또는 일관성 문제 가능
```

따라서 실제 스토리지 엔진과 배포 중 DDL 실행 여부를 고려해야 합니다.

### 백업 파일을 원자적으로 공개하기

백업 대상 파일에 바로 쓰다가 실패하면 "완성된 백업처럼 보이는 부분 파일"이 남을 수 있습니다.

```sh
tmp="appdb.sql.tmp"
final="appdb.sql"

if docker compose exec -T db \
    mariadb-dump \
    -uappuser \
    --single-transaction \
    --quick \
    appdb > "$tmp"
then
    mv "$tmp" "$final"
else
    rm -f "$tmp"
    exit 1
fi
```

같은 파일시스템 안에서 `mv`하면 완성된 임시 파일을 최종 이름으로 바꾸는 작업을 원자적으로 처리할 수 있습니다.

### 복원

```sh
docker compose exec -T db \
  mariadb \
  -uappuser \
  appdb < appdb.sql
```

복원 명령이 종료 코드 0으로 끝났다는 사실만으로 복구가 검증된 것은 아닙니다.

가능하면 별도의 빈 환경에 복원한 뒤 다음을 확인합니다.

- 예상 테이블이 모두 존재하는가
- 중요한 테이블의 행 수가 합리적인가
- PK/FK/UNIQUE 같은 제약 조건이 존재하는가
- 뷰, 트리거, routine, event가 필요한 만큼 복원됐는가
- 애플리케이션이 실제 읽기 요청을 처리하는가

> 복원해 보지 않은 백업은 복구 수단으로 검증된 것이 아닙니다.

## 14. 인덱스와 `EXPLAIN`

인덱스가 없으면 조건에 맞는 행을 찾기 위해 많은 행을 읽어야 할 수 있습니다.

예를 들어 다음 쿼리를 확인합니다.

```sql
EXPLAIN
SELECT id, display_name
FROM index_demo
WHERE email = 'user0500@users.local.test';
```

인덱스를 만든 뒤 같은 실행 계획을 다시 비교합니다.

```sql
CREATE UNIQUE INDEX idx_index_demo_email
ON index_demo (email);
```

```sql
EXPLAIN
SELECT id, display_name
FROM index_demo
WHERE email = 'user0500@users.local.test';
```

비교할 항목은 실행 시간 하나가 아닙니다.

- 실제로 선택된 인덱스가 있는가
- 어느 접근 방식으로 테이블을 읽는가
- 읽을 것으로 예상하는 행 수가 얼마나 줄었는가
- 전체 테이블 스캔이 사라졌는가
- 추가 정렬이나 임시 작업이 필요한가

`UNIQUE` 인덱스는 단순 성능 장치이기도 하지만 데이터 제약 조건이기도 합니다.

```sql
CREATE UNIQUE INDEX idx_index_demo_email
ON index_demo (email);
```

이 경우 같은 `email` 값을 가진 두 행을 저장하지 못하게 하므로, 애플리케이션의 데이터 모델이 실제로 `email`의 유일성을 요구할 때 사용해야 합니다.

인덱스에는 비용도 있습니다.

```text
장점
→ 특정 조회가 빨라질 수 있음

비용
→ INSERT/UPDATE/DELETE 시 인덱스도 갱신
→ 디스크 공간 증가
→ 버퍼 풀 사용 증가
→ 백업/복원 대상 증가
```

따라서 "자주 검색할 것 같다"는 추측만으로 추가하지 말고 실제 쿼리, 실행 계획과 데이터 분포를 보고 결정합니다.

## 15. 자주 생기는 오해

### `bind-address = 0.0.0.0`이면 인터넷에 공개됩니다

아닙니다. MariaDB가 **컨테이너 내부의 모든 IPv4 인터페이스에서 연결을 받는다**는 뜻입니다. 호스트 공개 여부는 Docker의 포트 게시 설정과 호스트 네트워크 정책이 별도로 결정합니다.

### `mariadb-admin ping`에 사용자와 비밀번호를 넣었으니 인증까지 검사됩니다

그렇지 않습니다. `ping`은 서버가 살아 있는지 확인하는 명령이며, 인증 오류가 발생해도 서버가 응답하면 성공 종료 코드를 반환할 수 있습니다. 인증과 권한까지 확인하려면 실제 사용자로 `SELECT 1` 같은 쿼리를 실행해야 합니다.

### `mariadb-install-db --auth-root-authentication-method=socket`을 썼지만 바로 root 비밀번호가 필요합니다

socket 인증을 사용하면 로컬 Unix 소켓에서 OS 계정 정보를 이용해 `root@localhost`에 접근할 수 있습니다. 초기 부트스트랩 단계에서 굳이 비밀번호 인증으로 전환하지 않아도 됩니다. 운영 정책상 root 비밀번호 인증이 필요하다면 별도의 명시적인 계정 변경 절차를 추가해야 합니다.

### `CREATE USER`나 `GRANT` 뒤에는 항상 `FLUSH PRIVILEGES`가 필요합니다

`CREATE USER`, `ALTER USER`, `GRANT` 같은 계정 관리 SQL은 변경 사항을 서버에 반영합니다. `FLUSH PRIVILEGES`는 권한 시스템 테이블을 직접 수정한 경우에 필요하며, 일반적인 계정 관리에서는 직접 수정 자체를 피하는 편이 좋습니다.

### 볼륨이 있으므로 백업은 필요 없습니다

볼륨은 컨테이너보다 오래 살 뿐입니다. 호스트 디스크 손상, SQL 실수, 볼륨 삭제에는 보호 장치가 되지 않습니다.

### 연결 수를 늘리면 DB 문제가 해결됩니다

느린 쿼리나 과도한 애플리케이션 연결 풀이 원인이라면 문제를 늦게 드러나게 하거나 메모리 압박을 더 키울 수 있습니다.

### 인덱스는 많을수록 좋습니다

조회 성능뿐 아니라 쓰기 비용, 저장 공간, 버퍼 풀과 백업·복원 비용도 함께 고려해야 합니다.

## 확인 문제

1. MariaDB 컨테이너와 데이터 볼륨의 수명을 분리해야 하는 이유는 무엇입니까?
2. 빈 데이터 디렉터리에 `mariadb-install-db`가 필요한 이유는 무엇입니까?
3. `mysql/` 디렉터리 존재만으로 초기화 완료를 완전히 보장할 수 없는 이유는 무엇입니까?
4. 초기 설정용 MariaDB에서 `--skip-networking`을 사용하는 이유는 무엇입니까?
5. `mariadb-admin ping`과 실제 `SELECT 1` 상태 검사는 무엇이 다릅니까?
6. 임시 서버를 종료한 뒤 `wait`해야 하는 이유는 무엇입니까?
7. `'appuser'@'%'`와 Docker 네트워크 제한은 각각 어떤 계층을 제어합니까?
8. 컨테이너 재생성과 볼륨 삭제는 데이터 결과가 어떻게 다릅니까?
9. 비밀값 파일만 바꿔도 기존 사용자 비밀번호가 자동으로 바뀌지 않는 이유는 무엇입니까?
10. 이름 있는 볼륨과 논리 백업은 각각 어떤 문제를 해결합니까?
11. `--single-transaction`이 비트랜잭션 테이블이나 덤프 중 DDL까지 자동으로 안전하게 만드는 것은 아닌 이유는 무엇입니까?
12. 인덱스를 추가할 때 조회 성능 외에 어떤 비용을 고려해야 합니까?

## 참고 문서

- `mariadb-install-db`: https://mariadb.com/docs/server/clients-and-utilities/deployment-tools/mariadb-install-db
- MariaDB Unix socket 인증: https://mariadb.com/docs/server/reference/plugins/authentication-plugins/authentication-plugin-unix-socket
- MariaDB `CREATE USER`: https://mariadb.com/docs/server/reference/sql-statements/account-management-sql-statements/create-user
- `mariadb-admin`: https://mariadb.com/docs/server/clients-and-utilities/administrative-tools/mariadb-admin
- `mariadb-dump`: https://mariadb.com/docs/server/clients-and-utilities/backup-restore-and-import-clients/mariadb-dump
- MariaDB `EXPLAIN`: https://mariadb.com/docs/server/reference/sql-statements/administrative-sql-statements/analyze-and-explain-statements/explain
- MariaDB 인덱스: https://mariadb.com/docs/server/ha-and-performance/optimization-and-tuning/optimization-and-indexes
- Docker Compose `down`: https://docs.docker.com/reference/cli/docker/compose/down/
- Docker 볼륨: https://docs.docker.com/engine/storage/volumes/
