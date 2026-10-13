# Changelog

## 0.2.0 (Unreleased)

### Breaking changes

- `Ros2DecodeFactory()` now returns immutable `bytes` for non-enum `uint8[]`
  and fixed `uint8[N]` fields, including nested fields and union members.
  Code that mutates these arrays, compares them with lists, or serializes them
  directly with `json.dumps` must use `Ros2DecodeFactory(array_mode="list")`
  or explicitly convert the fields to lists. Other arrays remain lists.
  Direct `MessageReader` usage still defaults to lists; opt into bytes with
  `MessageReaderOptions(arrayMode="bytes")`.
- CDR message decoding now requires the Rust/PyO3 native extension, with no
  automatic Python fallback. The build backend has changed from setuptools
  to maturin. Source installs require Rust, Cargo, and access to Cargo
  dependencies. Wheels are platform-specific and require CPython 3.10 or later;
  pure Python wheels and PyPy are no longer supported.
- The native decoder validates CDR encapsulation, payload bounds, and sequence
  lengths. Malformed payloads raise `ValueError`; parameter-list and delimited
  encapsulations are explicitly rejected. Nesting is limited to 128 levels.
  Callers relying on permissive decoding or previous error types may need
  to update their input validation and exception handling.

### Added

- Rust CDR decoding with compiled schema plans for primitives, arrays, nested
  structs, unions, and enum string mappings.
- Explicit support for plain CDR1 and plain XCDR2 in both byte orders, including
  RTPS plain XCDR2 encapsulation IDs.
- Reproducible MCAP reading and decoding benchmarks with recorded results and
  a Python reference decoder.
- CI builds and tests CPython 3.10+ abi3 wheels for Linux x86_64 and aarch64,
  macOS Apple Silicon, and Windows x86_64, plus a source distribution.
- Tag-triggered PyPI publishing of tested distributions, with validation that
  the tag matches the Python and Rust package versions.

### Fixed

- Zero-length fixed arrays consume no sequence-length prefix during decoding.

### Migration example

To retain the previous byte-array representation:

```python
from mcap_ros2idl_support import Ros2DecodeFactory

factory = Ros2DecodeFactory(array_mode="list")
```

The example CLI uses list mode to preserve its JSON output. The MCAP decoder
factory interface and `enum_as_string` option retain their behavior.

## 0.1.3

### Fixed

- Added `MessageReaderOptions(rootTypeName=...)` to select an explicit root
  message type. `Ros2DecodeFactory` uses the MCAP schema name to select the
  correct root when an IDL schema contains multiple definitions.

## 0.1.2

### Fixed

- Deferred IDL constant and bound resolution supports forward references.

## 0.1.1

### Fixed

- IDL `octet` is treated as `uint8`.
