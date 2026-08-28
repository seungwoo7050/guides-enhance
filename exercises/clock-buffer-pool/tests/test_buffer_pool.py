from __future__ import annotations

import unittest

from buffer_pool import BufferPool, BufferPoolFull, DiskManager


# [Implementation 7] buffer pool의 상태 전이를 검증합니다.
# cache hit, pinned frame 제외, second chance, dirty write, 실패 시 기존 mapping 보존을 확인합니다.
class BufferPoolTests(unittest.TestCase):
    def test_cache_hit_avoids_second_disk_read(self) -> None:
        disk = DiskManager(16)
        page = disk.allocate(b"alpha")
        pool = BufferPool(disk, 2)
        first = pool.fetch(page)
        pool.unpin(page)
        second = pool.fetch(page)
        self.assertIs(first, second)
        self.assertEqual(disk.read_count, 1)

    def test_dirty_eviction_writes_before_reuse(self) -> None:
        disk = DiskManager(16)
        first = disk.allocate(b"first")
        second = disk.allocate(b"second")
        pool = BufferPool(disk, 1)
        data = pool.fetch(first)
        data[:7] = b"changed"
        pool.unpin(first, dirty=True)
        pool.fetch(second)
        self.assertEqual(disk.pages[first][:7], b"changed")
        self.assertEqual(disk.write_count, 1)
        self.assertNotIn(first, pool.page_table)
        self.assertIn(second, pool.page_table)

    def test_pinned_page_is_not_evicted(self) -> None:
        disk = DiskManager(8)
        first = disk.allocate(b"one")
        second = disk.allocate(b"two")
        pool = BufferPool(disk, 1)
        pool.fetch(first)
        with self.assertRaises(BufferPoolFull):
            pool.fetch(second)
        self.assertIn(first, pool.page_table)
        self.assertNotIn(second, pool.page_table)

    def test_second_chance_skips_referenced_frame(self) -> None:
        disk = DiskManager(8)
        first = disk.allocate(b"one")
        second = disk.allocate(b"two")
        third = disk.allocate(b"three")
        pool = BufferPool(disk, 2)
        pool.fetch(first)
        pool.unpin(first)
        pool.fetch(second)
        pool.unpin(second)

        first_index = pool.page_table[first]
        second_index = pool.page_table[second]
        pool.frames[first_index].referenced = False
        pool.frames[second_index].referenced = True
        pool.hand = second_index
        pool.fetch(third)

        self.assertNotIn(first, pool.page_table)
        self.assertIn(second, pool.page_table)
        self.assertIn(third, pool.page_table)

    def test_dirty_flag_survives_multiple_pins(self) -> None:
        disk = DiskManager(8)
        page = disk.allocate(b"old")
        pool = BufferPool(disk, 1)
        data = pool.fetch(page)
        pool.fetch(page)
        data[:3] = b"new"
        pool.unpin(page, dirty=True)
        pool.unpin(page)
        pool.flush(page)
        self.assertEqual(disk.pages[page][:3], b"new")
        self.assertEqual(disk.write_count, 1)

    def test_rejects_double_unpin(self) -> None:
        disk = DiskManager(8)
        page = disk.allocate()
        pool = BufferPool(disk, 1)
        pool.fetch(page)
        pool.unpin(page)
        with self.assertRaises(RuntimeError):
            pool.unpin(page)

    def test_unknown_fetch_does_not_evict_resident_page(self) -> None:
        disk = DiskManager(8)
        page = disk.allocate(b"stable")
        pool = BufferPool(disk, 1)
        data = pool.fetch(page)
        pool.unpin(page)
        snapshot = bytes(data)
        reads = disk.read_count
        writes = disk.write_count

        with self.assertRaises(KeyError):
            pool.fetch(999)

        self.assertIn(page, pool.page_table)
        self.assertEqual(bytes(pool.fetch(page)), snapshot)
        self.assertEqual(disk.read_count, reads)
        self.assertEqual(disk.write_count, writes)


if __name__ == "__main__":
    unittest.main()
