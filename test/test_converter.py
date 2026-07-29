import pytest

from cyber_record.converter import convert_file, convert_record_to_record
from cyber_record.main import main as cli_main
from cyber_record.record import Record


ASSET_RECORD = "test/assets/example.record.00000"


def test_convert_record_to_record_full(tmp_path):
    output = tmp_path / "out.record"
    result = convert_record_to_record(ASSET_RECORD, str(output))
    assert result["converted"] == 34
    assert result["skipped"] == 0
    with Record(str(output)) as record:
        assert sum(1 for _ in record.read_messages()) == 34


def test_convert_record_to_record_filtered(tmp_path):
    output = tmp_path / "out_filtered.record"
    result = convert_record_to_record(
        ASSET_RECORD,
        str(output),
        topics="/apollo/canbus/chassis",
        start_time=1627031535164278940,
        end_time=1627031535215164773,
    )
    assert result["converted"] == 6
    with Record(str(output)) as record:
        assert sum(1 for _ in record.read_messages()) == 6


def test_convert_record_to_mcap(tmp_path):
    pytest.importorskip("mcap")
    output = tmp_path / "out.mcap"
    result = convert_file(
        input_file=ASSET_RECORD,
        output_file=str(output),
        from_format="record",
        to_format="mcap",
    )
    assert result["converted"] == 34
    assert result["output_channels"] == 8


def test_convert_mcap_to_record_round_trip(tmp_path):
    pytest.importorskip("mcap")
    mcap_output = tmp_path / "roundtrip.mcap"
    record_output = tmp_path / "roundtrip.record"

    to_mcap = convert_file(
        input_file=ASSET_RECORD,
        output_file=str(mcap_output),
        from_format="record",
        to_format="mcap",
    )
    assert to_mcap["converted"] == 34

    to_record = convert_file(
        input_file=str(mcap_output),
        output_file=str(record_output),
        from_format="mcap",
        to_format="record",
    )
    assert to_record["converted"] == 34
    with Record(str(record_output)) as record:
        assert sum(1 for _ in record.read_messages()) == 34


def test_convert_from_auto_detect(tmp_path):
    pytest.importorskip("mcap")
    mcap_output = tmp_path / "auto.mcap"
    result = convert_file(
        input_file=ASSET_RECORD,
        output_file=str(mcap_output),
        from_format="auto",
        to_format="mcap",
    )
    assert result["converted"] == 34


def test_convert_cli_exit_code_on_missing_args():
    with pytest.raises(SystemExit) as exc:
        cli_main(["cyber_record", "convert", "-f", ASSET_RECORD])
    assert exc.value.code == 1


def test_roundtrip_preserves_header_chunk_settings(tmp_path):
    pytest.importorskip("mcap")
    source = tmp_path / "source.record"
    mcap_mid = tmp_path / "mid.mcap"
    output = tmp_path / "output.record"

    with Record(ASSET_RECORD) as base:
        samples = list(base.read_messages())[:3]

    with Record(str(source), mode="w", chunk_threshold=4096) as record:
        record.set_write_header_options(
            chunk_interval=123456789,
            segment_interval=987654321,
            chunk_raw_size=4096,
            segment_raw_size=1 << 20,
        )
        for topic, msg, t in samples:
            record.write(topic, msg, t)

    convert_file(
        input_file=str(source),
        output_file=str(mcap_mid),
        from_format="record",
        to_format="mcap",
    )
    convert_file(
        input_file=str(mcap_mid),
        output_file=str(output),
        from_format="mcap",
        to_format="record",
    )

    with Record(str(output)) as record:
        assert record.chunk_threshold == 4096
        assert record._chunk_interval == 123456789
        assert record._segment_interval == 987654321
        assert record._segment_raw_size == 1 << 20
