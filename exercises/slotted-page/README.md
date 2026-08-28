# Slotted Page

가변 길이 `bytes` record를 하나의 고정 크기 page에 저장하는 Python 구현입니다. 외부에서 사용하는 record identifier는 byte offset이 아니라 `slot_id`입니다. Compaction이나 크기가 커지는 update로 record 위치가 바뀌어도 기존 `(page_id, slot_id)` 형태의 참조를 유지할 수 있습니다.

## 주요 기능

- 가변 길이 record의 insert, read, update, delete
- 삭제한 tombstone slot 재사용
- live record만 다시 배치하는 compaction
- 공간 부족 시 기존 page를 보존하는 insert와 update
- 고정 크기 binary page 직렬화와 역직렬화
- 잘못된 header, slot 상태, record 범위와 겹치는 slot 거부

## 구성

`SlottedPage`가 page bytes, slot directory와 남은 공간을 관리합니다. `Slot`에는 현재 record의 offset, length와 사용 여부를 저장합니다. 삭제할 때 slot 항목을 제거하지 않으므로 뒤의 slot 번호가 바뀌지 않습니다.

## 설치와 사용

Python 3.11 이상이 필요합니다.

```bash
python3 -m pip install -e .
```

```python
from slotted_page import SlottedPage

page = SlottedPage(256)
record_id = page.insert(b"payload")
page.update(record_id, b"larger-payload")

raw = page.serialize()
restored = SlottedPage.from_bytes(raw)
assert restored.read(record_id) == b"larger-payload"
```

## 테스트

```bash
make test
```

테스트는 slot_id 유지, compaction, tombstone 재사용, 실패 시 page 보존, 직렬화 왕복과 손상된 page 거부를 확인합니다.

## 설계에서 확인할 점

- Byte offset을 외부 RID로 사용하지 않습니다. Compaction이 record bytes를 옮겨도 slot 항목의 offset만 바꾸면 외부 참조는 유지됩니다.
- Insert와 크기가 커지는 update는 전체 수용 가능성을 먼저 계산합니다. 절대 들어갈 수 없는 요청은 compaction도 하지 않으므로 직렬화 결과가 실패 전과 같습니다.
- `from_bytes()`는 slot directory, tombstone 표현, live record 범위와 slot 겹침을 모두 검사한 뒤 객체를 반환합니다.

## Implementation Order

| 순서 | 구현 내용 | 주요 위치 |
| ---: | --- | --- |
| 1 | page header와 slot의 binary format | `src/slotted_page.py` · `HEADER`, `SLOT` |
| 2 | page bytes와 slot 상태 관리 | `src/slotted_page.py` · `Slot`, `SlottedPage` |
| 3 | 변경 전 payload와 slot 검증 | `src/slotted_page.py` · `_validate_payload`, `_slot` |
| 4 | 실패 시 page를 보존하는 insert와 slot 재사용 | `src/slotted_page.py` · `insert` |
| 5 | slot_id를 보존하는 record 변경 | `src/slotted_page.py` · `read`, `delete`, `update`, `compact` |
| 6 | page 직렬화 | `src/slotted_page.py` · `serialize` |
| 7 | 외부 page bytes 검증 | `src/slotted_page.py` · `from_bytes` |
| 8 | slotted page 불변식 검증 | `tests/test_slotted_page.py` · `SlottedPageTests` |

## 범위와 제한

이 구현은 메모리 안의 page 한 개와 RID 유지에 집중합니다. Page checksum, 동시 접근 제어, disk file allocation과 WAL 연동은 포함하지 않습니다.
