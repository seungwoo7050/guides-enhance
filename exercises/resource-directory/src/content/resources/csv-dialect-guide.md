---
title: "CSV 방언 확인표"
summary: "구분자, 인용부호, 줄바꿈과 인코딩 차이로 CSV 해석이 달라지는 지점을 정리합니다."
category: "data"
tags: ["CSV", "Parser", "Encoding"]
publishedAt: 2026-01-22
updatedAt: 2026-08-11
featured: false
draft: false
---

CSV는 하나의 고정된 형식처럼 보이지만 실제 파일은 구분자, 인용 규칙, 줄바꿈과 문자 인코딩이 다를 수 있습니다. 확장자만 보고 parser 옵션을 결정하지 않습니다.

## 입력에서 확인할 항목

- 구분자가 comma인지 semicolon인지
- 첫 행이 header인지
- field 안의 줄바꿈을 허용하는지
- quote escaping이 `""`인지 다른 방식인지
- 빈 field와 누락 field를 구분하는지
- UTF-8 BOM이 있는지

## 한 줄씩 단순 분리하지 않습니다

인용된 field 안에 구분자와 줄바꿈이 들어갈 수 있으므로 `line.split(",")`는 일반 CSV parser가 아닙니다. 검증된 parser를 사용하고, 예상 column 수와 필수 값을 별도로 확인합니다.

## 원본 위치를 오류에 남깁니다

변환 실패 시 row 번호와 column 이름을 함께 남기면 어떤 입력을 고쳐야 하는지 바로 찾을 수 있습니다. 전체 row를 로그에 남길 때는 개인정보와 비밀값이 포함되지 않았는지 확인합니다.
