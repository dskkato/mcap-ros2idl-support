# Design

`Ros2DecodeFactory` still implements `mcap.decoder.DecoderFactory`: pass it to
`make_reader(..., decoder_factories=[factory])` and consume
`iter_decoded_messages()`. Schema IDs cache a decoder; unsupported schema IDs
cache a negative result. MCAP records, indexes, chunks and compression are handled
entirely by the upstream Python `mcap` package.

## Decoding

1. Parse each `ros2idl` or `ros2msg` schema once with the existing Python parsers.
2. Select the root by schema name, resolve nested definitions and enum mappings,
   and compile an immutable Rust plan through PyO3.
3. Decode each CDR payload in Rust. Alignment, byte order, primitive and array
   reads, nested structs, union selection, and Python dictionary construction
   happen in the native extension. Field names and enum strings are interned
   once. MCAP's immutable `bytes` payload is borrowed during the call.

The original reader is retained privately in `_python_reader.py` as the benchmark
reference and for shared schema setup. It is not an automatic decoding fallback.
Schema parsing and the existing CDR writing/utilities APIs remain in Python.

## Performance and compatibility

The factory defaults to `array_mode="bytes"`: non-enum `uint8[]` and fixed
`uint8[N]` fields become immutable Python `bytes`, including nested fields and
union members. This avoids allocating one list entry per payload byte, which
dominates these samples. The bytes object owns a copy of its field data and
does not retain an entire MCAP chunk. Other arrays remain lists; structs and
time values remain dictionaries, and `enum_as_string` retains its behavior.

Use `Ros2DecodeFactory(array_mode="list")` to retain the original output types.
This mode can be slower than Python on messages dominated by large byte arrays:
Python's `memoryview.tolist()` is already a C loop, and Rust still has to create
all Python list elements. The basic MCAP interface is unchanged, but the default
byte-array representation is an intentional compatibility tradeoff. List
mutation, list equality, and direct JSON serialization require the list mode or
explicit conversion. For NumPy, use `numpy.frombuffer(message["data"], dtype=...)`.

Direct `MessageReader` usage continues to default to lists. Opt into bytes with
`MessageReaderOptions(arrayMode="bytes")`. `bytes` inputs are borrowed; mutable
`bytearray` and `memoryview` inputs are copied before native decoding. The decoder
holds Python's GIL while creating Python objects, so Python threads do not
parallelize decoding. Use processes for concurrent decoding.

Supported payloads are plain CDR1 and plain XCDR2, in both byte orders, including
RTPS plain XCDR2 IDs. Parameter-list and delimited encapsulations are rejected
explicitly: schema extensibility/member metadata would be needed to decode them
correctly. The previous message decoder did not interpret their headers either.
`wstring` remains unsupported. Reads check bounds and sequence lengths before
allocation, malformed payloads raise `ValueError`, and nesting is limited to 128
levels. Zero-length fixed arrays now consume no sequence-length prefix.

## Building

The build backend is maturin and the decoder is a Rust/PyO3 extension. Source
installs require a Rust toolchain and Cargo dependency downloads. Wheels use the
CPython stable ABI for Python 3.10 and later, but are platform-specific. Pure
Python wheels and PyPy are no longer supported. Release builds enable thin LTO;
benchmarks must use release builds.

See [benchmarks/README.md](benchmarks/README.md) for measurements and reproduction.
