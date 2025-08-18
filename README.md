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
   python -m pip install dist/mcap_ros2idl_support-<version>-py3-none-any.whl
   ```

5. (Optional) Upload to PyPI:

   ```bash
   python -m pip install --upgrade twine
   python -m twine upload dist/*
   ```

## Project structure

The repository is organized as follows:

- `mcap_ros2idl_support/` – core Python package
  - `cdr/` – helpers for reading and writing CDR streams
  - `ros2idl_parser/` – parser for `ros2idl` schema definitions
  - `rosmsg/` – parser for classic `.msg` message definitions
  - `rosmsg2_serialization/` – utilities for decoding CDR payloads into dictionaries
  - `decode_factory.py` – integrates parsers and CDR readers with the MCAP decoder
- `examples/` – example CLI demonstrating how to iterate decoded messages
- `tests/` – unit tests for the library

## Design notes

- Uses Foxglove’s `@foxglove/ros2idl-parser` to handle `.idl` files in addition to classic `.msg` definitions.
- MCAP file writing is not supported, though CDR encoding helpers are available for individual messages.
- Enumerations defined in IDL can be returned as their string values by
  enabling ``enum_as_string``.
- The goal is to enable parsing MCAP bags without any ROS 2 dependencies to make offline analysis easier.
