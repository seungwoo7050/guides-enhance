# 모바일 애플리케이션 개발

이 저장소는 웹 애플리케이션을 만들어 본 개발자가 Android와 iOS에서 동작하는 모바일 앱을 설계하고 검증하는 데 필요한 기반을 정리합니다. 문서를 모두 읽는 것으로 끝내지 않고, `Field Notes`를 실행·수정·검증하면서 개념을 실제 상태 변화와 실패 상황에 연결합니다.

기준 구현은 TypeScript, React Native, Expo를 사용합니다. 특정 프레임워크 사용법을 외우는 것이 목적은 아닙니다. 앱 프로세스가 종료되거나 네트워크가 끊기고 권한이 철회되는 상황에서도 사용자가 저장한 내용을 보존하고, 설치된 네이티브 바이너리와 JavaScript 코드가 서로 호환되는지 판정할 수 있는 수준을 목표로 합니다.

## 완료 후 갖춰야 할 능력

이 저장소를 마치면 다음 내용을 코드와 실행 결과를 근거로 설명할 수 있어야 합니다.

- JavaScript 프로세스, 설치된 네이티브 바이너리, 운영체제가 각각 무엇을 소유하는지 구분합니다.
- 화면에만 필요한 상태와 프로세스 종료 뒤에도 남아야 하는 상태를 나눕니다.
- 딥 링크, 알림, 복원된 경로를 검증한 뒤 현재 저장 상태에 맞는 화면을 엽니다.
- `Record` 변경과 outbox 명령 생성을 하나의 SQLite 트랜잭션으로 처리합니다.
- 응답 유실, 중복 전송, 순서 역전, 인증 만료, 버전 충돌 뒤에도 사용자의 변경을 보존합니다.
- 카메라, 사진 선택기, 포그라운드 위치 측정의 가용 여부와 권한 상태를 따로 처리합니다.
- 백그라운드 작업을 보장된 일정이 아니라 제한된 실행 기회로 다룹니다.
- Android와 iOS의 설정, 빌드 결과, 앱 식별 정보, runtimeVersion, 서명과 배포 근거를 구분합니다.
- 모델 테스트, 어댑터 테스트, 통합 테스트, 실제 기기 검사가 각각 무엇을 확인하고 무엇을 확인하지 못하는지 설명합니다.

## 저장소 구성

```text
.
├── .gitignore
├── README.md
├── docs/
│   ├── 00-roadmap.md
│   ├── 01-mobile-runtime-and-project-boundaries.md
│   ├── 02-layout-input-and-accessibility.md
│   ├── 03-navigation-links-and-state-restoration.md
│   ├── 04-networking-session-and-error-contracts.md
│   ├── 05-local-data-offline-and-sync.md
│   ├── 06-permissions-device-capabilities-and-privacy.md
│   ├── 07-background-work-notifications-and-lifecycle.md
│   ├── 08-native-boundary-kotlin-swift-and-builds.md
│   ├── 09-testing-performance-and-observability.md
│   └── 10-release-signing-updates-and-store-delivery.md
└── exercises/
    └── field-notes/
```

- `docs/`는 모바일 앱에서 반복해서 마주치는 실행 수명, 저장, 기기 기능, 네이티브 빌드와 배포 문제를 설명합니다.
- `exercises/field-notes/`는 기록·사진·선택적 위치를 기기에 저장하고 나중에 서버와 동기화하는 완성된 애플리케이션입니다. 별도의 학습자 작업 공간이나 정답 구현에 의존하지 않습니다.

## 필수 문서

다음 문서는 최소 완료 경로에 포함합니다.

1. [`00-roadmap.md`](docs/00-roadmap.md)
2. [`01-mobile-runtime-and-project-boundaries.md`](docs/01-mobile-runtime-and-project-boundaries.md)
3. [`02-layout-input-and-accessibility.md`](docs/02-layout-input-and-accessibility.md)
4. [`03-navigation-links-and-state-restoration.md`](docs/03-navigation-links-and-state-restoration.md)
5. [`05-local-data-offline-and-sync.md`](docs/05-local-data-offline-and-sync.md)
6. [`06-permissions-device-capabilities-and-privacy.md`](docs/06-permissions-device-capabilities-and-privacy.md)
7. [`07-background-work-notifications-and-lifecycle.md`](docs/07-background-work-notifications-and-lifecycle.md)
8. [`08-native-boundary-kotlin-swift-and-builds.md`](docs/08-native-boundary-kotlin-swift-and-builds.md)
9. [`09-testing-performance-and-observability.md`](docs/09-testing-performance-and-observability.md)
10. [`10-release-signing-updates-and-store-delivery.md`](docs/10-release-signing-updates-and-store-delivery.md)

