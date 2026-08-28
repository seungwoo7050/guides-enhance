from __future__ import annotations

import copy
import struct
import unittest

from mini_storage import (
    PAGE_HEADER,
    PAGE_SLOT,
    BufferPool,
    DiskManager,
    DuplicateKeyError,
    LogManager,
    LogRecord,
    MiniStorageEngine,
    OrderedLeafIndex,
    PageFull,
    SlottedPage,
    WALViolation,
)


# [Implementation 11] 저장 엔진의 구성 요소를 함께 검증합니다.
# page layout, buffer 교체, WAL 순서, index RID, checkpoint, 반복 recovery를 한 테스트 묶음에서 확인합니다.
class MiniStorageEngineTests(unittest.TestCase):
    def test_insert_get_range_and_duplicate_contract(self) -> None:
        engine = MiniStorageEngine(DiskManager(160), buffer_capacity=2)
        for key in (30, 10, 20, 40):
            engine.insert(key, f"value-{key}".encode())
        self.assertEqual(engine.get(20), b"value-20")
        self.assertEqual(engine.range(15, 35), [(20, b"value-20"), (30, b"value-30")])
        with self.assertRaises(DuplicateKeyError):
            engine.insert(20, b"duplicate")

    def test_grows_to_multiple_pages(self) -> None:
        disk = DiskManager(128)
        engine = MiniStorageEngine(disk, buffer_capacity=1)
        for key in range(12):
            engine.insert(key, b"x" * 20)
        engine.checkpoint()
        self.assertGreater(len(disk.page_ids), 1)
        self.assertEqual(engine.get(11), b"x" * 20)

    def test_buffer_pool_enforces_wal_before_data(self) -> None:
        disk = DiskManager(128)
        page_id = disk.allocate()
        log = LogManager()
        pool = BufferPool(disk, log, capacity=1)
        lsn = log.insert(1, page_id, 7, b"seven")
        page = pool.fetch(page_id)
        page.insert(7, b"seven")
        page.page_lsn = lsn
        pool.unpin(page_id, dirty=True)
        with self.assertRaises(WALViolation):
            pool.flush(page_id)
        log.flush(lsn)
        pool.flush(page_id)

    def test_recovers_committed_log_without_data_page_flush(self) -> None:
        disk = DiskManager(160)
        engine = MiniStorageEngine(disk)
        engine.insert(1, b"durable-log")
        recovered = MiniStorageEngine.recover(disk, engine.log.durable_records())
        self.assertEqual(recovered.get(1), b"durable-log")

    def test_ignores_uncommitted_insert(self) -> None:
        disk = DiskManager(160)
        page_id = disk.allocate()
        log = LogManager()
        lsn = log.insert(99, page_id, 9, b"not-committed")
        log.flush(lsn)
        recovered = MiniStorageEngine.recover(disk, log.durable_records())
        with self.assertRaises(KeyError):
            recovered.get(9)

    def test_removes_uncommitted_insert_that_reached_disk(self) -> None:
        disk = DiskManager(160)
        engine = MiniStorageEngine(disk)
        engine.insert(1, b"committed")
        engine.checkpoint()

        page_id = disk.page_ids[0]
        txid = engine._next_txid
        lsn = engine.log.insert(txid, page_id, 2, b"uncommitted-on-disk")
        engine.log.flush(lsn)
        page = engine.buffer.fetch(page_id)
        page.insert(2, b"uncommitted-on-disk")
        page.page_lsn = lsn
        engine.buffer.unpin(page_id, dirty=True)
        engine.buffer.flush(page_id)

        recovered = MiniStorageEngine.recover(disk, engine.log.durable_records())
        self.assertEqual(recovered.get(1), b"committed")
        with self.assertRaises(KeyError):
            recovered.get(2)

    def test_recovery_is_idempotent(self) -> None:
        disk = DiskManager(160)
        engine = MiniStorageEngine(disk)
        engine.insert(1, b"one")
        durable = engine.log.durable_records()
        first = MiniStorageEngine.recover(disk, durable)
        snapshot = copy.deepcopy(disk.pages)
        second = MiniStorageEngine.recover(disk, durable)
        self.assertEqual(disk.pages, snapshot)
        self.assertEqual(first.get(1), second.get(1))

    def test_recovery_advances_transaction_id_past_durable_history(self) -> None:
        disk = DiskManager(160)
        original = MiniStorageEngine(disk)
        original.insert(1, b"committed")
        recovered = MiniStorageEngine.recover(disk, original.log.durable_records())

        next_txid = recovered._next_txid
        durable_max = max(record.txid for record in recovered.log.durable_records())
        self.assertEqual(next_txid, durable_max + 1)

        page_id = disk.allocate()
        lsn = recovered.log.insert(next_txid, page_id, 2, b"uncommitted-after-recovery")
        recovered.log.flush(lsn)
        restarted = MiniStorageEngine.recover(disk, recovered.log.durable_records())
        self.assertEqual(restarted.get(1), b"committed")
        with self.assertRaises(KeyError):
            restarted.get(2)

    def test_insert_validation_does_not_append_wal(self) -> None:
        engine = MiniStorageEngine(DiskManager(128))
        before_records = list(engine.log.records)
        before_pages = list(engine.disk.page_ids)
        for key, value in ((True, b"bad"), (1, b""), (2**63, b"bad")):
            with self.subTest(key=key, value=value), self.assertRaises((TypeError, ValueError)):
                engine.insert(key, value)  # type: ignore[arg-type]
        with self.assertRaises(PageFull):
            engine.insert(1, b"x" * 200)
        self.assertEqual(engine.log.records, before_records)
        self.assertEqual(engine.disk.page_ids, before_pages)

    def test_page_decoder_rejects_truncation_and_slot_overlap(self) -> None:
        page = SlottedPage(0, 160)
        first = page.insert(1, b"first")
        second = page.insert(2, b"second")
        raw = page.serialize()
        with self.assertRaises(ValueError):
            SlottedPage.from_bytes(0, raw[: PAGE_HEADER.size - 1])

        corrupted = bytearray(raw)
        first_offset, first_length = PAGE_SLOT.unpack_from(
            corrupted, PAGE_HEADER.size + first * PAGE_SLOT.size
        )
        PAGE_SLOT.pack_into(
            corrupted,
            PAGE_HEADER.size + second * PAGE_SLOT.size,
            first_offset,
            first_length,
        )
        with self.assertRaises(ValueError):
            SlottedPage.from_bytes(0, bytes(corrupted))

    def test_ordered_leaf_index_validates_global_order(self) -> None:
        index = OrderedLeafIndex(leaf_capacity=2)
        for key in (4, 1, 3, 2):
            index.insert(key, (0, key))
        index.validate()
        self.assertEqual([key for key, _ in index.range(1, 4)], [1, 2, 3, 4])
        index.leaves[1][0] = index.leaves[0][-1]
        with self.assertRaises(AssertionError):
            index.validate()

    def test_recovery_rejects_invalid_transaction_lifecycle(self) -> None:
        disk = DiskManager(128)
        records = [LogRecord(1, 1, "COMMIT")]
        with self.assertRaises(ValueError):
            MiniStorageEngine.recover(disk, records)


if __name__ == "__main__":
    unittest.main()
