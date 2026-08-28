# 웹은 어떻게 동작하는가

브라우저 주소창에 URL을 입력하면 브라우저가 주소를 해석하고 서버에 HTTP 요청을 보냅니다. 서버의 응답이 HTML이면 브라우저는 문서를 만들고, 필요한 CSS와 JavaScript를 추가로 요청합니다. JSON API를 호출할 때도 같은 HTTP 규칙을 사용합니다.

처음부터 네트워크 세부 규칙을 모두 외울 필요는 없습니다. 다만 오류가 브라우저, 네트워크, 서버, 응답 해석 중 어디에서 발생했는지는 구분할 수 있어야 합니다.

## 목표

- URL의 스킴, 호스트, 포트, 경로, 쿼리, 프래그먼트를 구분합니다.
- HTTP 요청과 응답을 읽습니다.
- 연결 실패와 HTTP 오류 응답을 구분합니다.
- HTML, CSS, JavaScript, JSON이 각각 무엇을 전달하는지 설명합니다.
- 브라우저 개발자 도구에서 실제 요청을 확인합니다.

## URL 읽기

```text
https://example.com:443/boards/42?view=activity#latest
```

| 부분 | 의미 |
|---|---|
| `https` | 통신 방식과 TLS 사용 여부 |
| `example.com` | 연결할 호스트 이름 |
| `443` | 호스트 안에서 연결할 서비스 번호 |
| `/boards/42` | 서버가 처리할 경로 |
| `view=activity` | 조회 조건으로 전달하는 쿼리 문자열 |
| `latest` | 서버에는 보내지 않고 브라우저가 사용하는 문서 위치 |

`localhost`는 현재 컴퓨터를 뜻합니다. 같은 `localhost`라도 포트가 다르면 다른 프로세스에 연결할 수 있습니다.

```text
http://localhost:3000  → 프런트엔드 개발 서버
http://localhost:4000  → API 서버
localhost:5432         → PostgreSQL
```

## HTTP 요청과 응답

```http
GET /boards/42 HTTP/1.1
Host: localhost:4000
Accept: application/json
```

```http
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{"id":"42","title":"학습 보드"}
```

요청에는 메서드, 대상, 헤더, 필요하면 본문이 들어갑니다. 응답에는 상태 코드, 헤더, 필요하면 본문이 들어갑니다.

`404`나 `500`도 서버가 반환한 정상적인 HTTP 응답입니다. 반면 해당 포트에서 서버가 실행되지 않아 연결이 거부되면 상태 코드 자체가 없습니다.

| 관찰 결과 | 먼저 확인할 곳 |
|---|---|
| `ERR_CONNECTION_REFUSED` | 서버 프로세스와 포트 |
| `404` | 경로와 리소스 식별자 |
| `400` | 요청 본문·쿼리·헤더 값 |
| `500` | 서버 로그와 요청 ID |
| JSON 파싱 실패 | `Content-Type`과 실제 응답 본문 |
| 화면에 이전 데이터가 남음 | 요청 완료 순서, 캐시, 브라우저 상태 |

## HTML, CSS, JavaScript

```html
<h1>내 보드</h1>
<button type="button">새 보드</button>
```

```css
button { font: inherit; }
```

```js
document.querySelector("button")?.addEventListener("click", () => {
  console.log("클릭했습니다.");
});
```

- HTML은 콘텐츠의 의미와 문서 순서를 정합니다.
- CSS는 배치와 표현을 정합니다.
- JavaScript는 사용자 입력과 상태 변화에 따라 동작을 실행합니다.

의미 있는 버튼 대신 클릭 이벤트를 붙인 `div`를 사용하면 키보드 동작, 포커스, 비활성화 상태를 직접 구현해야 합니다. 브라우저가 이미 제공하는 기능을 먼저 사용합니다.

## 정적 파일과 API 요청

한 화면을 열 때도 여러 요청이 발생합니다.

```text
GET /             → HTML
GET /style.css    → CSS
GET /app.js       → JavaScript
GET /api/boards   → JSON 목록
POST /api/boards  → 서버 데이터 변경
```

개발자 도구의 Network 탭에서 다음 항목을 확인합니다.

- Request URL과 메서드
- 요청 헤더와 본문
- 응답 상태 코드
- 응답 헤더와 본문
- 요청 시작부터 완료까지 걸린 시간

Console 오류만 보지 말고 실제로 어떤 요청과 응답이 오갔는지 먼저 확인합니다.

## 브라우저의 입력은 신뢰하지 않습니다

브라우저 코드는 사용자 기기에서 실행됩니다. 사용자는 화면에 없는 요청을 직접 보내거나 JavaScript를 수정할 수 있습니다. 따라서 서버는 다음 값을 요청마다 다시 확인합니다.

- 본문, 경로, 쿼리, 헤더의 형식
- 로그인 상태와 세션 만료
- 대상 리소스를 읽거나 바꿀 권한
- 가격, 역할, 버전, 좌표처럼 서버가 정해야 하는 값
- 함께 성공해야 하는 데이터베이스 변경

브라우저 검증은 빠른 안내를 제공하지만 서버 검증을 대신하지 못합니다.

## 직접 확인하기

작은 정적 서버를 실행한 뒤 Network 탭에서 HTML, CSS, JavaScript 요청을 확인합니다. 존재하지 않는 경로를 열어 404를 확인하고, 서버를 종료한 뒤 같은 주소를 다시 열어 연결 실패와 비교합니다.

## 흔한 실수

- URL 전체를 하나의 문자열로만 보고 호스트·포트·경로 문제를 구분하지 않습니다.
- 연결 실패와 HTTP 오류 응답을 같은 문제로 취급합니다.
- TypeScript 클라이언트가 보낸 값이므로 서버에서 검사하지 않아도 된다고 생각합니다.
- 프런트엔드와 API가 항상 같은 프로세스에서 실행된다고 가정합니다.

## 완료 기준

- `http://localhost:3000/boards/1?q=mine`의 각 부분을 설명할 수 있습니다.
- 연결 실패, 404, 500, JSON 파싱 실패가 각각 어디에서 발생했는지 구분할 수 있습니다.
- Network 탭에서 요청 메서드, 상태 코드, 응답 본문을 확인할 수 있습니다.
- 브라우저 입력을 서버가 다시 검사해야 하는 이유를 설명할 수 있습니다.

## 다음 문서

폼과 문서 의미를 먼저 익히려면 [`HTML 폼과 접근성`](02-html-forms-accessibility.md)을 읽습니다. Core 학습을 이어 간다면 [`JavaScript 기초`](04-javascript-foundations.md)로 이동합니다.
