# Project, app과 settings

## 학습 목표

- Django project와 app이 맡는 책임을 구분합니다.
- `manage.py`, settings module, WSGI/ASGI entrypoint가 어떻게 연결되는지 설명합니다.
- custom user model을 첫 migration 전에 결정해야 하는 이유를 migration dependency 관점에서 이해합니다.
- 공통 settings와 개발·운영 settings를 분리하고 실행 환경이 사용할 settings module을 명시적으로 선택합니다.

## Project와 app

Django에서 **project**는 특정 사이트나 서비스를 실행하기 위한 최상위 구성입니다. 어떤 app을 사용할지, 요청을 어떤 URL로 보낼지, 어떤 settings와 server entrypoint를 사용할지 같은 **application 전체 수준의 설정**을 보관합니다.

예를 들어 다음 `config` package는 project 수준의 구성을 담당합니다.

```text
config/
├── settings/
│   ├── __init__.py
│   ├── base.py
│   ├── development.py
│   └── production.py
├── urls.py
├── asgi.py
└── wsgi.py
```

각 파일의 책임은 다음과 같습니다.

- `settings/`: 설치할 app, middleware, database, template, 보안 설정 등 실행 환경의 구성
- `urls.py`: project 최상위 URL routing
- `wsgi.py`: WSGI server가 Django application을 불러오기 위한 entrypoint
- `asgi.py`: ASGI server가 Django application을 불러오기 위한 entrypoint

반면 **app**은 특정 기능 영역에 속한 model, view, form, template, admin 설정 등을 함께 보관하는 Django 구성 단위입니다.

`catalog-site`에서는 다음과 같이 기능 경계를 나눌 수 있습니다.

```text
accounts/  사용자 model, 가입과 계정 관련 기능
catalog/   항목, 후기, 제보, 검색, admin
```

app을 model 하나마다 만들 필요는 없습니다. 중요한 기준은 **같은 기능을 위해 함께 변경되는 코드를 한 경계에 두는 것**입니다. 예를 들어 항목 검색을 수정할 때 `Item` model, 검색 view, form, template이 함께 바뀐다면 이들을 `catalog` app에 두는 편이 변경 이유를 한곳에 모으기 쉽습니다.

반대로 서로 다른 기능이 단지 같은 database를 사용한다는 이유만으로 하나의 큰 app에 모이면 변경 범위와 의존 관계가 불분명해질 수 있습니다.

## Scaffold 명령

새 project를 시작할 때 다음 명령으로 기본 구조를 생성할 수 있습니다.

```sh
django-admin startproject config .
python manage.py startapp accounts
python manage.py startapp catalog
```

첫 번째 명령에서 `config`는 생성할 project package 이름이고, 마지막 `.`은 현재 directory를 project root로 사용한다는 뜻입니다.

`startproject`는 단순히 directory만 만드는 명령이 아닙니다. 기본적으로 다음과 같은 Django 실행 구조를 생성합니다.

```text
manage.py
config/
├── __init__.py
├── settings.py
├── urls.py
├── asgi.py
└── wsgi.py
```

이후 settings를 환경별로 나누고 싶다면 `settings.py`를 `settings/` package 구조로 재구성할 수 있습니다.

`startapp`도 app directory만 만드는 것이 아니라 `apps.py`, `models.py`, `admin.py`, `migrations/` 등 Django가 기대하는 기본 구조를 생성합니다.

따라서 scaffold 명령은 단순한 편의 기능이 아니라 **project와 app의 초기 Django 구조를 만드는 구현 단계**입니다.

## `manage.py`

`manage.py`는 현재 project에서 Django management command를 실행하기 위한 entrypoint입니다.

대표적인 명령은 다음과 같습니다.

```sh
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py test
python manage.py runserver
```

`manage.py`의 핵심 역할은 Django가 사용할 settings module을 지정한 뒤 management command 실행기로 제어를 넘기는 것입니다. `startproject`가 생성한 기본 파일에는 일반적으로 다음과 같은 설정이 들어 있습니다.

```python
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
```

`DJANGO_SETTINGS_MODULE`은 Python import 경로 형태로 settings module을 지정합니다. settings를 환경별로 분리했다면 예를 들어 다음 두 module 중 하나를 선택할 수 있습니다.

```text
config.settings.development
config.settings.production
```

즉, settings 파일을 여러 개 만들어 두는 것만으로는 환경이 자동으로 선택되지 않습니다. **현재 프로세스가 어떤 settings module을 사용할지 `DJANGO_SETTINGS_MODULE`로 결정해야 합니다.**

예를 들어 개발 환경에서는 다음처럼 실행할 수 있습니다.

```sh
DJANGO_SETTINGS_MODULE=config.settings.development \
python manage.py runserver
```

운영 환경에서는 배포 환경, process manager, container 설정 등에서 다음과 같은 값을 주입할 수 있습니다.

```text
DJANGO_SETTINGS_MODULE=config.settings.production
```

### `runserver`와 운영 server

