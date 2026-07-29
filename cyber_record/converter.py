#!/usr/bin/env python

"""Format conversion helpers."""

from typing import Dict

from cyber_record.format_utils import detect_file_format
from cyber_record.mcap_adapter import mcap_to_record, record_to_mcap
from cyber_record.model import FileStats
from cyber_record.record import Record


def _iter_messages(record: Record, topics, start_time, end_time, allow_unindexed):
    if allow_unindexed:
        return record.read_messages_section_scan(topics, start_time, end_time)
    return record.read_messages(topics, start_time, end_time)


def _collect_stats(record: Record) -> FileStats:
    return FileStats(
        message_count=record.get_message_count(),
        channel_count=len(record.get_channel_cache()),
        begin_time=record.get_start_time(),
        end_time=record.get_end_time(),
    )


def convert_record_to_record(
    input_file: str,
    output_file: str,
    topics=None,
    start_time=None,
    end_time=None,
    allow_unindexed=False,
) -> Dict[str, int]:
    """Convert record to record with optional topic/time filtering."""
    converted = 0
    skipped = 0
    output_channels = set()
    with Record(input_file, allow_unindexed=allow_unindexed) as src:
        src_stats = _collect_stats(src)
        with Record(output_file, mode="w") as dst:
            for topic, message, t in _iter_messages(
                src, topics, start_time, end_time, allow_unindexed
            ):
                if message is None:
                    skipped += 1
                    continue
                dst.write(topic, message, t)
                converted += 1
                output_channels.add(topic)

    return {
        "converted": converted,
        "skipped": skipped,
        "source_messages": src_stats.message_count,
        "source_channels": src_stats.channel_count,
        "output_messages": converted,
        "output_channels": len(output_channels),
    }


def convert_file(
    input_file: str,
    output_file: str,
    from_format: str,
    to_format: str,
    topics=None,
    start_time=None,
    end_time=None,
    allow_unindexed=False,
) -> Dict[str, int]:
    """Convert files across supported formats."""
    if from_format == "auto":
        from_format = detect_file_format(input_file)

    if from_format == "record" and to_format == "record":
        return convert_record_to_record(
            input_file=input_file,
            output_file=output_file,
            topics=topics,
            start_time=start_time,
            end_time=end_time,
            allow_unindexed=allow_unindexed,
        )

    if from_format == "record" and to_format == "mcap":
        with Record(input_file, allow_unindexed=allow_unindexed) as src:
            src_stats = _collect_stats(src)
        output = record_to_mcap(
            input_file=input_file,
            output_file=output_file,
            topics=topics,
            start_time=start_time,
            end_time=end_time,
            allow_unindexed=allow_unindexed,
        )
        return {
            "converted": output["converted"],
            "skipped": output["skipped"],
            "source_messages": src_stats.message_count,
            "source_channels": src_stats.channel_count,
            "output_messages": output["converted"],
            "output_channels": output["output_channels"],
        }

    if from_format == "mcap" and to_format == "record":
        output = mcap_to_record(
            input_file=input_file,
            output_file=output_file,
            topics=topics,
            start_time=start_time,
            end_time=end_time,
            allow_unindexed=allow_unindexed,
        )
        with Record(output_file) as dst:
            dst_stats = _collect_stats(dst)
        return {
            "converted": output["converted"],
            "skipped": output["skipped"],
            "source_messages": output["source_messages"],
            "source_channels": output["source_channels"],
            "output_messages": dst_stats.message_count,
            "output_channels": dst_stats.channel_count,
        }

    raise ValueError(f"Unsupported conversion: {from_format} -> {to_format}")
