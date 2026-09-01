# Compose, 네트워크와 저장소

웹 서비스는 여러 프로세스로 구성되는 경우가 많습니다. 외부 요청을 받는 게이트웨이, 애플리케이션 서버, 데이터베이스는 사용하는 프로토콜·실행 권한·재시작 방식·데이터 수명이 서로 다를 수 있습니다.

Docker Compose는 이런 여러 컨테이너와 그에 필요한 네트워크·볼륨·설정을 하나의 Compose 파일에 **선언**하고, 하나의 프로젝트 단위로 관리할 수 있게 합니다.

Compose 문법을 외우기 전에 다음 세 가지를 먼저 구분해야 합니다.

```text
어떤 서비스가 어떤 서비스와 통신하는가?
→ 어느 네트워크와 포트를 사용하는가?
→ 어떤 데이터가 컨테이너보다 오래 남아야 하는가?
```

이 장에서는 이 세 질문을 기준으로 Compose의 네트워크와 저장소를 이해합니다.

---

## 1. 서비스를 나누는 기준

Compose의 `services` 아래에는 보통 서로 독립적으로 실행하고 관리할 필요가 있는 구성 요소를 서비스로 정의합니다.

프로세스를 별도 서비스나 컨테이너로 나눌지 판단할 때는 다음을 확인합니다.

- 독립적으로 시작·중지·재시작·교체할 필요가 있습니까?
- 사용하는 프로토콜과 포트가 다릅니까?
- 외부에 노출해야 하는 범위가 다릅니까?
- 실행 사용자나 필요한 권한이 다릅니까?
- 저장하는 데이터의 수명이 다릅니까?
- 로그와 장애 상태를 별도로 관찰할 필요가 있습니까?
- 다른 구성 요소와 독립적으로 확장할 필요가 있습니까?

모든 프로세스를 기계적으로 하나씩 컨테이너로 나누면 설정과 운영이 불필요하게 복잡해질 수 있습니다.

반대로 Nginx, PHP-FPM, MariaDB처럼 역할과 데이터 수명이 명확히 다른 프로세스를 하나의 컨테이너에서 함께 관리하면 다음 문제가 생기기 쉽습니다.

```text
어느 프로세스가 실패했는지 판단하기 어려움
하나만 재시작하거나 교체하기 어려움
로그와 종료 상태가 섞임
서로 다른 권한을 분리하기 어려움
데이터 저장소와 애플리케이션 수명을 분리하기 어려움
```

중요한 기준은 “프로세스 하나당 무조건 컨테이너 하나”가 아니라 **독립적인 수명과 책임을 가진 실행 단위인가**입니다.

---

## 2. Compose가 대신하는 수동 작업

두 컨테이너를 직접 연결하려면 네트워크를 만들고, 각 컨테이너를 그 네트워크에 연결하고, 이름과 명령을 지정해야 합니다.

예를 들어 수동으로 실행하면 다음과 비슷합니다.

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

Compose에서는 필요한 상태를 파일에 선언할 수 있습니다.

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

그리고 다음처럼 실행합니다.

```sh
docker compose up
```

Compose 파일은 명령을 위에서 아래로 한 줄씩 실행하는 셸 스크립트가 아닙니다.

다음과 같은 **원하는 상태(desired state)** 를 선언하는 파일에 가깝습니다.

```text
app 서비스가 존재해야 함
client 서비스가 존재해야 함
둘 다 app-net에 연결되어야 함
```

`docker compose up`은 현재 프로젝트 상태와 선언을 비교해 필요한 컨테이너·네트워크·볼륨을 생성하거나 다시 만듭니다.

따라서 YAML에 서비스가 먼저 적혔다고 해서 그 순서만으로 애플리케이션 준비 완료 시점까지 보장되는 것은 아닙니다. 서비스 간 시작 의존성은 뒤에서 다루는 `depends_on`과 상태 검사를 사용해 표현합니다.

---

## 3. 프로젝트와 기본 네트워크

Compose는 관련 자원을 **프로젝트(project)** 단위로 묶습니다.

프로젝트 이름은 일반적으로 다음과 같은 자원 이름에 반영됩니다.

```text
<project>_default
<project>_db-data
<project>-app-1
```

정확한 실제 이름은 Compose 버전, 설정, 명시적 `name` 지정 등에 따라 달라질 수 있으므로 이름 형식 자체에 의존하는 코드를 작성하지 않습니다.

### 기본 네트워크

Compose 파일에서 별도의 네트워크를 선언하지 않아도 Compose는 일반적으로 프로젝트용 기본 네트워크를 하나 만들고 서비스를 연결합니다.

예를 들어 다음 파일은:

```yaml
services:
  app:
    image: app-image

  db:
    image: mariadb:11
```

개념적으로 다음과 비슷합니다.

```yaml
services:
  app:
    image: app-image
    networks:
      - default

  db:
    image: mariadb:11
    networks:
      - default

networks:
  default:
```

두 서비스가 같은 기본 네트워크에 있으므로 `app`은 `db`라는 서비스 이름을 통해 데이터베이스를 찾을 수 있습니다.

