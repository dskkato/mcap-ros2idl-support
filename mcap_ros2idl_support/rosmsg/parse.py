from __future__ import annotations

import re
from typing import List, Optional

from mcap_ros2idl_support.message_definition import (
    MessageDefinition,
    MessageDefinitionField,
    is_msg_def_equal,
)

BUILTIN_TYPES = {
    "int8",
    "uint8",
    "int16",
    "uint16",
    "int32",
    "uint32",
    "int64",
    "uint64",
    "float32",
    "float64",
    "string",
    "bool",
    "char",
    "byte",
    "time",
    "duration",
}


ROS2_BUILTIN_TYPES = {
    "bool",
    "byte",
    "char",
    "float32",
    "float64",
    "int8",
    "uint8",
    "int16",
    "uint16",
    "int32",
    "uint32",
    "int64",
    "uint64",
    "string",
    "wstring",
    "time",
    "duration",
    "builtin_interfaces/Time",
    "builtin_interfaces/Duration",
    "builtin_interfaces/msg/Time",
    "builtin_interfaces/msg/Duration",
}

TYPE = r"(?P<type>[a-zA-Z0-9_/]+)"
STRING_BOUND = r"(?:<=(?P<stringBound>\d+))"
ARRAY_BOUND = (
    r"(?:(?P<unboundedArray>\[\])|\[(?P<arrayLength>\d+)\]|\[<=(?P<arrayBound>\d+)\])"
)
NAME = r"(?P<name>[a-zA-Z0-9_]+)"
QUOTED_STRING = r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\""
COMMENT_TERMINATED_LITERAL = (
    r"(?:" + QUOTED_STRING + r"|(?:\\.|[^\s'\"#\\])(?:\\.|[^#\\])*)"
)
ARRAY_TERMINATED_LITERAL = (
    r"(?:" + QUOTED_STRING + r"|(?:\\.|[^\s'\"\],#\\])(?:\\.|[^\],#\\])*)"
)
CONSTANT_ASSIGNMENT = r"\s*=\s*(?P<constantValue>" + COMMENT_TERMINATED_LITERAL + r"?)"
DEFAULT_VALUE_ARRAY = (
    r"\[(?:" + ARRAY_TERMINATED_LITERAL + r",)*" + ARRAY_TERMINATED_LITERAL + r"?\]"
)
DEFAULT_VALUE = (
    r"(?P<defaultValue>"
    + DEFAULT_VALUE_ARRAY
    + r"|"
    + COMMENT_TERMINATED_LITERAL
    + r")"
)
COMMENT = r"(?:#.*)"
DEFINITION_LINE_REGEX = re.compile(
    r"^"
    + TYPE
    + STRING_BOUND
    + r"?"
    + ARRAY_BOUND
    + r"?\s+"
    + NAME
    + r"(?:"
    + CONSTANT_ASSIGNMENT
    + r"|\s+"
    + DEFAULT_VALUE
    + r")?\s*"
    + COMMENT
    + r"?$"
)

STRING_ESCAPES = (
    r"\\(?P<char>['\"abfnrtv\\])|\\(?P<oct>[0-7]{1,3})|"
    r"\\x(?P<hex2>[a-fA-F0-9]{2})|\\u(?P<hex4>[a-fA-F0-9]{4})|"
    r"\\U(?P<hex8>[a-fA-F0-9]{8})"
)

LITERAL_REGEX = re.compile(ARRAY_TERMINATED_LITERAL)
COMMA_OR_END_REGEX = re.compile(r"\s*(,)?\s*|\s*$")


def _parse_big_int_literal(text: str, min_value: int, max_value: int) -> int:
    value = int(text)
    if value < min_value or value > max_value:
        raise ValueError(f"Number {text} out of range [{min_value}, {max_value}]")
    return value


def _parse_number_literal(text: str, min_value: int, max_value: int) -> int:
    try:
        value = int(text)
    except ValueError:
        raise ValueError(f"Invalid numeric literal: {text}")
    if value < min_value or value > max_value:
        raise ValueError(f"Number {text} out of range [{min_value}, {max_value}]")
    return value


def _parse_string_literal(maybe_quoted: str) -> str:
    quote = ""
    s = maybe_quoted
    for q in ("'", '"'):
        if s.startswith(q):
            if not s.endswith(q):
                raise ValueError(
                    f"Expected terminating {q} in string literal: {maybe_quoted}"
                )
            quote = q
            s = s[len(q) : -len(q)]
            break
    pattern = rf"^(?:[^\\{quote}]|{STRING_ESCAPES})*$"
    if re.fullmatch(pattern, s) is None:
        raise ValueError(f"Invalid string literal: {s}")

    def replace(match: re.Match) -> str:
        groups = match.groupdict()
        if groups.get("char"):
            return {
                "'": "'",
                '"': '"',
                "a": "\x07",
                "b": "\b",
                "f": "\f",
                "n": "\n",
                "r": "\r",
                "t": "\t",
                "v": "\v",
                "\\": "\\",
            }[groups["char"]]
        if groups.get("oct"):
            return chr(int(groups["oct"], 8))
        hex_val = groups.get("hex2") or groups.get("hex4") or groups.get("hex8")
        if hex_val:
            return chr(int(hex_val, 16))
        raise ValueError("Expected exactly one matched group")

    return re.sub(STRING_ESCAPES, replace, s)


