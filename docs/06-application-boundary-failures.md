# 애플리케이션에서 발생하는 대표 보안 실패

애플리케이션 취약점을 “입력 검증 부족”이라는 한 문장으로 묶으면 원인과 수정 범위를 놓치기 쉽습니다. 어떤 값이 어디에서 명령·path·resource ID·상태 변경 조건으로 사용됐는지, 누가 그 값을 다시 확인해야 하는지 구체적으로 봅니다.

## 1. 입력값이 어떤 용도로 쓰이는지 확인하기

다음 질문으로 시작합니다.

```text
입력이 query, command, template 또는 path로 해석됩니까?
resource 접근 가능 여부를 어느 함수가 판정합니까?
caller가 보낸 identity·URL·type을 왜 신뢰합니까?
검사한 뒤 실제 사용 전에 상태가 바뀔 수 있습니까?
업무 순서와 수량 제한을 어디에서 강제합니까?
```

## 2. 데이터와 interpreter를 분리하기

SQL, shell, template, 정규식과 표현식 언어는 문자열을 명령으로 해석할 수 있습니다.

유지해야 할 상태:

```text
사용자가 보낸 값은 명령의 문법을 바꾸지 않습니다.
허용한 operation과 parameter만 interpreter에 전달합니다.
```

대표 원인:

- 문자열을 이어 붙여 code와 data를 섞음
- 허용 operation이 아닌 임의 표현식을 전달함
- parameter API를 사용하다 중간 layer에서 다시 문자열로 조합함
- 여러 단계에서 서로 다른 escape를 적용함

검사할 내용:

- 실제 interpreter 호출까지 parameterization이 유지되는지
- 정상값과 문법을 바꾸려는 값의 결과가 어떻게 다른지
- 오류나 처리 시간 차이로 내부 상태가 드러나는지
- 같은 helper를 거치지 않는 다른 call site가 있는지

수정은 입력에서 몇 글자를 지우는 방식보다 code와 data를 API 수준에서 분리하고 허용 operation을 제한하는 방식이 적합합니다.

## 3. 출력 위치에 맞게 표현하기

외부 값이 HTML body, attribute, URL, JavaScript, CSS와 JSON에 들어갈 때 필요한 처리는 서로 다릅니다.

```text
신뢰하지 않는 값은 출력 위치의 문법을 벗어나 실행 가능한 코드가 되지 않습니다.
```

저장할 때 한 번 sanitize했다고 모든 출력 위치가 안전해지지는 않습니다. Framework의 context-aware encoding과 안전한 DOM API를 사용하고, server rendering, client rendering, preview, export와 email처럼 같은 값이 다시 출력되는 곳을 확인합니다.

CSP는 실행을 줄이는 보조 수단일 수 있지만 잘못된 출력 처리를 고치는 대신 사용할 수는 없습니다.

## 4. Object authorization

로그인과 route role 검사가 있어도 요청한 resource의 소유자를 확인하지 않으면 다른 사용자의 데이터에 접근할 수 있습니다.

```text
모든 resource action은 subject, action, resource와 현재 context를 함께 판정합니다.
```

잘못된 가정:

- identifier를 모르면 접근할 수 없음
- list에서 걸렀으므로 detail route도 안전함
- gateway가 확인했으므로 internal service는 다시 볼 필요가 없음
- cache key에 tenant·permission을 넣지 않아도 됨
- background worker가 자신의 broad identity로 사용자를 대신해도 됨

최소 검사표:

| subject | resource | action | 기대 결과 |
|---|---|---|---|
| owner | own | read | 허용 |
| other user | foreign | read | 거절 |
| same role | other tenant | read | 거절 |
| revoked user | former own | read | 거절 |
| worker | current job | read | 허용 |
| worker | other job | read | 거절 |

거절 여부만 보지 않습니다. Foreign data가 응답·log·cache에 남지 않았는지, downstream 호출과 상태 변경이 없었는지도 확인합니다.

## 5. Server-side request

애플리케이션이 사용자가 보낸 URL이나 redirect를 따라 요청하면 public 입력이 internal network 접근으로 바뀔 수 있습니다.

```text
Server-side fetch는 승인한 protocol, 목적지, address 범위와 redirect 규칙 안에서만 동작합니다.
검사한 목적지와 실제 연결한 peer가 같은 판정을 만족해야 합니다.
```

확인할 내용:

