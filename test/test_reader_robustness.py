import shutil

import pytest

from cyber_record.cyber.proto import record_pb2
from cyber_record.record import Record


ASSET_RECORD = "test/assets/example.record.00000"


def _read_header(path):
    header = record_pb2.Header()
    with open(path, "rb") as f:
        section = f.read(16)
        size = int.from_bytes(section[8:16], byteorder="little")
        header.ParseFromString(f.read(size))
    return header


def _corrupt_index_type(path):
    header = _read_header(path)
    with open(path, "r+b") as f:
        f.seek(header.index_position)
        f.write((0).to_bytes(8, byteorder="little"))


def _truncate_from_index(path):
    header = _read_header(path)
    with open(path, "r+b") as f:
        f.truncate(header.index_position)


def _count_messages(path, **kwargs):
    with Record(path, **kwargs) as record:
        return sum(1 for _ in record.read_messages_section_scan())


def test_section_scan_parity_with_index_mode():
    with Record(ASSET_RECORD) as record:
        normal = sum(
            1
            for _ in record.read_messages(
                topics="/apollo/canbus/chassis",
                start_time=1627031535164278940,
                end_time=1627031535215164773,
            )
        )
        scan = sum(
            1
            for _ in record.read_messages_section_scan(
                topics="/apollo/canbus/chassis",
                start_time=1627031535164278940,
                end_time=1627031535215164773,
            )
        )
    assert normal == scan == 6


def test_allow_unindexed_reads_corrupted_index(tmp_path):
    broken = tmp_path / "broken_index.record"
    shutil.copyfile(ASSET_RECORD, broken)
    _corrupt_index_type(str(broken))

    with pytest.raises(Exception):
        Record(str(broken))

    assert _count_messages(str(broken), allow_unindexed=True) == 34


def test_allow_unindexed_reads_truncated_index(tmp_path):
    broken = tmp_path / "truncated_index.record"
    shutil.copyfile(ASSET_RECORD, broken)
    _truncate_from_index(str(broken))

    with pytest.raises(Exception):
        Record(str(broken))

    assert _count_messages(str(broken), allow_unindexed=True) == 34
