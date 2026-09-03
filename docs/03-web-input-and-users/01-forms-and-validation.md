# Form과 입력 검증

## 학습 목표

- bound form과 unbound form의 차이를 이해하고, GET과 POST에서 form instance를 만드는 이유를 구분합니다.
- Django form의 validation 순서를 이해하고, field 하나의 규칙과 여러 field를 함께 보는 규칙을 알맞은 위치에 둡니다.
- `ModelForm`에 사용자가 수정할 수 있는 field만 명시하고, server가 결정하는 값은 form 입력과 분리합니다.
- `commit=False`가 필요한 경우와 many-to-many 저장 시 `save_m2m()`이 필요한 이유를 설명할 수 있습니다.
- 검증 실패 시 사용자가 제출한 값과 오류가 들어 있는 같은 bound form을 다시 렌더링합니다.

## Form binding

Django form은 **HTTP method 자체가 아니라, form instance를 만들 때 data를 전달했는지**에 따라 bound/unbound가 결정됩니다.

- **unbound form**: 제출 data가 연결되지 않은 form입니다. 최초 입력 화면을 보여 줄 때 사용합니다.
- **bound form**: 제출 data가 연결된 form입니다. 입력값을 검증할 수 있고, 검증에 실패하면 제출값과 오류를 함께 다시 렌더링할 수 있습니다.

일반적인 생성 form은 GET에서 빈 form을 보여 주고, POST에서 제출값을 검증합니다.

```python
if request.method == "POST":
    form = ReviewForm(request.POST)
else:
    form = ReviewForm()
```

따라서 위 코드에서 POST branch의 `form`은 bound form이고, GET branch의 `form`은 unbound form입니다. 그러나 **GET 요청이라고 항상 unbound form인 것은 아닙니다.** 예를 들어 검색 조건을 query string으로 받는 form이라면 다음처럼 `request.GET`을 binding할 수 있습니다.

```python
form = SearchForm(request.GET)
```

즉, 핵심 기준은 `request.method`가 아니라 form 생성자에 `data`가 전달되었는지입니다.

빈 POST도 제출된 요청으로 검증해야 하므로, 생성/수정 form에서는 다음처럼 HTTP method를 기준으로 분기하는 방식이 명확합니다. `request.POST or None`처럼 truthiness로 binding 여부를 결정하면 빈 POST가 `None`으로 바뀌어 required 오류를 검증하지 못할 수 있습니다.

## Validation과 `cleaned_data`

bound form에 대해 보통 `is_valid()`를 호출하여 검증을 시작합니다.

```python
if form.is_valid():
    body = form.cleaned_data["body"]
```

검증은 개념적으로 다음 순서로 진행됩니다.

```text
브라우저가 보낸 원시 값
→ 각 Field의 값 변환과 기본 검증
→ clean_<field>()
→ Form.clean()
→ cleaned_data와 errors
```

각 `Field`는 먼저 문자열 같은 원시 입력을 적절한 Python 값으로 변환하고(`to_python()`), field 자체의 규칙과 validator를 검사합니다. 예를 들어 `IntegerField`가 성공적으로 처리한 값은 `cleaned_data`에서 문자열이 아니라 `int`로 사용할 수 있습니다.

`cleaned_data`는 단순히 `request.POST`를 복사한 dictionary가 아닙니다. **검증과 정규화를 통과한 값**이 들어 있습니다. 특정 field가 검증에 실패했다면 그 field는 `cleaned_data`에 없을 수 있으므로, 다른 field까지 함께 검사하는 단계에서는 값이 항상 존재한다고 가정하면 안 됩니다.

또한 invalid bound form도 제출된 원시 값을 보존합니다. 따라서 같은 form instance를 다시 template에 전달하면 사용자가 입력한 값과 해당 오류를 함께 보여 줄 수 있습니다.

> 일반적인 코드에서는 `is_valid()`를 명시적으로 호출합니다. `form.errors` 접근도 내부적으로 validation을 일으킬 수 있지만, 처리 흐름을 분명하게 하기 위해 `is_valid()`를 기준으로 분기하는 편이 좋습니다.

## `ModelForm`

model을 생성하거나 수정하는 form이라면 `ModelForm`을 사용해 model field와 form field의 연결을 재사용할 수 있습니다.

```python
from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("rating", "body")
```

