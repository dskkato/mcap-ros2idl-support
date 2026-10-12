# MCAP reading benchmark

Run from the repository root with both sample files available:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
maturin develop --release
python benchmarks/read_mcap.py --repeat 3 --output benchmarks/results.json
```

The script compares the original Python decoder with Rust's compatible list mode
and its default bytes mode. It uses the upstream Python `mcap` reader for every
backend. Chunk reading and decompression remain outside this package.

## Method

- End-to-end times include opening the file, schema parsing/decoder setup, MCAP
  record/chunk processing, decoding, and consuming/discarding decoded messages.
  They use new readers and factories each time, with warmed filesystem caches
  and parser initialization. Reported times are medians of three runs, alternating
  backend order. Messages are read in file order (`log_time_order=False`).
- The `raw` baseline uses `iter_messages()` for the same supported topics, without
  decoding. It exposes the time spent outside this package; do not infer pure
  decoding time by subtracting medians.
- Decode-only times come from a separate streaming pass. Each timer starts after
  MCAP has extracted/decompressed a payload, with all schemas compiled already.
  It measures one decoder call including result allocation, but excludes result
  destruction, schema parsing and chunk processing. These are single-pass totals,
  with decoder order alternated per message, rather than three-run medians.
- All supported messages are decoded with all three backends and compared outside
  timing intervals. The list mode must preserve types and values; bytes mode's
  `uint8` arrays are normalized for value comparison. Matching NaNs count as equal.
- Only CDR messages with `ros2idl` or `ros2msg` schemas are decoded. Other schema
  encodings remain unsupported. The JSON records aggregate exclusion counts and
  actual message counts alongside the file's declared summary count.
- Payloads are streamed, so the benchmark does not keep entire bags in memory.
  It retains the three decoded results for one message during validation. This
  changes allocator/cache behavior in the decode-only pass, so end-to-end times
  are the primary measure for application use.

## Reported metadata

Results and progress output use anonymous labels (`sample_1`, `sample_2`, ...)
assigned in input order, or sorted discovery order when no paths are supplied.
Reports contain aggregate sizes, counts, timings, and software/build versions.
Source paths, filenames, topic names, schema names, recorded timestamps, and
machine-specific kernel/CPU details are omitted. Labels describe this run only;
no source-to-label mapping is saved. Decoder mismatch diagnostics report the
anonymous label and message ordinal.

## Results

Measured on Linux x86_64, CPython 3.10.12,
Rust 1.99.0, PyO3 0.23.5, mcap 1.5.0. Release build with thin LTO and the CPython
stable ABI for Python 3.10 and later. Full measurements are in
[results.json](results.json).

End-to-end median elapsed times (seconds):

| Recording | Messages | Raw MCAP | Python | Rust list | Rust bytes (default) | Speedup |
|---|---:|---:|---:|---:|---:|---:|
| sample_1 | 21,868 | 1.827 | 16.068 | 16.714 | 2.185 | 7.35x |
| sample_2 | 334 | 1.513 | 18.683 | 24.820 | 1.753 | 10.66x |

Decode-only totals (seconds; one validation pass):

| Recording | Python | Rust list | Rust bytes | Speedup |
|---|---:|---:|---:|---:|
| sample_1 | 12.077 | 12.208 | 0.446 | 27.10x |
| sample_2 | 14.205 | 20.379 | 0.266 | 53.38x |

All 22,202 actual messages were decoded and compared successfully. No actual
messages were excluded in either sample.

The default mode changes `uint8[]` and fixed `uint8[N]` values from lists to bytes.
This is responsible for most of the gain on these payload-heavy samples. Rust
alone does not improve large byte-list creation: the Python baseline already
uses C's `memoryview.tolist()`, and Rust list mode can be slower. Use
`Ros2DecodeFactory(array_mode="list")` when list operations or JSON serialization
are required. See [DESIGN.md](../DESIGN.md) for the complete tradeoffs.

These are local, warm-cache elapsed times for these recordings. They do not
measure cold disk performance or predict performance for other schema mixes.
