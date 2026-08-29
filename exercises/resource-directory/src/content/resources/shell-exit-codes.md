---
title: "Shell 종료 상태 사용법"
summary: "명령의 stdout과 stderr를 종료 상태와 분리하고 자동화에서 실패를 놓치지 않는 방법을 정리합니다."
category: "tooling"
tags: ["Shell", "CLI", "자동화"]
publishedAt: 2026-05-02
updatedAt: 2026-08-24
featured: true
draft: false
---

명령이 text를 출력했다고 성공한 것은 아닙니다. 자동화는 stdout, stderr와 process 종료 상태를 각각 확인해야 합니다.

## 성공과 결과를 분리합니다

일반적으로 종료 상태 `0`은 성공, 그 외 값은 실패를 나타냅니다. 다만 일부 명령은 검색 결과 없음처럼 정상적인 분기를 별도 상태로 표현하므로 해당 명령의 문서를 확인합니다.

```sh
command >result.txt 2>error.txt
status=$?
```

`$?`는 바로 앞 명령의 상태이므로 다른 명령을 실행하기 전에 저장합니다.

## Pipeline 실패를 숨기지 않습니다

Shell에 따라 pipeline의 마지막 명령만 성공하면 전체가 성공으로 보일 수 있습니다. Bash에서는 필요한 script에 `set -o pipefail`을 적용하고, 각 명령의 실패가 어떤 결과를 남기는지 확인합니다.

## 신호 종료를 기록합니다

하위 process가 signal로 종료되었는지와 일반 exit code를 구분하면 timeout, 사용자의 취소와 application 오류를 다르게 진단할 수 있습니다.
