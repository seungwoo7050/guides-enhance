# Template, static file과 context

## 학습 목표

- template 상속으로 공통 HTML을 한곳에서 관리합니다.
- 사용자 입력이 HTML에 출력될 때 자동 escaping을 유지합니다.
- app별 template와 static file 이름이 충돌하지 않게 배치합니다.
- 계산과 database 조회를 template에 숨기지 않습니다.

## Template 위치

app별 template는 app 이름으로 한 번 더 감쌉니다.

```text
catalog/templates/catalog/entry_list.html
accounts/templates/accounts/signup.html
```

서로 다른 app에 같은 `detail.html`이 있어도 경로가 충돌하지 않습니다.

공통 `base.html`은 설치된 app의 template directory에서 찾을 수 있습니다.

## Template 상속

```django
{% extends "base.html" %}

{% block content %}
  <h1>{{ entry.title }}</h1>
{% endblock %}
```

header, navigation, message, footer를 각 화면에 복사하지 않습니다. 공통 markup을 `base.html`에 두고 바뀌는 부분만 block으로 교체합니다.

## Context

view는 template에 필요한 값을 명시적으로 전달합니다.

```python
return render(request, "catalog/entry_list.html", {
    "entries": entries,
    "categories": categories,
})
```

Template에서 임의의 service를 호출하거나 복잡한 query를 만들지 않습니다. filter와 pagination은 view 또는 query function에서 끝내고 template는 이미 준비된 값을 표시합니다.

## 자동 escaping

Django template는 기본적으로 HTML special character를 escape합니다.

```django
{{ review.body }}
```

사용자 입력에 `safe` filter를 적용하면 script와 악성 markup이 실행될 수 있습니다. 신뢰할 수 없는 문자열에는 `safe`를 사용하지 않습니다.

## Form 출력

```django
<form method="post">
  {% csrf_token %}
  {{ form.as_p }}
  <button type="submit">저장</button>
</form>
```

validation 오류는 form field와 함께 표시합니다. POST 실패 후 새 form을 만들면 사용자가 입력한 값과 오류가 사라지므로, 검증에 실패한 form instance를 그대로 렌더링해야 합니다.

## Static file

```text
catalog/static/catalog/site.css
```

Template에서는 static tag를 사용합니다.

```django
{% load static %}
<link rel="stylesheet" href="{% static 'catalog/site.css' %}">
```

개발 server는 static file을 편의상 제공하지만 운영에서는 `collectstatic`으로 `STATIC_ROOT`에 모은 뒤 web server나 object storage가 제공하도록 구성합니다.

## Message

저장이나 삭제 후 다음 GET에서 한 번만 보여 줄 안내는 message framework를 사용할 수 있습니다.

```python
messages.success(request, "후기를 저장했습니다.")
```

message는 중요한 데이터 저장소가 아닙니다. 처리 결과의 영속적인 기록은 database나 log에 남겨야 합니다.

## 공식 문서

- https://docs.djangoproject.com/en/5.2/topics/templates/
- https://docs.djangoproject.com/en/5.2/howto/static-files/
- https://docs.djangoproject.com/en/5.2/ref/contrib/messages/