[`04-networking-session-and-error-contracts.md`](docs/04-networking-session-and-error-contracts.md)는 보강 문서입니다. HTTP 응답 분류, 인증 정보 수명, 401 처리나 오래된 응답이 익숙하지 않을 때 `05`와 동기화 구현 사이에서 읽습니다.

## 권장 진행 순서

문서를 전부 읽은 뒤 구현을 시작하지 않습니다. 의미 있는 코드를 작성할 수 있을 만큼만 읽고 바로 `Field Notes`에서 확인합니다.

```text
00
→ 01·02·03
→ Field Notes: 실행 환경, 상태 형식과 화면 이동

→ 05 전반
→ Field Notes: SQLite, outbox와 앱이 소유한 파일

→ 06·08 전반
→ Field Notes: 카메라, 사진 선택기, 위치와 네이티브 설정

→ 05 후반
→ Field Notes: 실패 재현 서버, 재시도, 충돌과 동기화 작업자

→ 07
→ Field Notes: 백그라운드 작업과 알림 처리

→ 08 후반·09·10
→ Field Notes: 네이티브 빌드 검토, 테스트와 릴리스 근거

→ Android·iOS 실제 기기 확인
→ 부족한 문서만 다시 읽기
```

세부 순서와 단계별 완료 조건은 [`docs/00-roadmap.md`](docs/00-roadmap.md)에 있습니다.

## 실습 프로젝트 실행

```sh
cd exercises/field-notes
npm install
npm run verify
```

Expo 앱을 실행하는 방법, 환경 변수, 실패 재현 서버, Android와 iOS 빌드 명령은 [`exercises/field-notes/README.md`](exercises/field-notes/README.md)에서 확인합니다.

자동 검사는 상태 전이, SQLite 사용 규칙, 응답 검증, 알림 처리와 릴리스 근거 형식을 확인합니다. 다음 항목은 자동 검사만으로 완료했다고 볼 수 없습니다.

- 실제 Android와 iOS 권한 대화 상자
- 카메라, 사진 선택기, 위치 제공자의 실제 동작
- 운영체제가 백그라운드 콜백을 주는지 여부
- 푸시 제공자와 실제 알림 전달
- 서명 인증 정보의 소유와 신뢰
- 스토어 업로드, 검토, 단계적 배포
- TalkBack과 VoiceOver 사용성

실행하지 못한 항목은 통과로 추정하지 않고 `미검사`로 기록합니다.

## 완료 기준

다음 조건을 모두 충족하면 이 저장소의 필수 경로를 마친 것으로 봅니다.

- 필수 문서의 상태 소유자, 상태를 바꾸는 사건, 실패 뒤 남아야 하는 값을 설명할 수 있습니다.
- `Field Notes`의 구현 순서와 주요 소스를 따라가며 저장부터 동기화·알림·배포 검증까지 연결할 수 있습니다.
- 프로젝트 자체의 타입 검사와 테스트가 통과합니다.
- 프로세스 종료, 이전 DB 마이그레이션, 오프라인 저장, 응답 유실, 중복 요청, 충돌, 권한 거절·철회를 재현합니다.
- Android와 iOS 개발용 빌드에서 핵심 작업을 확인합니다.
- 실제로 만들고 설치한 산출물과 소스, 앱 버전, 빌드 번호, runtimeVersion을 연결합니다.
- 확인하지 않은 플랫폼, 기기, 서명, 스토어 범위를 명시합니다.

이 저장소는 Kotlin·Swift 언어 전체, Android와 iOS 네이티브 전문 개발, 푸시와 백엔드 운영을 대신하지 않습니다. 이후 좁은 전문 영역은 실제 제품에서 필요해질 때 다시 학습합니다.
