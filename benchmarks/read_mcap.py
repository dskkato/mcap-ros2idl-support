"""Compare original Python and Rust decoding on real MCAP files.

Run: python benchmarks/read_mcap.py --repeat 3 --output benchmarks/results.json
"""

import argparse
import gc
import importlib.metadata
import json
import math
import platform
import statistics
import time
from pathlib import Path

from mcap.reader import make_reader

import mcap_ros2idl_support.decode_factory as factory_module
from mcap_ros2idl_support.rosmsg2_serialization._python_reader import (
    MessageReader as PythonMessageReader,
)
from mcap_ros2idl_support.rosmsg2_serialization.message_reader import MessageReader


def equal(a, b):
    if isinstance(a, bytes) and isinstance(b, list):
        return a == bytes(b)
    if isinstance(b, bytes) and isinstance(a, list):
        return bytes(a) == b
    if type(a) is not type(b):
        return False
    if a == b:
        return True
    if isinstance(a, float):
        return math.isnan(a) and math.isnan(b)
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(equal(v, b[k]) for k, v in a.items())
    if isinstance(a, list):
        return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    return False


def factory(backend):
    factory_module.MessageReader = (
        PythonMessageReader if backend == "python" else MessageReader
    )
    return factory_module.Ros2DecodeFactory(
        array_mode="bytes" if backend == "rust" else "list"
    )


def timed_read(path, backend, topics):
    decoder = factory(backend) if backend != "raw" else None
    gc.collect()
    start = time.perf_counter()
    count = 0
    with path.open("rb") as stream:
        reader = make_reader(stream, decoder_factories=[decoder] if decoder else [])
        messages = (
            reader.iter_decoded_messages(topics=topics, log_time_order=False)
            if decoder
            else reader.iter_messages(topics=topics, log_time_order=False)
        )
        for message in messages:
            count += 1
            del message
    return time.perf_counter() - start, count


def measure(path, repeat, sample_id):
    with path.open("rb") as stream:
        summary = make_reader(stream).get_summary()
        assert summary is not None
    supported = {
        sid
        for sid, s in summary.schemas.items()
        if s.encoding in ("ros2idl", "ros2msg")
    }
    topics = [
        c.topic
        for c in summary.channels.values()
        if c.schema_id in supported and c.message_encoding == "cdr"
    ]
    decoders = {}
    setup = {}
    for backend in ("python", "rust_list", "rust"):
        f = factory(backend)
        start = time.perf_counter()
        decoders[backend] = {
            sid: f.decoder_for("cdr", summary.schemas[sid]) for sid in supported
        }
        setup[backend] = time.perf_counter() - start
    # Stream once: payloads are already extracted/decompressed before each timer.
    # Compare every decoded message, outside the measured decoding intervals.
    isolated = {backend: 0.0 for backend in decoders}
    print(f"{sample_id}: checking all payloads with three decoders", flush=True)
    decoded_count = 0
    total_count = 0
    excluded_count = 0
    payload_bytes = 0
    with path.open("rb") as stream:
        for schema, channel, message in make_reader(stream).iter_messages(
            log_time_order=False
        ):
            total_count += 1
            if channel.topic not in topics:
                excluded_count += 1
                continue
            values = {}
            for backend in (
                ("python", "rust_list", "rust")
                if decoded_count % 2 == 0
                else ("rust", "rust_list", "python")
            ):
                start = time.perf_counter()
                values[backend] = decoders[backend][schema.id](message.data)
                isolated[backend] += time.perf_counter() - start
            if any(
                not equal(values["python"], values[b]) for b in ("rust_list", "rust")
            ):
                raise AssertionError(
                    f"Decode mismatch: {sample_id}, message {total_count}"
                )
            decoded_count += 1
            payload_bytes += len(message.data)
            del values
    times = {k: [] for k in ("raw", "python", "rust_list", "rust")}
    # Warm filesystem caches; results are warm-cache elapsed times, not disk benchmarks.
    timed_read(path, "raw", topics)
    for i in range(repeat):
        for backend in (
            ("raw", "python", "rust_list", "rust")
            if i % 2 == 0
            else ("rust", "rust_list", "python", "raw")
        ):
            elapsed, count = timed_read(path, backend, topics)
            assert count == decoded_count
            times[backend].append(elapsed)
            print(
                f"{sample_id}: {backend} {elapsed:.3f}s ({count} messages)", flush=True
            )
    medians = {k: statistics.median(v) for k, v in times.items()}
    return dict(
        sample_id=sample_id,
        file_bytes=path.stat().st_size,
        total_messages=total_count,
        summary_message_count=summary.statistics.message_count,
        excluded_message_count=excluded_count,
        decoded_messages=decoded_count,
        decoded_payload_bytes=payload_bytes,
        excluded_topic_count=sum(
            c.topic not in topics for c in summary.channels.values()
        ),
        schema_setup_seconds=setup,
        decode_only_seconds=isolated,
        all_messages_values_equal=True,
        rust_array_mode="bytes",
        rust_list_array_mode="list",
        end_to_end_seconds=times,
        median_seconds=medians,
        end_to_end_speedup=medians["python"] / medians["rust"],
        decode_speedup=isolated["python"] / isolated["rust"],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", type=Path, nargs="*")
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("benchmarks/results.json"))
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be positive")
    paths = args.paths or sorted(Path("samples").rglob("*.mcap"))
    if not paths:
        parser.error("No MCAP files found")
    result = dict(
        python=platform.python_version(),
        platform=platform.system(),
        architecture=platform.machine(),
        rust_build="release, thin LTO, CPython abi3-py310",
        mcap_version=importlib.metadata.version("mcap"),
        repeat=args.repeat,
        results=[
            measure(p, args.repeat, f"sample_{i}") for i, p in enumerate(paths, start=1)
        ],
    )
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
