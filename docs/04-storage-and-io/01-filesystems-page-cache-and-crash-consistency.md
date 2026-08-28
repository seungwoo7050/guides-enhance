# 파일시스템, page cache와 장애 일관성

## 학습 목표

- path, directory entry, inode, cached data와 durable data를 구분합니다.
- file `fsync`, directory `fsync`, atomic rename과 journal commit이 각각 무엇을 보장하는지 설명합니다.
- crash 지점마다 남을 수 있는 상태를 나누고 recovery가 같은 작업을 두 번 적용하지 않도록 검증합니다.

## path와 data는 다른 상태입니다

단순화한 Unix 계열 파일시스템에서 path는 다음 객체를 연결합니다.

```text
path component
→ directory entry
→ inode 또는 file object
→ metadata
→ data block 또는 page cache 내용
```

`rename`은 이름을 바꾸고, `link`와 `unlink`는 inode를 가리키는 이름 수를 바꾸며, `write`는 file content를 바꿉니다. 이 연산들은 서로 다른 값을 갱신합니다.

다음 관계가 항상 맞아야 합니다.

```text
유효한 directory entry는 존재하는 inode를 가리킵니다.
inode link count는 현재 namespace의 참조 수와 맞습니다.
free block은 어떤 live file에도 속하지 않습니다.
한 block을 충돌하는 두 file에 동시에 할당하지 않습니다.
file size와 data block 목록이 모순되지 않습니다.
```

실제 filesystem에는 open-but-unlinked file, snapshot과 delayed allocation이 추가되지만, 이름, object와 data를 나누어 보는 것이 출발점입니다.

## file descriptor와 이름의 수명

process가 file을 열면 descriptor는 path가 아니라 open file object를 참조합니다. 이후 이름을 삭제해도 descriptor가 남아 있으면 같은 object를 계속 사용할 수 있습니다.

```text
open("log")
→ descriptor가 file object 참조

unlink("log")
→ directory entry 제거, link count 감소

process가 descriptor 유지
→ data 접근 가능

마지막 이름과 마지막 open reference 제거
→ object와 block 회수 가능
```

파일 이름이 보이지 않는다고 storage 공간이 즉시 회수됐다고 단정할 수 없습니다.

## buffered write와 page cache

일반적인 write는 먼저 memory의 page cache를 바꿀 수 있습니다.

```text
application write
→ page cache 변경
→ dirty 표시
→ application에 성공 반환 가능
→ background writeback
→ device cache
→ non-volatile media
```

`write` 성공만으로 다음을 모두 보장하지는 않습니다.

- file data가 non-volatile media에 도달했습니다.
- file size와 inode metadata가 durable합니다.
- 새 file name이 parent directory에 남습니다.
- rename 결과가 crash 뒤에도 남습니다.
- device의 volatile cache가 flush됐습니다.

정확한 보장은 API, filesystem, mount option과 hardware에 따라 달라집니다.

## file과 directory durability

새 file을 만드는 과정을 단순화하면 다음과 같습니다.

```text
1. inode 생성
2. directory entry 추가
3. data write
4. file data flush
5. directory metadata flush
```

4까지만 끝난 뒤 crash가 발생하면 data object가 storage에 있어도 이름이 남지 않을 수 있습니다. 반대로 directory entry가 먼저 남고 data가 준비되지 않으면 이전 값이나 불완전한 값을 볼 수 있습니다.

`kernel-model`은 다음 값을 따로 보관합니다.

- 현재 `directory`
- crash 뒤 남을 `durable_directory`
- 현재 `cached_data`
- crash 뒤 남을 `durable_data`

이 구분으로 file `fsync`와 directory `fsync`의 차이를 확인합니다.

## 안전한 file 교체

설정 파일 전체를 교체할 때 흔히 다음 순서를 사용합니다.

```text
1. 같은 filesystem에 임시 file 생성
2. 새 내용 전체 write
3. 임시 file fsync
4. 목적 path로 atomic rename
5. parent directory fsync
```

rename의 atomicity는 실행 중 관찰자가 old 또는 new name 중 하나를 보게 한다는 뜻일 수 있습니다. crash 뒤 new name이 반드시 남는 durability와는 다릅니다.

다음 항목도 확인해야 합니다.

- 임시 file과 목적 file이 같은 filesystem에 있습니까?
- permission과 ownership을 언제 설정합니까?
- old metadata를 유지해야 합니까?
- directory fsync를 지원합니까?
- write, close와 fsync 오류를 확인합니까?

## write ordering과 crash window

application에서 여러 write가 끝난 순서와 storage에 남는 순서는 다를 수 있습니다. filesystem은 다음 방법을 조합합니다.

- write barrier와 flush
- ordered writeback
- journal
- copy-on-write tree
- log-structured update
- checksum과 generation

중요한 질문은 어떤 순서로 durable해야 내부 상태가 모순되지 않는가입니다.

