# cyber_record

## Overview

`cyber_record` is a pure-Python offline tool for Apollo/Cyber record files.
It is a file-level reader, writer, recovery tool, and format converter; it
does not start a Cyber runtime or provide online vehicle control.

Implemented capabilities:

- Read indexed record files and return `(topic, protobuf_message, timestamp_ns)`.
- Filter reads by topic and inclusive nanosecond start/end time.
- Fall back to section scanning when an index is broken or unavailable.
- Inspect record version, size, time range, message count, and channel cache.
- Write protobuf messages or serialized payloads to new record files.
- Open records for reading, writing, and index modification/recovery.
- Expose record compression and chunk/segment header settings in the record
  header.
- Recover a channel index from a protobuf `FileDescriptorSet`.
- Convert `record -> record`, `record -> mcap`, and `mcap -> record`.
- Detect an input format by MCAP magic bytes when `--from-format auto` is used.
- Optionally convert protobuf image and point-cloud messages to/from files and
  flatten protobuf values for CSV output.

The core package requires Python `>=3.8` and
`protobuf>=5.29.0,<6`. MCAP, WheelOS message definitions, and message tools
are optional.

## Role in WheelOS

`cyber_record` is an offline developer/data tool in WheelOS. It sits beside
runtime data producers and consumers and provides post-processing for recorded
protobuf sensor data. It is not a Runtime, Perception, Control, Hardware, or
Calibration component.

```text
WheelOS
 |
 +--- Tools
      |
      +--- cyber_record
```

## Architecture

```text
record file
    |
    +--> Reader
    |      +--> index-based read
    |      +--> section-scan read (broken-index fallback)
    |      +--> channel descriptors -> dynamic protobuf messages
    |
    +--> Writer
           +--> protobuf message serialization
           +--> raw payload writing with explicit type/descriptor
           +--> record header, chunks, and index

Record API
    +--> Python application
    +--> message_tools (optional: image / PCD / CSV)
    +--> converter (optional mcap package)
                +--> record
                +--> MCAP
```

Relevant implementation modules:

| Module | Responsibility |
| --- | --- |
| `record.py` | `Record` public read/write API and record lifecycle |
| `reader.py` | Indexed reads, section scans, channel metadata, protobuf decoding |
| `writer.py` | Headers, channels, chunks, indexes, protobuf/raw payload writes |
| `message_tools.py` | Optional image, point-cloud, and CSV helpers |
| `converter.py` | Record-to-record and cross-format conversion dispatch |
| `mcap_adapter.py` | MCAP reader/writer adapters |
| `main.py` | `cyber_record` command-line entry point |

## Installation

Install the core package:

```sh
python3 -m pip install cyber_record
```

Install from a checkout for development:

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip
python3 -m pip install -e ".[dev,mcap]"
```

Optional extras declared by `pyproject.toml`:

| Extra | Provides | Install |
| --- | --- | --- |
| `msgs` | `wheelos-msgs>=0.1.5`, default Apollo/WheelOS protobuf classes | `python3 -m pip install "cyber_record[msgs]"` |
| `msg-tools` | `numpy`, Pillow, and `python-lzf` for image/PCD/CSV helpers | `python3 -m pip install "cyber_record[msg-tools]"` |
| `mcap` | MCAP conversion dependency | `python3 -m pip install "cyber_record[mcap]"` |
| `dev` | Build, test, message, and helper dependencies used by the repository | `python3 -m pip install "cyber_record[dev]"` |

For typed WheelOS image or point-cloud messages, install both `msgs` and
`msg-tools`:

```sh
python3 -m pip install "cyber_record[msgs,msg-tools]"
```

### Dependency boundary and release scope

The core wheel has exactly one runtime dependency: `protobuf>=5.29.0,<6`.
It does not require or import `wheelos_msgs`, `record_msgs`, `mcap`, Pillow,
NumPy, or `python-lzf` during core record reads and writes. `wheelos_msgs` is
needed only when using the default WheelOS protobuf classes or the `msgs`
extra. A caller can provide custom protobuf message classes to the message
builders.

**Release conclusion:** the core offline record reader/writer and CLI are
publishable as the current package version. MCAP conversion and message
helpers are publishable as opt-in extras. This is not a claim that every
placeholder or unfinished path is production-ready: append mode is not
initialized, record compression values are currently stored in headers but
chunk bodies are not compressed, and `Query`/`Viewer` are placeholders.

## CLI

The package installs the `cyber_record` entry point:

```text
cyber_record <command> [options]
```

### `info`

Print record metadata and per-channel statistics:

```sh
cyber_record info -f test/assets/example.record.00000
```

### `echo`

Print decoded messages for one topic:

```sh
cyber_record echo -f test/assets/example.record.00000 \
  -t /apollo/canbus/chassis
