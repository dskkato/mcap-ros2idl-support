from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Sequence

from mcap_ros2idl_support.cdr import CdrReader
from mcap_ros2idl_support.message_definition import (
    AggregatedKind,
    MessageDefinition,
    MessageDefinitionField,
)
from mcap_ros2idl_support.rosmsg2_serialization.message_definition_has_data_fields import (  # noqa: E501
    message_definition_has_data_fields,
)

Ros2Time = Dict[str, int]
Ros1Time = Dict[str, int]

Deserializer = Callable[[CdrReader], Any]
ArrayDeserializer = Callable[[CdrReader, int], Any]


@dataclass
class MessageReaderOptions:
    timeType: str = "sec,nanosec"  # "sec,nanosec" or "sec,nsec"
    enumAsString: bool = False


class MessageReader:
    _root_definition: MessageDefinition
    _definitions: Mapping[str, MessageDefinition]
    _use_ros1_time: bool
    _enum_as_string: bool
    _enum_mappings: Dict[str, Dict[int, str]]
    _union_enum_mappings: Dict[str, Dict[int, str]]

    def __init__(
        self,
        definitions: Sequence[MessageDefinition],
        options: MessageReaderOptions | None = None,
    ) -> None:
        opts = options or MessageReaderOptions()
        time_type = opts.timeType
        self._enum_as_string = opts.enumAsString

        # ros2idl modules could have constant modules before the root struct used
        # to decode message
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
            raise ValueError("MessageReader initialized with no root MessageDefinition")
        self._root_definition = root_definition
        self._definitions = {d.name or "": d for d in definitions}
        self._use_ros1_time = time_type == "sec,nsec"

        # Build enum mappings
        enum_defns: Dict[str, Dict[int, str]] = {}
        for d in definitions:
            if _is_constant_module(d):
                mapping: Dict[int, str] = {}
                for f in d.definitions:
                    if isinstance(f.value, int):
                        mapping[f.value] = f.name
                if mapping:
                    enum_defns[d.name or ""] = mapping

        self._enum_mappings = enum_defns

        self._union_enum_mappings = {}
        for d in definitions:
            if d.aggregatedKind != AggregatedKind.UNION:
                continue
            case_values: set[int] = set()
            for c in d.cases:
                preds = c.predicates
                if preds:
                    case_values.update(preds)
            prefix = (d.name or "").rsplit("/", 1)[0]
            mapping = None
            for name, enum_map in enum_defns.items():
                if prefix and not name.startswith(prefix):
                    continue
                if case_values.issubset(enum_map.keys()):
                    mapping = enum_map
                    break
            if mapping is not None:
                self._union_enum_mappings[d.name or ""] = mapping

    def read_message(self, buffer: bytes | bytearray | memoryview) -> Any:
        reader = CdrReader(buffer)
        return self._read_complex_type(self._root_definition, reader)

    def _map_enum(self, value: Any, enum_type: str | None) -> Any:
        if not (self._enum_as_string and enum_type):
            return value
        enum_map = self._enum_mappings.get(enum_type)
        if enum_map is None:
            return value
        if isinstance(value, list):
            return [enum_map.get(v, v) for v in value]
        return enum_map.get(value, value)

    def _read_complex_type(
        self, definition: MessageDefinition, reader: CdrReader
    ) -> Dict[str, Any]:
        msg: Dict[str, Any] = {}
        fields = definition.definitions

        if (
            definition.aggregatedKind != AggregatedKind.UNION
            and not message_definition_has_data_fields(fields)
        ):
            # In case a message definition definition is empty, ROS 2 adds a
            # `uint8 structure_needs_at_least_one_member` field when converting to IDL,
            # to satisfy the requirement from IDL of not being empty.
            reader.uint8()
            return msg

        if definition.aggregatedKind == AggregatedKind.UNION:
            deser_map = _ros1_deserializers if self._use_ros1_time else _deserializers
            switch_deser = deser_map.get(definition.switchType or "")
            if switch_deser is None:
                raise ValueError(
                    "Unrecognized primitive type "
                    f"{definition.switchType} for union discriminant"
                )
            discr = switch_deser(reader)
            enum_map = self._union_enum_mappings.get(definition.name or "")
            if self._enum_as_string and enum_map:
                msg["discriminator"] = enum_map.get(discr, discr)
            else:
                msg["discriminator"] = discr

            field = _union_case_field(definition, discr)
            if field is None:
                raise ValueError(f"No union field matches discriminant {discr}")
            if field.isComplex is True:
                nested_definition = self._definitions.get(field.type)
                if nested_definition is None:
                    raise ValueError(f"Unrecognized complex type {field.type}")
                if field.isArray is True:
                    array_length = field.arrayLength or reader.sequence_length()
                    array = []
                    for _ in range(array_length):
                        array.append(self._read_complex_type(nested_definition, reader))
                    msg[field.name] = array
                else:
                    msg[field.name] = self._read_complex_type(nested_definition, reader)
            else:
                if field.isArray is True:
                    deser_map = (
                        _ros1_typed_array_deserializers
                        if self._use_ros1_time
                        else _typed_array_deserializers
                    )
                    deser = deser_map.get(field.type)
                    if deser is None:
                        raise ValueError(
                            f"Unrecognized primitive array type {field.type}[]"
                        )
                    array_length = field.arrayLength or reader.sequence_length()
                    value = deser(reader, array_length)
                    msg[field.name] = self._map_enum(value, field.enumType)
                else:
                    deser_map = (
                        _ros1_deserializers if self._use_ros1_time else _deserializers
                    )
                    deser = deser_map.get(field.type)
                    if deser is None:
                        raise ValueError(f"Unrecognized primitive type {field.type}")
                    value = deser(reader)
                    msg[field.name] = self._map_enum(value, field.enumType)
            return msg

        for field in fields:
            if field.isConstant is True:
                continue

            if field.isComplex is True:
                nested_definition = self._definitions.get(field.type)
                if nested_definition is None:
                    raise ValueError(f"Unrecognized complex type {field.type}")
                if field.isArray is True:
                    array_length = field.arrayLength or reader.sequence_length()
                    array = []
                    for _ in range(array_length):
                        array.append(self._read_complex_type(nested_definition, reader))
                    msg[field.name] = array
                else:
                    msg[field.name] = self._read_complex_type(nested_definition, reader)
            else:
                if field.isArray is True:
                    deser_map = (
                        _ros1_typed_array_deserializers
                        if self._use_ros1_time
                        else _typed_array_deserializers
                    )
                    deser = deser_map.get(field.type)
                    if deser is None:
                        raise ValueError(
                            f"Unrecognized primitive array type {field.type}[]"
                        )
                    array_length = field.arrayLength or reader.sequence_length()
                    value = deser(reader, array_length)
                    msg[field.name] = self._map_enum(value, field.enumType)
                else:
                    deser_map = (
                        _ros1_deserializers if self._use_ros1_time else _deserializers
                    )
                    deser = deser_map.get(field.type)
                    if deser is None:
                        raise ValueError(f"Unrecognized primitive type {field.type}")
                    value = deser(reader)
                    msg[field.name] = self._map_enum(value, field.enumType)

        return msg


