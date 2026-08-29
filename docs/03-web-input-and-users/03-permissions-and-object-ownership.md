# 권한과 object ownership

## 학습 목표

- 로그인 여부와 특정 작업 권한을 따로 검사합니다.
- 작성자만 자신의 후기를 수정하거나 삭제하도록 제한합니다.
- staff 권한과 일반 사용자 권한을 구분합니다.
- 화면에서 button을 숨기는 것과 server 권한 검사가 다른 작업임을 이해합니다.

## 인증과 권한

- 인증: 사용자가 누구인지 확인
- 권한: 확인된 사용자가 이 작업을 해도 되는지 확인

로그인한 모든 사용자가 모든 후기를 수정할 수 있는 것은 아닙니다.

```python
def test_func(self):
    return self.get_object().author_id == self.request.user.id
```

Template에서 수정 button을 숨겨도 URL을 직접 호출할 수 있습니다. View에서 반드시 다시 검사해야 합니다.

## QuerySet에서 제한하기

다른 사용자의 object를 먼저 가져온 뒤 `if`로 검사하는 대신, 처음부터 현재 사용자가 소유한 row만 조회할 수 있습니다.

```python
Review.objects.filter(author=request.user)
```

Object가 없을 때 404를 반환하면 다른 사용자의 object 존재 여부도 노출하지 않습니다.

## `UserPassesTestMixin`

```python
class ReviewUpdateView(
    LoginRequiredMixin,
    UserPassesTestMixin,
    UpdateView,
):
    ...
```

권한이 없을 때 로그인 화면으로 계속 redirect하지 않도록 인증 여부와 `raise_exception` 동작을 확인합니다. 인증된 사용자에게는 403 또는 404 중 어느 결과가 적절한지 정합니다.

## Staff 권한

제보 승인과 거절은 일반 사용자가 호출할 수 없어야 합니다.

```python
if not reviewer.is_active or not reviewer.is_staff:
    raise PermissionDenied
```

Admin 화면에 접근할 수 있다는 사실만 믿지 않고, 실제 변경을 수행하는 service function에서도 staff 여부를 확인합니다. 그래야 management command나 다른 view가 service를 호출해도 같은 규칙이 유지됩니다.

## Django permission

Django는 model별 `add`, `change`, `delete`, `view` permission을 자동 생성합니다. Admin과 세밀한 역할 구분이 필요하면 group과 permission을 사용할 수 있습니다.

현재 project는 다음처럼 단순하게 제한합니다.

- 일반 사용자: 자신의 review와 submission
- staff: admin 접근과 submission 검수
- superuser: 모든 admin 권한

## Test해야 할 요청

- 비로그인 후기 작성
- 다른 사용자의 후기 수정·삭제
- 일반 사용자의 검수 service 호출
- draft Entry 상세 조회
- 본인 제보 목록에 다른 사용자 row가 포함되는지 여부

정상 요청만 검사하면 권한 누락을 찾기 어렵습니다.

## 공식 문서

- https://docs.djangoproject.com/en/5.2/topics/auth/default/#permissions-and-authorization
- https://docs.djangoproject.com/en/5.2/topics/class-based-views/mixins/
