---
title: "Unicode 정규화 메모"
summary: "겉보기에는 같은 문자열이 다른 코드 포인트로 표현될 때 비교, 검색과 식별자 생성을 어떻게 다룰지 정리합니다."
category: "data"
tags: ["Unicode", "문자열", "정규화"]
publishedAt: 2026-04-12
updatedAt: 2026-08-22
featured: true
draft: false
sourceUrl: "https://unicode.org/reports/tr15/"
---

문자열이 화면에서 같아 보여도 내부 코드 포인트 배열은 다를 수 있습니다. 특히 조합형 문자와 분해형 문자는 단순한 `===` 비교에서 다르게 처리될 수 있습니다.

## 비교 목적을 먼저 정합니다

- 사용자 검색: 대소문자, 공백, locale 규칙까지 함께 고려할 수 있습니다.
- 식별자: 한 번 정한 정규화 방식과 slug 생성 규칙을 바꾸면 기존 URL이 깨질 수 있습니다.
- 보안 판단: 비슷하게 보이는 다른 문자를 같은 값으로 취급하면 안 되는 경우가 있습니다.

## 필요한 위치에서만 정규화합니다

JavaScript의 `String.prototype.normalize()`는 `NFC`, `NFD`, `NFKC`, `NFKD`를 지원합니다. 원본을 보존해야 하는 데이터까지 무조건 덮어쓰지 말고, 비교용 값을 별도로 만들 수 있습니다.

```ts
const comparable = input.normalize("NFC");
```

## byte 길이와 문자 수를 구분합니다

문자열의 `length`는 UTF-16 code unit 수입니다. 화면 글자 수, Unicode code point 수와 UTF-8 byte 수가 모두 같다고 가정하지 않습니다.