즉, 단순한 Compose 프로젝트에서는 네트워크를 직접 선언하지 않아도 서비스 간 통신이 가능합니다.

반대로 특정 서비스에 명시적으로 서로 다른 네트워크만 연결하면 공통 네트워크가 없는 서비스끼리는 직접 통신할 수 없습니다.

---

## 4. 서비스 이름과 내부 DNS

같은 Compose 네트워크에 연결된 서비스는 일반적으로 **서비스 이름**으로 서로를 찾을 수 있습니다.

예를 들어 다음과 같은 서비스가 있다고 가정합니다.

```yaml
services:
  app:
    image: app-image

  db:
    image: mariadb:11
```

`app` 컨테이너에서는 데이터베이스 주소를 다음처럼 사용할 수 있습니다.

```text
db:3306
```

게이트웨이와 애플리케이션이 다음과 같은 구조라면:

```text
gateway → app:9000
app     → db:3306
```

설정에는 컨테이너의 고정 IP 대신 서비스 이름을 사용합니다.

```text
피할 값: 172.19.0.4
사용할 값: db
```

컨테이너를 다시 만들면 새 IP 주소를 받을 수 있습니다. 그러나 서비스 이름은 Compose 선언에 남아 있으므로 내부 DNS가 현재 컨테이너 주소를 다시 알려 줄 수 있습니다.

### 이름 해석과 기존 연결은 다른 문제

DNS가 새 IP를 반환한다고 해서 **이미 열린 TCP 연결이 자동으로 새 컨테이너에 연결되는 것은 아닙니다.**

예를 들어:

```text
app ───── 기존 TCP 연결 ─────▶ db(old)
```

`db`가 다시 만들어지면:

```text
app                    db(old) 종료
                         ✕
                       db(new)
```

기존 연결은 끊길 수 있습니다.

애플리케이션이 새 연결을 만들 때 다시 `db` 이름을 해석하면 새 IP를 얻을 수 있지만, 그 전에 다음 처리가 필요할 수 있습니다.

```text
연결 끊김 감지
→ 실패한 요청 처리
→ 필요하면 제한적으로 재시도
→ 새 연결 생성
```

따라서 **서비스 이름 DNS는 주소 발견 문제를 해결하지만 실행 중 연결 복구까지 대신하지는 않습니다.**

---

## 5. 내부 포트와 공개 포트

Compose에서 가장 자주 혼동하는 부분 중 하나가 **컨테이너 내부 포트**와 **호스트에 게시된 포트**입니다.

같은 Compose 네트워크의 서비스끼리는 보통 컨테이너가 실제로 수신하는 내부 포트로 통신합니다.

```text
gateway → app:9000
app     → db:3306
```

이 통신에는 일반적으로 호스트 포트 게시가 필요하지 않습니다.

### `ports`

호스트 또는 Docker 네트워크 밖의 클라이언트가 컨테이너 서비스에 접근해야 할 때 `ports`를 사용합니다.

```yaml
services:
  gateway:
    ports:
      - "127.0.0.1:19443:443"
```

의미는 다음과 같습니다.

```text
호스트 127.0.0.1:19443
          │
          ▼
gateway 컨테이너의 443
```

따라서 관점에 따라 주소가 달라집니다.

```text
같은 Compose 네트워크의 서비스
→ gateway:443

Docker 호스트에서 실행한 클라이언트
→ 127.0.0.1:19443
```

`19443`은 호스트 쪽 포트이고, `443`은 컨테이너 쪽 포트입니다.

### 데이터베이스는 보통 게시할 필요가 없습니다

예를 들어 데이터베이스가 컨테이너 안에서 `0.0.0.0:3306`에 바인드되어 있어도:

```yaml
services:
  db:
    image: mariadb:11
```

`ports`를 선언하지 않았다면 Compose 네트워크 외부의 호스트 포트로 자동 게시되는 것은 아닙니다.

애플리케이션은 같은 네트워크에서 다음처럼 연결할 수 있습니다.

```text
db:3306
```

호스트나 외부 클라이언트가 직접 접근할 필요가 없다면 데이터베이스 포트를 게시하지 않는 편이 공격 표면을 줄이는 데 도움이 됩니다.

개발 목적으로 호스트에 게시해야 한다면 가능하면 필요한 인터페이스에만 제한합니다.

```yaml
ports:
  - "127.0.0.1:13306:3306"
```

이렇게 하면 일반적으로 호스트의 루프백 인터페이스를 통해서만 접근하도록 제한할 수 있습니다.

### `expose`와 `ports`

Compose의 `expose`는 컨테이너가 사용하는 포트를 서비스 메타데이터로 표현할 수 있지만, 호스트에 포트를 게시하지 않습니다.

```yaml
services:
  app:
    expose:
      - "9000"
```

같은 네트워크의 컨테이너가 `app:9000`으로 통신하기 위해 반드시 `expose`가 필요한 것은 아닙니다. 실제 서버가 해당 포트에서 수신 중이고 네트워크가 연결되어 있으면 통신할 수 있습니다.

따라서 핵심 차이는 다음과 같습니다.

```text
서비스 내부 통신
→ 서비스 이름 + 컨테이너 포트

호스트에서 접근
→ ports로 게시한 호스트 주소 + 호스트 포트
```

