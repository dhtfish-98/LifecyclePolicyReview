"""Read one explicit snapshot through held directories, never walk dependencies."""

import os
import stat

from .model import DEFAULT_LIMITS, InputIssue


def read_snapshot(path):
    if type(path) is not str:
        raise InputIssue("snapshot_path_invalid")
    try:
        encoded = path.encode("utf-8", "strict")
    except UnicodeError:
        raise InputIssue("snapshot_path_invalid") from None
    if not encoded or len(encoded) > 8192 or b"\0" in encoded:
        raise InputIssue("snapshot_path_invalid")
    if (
        not all(
            hasattr(os, name) for name in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK")
        )
        or os.open not in os.supports_dir_fd
    ):
        raise InputIssue("snapshot_reader_platform_open")
    components = path.split("/")
    anchor = "/" if path.startswith("/") else "."
    if anchor == "/":
        components = components[1:]
    if any(part in ("", ".", "..") for part in components):
        raise InputIssue("snapshot_path_components")
    descriptors = []
    try:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        descriptors.append(os.open(anchor, directory_flags))
        for component in components[:-1]:
            descriptors.append(
                os.open(component, directory_flags, dir_fd=descriptors[-1])
            )
        final = os.open(
            components[-1],
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=descriptors[-1],
        )
        descriptors.append(final)
        before = os.fstat(final)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_size > DEFAULT_LIMITS.file_bytes
        ):
            raise InputIssue("snapshot_regular_byte_profile")
        chunks, count = [], 0
        while count <= DEFAULT_LIMITS.file_bytes:
            block = os.read(final, min(65536, DEFAULT_LIMITS.file_bytes + 1 - count))
            if not block:
                break
            chunks.append(block)
            count += len(block)
        if count > DEFAULT_LIMITS.file_bytes:
            raise InputIssue("snapshot_byte_budget")
        after = os.fstat(final)
        attributes = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        if (
            not stat.S_ISREG(after.st_mode)
            or count != after.st_size
            or any(getattr(before, name) != getattr(after, name) for name in attributes)
        ):
            raise InputIssue("snapshot_changed_or_short")
        return b"".join(chunks)
    except (OSError, UnicodeError):
        raise InputIssue("snapshot_file_error") from None
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
