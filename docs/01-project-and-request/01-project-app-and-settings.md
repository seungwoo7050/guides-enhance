# Project, app과 settings

## 학습 목표

- Django project와 app이 저장하는 내용을 구분합니다.
- `manage.py`, settings module, WSGI/ASGI entrypoint의 용도를 설명합니다.
- custom user model을 첫 migration 전에 결정해야 하는 이유를 이해합니다.
- 개발 settings와 운영 settings를 분리합니다.

## Project와 app

Django project는 한 사이트를 실행하는 설정과 최상위 URL 구성을 보관합니다.

```text
config/
├── settings/
├── urls.py
├── asgi.py
└── wsgi.py
```

app은 함께 변경되는 기능과 데이터를 보관합니다. `catalog-site`는 두 app만 사용합니다.

```text
accounts/  사용자 model, 가입 화면
catalog/   항목, 후기, 제보, 검색, admin
```

model 하나마다 app을 만들지 않습니다. URL, model, form, template이 같은 기능을 위해 함께 변경된다면 한 app에 두는 편이 관리하기 쉽습니다.

## Scaffold 명령

새 project를 시작할 때 다음 명령은 유지할 파일을 생성합니다.

```sh
django-admin startproject config .
python manage.py startapp accounts
python manage.py startapp catalog
```

단순히 directory를 만드는 명령이 아닙니다. settings package, management command entrypoint, app configuration을 생성하므로 구현 순서에 포함할 수 있습니다.

## `manage.py`

`manage.py`는 현재 project의 settings를 지정한 뒤 Django management command를 실행합니다.

```sh
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py test
python manage.py runserver
```

`runserver`는 개발용입니다. 운영에서는 WSGI 또는 ASGI server가 `config.wsgi.application`이나 `config.asgi.application`을 불러옵니다.

## Settings 분리

공통값과 환경별 값을 나눕니다.

```text
config/settings/
├── base.py
├── development.py
└── production.py
```

- `base.py`: app, middleware, template, database 기본값, 언어와 시간대
- `development.py`: `DEBUG=True`, local host 허용
- `production.py`: secret key, host, HTTPS cookie, HSTS, log 설정

설정 파일을 나눴다고 비밀값이 안전해지는 것은 아닙니다. 운영용 `SECRET_KEY`, database password, mail password는 environment variable이나 별도 secret 저장소에서 읽어야 합니다.

## Custom user model

새 project에서는 기본 `User`를 그대로 사용하더라도 `AbstractUser`를 상속한 project 전용 model을 먼저 만드는 편이 안전합니다.

```python
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    pass
```

그리고 첫 migration 전에 다음 설정을 추가합니다.

```python
AUTH_USER_MODEL = "accounts.User"
```

user table을 만든 뒤 model을 교체하면 foreign key와 migration dependency를 수동으로 정리해야 합니다. 따라서 custom user model은 `migrate`를 처음 실행하기 전에 결정합니다.

다른 app의 model은 `User` class를 직접 import하지 않고 settings를 참조합니다.

```python
from django.conf import settings

models.ForeignKey(settings.AUTH_USER_MODEL, ...)
```

runtime code에서 model class가 필요하면 `get_user_model()`을 사용합니다.

## `INSTALLED_APPS`

app을 directory에 만들기만 해서는 Django가 model, template, admin registration을 찾지 않습니다. `INSTALLED_APPS`에 app configuration을 등록해야 합니다.

```python
INSTALLED_APPS = [
    ...,
    "accounts.apps.AccountsConfig",
    "catalog.apps.CatalogConfig",
]
```

## 확인할 것

```sh
python manage.py check
python manage.py showmigrations
```

`check`는 settings와 model 구성 문제를 찾지만, 실제 운영 환경의 secret 관리나 reverse proxy 설정까지 증명하지는 않습니다.

## 공식 문서

- https://docs.djangoproject.com/en/5.2/intro/tutorial01/
- https://docs.djangoproject.com/en/5.2/topics/settings/
- https://docs.djangoproject.com/en/5.2/topics/auth/customizing/
