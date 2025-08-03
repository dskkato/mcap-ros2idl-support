# mcap-schema-cli

A command-line and Python tool to read and parse ROS 2 MCAP bag files without a ROS 2 runtime.
It extracts schemas from rosbag2 messages and decodes their CDR payloads.

## Features

- Read-only parsing of MCAP/rosbag2 files
- Supports ROS 2 IDL (including potential enum support) through [@foxglove/ros2idl-parser](https://www.npmjs.com/package/@foxglove/ros2idl-parser)
- Treats each struct as a Python `dict` instead of generating dynamic classes
- Ignores default values; CDR payloads are assumed to contain all field values
- Allows analysis of bags in Python without installing ROS 2

## Installation

Requires Node.js ≥20 and Python ≥3.10.

```bash
npm install
npm run build
npm link
```

```bash
pip install -r requirements.txt
```

## Usage

```bash
mcap-schema-cli sample.mcap -o schemas.json
python3 -m mcap_schema_cli --type-definitions schemas.json --mcap-file sample.mcap
```

## Design notes

- Uses Foxglove’s `@foxglove/ros2idl-parser` to handle `.idl` files in addition to classic `.msg` definitions.
- Only reading is supported; writing MCAP files is out of scope.
- Enumerations defined in IDL are parsed and returned as their string values when present.
- The goal is to enable parsing MCAP bags without any ROS 2 dependencies to make offline analysis easier.
