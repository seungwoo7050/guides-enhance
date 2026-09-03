# Settings, 보안과 배포 준비

## 학습 목표

- 개발용 `runserver`와 운영용 application server를 구분합니다.
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, HTTPS 관련 cookie 설정을 환경에 맞게 구성합니다.
- reverse proxy 뒤에서 Django가 요청의 실제 scheme을 올바르게 판단하도록 설정할 때의 조건을 이해합니다.
- static file과 사용자 upload인 media file을 서로 다른 데이터로 취급합니다.
- 운영 settings를 사용해 `check --deploy`를 실행하고, 경고를 실제 배포 구조와 함께 해석합니다.

## `DEBUG`

`DEBUG`는 개발 중 상세 오류 화면과 디버깅 정보를 제공하기 위한 설정입니다.

운영 환경에서는 반드시 `False`로 둡니다.

```python
DEBUG = False
```

운영에서 `DEBUG=True`를 사용하면 오류가 발생했을 때 source code 일부, local variable, settings 값과 같은 내부 정보가 상세 오류 화면에 노출될 수 있습니다. 따라서 `DEBUG=False`는 단순한 성능 설정이 아니라 중요한 보안 설정입니다.

`DEBUG=False`일 때는 요청의 `Host` header가 `ALLOWED_HOSTS`에 허용된 값인지 검사합니다. 운영에서 사용할 hostname을 명시적으로 등록합니다.

```python
ALLOWED_HOSTS = ["example.com", "www.example.com"]
```

`ALLOWED_HOSTS`는 "이 서버가 어떤 host 이름으로 요청을 받아도 되는가"를 제한하는 설정입니다. 외부에서 전달된 임의의 `Host` header를 그대로 신뢰하지 않도록 하는 데 사용됩니다.

환경 변수로 전달한다면 문자열을 그대로 넣지 말고 목록으로 변환해야 합니다.

```python
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ["DJANGO_ALLOWED_HOSTS"].split(",")
    if host.strip()
]
```

예를 들어 다음 값은 두 개의 host로 해석됩니다.

```text
DJANGO_ALLOWED_HOSTS=example.com,www.example.com
```

## Secret

`SECRET_KEY`는 session, password reset token 등 Django의 여러 암호학적 서명 기능에 사용되는 secret 값입니다. 공개 저장소나 image에 고정된 값으로 포함하지 않습니다.

```python
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
```

다음처럼 운영 환경에서 사용할 기본값을 source code에 넣는 방식은 피합니다.

```python
# 피해야 할 예
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "development-secret")
```

환경 변수가 누락되었는데도 애플리케이션이 기본값으로 시작하면 잘못된 설정을 발견하지 못한 채 운영될 수 있습니다. 필요한 secret이 없으면 startup 자체를 실패시키는 편이 안전합니다.

개발 환경에서 별도의 임시 key가 필요하다면 운영 settings와 개발 settings를 분리하여 의도를 명확하게 합니다.

## HTTPS와 cookie

로그인이나 session을 사용하는 사이트라면 운영 트래픽 전체를 HTTPS로 제공해야 합니다.

Django가 직접 HTTPS 요청을 받는 구조에서는 다음과 같은 설정을 사용할 수 있습니다.

```python
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

각 설정의 역할은 다릅니다.

- `SECURE_SSL_REDIRECT=True`: Django가 HTTP 요청을 HTTPS로 redirect합니다.
- `SESSION_COOKIE_SECURE=True`: browser가 session cookie를 HTTPS 연결에서만 전송하도록 합니다.
- `CSRF_COOKIE_SECURE=True`: browser가 CSRF cookie를 HTTPS 연결에서만 전송하도록 합니다.

cookie의 `Secure` 속성은 HTTP 요청에서 cookie 전송을 막는 설정이지, cookie 내용을 암호화하는 설정은 아닙니다.

### Reverse proxy 뒤의 HTTPS

운영에서는 다음과 같은 구조가 흔합니다.

```text
browser
   │ HTTPS
   ▼
reverse proxy / load balancer
   │ HTTP 또는 내부 HTTPS
   ▼
Django application server
```

TLS를 reverse proxy에서 종료하고 proxy와 Django 사이를 HTTP로 연결하면, Django가 직접 관찰하는 요청은 HTTP일 수 있습니다. 이때 Django가 원래 client 요청이 HTTPS였다는 사실을 알지 못하면 다음과 같은 문제가 생길 수 있습니다.

- `request.is_secure()`가 `False`가 됨
- `SECURE_SSL_REDIRECT`와 proxy 설정이 맞지 않아 redirect loop가 생길 수 있음
- HTTPS 여부에 따라 동작하는 보안 로직이 잘못 판단될 수 있음

신뢰할 수 있는 proxy가 원래 요청 scheme을 header로 전달한다면 `SECURE_PROXY_SSL_HEADER`를 사용할 수 있습니다.

예를 들어 proxy가 다음 header를 직접 설정한다고 가정합니다.

```http
X-Forwarded-Proto: https
```

Django 설정은 다음과 같이 구성할 수 있습니다.

```python
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

