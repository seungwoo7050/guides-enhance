# Field Notes

Field Notes는 통신이 불안정한 현장에서 기록, 사진과 선택적 위치 정보를 기기에 먼저 저장한 뒤 서버와 동기화하는 Expo 기반 모바일 앱입니다.

단순한 화면 예제가 아닙니다. SQLite 트랜잭션, 앱 전용 파일 저장, outbox, 명령 중복 처리, 버전 충돌, 백그라운드 실행 기회, 알림 진입과 릴리스 근거 검사를 하나의 독립 프로젝트에 연결합니다.

## 주요 기능

- `Record` 생성, 수정, 삭제와 outbox 명령 생성을 하나의 SQLite 트랜잭션으로 처리합니다.
- 카메라와 사진 선택기가 반환한 임시 URI를 앱 전용 경로로 복사하고 체크섬과 크기를 확인합니다.
- 카메라, 선택기, 포그라운드 위치 측정의 가용 여부와 권한 상태를 별도 값으로 처리합니다.
- outbox 명령을 lease로 선점하고 응답 유실이나 로컬 처리 결과 저장 실패 뒤에도 같은 최초 시도 명령을 다시 보냅니다.
- 원격 버전 충돌이 발생하면 최초 시도 명령, 현재 로컬 값과 원격 값을 함께 보존합니다.
- 충돌 해결 시 원격 적용, 로컬 재전송, 병합 중 하나를 선택하고 새 명령을 만듭니다.
- 수동 실행, 앱 활성화, 백그라운드와 알림이 같은 제한 시간형 동기화 작업자를 사용합니다.
- 커스텀 scheme, Expo 개발 URL과 복원 경로를 같은 파서로 검증합니다.
- 저장하지 않은 초안이 있으면 외부 링크와 알림 이동을 보류합니다.
- 알림 데이터를 현재 계정과 기록 상태에 대조하고 화면 이동이 끝난 뒤 메시지 선점을 완료합니다.
- Android 알림 채널, 권한, 푸시 토큰과 설치·계정 연결을 별도 상태로 처리합니다.
- 백그라운드 작업은 사용자가 명시적으로 등록하거나 해제합니다. 운영체제가 콜백을 주지 않아도 다음 포그라운드 실행에서 대기 중인 명령을 처리할 수 있습니다.
- 개발, 미리보기와 운영 빌드가 서로 다른 애플리케이션 ID와 URL scheme을 사용합니다.
- EAS 프로필과 Android와 iOS 릴리스 근거가 같은 소스, 앱 버전과 런타임 후보를 가리키는지 검사합니다.
- 실패 재현 서버에서 응답 유실, 지연, 401, 잘못된 본문과 버전 감소를 같은 입력으로 반복 재현합니다.

## 디렉터리 구성

```text
field-notes/
├── apps/
│   └── mobile/                 Expo Router 앱과 Expo 어댑터
├── packages/
│   ├── core/                   Record 상태, 호출 형식, 화면 이동과 기기 결과 처리
│   ├── fault-server/           같은 실패를 반복 재현하는 테스트 서버
│   ├── sync-engine/            명령, lease, 재시도, 결과 저장과 충돌 처리
│   ├── lifecycle-engine/       백그라운드 실행과 알림 처리
│   └── release-contract/       EAS 프로필과 릴리스 근거 검사
├── scripts/
│   └── verify-source.mjs       독립 실행 구성과 Implementation Order 검사
├── package.json
└── tsconfig.json
```

`apps/mobile`은 화면, Expo API 연결, SQLite 어댑터와 실행 시 사용할 서비스를 만듭니다. `packages/*`는 React Native와 Expo 없이 실행할 수 있는 TypeScript로 작성해 동기화와 알림 상태를 결정적으로 검사합니다.

## 요구 사항

- Node.js `24.19.0`
- npm `11.17.x`
- Android 실행: Android Studio와 Android SDK
- iOS 실행: macOS, Xcode와 CocoaPods
- 실제 카메라, 선택기, 위치, 알림과 백그라운드 검증: Expo 개발용 빌드와 실제 기기

## 설치

