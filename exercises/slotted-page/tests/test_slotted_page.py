from __future__ import annotations
import unittest
from slotted_page import PageFullError, SlottedPage

class SlottedPageTests(unittest.TestCase):

    def test_insert_read_delete_and_slot_reuse(self) -> None:
        page = SlottedPage(128)
        first = page.insert(b'first')
        second = page.insert(b'second-record')
        self.assertEqual(page.read(first), b'first')
        page.delete(first)
        with self.assertRaises(KeyError):
            page.read(first)
        reused = page.insert(b'replacement')
        self.assertEqual(reused, first)
        self.assertEqual(page.read(second), b'second-record')

    def test_compaction_and_expanding_update_keep_rids_stable(self) -> None:
        page = SlottedPage(160)
        first = page.insert(b'a' * 10)
        removed = page.insert(b'b' * 20)
        last = page.insert(b'c' * 10)
        page.delete(removed)
        page.update(first, b'a' * 30)
        page.compact()
        self.assertEqual(page.read(first), b'a' * 30)
        self.assertEqual(page.read(last), b'c' * 10)
        with self.assertRaises(KeyError):
            page.read(removed)

    def test_failed_update_is_atomic(self) -> None:
        page = SlottedPage(96)
        target = page.insert(b'stable')
        page.insert(b'x' * 40)
        snapshot = (bytes(page._data), [(slot.offset, slot.length, slot.alive) for slot in page._slots], page._free_end)
        with self.assertRaises(PageFullError):
            page.update(target, b'y' * 70)
        self.assertEqual((bytes(page._data), [(slot.offset, slot.length, slot.alive) for slot in page._slots], page._free_end), snapshot)
        self.assertEqual(page.read(target), b'stable')

    def test_failed_insert_is_atomic_even_when_fragmented(self) -> None:
        page = SlottedPage(96)
        first = page.insert(b'a' * 20)
        second = page.insert(b'b' * 20)
        page.delete(first)
        snapshot = (bytes(page._data), [(slot.offset, slot.length, slot.alive) for slot in page._slots], page._free_end)
        with self.assertRaises(PageFullError):
            page.insert(b'c' * 70)
        self.assertEqual((bytes(page._data), [(slot.offset, slot.length, slot.alive) for slot in page._slots], page._free_end), snapshot)
        self.assertEqual(page.read(second), b'b' * 20)

    def test_rejects_invalid_identifiers_and_empty_records(self) -> None:
        page = SlottedPage()
        slot = page.insert(b'record')
        for invalid in (-1, True, 99):
            with self.subTest(invalid=invalid), self.assertRaises(KeyError):
                page.read(invalid)
        self.assertEqual(page.read(slot), b'record')
        with self.assertRaises(ValueError):
            page.insert(b'')
if __name__ == '__main__':
    unittest.main()