`fields`는 단순한 표시 목록이 아니라 **사용자가 form을 통해 수정할 수 있는 model field의 허용 목록**으로 생각하는 것이 안전합니다.

```python
fields = "__all__"
```

처럼 모든 field를 자동 포함하면, 나중에 model에 새로운 field가 추가됐을 때 의도하지 않은 값까지 form에서 수정 가능해질 수 있습니다. 특히 권한, 소유자, moderation 상태처럼 server가 통제해야 하는 field가 추가되면 보안 문제가 될 수 있습니다. 따라서 사용자 입력으로 허용할 field를 명시합니다.

예를 들어 다음 값은 보통 form에서 제외합니다.

- `author`: 현재 인증된 사용자처럼 request context가 결정하는 값
- `entry`: URL이나 server-side 조회 결과로 결정하는 연결 대상
- moderation 상태: 관리자나 별도 workflow가 결정하는 값
- 내부 audit field: 생성 주체, 처리 상태 등 client가 선택해서는 안 되는 값

이런 값을 `<input type="hidden">`으로 숨기는 것만으로는 보호할 수 없습니다. hidden input도 client가 변경해서 보낼 수 있으므로, 신뢰해야 하는 값은 request나 server 상태에서 다시 결정해야 합니다.

## Field 하나의 검증

field 하나만 보면 판단할 수 있는 규칙은 `clean_<field>()`에 둡니다.

```python
from django import forms


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("rating", "body")

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if len(body) < 10:
            raise forms.ValidationError("후기는 10자 이상 작성해 주세요.")
        return body
```

`clean_body()`가 호출될 때는 `body` field의 기본 변환과 field-level validation이 이미 성공한 상태이므로 `self.cleaned_data["body"]`에서 변환된 값을 읽습니다.

이 method는 검증만 하는 곳이 아니라 field 값을 **정규화(normalization)** 하는 곳으로도 사용할 수 있습니다. 위 예제에서는 앞뒤 공백을 제거한 `body`를 반환하므로, 이후 `cleaned_data["body"]`와 `ModelForm` 저장에는 공백이 제거된 값이 사용됩니다.

반드시 값을 반환해야 합니다. 반환값이 해당 field의 최종 cleaned value가 됩니다.

여러 form에서 재사용할 수 있고 field 하나의 값만 필요한 규칙이라면 `clean_<field>()`에 반복해서 작성하기보다 validator로 분리하는 것도 적합합니다.

## 여러 field를 함께 보는 검증

두 개 이상의 field 관계를 확인해야 하는 규칙은 form의 `clean()`에 둡니다.

예를 들어 낮은 평점에는 이유를 충분히 적도록 요구한다고 가정할 수 있습니다.

```python
class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("rating", "body")

    def clean(self):
        cleaned_data = super().clean()
        rating = cleaned_data.get("rating")
        body = cleaned_data.get("body")

        if rating is not None and rating <= 2 and body and len(body) < 30:
            raise forms.ValidationError(
                "평점이 2점 이하라면 이유를 30자 이상 작성해 주세요."
            )

        return cleaned_data
```

여기서는 `cleaned_data.get()`을 사용합니다. `clean()`이 실행되기 전에 각 field 검증은 진행되지만, 어떤 field는 이미 실패하여 `cleaned_data`에서 제거되었을 수 있기 때문입니다.

`clean()`에서 직접 `ValidationError`를 raise하면 특정 field 하나가 아니라 form 전체에 해당하는 **non-field error**가 됩니다. template에서는 `{{ form.non_field_errors }}`로 표시할 수 있습니다.

오류를 특정 field에 연결하는 편이 사용자에게 더 명확하다면 `add_error()`를 사용할 수 있습니다.

```python
def clean(self):
    cleaned_data = super().clean()
    rating = cleaned_data.get("rating")
    body = cleaned_data.get("body")

    if rating is not None and rating <= 2 and body and len(body) < 30:
        self.add_error(
            "body",
            "평점이 2점 이하라면 이유를 30자 이상 작성해 주세요.",
        )

    return cleaned_data
```

`add_error()`로 오류가 추가된 field의 값은 `cleaned_data`에서 제거되므로, 이후 처리에서는 해당 값이 유효하다고 가정하면 안 됩니다.

## Form validation, Model validation, database constraint

검증 위치는 모두 같은 역할을 하지 않습니다.

### Form validation

Form은 **현재 입력 화면과 요청에 맞는 검증과 오류 표시**를 담당합니다.