def _parse_primitive_literal(type_name: str, text: str):
    if type_name == "bool":
        if text in {"true", "True", "1"}:
            return True
        if text in {"false", "False", "0"}:
            return False
    elif type_name in {"float32", "float64"}:
        value = float(text)
        if value == value:  # not NaN
            return value
    elif type_name == "int8":
        return _parse_number_literal(text, -0x80, 0x7F)
    elif type_name == "uint8":
        return _parse_number_literal(text, 0, 0xFF)
    elif type_name == "int16":
        return _parse_number_literal(text, -0x8000, 0x7FFF)
    elif type_name == "uint16":
        return _parse_number_literal(text, 0, 0xFFFF)
    elif type_name == "int32":
        return _parse_number_literal(text, -0x80000000, 0x7FFFFFFF)
    elif type_name == "uint32":
        return _parse_number_literal(text, 0, 0xFFFFFFFF)
    elif type_name == "int64":
        return _parse_big_int_literal(text, -0x8000000000000000, 0x7FFFFFFFFFFFFFFF)
    elif type_name == "uint64":
        return _parse_big_int_literal(text, 0, 0xFFFFFFFFFFFFFFFF)
    elif type_name in {"string", "wstring"}:
        return _parse_string_literal(text)
    raise ValueError(f"Invalid literal of type {type_name}: {text}")


def _parse_array_literal(type_name: str, raw: str):
    if not raw.startswith("[") or not raw.endswith("]"):
        raise ValueError("Array must start with [ and end with ]")
    inner = raw[1:-1]
    if type_name in {"string", "wstring"}:
        results = []
        offset = 0
        while offset < len(inner):
            if inner[offset] == ",":
                raise ValueError("Expected array element before comma")
            m = LITERAL_REGEX.match(inner, offset)
            if m:
                results.append(_parse_string_literal(m.group(0)))
                offset = m.end()
            m = COMMA_OR_END_REGEX.match(inner, offset)
            if not m:
                raise ValueError("Expected comma or end of array")
            if not m.group(1):
                break
            offset = m.end()
        return results
    return [
        _parse_primitive_literal(type_name, part.strip())
        for part in inner.split(",")
        if part.strip() != ""
    ]


def _normalize_type_ros2(type_name: str) -> str:
    if type_name in {"char", "byte"}:
        return "uint8"
    if type_name in {"builtin_interfaces/Time", "builtin_interfaces/msg/Time"}:
        return "time"
    if type_name in {"builtin_interfaces/Duration", "builtin_interfaces/msg/Duration"}:
        return "duration"
    return type_name


def _build_ros2_type(lines: List[str]) -> MessageDefinition:
    definitions: List[MessageDefinitionField] = []
    complex_type_name: Optional[str] = None
    for line in lines:
        if line.startswith("#"):
            continue
        m_msg = re.match(r"^MSG: ([^ ]+)\s*(?:#.+)?$", line)
        if m_msg:
            complex_type_name = m_msg.group(1)
            continue
        m = DEFINITION_LINE_REGEX.match(line)
        if not m:
            raise ValueError(f"Could not parse line: '{line}'")
        groups = m.groupdict()
        raw_type = groups["type"]
        type_name = _normalize_type_ros2(raw_type)
        string_bound = groups.get("stringBound")
        unbounded_array = groups.get("unboundedArray")
        array_length = groups.get("arrayLength")
        array_bound = groups.get("arrayBound")
        name = groups["name"]
        constant_value = groups.get("constantValue")
        default_value = groups.get("defaultValue")

        if string_bound is not None and type_name not in {"string", "wstring"}:
            raise ValueError(f"Invalid string bound for type {type_name}")
        if constant_value is not None:
            if re.fullmatch(r"[A-Z](?:_?[A-Z0-9]+)*", name) is None:
                raise ValueError(f"Invalid constant name: {name}")
        else:
            if re.fullmatch(r"[a-z](?:_?[a-z0-9]+)*", name) is None:
                raise ValueError(f"Invalid field name: {name}")

        is_complex = type_name not in ROS2_BUILTIN_TYPES
        is_array = bool(unbounded_array or array_length or array_bound)

        field = MessageDefinitionField(
            name=name,
            type=type_name,
            isComplex=is_complex,
            isArray=is_array,
            arrayLength=int(array_length) if array_length else None,
            arrayUpperBound=int(array_bound) if array_bound else None,
            upperBound=int(string_bound) if string_bound else None,
            isConstant=constant_value is not None,
            defaultValue=(
                _parse_array_literal(type_name, default_value.strip())
                if default_value is not None and is_array
                else (
                    _parse_primitive_literal(type_name, default_value.strip())
                    if default_value is not None
                    else None
                )
            ),
            value=(
                _parse_primitive_literal(type_name, constant_value.strip())
                if constant_value is not None
                else None
            ),
            valueText=constant_value.strip() if constant_value is not None else None,
        )
        definitions.append(field)
    return MessageDefinition(name=complex_type_name, definitions=definitions)