`python manage.py runserver`는 개발 편의를 위한 server입니다. 코드 변경 감지와 개발용 오류 화면 등 개발에 유용한 동작을 제공하지만 운영 traffic을 처리하기 위한 server로 사용하지 않습니다.

운영에서는 WSGI 또는 ASGI server가 Django application object를 직접 불러옵니다.

```text
WSGI server
    │
    └─ config.wsgi.application

ASGI server
    │
    └─ config.asgi.application
```

- **WSGI(Web Server Gateway Interface)**: 전통적인 동기식 Python web application interface
- **ASGI(Asynchronous Server Gateway Interface)**: 비동기 처리를 지원하도록 확장된 application interface

`wsgi.py`와 `asgi.py` 자체가 web server는 아닙니다. 이 파일들은 server가 import할 **Django application object를 생성하고 노출하는 entrypoint**입니다.

## Settings 분리

개발 환경과 운영 환경은 `DEBUG`, host, database, cookie 보안, logging 등에서 요구사항이 다릅니다. 모든 값을 한 파일에서 조건문으로 관리하기보다 공통값과 환경별 값을 분리하면 각 환경의 차이를 명시적으로 확인하기 쉽습니다.

예를 들어 다음 구조를 사용할 수 있습니다.

```text
config/settings/
├── __init__.py
├── base.py
├── development.py
└── production.py
```

역할은 다음과 같이 나눌 수 있습니다.

- `base.py`: 여러 환경에서 공유하는 app, middleware, template, 언어, 시간대 등의 기본 설정
- `development.py`: local 개발에 필요한 `DEBUG=True`, 개발용 host와 database 설정
- `production.py`: 운영 host, HTTPS cookie, HSTS, logging 등 운영 전용 설정

환경별 파일은 공통 설정을 가져온 뒤 필요한 값만 덮어쓸 수 있습니다.

```python
# config/settings/development.py

from .base import *

DEBUG = True
```

```python
# config/settings/production.py

from .base import *

DEBUG = False
```

여기서 중요한 점은 **settings 파일을 분리하는 것과 비밀값을 보호하는 것은 서로 다른 문제**라는 것입니다.

다음과 같은 운영 비밀값을 source code에 직접 기록해서는 안 됩니다.

```text
SECRET_KEY
database password
mail service password
외부 API credential
```

이 값들은 environment variable이나 배포 환경의 secret 저장소처럼 source repository와 분리된 경로에서 주입해야 합니다.

예를 들어 필수 secret은 다음처럼 읽을 수 있습니다.

```python
import os

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
```

`os.environ["DJANGO_SECRET_KEY"]`처럼 필수 환경 변수를 직접 읽으면 값이 누락된 경우 application 시작 단계에서 즉시 실패합니다. 운영 secret이 실수로 빈 값이나 개발용 기본값으로 대체되는 것을 막는 데 도움이 됩니다.

또한 `DEBUG=False`에서는 요청의 `Host` header를 허용할 값을 `ALLOWED_HOSTS`에 올바르게 지정해야 합니다. settings 분리는 이러한 운영 전용 요구사항을 개발 설정과 분리하여 검토하기 쉽게 만드는 수단입니다.

## Custom user model

Django는 기본 사용자 model을 제공하지만, 새 project에서는 처음부터 project 전용 user model을 정의해 두는 편이 이후 확장에 유리합니다.

가장 단순한 형태는 `AbstractUser`를 상속하는 것입니다.

```python
# accounts/models.py

from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    pass
```

`AbstractUser`는 Django 기본 `User`가 제공하는 username, password, 권한 관련 필드와 동작을 상속할 수 있는 추상 model입니다. 지금 추가 필드가 없더라도 project 전용 `User` class를 먼저 만들어 두면 이후 필요한 필드를 같은 model에 추가할 수 있습니다.

그리고 **첫 migration을 적용하기 전에** 다음 설정을 지정합니다.

```python
AUTH_USER_MODEL = "accounts.User"
```

문자열 형식은 다음과 같습니다.

```text
"<app_label>.<model_name>"
```

따라서 `"accounts.User"`는 `accounts` app의 `User` model을 인증 시스템의 사용자 model로 사용한다는 뜻입니다.

### 왜 첫 migration 전에 결정해야 하는가

user model은 다른 model이 foreign key나 many-to-many relation으로 자주 참조하는 중심 model입니다. Django의 auth 관련 migration도 `AUTH_USER_MODEL` 설정을 기준으로 dependency를 구성합니다.

처음부터 custom user model을 사용하면 dependency를 다음과 같이 만들 수 있습니다.

```text
accounts.User
     ▲
     │ ForeignKey
     │
catalog.Review
```

하지만 이미 기본 user model을 기준으로 migration을 만들고 적용한 뒤 `AUTH_USER_MODEL`을 바꾸면 단순히 settings 한 줄만 수정해서 끝나지 않습니다. 이미 생성된 table, foreign key, many-to-many table, migration dependency와 기존 데이터를 새로운 user model 기준으로 정리해야 할 수 있습니다.