```sh
npm install
cp apps/mobile/.env.example apps/mobile/.env.local
```

개발 프로필은 `EXPO_PUBLIC_FIELD_NOTES_SYNC_URL`이 없으면 `http://127.0.0.1:8787`을 사용합니다. 실제 기기에서 로컬 실패 재현 서버에 연결할 때는 `127.0.0.1` 대신 개발 PC의 내부 네트워크 주소를 지정합니다.

미리보기와 운영 프로필은 동기화 URL을 반드시 지정해야 합니다. 값은 절대 `http` 또는 `https` URL이어야 합니다.

| 프로필 | 애플리케이션 ID | URL scheme |
|---|---|---|
| `development` | `dev.seungwoo7050.fieldnotes.development` | `fieldnotes-development` |
| `preview` | `dev.seungwoo7050.fieldnotes.preview` | `fieldnotes-preview` |
| `production` | `dev.seungwoo7050.fieldnotes` | `fieldnotes` |

## 실행

먼저 실패 재현 서버를 실행합니다.

```sh
npm run start --workspace=@field-notes/fault-server
```

다른 터미널에서 Expo 개발 클라이언트를 시작합니다.

```sh
npm start
```

네이티브 프로젝트를 생성하고 실행하려면 다음 명령을 사용합니다.

```sh
npm run android
npm run ios
```

이 프로젝트는 개발용 빌드를 기준으로 합니다. Expo Go에서 일부 JavaScript 화면이 보이더라도 권한 설정, 백그라운드 작업, 원격 알림과 설치된 제품 바이너리를 확인한 것으로 보지 않습니다.

## 로컬 저장과 동기화

사용자의 변경은 네트워크 요청보다 먼저 저장됩니다.

```text
기록 변경
→ SQLite에서 기록과 outbox 명령을 함께 커밋
→ 실행 가능한 명령을 lease로 선점
→ HTTP 요청
→ 응답 필드 검증
→ 명령 결과를 한 번만 기록
→ 현재 기록과 아직 보내지 않은 명령 조정
```

첫 선점에서는 다음 값을 최초 시도 명령으로 고정합니다.

```text
commandId
recordId
작업
baseVersion
localRevision
데이터 또는 tombstone
createdAt
```

응답을 받지 못했거나 서버 성공 뒤 로컬 처리 결과 저장이 실패해도 성공으로 추측하지 않습니다. Lease가 만료되면 같은 최초 시도 명령을 다시 보냅니다. 실패 재현 서버는 같은 `commandId`에 이전 결과를 반환하므로 원격 변경을 중복 적용하지 않습니다.

앞선 명령을 보내는 동안 같은 기록이 다시 수정되면 현재 로컬 데이터를 유지합니다. 앞선 명령의 성공으로 받은 원격 버전만 저장하고, 아직 한 번도 보내지 않은 대기 중인 명령을 새 명령 ID와 새 기준 버전으로 교체합니다.

## 충돌 처리

서버의 현재 버전이 명령의 `baseVersion`과 다르면 다음 값을 저장합니다.

- 처음 보낸 최초 시도 명령
- 현재 로컬 데이터와 로컬 리비전
- 서버의 현재 데이터와 버전
- 충돌이 생긴 시각

사용자는 다음 중 하나를 선택할 수 있습니다.

- 원격 값을 적용합니다.
- 현재 로컬 값을 서버 현재 버전을 기준으로 다시 보냅니다.
- 두 값을 합친 데이터로 새 명령을 만듭니다.

원 충돌 명령을 그대로 다시 보내지 않습니다. 해결 결과는 새 명령 ID로 기록합니다. 충돌 뒤에 같은 기록으로 쌓인 아직 보내지 않은 명령은 `superseded`로 종료하고 사용자가 선택한 상태만 전송합니다.

## 첨부 파일 소유

선택기나 카메라가 반환한 URI를 장기 저장 값으로 사용하지 않습니다.

```text
임시 URI
→ 임시 저장 경로로 복사
→ 파일 존재, 체크섬, 바이트 크기 확인
→ 앱이 관리하는 영구 저장 경로로 이동
→ SQLite에 첨부 파일 메타데이터 추가
```

