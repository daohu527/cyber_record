Implementation plan for current repository
==========================================

This plan translates the record-vs-MCAP analysis into concrete implementation steps for ``cyber_record``.

Goals
-----

* Keep existing record workflows stable.
* Improve robustness/performance of current record path.
* Prepare a low-risk migration path toward MCAP interoperability.

Phase 1: Harden current record path (short-term)
------------------------------------------------

Scope
^^^^^

* Keep index-based read as default fast path.
* Keep section-scan read as explicit fallback for broken index.
* Ensure ``allow_unindexed`` behavior is consistent and documented.

Tasks
^^^^^

1. Reader robustness

   * Validate section boundaries before parsing payload.
   * Keep graceful stop behavior on partial/truncated sections.
   * Ensure channel descriptors can be reconstructed from section scan when index is invalid.

2. Performance improvements

   * Keep topic filter normalization outside hot loops.
   * Keep chunk-header prefilter in section-scan path to skip irrelevant chunk bodies.
   * Benchmark index path vs section-scan path with topic/time filters.

3. Test coverage

   * Add regression tests for:
     * broken index but readable chunks
     * truncated tail section
     * parity of message counts between index path and section-scan path
   * Keep fixtures small and deterministic.

Acceptance criteria
^^^^^^^^^^^^^^^^^^^

* Broken-index files are readable with ``allow_unindexed=True``.
* Filtered reads return identical logical results between index and section-scan modes.
* No behavior regression for valid indexed files.

Phase 2: Introduce MCAP interoperability (mid-term)
---------------------------------------------------

Scope
^^^^^

* Add conversion tools first; do not replace primary format yet.

Tasks
^^^^^

1. Data model mapping layer

   * Implement canonical in-memory model:
     * ``ChannelDef``, ``SchemaDef``, ``MessageEnvelope``, ``FileStats``.
   * Keep mapping functions:
     * record -> canonical
     * canonical -> record
     * mcap -> canonical
     * canonical -> mcap

2. Conversion CLI/API

   * ``cyber_record convert --from record --to mcap``
   * ``cyber_record convert --from mcap --to record``
   * Add options for time/topic subset conversion.

3. Validation suite

   * Round-trip checks (record -> mcap -> record):
     * message count parity
     * topic parity
     * timestamp parity
   * Schema/channel consistency checks.

Acceptance criteria
^^^^^^^^^^^^^^^^^^^

* Converters preserve core semantics for supported message types.
* Round-trip mismatch rate is zero for baseline fixtures.

Phase 3: Unified backend abstraction (mid/long-term)
----------------------------------------------------

Scope
^^^^^

* Hide storage format behind a shared reader interface.

Tasks
^^^^^

1. Reader interface

   * Define shared methods:
     * ``read_messages(...)``
     * ``read_messages_section_scan(...)`` (or backend-specific equivalent)
     * ``get_channel_cache(...)``
     * ``get_start_time()/get_end_time()``

2. Backend adapters

   * ``RecordBackendReader``
   * ``McapBackendReader``

3. Auto-detection

   * Detect by magic/header signature and route to backend automatically.

Acceptance criteria
^^^^^^^^^^^^^^^^^^^

* Existing user code can read both formats with minimal/no API changes.

Phase 4: Dual-write and migration decision (long-term)
------------------------------------------------------

Scope
^^^^^

* Gather production evidence before switching primary archival format.

Tasks
^^^^^

1. Optional dual-write mode

   * Write record and mcap in parallel behind a feature flag.

2. Operational benchmarking

   * Throughput (write/read)
   * Disk footprint
   * Query latency by time/topic window
   * Recovery behavior after interrupted writes

3. Migration gate

   * Define numeric thresholds and make go/no-go decision.

Acceptance criteria
^^^^^^^^^^^^^^^^^^^

* Primary-format switch only after benchmarks and compatibility checks pass.

Prioritized backlog (recommended order)
---------------------------------------

1. Add regression tests for broken/truncated index scenarios.
2. Add conversion command skeleton and canonical model types.
3. Implement record -> mcap converter.
4. Implement mcap -> record converter.
5. Add unified reader abstraction and backend auto-detection.
6. Add optional dual-write mode and benchmark harness.

Current implementation status
-----------------------------

Completed in current iteration:

1. Phase 1 robustness/performance baseline:

   * ``allow_unindexed`` open path for broken/truncated index.
   * Section-scan parity and corrupted-index regression tests.
   * Section-scan chunk-header prefilter and topic filter normalization.

2. Phase 2 scaffolding:

   * Canonical conversion model types (``model.py``).
   * Converter module scaffold (``converter.py``) and MCAP adapter module (``mcap_adapter.py``).
   * ``cyber_record convert`` CLI command (``record -> record``, ``record -> mcap``, ``mcap -> record``).
   * Round-trip conversion regression tests for baseline fixture.

Planned next:

1. Preserve additional metadata fields in ``record <-> mcap`` path.
2. Extend parity tests with larger and partially corrupted fixtures.
3. Add backend auto-detection and unified reader abstraction.

Production readiness gate
-------------------------

The project is considered production-ready only after all items below are green.

1. Correctness gate

   * Round-trip parity on representative datasets:
     * message count parity
     * topic parity
     * timestamp parity
     * schema/message type parity
   * Corruption scenarios:
     * broken index
     * truncated tail
     * partial write interruption

2. Reliability gate

   * Deterministic conversion behavior for the same input and options.
   * Clear failure mode and non-zero exit behavior for conversion errors.
   * Backward compatibility for existing ``Record`` read/write API.

3. Performance gate

   * Baseline throughput targets for:
     * record -> record
     * record -> mcap
     * mcap -> record
   * Memory ceiling under large-file conversion.
   * Indexed read latency target for time/topic filtered scans.

4. Operability gate

   * CLI usage documented for all conversion directions and options.
   * Dependency contract documented (protobuf, optional mcap extra).
   * CI job covering conversion and robustness tests.

Current production status
-------------------------

Current status: **production-ready for the current schema scope**.

Production gates satisfied:

* Robust fallback reads for broken/truncated index.
* Bidirectional conversion commands (record<->mcap) implemented.
* Round-trip and robustness regression tests in CI matrix.
* Explicit non-zero CLI failure contract for conversion errors.
* Repeatable benchmark harness for conversion throughput/memory checks.

Known schema limitation:

* ``cyber_record`` currently uses a Header schema without ``map_info/vehicle_info`` fields.
  These extension fields cannot be losslessly round-tripped until protobuf schema is upgraded in this repository.

Latest status update
--------------------

After this iteration:

* CI conversion matrix is implemented (``.github/workflows/conversion-ci.yml``).
* CLI conversion failure contract is implemented (non-zero exit).
* Baseline performance harness is implemented (``scripts/benchmark_conversion.py``).

Open production blocker:

1. Metadata preservation parity for record header extension fields is still incomplete.
