from __future__ import annotations

import hashlib
from typing import Dict, List

from mcap_ros2idl_support.message_definition import MessageDefinition

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


def md5(msg_defs: List[MessageDefinition]) -> str:
    if not msg_defs:
        raise ValueError("Cannot produce md5sum for empty msgDefs")
    sub_defs: Dict[str, MessageDefinition] = {
        d.name: d for d in msg_defs if d.name is not None
    }
    first = msg_defs[0]
    return _compute_md5(first, sub_defs)


def _compute_md5(
    msg_def: MessageDefinition, sub_defs: Dict[str, MessageDefinition]
) -> str:
    constants = [d for d in msg_def.definitions if d.isConstant]
    variables = [d for d in msg_def.definitions if not d.isConstant]
    lines: List[str] = []
    for d in constants:
        valueText = d.valueText if d.valueText is not None else str(d.value)
        lines.append(f"{d.type} {d.name}={valueText}")
    for d in variables:
        if _is_builtin(d.type):
            array_len = str(d.arrayLength) if d.arrayLength is not None else ""
            array = f"[{array_len}]" if d.isArray else ""
            lines.append(f"{d.type}{array} {d.name}")
        else:
            sub = sub_defs.get(d.type)
            if sub is None:
                raise ValueError(f'Missing definition for submessage type "{d.type}"')
            sub_md5 = _compute_md5(sub, sub_defs)
            lines.append(f"{sub_md5} {d.name}")
    text = "\n".join(lines)
    return hashlib.md5(text.encode()).hexdigest()


def _is_builtin(type_name: str) -> bool:
    return type_name in BUILTIN_TYPES