def parse(
    message_definition: str, ros2: bool = False, skip_type_fixup: bool = False
) -> List[MessageDefinition]:
    lines = [line.strip() for line in message_definition.splitlines() if line.strip()]
    definition_lines: List[str] = []
    types: List[MessageDefinition] = []
    for line in lines:
        if line.startswith("#"):
            continue
        if line.startswith("=="):
            types.append(
                _build_ros2_type(definition_lines)
                if ros2
                else _build_type(definition_lines)
            )
            definition_lines = []
        else:
            definition_lines.append(line)
    types.append(
        _build_ros2_type(definition_lines) if ros2 else _build_type(definition_lines)
    )

    unique: List[MessageDefinition] = []
    for t in types:
        if not any(is_msg_def_equal(t, other) for other in unique):
            unique.append(t)

    if not skip_type_fixup:
        fixup_types(unique)

    return unique


def fixup_types(types: List[MessageDefinition]) -> None:
    for msg in types:
        namespace = "/".join(msg.name.split("/")[:-1]) if msg.name else None
        for field in msg.definitions:
            if field.isComplex:
                found = _find_type_by_name(types, field.type, namespace)
                if found.name is None:
                    raise ValueError(f"Missing type definition for {field.type}")
                field.type = found.name


def _build_type(lines: List[str]) -> MessageDefinition:
    definitions: List[MessageDefinitionField] = []
    complex_type_name: Optional[str] = None
    for line in lines:
        if line.startswith("MSG:"):
            complex_type_name = line.split(":", 1)[1].strip()
            continue
        line = re.sub(r"#.*", "", line).strip()
        if not line:
            continue
        m = re.match(
            r"(?P<type>[^\s]+)\s+(?P<name>[^\s=]+)(\s*=\s*(?P<value>.*))?", line
        )
        if not m:
            raise ValueError(f"Could not parse line: '{line}'")
        type_name = normalize_type(m.group("type"))
        name = m.group("name")
        value_text = m.group("value")
        is_array = False
        array_length: Optional[int] = None
        array_match = re.match(r"^(?P<base>[^\[]+)\[(?P<len>\d*)\]$", type_name)
        if array_match:
            type_name = array_match.group("base")
            is_array = True
            length = array_match.group("len")
            if length:
                array_length = int(length)
        isComplex = not _is_builtin(type_name)
        field = MessageDefinitionField(
            type=type_name,
            name=name,
            isArray=is_array,
            arrayLength=array_length,
            isConstant=value_text is not None,
            valueText=value_text.strip() if value_text is not None else None,
            isComplex=isComplex,
        )
        definitions.append(field)
    return MessageDefinition(name=complex_type_name, definitions=definitions)


def _find_type_by_name(
    types: List[MessageDefinition], name: str, type_namespace: Optional[str]
) -> MessageDefinition:
    matches: List[MessageDefinition] = []
    for t in types:
        type_name = t.name or ""
        if not name:
            if not type_name:
                matches.append(t)
        elif "/" in name:
            if type_name == name:
                matches.append(t)
        elif name == "Header":
            if type_name == "std_msgs/Header":
                matches.append(t)
        elif type_namespace:
            if type_name == f"{type_namespace}/{name}":
                matches.append(t)
        else:
            if type_name.endswith(f"/{name}"):
                matches.append(t)
    if not matches:
        raise ValueError(
            f"Expected 1 top level type definition for '{name}' "
            f"but found {len(matches)}"
        )
    if len(matches) > 1:
        raise ValueError(
            f"Cannot unambiguously determine fully-qualified type name for '{name}'"
        )
    return matches[0]


def normalize_type(type_name: str) -> str:
    if type_name == "char":
        return "uint8"
    if type_name == "byte":
        return "int8"
    return type_name


def _is_builtin(type_name: str) -> bool:
    return type_name in BUILTIN_TYPES
