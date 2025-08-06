# mcap-rs

A small Rust prototype demonstrating how to read [MCAP](https://mcap.dev) files,
parse ROS 2 IDL type definitions, and decode CDR-encoded message data.

## Usage

Decode all messages in an MCAP file (type definitions are extracted via the
bundled Node.js CLI and decoded as JSON):

```
cargo run -- <mcap-file>
```

Decode a CDR message using loaded type definitions:

```
use mcap_rs::CdrReader;
// `schemas` is a HashMap<u32, SchemaInfo> produced by the Node helper
let info = &schemas[&1];
let reader = CdrReader::new(info);
let msg = reader.read("Msg", &cdr_bytes)?;
```

The crate exposes [`count_messages`] for iterating over messages and
[`CdrReader`] for decoding CDR payloads into structured
`serde_json::Value`s.