---

## 6. 사용자 정의 브리지 네트워크

Compose의 기본 네트워크만으로도 단순한 서비스는 충분하지만, 통신 관계를 제한하거나 구조를 명확히 표현하고 싶다면 여러 네트워크를 정의할 수 있습니다.

예를 들어:

```yaml
services:
  gateway:
    image: gateway-image
    networks:
      - frontend

  app:
    image: app-image
    networks:
      - frontend
      - backend

  db:
    image: mariadb:11
    networks:
      - backend

networks:
  frontend:
  backend:
```

구조는 다음과 같습니다.

```text
frontend network
gateway ───────▶ app

backend network
                 app ───────▶ db
```

`gateway`와 `db`는 공통 네트워크가 없으므로 서비스 이름을 이용한 직접 통신 경로가 만들어지지 않습니다.

이 구조는 통신 관계를 다음처럼 제한합니다.

```text
gateway → app   가능
app → db        가능
gateway → db    공통 네트워크 없음
```

### 네트워크 분리는 보안의 한 층일 뿐입니다

Docker 네트워크를 나눈다고 해서 완전한 보안이 자동으로 생기는 것은 아닙니다.

별도로 고려해야 할 항목이 있습니다.

- 애플리케이션 인증과 인가
- 데이터베이스 계정과 권한
- 호스트 방화벽
- Docker 데몬 접근 권한
- 컨테이너 실행 권한
- 호스트에 게시한 포트
- TLS 같은 전송 보안

네트워크 분리는 **불필요한 직접 통신 경로를 줄이는 수단**으로 이해하는 것이 좋습니다.

---

## 7. 컨테이너의 저장 방식

컨테이너에서 파일이 보인다고 해서 모두 같은 수명을 가지는 것은 아닙니다.

대표적인 저장 방식은 다음 네 가지로 구분할 수 있습니다.

```text
컨테이너 쓰기 가능 계층
이름 있는 볼륨
바인드 마운트
tmpfs
```

### 컨테이너 쓰기 가능 계층

이미지의 읽기 전용 계층 위에 컨테이너별 쓰기 가능 계층이 존재합니다.

별도 마운트가 없는 경로에 파일을 쓰면 일반적으로 이 계층에 저장됩니다.

```text
이미지 읽기 전용 계층
        +
컨테이너 쓰기 가능 계층
```

컨테이너가 삭제되면 이 쓰기 계층도 함께 사라집니다.

따라서 다음과 같은 데이터에 적합합니다.

- 다시 만들어도 되는 캐시
- 임시 생성물
- 컨테이너 수명과 함께 사라져도 되는 파일

반대로 데이터베이스 파일처럼 컨테이너를 교체해도 남아야 하는 데이터에는 적합하지 않습니다.

### 이름 있는 볼륨

이름 있는 볼륨(named volume)은 Docker가 관리하는 영속 저장소입니다.

```yaml
services:
  db:
    image: mariadb:11
    volumes:
      - db-data:/var/lib/mysql

volumes:
  db-data:
```

여기서:

```text
db-data
```

는 Compose에서 관리하는 볼륨이고:

```text
/var/lib/mysql
```

은 컨테이너 안에서 그 볼륨이 보이는 경로입니다.

볼륨의 수명은 특정 컨테이너의 수명과 분리됩니다.

```text
db 컨테이너 삭제
→ db-data 볼륨은 기본적으로 남을 수 있음

새 db 컨테이너 생성
→ 같은 db-data 볼륨 연결
→ 기존 데이터 사용
```

따라서 “데이터베이스 컨테이너를 다시 만들었는데 데이터가 남아 있다”는 것은 정상적인 동작일 수 있습니다.

### 바인드 마운트

바인드 마운트(bind mount)는 호스트의 특정 파일이나 디렉터리를 컨테이너 경로에 직접 연결합니다.

```yaml
services:
  app:
    volumes:
      - type: bind
        source: ./public
        target: /var/www/html
        read_only: true
```

이 경우:

```text
호스트 ./public
      │
      ▼
컨테이너 /var/www/html
```

개발 중 소스 변경을 즉시 반영하거나 호스트에서 직접 관리해야 하는 파일을 연결할 때 편리합니다.

하지만 호스트 환경에 더 강하게 의존합니다.

예를 들어 다음 차이가 문제가 될 수 있습니다.

- 호스트 디렉터리 구조
- 운영체제별 파일 공유 방식
- UID/GID
- 파일 권한
- SELinux 같은 보안 정책

운영 데이터를 저장할 때는 이런 특성을 고려하여 이름 있는 볼륨이나 외부 저장소와 비교해야 합니다.

### tmpfs

`tmpfs`는 메모리 기반 임시 파일 시스템입니다.

```yaml
services:
  app:
    tmpfs:
      - /run/app-tmp
```

컨테이너가 중지되거나 해당 마운트가 사라지면 내용이 유지되지 않습니다.

다음처럼 **영속성이 필요하지 않고 디스크에 남기고 싶지 않은 런타임 임시 파일**에 사용할 수 있습니다.

