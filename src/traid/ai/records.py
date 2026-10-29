"""Local, immutable C14 analysis records (F7).

Root: caller-supplied, no default, outside the repository, under the C06 rules (exists, absolute, fully
resolved, no symlink in the path), owned by the current user and not group/other writable. It is
opened once without following symlinks and every later operation goes through that directory handle,
so swapping the path after the check has no effect.

Publication: canonical JSON <= 512 KiB (once dropping the raw response if needed) -> credential scan ->
``.stage-<run_id>-<hex>`` created exclusively, mode 0600, flushed -> ``os.link`` to the final name
(which fails if the name exists) -> directory flush -> stage removed.

* COMMITTED: stage flushed, link succeeded, directory flushed.
* FAILED_NOT_PUBLISHED: nothing was published (stage failure, scan hit, oversize) or the name already
  existed (``EEXIST``; that file is never touched).
* UNCONFIRMED: any other link error, or the directory flush failed after the link. A final-named file
  may exist; C14 never removes or rewrites it. Failure never means "no file exists".

There is no listing, index, update or deletion; the only read-back is ``load_record(path)``.
"""
from __future__ import annotations

from dataclasses import dataclass
import errno
import json
import os
from pathlib import Path
import re
import secrets
import stat

from traid.ai.models import AIAnalysisRecord, BoundedRaw

REPO_ROOT = Path(__file__).resolve().parents[3]
MAX_RECORD_BYTES = 512 * 1024
FINAL_NAME = re.compile(r"^\d{8}T\d{12}Z-[0-9a-f]{32}\.json$")
CREDENTIALS = re.compile(r"(AKIA|ASIA)[0-9A-Z]{16}|aws_secret_access_key|aws_session_token", re.IGNORECASE)


class OsOps:
    """The filesystem calls used for publication; replaceable in tests to inject failures."""
    def open(self, path, flags, mode=0o777, *, dir_fd=None):
        return os.open(path, flags, mode, dir_fd=dir_fd)

    def fstat(self, fd):
        return os.fstat(fd)

    def write(self, fd, data: bytes) -> int:
        return os.write(fd, data)

    def fsync(self, fd) -> None:
        os.fsync(fd)

    def close(self, fd) -> None:
        os.close(fd)

    def link(self, src, dst, *, dir_fd) -> None:
        os.link(src, dst, src_dir_fd=dir_fd, dst_dir_fd=dir_fd, follow_symlinks=False)

    def unlink(self, path, *, dir_fd) -> None:
        os.unlink(path, dir_fd=dir_fd)


@dataclass(frozen=True)
class PublishOutcome:
    kind: str           # COMMITTED, FAILED_NOT_PUBLISHED or UNCONFIRMED
    path: str | None    # set whenever a final-named file may exist
    reason: str


class RecordStoreError(ValueError):
    pass


def check_root(root: Path) -> Path:
    root = Path(root)
    if not root.is_absolute():
        raise RecordStoreError("record root must be absolute")
    if not root.is_dir():
        raise RecordStoreError("record root must already exist")
    if root.resolve() != root or root == REPO_ROOT or REPO_ROOT in root.parents:
        raise RecordStoreError("record root must be an ordinary directory outside Git")
    if any(p.is_symlink() for p in (root, *root.parents)):
        raise RecordStoreError("record root may not traverse a symlink")
    return root


def _owner_only(st) -> bool:
    return stat.S_ISDIR(st.st_mode) and st.st_uid == os.getuid() and st.st_mode & 0o022 == 0