- scheme, hostname과 port 해석
- DNS가 반환한 모든 address
- redirect마다 새 URL과 address를 다시 확인하는지
- IPv4·IPv6와 대체 표기
- localhost, metadata service와 control plane
- proxy·service mesh가 추가하는 접근 가능 범위
- response 크기, 시간과 content type 한도
- 실제 연결한 peer와 TLS hostname·certificate

URL 문자열 allowlist와 연결 전에 한 번 수행한 DNS 검사만으로 충분하지 않습니다. 검사가 끝난 뒤 DNS 결과나 redirect 대상이 바뀔 수 있기 때문입니다. Egress proxy가 대신 판정한다면 원래 목적지와 각 redirect를 proxy가 확인하고 결과를 별도 event로 남겨야 합니다.

## 6. File, path와 upload

대표적인 잘못된 가정:

- filename을 그대로 storage path로 써도 됨
- extension이 실제 content type을 증명함
- archive entry가 대상 directory 안에 머묾
- path를 검사한 뒤 다시 열어도 같은 file임
- symlink·hard link·rename 경쟁이 없음

유지해야 할 상태:

```text
caller가 보낸 이름을 storage identity로 사용하지 않습니다.
쓰기 대상은 지정한 root 밖으로 나가지 않습니다.
검사한 file과 실제 처리하는 file이 같습니다.
```

`canonicalize → root 안인지 확인 → path로 다시 open` 순서는 검사와 사용 사이에 대상이 바뀔 수 있습니다. 지원되는 환경에서는 신뢰한 directory descriptor를 기준으로 상대 경로를 열고, symlink를 따르지 않으며, open한 descriptor의 type과 identity를 확인합니다. 임시 파일을 완전히 검사한 뒤 원자적으로 공개합니다.

Upload 처리에는 크기, 파일 수, 압축 해제 크기, CPU·시간 한도를 둡니다. 처리 실패 뒤 임시 file과 object가 남는지도 확인합니다.

## 7. Deserialization

외부 데이터가 runtime type, constructor, hook와 object graph를 선택하게 하면 단순 데이터가 실행 동작을 결정할 수 있습니다.

- 단순한 data schema를 사용합니다.
- 허용 type과 field를 명시합니다.
- parser의 깊이·크기·시간을 제한합니다.
- signature가 있어도 위험한 object graph 자체가 안전해지는 것은 아님을 구분합니다.
- version, migration과 unknown field 처리 규칙을 정합니다.

## 8. 업무 상태 변경

문법상 올바른 요청도 업무 순서를 깨뜨릴 수 있습니다.

- 승인 전에 지급
- 같은 coupon·refund를 여러 번 사용
- 병렬 요청으로 한도 검사 우회
- 한 사용자의 1단계 결과를 다른 사용자가 2단계에서 사용
- client가 가격·role·완료 상태를 직접 지정

Endpoint별 검사가 아니라 상태 변경으로 봅니다.

```text
현재 상태 + actor + command + 사전 조건
→ 허용된 다음 상태 또는 거절
```

## 9. 동시성 및 검사·사용 사이 변경

다음 작업은 검사와 변경을 따로 하면 경쟁 상태가 생길 수 있습니다.

- quota 확인 뒤 차감
- permission 확인 뒤 owner 변경
- one-time token 확인 뒤 소비
- 재고 확인 뒤 예약
- path 확인 뒤 file open

Lock 하나를 무조건 추가하는 것이 답은 아닙니다. 정본에서 atomic update, unique constraint, compare-and-set, transaction, idempotency key와 state version으로 상태 변경을 묶습니다.

## 10. 오류와 side channel

응답 body가 없어도 status, 길이, 처리 시간, retry 여부와 log로 상태가 드러날 수 있습니다.

- account·resource 존재 여부
- permission 판정 차이
- secret 비교 시간
- parser 오류의 내부 path·query
- retryable·non-retryable 구분

사용자 응답에는 필요한 정보만 제공하고, 운영자가 조사할 상세 정보는 접근이 제한된 event에 남깁니다.

## 완료 질문

- “입력을 검증합니다”보다 interpreter와 사용 위치를 구체적으로 적어야 하는 이유는 무엇입니까?
- authentication과 object authorization은 어떻게 다릅니까?
- URL allowlist 하나로 server-side request를 제한하기 어려운 이유는 무엇입니까?
- path를 확인한 뒤 다시 open하면 어떤 경쟁 상태가 남을 수 있습니까?
- transaction이 있어도 업무 규칙이 깨질 수 있는 경우는 무엇입니까?