```text
임시 작업 파일
프로세스 런타임 파일
짧은 수명의 민감 데이터 복사본
```

중요한 데이터를 tmpfs에 저장하면 재시작 후 사라집니다.

---

## 8. 볼륨을 마운트할 때 기존 파일은 어떻게 되는가

마운트는 단순히 “추가 디렉터리가 하나 생기는 것”과 다릅니다.

예를 들어 이미지 안에 다음 파일이 있다고 가정합니다.

```text
/app/data/default.txt
```

그런데 `/app/data`에 볼륨을 마운트하면 마운트가 활성화된 동안 이미지의 기존 `/app/data` 내용은 그 경로에서 직접 보이지 않고 **마운트된 저장소의 내용이 대신 보입니다.**

```text
이미지의 /app/data
        ↓ 마운트
볼륨의 /app/data 내용이 보임
```

새 빈 볼륨을 컨테이너의 기존 데이터가 있는 경로에 처음 마운트할 때 Docker가 기존 내용을 볼륨에 복사하는 동작이 발생할 수도 있습니다.

따라서 “이미지에 파일을 넣었는데 실행 컨테이너에서 안 보인다”는 문제를 만났다면 해당 경로에 볼륨이나 바인드 마운트가 덮여 있는지 확인해야 합니다.

---

## 9. `down`과 볼륨 삭제

Compose 프로젝트를 내릴 때 가장 중요한 것은 **컨테이너 제거와 데이터 제거를 같은 작업으로 생각하지 않는 것**입니다.

### 기본 `down`

```sh
docker compose down
```

기본적으로 Compose가 만든 서비스 컨테이너와 프로젝트 네트워크를 제거합니다.

Compose 파일에서 선언한 이름 있는 볼륨은 기본적으로 제거하지 않습니다.

따라서:

```text
docker compose down
docker compose up
```

을 수행하면 컨테이너는 새로 만들어져도 같은 이름 있는 볼륨을 다시 연결해 기존 데이터를 사용할 수 있습니다.

### `down -v`

```sh
docker compose down -v
```

또는:

```sh
docker compose down --volumes
```

는 Compose 파일의 `volumes`에 선언된 이름 있는 볼륨과 컨테이너에 붙은 익명 볼륨을 제거할 수 있습니다.

따라서 데이터베이스 초기화 의도가 없다면 신중하게 사용해야 합니다.

### 외부 볼륨

외부에서 이미 만들어진 볼륨을 Compose에 연결할 수도 있습니다.

```yaml
volumes:
  db-data:
    external: true
```

이런 외부 볼륨은 Compose 프로젝트의 수명 밖에서 관리되는 자원입니다. `docker compose down -v`로도 Compose가 외부 볼륨 자체를 제거하지 않습니다.

즉, 볼륨은 다음처럼 구분해야 합니다.

```text
Compose가 관리하는 이름 있는 볼륨
외부(external) 볼륨
익명 볼륨
```

### 작업별 수명 비교

일반적인 이름 있는 Compose 볼륨을 기준으로 보면 다음과 같습니다.

| 작업 | 서비스 컨테이너 | Compose 이름 있는 볼륨 |
|---|---|---|
| `docker compose restart` | 같은 컨테이너를 재시작 | 유지 |
| `docker compose up --force-recreate` | 교체 | 유지 |
| `docker compose down` 후 `up` | 새로 생성 | 유지 |
| `docker compose down -v` 후 `up` | 새로 생성 | 제거 후 새로 생성될 수 있음 |

따라서 **재배포와 데이터 삭제를 같은 작업으로 취급하면 안 됩니다.**

데이터 삭제 명령을 실행하기 전에는 어떤 볼륨이 대상인지 반드시 확인합니다.

```sh
docker volume ls
docker compose config
```

---

## 10. 설정, 비밀값과 데이터

애플리케이션이 사용하는 모든 값을 같은 방식으로 저장하면 관리하기 어려워집니다.

다음 세 범주를 구분합니다.

| 종류 | 예 | 일반적인 전달·저장 방식 | 일반적인 수명 |
|---|---|---|---|
| 설정 | 포트, 로그 수준, 서비스 주소 | 환경변수, 설정 파일 | 배포와 함께 변경 |
| 비밀값 | DB 비밀번호, API 키, 개인키 | 제한된 파일, Compose secret, 외부 비밀 관리 시스템 | 별도 회전 필요 |
| 데이터 | DB 파일, 사용자 업로드 | 볼륨, 객체 저장소, 외부 DB | 컨테이너보다 오래 유지 |

### 설정

설정은 환경마다 달라질 수 있지만 공개되어도 즉시 자격 증명이 되는 값은 아닙니다.

예:

```text
APP_PORT=8080
LOG_LEVEL=info
DB_HOST=db
```

### 비밀값

다음 값은 소스 코드나 이미지에 직접 넣지 않습니다.

```text
DB_PASSWORD
API_TOKEN
TLS_PRIVATE_KEY
```

특히 Dockerfile의 `ENV`에 비밀값을 넣으면 이미지 설정과 빌드 산출물에 남을 수 있습니다.

