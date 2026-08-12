cyber_record
============

``cyber_record`` is a pure-Python offline reader and writer for Apollo/Cyber
record files. It reads and writes protobuf payloads, reports record metadata,
supports indexed and section-scan reads, and provides optional record/MCAP
conversion and image, point-cloud, and CSV helpers.

Implemented capabilities
-------------------------

* Read indexed records and return ``(topic, protobuf_message, timestamp_ns)``.
* Filter reads and conversions by topic and nanosecond time bounds.
* Scan record sections when the index is broken or unavailable.
* Inspect version, size, time range, message count, and channel metadata.
* Write protobuf messages or serialized payloads with explicit descriptors.
* Create and modify record files; expose compression and chunk or segment
  header settings.
* Recover a channel index from a protobuf ``FileDescriptorSet``.
* Convert ``record -> record``, ``record -> mcap``, and ``mcap -> record``.
* Optionally build/parse image and point-cloud messages and flatten values to
  CSV.

Installation
------------

The core package supports Python 3.8 or newer:

.. code-block:: sh

   python3 -m pip install cyber_record

Install optional capabilities with the project extras:

.. code-block:: sh

   python3 -m pip install "cyber_record[msgs]"
   python3 -m pip install "cyber_record[msg-tools]"
   python3 -m pip install "cyber_record[mcap]"

For repository development:

.. code-block:: sh

   python3 -m venv .venv
   source .venv/bin/activate
   python3 -m pip install -U pip
   python3 -m pip install -e ".[dev,mcap]"

Dependency boundary and release scope
-------------------------------------

The core package runtime dependency is exactly
``protobuf>=5.29.0,<6``. Core record reads, writes, and the CLI do not require
``wheelos_msgs``, ``record_msgs``, ``mcap``, Pillow, NumPy, or ``python-lzf``.
The optional ``msgs`` extra provides ``wheelos-msgs``; ``mcap`` and
``msg-tools`` enable their corresponding optional capabilities.

The core offline reader/writer and CLI are publishable as the current package
version. This does not make unfinished paths production-ready: append mode is
not initialized, compression values are stored in headers but chunk bodies
are not compressed, and ``Query``/``Viewer`` are placeholders.

Usage
-----

Inspect a record and print messages from a topic:

.. code-block:: sh

   cyber_record info -f test/assets/example.record.00000
   cyber_record echo -f test/assets/example.record.00000 \
      -t /apollo/canbus/chassis

Read messages with the Python API:

.. code-block:: python

   from cyber_record.record import Record

   with Record("test/assets/example.record.00000") as record:
       for topic, message, timestamp_ns in record.read_messages():
           print(topic, type(message), timestamp_ns)

Read a filtered range:

.. code-block:: python

   from cyber_record.record import Record

   with Record("test/assets/example.record.00000") as record:
       messages = record.read_messages(
           "/apollo/canbus/chassis",
           start_time=1627031535164278940,
           end_time=1627031535215164773,
       )
       for topic, message, timestamp_ns in messages:
           print(topic, message, timestamp_ns)

Use section-scan reading for a record with a broken index:

.. code-block:: python

   from cyber_record.record import Record

   with Record("broken.record", allow_unindexed=True) as record:
       for topic, message, timestamp_ns in record.read_messages_section_scan():
           print(topic, message, timestamp_ns)

Write a protobuf message (requires ``wheelos-msgs``):

.. code-block:: python

   import time

   from cyber_record.record import Record
   from wheelos_msgs.map_msgs import map_pb2

   message = map_pb2.Map()
   message.header.version = b"hello"

   with Record("example.record.00000", mode="w") as record:
       record.write("/apollo/map", message, int(time.time() * 1e9))

Convert record and MCAP files (requires ``mcap``):

.. code-block:: sh

   cyber_record convert -f input.record -o output.mcap \
      --from-format record --to-format mcap
   cyber_record convert -f input.mcap -o output.record \
      --from-format mcap --to-format record