또한 Django의 swappable user model dependency가 안정적으로 구성되려면 custom user model은 일반적으로 해당 app의 **첫 migration인 `0001_initial`에서 생성**되어야 합니다.

따라서 새 project에서는 다음 순서를 지키는 것이 안전합니다.

```text
1. accounts app 생성
2. accounts.User 정의
3. AUTH_USER_MODEL = "accounts.User" 설정
4. accounts를 INSTALLED_APPS에 등록
5. makemigrations
6. migrate
```

핵심은 단순히 "`migrate`를 아직 실행하지 않았다"는 것뿐 아니라, **기본 user model을 전제로 migration 구조를 확정하기 전에 custom user model을 결정하는 것**입니다.

### 다른 model에서 user를 참조하는 방법

model field를 선언할 때는 Django 기본 `User` class를 직접 import하지 않고 `settings.AUTH_USER_MODEL`을 사용합니다.

```python
from django.conf import settings
from django.db import models


class Review(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
```

이렇게 하면 실제 user model이 무엇인지 model 코드에 고정하지 않고 project settings를 따를 수 있습니다.

반면 runtime code에서 실제 user model class 자체가 필요하다면 `get_user_model()`을 사용합니다.

```python
from django.contrib.auth import get_user_model

User = get_user_model()
```

두 방법의 용도를 구분하면 다음과 같습니다.

```text
model relation 선언
    └─ settings.AUTH_USER_MODEL

runtime에서 실제 model class 조회
    └─ get_user_model()
```

## `INSTALLED_APPS`

app을 directory에 만들었다고 해서 Django project에 자동으로 설치되는 것은 아닙니다. Django가 해당 app을 project 구성의 일부로 취급하려면 settings의 `INSTALLED_APPS`에 등록해야 합니다.

```python
INSTALLED_APPS = [
    ...,
    "accounts.apps.AccountsConfig",
    "catalog.apps.CatalogConfig",
]
```

`accounts.apps.AccountsConfig`는 보통 `accounts/apps.py`에 정의된 `AppConfig` subclass를 가리킵니다.

```python
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
```

설치된 app은 Django app registry에 등록됩니다. 이를 기준으로 Django는 model metadata와 migration 대상을 구성하고, 설정에 따라 app 내부 template을 탐색하며, admin autodiscovery 과정에서도 설치된 app의 `admin` module을 대상으로 탐색합니다.

따라서 다음 두 단계는 서로 다른 작업입니다.

```text
python manage.py startapp accounts
        │
        └─ app의 파일 구조를 생성

INSTALLED_APPS에 accounts 등록
        │
        └─ 현재 project가 그 app을 사용한다고 Django에 알림
```

app을 만든 뒤 등록하지 않으면 model을 작성했더라도 migration 대상에 포함되지 않는 등 예상한 Django 동작을 얻지 못할 수 있습니다.

## 전체 연결 관계

지금까지의 요소를 한 번에 연결하면 다음과 같습니다.

```text
manage.py / WSGI server / ASGI server
              │
              │ DJANGO_SETTINGS_MODULE
              ▼
      config.settings.<환경>
              │
              ├─ INSTALLED_APPS
              │      ├─ accounts
              │      └─ catalog
              │
              ├─ AUTH_USER_MODEL
              │      └─ accounts.User
              │
              └─ ROOT_URLCONF
                     └─ config.urls
```

즉, project 수준의 settings가 어떤 app과 user model, URL 구성을 사용할지 결정하고, `manage.py` 또는 운영 server가 그 settings를 선택하여 Django application을 시작합니다.

## 확인할 것

구성이 끝나면 먼저 Django의 system check와 migration 상태를 확인합니다.

```sh
python manage.py check
python manage.py showmigrations
```

환경별 settings를 사용한다면 실제로 검사하려는 settings module을 명시하는 것이 좋습니다.

```sh
DJANGO_SETTINGS_MODULE=config.settings.development \
python manage.py check
```

```sh
DJANGO_SETTINGS_MODULE=config.settings.production \
python manage.py check
```

`check`는 model 관계, settings 값, URL 구성 등 Django가 검사할 수 있는 여러 구성 문제를 찾습니다. 하지만 성공했다고 해서 운영 구성이 모두 안전하다는 뜻은 아닙니다.

예를 들어 다음 사항은 별도로 확인해야 합니다.

```text
secret이 source repository에 포함되지 않았는가
운영 환경 변수가 실제로 주입되는가
reverse proxy가 요청 header를 올바르게 전달하는가
HTTPS와 secure cookie 설정이 실제 배포 구조와 일치하는가
운영 database와 외부 service 연결이 올바른가
```

따라서 `python manage.py check`는 **Django configuration 검증의 한 단계**이지 운영 환경 전체의 안전성을 증명하는 검사는 아닙니다.

## 공식 문서

- https://docs.djangoproject.com/en/5.2/intro/tutorial01/
- https://docs.djangoproject.com/en/5.2/topics/settings/
- https://docs.djangoproject.com/en/5.2/topics/auth/customizing/