예:

- 후기 본문 최소 길이
- 특정 선택값에 따라 다른 field가 필요한 규칙
- 사용자가 바로 수정할 수 있도록 이해하기 쉬운 오류 메시지 제공

`ModelForm.is_valid()`는 form field 검증뿐 아니라 연결된 model instance의 model validation도 validation 과정에 포함합니다. 다만 form에서 제외한 model field는 상황에 따라 해당 검증에서 제외될 수 있으므로, form 검증만으로 database invariant 전체가 보장된다고 생각하면 안 됩니다.

### Model validation

`Model.clean()`은 form 이외의 생성 경로에서도 공유해야 하는 **model-level 규칙**을 표현하는 데 적합합니다.

예를 들어 model의 두 속성 조합 자체가 어떤 입력 경로에서도 유효해야 한다면 model validation이 더 자연스러운 위치일 수 있습니다.

중요한 점은 일반적인 `model.save()`가 자동으로 `full_clean()`을 호출하지 않는다는 것입니다. 따라서 `ModelForm`을 거치지 않고 model을 직접 생성하는 코드가 있다면, model validation이 언제 실행되는지 별도로 설계해야 합니다.

### Database constraint

중복, 범위, 관계처럼 **어떤 쓰기 경로에서도 반드시 지켜져야 하는 invariant**는 database constraint로도 보호해야 합니다.

예:

- `UniqueConstraint`: 같은 사용자가 같은 항목에 후기를 하나만 작성할 수 있음
- `CheckConstraint`: 허용된 범위나 조건을 database 수준에서 강제
- foreign key / NOT NULL 등 schema가 보장하는 관계와 필수값

Form validation은 좋은 오류 메시지를 제공하지만, application에서 먼저 중복 여부를 검사한 직후 다른 요청이 같은 값을 저장할 수도 있습니다. database constraint는 이런 동시성 상황에서도 최종 invariant를 지키는 경계입니다.

세 위치에 같은 코드를 기계적으로 복사하기보다 책임을 나눕니다.

```text
Form
→ 현재 입력 화면에서 빠른 피드백과 요청별 규칙

Model
→ Python 객체 수준에서 공유할 domain 검증

Database constraint
→ 모든 쓰기 경로에서 반드시 유지할 최종 invariant
```

## 저장 시 server 값 추가

`author`, `entry`처럼 form에서 받지 않은 값을 저장 전에 넣어야 한다면 `save(commit=False)`를 사용합니다.

```python
review = form.save(commit=False)
review.author = request.user
review.entry = entry
review.save()
```

`form.save(commit=False)`는 form의 검증된 값으로 `Review` instance를 만들지만 아직 database에는 저장하지 않습니다. 따라서 server가 결정해야 하는 값을 채운 뒤 `review.save()`를 호출할 수 있습니다.

`commit=False`는 validation을 대신하지 않습니다. 반드시 `form.is_valid()`가 성공한 이후에 호출해야 합니다.

```python
if form.is_valid():
    review = form.save(commit=False)
    review.author = request.user
    review.entry = entry
    review.save()
```

### Many-to-many field가 있는 경우

many-to-many 관계는 대상 model instance가 먼저 database에 저장되어 primary key를 가져야 저장할 수 있습니다. 따라서 `commit=False`를 사용했고 form이 many-to-many field도 처리한다면 instance 저장 후 `form.save_m2m()`을 호출합니다.

```python
review = form.save(commit=False)
review.author = request.user
review.entry = entry
review.save()
form.save_m2m()
```

`commit=False` 없이 `form.save()`가 직접 instance를 저장하는 경우에는 `ModelForm`이 many-to-many data도 함께 처리하므로 별도의 `save_m2m()` 호출이 필요하지 않습니다.

## 성공 후 redirect와 검증 실패 시 재렌더링

생성 form의 일반적인 처리 흐름은 다음과 같습니다.

```text
GET
→ 빈 form 렌더링

POST
→ bound form 생성
→ validation
   ├─ 실패: 같은 bound form 재렌더링
   └─ 성공: 저장 → redirect
```

성공 시에는 보통 **POST/Redirect/GET(PRG)** 패턴을 사용합니다.

```text
POST form 제출
→ validation 성공
→ 저장
→ redirect 응답
→ 상세 화면 GET
```

