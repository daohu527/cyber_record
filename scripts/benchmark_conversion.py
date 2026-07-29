#!/usr/bin/env python3

"""Simple conversion benchmark for production readiness checks."""

import argparse
import os
import tempfile
import time
import tracemalloc

from cyber_record.converter import convert_file


def run_benchmark(input_file, repeat=3):
    results = []
    for _ in range(repeat):
        tmp_mcap = tempfile.NamedTemporaryFile(prefix="bench_", suffix=".mcap", delete=False)
        tmp_record = tempfile.NamedTemporaryFile(prefix="bench_", suffix=".record", delete=False)
        tmp_mcap.close()
        tmp_record.close()
        try:
            tracemalloc.start()
            t0 = time.perf_counter()
            result_rm = convert_file(
                input_file=input_file,
                output_file=tmp_mcap.name,
                from_format="record",
                to_format="mcap",
            )
            t1 = time.perf_counter()
            result_mr = convert_file(
                input_file=tmp_mcap.name,
                output_file=tmp_record.name,
                from_format="mcap",
                to_format="record",
            )
            t2 = time.perf_counter()
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            results.append(
                {
                    "record_to_mcap_s": t1 - t0,
                    "mcap_to_record_s": t2 - t1,
                    "messages": result_rm["converted"],
                    "peak_mem_mb": peak / (1024 * 1024),
                    "roundtrip_messages": result_mr["converted"],
                }
            )
        finally:
            os.unlink(tmp_mcap.name)
            os.unlink(tmp_record.name)
    return results


def main():
    parser = argparse.ArgumentParser(description="Benchmark conversion paths.")
    parser.add_argument("-f", "--file", required=True, help="input record file")
    parser.add_argument("--repeat", type=int, default=3, help="repeat times")
    args = parser.parse_args()

    results = run_benchmark(args.file, args.repeat)
    for idx, result in enumerate(results, start=1):
        print(
            f"run={idx} messages={result['messages']} "
            f"record_to_mcap={result['record_to_mcap_s']:.4f}s "
            f"mcap_to_record={result['mcap_to_record_s']:.4f}s "
            f"peak_mem={result['peak_mem_mb']:.2f}MB "
            f"roundtrip_messages={result['roundtrip_messages']}"
        )


if __name__ == "__main__":
    main()
