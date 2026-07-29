Record vs MCAP (for upgrade decisions)
======================================

This document compares the current Apollo record format used by this repository with MCAP, and highlights migration implications for ``cyber_record``.

Executive summary
-----------------

* If the priority is short-term compatibility and minimal risk, keep record as primary and improve fallback/read-path robustness.
* If the priority is long-term interoperability, tooling ecosystem, and indexed random access, MCAP is the stronger target format.
* Recommended strategy: add ``record <-> mcap`` conversion and dual-read/dual-write capability first, then evaluate primary format switch.

High-level file structure
-------------------------

Current record
^^^^^^^^^^^^^^

Current record uses sectioned protobuf payloads:

* Header section
* Repeated channel / chunk header / chunk body sections
* Index section (with chunk/channel caches)

In this repository, index-based reading is fast path; section-scan is fallback path for damaged index files.

MCAP
^^^^

MCAP uses a fixed container skeleton:

* ``Magic + Header + Data + [Summary] + [SummaryOffset] + Footer + Magic``
* Data/Summary are sequences of typed records (opcode + length + payload).

MCAP explicitly separates write path and summary/index path, enabling efficient tail-based discovery via Footer.

Detailed comparison
-------------------

+------------------------------+-------------------------------------------------------------+-------------------------------------------------------------------+
| Dimension                    | Apollo record (current)                                     | MCAP                                                              |
+==============================+=============================================================+===================================================================+
| Container framing            | Section type + section size + protobuf payload             | Opcode + uint64 length + binary payload records                   |
+------------------------------+-------------------------------------------------------------+-------------------------------------------------------------------+
| Self-describing schemas      | ``Channel.proto_desc`` embeds protobuf descriptor bytes    | First-class Schema + Channel records, supports multiple encodings |
+------------------------------+-------------------------------------------------------------+-------------------------------------------------------------------+
| Message model                | ``SingleMessage(channel_name, time, content)``             | ``Message(channel_id, sequence, log_time, publish_time, data)``   |
+------------------------------+-------------------------------------------------------------+-------------------------------------------------------------------+
| Indexing model               | Single Index section with chunk/channel caches             | ChunkIndex + MessageIndex + SummaryOffset (multi-level)           |
+------------------------------+-------------------------------------------------------------+-------------------------------------------------------------------+
| Random access                | Good when index is valid; fragile when index is broken     | Strong: Footer-driven summary lookup and per-chunk/per-channel idx|
+------------------------------+-------------------------------------------------------------+-------------------------------------------------------------------+
| Corruption tolerance         | Section scan fallback can recover many broken-index files  | Designed for append/recovery; DataEnd/Footer/CRC improve recovery |
+------------------------------+-------------------------------------------------------------+-------------------------------------------------------------------+
| Integrity checks             | Limited explicit checks in format                           | CRC fields on key records/sections (optional but standardized)    |
+------------------------------+-------------------------------------------------------------+-------------------------------------------------------------------+
| Compression                  | Usually configured by implementation (none/bz2/lz4, etc.)  | Standardized chunk-level compression (commonly zstd/lz4)          |
+------------------------------+-------------------------------------------------------------+-------------------------------------------------------------------+
| Metadata/attachments         | Mostly custom extensions / embedded messages               | First-class Attachment/Metadata/Statistics records                |
+------------------------------+-------------------------------------------------------------+-------------------------------------------------------------------+
| Ecosystem/tooling            | Apollo-centric / custom                                    | Broad robotics and cross-language ecosystem support               |
+------------------------------+-------------------------------------------------------------+-------------------------------------------------------------------+
| Forward extensibility        | Extend protobufs, but less standardized cross-tools        | Explicit opcode/registry evolution path                           |
+------------------------------+-------------------------------------------------------------+-------------------------------------------------------------------+

What this means for this repository
-----------------------------------

Strengths already present
^^^^^^^^^^^^^^^^^^^^^^^^^

* Index path + section-scan path coexist (good base for robust readers).
* Channel descriptors are embedded in files (good for self-contained decode).

Current gaps compared with MCAP-style capabilities
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Summary/index structure is less expressive than MCAP multi-level indices.
* Integrity and consistency metadata are weaker.
* Attachments/metadata/statistics are not first-class file records.
* Cross-ecosystem interoperability cost is higher.

Field mapping reference (record -> MCAP)
----------------------------------------

* ``Header.begin_time/end_time/message_number`` -> MCAP ``Statistics`` (+ optional Metadata mirror)
* ``Channel(name, message_type, proto_desc)`` -> MCAP ``Schema + Channel``
* ``SingleMessage(time, content)`` -> MCAP ``Message(log_time, publish_time, data)``
* ``Index(chunk/channel caches)`` -> MCAP ``ChunkIndex + MessageIndex + SummaryOffset``
* ``map_info/vehicle_info`` -> MCAP ``Metadata``

Performance perspective
-----------------------

* Sequential full scan: both can be fast; implementation details dominate.
* Time/topic selective read: MCAP generally has an advantage due to richer indexing.
* Damaged index scenarios: this repository's section-scan fallback is essential and should be kept even after MCAP integration.

Upgrade recommendation
----------------------

1. Keep current record reader/writer stable for compatibility.
2. Introduce a conversion layer (``record -> mcap``, ``mcap -> record``).
3. Add a unified reader abstraction so tools can consume both backends.
4. Run dual-write/dual-read validation in production-like workloads.
5. Switch primary archival format only after compatibility and performance baselines are met.
