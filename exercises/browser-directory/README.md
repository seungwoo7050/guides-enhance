# Browser Directory

URL의 `q` 쿼리를 **검색 화면의 기준 상태(source of truth)** 로 사용하는 정적 문서 검색 애플리케이션입니다. 검색어를 별도의 메모리 상태에 중복 저장하지 않고, 현재 URL을 읽어 입력값과 결과를 복원합니다.

이 구조에서는 다음 두 상태가 서로 어긋나는 문제를 피할 수 있습니다.

```text
메모리 검색어 = "react"
URL ?q=css
```

검색어의 기준을 URL 하나로 두면 새로고침, 링크 공유, 뒤로 가기와 앞으로 가기가 모두 같은 복원 규칙을 사용합니다.

## 주요 기능

- 제목과 본문을 대상으로 한 대소문자 구분 없는 검색
- `?q=`에 검색어 저장
- 검색 제출 시 `history.pushState()`로 새 방문 기록 추가
- `popstate`에서 이동한 URL을 다시 읽어 검색어와 결과 복원
- `createElement()`와 `textContent`를 사용한 결과 출력
- 본문 건너뛰기 링크, 입력 레이블, 결과 개수 상태 알림
- 32rem 이하에서 세로로 바뀌는 검색 폼

## 실행

```sh
npm run serve
```

브라우저에서 `http://localhost:8080`을 엽니다.

다음 흐름으로 URL과 화면 상태가 함께 움직이는지 확인합니다.

```text
첫 검색 제출
→ URL에 ?q=... 추가
→ 검색어와 결과 갱신

두 번째 검색 제출
→ 새 history entry 추가
→ 새 결과 표시

브라우저 뒤로 가기
→ 이전 URL로 이동
→ popstate 발생
→ 이동한 URL의 q를 다시 읽음
→ 입력값과 결과 복원
```

중요한 점은 뒤로 가기 때 과거의 JavaScript 변수 값을 복원하는 것이 아니라 **브라우저가 실제로 이동한 현재 URL을 다시 해석한다는 것**입니다.

## 검색 상태와 URL

검색 제출 시 쿼리는 `URLSearchParams` 같은 URL API를 이용해 기록합니다.

개념적인 흐름은 다음과 같습니다.

```text
사용자 입력
→ q 정규화
→ 현재 URL 객체 생성
→ searchParams.set("q", query)
→ history.pushState(...)
→ 현재 URL을 다시 기준으로 화면 렌더링
```

빈 검색어를 어떻게 표현할지는 프로젝트의 기존 구현 규칙을 따릅니다. 중요한 것은 화면과 URL이 서로 다른 값을 독립적으로 들고 있지 않게 하는 것입니다.

## 뒤로 가기와 앞으로 가기

`history.pushState()`를 호출한다고 `popstate`가 즉시 발생하는 것은 아닙니다. `popstate`는 사용자가 뒤로 가기나 앞으로 가기 등으로 다른 history entry로 이동할 때 처리합니다.

따라서 두 동작의 책임을 구분합니다.

```text
검색 제출
→ pushState
→ 새 URL 기준으로 즉시 렌더링

뒤로/앞으로 이동
→ popstate
→ 도착한 URL 기준으로 다시 렌더링
```

이 구분이 없으면 검색 제출 직후 화면은 바뀌지 않거나, 뒤로 가기 때 URL과 화면이 어긋날 수 있습니다.

## 안전한 결과 렌더링

검색 결과의 제목과 본문은 데이터이므로 HTML 코드로 해석하지 않습니다.

다음처럼 문자열을 HTML에 직접 결합하면:

```js
results.innerHTML = `<li>${document.title}</li>`;
```

문서 데이터에 마크업이 포함되었을 때 의도하지 않은 HTML이 만들어질 수 있습니다.

이 프로젝트는 DOM 노드를 직접 만들고 문자열은 `textContent`로 넣습니다.

```text
createElement()
→ textContent
→ append()
```

즉 검색 데이터는 **표시할 텍스트**이고, 실행할 HTML 템플릿이 아닙니다.

## 접근성