메타데이터 추가가 실패하면 새 파일을 제거합니다. 프로세스가 중간에 종료되면 파일과 SQLite가 어긋날 수 있으므로 시작 절차에서 다음 상태를 확인합니다.

- 메타데이터가 없는 미참조 파일
- 메타데이터는 있지만 실제 파일이 없는 첨부 파일
- 남아 있는 임시 저장 파일과 부분 파일

파일 시스템과 SQLite가 하나의 원자 트랜잭션이라고 가정하지 않습니다.

## 카메라, 선택기와 위치

`DeviceFeatureCoordinator`는 플랫폼 API가 반환한 값을 애플리케이션이 처리할 수 있는 상태로 바꿉니다.

- 기기 기능: `available`, `limited`, `unavailable`
- 권한: `not-required`, `not-determined`, `granted`, `limited`, `denied`, `restricted`
- 미디어 결과: `acquired`, `cancelled`, `failed`, `interrupted`
- 위치 결과: `measured`, `permission-revoked`, `unavailable`, `failed`

권한은 사용자가 실제 기능을 선택했을 때 요청합니다. 위치를 거절하거나 카메라를 사용할 수 없어도 텍스트 기록은 저장할 수 있습니다.

Android에서 선택기 실행 중 프로세스가 종료된 경우 플랫폼 대기 중인 결과를 다시 읽습니다. 같은 작업을 두 번 처리하지 않도록 작업 ID를 선점합니다.

## 알림과 백그라운드 작업

백그라운드 작업 등록은 정확한 실행 시각을 보장하지 않습니다. 설정 화면에서 등록하면 운영체제에 최소 간격을 요청할 뿐입니다.

화면 없는 콜백을 받은 경우 다음 순서로 실행합니다.

```text
SQLite 저장소 열기
→ 자동 동기화 설정 확인
→ 마감 시각과 AbortSignal 준비
→ 포그라운드와 같은 작업자 실행
→ 선점한 명령 수와 저장한 처리 결과 수 비교
```

선점한 명령마다 처리 결과가 저장된 경우에만 성공을 반환합니다. 콜백을 받지 못하거나 시간이 끝난 명령은 다음 앱 활성화 또는 수동 동기화에서 처리합니다.

알림은 기록 내용을 포함하지 않습니다. 스키마 버전, 메시지 ID, 계정 ID와 불투명한 기록 ID를 검증한 뒤 현재 데이터베이스 상태를 다시 읽어 경로를 정합니다.

```text
데이터 검증
→ 저장소 준비
→ 현재 계정 확인
→ 메시지 ID를 lease로 선점
→ 현재 기록과 충돌 상태 확인
→ 경로 적용
→ 메시지 처리 완료 기록
```

저장하지 않은 초안이 있으면 선점을 해제하고 네이티브 응답을 남깁니다. 초안이 닫힌 뒤 명시적으로 다시 처리할 수 있습니다.

딥 링크와 알림이 동시에 같은 경로를 요청하면 프로세스 안의 경로 예약이 중복 이동을 줄입니다. 이 메모리 집합은 알림의 저장된 선점 기록이나 프로세스 간 중복 처리를 대신하지 않습니다.

## 릴리스 근거 도구

합성 Android와 iOS 시험 데이터의 일관성을 검사합니다.

```sh
npm run validate:fixtures --workspace=@field-notes/release-contract
npm run validate:eas --workspace=@field-notes/release-contract
```

실제 매니페스트 두 개를 검사하려면 다음 명령을 사용합니다.

```sh
npm run validate:release -- path/to/android.json path/to/ios.json
```

`.xcarchive`나 시뮬레이터 `.app`처럼 디렉터리 자체가 산출물인 경우 정규화된 트리 해시값을 계산합니다.

```sh
npm run digest:directory-tree -- /absolute/path/FieldNotes.xcarchive
```

검증기 성공은 제출한 값이 서로 모순되지 않는다는 뜻입니다. 네이티브 빌드, 서명 신뢰, 실제 설치, 스토어 승인과 원격 업데이트 전달을 직접 확인하지 않습니다.

