# mcap-ros2idl-support


A Python library to read and parse ROS 2 MCAP bag files without a ROS 2 runtime.
It extracts schemas from rosbag2 messages and decodes their CDR payloads.

## Features

- Read-only parsing of MCAP/rosbag2 files without needing a ROS 2 runtime
- Treats each struct as a Python `dict` instead of generating dynamic classes

## Installation

Requires Python ≥3.10.

Install the Python package:

```bash
pip install .
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

3. Build the Rust Python bindings using `maturin`:

   ```bash
   maturin develop --manifest-path rust/mcap-rs/Cargo.toml
   ```

4. Install and run `pre-commit`:

   ```bash
   pre-commit install
   pre-commit run --files <file> [<file> ...]
   ```

   To check the entire repository, use:

   ```bash
   pre-commit run --all-files
   ```

5. Run tests with `pytest`:

   ```bash
   pytest
   ```

## Usage

```bash
python examples/cli.py --mcap-file sample.mcap
```

Use the ``--enum-as-string`` flag to return enumeration values as strings:

```bash
python examples/cli.py --mcap-file sample.mcap --enum-as-string
```

## Building the wheel

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

5. (Optional) Verify the wheel locally:

   ```bash
   python -m pip install dist/mcap_ros2idl_support-<version>-py3-none-any.whl
   ```

6. (Optional) Upload to PyPI:

   ```bash
   python -m pip install --upgrade twine
   python -m twine upload dist/*
   ```

## Design notes

- Uses Foxglove’s `@foxglove/ros2idl-parser` to handle `.idl` files in addition to classic `.msg` definitions.
- Only reading is supported; writing MCAP files is out of scope.
- Enumerations defined in IDL can be returned as their string values by
  enabling ``enum_as_string``.
- The goal is to enable parsing MCAP bags without any ROS 2 dependencies to make offline analysis easier.

## Rust prototype

A lightweight Rust implementation demonstrating MCAP parsing is available in [`rust/mcap-rs`](rust/mcap-rs). The CLI accepts an MCAP file, invokes the bundled Node tool to extract type definitions, and prints each decoded message. The crate also exposes library functions for counting messages and decoding CDR payloads. Python bindings for these utilities can be installed with:

```bash
maturin develop --manifest-path rust/mcap-rs/Cargo.toml
```