예를 들어 새 block을 file에 연결했는데 free-space metadata가 아직 그 block을 free라고 기록하면 crash 뒤 double allocation이 생길 수 있습니다. 반대 순서는 block leak을 만들 수 있습니다. recovery가 무엇을 고칠 수 있는지까지 정해야 합니다.

## journal

단순한 write-ahead journal은 다음 순서를 가질 수 있습니다.

```text
BEGIN tx
OPERATION 또는 UPDATE record
COMMIT tx
journal flush
home location 반영
checkpoint 또는 log 공간 회수
```

crash 뒤에는 commit record가 durable한 transaction만 replay합니다. commit되지 않은 operation은 적용하지 않습니다.

`kernel-model`의 journal은 다음을 검사합니다.

```text
BEGIN 없는 operation을 허용하지 않습니다.
BEGIN 없는 COMMIT을 허용하지 않습니다.
COMMIT 뒤 같은 transaction에 operation을 추가하지 않습니다.
이미 적용한 transaction을 다시 replay하지 않습니다.
```

### redo와 undo

- redo logging은 새 값을 기록하고 committed transaction을 다시 적용합니다.
- undo logging은 이전 값을 기록하고 commit되지 않은 변경을 되돌립니다.

redo operation은 여러 번 실행해도 같은 결과가 되거나 transaction id로 중복 실행을 막아야 합니다. undo는 data가 log보다 먼저 durable해질 수 있는지 등 write ordering을 정해야 합니다.

### physical과 logical record

- physical record는 block 또는 byte 변경을 기록합니다.
- logical record는 “directory entry 추가” 같은 operation을 기록합니다.

logical operation은 replay 시 현재 상태를 확인해야 합니다. 예를 들어 이미 새 이름이 있거나 old 이름이 사라졌다면 단순히 같은 rename을 반복할 수 없습니다.

## filesystem journal과 application transaction

filesystem journal은 filesystem 내부 metadata와 data 배치를 보호합니다. 다음 application 규칙까지 자동으로 보장하지는 않습니다.

```text
두 file이 같은 version이어야 합니다.
configuration과 secret이 함께 바뀌어야 합니다.
database row와 filesystem object가 한 transaction이어야 합니다.
여러 service가 같은 release manifest를 사용해야 합니다.
```

application은 자체 transaction, version 또는 recovery procedure를 마련해야 합니다.

## memory-mapped file

mapped write는 page cache를 dirty하게 만들 수 있습니다.

```text
mapped write
→ process와 다른 mapping에서 새 값 관찰 가능
→ dirty page
→ writeback 전 crash
→ storage에는 이전 값
```

mapping을 해제하는 것, writeback을 요청하는 것과 directory metadata를 durable하게 만드는 것은 서로 다른 동작입니다.

## short write와 delayed error

storage 부족, quota 또는 device error로 write가 일부만 성공할 수 있습니다. buffered write는 처음에는 성공하고 나중의 `fsync`, `close` 또는 background writeback에서 오류가 드러날 수도 있습니다.

확인할 항목은 다음과 같습니다.

```text
실제로 쓴 byte 수
남은 data의 재시도 위치
file offset 변화
부분 data가 유효한지
fsync와 close의 반환값
재시도 시 중복 side effect 여부
```

## 연결 실습

```sh
cd exercises/kernel-model
python3 -m unittest tests.test_models.StorageTests -v
python3 kernel-model.py filesystem examples/filesystem-crash.json
```

scenario는 file과 directory를 durable하게 만든 뒤 새 값을 cache에만 쓰고 crash를 발생시킵니다. 복구 결과는 마지막으로 durable했던 값을 사용합니다.

invalid snapshot 테스트는 directory가 가리키는 inode 수와 저장된 link count가 다른 상태, BEGIN 없이 COMMIT한 journal을 거부합니다.

## 완료 기준

- path, directory entry, inode와 data를 구분할 수 있습니다.
- page cache에 보이는 값과 storage에 남은 값을 구분할 수 있습니다.
- file `fsync`와 directory `fsync`가 필요한 이유를 설명할 수 있습니다.
- atomic rename과 crash durability가 같은 보장이 아님을 설명할 수 있습니다.
- committed transaction만 replay하고 중복 적용을 막는 방법을 설명할 수 있습니다.

## 잘못된 이해

- `write`가 성공하면 data와 이름이 모두 media에 남았다고 생각합니다.
- rename이 atomic이면 directory fsync가 필요 없다고 단정합니다.
- journaling이 application의 여러 file transaction까지 보장한다고 생각합니다.
- buffered write의 오류는 항상 최초 `write`에서만 나타난다고 생각합니다.

## 자기 설명

- file data를 fsync했는데도 새 이름이 crash 뒤 사라질 수 있는 이유는 무엇입니까?
- committed journal record만 replay해야 하는 이유는 무엇입니까?
- logical operation을 재실행할 때 현재 상태를 확인해야 하는 이유는 무엇입니까?
