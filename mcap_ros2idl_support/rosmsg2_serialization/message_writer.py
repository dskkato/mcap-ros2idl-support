from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Sequence

from mcap_ros2idl_support.cdr import CdrWriter
from mcap_ros2idl_support.message_definition import (
    AggregatedKind,
    DefaultValue,
    MessageDefinition,
    MessageDefinitionField,
)
from mcap_ros2idl_support.rosmsg2_serialization.message_definition_has_data_fields import (  # noqa: E501
    message_definition_has_data_fields,
)

PrimitiveWriter = Callable[[Any, DefaultValue, CdrWriter, int | None], None]
PrimitiveArrayWriter = Callable[[Any, DefaultValue, CdrWriter, int | None], None]

PRIMITIVE_SIZES: Dict[str, int] = {
    "bool": 1,
    "int8": 1,
    "uint8": 1,
    "int16": 2,
    "uint16": 2,
    "int32": 4,
    "uint32": 4,
    "int64": 8,
    "uint64": 8,
    "float32": 4,
    "float64": 8,
    # string handled separately
    "time": 8,
    "duration": 8,
}


class MessageWriter:
    _root_definition: MessageDefinition
    _definitions: Mapping[str, MessageDefinition]

    def __init__(self, definitions: Sequence[MessageDefinition]) -> None:
        root_definition = next(
            (
                d
                for d in definitions
                if d.aggregatedKind == AggregatedKind.STRUCT
                and not _is_constant_module(d)
            ),
            None,
        )
        if root_definition is None:
            root_definition = next(
                (d for d in definitions if not _is_constant_module(d)), None
            )
        if root_definition is None:
            raise ValueError(
                "MessageWriter initialized with no root MessageDefinition"
            )
        self._root_definition = root_definition
        self._definitions = {d.name or "": d for d in definitions}

        enum_name_to_value: Dict[str, Dict[str, int]] = {}
        enum_value_to_name: Dict[str, Dict[int, str]] = {}
        for d in definitions:
            if not _is_constant_module(d):
                continue
            name = d.name or ""
            name_map: Dict[str, int] = {}
            value_map: Dict[int, str] = {}
            for field in d.definitions:
                if isinstance(field.value, int):
                    value = int(field.value)
                    name_map[field.name] = value
                    value_map[value] = field.name
            if name_map:
                enum_name_to_value[name] = name_map
                enum_value_to_name[name] = value_map

        self._enum_name_to_value = enum_name_to_value
        self._union_enum_name_to_value: Dict[str, Dict[str, int]] = {}
        for d in definitions:
            if d.aggregatedKind != AggregatedKind.UNION:
                continue
            case_values: set[int] = set()
            for case in d.cases:
                preds = case.predicates or []
                case_values.update(int(p) for p in preds)
            prefix = (d.name or "").rsplit("/", 1)[0]
            mapping_name = None
            for enum_name, values in enum_value_to_name.items():
                if prefix and not enum_name.startswith(prefix):
                    continue
                if case_values.issubset(values.keys()):
                    mapping_name = enum_name
                    break
            if mapping_name is not None:
                self._union_enum_name_to_value[d.name or ""] = enum_name_to_value[
                    mapping_name
                ]

    def calculate_byte_size(self, message: Any) -> int:
        return self._byte_size_definition(self._root_definition, message, 4)

    def write_message(self, message: Any, output: bytearray | None = None) -> bytes:
        writer = CdrWriter(
            buffer=output,
            size=None if output is not None else self.calculate_byte_size(message),
        )
        self._write_definition(self._root_definition, message, writer)
        return writer.data

    def _byte_size_definition(
        self, definition: MessageDefinition, message: Any, offset: int
    ) -> int:
        if definition.aggregatedKind == AggregatedKind.UNION:
            return self._byte_size_union(definition, message, offset)
        if definition.aggregatedKind != AggregatedKind.STRUCT:
            raise ValueError(
                "Cannot serialize message definition of kind {}".format(
                    definition.aggregatedKind
                )
            )
        return self._byte_size_struct(definition, message, offset)

    def _byte_size_struct(
        self, definition: MessageDefinition, message: Any, offset: int
    ) -> int:
        message_obj = message if isinstance(message, dict) else {}
        new_offset = offset

        if not message_definition_has_data_fields(definition.definitions):
            return offset + self._get_primitive_size("uint8")

        for field in definition.definitions:
            if field.isConstant is True:
                continue
            nested_message = (
                message_obj.get(field.name) if isinstance(message_obj, dict) else None
            )
            new_offset = self._byte_size_field(field, nested_message, new_offset)
        return new_offset

    def _byte_size_union(
        self, definition: MessageDefinition, message: Any, offset: int
    ) -> int:
        message_obj = message if isinstance(message, dict) else {}
        switch_type = definition.switchType or ""
        discr = self._resolve_union_discriminator(definition, message_obj)
        discr = self._coerce_union_discriminator(discr, switch_type)
        entry_size = self._get_primitive_size(switch_type or "uint32")
        alignment = 4 if switch_type in {"time", "duration"} else entry_size
        new_offset = offset + _padding(offset, alignment) + entry_size
        field = _union_case_field(definition, discr)
        if field is None:
            raise ValueError(f"No union field matches discriminant {discr}")
        nested_message = message_obj.get(field.name)
        return self._byte_size_field(field, nested_message, new_offset)

    def _byte_size_field(
        self, field: MessageDefinitionField, nested_message: Any, offset: int
    ) -> int:
        new_offset = offset
        if field.isArray is True:
            array_length = field.arrayLength or _field_length(nested_message)
            data_is_array = isinstance(nested_message, (list, tuple))
            data_array = list(nested_message) if data_is_array else []
            if field.arrayLength is None:
                new_offset += _padding(new_offset, 4)
                new_offset += 4
            if field.isComplex is True:
                nested_definition = self._get_definition(field.type)
                for i in range(array_length):
                    entry = data_array[i] if i < len(data_array) else {}
                    new_offset = self._byte_size_definition(
                        nested_definition, entry, new_offset
                    )
            elif field.type == "string":
                for i in range(array_length):
                    entry = data_array[i] if i < len(data_array) else ""
                    new_offset += _padding(new_offset, 4)
                    new_offset += 4 + len(entry) + 1
            else:
                entry_size = self._get_primitive_size(field.type)
                alignment = 4 if field.type in {"time", "duration"} else entry_size
                new_offset += _padding(new_offset, alignment)
                new_offset += entry_size * array_length
            return new_offset
        if field.isComplex is True:
            nested_definition = self._get_definition(field.type)
            entry = nested_message if isinstance(nested_message, dict) else {}
            return self._byte_size_definition(nested_definition, entry, new_offset)
        if field.type == "string":
            entry = nested_message if isinstance(nested_message, str) else ""
            new_offset += _padding(new_offset, 4)
            new_offset += 4 + len(entry) + 1
            return new_offset
        entry_size = self._get_primitive_size(field.type)
        alignment = 4 if field.type in {"time", "duration"} else entry_size
        new_offset += _padding(new_offset, alignment)
        new_offset += entry_size
        return new_offset

    def _write_definition(
        self, definition: MessageDefinition, message: Any, writer: CdrWriter
    ) -> None:
        if definition.aggregatedKind == AggregatedKind.UNION:
            self._write_union(definition, message, writer)
            return
        if definition.aggregatedKind != AggregatedKind.STRUCT:
            raise ValueError(
                "Cannot serialize message definition of kind {}".format(
                    definition.aggregatedKind
                )
            )
        self._write_struct(definition, message, writer)

    def _write_struct(
        self, definition: MessageDefinition, message: Any, writer: CdrWriter
    ) -> None:
        message_obj = message if isinstance(message, dict) else {}

        if not message_definition_has_data_fields(definition.definitions):
            _uint8(0, 0, writer)
            return

        for field in definition.definitions:
            if field.isConstant is True:
                continue

            nested_message = (
                message_obj.get(field.name) if isinstance(message_obj, dict) else None
            )

            self._write_field(field, nested_message, writer)

    def _write_union(
        self, definition: MessageDefinition, message: Any, writer: CdrWriter
    ) -> None:
        message_obj = message if isinstance(message, dict) else {}
        discr = self._resolve_union_discriminator(definition, message_obj)
        switch_type = definition.switchType or ""
        discr = self._coerce_union_discriminator(discr, switch_type)
        switch_writer = self._get_primitive_writer(switch_type)
        switch_writer(discr, 0, writer, None)

        field = _union_case_field(definition, discr)
        if field is None:
            raise ValueError(f"No union field matches discriminant {discr}")
        nested_message = message_obj.get(field.name)
        self._write_field(field, nested_message, writer)

    def _write_field(
        self, field: MessageDefinitionField, nested_message: Any, writer: CdrWriter
    ) -> None:
        if field.isArray is True:
            array_length = field.arrayLength or _field_length(nested_message)
            data_is_array = isinstance(nested_message, (list, tuple))
            data_array = list(nested_message) if data_is_array else []
            if field.arrayLength is None:
                writer.sequenceLength(array_length)
            if field.arrayLength is not None and nested_message is not None:
                given_length = _field_length(nested_message)
                if given_length != field.arrayLength:
                    raise ValueError(
                        "Expected {exp} items for fixed-length array field {name} "
                        "but received {got}".format(
                            exp=field.arrayLength,
                            name=field.name,
                            got=given_length,
                        )
                    )
            if field.isComplex is True:
                nested_definition = self._get_definition(field.type)
                for i in range(array_length):
                    entry = data_array[i] if i < len(data_array) else {}
                    self._write_definition(nested_definition, entry, writer)
            else:
                write_value, write_default = self._resolve_enum_inputs(
                    nested_message, field.defaultValue, field.enumType
                )
                array_writer = self._get_primitive_array_writer(field.type)
                array_writer(write_value, write_default, writer, field.arrayLength)
            return
        if field.isComplex is True:
            nested_definition = self._get_definition(field.type)
            entry = nested_message if nested_message is not None else {}
            self._write_definition(nested_definition, entry, writer)
            return
        write_value, write_default = self._resolve_enum_inputs(
            nested_message, field.defaultValue, field.enumType
        )
        primitive_writer = self._get_primitive_writer(field.type)
        primitive_writer(write_value, write_default, writer, None)

    def _resolve_enum_inputs(
        self, value: Any, default: DefaultValue, enum_type: str | None
    ) -> tuple[Any, DefaultValue]:
        if enum_type is None:
            return value, default
        mapping = self._enum_name_to_value.get(enum_type)
        if mapping is None:
            return value, default
        return (
            self._convert_enum_value(value, mapping),
            self._convert_enum_value(default, mapping),
        )

    def _convert_enum_value(
        self, value: Any, mapping: Dict[str, int]
    ) -> Any:  # noqa: D401
        if value is None:
            return None
        if isinstance(value, str):
            if value not in mapping:
                raise ValueError(f"Unknown enumerator '{value}'")
            return mapping[value]
        if isinstance(value, Sequence) and not isinstance(
            value, (str, bytes, bytearray)
        ):
            return [self._convert_enum_value(entry, mapping) for entry in value]
        return value

    def _resolve_union_discriminator(
        self, definition: MessageDefinition, message_obj: Mapping[str, Any]
    ) -> Any:
        if "discriminator" not in message_obj:
            raise ValueError(
                f"Union {definition.name} requires a 'discriminator' entry"
            )
        discr = message_obj["discriminator"]
        if isinstance(discr, str):
            mapping = self._union_enum_name_to_value.get(definition.name or "")
            if mapping is None or discr not in mapping:
                raise ValueError(
                    f"Unknown union discriminator '{discr}' for {definition.name}"
                )
            return mapping[discr]
        return discr

    def _coerce_union_discriminator(self, value: Any, switch_type: str) -> Any:
        if switch_type in {
            "int8",
            "uint8",
            "int16",
            "uint16",
            "int32",
            "uint32",
            "int64",
            "uint64",
            "char",
            "byte",
        }:
            return int(value)
        if switch_type in {"float32", "float64"}:
            return float(value)
        if switch_type == "bool":
            return bool(value)
        return value

    def _get_definition(self, datatype: str) -> MessageDefinition:
        nested = self._definitions.get(datatype)
        if nested is None:
            raise ValueError(f"Unrecognized complex type {datatype}")
        return nested

    def _get_primitive_size(self, primitive_type: str) -> int:
        size = PRIMITIVE_SIZES.get(primitive_type)
        if size is None:
            if primitive_type == "wstring":
                _throw_on_wstring()
            raise ValueError(f"Unrecognized primitive type {primitive_type}")
        return size

    def _get_primitive_writer(self, primitive_type: str) -> PrimitiveWriter:
        writer = PRIMITIVE_WRITERS.get(primitive_type)
        if writer is None:
            raise ValueError(f"Unrecognized primitive type {primitive_type}")
        return writer

    def _get_primitive_array_writer(self, primitive_type: str) -> PrimitiveArrayWriter:
        writer = PRIMITIVE_ARRAY_WRITERS.get(primitive_type)
        if writer is None:
            raise ValueError(f"Unrecognized primitive type {primitive_type}[]")
        return writer