## 자동 검사

```sh
npm run verify
```

다음 항목을 확인합니다.

- 화면 이동 입력 검증과 중복 경로 처리
- 저장하지 않은 초안의 뒤로 가기·딥 링크·알림 처리
- 실패 재현 서버의 명령 중복 처리와 응답 유실
- 최초 시도 명령, lease 만료, 재시도, 인증 차단, 처리 결과 저장 실패
- 더 최신인 로컬 편집을 보존하고 아직 보내지 않은 명령의 기준 버전을 갱신
- 충돌 해결과 대체된 명령 처리
- 앱 수명에 따른 실행 계기 합치기와 마감 시각 전달
- 알림 스키마, 저장된 선점 기록과 현재 저장 상태에 따른 화면 이동
- Android 채널 → 권한 → 토큰 호출 순서
- 토큰 교체, 계정 전환과 오래된 로그아웃 보호
- Expo 권한과 설정과 프로필별 앱 식별 정보
- EAS 프로필 역할과 Android와 iOS 릴리스 후보 일관성
- 소스 주석과 README의 구현 순서 일치
- 상위 저장소를 벗어나는 상대 import가 없는지 확인

모바일 앱의 TypeScript와 번들은 의존성 설치 뒤 별도로 확인합니다.

```sh
npm run typecheck --workspace=@field-notes/mobile
npm run bundle:android --workspace=@field-notes/mobile
npm run bundle:ios --workspace=@field-notes/mobile
```

## 주요 구현 선택

### 저장과 outbox를 함께 저장합니다

기록만 커밋한 뒤 outbox 추가 전에 프로세스가 종료되면 서버로 보낼 근거가 사라집니다. 반대로 명령만 남고 기록 변경이 실패해서도 안 됩니다. 두 행을 같은 SQLite 트랜잭션에서 처리합니다.

### Lease와 서버의 명령 ID를 함께 사용합니다

Lease는 여러 작업자가 같은 명령을 동시에 가져가는 일을 줄입니다. 네트워크 전송이 정확히 한 번만 일어나게 하지는 못합니다. 서버가 `commandId`로 이전 결과를 기억해야 응답 유실 뒤 재전송을 안전하게 처리할 수 있습니다.

### 플랫폼 결과를 불리언 하나로 줄이지 않습니다

권한 거절, 제한된 권한, 기기 기능 없음, 사용자 취소와 프로세스 중단은 다음 동작이 다릅니다. 어댑터는 플랫폼 원본 값을 명시적인 결과로 바꿉니다.

### 릴리스 완료를 자동으로 승인하지 않습니다

산출물 이름이나 빌드 프로필만 보고 빌드, 서명, 설치와 스토어 배포를 완료했다고 판단하지 않습니다. 각 결과는 정확한 산출물 참조와 실제 관찰 자료를 가리켜야 합니다. 실행하지 않은 항목은 `not-run`으로 남깁니다.

## 구현 순서

아래 순서는 파일 순서가 아니라 프로젝트를 처음부터 만들 때 필요한 선후관계를 나타냅니다. 소스의 각 `[Implementation N]` 주석과 정확히 일치합니다.

