#!/usr/bin/env python3
"""Generate an MCAP file containing a std_msgs/msg/String message.

The schema encoding can be either ROS 2 .msg or IDL depending on the
selected ``--encoding`` option.
"""

from __future__ import annotations

import argparse
import struct

from mcap.writer import Writer

ROS2MSG_DEF = "string data\n"
ROS2IDL_DEF = (
    "module std_msgs {\n"
    "  module msg {\n"
    "    struct String {\n"
    "      string data;\n"
    "    };\n"
    "  };\n"
    "};\n"
)


def encode_string(message: str) -> bytes:
    """Encode a ``std_msgs/msg/String`` message as CDR."""
    data = message.encode("utf-8")
    length = len(data) + 1  # include null terminator
    return b"\x00\x00\x00\x00" + struct.pack("<I", length) + data + b"\x00"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--encoding", choices=["ros2msg", "ros2idl"], required=True)
    parser.add_argument("--output", required=True, help="Path to output MCAP file")
    parser.add_argument(
        "--data", default="hello", help="String data to encode in the message"
    )
    args = parser.parse_args()

    if args.encoding == "ros2msg":
        schema_data = ROS2MSG_DEF
    else:
        schema_data = ROS2IDL_DEF

    with open(args.output, "wb") as f:
        writer = Writer(f)
        writer.start(profile="", library="mcap-generator")
        schema_id = writer.register_schema(
            name="std_msgs/msg/String",
            encoding=args.encoding,
            data=schema_data.encode("utf-8"),
        )
        channel_id = writer.register_channel(
            schema_id=schema_id,
            topic="std_msgs/msg/String",
            message_encoding="cdr",
            metadata={},
        )
        writer.add_message(
            channel_id=channel_id,
            log_time=0,
            publish_time=0,
            sequence=0,
            data=encode_string(args.data),
        )
        writer.finish()


if __name__ == "__main__":
    main()
