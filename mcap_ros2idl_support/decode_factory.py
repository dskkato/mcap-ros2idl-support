"""DecodeFactory integrating CDR decoding with the mcap reader."""

from __future__ import annotations

from typing import Callable, Optional

from mcap.decoder import DecoderFactory
from mcap.records import Schema

from mcap_ros2idl_support.ros2idl_parser import parse_ros2idl
from mcap_ros2idl_support.rosmsg import parse as parse_ros2msg
from mcap_ros2idl_support.rosmsg2_serialization import (
    MessageReader,
    MessageReaderOptions,
)


class Ros2DecodeFactory(DecoderFactory):
    """DecodeFactory for CDR-encoded ROS 2 messages.

    Instances of this factory can be supplied to
    :py:meth:`mcap.reader.make_reader` so that calls to
    :py:meth:`mcap.reader.McapReader.iter_decoded_messages` will return
    dictionaries representing ROS 2 messages.
    """

    def __init__(self, enum_as_string: bool = False) -> None:
        """Create a new :class:`Ros2DecodeFactory`.

        Args:
            enum_as_string: When ``True``, enumerated values are returned as
                their string representations instead of integers.
        """

        self._readers: dict[int, MessageReader] = {}
        self._unsupported_schema_ids: set[int] = set()
        self._enum_as_string = enum_as_string

    def _build_reader(self, schema: Schema) -> Optional[MessageReader]:
        if schema.encoding == "ros2idl":
            try:
                parsed = parse_ros2idl(schema.data.decode("utf-8"))
            except AttributeError as e:
                # When the schema contains union types, the parsing may fail
                print(f"Error parsing ros2idl for schema ID {schema.id}: {e}")
                return None
        elif schema.encoding == "ros2msg":
            parsed = parse_ros2msg(schema.data.decode("utf-8"))
        else:
            print(
                f"Unknown schema encoding: {schema.encoding} for schema ID: {schema.id}"
            )
            return None

        options = MessageReaderOptions(enumAsString=self._enum_as_string)
        return MessageReader(parsed, options)

    def decoder_for(
        self, message_encoding: str, schema: Optional[Schema]
    ) -> Optional[Callable[[bytes], object]]:
        if message_encoding != "cdr" or schema is None:
            return None

        if schema.id in self._unsupported_schema_ids:
            return None

        reader = self._readers.get(schema.id)
        if reader is None:
            reader = self._build_reader(schema)
            if reader is None:
                self._unsupported_schema_ids.add(schema.id)
                return None
            self._readers[schema.id] = reader

        def decode(data: bytes) -> object:
            return reader.read_message(data)

        return decode