# Primitive writers


def _bool(
    value: Any, default: DefaultValue, writer: CdrWriter, _length: int | None = None
) -> None:
    bool_value = (
        value
        if isinstance(value, bool)
        else (default if isinstance(default, bool) else False)
    )
    writer.int8(1 if bool_value else 0)


def _int8(
    value: Any, default: DefaultValue, writer: CdrWriter, _length: int | None = None
) -> None:
    writer.int8(int(value if isinstance(value, (int, float)) else default or 0))


def _uint8(
    value: Any, default: DefaultValue, writer: CdrWriter, _length: int | None = None
) -> None:
    writer.uint8(int(value if isinstance(value, (int, float)) else default or 0))


def _int16(
    value: Any, default: DefaultValue, writer: CdrWriter, _length: int | None = None
) -> None:
    writer.int16(int(value if isinstance(value, (int, float)) else default or 0))


def _uint16(
    value: Any, default: DefaultValue, writer: CdrWriter, _length: int | None = None
) -> None:
    writer.uint16(int(value if isinstance(value, (int, float)) else default or 0))


def _int32(
    value: Any, default: DefaultValue, writer: CdrWriter, _length: int | None = None
) -> None:
    writer.int32(int(value if isinstance(value, (int, float)) else default or 0))


def _uint32(
    value: Any, default: DefaultValue, writer: CdrWriter, _length: int | None = None
) -> None:
    writer.uint32(int(value if isinstance(value, (int, float)) else default or 0))


