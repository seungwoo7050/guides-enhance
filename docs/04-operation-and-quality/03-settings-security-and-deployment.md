# Settings, 보안과 배포 준비

## 학습 목표

- 개발용 `runserver`와 운영 server를 구분합니다.
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, HTTPS cookie를 환경에 맞게 설정합니다.
- static file과 사용자 upload를 다른 데이터로 취급합니다.
- 운영 settings로 `check --deploy`를 실행합니다.

## `DEBUG`

운영에서 `DEBUG=True`를 사용하면 source code 일부, local variable, settings가 오류 화면에 노출될 수 있습니다.

```python
DEBUG = False
```

`DEBUG=False`이면 `ALLOWED_HOSTS`가 올바르게 설정되어야 요청을 처리합니다.

## Secret

`SECRET_KEY`를 source control에 저장하지 않습니다.

```python
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
```

누락된 경우 임의의 기본값으로 운영을 시작하기보다 startup을 실패시키는 편이 안전합니다.

## HTTPS와 cookie

로그인 기능이 있다면 전체 사이트를 HTTPS로 제공해야 합니다.

```python
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

Reverse proxy가 HTTPS를 종료한다면 Django가 실제 scheme을 신뢰하도록 설정해야 할 수 있습니다. `SECURE_PROXY_SSL_HEADER`는 proxy가 해당 header를 외부 요청에서 제거하고 직접 설정한다는 보장이 있을 때만 사용합니다.

## HSTS

HSTS는 browser가 일정 기간 HTTP 연결을 시도하지 않게 합니다. 잘못 설정하면 인증서나 subdomain 준비가 끝나기 전 서비스 복구가 어려울 수 있습니다. 짧은 값으로 확인한 뒤 기간과 subdomain, preload 여부를 늘립니다.

## Static과 media

- static: 개발자가 배포한 CSS, JavaScript, image
- media: 사용자가 업로드한 신뢰할 수 없는 파일

```sh
python manage.py collectstatic
```

운영 server는 `STATIC_ROOT` 결과를 제공합니다. 사용자 upload를 script로 실행하지 않도록 web server와 storage를 설정해야 합니다.

현재 exercise는 사용자 upload를 받지 않습니다.

## Database

SQLite는 설치 없이 학습하고 test하기 좋습니다. 여러 process가 동시에 write하고 backup·replication·운영 모니터링이 필요하다면 PostgreSQL 같은 운영 database를 사용합니다.

Database password도 secret입니다. URL 전체를 error message나 log에 출력하지 않습니다.

## Log와 오류 보고

운영에서는 request error, permission failure, moderation 작업을 추적할 수 있어야 합니다. Password, session cookie, secret key, 전체 POST body를 log에 남기지 않습니다.

## Deployment check

운영 settings와 환경 변수를 지정해 실행합니다.

```sh
DJANGO_SETTINGS_MODULE=config.settings.production \
DJANGO_SECRET_KEY='replace-with-a-long-random-value' \
DJANGO_ALLOWED_HOSTS='example.com' \
python manage.py check --deploy
```

경고를 무조건 없애기보다 현재 TLS 종료 위치, host 검증, cookie, HSTS 설정과 비교해 판단합니다.

`runserver`는 운영 server가 아닙니다. WSGI 또는 ASGI application을 Gunicorn, Uvicorn 등 운영용 server에서 실행하고 reverse proxy, TLS, static file, log, process restart를 별도로 구성해야 합니다.

## 공식 문서

- https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
- https://docs.djangoproject.com/en/5.2/howto/deployment/
- https://docs.djangoproject.com/en/5.2/ref/settings/
- https://docs.djangoproject.com/en/5.2/topics/security/