| 순서 | 구현 항목 | 주요 위치 |
|---:|---|---|
| `0` | 프로세스가 사용할 저장소·파일·기기 기능·동기화 서비스를 생성합니다 | `apps/mobile/src/application/FieldNotesRuntime.tsx` |
| `1` | 기록·첨부 파일·outbox·충돌·화면 이동 상태를 정의합니다 | `packages/core/src/contracts.ts` |
| `1-1` | 저장소·파일·기기 API·세션·동기화 전송 호출 형식을 정의합니다 | `packages/core/src/ports.ts` |
| `2` | 화면 이동 입력을 검증하고 중복 요청을 거른 뒤 안전한 경로를 선택합니다 | `packages/core/src/navigation.ts` |
| `3` | 프로세스 재시작 뒤 복원할 SQLite 테이블을 만들고 마이그레이션합니다 | `apps/mobile/src/storage/SQLiteFieldNotesRepository.ts` |
| `3-1` | 기록 변경과 outbox 명령 추가를 하나의 트랜잭션으로 커밋합니다 | `apps/mobile/src/storage/SQLiteFieldNotesRepository.ts` |
| `3-2` | 선택한 파일을 앱 저장소로 옮기고 시작할 때 누락·미참조 파일을 정리합니다 | `apps/mobile/src/storage/attachment-files.ts` |
| `4` | 카메라·사진 선택기·위치·권한·중단 결과를 앱이 처리할 상태로 변환합니다 | `packages/core/src/device-coordinator.ts` |
| `5` | 각 명령을 한 번만 적용하고 원격 처리 실패를 결정적으로 재현합니다 | `packages/fault-server/src/server.ts` |
| `6` | 명령의 최초 시도 사본·lease·재시도·처리 결과·충돌을 저장합니다 | `packages/sync-engine/src/repository.ts` |
| `6-1` | 처리 결과를 기록하기 전에 응답 ID·버전·필수 값을 검증합니다 | `packages/sync-engine/src/response-parser.ts` |
| `6-2` | 제한 시간 안에 명령을 가져오고 결과를 모르는 요청은 같은 명령으로 재시도합니다 | `packages/sync-engine/src/worker.ts` |
| `6-3` | 새 명령으로 충돌을 해결하고 아직 보내지 않은 명령만 새 기준 버전으로 바꿉니다 | `packages/sync-engine/src/repository.ts` |
| `7` | 제한 시간형 동기화 작업자를 SQLite 저장소와 HTTP 전송에 연결합니다 | `apps/mobile/src/sync/production-sync.ts` |
| `8` | 수동·앱 활성화·백그라운드·알림 실행에서 같은 동기화 작업자를 호출합니다 | `packages/lifecycle-engine/src/sync-coordinator.ts` |
| `8-1` | 알림 ID를 먼저 저장하고 현재 저장 상태를 조회해 이동할 화면을 정합니다 | `packages/lifecycle-engine/src/notification.ts` |
| `8-2` | Android 알림 채널 생성·권한 확인·푸시 토큰 요청 순서를 고정합니다 | `packages/lifecycle-engine/src/android-registration.ts` |
| `8-3` | 오래된 로그아웃이 새 계정을 지우지 않도록 설치·계정·토큰 연결을 갱신합니다 | `packages/lifecycle-engine/src/installation-coordinator.ts` |
| `9` | 화면에서 저장·사진·동기화·백그라운드·알림 기능을 호출할 수 있게 제공합니다 | `apps/mobile/src/application/FieldNotesRuntime.tsx` |
| `10` | EAS 빌드 프로필과 Android·iOS 릴리스 후보 근거가 서로 일치하는지 검증합니다 | `packages/release-contract/src/validate.ts` |
| `11` | 서로 모순되는 릴리스 근거를 거부하고 프로젝트 전체 불변식을 회귀 테스트로 확인합니다 | `packages/release-contract/tests/release-contract.test.ts` |

## 범위와 제한

- 첨부 파일 업로드 의존성과 재개 가능한 업로드는 구현하지 않습니다. 현재 동기화 대상은 기록 명령입니다.
- 인증 정보 발급과 갱신 전체는 구현하지 않습니다. 401 뒤 명령을 보존하고 외부 인증 회복 후 다시 실행하는 지점까지만 제공합니다.
- 실패 재현 서버는 운영 인가, 데이터베이스, 백업, 요청 제한과 운영 관찰 기능을 대신하지 않습니다.
- 운영체제가 백그라운드 콜백을 주는 시각과 빈도는 앱이 보장할 수 없습니다.
- 푸시 토큰 획득은 제공자 수락, 백엔드 등록, 알림 전달과 사용자 탭을 의미하지 않습니다.
- 릴리스 검증기는 제출한 근거의 형식과 연결 관계를 검사합니다. 산출물 바이트와 서명을 직접 확인하지 않습니다.
- Android와 iOS 네이티브 동작은 각 플랫폼의 개발용 빌드와 실제 기기에서 별도로 확인해야 합니다.
