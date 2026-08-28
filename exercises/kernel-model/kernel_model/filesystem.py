"""현재 보이는 값과 crash 뒤 남는 값을 분리한 단일 directory 모델입니다."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


class FileSystemError(ValueError):
    """filesystem operation 또는 namespace 상태가 유효하지 않을 때 발생합니다."""


# [Implementation 6] 현재값과 durable filesystem 상태 분리
@dataclass
class Inode:
    inode_id: int
    cached_data: str
    durable_data: str = ""
    dirty: bool = True
    links: int = 0


@dataclass
class FileSystemModel:
    """현재 보이는 상태와 crash 뒤 복구할 상태를 따로 관리합니다."""

    directory: dict[str, int] = field(default_factory=dict)
    durable_directory: dict[str, int] = field(default_factory=dict)
    inodes: dict[int, Inode] = field(default_factory=dict)
    directory_dirty: bool = False
    _next_inode: int = 1

    # [Implementation 6-1] namespace와 link count 변경
    def create(self, name: str, data: str = "") -> int:
        self._validate_name(name)
        if name in self.directory:
            raise FileSystemError(f"Name already exists: {name}")
        inode_id = self._next_inode
        self._next_inode += 1
        inode = Inode(
            inode_id=inode_id,
            cached_data=data,
            dirty=True,
            links=1,
        )
        self.inodes[inode_id] = inode
        self.directory[name] = inode_id
        self.directory_dirty = True
        self.assert_invariants()
        return inode_id

    def write(self, name: str, data: str) -> None:
        inode = self._inode_for_name(name)
        inode.cached_data = data
        inode.dirty = inode.cached_data != inode.durable_data
        self.assert_invariants()

    def read(self, name: str) -> str:
        return self._inode_for_name(name).cached_data

    def rename(self, old: str, new: str) -> None:
        self._validate_name(new)
        if old not in self.directory:
            raise FileSystemError(f"Name not found: {old}")
        if new in self.directory:
            raise FileSystemError(f"Target name already exists: {new}")
        inode_id = self.directory.pop(old)
        self.directory[new] = inode_id
        self.directory_dirty = True
        self.assert_invariants()

    def link(self, existing: str, new: str) -> None:
        self._validate_name(new)
        if new in self.directory:
            raise FileSystemError(f"Target name already exists: {new}")
        inode = self._inode_for_name(existing)
        self.directory[new] = inode.inode_id
        inode.links += 1
        self.directory_dirty = True
        self.assert_invariants()

    def unlink(self, name: str) -> None:
        if name not in self.directory:
            raise FileSystemError(f"Name not found: {name}")
        inode_id = self.directory.pop(name)
        inode = self.inodes[inode_id]
        inode.links -= 1
        self.directory_dirty = True
        if inode.links == 0 and inode_id not in self.durable_directory.values():
            self.inodes.pop(inode_id)
        self.assert_invariants()

    # [Implementation 6-2] fsync와 crash recovery
    # file data를 flush해도 새 이름이 directory에 durable해지는 것은 아닙니다.
    def fsync_file(self, name: str) -> None:
        inode = self._inode_for_name(name)
        inode.durable_data = inode.cached_data
        inode.dirty = False
        self.assert_invariants()

    def fsync_directory(self) -> None:
        self.durable_directory = dict(self.directory)
        self.directory_dirty = False
        self._recompute_links()
        self._collect_unreferenced()
        self.assert_invariants()

    # 현재 cache와 namespace를 버리고 마지막으로 durable했던 값만 복원합니다.
    def crash_recover(self) -> None:
        """durable directory와 file data에 기록되지 않은 변경을 버립니다."""

        self.directory = dict(self.durable_directory)
        durable_ids = set(self.directory.values())
        for inode_id in list(self.inodes):
            if inode_id not in durable_ids:
                self.inodes.pop(inode_id)
                continue
            inode = self.inodes[inode_id]
            inode.cached_data = inode.durable_data
            inode.dirty = False
        self.directory_dirty = False
        self._recompute_links()
        self.assert_invariants()

    # [Implementation 6-3] journal replay용 filesystem operation
    def apply_operation(self, operation: Mapping[str, Any]) -> None:
        """journal recovery가 허용한 filesystem operation 하나를 적용합니다."""

        kind = operation.get("op")
        if kind == "create":
            name = str(operation["name"])
            if name not in self.directory:
                self.create(name, str(operation.get("data", "")))
        elif kind == "write":
            name = str(operation["name"])
            data = str(operation.get("data", ""))
            if name not in self.directory:
                raise FileSystemError(f"Write target does not exist: {name}")
            self.write(name, data)
        elif kind == "rename":
            old = str(operation["old"])
            new = str(operation["new"])
            if old in self.directory and new not in self.directory:
                self.rename(old, new)
            elif new not in self.directory:
                raise FileSystemError(f"Ambiguous rename recovery state: {old} -> {new}")
        elif kind == "unlink":
            name = str(operation["name"])
            if name in self.directory:
                self.unlink(name)
        elif kind == "fsync-file":
            self.fsync_file(str(operation["name"]))
        elif kind == "fsync-directory":
            self.fsync_directory()
        else:
            raise FileSystemError(f"Unsupported filesystem operation: {kind}")

    # [Implementation 6-4] 관찰 가능한 filesystem snapshot
    def snapshot(self) -> dict[str, Any]:
        return {
            "directory": dict(sorted(self.directory.items())),
            "durable_directory": dict(sorted(self.durable_directory.items())),
            "directory_dirty": self.directory_dirty,
            "inodes": {
                str(inode_id): {
                    "cached_data": inode.cached_data,
                    "durable_data": inode.durable_data,
                    "dirty": inode.dirty,
                    "links": inode.links,
                }
                for inode_id, inode in sorted(self.inodes.items())
            },
        }

    # [Implementation 6-5] namespace·inode 불변식 검사
    def assert_invariants(self) -> None:
        for name, inode_id in self.directory.items():
            self._validate_name(name)
            if inode_id not in self.inodes:
                raise FileSystemError(f"Directory references a missing inode: {name}")
        for name, inode_id in self.durable_directory.items():
            self._validate_name(name)
            if inode_id not in self.inodes:
                raise FileSystemError(
                    f"Durable directory references a missing inode: {name}"
                )

        live_counts: dict[int, int] = {
            inode_id: 0 for inode_id in self.inodes
        }
        for inode_id in self.directory.values():
            live_counts[inode_id] = live_counts.get(inode_id, 0) + 1

        for inode_id, inode in self.inodes.items():
            actual = live_counts.get(inode_id, 0)
            if inode.links != actual:
                raise FileSystemError(
                    "Inode link count disagrees with the live directory: "
                    f"inode={inode_id} stored={inode.links} actual={actual}"
                )
            if inode.links == 0 and inode_id not in self.durable_directory.values():
                raise FileSystemError(f"An unreferenced inode remains allocated: {inode_id}")
            if not inode.dirty and inode.cached_data != inode.durable_data:
                raise FileSystemError(
                    f"A clean inode has different cached and durable data: {inode_id}"
                )

    @classmethod
    def validate_snapshot(cls, snapshot: Mapping[str, Any]) -> None:
        raw_directory = snapshot.get("directory")
        raw_durable = snapshot.get("durable_directory")
        raw_inodes = snapshot.get("inodes")
        if (
            not isinstance(raw_directory, Mapping)
            or not isinstance(raw_durable, Mapping)
            or not isinstance(raw_inodes, Mapping)
        ):
            raise FileSystemError("Filesystem snapshot has an invalid shape")

        model = cls()
        model.directory = {
            str(name): int(inode_id)
            for name, inode_id in raw_directory.items()
        }
        model.durable_directory = {
            str(name): int(inode_id)
            for name, inode_id in raw_durable.items()
        }
        model.directory_dirty = bool(snapshot.get("directory_dirty", False))
        model.inodes = {}
        for raw_id, raw in raw_inodes.items():
            if not isinstance(raw, Mapping):
                raise FileSystemError("An inode entry has an invalid shape")
            inode_id = int(raw_id)
            model.inodes[inode_id] = Inode(
                inode_id=inode_id,
                cached_data=str(raw.get("cached_data", "")),
                durable_data=str(raw.get("durable_data", "")),
                dirty=bool(raw.get("dirty", False)),
                links=int(raw.get("links", 0)),
            )
        model._next_inode = max(model.inodes, default=0) + 1
        model.assert_invariants()

    def _inode_for_name(self, name: str) -> Inode:
        try:
            return self.inodes[self.directory[name]]
        except KeyError as exc:
            raise FileSystemError(f"Name not found: {name}") from exc

    def _recompute_links(self) -> None:
        for inode in self.inodes.values():
            inode.links = 0
        for inode_id in self.directory.values():
            self.inodes[inode_id].links += 1

    def _collect_unreferenced(self) -> None:
        protected = set(self.durable_directory.values())
        for inode_id in list(self.inodes):
            if self.inodes[inode_id].links == 0 and inode_id not in protected:
                self.inodes.pop(inode_id)

    @staticmethod
    def _validate_name(name: str) -> None:
        if not name or "/" in name or name in {".", ".."}:
            raise FileSystemError(f"Invalid single-directory name: {name!r}")
