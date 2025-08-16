# Design

This document explains how `mcap_ros2idl_support` decodes ROS 2 messages from MCAP bag files without a ROS 2 runtime.

## Overview

1. An application opens an MCAP file using the `mcap` reader and supplies a `Ros2DecodeFactory`.
2. For each schema encountered, the factory determines the encoding:
   - `ros2idl` schemas are parsed by `parse_ros2idl`.
   - `ros2msg` schemas are parsed by `parse_ros2msg`.
3. The resulting `MessageDefinition` objects are used to build a `MessageReader`.
4. `MessageReader` uses the `cdr` module to interpret CDR-encoded payloads and returns Python dictionaries.
5. Decoded messages are yielded via `iter_decoded_messages()`.

## Modules

- **cdr** – primitives for reading and writing CDR streams.
- **ros2idl_parser** / **rosmsg** – parse IDL and `.msg` definitions into message descriptions.
- **rosmsg2_serialization** – converts raw CDR data to Python data structures.
- **decode_factory** – ties everything together by providing decoders to the `mcap` reader.

## Flow

```
MCAP file
   ↓
mcap.reader + Ros2DecodeFactory
   ↓                              schema parsing
MessageReader (per schema) ← parse_ros2idl/parse_ros2msg
   ↓
cdr.CdrReader
   ↓
Python dict representing the ROS 2 message
```

Enumerated fields can optionally be returned as their string names, and union types are supported through `MessageReader`.

Example usage is shown in `examples/cli.py`.
