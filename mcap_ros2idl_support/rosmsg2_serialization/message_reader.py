"""Compile schema metadata once and decode CDR payloads in Rust."""

from dataclasses import dataclass
from typing import Any, Sequence

from mcap_ros2idl_support._native import Decoder
from mcap_ros2idl_support.message_definition import AggregatedKind, MessageDefinition

from ._python_reader import MessageReader as PythonMessageReader
from ._python_reader import MessageReaderOptions as PythonMessageReaderOptions


@dataclass
class MessageReaderOptions(PythonMessageReaderOptions):
    arrayMode: str = "list"


class MessageReader(PythonMessageReader):
    def __init__(
        self,
        definitions: Sequence[MessageDefinition],
        options: MessageReaderOptions | None = None,
    ) -> None:
        options = options or MessageReaderOptions()
        if options.arrayMode not in ("list", "bytes"):
            raise ValueError("arrayMode must be 'list' or 'bytes'")
        super().__init__(definitions, options)
        definitions = list(self._definitions.values())
        indices = {d.name or "": i for i, d in enumerate(definitions)}

        def field_plan(field):
            kind = "complex" if field.isComplex else field.type
            if field.isComplex and field.type not in indices:
                raise ValueError(f"Unrecognized complex type {field.type}")
            target = indices[field.type] if field.isComplex else 0
            count = (
                (field.arrayLength if field.arrayLength is not None else -2)
                if field.isArray
                else -1
            )
            mapping = (
                self._enum_mappings.get(field.enumType, {})
                if self._enum_as_string
                else {}
            )
            return (field.name, kind, target, count, mapping)

        plans = []
        for definition in definitions:
            fields = [field_plan(f) for f in definition.definitions if not f.isConstant]
            cases = [
                (list(map(int, c.predicates)), field_plan(c.type))
                for c in definition.cases
            ]
            default = (
                field_plan(definition.defaultCase) if definition.defaultCase else None
            )
            mapping = (
                self._union_enum_mappings.get(definition.name or "", {})
                if self._enum_as_string
                else {}
            )
            plans.append(
                (
                    definition.aggregatedKind == AggregatedKind.UNION,
                    definition.switchType or "",
                    fields,
                    cases,
                    default,
                    mapping,
                )
            )
        self._native = Decoder(
            plans,
            indices[self._root_definition.name or ""],
            self._use_ros1_time,
            options.arrayMode == "bytes",
        )

    def read_message(self, buffer: bytes | bytearray | memoryview) -> Any:
        if not isinstance(buffer, bytes):
            buffer = bytes(buffer)
        return self._native.read_message(buffer)


__all__ = ["MessageReader", "MessageReaderOptions"]