실제 비밀 파일은 Git에서 제외하고, 저장소에는 `.example` 파일이나 생성 절차만 두는 방식이 일반적입니다.

### 사용자 데이터

데이터베이스 파일이나 사용자 업로드는 애플리케이션 컨테이너와 독립적인 수명이 필요한 경우가 많습니다.

컨테이너를 새 버전으로 교체하는 것과 사용자 데이터를 삭제하는 것은 완전히 다른 작업이어야 합니다.

---

## 11. Compose secrets

Compose는 서비스에 비밀값을 **파일 형태**로 제공할 수 있습니다.

예를 들어:

```yaml
services:
  app:
    image: app-image
    secrets:
      - db_password
    environment:
      DB_PASSWORD_FILE: /run/secrets/db_password

secrets:
  db_password:
    file: ./secrets/db_password.txt
```

서비스 내부에서는 일반적으로 다음 경로로 접근할 수 있습니다.

```text
/run/secrets/db_password
```

중요한 점은 최상위 `secrets`에 정의했다고 해서 모든 서비스가 자동으로 읽을 수 있는 것이 아니라는 점입니다.

서비스가 사용하려면 해당 서비스의 `secrets`에도 명시적으로 부여해야 합니다.

```yaml
services:
  app:
    secrets:
      - db_password
```

### `_FILE` 변수는 애플리케이션 기능입니다

다음 설정을 보겠습니다.

```yaml
environment:
  DB_PASSWORD_FILE: /run/secrets/db_password
```

Compose가 `DB_PASSWORD_FILE`이라는 이름을 특별히 해석하여 자동으로 파일을 읽어 비밀번호를 전달하는 것은 아닙니다.

애플리케이션이나 이미지의 시작 스크립트가 이런 `_FILE` 관례를 지원해야 합니다.

예를 들어 일부 공식 데이터베이스 이미지는 다음과 같은 변수를 지원합니다.

```text
MYSQL_ROOT_PASSWORD_FILE
MYSQL_PASSWORD_FILE
```

직접 만든 애플리케이션이라면 프로그램에서 `/run/secrets/db_password` 파일을 읽는 코드를 작성해야 합니다.

### Compose secret이 해결하지 않는 것

파일 기반 secret은 다음 위험을 줄이는 데 도움이 됩니다.

```text
Dockerfile에 비밀값 포함
일반 환경변수에 평문 비밀값 전달
모든 서비스에 불필요하게 비밀값 전달
```

그러나 다음 문제를 자동으로 해결하지는 않습니다.

- 원본 호스트 파일의 권한
- 누가 Docker 호스트에 접근할 수 있는지
- 비밀값 회전 정책
- 애플리케이션이 비밀값을 로그에 출력하는 문제
- 백업과 배포 시스템의 비밀값 보호

즉, Compose secret은 **비밀 관리 전체가 아니라 전달 방법의 한 부분**입니다.

---

## 12. Compose 변수 보간

Compose는 YAML 파일을 해석할 때 호스트 환경변수나 Compose가 읽는 환경 파일의 값을 사용해 문자열을 보간할 수 있습니다.

예를 들어:

```yaml
services:
  gateway:
    ports:
      - "127.0.0.1:${TLS_PORT:-19443}:443"
```

주요 형식은 다음과 같습니다.

```text
${VAR}
${VAR:-default}
${VAR:?message}
```

의미는 다음과 같습니다.

- `${VAR}`: 변수 값을 사용합니다.
- `${VAR:-default}`: 변수가 설정되지 않았거나 비어 있으면 `default`를 사용합니다.
- `${VAR:?message}`: 필요한 값이 없거나 비어 있으면 오류를 내고 `message`를 표시합니다.

예:

```yaml
environment:
  DB_HOST: ${DB_HOST:-db}
  DB_USER: ${DB_USER:?DB_USER is required}
```

### 보간과 컨테이너 환경변수는 다른 단계입니다

다음 두 개념을 반드시 구분해야 합니다.

```text
Compose 변수 보간
→ compose.yaml을 해석할 때 사용

services.<name>.environment
→ 최종 컨테이너 프로세스의 환경에 값을 전달
```

예를 들어 `.env`에 값이 있다고 해서 모든 값이 자동으로 컨테이너 환경에 들어가는 것은 아닙니다.

컨테이너에 전달하려면 `environment`나 `env_file` 같은 서비스 설정을 통해 명시해야 합니다.

렌더링된 설정은 다음 명령으로 확인할 수 있습니다.

```sh
docker compose config
```

문법과 설정을 검사하고 결과를 출력하지 않으려면 다음을 사용할 수 있습니다.

```sh
docker compose config --quiet
```

`docker compose config` 결과에는 보간된 값이 포함될 수 있으므로 비밀값이 사용되는 환경에서는 공유 로그에 그대로 남기지 않도록 주의합니다.

---

## 13. 실행 중과 준비 완료

컨테이너가 Docker에서 `running` 상태라는 것은 기본적으로 **컨테이너의 주 프로세스가 아직 종료되지 않았다는 뜻**입니다.

서비스가 실제 요청을 처리할 준비가 끝났다는 뜻은 아닙니다.

예를 들어 데이터베이스 프로세스가 시작된 뒤에도 다음 초기화가 필요할 수 있습니다.

