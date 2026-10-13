# mcap-ros2idl-support


A Python library to read and parse ROS 2 MCAP bag files without a ROS 2 runtime.
It extracts schemas from rosbag2 messages and decodes their CDR payloads.

See [CHANGELOG.md](CHANGELOG.md) for release notes and breaking changes.

## Features

- Read-only parsing of MCAP/rosbag2 files without needing a ROS 2 runtime
- Treats each struct as a Python `dict` instead of generating dynamic classes
- Decodes CDR payloads in Rust; `uint8` arrays default to `bytes` for speed

## Installation

Requires CPython ≥3.10. Building from source also requires Rust and Cargo.
The package uses a Rust/PyO3 decoder built with maturin.

Install the Python package:

```bash
pip install .
```

## Usage

### Python example

```python
from mcap.reader import make_reader
from mcap_ros2idl_support import Ros2DecodeFactory

factory = Ros2DecodeFactory()

with open("sample.mcap", "rb") as f:
    reader = make_reader(f, decoder_factories=[factory])
    for decoded in reader.iter_decoded_messages():
        print(decoded.channel.topic)
        print(decoded.decoded_message)
```

### Byte-array compatibility

The factory defaults to `Ros2DecodeFactory(array_mode="bytes")`. `uint8[]` and
fixed `uint8[N]` fields return immutable `bytes`; all other arrays remain lists.
This substantially reduces the time and memory needed for image/point-cloud data.
Use `Ros2DecodeFactory(array_mode="list")` for the previous list representation,
including direct JSON serialization. The MCAP decoder factory interface and
`enum_as_string` option are unchanged.

See [DESIGN.md](DESIGN.md) for compatibility details and
[benchmarks/README.md](benchmarks/README.md) for sample benchmarks.

### Command line

```bash
python examples/cli.py --mcap-file sample.mcap
```

Use the ``--enum-as-string`` flag to return enumeration values as strings:

```bash
python examples/cli.py --mcap-file sample.mcap --enum-as-string
```

## Development

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install project and development dependencies:

   ```bash
   pip install -e '.[dev]'
   ```

3. Install and run `pre-commit`:

   ```bash
   pre-commit install
   pre-commit run --files <file> [<file> ...]
   ```

   To check the entire repository, use:

   ```bash
   pre-commit run --all-files
   ```

4. Run tests with `pytest`:

   ```bash
   pytest
   ```

## Building the wheel

The [Package build workflow](.github/workflows/package-build.yml) runs on branch pushes,
pull requests, and manual dispatches. It builds and tests CPython 3.10+ abi3 wheels
for Linux x86_64 and aarch64 (manylinux2014), macOS Apple Silicon, and Windows
x86_64. Wheels and a source distribution are available in the workflow run's
Artifacts section.

1. Clean old artifacts:

   ```bash
   rm -rf dist
   ```

2. Install the build backend:

   ```bash
   python -m pip install --upgrade build
   ```

3. Build the wheel:

   ```bash
   python -m build
   ```

4. (Optional) Verify the wheel locally:

   ```bash
   python -m pip install dist/mcap_ros2idl_support-<version>-cp310-abi3-<platform>.whl
   ```

5. (Optional) Upload to PyPI:

   ```bash
   python -m pip install --upgrade twine
   python -m twine upload dist/*
   ```

## Releasing to PyPI

The [Release workflow](.github/workflows/release.yml) runs when a `v*` tag is
pushed. It checks that the tag matches the versions in both `pyproject.toml` and
`Cargo.toml`, builds and tests all four platform wheels, then publishes the wheels
and source distribution to PyPI.

Before the first release, create the GitHub Actions environment `pypi` and
[configure a PyPI Trusted Publisher](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)
for the project with these values:

- Owner: `dskkato`
- Repository: `mcap-ros2idl-support`
- Workflow filename: `release.yml`
- Environment: `pypi`

No PyPI API token secret is required. Update both package versions, commit the
changes, and push a matching tag on that commit, for example:

```bash
git tag v0.2.0
git push origin v0.2.0
```

Use a new version for each release; PyPI does not allow replacing published files.

## Project structure

The repository is organized as follows:

- `mcap_ros2idl_support/` – core Python package
  - `cdr/` – helpers for reading and writing CDR streams
  - `ros2idl_parser/` – parser for `ros2idl` schema definitions
  - `rosmsg/` – parser for classic `.msg` message definitions
  - `rosmsg2_serialization/` – utilities for decoding CDR payloads into dictionaries
  - `decode_factory.py` – integrates parsers and the Rust decoder with MCAP
- `src/lib.rs` – native CDR decoder
- `benchmarks/` – reproducible reading and decoding comparisons
- `examples/` – example CLI demonstrating how to iterate decoded messages
- `tests/` – unit tests for the library

## Design notes

- Uses Foxglove’s `@foxglove/ros2idl-parser` to handle `.idl` files in addition to classic `.msg` definitions.
- MCAP file writing is not supported, though CDR encoding helpers are available for individual messages.
- Enumerations defined in IDL can be returned as their string values by
  enabling ``enum_as_string``.
- The goal is to enable parsing MCAP bags without any ROS 2 dependencies to make offline analysis easier.