그러나 이 설정은 **proxy가 외부 client가 보낸 해당 header를 제거하거나 덮어쓰고, 자신이 확인한 값만 전달한다는 보장이 있을 때만** 사용해야 합니다.

외부 client가 임의로 `X-Forwarded-Proto: https`를 보내고 그 값이 그대로 Django까지 전달될 수 있다면 Django가 안전하지 않은 요청을 HTTPS 요청으로 잘못 신뢰할 수 있습니다.

따라서 `SECURE_PROXY_SSL_HEADER`는 Django 설정만 보고 결정하지 않고 reverse proxy의 header 처리 규칙과 함께 검토해야 합니다.

## HSTS

HSTS(HTTP Strict Transport Security)는 HTTPS 응답의 `Strict-Transport-Security` header를 통해 browser에게 일정 기간 해당 site에 HTTP로 접속하지 말라고 지시하는 정책입니다.

Django에서는 대표적으로 다음 설정을 사용합니다.

```python
SECURE_HSTS_SECONDS = 3600
```

설정한 기간 동안 browser는 사용자가 `http://` URL을 입력하더라도 HTTPS 연결을 우선 사용합니다.

HSTS는 강력하지만 한번 browser에 전달된 정책은 설정한 시간이 끝날 때까지 client 쪽에 남을 수 있습니다. 따라서 인증서, HTTPS redirect, proxy 설정이 충분히 검증되지 않은 상태에서 처음부터 긴 기간을 설정하면 장애 복구가 어려워질 수 있습니다.

보통 다음 순서로 적용합니다.

1. 모든 정상 요청이 HTTPS로 동작하는지 확인합니다.
2. 짧은 `SECURE_HSTS_SECONDS` 값으로 시작합니다.
3. 문제가 없는지 확인한 뒤 기간을 늘립니다.
4. 모든 subdomain도 HTTPS 준비가 끝난 경우에만 `SECURE_HSTS_INCLUDE_SUBDOMAINS=True`를 검토합니다.
5. preload 요구 조건을 이해하고 되돌리기 어려운 영향을 검토한 뒤에만 `SECURE_HSTS_PRELOAD=True`를 검토합니다.

예를 들어 다음 설정은 모든 subdomain까지 HSTS 대상으로 만들기 때문에 단순히 "더 안전한 기본값"으로 추가해서는 안 됩니다.

```python
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
```

HTTPS를 지원하지 않는 기존 subdomain이 하나라도 있다면 접근 문제가 발생할 수 있습니다.

## Static과 media

Django 애플리케이션에서 static file과 media file은 생성 주체와 신뢰 수준이 다릅니다.

- **static**: 개발자가 application과 함께 배포하는 CSS, JavaScript, image, font 등의 파일
- **media**: 사용자가 application 기능을 통해 업로드한 파일

static file은 배포 artifact의 일부이고, media file은 runtime 중 생성되는 사용자 데이터입니다. 두 종류를 같은 directory와 같은 보안 정책으로 다루지 않는 편이 좋습니다.

### Static file

운영 배포 전에는 일반적으로 다음 명령으로 여러 application의 static file을 `STATIC_ROOT`에 수집합니다.

```sh
python manage.py collectstatic
```

개념적인 흐름은 다음과 같습니다.

```text
각 app의 static/
        │
        │ collectstatic
        ▼
    STATIC_ROOT
        │
        ▼
web server / CDN
```

운영에서는 보통 Django 개발 server가 static file을 직접 제공하도록 두지 않고 web server, CDN, object storage 또는 이에 적합한 배포 구성을 사용합니다.

`collectstatic`은 static file을 수집하는 작업이지 사용자 upload를 수집하는 작업이 아닙니다.

### Media file

사용자 upload는 신뢰할 수 없는 입력으로 취급해야 합니다.

예를 들어 사용자가 `photo.jpg`라는 이름으로 파일을 업로드했다고 해서 실제 내용까지 안전한 image라고 가정할 수 없습니다. 따라서 파일 이름이나 확장자만으로 신뢰하지 않습니다.

media를 제공하는 web server나 storage는 업로드된 파일이 application code처럼 실행되지 않도록 구성해야 합니다. 특히 사용자 upload directory를 executable script 경로와 섞지 않습니다.

현재 exercise는 사용자 upload를 받지 않으므로 media storage 구현 자체는 범위에 포함하지 않습니다. 여기서는 static과 media의 역할 및 신뢰 경계가 다르다는 점을 이해하면 됩니다.

## Database

SQLite는 별도 database server 설치 없이 사용할 수 있어 학습, local 개발, 작은 도구와 test 환경에 편리합니다.

그러나 운영 환경에서는 단순히 "데이터 양이 많다"는 이유만이 아니라 다음과 같은 요구를 함께 고려해야 합니다.