```text
데이터 파일 검사
복구 로그 적용
소켓 생성
네트워크 포트 수신 시작
사용자·스키마 초기화
```

따라서 다음 상태를 구분해야 합니다.

```text
컨테이너 프로세스가 실행 중
≠
서비스가 실제 요청을 처리할 준비가 됨
```

### `healthcheck`

Compose에서 컨테이너 상태 검사를 정의할 수 있습니다.

```yaml
services:
  app:
    healthcheck:
      test: ["CMD", "python", "/app/healthcheck.py"]
      interval: 5s
      timeout: 2s
      retries: 10
      start_period: 5s
```

주요 항목은 다음과 같습니다.

- `test`: 실행할 검사 명령
- `interval`: 검사 간격
- `timeout`: 한 번의 검사를 기다리는 최대 시간
- `retries`: 연속 실패 후 unhealthy로 판단하기 위한 횟수
- `start_period`: 시작 직후 초기화 시간을 고려하는 유예 구간

좋은 상태 검사는 다음 조건을 만족하는 편이 좋습니다.

- 짧은 시간 안에 끝납니다.
- 명확한 제한 시간이 있습니다.
- 반복 실행해도 상태를 변경하지 않습니다.
- 서비스가 실제 사용하는 프로토콜이나 핵심 기능을 확인합니다.
- 검사 범위가 명확합니다.
- 외부 장애 하나 때문에 불필요하게 자기 서비스까지 unhealthy가 되지 않도록 범위를 조절합니다.

예를 들어 프로세스 이름만 확인하면 다음 고장을 놓칠 수 있습니다.

```text
프로세스는 존재함
하지만 포트 수신 실패
```

반대로 상태 검사에 매우 무거운 DB 쿼리나 외부 인터넷 요청을 넣으면 상태 검사 자체가 부하나 오탐의 원인이 될 수 있습니다.

---

## 14. `depends_on`

서비스 시작 순서를 표현할 때 `depends_on`을 사용할 수 있습니다.

짧은 형식은 다음과 같습니다.

```yaml
services:
  app:
    depends_on:
      - db
```

이 설정은 Compose가 의존 서비스를 먼저 시작하도록 순서를 정하는 데 사용됩니다.

그러나 **프로세스가 시작되었다는 것과 서비스가 준비되었다는 것은 다릅니다.**

### `service_healthy`

데이터베이스가 상태 검사를 통과할 때까지 기다린 뒤 애플리케이션을 시작하려면 다음처럼 정의할 수 있습니다.

```yaml
services:
  app:
    image: app-image
    depends_on:
      db:
        condition: service_healthy

  db:
    image: mariadb:11
    healthcheck:
      test: ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 10s
```

여기서 핵심은:

```text
db 컨테이너 생성·시작
→ db healthcheck 통과
→ app 시작
```

입니다.

실제 상태 검사 명령은 사용하는 이미지가 제공하는 도구와 버전에 맞게 선택해야 합니다.

### `service_completed_successfully`

한 번 실행되고 정상 종료되어야 하는 초기화 작업이나 마이그레이션 서비스에는 `service_completed_successfully`를 사용할 수 있습니다.

개념적으로:

```yaml
services:
  app:
    depends_on:
      migrate:
        condition: service_completed_successfully
```

처럼 “이 서비스가 성공적으로 끝난 뒤 다음 서비스를 시작한다”는 의존성을 표현할 수 있습니다.

### `depends_on`이 해결하지 않는 문제

`depends_on`과 `service_healthy`는 **시작 시점의 의존성 조정**에 유용합니다.

하지만 다음 상황까지 애플리케이션 대신 해결하지는 않습니다.

- 실행 중 데이터베이스 프로세스가 재시작됨
- 기존 TCP 연결이 끊어짐
- 네트워크가 일시적으로 단절됨
- 비밀번호가 잘못됨
- 권한이 부족함
- 데이터베이스 쿼리가 실패함
- 외부 서비스가 장애 상태가 됨

따라서 다음 두 문제를 분리해야 합니다.

```text
시작 시점 준비 순서
→ Compose의 depends_on + healthcheck

실행 중 장애 복구
→ 애플리케이션의 연결 관리, 제한된 재시도, 오류 처리
```

---

## 15. 재시작 설정

Compose 서비스에 재시작 정책을 지정할 수 있습니다.

```yaml
services:
  app:
    restart: unless-stopped
```

재시작 정책은 프로세스가 비정상 종료된 뒤 다시 시작하는 데 도움을 줄 수 있습니다.

하지만 다음과 같은 **영구적인 설정 오류**를 고쳐 주지는 않습니다.

```text
잘못된 DB 비밀번호
존재하지 않는 설정 파일
권한 오류
잘못된 포트
프로그램 시작 즉시 발생하는 예외
```

이런 상태에서 자동 재시작만 설정하면 다음이 반복될 수 있습니다.

```text
시작
→ 즉시 실패
→ 재시작
→ 즉시 실패
→ ...
```

이를 흔히 restart loop 또는 crash loop라고 부릅니다.

