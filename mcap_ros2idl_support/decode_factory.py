"""DecodeFactory integrating CDR decoding with the mcap reader."""

from __future__ import annotations

import logging
from typing import Callable, Optional

from mcap.decoder import DecoderFactory
from mcap.records import Schema

from mcap_ros2idl_support.ros2idl_parser import parse_ros2idl
from mcap_ros2idl_support.rosmsg import parse as parse_ros2msg
from mcap_ros2idl_support.rosmsg2_serialization import (
    MessageReader,
    MessageReaderOptions,
)

logger = logging.getLogger(__name__)


class Ros2DecodeFactory(DecoderFactory):
    """DecodeFactory for CDR-encoded ROS 2 messages.

    Instances of this factory can be supplied to
    :py:meth:`mcap.reader.make_reader` so that calls to
    :py:meth:`mcap.reader.McapReader.iter_decoded_messages` will return
    dictionaries representing ROS 2 messages.
    """

    def __init__(
        self, enum_as_string: bool = False, *, array_mode: str = "bytes"
    ) -> None:
        """Create a new :class:`Ros2DecodeFactory`.

        Args:
            enum_as_string: When ``True``, enumerated values are returned as
                their string representations instead of integers.
            array_mode: "bytes" returns uint8 arrays as bytes for speed.
                "list" preserves the original list representation.
        """

        if array_mode not in ("list", "bytes"):
            raise ValueError("array_mode must be 'list' or 'bytes'")
        self._array_mode = array_mode
        self._readers: dict[int, MessageReader] = {}
        self._unsupported_schema_ids: set[int] = set()
        self._enum_as_string = enum_as_string

    def _build_reader(self, schema: Schema) -> Optional[MessageReader]:
        try:
            if schema.encoding == "ros2idl":
                # Parsing can fail for some schemas, such as those
                # containing union types.
                parsed = parse_ros2idl(schema.data.decode("utf-8"))
            elif schema.encoding == "ros2msg":
                parsed = parse_ros2msg(schema.data.decode("utf-8"))
            else:
                logger.warning(
                    "Unknown schema encoding %r for schema ID %d",
                    schema.encoding,
                    schema.id,
                )
                return None
        except Exception:
            logger.warning(
                "Failed to parse %s schema for schema ID %d",
                schema.encoding,
                schema.id,
                exc_info=True,
            )
            return None

        options = MessageReaderOptions(
            enumAsString=self._enum_as_string,
            rootTypeName=schema.name,
            arrayMode=self._array_mode,
        )
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
