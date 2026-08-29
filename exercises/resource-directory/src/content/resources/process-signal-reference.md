---
title: "Process signal 처리 참고"
summary: "SIGTERM, SIGINT와 강제 종료의 차이를 이해하고 하위 process를 남기지 않는 종료 순서를 정리합니다."
category: "tooling"
tags: ["Process", "Signal", "Cleanup"]
publishedAt: 2026-02-28
updatedAt: 2026-08-15
featured: false
draft: false
---

자동화가 server process를 시작했다면 성공과 실패 모두에서 종료해야 합니다. 부모 process만 끝내고 자식 process가 남으면 다음 실행에서 port 충돌이나 데이터 오염이 발생할 수 있습니다.

## 정상 종료 기회를 줍니다

먼저 `SIGTERM`을 보내고 제한 시간 동안 종료를 기다립니다. process가 종료되지 않을 때만 `SIGKILL`을 사용합니다. `SIGKILL`은 cleanup handler를 실행할 기회를 주지 않습니다.

## Process group을 확인합니다

`npm run`이나 shell wrapper가 실제 server를 다시 실행할 수 있습니다. Unix 환경에서는 별도 process group으로 시작한 뒤 group에 signal을 보내야 하위 process까지 정리할 수 있습니다.

## 두 실패를 함께 남깁니다

검증 자체의 실패와 process cleanup 실패가 동시에 발생할 수 있습니다. cleanup 오류로 원래 실패를 덮어쓰지 말고 두 원인을 모두 보고합니다.