따라서 반복 재시작 중에는 컨테이너 상태뿐 아니라 **최초 실패 원인이 담긴 로그**를 확인해야 합니다.

```sh
docker compose ps -a
docker compose logs app
```

### `depends_on`의 `restart`와 서비스 `restart`는 다릅니다

긴 형식의 `depends_on`에는 다음처럼 `restart: true`를 둘 수도 있습니다.

```yaml
depends_on:
  db:
    condition: service_healthy
    restart: true
```

이 `restart`는 서비스 자체의 일반 재시작 정책인:

```yaml
restart: unless-stopped
```

과 같은 의미가 아닙니다.

의존성의 `restart: true`는 Compose가 의존 서비스를 명시적인 Compose 작업으로 업데이트하거나 재시작할 때 의존하는 서비스도 다시 시작하도록 연결하는 설정입니다.

따라서 두 위치의 `restart`를 혼동하지 않아야 합니다.

---

## 16. 주요 명령

Compose 프로젝트를 진단할 때 자주 사용하는 명령은 다음과 같습니다.

### 설정 확인

```sh
docker compose config --quiet
```

Compose 파일이 유효하게 해석되는지 확인합니다.

렌더링된 전체 설정을 보고 싶다면:

```sh
docker compose config
```

을 사용합니다.

### 이미지 빌드

```sh
docker compose build
```

`build`가 정의된 서비스 이미지를 빌드합니다.

### 서비스 시작

```sh
docker compose up -d
```

`-d`는 서비스를 백그라운드(detached mode)로 실행합니다.

### 상태 확인

```sh
docker compose ps
docker compose ps -a
```

`-a`를 사용하면 종료된 서비스 컨테이너도 함께 확인할 수 있습니다.

### 로그 확인

```sh
docker compose logs -f app
```

`-f`는 새 로그를 계속 따라갑니다.

### 실행 중 컨테이너 안에서 명령 실행

```sh
docker compose exec app ps -ef
```

`exec`는 이미 실행 중인 서비스 컨테이너 안에서 추가 명령을 실행합니다.

### 서비스 중지

```sh
docker compose stop
```

서비스 컨테이너를 중지하지만 기본적으로 컨테이너를 삭제하지는 않습니다.

다시 시작할 수 있습니다.

```sh
docker compose start
```

### 프로젝트 내리기

```sh
docker compose down
```

서비스 컨테이너와 Compose가 관리하는 프로젝트 네트워크 등을 제거합니다.

볼륨까지 제거하려면:

```sh
docker compose down -v
```

를 사용하지만, 영속 데이터가 삭제될 수 있으므로 의도를 확인한 뒤 실행합니다.

---

## 17. 단계별 진단 방법

Compose 서비스가 연결되지 않을 때는 한 번에 모든 설정을 바꾸기보다 계층별로 확인합니다.

예를 들어 `gateway → app → db` 구조라면 다음 순서로 좁힐 수 있습니다.

### 1단계: Compose 파일이 유효한가

```sh
docker compose config --quiet
```

### 2단계: 필요한 컨테이너가 실행 중인가

```sh
docker compose ps -a
```

### 3단계: 실패한 서비스 로그는 무엇인가

```sh
docker compose logs app
docker compose logs db
```

### 4단계: 서비스가 같은 네트워크에 있는가

```sh
docker inspect <container>
docker network ls
docker network inspect <network>
```

### 5단계: 서비스 이름이 해석되는가

예를 들어 `app` 안에서:

```sh
getent hosts db
```

이미지에 `getent`가 없는 경우 다른 진단 도구를 사용해야 합니다.

### 6단계: 대상 내부 포트에 연결할 수 있는가

```text
app → db:3306
```

처럼 **호스트에 게시한 포트가 아니라 대상 컨테이너의 실제 내부 포트**를 확인합니다.

### 7단계: 프로토콜 수준 요청이 성공하는가

단순 TCP 연결만 확인하지 말고 실제 서비스 프로토콜로 확인합니다.

예:

```text
HTTP → HTTP 요청과 상태 코드
MariaDB → DB 클라이언트 또는 이미지 제공 healthcheck
Redis → redis-cli ping
```

이렇게 계층을 나누면 “컨테이너가 떠 있는데 연결이 안 된다” 같은 모호한 문제를 더 구체적인 실패 지점으로 바꿀 수 있습니다.

---

## 18. 자주 생기는 오해

### “같은 Compose 파일의 서비스는 항상 서로 통신할 수 있습니다”

기본 설정에서는 네트워크를 따로 지정하지 않은 서비스들이 Compose의 기본 네트워크에 함께 연결되므로 서비스 이름으로 통신할 수 있습니다.

하지만 명시적으로 네트워크를 나누면 달라집니다.

```yaml
services:
  a:
    networks: [net-a]

  b:
    networks: [net-b]
```

`a`와 `b`는 공통 네트워크가 없으므로 직접 통신할 수 없습니다.

정확한 기준은 **같은 Compose 파일에 있는가**가 아니라 **공통 네트워크가 있는가**입니다.

### “서비스 간 통신에도 `ports`가 필요합니다”

아닙니다.

같은 Compose 네트워크의 서비스끼리는 보통 다음처럼 연결합니다.