def serialize(record: AIAnalysisRecord) -> bytes:
    return json.dumps(record.model_dump(mode="json"), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode()


class RecordStore:
    def __init__(self, root, ops: OsOps | None = None) -> None:
        self.root = Path(root)
        self.ops = ops or OsOps()

    def path_for(self, file_name: str) -> str:
        return str(self.root / file_name)

    def publish(self, record: AIAnalysisRecord, file_name: str) -> PublishOutcome:
        if not FINAL_NAME.match(file_name):
            return PublishOutcome("FAILED_NOT_PUBLISHED", None, "INVALID_FILE_NAME")
        data = serialize(record)
        if len(data) > MAX_RECORD_BYTES and record.raw_response is not None:
            raw = record.raw_response
            record = record.model_copy(update={"raw_response": BoundedRaw(
                content=None, sha256=raw.sha256, size_bytes=raw.size_bytes, truncated=False,
                omitted_reason="RECORD_LIMIT")})
            data = serialize(AIAnalysisRecord.model_validate(record.model_dump()))
        if len(data) > MAX_RECORD_BYTES:
            return PublishOutcome("FAILED_NOT_PUBLISHED", None, "RECORD_LIMIT")
        if CREDENTIALS.search(data.decode("ascii")):
            return PublishOutcome("FAILED_NOT_PUBLISHED", None, "CREDENTIAL_PATTERN")
        ops = self.ops
        try:
            root = check_root(self.root)
            dfd = ops.open(str(root), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except (OSError, RecordStoreError):
            return PublishOutcome("FAILED_NOT_PUBLISHED", None, "ROOT_REJECTED")
        final = self.path_for(file_name)
        try:
            if not _owner_only(ops.fstat(dfd)):
                return PublishOutcome("FAILED_NOT_PUBLISHED", None, "ROOT_PERMISSIONS")
            stage = f".stage-{record.run_id}-{secrets.token_hex(8)}"
            try:
                fd = ops.open(stage, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dfd)
            except OSError:
                return PublishOutcome("FAILED_NOT_PUBLISHED", None, "STAGE_CREATE_FAILED")
            try:
                view = memoryview(data)
                while view:
                    view = view[ops.write(fd, view):]
                ops.fsync(fd)
            except OSError:
                self._discard(stage, dfd, fd)
                return PublishOutcome("FAILED_NOT_PUBLISHED", None, "STAGE_WRITE_FAILED")
            try:
                ops.close(fd)
            except OSError:
                self._discard(stage, dfd, None)
                return PublishOutcome("FAILED_NOT_PUBLISHED", None, "STAGE_WRITE_FAILED")
            try:
                ops.link(stage, file_name, dir_fd=dfd)
            except OSError as e:
                if e.errno == errno.EEXIST:
                    self._discard(stage, dfd, None)
                    return PublishOutcome("FAILED_NOT_PUBLISHED", None, "NAME_EXISTS")
                return PublishOutcome("UNCONFIRMED", final, "LINK_FAILED")
            try:
                ops.fsync(dfd)
            except OSError:
                return PublishOutcome("UNCONFIRMED", final, "DIRECTORY_FLUSH_FAILED")
            try:
                ops.unlink(stage, dir_fd=dfd)
            except OSError:
                pass        # a leftover stage file is non-final and never read as a record
            return PublishOutcome("COMMITTED", final, "")
        finally:
            try:
                ops.close(dfd)
            except OSError:
                pass

    def _discard(self, stage: str, dfd, fd) -> None:
        for step in ((lambda: self.ops.close(fd)) if fd is not None else None,
                     lambda: self.ops.unlink(stage, dir_fd=dfd)):
            if step is None:
                continue
            try:
                step()
            except OSError:
                pass


def load_record(path) -> AIAnalysisRecord:
    """Bounded, schema-checked read-back of one record file."""
    flags = os.O_RDONLY | os.O_NOFOLLOW
    fd = os.open(str(path), flags)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_RECORD_BYTES:
            raise RecordStoreError("not a bounded record file")
        chunks, total = [], 0
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_RECORD_BYTES:
                raise RecordStoreError("record exceeds the size limit")
            chunks.append(chunk)
    finally:
        os.close(fd)
    return AIAnalysisRecord.model_validate_json(b"".join(chunks), strict=True)