def _int64(
    value: Any, default: DefaultValue, writer: CdrWriter, _length: int | None = None
) -> None:
    if isinstance(value, int):
        writer.int64(value)
    elif isinstance(value, float):
        writer.int64(int(value))
    else:
        writer.int64(int(default or 0))


def _uint64(
    value: Any, default: DefaultValue, writer: CdrWriter, _length: int | None = None
) -> None:
    if isinstance(value, int):
        writer.uint64(value)
    elif isinstance(value, float):
        writer.uint64(int(value))
    else:
        writer.uint64(int(default or 0))


def _float32(
    value: Any, default: DefaultValue, writer: CdrWriter, _length: int | None = None
) -> None:
    writer.float32(float(value if isinstance(value, (int, float)) else default or 0.0))


def _float64(
    value: Any, default: DefaultValue, writer: CdrWriter, _length: int | None = None
) -> None:
    writer.float64(float(value if isinstance(value, (int, float)) else default or 0.0))


def _string(
    value: Any, default: DefaultValue, writer: CdrWriter, _length: int | None = None
) -> None:
    writer.string(str(value if isinstance(value, str) else default or ""))


def _time(
    value: Any, _default: DefaultValue, writer: CdrWriter, _length: int | None = None
) -> None:
    if value is None:
        writer.int32(0)
        writer.uint32(0)
        return
    sec = value.get("sec", 0) if isinstance(value, dict) else 0
    nsec = value.get("nsec") if isinstance(value, dict) else None
    nanosec = value.get("nanosec") if isinstance(value, dict) else None
    writer.int32(int(sec))
    writer.uint32(int(nsec if nsec is not None else nanosec or 0))


