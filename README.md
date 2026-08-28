# 웹 인프라 가이드

웹 요청이 서버 프로세스에 도착하고, Docker Compose 안에서 Nginx, PHP-FPM, MariaDB가 함께 동작하는 과정을 설명합니다. 특정 제품의 설정을 외우기보다 다음 질문에 답할 수 있는 상태를 목표로 합니다.

- 요청은 어느 주소와 포트로 들어오는가?
- 컨테이너 안에서 어떤 프로세스가 PID 1로 실행되는가?
- 서비스끼리는 어떤 이름과 포트로 연결되는가?
- 컨테이너를 다시 만들어도 남아야 하는 데이터는 어디에 저장하는가?
- 데이터베이스와 애플리케이션은 어떤 순서로 준비되는가?
- 장애가 발생했을 때 어느 단계부터 확인해야 하는가?

## 학습 방식

이 저장소는 모든 문서와 실습를 끝낸 뒤 실제 개발을 시작하는 방식으로 사용하지 않습니다.

```text
기초 문서 정독
→ 실제 프로젝트에 바로 진입
→ 필요한 문서를 그 시점에 읽음
→ 프로젝트 완료 및 검증
→ 장애 진단 문서로 경험 정리
→ notes-stack을 가이드 없이 다시 구현
→ 실패한 부분만 복습
```

프로젝트에 들어가기 전에는 `docs/01-foundations/`의 세 문서만 정독합니다. Nginx, MariaDB, 애플리케이션 초기화는 실제 구현에서 필요해졌을 때 `docs/02-service-stack/`의 해당 문서를 읽습니다.

`exercises/notes-stack`은 선행 연습이 아닙니다. 실제 프로젝트를 끝낸 뒤, 익숙한 코드와 설정을 보지 않고 같은 개발 능력을 다시 사용할 수 있는지 확인하는 통합 실습입니다.

자세한 진행 순서는 [`docs/00-roadmap.md`](docs/00-roadmap.md)에 정리되어 있습니다.

## 문서

### 기초

1. [`웹 요청과 서버`](docs/01-foundations/01-web-request-and-server.md)
2. [`Docker 이미지와 컨테이너`](docs/01-foundations/02-docker-image-and-container.md)
3. [`Compose, 네트워크와 저장소`](docs/01-foundations/03-compose-network-and-storage.md)

세 문서는 프로젝트 종류와 관계없이 필요한 실행 모델을 다룹니다. 요청, 프로세스, 컨테이너, 서비스 이름, 포트와 볼륨을 구분하지 못하면 이후 설정을 복사해서 맞추는 수준에 머물기 쉽습니다.

### 서비스 구성

4. [`Nginx, TLS와 PHP-FPM`](docs/02-service-stack/04-nginx-tls-and-php-fpm.md)
5. [`데이터베이스 생명주기`](docs/02-service-stack/05-database-lifecycle.md)
6. [`반복 가능한 애플리케이션 초기화`](docs/02-service-stack/06-idempotent-app-bootstrap.md)
7. [`운영, 장애 진단과 복구`](docs/02-service-stack/07-operations-debugging-and-recovery.md)

4~6장은 실제 구현에서 해당 기술이 필요해졌을 때 읽습니다. 7장은 구현 중 충분한 장애를 경험했거나 프로젝트를 완료한 뒤 읽는 편이 효율적입니다.

## 실습

### `notes-stack`

Nginx, PHP-FPM, MariaDB를 별도 컨테이너로 실행하는 작은 메모 서비스입니다.

```text
HTTPS 요청
    ↓
Nginx
    ↓ FastCGI
PHP-FPM
    ↓
MariaDB
```

다음 내용을 한 프로젝트에서 검증합니다.

- 빈 데이터 디렉터리에서만 실행되는 MariaDB 초기화
- 내부 네트워크에서만 접근 가능한 데이터베이스와 PHP-FPM
- Nginx의 로컬 TLS와 FastCGI 전달
- 파일로 주입한 비밀번호와 PHP-FPM 작업자가 읽는 tmpfs 복사본
- 횟수를 제한한 데이터베이스 연결 재시도
- 반복 실행해도 중복되지 않는 스키마와 초기 데이터
- 데이터베이스 볼륨의 보존
- 논리 백업과 복원
- 잘못된 호스트, 비밀번호, 비밀값 경로, FastCGI 포트와 상태 검사 재현

실행 방법, 설계 선택과 전체 Implementation Order는 [`exercises/notes-stack/README.md`](exercises/notes-stack/README.md)를 참고합니다.

## 저장소 구조

```text
.
├── .gitignore
├── README.md
├── docs/
│   ├── 00-roadmap.md
│   ├── 01-foundations/
│   └── 02-service-stack/
└── exercises/
    └── notes-stack/
```

`docs/`는 개념과 판단 기준을 설명합니다. `exercises/`는 skeleton이나 정답 비교용 디렉터리가 아니라, 독립적으로 실행하고 검사할 수 있는 완성된 프로젝트를 담습니다.

## 완료 기준

다음 내용을 코드와 설정을 보며 설명할 수 있어야 합니다.

- `127.0.0.1`, `0.0.0.0`, Compose 서비스 이름의 차이
- 호스트 공개 포트와 컨테이너 내부 포트의 차이
- 이미지, 컨테이너와 이름 있는 볼륨의 수명 차이
- Nginx가 HTTPS를 받고 PHP-FPM에 FastCGI 요청을 보내는 과정
- MariaDB가 최초 실행인지 기존 데이터인지 판정하는 방법
- 초기 데이터 마커와 데이터 삽입을 같은 트랜잭션에 두는 이유
- 시작 스크립트가 마지막에 `exec`를 사용하는 이유
- 404, 500, 502, 데이터베이스 인증 실패와 비밀값 누락을 구분하는 순서
- 백업 파일을 실제 복구 수단으로 인정하려면 복원 검사가 필요한 이유

`notes-stack`을 가이드와 이전 구현을 보지 않고 다시 만들고, 프로젝트 자체 테스트를 통과하면 이 가이드가 다루는 범위를 독립적으로 사용할 수 있다고 판단합니다.

## 범위 밖

다음 주제는 본격적으로 다루지 않습니다.

- Kubernetes와 다중 호스트 오케스트레이션
- 고가용성 데이터베이스와 자동 장애 조치
- 공인 인증서 자동 갱신
- CI/CD와 이미지 registry 운영
- 대규모 관측 시스템
- 조직 단위의 비밀값 관리와 보안 감사

이 주제들은 여기서 다루는 프로세스, 네트워크, 저장소와 시작 절차를 이해한 뒤 별도의 가이드에서 다루는 편이 적절합니다.