```text
db:3306
app:9000
```

`ports`는 주로 호스트 또는 Docker 네트워크 밖에서 컨테이너에 접근할 수 있도록 포트를 게시할 때 필요합니다.

### “`depends_on`이면 데이터베이스 쿼리가 반드시 성공합니다”

아닙니다.

짧은 `depends_on`은 서비스 시작 순서를 정하는 데 사용됩니다.

`condition: service_healthy`를 사용하면 시작 시점에 데이터베이스의 healthcheck 통과를 기다릴 수 있지만, 실행 중 데이터베이스 재시작이나 연결 끊김까지 자동으로 복구해 주지는 않습니다.

### “`running`이면 서비스가 준비되었습니다”

아닙니다.

`running`은 컨테이너 주 프로세스가 살아 있다는 뜻입니다.

실제 요청을 처리할 준비가 되었는지는 healthcheck나 프로토콜 수준 요청으로 별도로 확인해야 합니다.

### “`down`은 모든 데이터를 지웁니다”

아닙니다.

기본 `docker compose down`은 Compose의 이름 있는 볼륨을 보통 유지합니다.

Compose가 관리하는 볼륨까지 제거하려면:

```sh
docker compose down -v
```

를 사용합니다.

또한 `external: true`로 선언한 외부 볼륨은 Compose가 제거하지 않습니다.

### “비밀값 파일을 쓰면 비밀 관리가 끝납니다”

아닙니다.

Compose secret은 일반 환경변수나 이미지에 비밀값을 직접 넣지 않도록 전달 경로를 개선합니다.

하지만 다음은 별도로 관리해야 합니다.

```text
원본 파일 권한
Docker 호스트 접근 권한
비밀값 회전
로그 노출 방지
백업 보안
```

### “`.env`에 적은 값은 모두 컨테이너 환경변수가 됩니다”

아닙니다.

Compose가 `.env`의 값을 YAML 변수 보간에 사용할 수 있는 것과 컨테이너 프로세스에 환경변수를 전달하는 것은 다른 단계입니다.

컨테이너에 전달하려면 `environment`나 `env_file` 같은 설정이 필요합니다.

### “서비스 이름의 IP가 바뀌어도 기존 연결은 자동으로 새 서버로 이동합니다”

아닙니다.

DNS는 새 연결을 만들 때 새 주소를 찾는 데 도움을 줍니다. 이미 열린 TCP 연결은 대상 컨테이너가 사라지면 끊길 수 있습니다.

애플리케이션은 연결 실패와 재연결을 처리해야 합니다.

---

## 확인 문제

1. `gateway:443`과 `127.0.0.1:19443`은 각각 어느 네트워크 관점의 주소와 포트입니까?
2. Compose 파일에 `networks`를 전혀 선언하지 않았을 때 서비스끼리 서비스 이름으로 통신할 수 있는 이유는 무엇입니까?
3. 공통 네트워크가 없는 두 서비스가 직접 통신하지 못하는 이유는 무엇입니까?
4. 데이터베이스 컨테이너를 삭제하고 다시 만들어도 같은 이름 있는 볼륨을 연결했을 때 데이터가 남는 이유는 무엇입니까?
5. 컨테이너의 쓰기 가능 계층과 이름 있는 볼륨은 수명 면에서 어떻게 다릅니까?
6. 서비스 이름을 고정 컨테이너 IP보다 우선해야 하는 이유는 무엇입니까?
7. DNS가 새 컨테이너 IP를 반환해도 기존 TCP 연결이 자동으로 복구되지 않는 이유는 무엇입니까?
8. `running`과 `healthy`는 무엇을 각각 의미합니까?
9. `depends_on: condition: service_healthy`가 해결하는 문제와 해결하지 못하는 문제를 각각 설명해 보세요.
10. `docker compose down`과 `docker compose down -v`는 이름 있는 볼륨을 어떻게 다르게 처리합니까?
11. `external: true`인 볼륨을 `docker compose down -v`가 제거하지 않는 이유는 무엇입니까?
12. Compose 변수 보간과 컨테이너의 `environment`는 어떤 단계에서 사용됩니까?
13. `DB_PASSWORD_FILE=/run/secrets/db_password`가 동작하려면 Compose 외에 애플리케이션 또는 이미지가 무엇을 지원해야 합니까?
14. 서비스 자체의 `restart: unless-stopped`와 `depends_on` 아래의 `restart: true`는 무엇이 다릅니까?

---

## 참고 문서

- Compose 파일: https://docs.docker.com/reference/compose-file/
- 서비스 정의: https://docs.docker.com/reference/compose-file/services/
- Compose 네트워크: https://docs.docker.com/compose/how-tos/networking/
- Compose 네트워크 정의: https://docs.docker.com/reference/compose-file/networks/
- 시작 순서와 `depends_on`: https://docs.docker.com/compose/how-tos/startup-order/
- Compose secrets: https://docs.docker.com/compose/how-tos/use-secrets/
- Docker 볼륨: https://docs.docker.com/engine/storage/volumes/
- `docker compose down`: https://docs.docker.com/reference/cli/docker/compose/down/