def _throw_on_wstring(*_: Any) -> None:
    raise RuntimeError("wstring is implementation-defined and therefore not supported")


def _bool_array(
    value: Any, default: DefaultValue, writer: CdrWriter, array_length: int | None
) -> None:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        writer.int8Array([1 if bool(v) else 0 for v in value])
    else:
        arr = [1 if bool(v) else 0 for v in (default or [False] * (array_length or 0))]
        writer.int8Array(arr)


def _int8_array(
    value: Any, default: DefaultValue, writer: CdrWriter, array_length: int | None
) -> None:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        writer.int8Array([int(v) for v in value])
    else:
        arr = [int(v) for v in (default or [0] * (array_length or 0))]
        writer.int8Array(arr)


def _uint8_array(
    value: Any, default: DefaultValue, writer: CdrWriter, array_length: int | None
) -> None:
    if isinstance(value, (bytes, bytearray)):
        writer.uint8Array(value)
    elif isinstance(value, Sequence) and not isinstance(value, str):
        writer.uint8Array([int(v) for v in value])
    else:
        arr = [int(v) for v in (default or [0] * (array_length or 0))]
        writer.uint8Array(arr)


def _int16_array(
    value: Any, default: DefaultValue, writer: CdrWriter, array_length: int | None
) -> None:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        writer.int16Array([int(v) for v in value])
    else:
        arr = [int(v) for v in (default or [0] * (array_length or 0))]
        writer.int16Array(arr)