```

### `convert`

Supported source formats are `auto`, `record`, and `mcap`; supported targets
are `record` and `mcap`. `--topic`, `--start-time`, and `--end-time` filter the
converted messages. Timestamps are nanoseconds. `--allow-unindexed` uses the
record section-scan path:

```sh
cyber_record convert -f input.record -o output.record \
  --from-format record --to-format record
cyber_record convert -f input.record -o output.mcap \
  --from-format record --to-format mcap
cyber_record convert -f input.mcap -o output.record \
  --from-format auto --to-format record
cyber_record convert -f broken.record -o output.mcap \
  --from-format record --to-format mcap --allow-unindexed
cyber_record convert -f input.record -o window.mcap \
  --from-format record --to-format mcap \
  --topic /apollo/canbus/chassis \
  --start-time 1627031535164278940 \
  --end-time 1627031535215164773
```

MCAP conversion requires the `mcap` extra. Conversion errors return a
non-zero exit status.

### `recover`

Recover a record channel index using a protobuf descriptor set. The descriptor
set must contain the target message definition and its dependencies. Generate
one with `protoc` from an Apollo source tree, then pass its file, topic, and
message type:

```sh
protoc --include_imports \
  --descriptor_set_out=tmp \
  modules/drivers/proto/sensor_image.proto

cyber_record recover \
  -f broken.record \
  -t /apollo/sensor/camera/front_6mm/image \
  -d tmp \
  -m apollo.drivers.Image
```

Back up the record before recovery. The `-t`, `-m`, and `-d` options map to
the CLI arguments implemented in `main.py`; a topic or message type is
required.

## Python API

### Reading

```python
from cyber_record.record import Record

with Record("test/assets/example.record.00000") as record:
    print(record.version)
    print(record.size)
    print(record.get_message_count())
    print(record.get_channel_cache())
    print(record.get_start_time(), record.get_end_time())

    for topic, message, timestamp_ns in record.read_messages():
        print(topic, type(message), timestamp_ns)
```

`Record.read_messages(topics=None, start_time=None, end_time=None)` accepts a
topic string or topic collection and nanosecond time bounds. For damaged index
files, use the equivalent `read_messages_section_scan(...)` method:

```python
with Record("broken.record", allow_unindexed=True) as record:
    for topic, message, timestamp_ns in record.read_messages_section_scan():
        print(topic, message, timestamp_ns)
```

`read_messages_fallback(...)` exists as a deprecated alias for
`read_messages_section_scan(...)`.

### Writing

`Record` accepts a path or file object. The constructor recognizes `r` (read),
`w` (truncate/create and write), `a` (append), and `m` (modify/recovery).
Messages should be written in chronological order. Append initialization is
currently empty in `record.py`, so `a` is not a supported workflow.

```python
import time

from cyber_record.record import Record
from wheelos_msgs.map_msgs import map_pb2

message = map_pb2.Map()
message.header.version = b"hello"

with Record("example.record.00000", mode="w") as record:
    record.write("/apollo/map", message, int(time.time() * 1e9))
```

For an already serialized protobuf payload, use
`write_raw(topic, raw_msg, message_type, proto_desc, t=None)` with the
message type and serialized descriptor bytes:

```python
with Record("raw.record.00000", mode="w") as record:
    record.write_raw(
        "/example/topic",
        raw_msg=serialized_payload,
        message_type="example.Message",
        proto_desc=serialized_file_descriptor,
        t=1,
    )
