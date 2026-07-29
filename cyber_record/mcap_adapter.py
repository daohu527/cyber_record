#!/usr/bin/env python

"""MCAP read/write adapters used by converter."""

from typing import Dict, Tuple

from cyber_record.record import Record

CYBER_RECORD_HEADER_METADATA = "cyber_record.header.v1"


def _import_mcap():
    try:
        from mcap.reader import make_reader
        from mcap.writer import CompressionType, Writer
    except ImportError as err:
        raise ImportError(
            "mcap package is required for mcap conversion. Install with: pip install mcap"
        ) from err
    return make_reader, Writer, CompressionType


def _normalize_topics(topics):
    if topics is None:
        return None
    if isinstance(topics, str):
        return {topics}
    return set(topics)


def _record_message_iter(record, topics, start_time, end_time, allow_unindexed):
    if allow_unindexed:
        return record.read_messages_section_scan(topics, start_time, end_time)
    return record.read_messages(topics, start_time, end_time)


def _build_record_header_metadata(record):
    return {
        "version": record.version,
        "chunk_threshold": str(record.chunk_threshold),
        "chunk_interval": str(record._chunk_interval),
        "segment_interval": str(record._segment_interval),
        "chunk_raw_size": str(record._chunk_raw_size),
        "segment_raw_size": str(record._segment_raw_size),
    }


def _parse_record_header_metadata(reader):
    for item in reader.iter_metadata():
        if item.name == CYBER_RECORD_HEADER_METADATA:
            return dict(item.metadata)
    return {}


def record_to_mcap(
    input_file,
    output_file,
    topics=None,
    start_time=None,
    end_time=None,
    allow_unindexed=False,
):
    """Convert record file to mcap file."""
    _, Writer, CompressionType = _import_mcap()

    converted = 0
    skipped = 0
    schema_ids: Dict[Tuple[str, bytes], int] = {}
    channel_ids: Dict[str, int] = {}

    with Record(input_file, allow_unindexed=allow_unindexed) as src:
        channel_cache = {item.name: item for item in src.get_channel_cache()}
        allowed_topics = _normalize_topics(topics)
        iterator = _record_message_iter(
            src, topics, start_time, end_time, allow_unindexed
        )
        with open(output_file, "wb") as out_stream:
            writer = Writer(out_stream, compression=CompressionType.ZSTD)
            writer.start(profile="cyber_record")
            writer.add_metadata(
                name=CYBER_RECORD_HEADER_METADATA,
                data=_build_record_header_metadata(src),
            )
            for topic_name, cache in channel_cache.items():
                if allowed_topics is not None and topic_name not in allowed_topics:
                    continue
                schema_key = (cache.message_type, bytes(cache.proto_desc))
                schema_id = schema_ids.get(schema_key)
                if schema_id is None:
                    schema_id = writer.register_schema(
                        name=cache.message_type,
                        encoding="protobuf",
                        data=bytes(cache.proto_desc),
                    )
                    schema_ids[schema_key] = schema_id
                channel_ids[topic_name] = writer.register_channel(
                    topic=topic_name,
                    message_encoding="protobuf",
                    schema_id=schema_id,
                )

            for topic, message, t in iterator:
                if message is None:
                    skipped += 1
                    continue

                cache = channel_cache.get(topic)
                if cache is not None:
                    message_type = cache.message_type
                    proto_desc = bytes(cache.proto_desc)
                else:
                    message_type = f"{message.DESCRIPTOR.file.package}.{type(message).__name__}"
                    proto_desc = b""

                schema_key = (message_type, proto_desc)
                schema_id = schema_ids.get(schema_key)
                if schema_id is None:
                    schema_id = writer.register_schema(
                        name=message_type,
                        encoding="protobuf",
                        data=proto_desc,
                    )
                    schema_ids[schema_key] = schema_id

                channel_id = channel_ids.get(topic)
                if channel_id is None:
                    channel_id = writer.register_channel(
                        topic=topic,
                        message_encoding="protobuf",
                        schema_id=schema_id,
                    )
                    channel_ids[topic] = channel_id

                writer.add_message(
                    channel_id=channel_id,
                    log_time=t,
                    publish_time=t,
                    data=message.SerializeToString(),
                )
                converted += 1
            writer.finish()

    return {
        "converted": converted,
        "skipped": skipped,
        "output_channels": len(channel_ids),
    }


def mcap_to_record(
    input_file,
    output_file,
    topics=None,
    start_time=None,
    end_time=None,
    allow_unindexed=False,  # kept for API consistency
):
    """Convert mcap file to record file."""
    make_reader, _, _ = _import_mcap()

    converted = 0
    skipped = 0
    source_messages = 0
    source_channels = set()
    output_channels = set()

    with open(input_file, "rb") as in_stream:
        reader = make_reader(in_stream)
        with Record(output_file, mode="w") as dst:
            meta = _parse_record_header_metadata(reader)
            if meta:
                dst.set_write_header_options(
                    chunk_interval=meta.get("chunk_interval"),
                    segment_interval=meta.get("segment_interval"),
                    chunk_raw_size=meta.get("chunk_raw_size"),
                    segment_raw_size=meta.get("segment_raw_size"),
                )
            for schema, channel, message in reader.iter_messages(
                topics=topics,
                start_time=start_time,
                end_time=end_time,
                log_time_order=True,
            ):
                source_messages += 1
                source_channels.add(channel.topic)
                msg_type = schema.name if schema else channel.message_encoding
                proto_desc = schema.data if schema else b""
                if not msg_type:
                    skipped += 1
                    continue
                dst.write_raw(
                    topic=channel.topic,
                    raw_msg=message.data,
                    message_type=msg_type,
                    proto_desc=proto_desc,
                    t=message.log_time,
                )
                output_channels.add(channel.topic)
                converted += 1

    return {
        "converted": converted,
        "skipped": skipped,
        "source_messages": source_messages,
        "source_channels": len(source_channels),
        "output_channels": len(output_channels),
    }
