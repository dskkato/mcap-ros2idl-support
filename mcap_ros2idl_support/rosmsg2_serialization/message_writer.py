from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, Sequence

from mcap_ros2idl_support.cdr import CdrWriter
from mcap_ros2idl_support.message_definition import (
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
    _root_definition: List[MessageDefinitionField]
    _definitions: Mapping[str, List[MessageDefinitionField]]

    def __init__(self, definitions: Sequence[MessageDefinition]) -> None:
        root_definition = next(
            (d for d in definitions if not _is_constant_module(d)), None
        )
        if root_definition is None:
            raise ValueError("MessageReader initialized with no root MessageDefinition")
        self._root_definition = list(root_definition.definitions)
        self._definitions = {d.name or "": list(d.definitions) for d in definitions}

    def calculate_byte_size(self, message: Any) -> int:
        return self._byte_size(self._root_definition, message, 4)

    def write_message(self, message: Any, output: bytearray | None = None) -> bytes:
        writer = CdrWriter(
            buffer=output,
            size=None if output is not None else self.calculate_byte_size(message),
        )
        self._write(self._root_definition, message, writer)
        return writer.data

    def _byte_size(
        self, definition: Sequence[MessageDefinitionField], message: Any, offset: int
    ) -> int:
        message_obj = message if isinstance(message, dict) else {}
        new_offset = offset

        if not message_definition_has_data_fields(definition):
            return offset + self._get_primitive_size("uint8")

        for field in definition:
            if field.isConstant is True:
                continue
            nested_message = (
                message_obj.get(field.name) if isinstance(message_obj, dict) else None
            )
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
                        new_offset = self._byte_size(
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
            else:
                if field.isComplex is True:
                    nested_definition = self._get_definition(field.type)
                    entry = nested_message if isinstance(nested_message, dict) else {}
                    new_offset = self._byte_size(nested_definition, entry, new_offset)
                elif field.type == "string":
                    entry = nested_message if isinstance(nested_message, str) else ""
                    new_offset += _padding(new_offset, 4)
                    new_offset += 4 + len(entry) + 1
                else:
                    entry_size = self._get_primitive_size(field.type)
                    alignment = 4 if field.type in {"time", "duration"} else entry_size
                    new_offset += _padding(new_offset, alignment)
                    new_offset += entry_size
        return new_offset

    def _write(
        self,
        definition: Sequence[MessageDefinitionField],
        message: Any,
        writer: CdrWriter,
    ) -> None:
        message_obj = message if isinstance(message, dict) else {}

        if not message_definition_has_data_fields(definition):
            _uint8(0, 0, writer)
            return

        for field in definition:
            if field.isConstant is True:
                continue

            nested_message = (
                message_obj.get(field.name) if isinstance(message_obj, dict) else None
            )

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
                        self._write(nested_definition, entry, writer)
                else:
                    array_writer = self._get_primitive_array_writer(field.type)
                    array_writer(
                        nested_message, field.defaultValue, writer, field.arrayLength
                    )
            else:
                if field.isComplex is True:
                    nested_definition = self._get_definition(field.type)
                    entry = nested_message if nested_message is not None else {}
                    self._write(nested_definition, entry, writer)
                else:
                    primitive_writer = self._get_primitive_writer(field.type)
                    primitive_writer(nested_message, field.defaultValue, writer, None)

    def _get_definition(self, datatype: str) -> List[MessageDefinitionField]:
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


__all__ = ["MessageWriter"]