```

The `Record` constructor accepts `compression=Compression.NONE`,
`Compression.BZ2`, or `Compression.LZ4`, and `chunk_threshold`. These values
are stored in the record header; the current writer does not compress chunk
bodies. The `options` dictionary can provide `compression` and
`chunk_threshold`. `set_write_header_options(...)` overrides chunk/segment
intervals and raw sizes before the first write flush.

### Conversion API

The conversion functions are available without the CLI:

```python
from cyber_record.converter import convert_file

result = convert_file(
    input_file="input.record",
    output_file="output.mcap",
    from_format="record",
    to_format="mcap",
    topics="/apollo/canbus/chassis",
)
print(result)
```

For record inputs, `convert_file` supports the same format directions,
topic/time filters, and `allow_unindexed` behavior as the CLI. The lower-level
`convert_record_to_record`, `record_to_mcap`, and `mcap_to_record` functions
are also implemented.

## Optional message tools

Install `msg-tools` for `cyber_record.message_tools`:

- `to_csv(value)` flattens scalar values, sequences, protobuf messages, and
  iterables into a list suitable for `csv.writer`.
- `ImageBuilder` builds a protobuf image from an input image using `rgb8`,
  `bgr8`, `gray`, or `y` encoding.
- `ImageParser` writes protobuf images as files (JPEG by default) and supports
  those same encodings. It uses Pillow and does not require OpenCV.
- `PointCloudBuilder` reads ASCII, binary, or `binary_compressed` PCD files.
  The PCD must contain `x`, `y`, `z`, and `intensity` fields; compressed PCD
  input additionally requires `python-lzf`.
- `PointCloudParser` writes protobuf point clouds as ASCII PCD files and
  returns a NumPy structured array. Its output mode is currently ASCII only.

The builders use `wheelos_msgs` message types by default. A caller can pass a
protobuf `message_type` explicitly instead of installing `wheelos-msgs`.

## Repository examples and development

The repository contains the fixture `test/assets/example.record.00000`,
`test/assets/test.jpg`, and `test/assets/test.pcd`. It also contains analysis
examples under `examples/analysis/` and the conversion benchmark:

```sh
PYTHONPATH=. PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python \
python3 scripts/benchmark_conversion.py \
  -f test/assets/example.record.00000 --repeat 3
```

Run the repository tests after installing the `dev` extra:

```sh
pytest -q
```

### Apollo dataset validation

The following local validation was performed against
`/mnt/synology/apollo/sensor_rgb.record`:

| Data | Result |
| --- | --- |
| `/apollo/sensor/camera/front_6mm/image` | Read dynamically as `apollo.drivers.Image`; `rgb8`, 1920x1080 |
| `/apollo/sensor/velodyne64/compensator/PointCloud2` | Read dynamically as `apollo.drivers.PointCloud`; 101,101 points |
| `ImageParser` | Wrote 3 JPEG samples successfully |
| `PointCloudParser` | Wrote 1 ASCII PCD sample successfully |

The extracted samples and `manifest.json` are in
`/mnt/synology/apollo/cyber_record_validation/`. The source record was not
modified. `demo_3.5.record` opens successfully but has no image or point-cloud
channel. `sensor_rgb_mixed_pod.record` currently fails before message
decoding with `google.protobuf.message.DecodeError` while parsing a channel
`ProtoDesc`; `allow_unindexed=True` does not bypass this descriptor error.
Therefore compatibility with that file, and with arbitrary Apollo records, is
not established by this release.

## Documentation

- [Online documentation](https://cyber-record.readthedocs.io/en/latest/)
- [Documentation source](docs/index.rst)
- [Record and MCAP comparison](docs/record_vs_mcap.rst)
- [Implementation plan](docs/implementation_plan.rst)
- [Project repository](https://github.com/daohu527/cyber_record)
- [Issue tracker](https://github.com/daohu527/cyber_record/issues)

The `Query` and `Viewer` modules currently contain placeholder classes and are
not documented as user-facing features.
