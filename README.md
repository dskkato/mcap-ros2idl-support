# mcap-ros2idl-support

A command-line and Python tool to read and parse ROS 2 MCAP bag files without a ROS 2 runtime.
It extracts schemas from rosbag2 messages and decodes their CDR payloads.

## Features

- Read-only parsing of MCAP/rosbag2 files without needing a ROS 2 runtime
- Supports ROS 2 IDL (including potential enum support) through [@foxglove/ros2idl-parser](https://www.npmjs.com/package/@foxglove/ros2idl-parser)
- Treats each struct as a Python `dict` instead of generating dynamic classes

## Installation

Requires Node.js ≥20 and Python ≥3.10.

```bash
npm --prefix nodejs install
npm --prefix nodejs run deploy
```

```bash
pip install .
```

## Development

### Python

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

### Node.js

The Node.js CLI lives in [`nodejs/`](nodejs/). From that directory:

```bash
npm install
npm run lint
npm test
npm run deploy
```

See [nodejs/README.md](nodejs/README.md) for additional details.

## Usage

```bash
python3 -m mcap_ros2idl_support --mcap-file sample.mcap
```

This command automatically invokes the bundled Node `mcap-schema-extractor` tool to
extract type definitions before decoding messages. You can also run this Node
tool directly during development to generate type definitions:

```bash
npm --prefix nodejs run dev -- sample.mcap -o types.json
```

This runs the TypeScript source without first bundling the CLI. If you've
installed the package, you can invoke the executable directly:

```bash
mcap-schema-extractor sample.mcap -o types.json
```

Currently, the above command will print the whole messages. You can use the internal API to extract specific fields or perform more complex analysis, including visualization. See the `mcap_ros2idl_support/cli.py` file for the basic API usage.

## Building the wheel

This project bundles a Node.js CLI into the Python package. When generating a
wheel for distribution, remove any previous build artifacts so that Node.js
build output doesn't conflict with Python's `dist/` directory.

1. Clean old artifacts:

   ```bash
   rm -rf dist
   ```

2. Install the build backend:

   ```bash
   python -m pip install --upgrade build
   ```

3. Bundle the Node.js CLI:

   ```bash
   npm --prefix nodejs run deploy
   ```

4. Build the wheel:

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
- Enumerations defined in IDL are parsed and returned as their string values when present.
- The goal is to enable parsing MCAP bags without any ROS 2 dependencies to make offline analysis easier.

## Rust prototype

A lightweight Rust implementation demonstrating MCAP parsing is available in [`rust/mcap-rs`](rust/mcap-rs). The CLI accepts an MCAP file, invokes the bundled Node tool to extract type definitions, and prints each decoded message. The crate also exposes library functions for counting messages and decoding CDR payloads. Python bindings for these utilities can be installed with:

```bash
maturin develop --manifest-path rust/mcap-rs/Cargo.toml
```
