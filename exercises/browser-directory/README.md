# Browser Directory

URL의 `q` 쿼리를 기준으로 검색 화면을 복원하는 정적 문서 검색 애플리케이션입니다. 별도의 메모리 값에 검색어를 중복 저장하지 않으며, 뒤로 가기와 앞으로 가기 때 도착한 URL을 다시 읽습니다.

## 주요 기능

- 제목과 본문을 대상으로 한 대소문자 구분 없는 검색
- `?q=`에 검색어 저장
- 제출할 때 `history.pushState()`로 방문 기록 추가
- `popstate`에서 검색어와 결과 복원
- `createElement()`와 `textContent`를 사용한 결과 출력
- 본문 건너뛰기 링크, 입력 레이블, 결과 개수 알림
- 32rem 이하에서 세로로 바뀌는 검색 폼

## 실행

```sh
npm run serve
```

브라우저에서 `http://localhost:8080`을 엽니다. 검색어를 제출하면 주소에 `?q=`가 추가됩니다. 검색을 두 번 수행한 뒤 뒤로 가기를 눌러 이전 검색어와 결과가 함께 복원되는지 확인합니다.

## 테스트

```sh
npm test
```

테스트는 다음 잘못된 구현을 검출합니다.

- 검색 폼의 레이블이나 상태 알림을 제거함
- 검색어를 URL에 기록하지 않음
- `popstate`를 처리하지 않음
- 사용자 문자열을 `innerHTML`에 넣음
- 좁은 화면 처리와 포커스 표시를 제거함

## 코드 구성

- `index.html`: 검색 폼, 결과 영역과 키보드 탐색 요소
- `style.css`: 좁은 화면 배치, 긴 문자열 줄바꿈과 포커스 표시
- `app.js`: URL 읽기, 검색, DOM 생성과 방문 기록 처리
- `tests/static.test.mjs`: 외부에서 확인 가능한 HTML·CSS·JavaScript 조건 검사

## 주요 선택

- 검색어의 기준값은 현재 URL입니다. 새로고침하거나 링크를 공유해도 같은 화면을 만들 수 있습니다.
- 뒤로 가기 때 과거 메모리 값을 재사용하지 않고 이동한 URL을 다시 읽습니다.
- 검색 결과는 HTML 문자열로 만들지 않습니다. 문서 데이터가 마크업으로 실행되지 않게 모든 문자열을 `textContent`로 넣습니다.

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

## 범위와 제한

검색 데이터는 `app.js`에 고정되어 있습니다. 원격 검색 서버, 점수 기반 정렬, 오타 교정, 강조 표시와 페이지네이션은 포함하지 않습니다.
