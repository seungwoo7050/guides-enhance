# Django

Django 5.2 LTS를 사용해 서버 렌더링 웹 애플리케이션을 처음부터 운영 가능한 형태까지 만드는 가이드입니다.

문서를 모두 읽은 뒤 구현을 시작하지 않습니다. URL과 view를 이해하면 화면을 만들고, model과 migration을 이해하면 데이터를 저장하며, form과 인증을 이해하면 사용자 입력을 받는 식으로 `catalog-site`를 계속 확장합니다.

## 기준 환경

- Python 3.12 이상
- Django 5.2.17
- 개발·테스트 데이터베이스: SQLite
- 운영 데이터베이스 권장: PostgreSQL

Django 5.2는 LTS release입니다. 이 저장소는 5.2 계열의 API와 동작을 기준으로 작성되어 있습니다.

## 완료 후 할 수 있는 일

필수 과정을 마치면 다음 작업을 수행할 수 있어야 합니다.

- Django project와 app이 각각 무엇을 보관하는지 설명합니다.
- URL을 view에 연결하고 request를 검증해 response를 반환합니다.
- template 상속, context, static file을 사용해 서버 렌더링 화면을 만듭니다.
- model, relation, migration, database constraint를 사용해 데이터를 저장합니다.
- `QuerySet`, `select_related()`, `prefetch_related()`로 필요한 데이터를 읽습니다.
- `ModelForm`과 CSRF 보호를 사용해 입력을 검증합니다.
- 로그인, session, object ownership, staff 권한을 구분합니다.
- 여러 row를 함께 바꾸는 작업을 transaction으로 처리합니다.
- admin에서 데이터를 조회하고 검수 작업을 실행합니다.
- model, query, form, permission, HTTP response를 자동으로 검사합니다.
- 개발 설정과 운영 설정을 분리하고 `check --deploy` 결과를 검토합니다.

## 저장소 구성

```text
.
├── .gitignore
├── README.md
├── docs
│   ├── 00-roadmap.md
│   ├── 01-project-and-request
│   ├── 02-data
│   ├── 03-web-input-and-users
│   ├── 04-operation-and-quality
│   └── 05-api-integration
└── exercises
    └── catalog-site
```

`docs/`는 각 기능을 구현하기 전에 필요한 개념과 실패 조건을 설명합니다. `exercises/catalog-site/`는 목록·상세 조회, 검색, 후기, 제보, 관리자 검수, 테스트, 운영 설정을 포함한 완성된 Django project입니다.

## 권장 진행 순서

```text
project와 settings
→ request, URL, view
→ 첫 목록 화면
→ model과 migration
→ query와 상세 화면
→ form과 사용자 입력
→ 인증과 소유권
→ transaction과 admin 검수
→ 테스트
→ 운영 설정
→ 선택: JSON API와 Astro 연동
```

정확한 문서와 구현 순서는 [로드맵](docs/00-roadmap.md)에 정리되어 있습니다.

## Exercise

[`catalog-site`](exercises/catalog-site/)는 장소, 게임, 제품, 서비스처럼 분류와 검색이 필요한 항목을 게시하고 사용자 후기를 받는 사이트입니다.

주요 기능:

- 공개된 항목 목록과 상세 조회
- 검색, category/tag filter, pagination
- 회원가입, 로그인, 로그아웃
- 항목당 사용자 후기 1건 작성·수정·삭제
- 사용자 제보와 본인 제보 내역 조회
- staff가 제보를 승인해 draft 항목으로 변환하거나 거절
- Django admin을 사용한 데이터 관리
- read-only JSON API
- 개발·운영 settings 분리
- model, query, view, permission, transaction, API test

설치와 실행 방법은 [exercise README](exercises/catalog-site/README.md)를 따릅니다.

## 필수와 선택 범위

필수 과정은 서버 렌더링 Django 애플리케이션 완성까지입니다. `docs/05-api-integration/`과 JSON API는 Django 데이터를 Astro 같은 별도 frontend에서 읽어야 할 때 사용하는 선택 과정입니다.

Django REST Framework, Celery, Channels, cache server, container orchestration은 포함하지 않습니다. 해당 도구가 필요한 문제가 생긴 뒤 별도로 학습하는 편이 낫습니다.
