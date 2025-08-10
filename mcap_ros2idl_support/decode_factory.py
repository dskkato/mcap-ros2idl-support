"""DecodeFactory integrating CDR decoding with the mcap reader."""

from __future__ import annotations

from typing import Callable, Optional

from mcap.decoder import DecoderFactory
from mcap.records import Schema

from .cdr_reader import CdrReader
from .idl_loader import SchemaInfo


class CdrDecodeFactory(DecoderFactory):
    """DecodeFactory for CDR-encoded ROS 2 messages.

    Instances of this factory can be supplied to
    :py:meth:`mcap.reader.make_reader` so that calls to
    :py:meth:`mcap.reader.McapReader.iter_decoded_messages` will return
    dictionaries representing ROS 2 messages.
    """

    def __init__(self, schemas: dict[int, SchemaInfo]):
        self._readers: dict[int, CdrReader] = {
            schema_id: CdrReader(info.type_map, info.enum_map)
            for schema_id, info in schemas.items()
        }

    def decoder_for(
        self, message_encoding: str, schema: Optional[Schema]
    ) -> Optional[Callable[[bytes], object]]:
        if message_encoding != "cdr" or schema is None:
            return None
        reader = self._readers.get(schema.id)
        if reader is None:
            return None
        type_name = schema.name.replace("::", "/")

        def decode(data: bytes) -> object:
            return reader.read(type_name, data)

        return decode


def make_decoder_factory(mcap_file: str) -> CdrDecodeFactory:
    """Create a :class:`CdrDecodeFactory` from an MCAP file.

    This convenience function parses the schemas embedded in ``mcap_file``
    using the pure-Python IDL loader and returns a decode factory ready to be
    supplied to :py:meth:`mcap.reader.make_reader`.
    """
    from .idl_loader_py import load_idl as load_idl_py

    schemas = load_idl_py(mcap_file)
    return CdrDecodeFactory(schemas)