redirect 후 브라우저의 현재 화면은 GET 결과가 되므로, 새로고침으로 같은 POST가 다시 전송되어 중복 저장되는 위험을 줄일 수 있습니다.

반대로 validation 실패 시에는 redirect하지 않습니다. redirect하면 현재 bound form에 들어 있는 오류와 제출값을 다음 요청에 자동으로 전달할 수 없기 때문입니다. 같은 form instance를 바로 template에 전달합니다.

```python
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ReviewForm
from .models import Entry


def create_review(request, entry_id):
    entry = get_object_or_404(Entry, pk=entry_id)

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.author = request.user
            review.entry = entry
            review.save()
            return redirect("entry-detail", pk=entry.pk)
    else:
        form = ReviewForm()

    return render(
        request,
        "reviews/review_form.html",
        {"form": form, "entry": entry},
    )
```

POST가 invalid이면 `if form.is_valid()` 내부로 들어가지 않고 마지막 `render()`까지 내려갑니다. 이때 `form`은 **오류와 사용자가 제출한 값이 들어 있는 동일한 bound form**입니다. `render()`의 기본 응답 status는 `200`이므로 일반적인 HTML form에서는 그대로 입력 화면을 다시 보여 줄 수 있습니다.

다음처럼 invalid POST에서 새 form을 만들면 안 됩니다.

```python
if not form.is_valid():
    form = ReviewForm()  # 잘못된 예: 제출값과 validation error를 잃는다.
```

## Template에서 오류와 입력값 표시

Django form field를 그대로 렌더링하면 bound form의 제출값이 다시 표시됩니다. field 오류와 non-field 오류도 함께 보여 주어 사용자가 무엇을 수정해야 하는지 알 수 있게 합니다.

```django
<form method="post">
    {% csrf_token %}

    {{ form.non_field_errors }}

    <div>
        {{ form.rating.label_tag }}
        {{ form.rating }}
        {{ form.rating.errors }}
    </div>

    <div>
        {{ form.body.label_tag }}
        {{ form.body }}
        {{ form.body.errors }}
    </div>

    <button type="submit">저장</button>
</form>
```

invalid POST를 같은 `form`으로 재렌더링하면 사용자는 입력값을 다시 작성할 필요 없이 오류가 난 부분만 수정할 수 있습니다.

## File upload

파일을 받는 form은 일반 POST data와 별도로 file data를 binding해야 합니다.

```python
form = UploadForm(request.POST, request.FILES)
```

HTML `<form>`에도 `multipart/form-data` encoding이 필요합니다.

```html
<form method="post" enctype="multipart/form-data">
    ...
</form>
```

`request.FILES`는 `multipart/form-data`로 전송된 upload data를 담습니다. 둘 중 하나가 빠지면 file field가 정상적으로 binding되지 않습니다.

업로드 파일은 신뢰할 수 없는 입력입니다. 확장자나 사용자가 보낸 MIME type만 신뢰하지 말고, application 요구사항에 따라 다음을 검토해야 합니다.

- 허용 가능한 파일 크기
- 실제 파일 형식과 내용
- 저장 위치와 파일명 처리
- 업로드된 파일이 실행 가능한 content로 제공되지 않도록 하는 web server/storage 설정

이 project는 파일 업로드를 포함하지 않습니다.

## 핵심 정리

```text
최초 GET
→ unbound form을 보여 준다.

POST 제출
→ request.POST를 전달한 bound form을 만든다.
→ is_valid()로 변환과 validation을 실행한다.

field 하나의 규칙
→ clean_<field>() 또는 재사용 가능한 validator

여러 field의 관계
→ Form.clean()

사용자가 수정할 model field
→ ModelForm.Meta.fields에 명시한다.

server가 결정하는 값
→ form에서 제외하고 save(commit=False) 후 설정한다.

validation 실패
→ redirect하지 않고 같은 bound form을 다시 렌더링한다.

validation 성공
→ 저장 후 redirect한다.

반드시 지켜야 하는 invariant
→ 필요한 경우 database constraint로 최종 보장한다.
```

## 공식 문서

- https://docs.djangoproject.com/en/5.2/topics/forms/
- https://docs.djangoproject.com/en/5.2/topics/forms/modelforms/
- https://docs.djangoproject.com/en/5.2/ref/forms/validation/
- https://docs.djangoproject.com/en/5.2/ref/forms/api/
- https://docs.djangoproject.com/en/5.2/ref/models/instances/#validating-objects
