"""DecodeFactory integrating CDR decoding with the mcap reader."""

from __future__ import annotations

from dataclasses import asdict
from typing import Callable, Optional

from mcap.decoder import DecoderFactory
from mcap.records import Schema
from ros2idl_parser import parse_ros2idl
from rosmsg import parse as parse_ros2msg

from .cdr_reader import CdrReader, MessageType


def ros2_type_name_from_schema_name(name: str) -> str:
    """Convert an MCAP schema name to a ROS 2 type name.

    MCAP schemas use C++ style ``::`` namespace separators, while ROS 2
    type names use ``/``. This helper performs the necessary transformation.
    """

    return name.replace("::", "/")


class Ros2DecodeFactory(DecoderFactory):
    """DecodeFactory for CDR-encoded ROS 2 messages.

    Instances of this factory can be supplied to
    :py:meth:`mcap.reader.make_reader` so that calls to
    :py:meth:`mcap.reader.McapReader.iter_decoded_messages` will return
    dictionaries representing ROS 2 messages.
    """

    def __init__(self) -> None:
        self._readers: dict[int, CdrReader] = {}

    def _build_reader(self, schema: Schema) -> Optional[CdrReader]:
        if schema.encoding == "ros2idl":
            try:
                parsed = parse_ros2idl(schema.data.decode("utf-8"))
            except ValueError as e:
                print(f"Error parsing ros2idl for schema ID {schema.id}: {e}")
                return None
        elif schema.encoding == "ros2msg":
            parsed = parse_ros2msg(schema.data.decode("utf-8"))
        else:
            print(
                f"Unknown schema encoding: {schema.encoding} for schema ID: {schema.id}"
            )
            return None

        type_map: dict[str, MessageType] = {}
        enum_map: dict[str, dict[int, str]] = {}
        for type_def in parsed:
            name = type_def.name or schema.name
            field_dicts = [asdict(f) for f in type_def.definitions]
            type_map[name] = MessageType(name, field_dicts)
            enum_candidates = [f for f in type_def.definitions if f.isConstant]
            if enum_candidates:
                enum_lookup = {f.value: f.name for f in enum_candidates}
                enum_map[name] = enum_lookup
        return CdrReader(type_map, enum_map)

    def decoder_for(
        self, message_encoding: str, schema: Optional[Schema]
    ) -> Optional[Callable[[bytes], object]]:
        if message_encoding != "cdr" or schema is None:
            return None
        reader = self._readers.get(schema.id)
        if reader is None:
            reader = self._build_reader(schema)
            if reader is None:
                return None
            self._readers[schema.id] = reader
        type_name = ros2_type_name_from_schema_name(schema.name)

        def decode(data: bytes) -> object:
            return reader.read(type_name, data)

        return decode