- 여러 application process의 동시 write
- 독립적인 backup과 restore 운영
- replication이나 failover
- connection 관리
- database 수준의 monitoring과 운영 도구

이러한 요구가 있다면 PostgreSQL과 같은 운영용 database server를 사용하는 구성이 일반적입니다.

database 접속 정보도 secret으로 취급합니다.

예를 들어 다음과 같은 URL에는 password가 포함될 수 있습니다.

```text
postgresql://app_user:password@db.example.internal/app
```

따라서 database URL 전체를 exception message, health check response 또는 일반 application log에 그대로 출력하지 않습니다.

## Log와 오류 보고

운영 log의 목적은 장애와 보안 관련 사건을 추적할 수 있게 하는 것입니다. 필요한 정보가 너무 적으면 문제 원인을 찾을 수 없지만, 요청 데이터를 무분별하게 기록하면 secret이나 개인정보가 노출될 수 있습니다.

예를 들어 다음과 같은 사건은 추적 가능해야 합니다.

- 처리되지 않은 request error
- 반복되는 permission failure
- moderation 승인·거절과 같은 운영상 중요한 변경
- 외부 service 또는 database 연결 실패

반대로 다음 값은 일반 log에 직접 기록하지 않습니다.

- password
- `SECRET_KEY`
- session cookie
- authentication token
- database password가 포함된 connection URL
- 민감한 값이 포함될 수 있는 전체 POST body

필요한 경우 사용자나 요청을 식별할 수 있는 최소한의 식별자와 작업 종류를 기록하고, secret 자체는 기록하지 않는 방식으로 설계합니다.

## Deployment check

Django는 운영 배포에서 흔히 잘못 설정되는 항목을 검사하기 위해 deployment check를 제공합니다.

운영에서 실제로 사용할 settings module과 필요한 환경 변수를 지정해 실행합니다.

```sh
DJANGO_SETTINGS_MODULE=config.settings.production \
DJANGO_SECRET_KEY='replace-with-a-long-random-value' \
DJANGO_ALLOWED_HOSTS='example.com' \
python manage.py check --deploy
```

중요한 점은 `check --deploy`가 **현재 로드된 settings를 검사한다는 것**입니다. 개발 settings로 실행한 결과를 운영 설정 검증 결과로 간주하면 안 됩니다.

또한 이 명령이 성공했다고 해서 배포 전체가 자동으로 안전해지는 것은 아닙니다. Django는 reverse proxy, firewall, TLS certificate, DNS, secret 배포 방식 등 외부 infrastructure 전체를 알 수 없기 때문입니다.

따라서 경고는 무조건 제거하거나 무시하기보다 실제 배포 구조와 비교해서 판단합니다.

특히 다음 항목을 함께 확인합니다.

- TLS는 어디에서 종료되는가
- Django가 HTTPS 여부를 어떻게 판단하는가
- 허용할 hostname이 `ALLOWED_HOSTS`에 정확히 들어 있는가
- session과 CSRF cookie가 HTTPS에서만 전송되는가
- HSTS를 적용할 준비가 되었는가
- secret이 source control이나 log에 노출되지 않는가

## `runserver`와 운영 server

다음 명령은 개발 편의를 위한 server입니다.

```sh
python manage.py runserver
```

`runserver`는 개발 중 코드 변경을 빠르게 확인하고 오류를 살펴보기 위한 용도이며 운영 traffic을 처리하도록 설계된 server가 아닙니다.

운영에서는 Django가 노출하는 WSGI 또는 ASGI application을 운영용 application server에서 실행합니다.

예를 들면 다음과 같은 역할 분리가 가능합니다.

```text
Internet
   │
   ▼
reverse proxy / load balancer
   │
   ├── TLS 종료
   ├── request forwarding
   └── static file 처리 또는 CDN 연계
   │
   ▼
Gunicorn / Uvicorn 등 application server
   │
   ▼
Django WSGI / ASGI application
```

- WSGI deployment는 전통적인 synchronous Django application 실행 방식입니다.
- ASGI deployment는 async request 처리나 WebSocket 등 ASGI 기능이 필요한 경우 사용할 수 있는 인터페이스입니다.
- 실제 server 선택은 application의 WSGI/ASGI 구성과 운영 요구에 맞춰 결정합니다.

운영 환경에서는 application server 실행만으로 배포가 끝나지 않습니다. 다음 항목도 별도로 구성해야 합니다.

- process 시작과 재시작
- TLS certificate와 HTTPS
- reverse proxy 또는 load balancer
- static file 제공
- log 수집과 오류 보고
- secret 및 환경 변수 공급
- database backup과 운영 정책

즉, Django application을 실행하는 process와 서비스 전체를 안전하게 운영하는 infrastructure는 서로 다른 문제입니다.

## 공식 문서

- https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
- https://docs.djangoproject.com/en/5.2/howto/deployment/
- https://docs.djangoproject.com/en/5.2/ref/settings/
- https://docs.djangoproject.com/en/5.2/topics/security/
