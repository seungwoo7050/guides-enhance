from __future__ import annotations

import unittest

from slotted_page import HEADER, SLOT, PageFullError, SlottedPage


# [Implementation 8] slotted page의 불변식을 검증합니다.
# slot_id 유지, 실패 시 page 보존, compaction, 손상된 직렬화 입력 거부를 확인합니다.
class SlottedPageTests(unittest.TestCase):
    def test_insert_read_delete_and_slot_reuse(self) -> None:
        page = SlottedPage(128)
        first = page.insert(b"first")
        second = page.insert(b"second-record")
        self.assertEqual(page.read(first), b"first")
        page.delete(first)
        with self.assertRaises(KeyError):
            page.read(first)
        reused = page.insert(b"replacement")
        self.assertEqual(reused, first)
        self.assertEqual(page.read(second), b"second-record")

    def test_compaction_and_expanding_update_keep_rids_stable(self) -> None:
        page = SlottedPage(160)
        first = page.insert(b"a" * 10)
        removed = page.insert(b"b" * 20)
        last = page.insert(b"c" * 10)
        page.delete(removed)
        page.update(first, b"a" * 30)
        page.compact()
        self.assertEqual(page.read(first), b"a" * 30)
        self.assertEqual(page.read(last), b"c" * 10)
        with self.assertRaises(KeyError):
            page.read(removed)

    def test_failed_update_is_atomic(self) -> None:
        page = SlottedPage(96)
        target = page.insert(b"stable")
        page.insert(b"x" * 40)
        snapshot = page.serialize()
        with self.assertRaises(PageFullError):
            page.update(target, b"y" * 70)
        self.assertEqual(page.serialize(), snapshot)
        self.assertEqual(page.read(target), b"stable")

    def test_failed_insert_is_atomic_even_when_fragmented(self) -> None:
        page = SlottedPage(96)
        first = page.insert(b"a" * 20)
        second = page.insert(b"b" * 20)
        page.delete(first)
        snapshot = page.serialize()
        with self.assertRaises(PageFullError):
            page.insert(b"c" * 70)
        self.assertEqual(page.serialize(), snapshot)
        self.assertEqual(page.read(second), b"b" * 20)

    def test_round_trip_preserves_live_and_dead_slots(self) -> None:
        page = SlottedPage(192)
        live = page.insert(b"persisted")
        dead = page.insert(b"deleted")
        page.delete(dead)
        restored = SlottedPage.from_bytes(page.serialize())
        self.assertEqual(restored.read(live), b"persisted")
        with self.assertRaises(KeyError):
            restored.read(dead)

    def test_rejects_invalid_identifiers_and_empty_records(self) -> None:
        page = SlottedPage()
        slot = page.insert(b"record")
        for invalid in (-1, True, 99):
            with self.subTest(invalid=invalid), self.assertRaises(KeyError):
                page.read(invalid)  # type: ignore[arg-type]
        self.assertEqual(page.read(slot), b"record")
        with self.assertRaises(ValueError):
            page.insert(b"")

    def test_rejects_invalid_slot_state_and_overlap(self) -> None:
        page = SlottedPage(128)
        first = page.insert(b"alpha")
        second = page.insert(b"beta")
        raw = bytearray(page.serialize())

        state_offset = HEADER.size + first * SLOT.size + 4
        raw[state_offset] = 2
        with self.assertRaises(ValueError):
            SlottedPage.from_bytes(bytes(raw))

        raw = bytearray(page.serialize())
        first_offset, first_length, _ = SLOT.unpack_from(raw, HEADER.size + first * SLOT.size)
        SLOT.pack_into(raw, HEADER.size + second * SLOT.size, first_offset, first_length, 1)
        with self.assertRaises(ValueError):
            SlottedPage.from_bytes(bytes(raw))


if __name__ == "__main__":
    unittest.main()
