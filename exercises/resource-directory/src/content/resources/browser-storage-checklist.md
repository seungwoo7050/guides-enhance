---
title: "브라우저 저장소 점검표"
summary: "localStorage, sessionStorage와 cookie를 선택할 때 수명, 공개 범위와 실패 처리를 확인합니다."
category: "web"
tags: ["Browser", "Storage", "보안"]
publishedAt: 2026-03-05
updatedAt: 2026-08-18
featured: false
draft: false
---

브라우저 저장소는 사용하기 쉽지만 서버와 동기화되는 데이터베이스가 아닙니다. 값의 수명, 다른 탭과의 공유 여부, 사용자가 저장소를 지웠을 때의 동작을 먼저 정합니다.

## 저장 위치를 고릅니다

- `localStorage`: origin 단위로 유지되며 브라우저를 다시 열어도 남습니다.
- `sessionStorage`: 현재 탭의 수명 동안 유지됩니다.
- cookie: 요청과 함께 서버로 보낼 필요가 있을 때 사용합니다. 크기와 보안 속성을 함께 관리해야 합니다.

## 읽을 때도 검사합니다

저장된 JSON은 이전 버전의 코드가 남긴 값이거나 사용자가 직접 바꾼 값일 수 있습니다. `JSON.parse()` 성공만 확인하지 말고 배열, 문자열과 허용된 필드를 검사합니다.

```ts
const value: unknown = JSON.parse(raw);
if (!Array.isArray(value)) return [];
return value.filter((entry): entry is string => typeof entry === "string");
```

## 실패해도 기능을 막지 않습니다

저장소가 차단되거나 quota를 초과할 수 있습니다. 즐겨찾기 같은 보조 기능은 저장 실패를 처리하되 본문을 읽는 기본 기능까지 막지 않도록 분리합니다.
