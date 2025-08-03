# mcap-schema-cli

A command-line tool for reading **MCAP** rosbag files and decoding the **CDR**
payloads without a ROS 2 installation.

## Overview

This project was created to make it easier to inspect rosbag data recorded in
the [MCAP](https://mcap.dev) format. The existing Foxglove ros2-support library
only handles `ros2msg` files, so this CLI adds support for full **ROS 2 IDL**
definitions, including enums. It uses Foxglove's
[`@foxglove/ros2idl-parser`](https://www.npmjs.com/package/@foxglove/ros2idl-parser)
to parse IDL files and extracts schema information for each topic.

Parsing is read-only: all fields are expected to be present in the CDR payload
and default values are ignored. Each IDL struct is returned as a plain Python
`dict` so no dynamic class generation is required. The aim is to enable Python
based analysis without depending on a ROS 2 environment.

## Installation

Requires **Node.js 20+** and **Python 3.10+**.

```bash
npm install
npm run build
npm link
```

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Generate type definitions from an MCAP file and decode its messages:

```bash
mcap-schema-cli sample.mcap -o schemas.json
python3 -m mcap_schema_cli --type-definitions schemas.json --mcap-file sample.mcap
```

At present only reading is supported; writing or modifying MCAP files is out of
scope.