def _is_constant_module(defn: MessageDefinition) -> bool:
    return len(defn.definitions) > 0 and all(f.isConstant for f in defn.definitions)


def _union_case_field(
    defn: MessageDefinition, discriminator: Any
) -> MessageDefinitionField | None:
    """Return the field for ``discriminator`` from ``defn``."""

    for case in defn.cases:
        if case.predicates and discriminator in case.predicates:
            return case.type

    return defn.defaultCase


def _read_bool_array(reader: CdrReader, count: int) -> List[bool]:
    return [bool(reader.int8()) for _ in range(count)]


def _read_string_array(reader: CdrReader, count: int) -> List[str]:
    return [reader.string() for _ in range(count)]


def _read_ros1_time_array(reader: CdrReader, count: int) -> List[Ros1Time]:
    array: List[Ros1Time] = []
    for _ in range(count):
        sec = reader.int32()
        nsec = reader.uint32()
        array.append({"sec": sec, "nsec": nsec})
    return array


def _read_time_array(reader: CdrReader, count: int) -> List[Ros2Time]:
    array: List[Ros2Time] = []
    for _ in range(count):
        sec = reader.int32()
        nanosec = reader.uint32()
        array.append({"sec": sec, "nanosec": nanosec})
    return array


def _throw_on_wstring(*_: Any) -> None:
    raise RuntimeError("wstring is implementation-defined and therefore not supported")


_deserializers: Dict[str, Deserializer] = {
    "bool": lambda r: bool(r.int8()),
    "int8": lambda r: r.int8(),
    "uint8": lambda r: r.uint8(),
    "int16": lambda r: r.int16(),
    "uint16": lambda r: r.uint16(),
    "int32": lambda r: r.int32(),
    "uint32": lambda r: r.uint32(),
    "int64": lambda r: r.int64(),
    "uint64": lambda r: r.uint64(),
    "float32": lambda r: r.float32(),
    "float64": lambda r: r.float64(),
    "string": lambda r: r.string(),
    "wstring": _throw_on_wstring,
    "time": lambda r: {"sec": r.int32(), "nanosec": r.uint32()},
    "duration": lambda r: {"sec": r.int32(), "nanosec": r.uint32()},
}

_ros1_deserializers: Dict[str, Deserializer] = {
    **_deserializers,
    "time": lambda r: {"sec": r.int32(), "nsec": r.uint32()},
    "duration": lambda r: {"sec": r.int32(), "nsec": r.uint32()},
}

_typed_array_deserializers: Dict[str, ArrayDeserializer] = {
    "bool": _read_bool_array,
    "int8": lambda r, c: r.int8_array(c).tolist(),
    "uint8": lambda r, c: r.uint8_array(c).tolist(),
    "int16": lambda r, c: r.int16_array(c).tolist(),
    "uint16": lambda r, c: r.uint16_array(c).tolist(),
    "int32": lambda r, c: r.int32_array(c).tolist(),
    "uint32": lambda r, c: r.uint32_array(c).tolist(),
    "int64": lambda r, c: r.int64_array(c).tolist(),
    "uint64": lambda r, c: r.uint64_array(c).tolist(),
    "float32": lambda r, c: r.float32_array(c).tolist(),
    "float64": lambda r, c: r.float64_array(c).tolist(),
    "string": _read_string_array,
    "wstring": _throw_on_wstring,
    "time": _read_time_array,
    "duration": _read_time_array,
}

_ros1_typed_array_deserializers: Dict[str, ArrayDeserializer] = {
    **_typed_array_deserializers,
    "time": _read_ros1_time_array,
    "duration": _read_ros1_time_array,
}

__all__ = ["MessageReader", "MessageReaderOptions"]