The conversion command also accepts ``--from-format auto``,
``--topic``, ``--start-time``, ``--end-time``, and
``--allow-unindexed``. Supported source formats are ``auto``, ``record``, and
``mcap``; supported targets are ``record`` and ``mcap``. Conversion failures
return a non-zero exit code.

Recover an index with a protobuf descriptor set:

.. code-block:: sh

   protoc --include_imports \
      --descriptor_set_out=tmp \
      modules/drivers/proto/sensor_image.proto
   cyber_record recover \
      -f broken.record \
      -t /apollo/sensor/camera/front_6mm/image \
      -d tmp \
      -m apollo.drivers.Image

Back up the record before recovery. A topic or message type is required.

Write a protobuf message:

.. code-block:: python

   import time

   from cyber_record.record import Record
   from wheelos_msgs.map_msgs import map_pb2

   message = map_pb2.Map()
   message.header.version = b"hello"

   with Record("example.record.00000", mode="w") as record:
       record.write("/apollo/map", message, int(time.time() * 1e9))

The ``Record`` modes are ``r`` (read), ``w`` (create/truncate), ``a``
(accepted by the constructor but not initialized for appending), and ``m``
(modify/recovery). ``Record.write_raw`` accepts an already serialized payload
together with its message type and descriptor. The constructor supports
``Compression.NONE``, ``Compression.BZ2``, ``Compression.LZ4``,
``chunk_threshold``, and an ``options`` dictionary. Compression values are
stored in the record header; the current writer does not compress chunk
bodies.

Optional message tools
----------------------

Install ``cyber_record[msg-tools]`` for ``cyber_record.message_tools``:

* ``to_csv`` flattens scalar, sequence, iterable, and protobuf values.
* ``ImageBuilder`` and ``ImageParser`` support ``rgb8``, ``bgr8``, ``gray``,
  and ``y``. Image output uses Pillow, not OpenCV.
* ``PointCloudBuilder`` reads ASCII, binary, and ``binary_compressed`` PCD
  files containing ``x``, ``y``, ``z``, and ``intensity`` fields.
* ``PointCloudParser`` writes ASCII PCD files and returns a NumPy structured
  array.

The builders use ``wheelos_msgs`` types by default, or accept a caller-provided
protobuf message class. Compressed PCD input additionally needs
``python-lzf``.

Conversion API
--------------

The same conversion paths are available from Python:

.. code-block:: python

   from cyber_record.converter import convert_file

   result = convert_file(
       input_file="input.record",
       output_file="output.mcap",
       from_format="record",
       to_format="mcap",
       topics="/apollo/canbus/chassis",
   )
   print(result)

``convert_record_to_record``, ``record_to_mcap``, and ``mcap_to_record`` are
also implemented.

Repository development
-----------------------

The repository provides ``test/assets/example.record.00000`` and analysis
examples under ``examples/analysis/``. Run the conversion benchmark with:

.. code-block:: sh

   PYTHONPATH=. PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python \
   python3 scripts/benchmark_conversion.py \
      -f test/assets/example.record.00000 --repeat 3

Run tests after installing the ``dev`` extra:

.. code-block:: sh

   pytest -q

Apollo dataset validation
-------------------------

The current implementation was validated against
``/mnt/synology/apollo/sensor_rgb.record``:

* ``/apollo/sensor/camera/front_6mm/image`` decoded as
  ``apollo.drivers.Image`` and produced 1920x1080 ``rgb8`` JPEG samples.
* ``/apollo/sensor/velodyne64/compensator/PointCloud2`` decoded as
  ``apollo.drivers.PointCloud`` and produced an ASCII PCD sample containing
  101,101 points.

The generated samples and ``manifest.json`` are in
``/mnt/synology/apollo/cyber_record_validation/``. ``demo_3.5.record`` opens
but contains no image or point-cloud channel. ``sensor_rgb_mixed_pod.record``
fails during channel ``ProtoDesc`` parsing, including with
``allow_unindexed=True``; support for that file is not established.

Further documentation
---------------------

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   record_vs_mcap
   implementation_plan
