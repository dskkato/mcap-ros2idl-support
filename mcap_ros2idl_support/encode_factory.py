"""Factory for building CDR encoders from ROS 2 schemas."""

from __future__ import annotations

from typing import Any, Callable, Dict, Tuple

from mcap.records import Schema

from mcap_ros2idl_support.ros2idl_parser import parse_ros2idl
from mcap_ros2idl_support.rosmsg import parse as parse_ros2msg
from mcap_ros2idl_support.rosmsg2_serialization import MessageWriter


class Ros2EncodeFactory:
    """Create :class:`MessageWriter` instances for ROS 2 schemas.

    This mirrors :class:`Ros2DecodeFactory` but works in the opposite
    direction: it parses ros2idl/ros2msg schemas and provides helpers to
    encode Python dictionaries into CDR byte strings ready to hand to
    :class:`mcap.writer.Writer.add_message`.
    """

    def __init__(self) -> None:
        self._writers_by_schema_id: Dict[int, MessageWriter] = {}
        self._writers_by_blob: Dict[Tuple[str, bytes], MessageWriter] = {}

    # ------------------------------------------------------------------
    # Schema registration helpers
    # ------------------------------------------------------------------
    def register_schema(self, schema_id: int, *, encoding: str, data: bytes | str) -> None:
        """Register ``schema_id`` for subsequent :meth:`encode` calls."""

        self._writers_by_schema_id[schema_id] = self._writer_from_blob(encoding, data)

    # ------------------------------------------------------------------
    # Encoding APIs using registered schemas
    # ------------------------------------------------------------------
    def encode(self, schema_id: int, message: Any) -> bytes:
        """Encode ``message`` using a schema registered via :meth:`register_schema`."""

        writer = self._writers_by_schema_id.get(schema_id)
        if writer is None:
            raise KeyError(f"Schema ID {schema_id} has not been registered")
        return writer.write_message(message)

    def calculate_size(self, schema_id: int, message: Any) -> int:
        """Return the serialized size of ``message`` for ``schema_id``."""

        writer = self._writers_by_schema_id.get(schema_id)
        if writer is None:
            raise KeyError(f"Schema ID {schema_id} has not been registered")
        return writer.calculate_byte_size(message)

    # ------------------------------------------------------------------
    # APIs that accept :class:`mcap.records.Schema` directly
    # ------------------------------------------------------------------
    def writer_for_schema(self, schema: Schema) -> MessageWriter:
        """Return a :class:`MessageWriter` for ``schema``."""

        writer = self._writers_by_schema_id.get(schema.id)
        if writer is not None:
            return writer
        writer = self._writer_from_blob(schema.encoding, schema.data)
        self._writers_by_schema_id[schema.id] = writer
        return writer

    def encoder_for_schema(self, schema: Schema) -> Callable[[Any], bytes]:
        """Return a callable that encodes messages for ``schema``."""

        writer = self.writer_for_schema(schema)

        def encode(message: Any) -> bytes:
            return writer.write_message(message)

        return encode

    def encode_with_schema(self, schema: Schema, message: Any) -> bytes:
        """Encode ``message`` directly from ``schema``."""

        return self.writer_for_schema(schema).write_message(message)

    def calculate_size_with_schema(self, schema: Schema, message: Any) -> int:
        """Return the serialized size of ``message`` using ``schema``."""

        return self.writer_for_schema(schema).calculate_byte_size(message)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _writer_from_blob(self, encoding: str, data: bytes | bytearray | str) -> MessageWriter:
        schema_bytes = self._ensure_bytes(data)
        key = (encoding, schema_bytes)
        writer = self._writers_by_blob.get(key)
        if writer is None:
            writer = self._build_writer(encoding, schema_bytes)
            self._writers_by_blob[key] = writer
        return writer

    def _build_writer(self, encoding: str, data: bytes) -> MessageWriter:
        schema_text = data.decode("utf-8")
        if encoding == "ros2idl":
            definitions = parse_ros2idl(schema_text)
        elif encoding == "ros2msg":
            definitions = parse_ros2msg(schema_text)
        else:
            raise ValueError(f"Unknown schema encoding: {encoding}")
        return MessageWriter(definitions)

    @staticmethod
    def _ensure_bytes(data: bytes | bytearray | str) -> bytes:
        if isinstance(data, bytes):
            return data
        if isinstance(data, bytearray):
            return bytes(data)
        return data.encode("utf-8")


__all__ = ["Ros2EncodeFactory"]
