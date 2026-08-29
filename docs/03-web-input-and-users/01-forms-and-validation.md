# Form과 입력 검증

## 학습 목표

- GET과 POST에서 form instance를 만드는 방법을 구분합니다.
- field별 검증과 여러 field를 함께 보는 검증을 알맞은 위치에 둡니다.
- `ModelForm`의 저장 대상 field를 명시합니다.
- 검증 실패 시 입력값과 오류를 그대로 다시 보여 줍니다.

## Form binding

```python
if request.method == "POST":
    form = ReviewForm(request.POST)
else:
    form = ReviewForm()
```

POST data를 전달한 form은 bound form입니다. `is_valid()`를 실행하면 field 변환과 validation이 진행되고 `cleaned_data`가 만들어집니다.

## ModelForm

```python
class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("rating", "body")
```

`fields = "__all__"`을 사용하면 나중에 model field가 추가됐을 때 사용자가 수정하면 안 되는 값까지 form에 노출될 수 있습니다. 화면에서 받을 field를 명시합니다.

`author`, `entry`, moderation field처럼 request나 server가 결정하는 값은 form에서 제외하고 view에서 설정합니다.

## Field 검증

field 하나만 보는 규칙은 `clean_<field>()`에 둡니다.

```python
def clean_body(self):
    body = self.cleaned_data["body"].strip()
    if len(body) < 10:
        raise forms.ValidationError("후기는 10자 이상 작성해 주세요.")
    return body
```

여러 field를 함께 확인해야 하면 `clean()`을 사용합니다. 단, 각 field가 이미 실패했을 수 있으므로 `cleaned_data.get()`으로 값의 존재 여부를 확인합니다.

## Model validation과 database constraint

Form은 사용자에게 이해할 오류를 보여 주는 첫 단계입니다. Model `clean()`은 여러 입력 경로에서 공유할 model-level 규칙에 적합합니다. 중복과 범위처럼 반드시 지켜야 하는 조건은 database constraint도 필요합니다.

세 위치에 같은 검사를 그대로 복사하지 않습니다. 각 위치가 어떤 요청을 막는지 구분합니다.

## 저장 시 server 값 추가

```python
review = form.save(commit=False)
review.author = request.user
review.entry = entry
review.save()
```

`commit=False`로 만든 instance는 아직 database에 저장되지 않았습니다. Many-to-many field를 form에서 받는다면 instance 저장 후 `form.save_m2m()`도 호출해야 합니다.

## 성공 후 redirect

```text
POST form 제출
→ validation
→ 저장
→ redirect
→ 상세 화면 GET
```

검증 실패 시에는 redirect하지 않습니다. 오류가 들어 있는 같은 form을 status 200으로 다시 렌더링합니다.

## File upload

파일을 받는 form은 `request.FILES`와 `multipart/form-data`가 필요합니다. 업로드 파일은 신뢰할 수 없는 입력입니다. 확장자만 검사하지 말고 크기, 실제 내용, 저장 위치, web server가 실행 파일로 처리하지 않는지도 확인해야 합니다.

이 project는 파일 업로드를 포함하지 않습니다.

## 공식 문서

- https://docs.djangoproject.com/en/5.2/topics/forms/
- https://docs.djangoproject.com/en/5.2/topics/forms/modelforms/
- https://docs.djangoproject.com/en/5.2/ref/forms/validation/
