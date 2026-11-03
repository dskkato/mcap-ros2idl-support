#!/usr/bin/env python3
"""Encode ROS 2 messages into MCAP using Ros2EncodeFactory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import time_ns
from typing import Any, Iterable, List

from mcap.writer import Writer

from mcap_ros2idl_support import Ros2EncodeFactory


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Encode JSON ROS 2 messages as CDR and store them in an MCAP file."
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output MCAP file path.",
    )
    parser.add_argument(
        "--topic",
        required=True,
        help="Topic name to record messages under.",
    )
    parser.add_argument(
        "--schema-file",
        required=True,
        help="Path to a ros2idl or ros2msg schema definition.",
    )
    parser.add_argument(
        "--schema-name",
        required=True,
        help="Schema name stored in the MCAP file.",
    )
    parser.add_argument(
        "--schema-encoding",
        choices=("ros2idl", "ros2msg"),
        default="ros2idl",
        help="Schema encoding, matching the contents of --schema-file.",
    )
    parser.add_argument(
        "--message-file",
        action="append",
        default=[],
        help="Path to a JSON file containing a message object or array of objects.",
    )
    parser.add_argument(
        "--message",
        action="append",
        default=[],
        help="Inline JSON message. Can be provided multiple times.",
    )
    parser.add_argument(
        "--message-encoding",
        default="cdr",
        help="Value recorded as Channel.message_encoding (default: cdr).",
    )
    parser.add_argument(
        "--log-time",
        type=int,
        default=None,
        help="Override log_time (nanoseconds). Defaults to current time per message.",
    )
    parser.add_argument(
        "--publish-time",
        type=int,
        default=None,
        help="Override publish_time (nanoseconds). Defaults to log_time per message.",
    )
    return parser.parse_args()


def _load_messages(paths: Iterable[str], literals: Iterable[str]) -> List[Any]:
    messages: List[Any] = []

    for literal in literals:
        messages.append(json.loads(literal))

    for path in paths:
        data = json.loads(Path(path).read_text())
        if isinstance(data, list):
            messages.extend(data)
        else:
            messages.append(data)

    return messages


def main() -> None:
    args = _parse_args()
    messages = _load_messages(args.message_file, args.message)
    if not messages:
        raise SystemExit("No messages provided. Use --message or --message-file.")

    schema_bytes = Path(args.schema_file).read_bytes()

    factory = Ros2EncodeFactory()
    writer = Writer(args.output)
    writer.start()

    schema_id = writer.register_schema(
        name=args.schema_name,
        encoding=args.schema_encoding,
        data=schema_bytes,
    )
    factory.register_schema(
        schema_id,
        encoding=args.schema_encoding,
        data=schema_bytes,
    )
    channel_id = writer.register_channel(
        topic=args.topic,
        message_encoding=args.message_encoding,
        schema_id=schema_id,
    )

    for message in messages:
        log_time = args.log_time if args.log_time is not None else time_ns()
        publish_time = args.publish_time if args.publish_time is not None else log_time
        payload = factory.encode(schema_id, message)
        writer.add_message(
            channel_id=channel_id,
            log_time=log_time,
            publish_time=publish_time,
            data=payload,
        )
    writer.finish()


if __name__ == "__main__":
    main()
