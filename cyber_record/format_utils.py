#!/usr/bin/env python

"""Format detection helpers."""

MCAP_MAGIC = bytes((137, 77, 67, 65, 80, 48, 13, 10))


def detect_file_format(path):
    """Detect storage format by magic bytes."""
    with open(path, "rb") as f:
        magic = f.read(8)
    if magic == MCAP_MAGIC:
        return "mcap"
    return "record"