def _uint16_array(
    value: Any, default: DefaultValue, writer: CdrWriter, array_length: int | None
) -> None:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        writer.uint16Array([int(v) for v in value])
    else:
        arr = [int(v) for v in (default or [0] * (array_length or 0))]
        writer.uint16Array(arr)


def _int32_array(
    value: Any, default: DefaultValue, writer: CdrWriter, array_length: int | None
) -> None:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        writer.int32Array([int(v) for v in value])
    else:
        arr = [int(v) for v in (default or [0] * (array_length or 0))]
        writer.int32Array(arr)


def _uint32_array(
    value: Any, default: DefaultValue, writer: CdrWriter, array_length: int | None
) -> None:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        writer.uint32Array([int(v) for v in value])
    else:
        arr = [int(v) for v in (default or [0] * (array_length or 0))]
        writer.uint32Array(arr)


def _int64_array(
    value: Any, default: DefaultValue, writer: CdrWriter, array_length: int | None
) -> None:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        writer.int64Array([int(v) for v in value])
    else:
        arr = [int(v) for v in (default or [0] * (array_length or 0))]
        writer.int64Array(arr)


def _uint64_array(
    value: Any, default: DefaultValue, writer: CdrWriter, array_length: int | None
) -> None:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        writer.uint64Array([int(v) for v in value])
    else:
        arr = [int(v) for v in (default or [0] * (array_length or 0))]
        writer.uint64Array(arr)


def _float32_array(
    value: Any, default: DefaultValue, writer: CdrWriter, array_length: int | None
) -> None:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        writer.float32Array([float(v) for v in value])
    else:
        arr = [float(v) for v in (default or [0.0] * (array_length or 0))]
        writer.float32Array(arr)


def _float64_array(
    value: Any, default: DefaultValue, writer: CdrWriter, array_length: int | None
) -> None:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        writer.float64Array([float(v) for v in value])
    else:
        arr = [float(v) for v in (default or [0.0] * (array_length or 0))]
        writer.float64Array(arr)


def _string_array(
    value: Any, default: DefaultValue, writer: CdrWriter, array_length: int | None
) -> None:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            writer.string(str(item))
    else:
        arr = list(default or [""] * (array_length or 0))
        for item in arr:
            writer.string(str(item))


def _time_array(
    value: Any, _default: DefaultValue, writer: CdrWriter, array_length: int | None
) -> None:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            _time(item, None, writer)
    else:
        arr = [None] * (array_length or 0)
        for item in arr:
            _time(item, None, writer)


PRIMITIVE_WRITERS: Dict[str, PrimitiveWriter] = {
    "bool": _bool,
    "int8": _int8,
    "uint8": _uint8,
    "int16": _int16,
    "uint16": _uint16,
    "int32": _int32,
    "uint32": _uint32,
    "int64": _int64,
    "uint64": _uint64,
    "float32": _float32,
    "float64": _float64,
    "string": _string,
    "time": _time,
    "duration": _time,
    "wstring": _throw_on_wstring,
}

PRIMITIVE_ARRAY_WRITERS: Dict[str, PrimitiveArrayWriter] = {
    "bool": _bool_array,
    "int8": _int8_array,
    "uint8": _uint8_array,
    "int16": _int16_array,
    "uint16": _uint16_array,
    "int32": _int32_array,
    "uint32": _uint32_array,
    "int64": _int64_array,
    "uint64": _uint64_array,
    "float32": _float32_array,
    "float64": _float64_array,
    "string": _string_array,
    "time": _time_array,
    "duration": _time_array,
    "wstring": _throw_on_wstring,
}


def _field_length(value: Any) -> int:
    length = getattr(value, "__len__", None)
    return (
        int(length())
        if callable(length)
        else (len(value) if isinstance(value, Sequence) else 0)
    )


def _padding(offset: int, byte_width: int) -> int:
    alignment = (offset - 4) % byte_width
    return byte_width - alignment if alignment > 0 else 0


def _is_constant_module(defn: MessageDefinition) -> bool:
    return len(defn.definitions) > 0 and all(f.isConstant for f in defn.definitions)


def _union_case_field(
    defn: MessageDefinition, discriminator: Any
) -> MessageDefinitionField | None:
    for case in defn.cases:
        if case.predicates and discriminator in case.predicates:
            return case.type
    return defn.defaultCase


__all__ = ["MessageWriter"]