검색 화면은 포인터만 사용할 수 있는 UI가 되지 않도록 다음 요소를 포함합니다.

- 검색 입력과 연결된 명시적 레이블
- 키보드 사용자가 반복되는 상단 UI를 건너뛸 수 있는 본문 건너뛰기 링크
- 검색 결과 개수를 알리는 상태 영역
- 키보드 포커스를 시각적으로 확인할 수 있는 스타일
- 좁은 화면에서도 입력과 버튼이 잘리지 않는 배치

검색 결과가 바뀌었다는 사실은 시각적으로만 나타내지 않고 상태 알림으로도 전달합니다.

## 반응형 레이아웃

32rem 이하에서는 검색 폼을 세로 방향으로 바꿉니다.

이 기준은 "특정 기기 이름"을 의미하는 것이 아니라, 가로 공간이 좁아져 한 줄 배치가 불편해지는 구간입니다.

또한 긴 제목이나 본문 문자열이 컨테이너 밖으로 넘치지 않도록 줄바꿈 규칙을 둡니다.

## 테스트

```sh
npm test
```

테스트는 외부에서 관찰 가능한 HTML·CSS·JavaScript 조건을 검사하며, 다음 잘못된 구현을 검출해야 합니다.

- 검색 폼의 레이블을 제거함
- 결과 개수 상태 알림을 제거함
- 검색어를 URL에 기록하지 않음
- `popstate`를 처리하지 않음
- 사용자 문자열을 `innerHTML`에 넣음
- 좁은 화면 처리를 제거함
- 키보드 포커스 표시를 제거함

테스트는 내부 함수 이름보다 최종 동작을 기준으로 이해합니다.

```text
URL을 공유하면 같은 검색 화면을 복원할 수 있는가?
뒤로 가기 후 이전 검색 결과가 돌아오는가?
문서 문자열이 HTML로 실행되지 않는가?
키보드 사용자가 검색 폼을 이해하고 조작할 수 있는가?
```

## 코드 구성

- `index.html`: 검색 폼, 결과 영역과 키보드 탐색 요소
- `style.css`: 좁은 화면 배치, 긴 문자열 줄바꿈과 포커스 표시
- `app.js`: URL 읽기, 검색, DOM 생성과 방문 기록 처리
- `tests/static.test.mjs`: 외부에서 확인 가능한 HTML·CSS·JavaScript 조건 검사

## 주요 선택

- 검색어의 기준값은 현재 URL입니다. 새로고침하거나 링크를 공유해도 같은 화면을 만들 수 있습니다.
- 뒤로 가기 때 과거 메모리 값을 재사용하지 않고 이동한 URL을 다시 읽습니다.
- 검색 결과는 HTML 문자열로 만들지 않습니다. 문서 데이터가 마크업으로 실행되지 않게 모든 문자열을 `textContent`로 넣습니다.
- 브라우저 history와 화면 상태를 서로 다른 저장소처럼 운영하지 않고 URL 해석 규칙 하나로 연결합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | --- | --- |
| 1 | Search form semantics | `index.html` |
| 2 | Narrow-screen layout and keyboard focus | `style.css` |
| 3 | Search data and required DOM references | `app.js` |
| 4 | Query parsing from the current URL | `app.js` |
| 5 | Text-only result rendering | `app.js` |
| 6 | Form submission and history entry | `app.js` |
| 7 | Back and forward restoration | `app.js` |

이 순서는 먼저 접근 가능한 정적 구조를 만들고, 그 위에 URL 기반 상태와 history 동작을 차례로 연결하도록 되어 있습니다.

## 범위와 제한

검색 데이터는 `app.js`에 고정되어 있습니다. 원격 검색 서버, 점수 기반 정렬, 오타 교정, 검색어 강조 표시와 페이지네이션은 포함하지 않습니다.

따라서 이 exercise의 핵심은 검색 알고리즘 고도화가 아니라 다음 기본기를 확인하는 것입니다.

```text
URL을 상태의 기준으로 사용
history와 popstate 처리
안전한 DOM 생성
기본 접근성
좁은 화면 대응
```