from __future__ import annotations

import json
from typing import Any, List

from mcap_ros2idl_support.message_definition import MessageDefinition


def _stringify_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, float):
        return format(value, "g")
    return str(value)


def stringify_default_value(value: Any) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(_stringify_value(x) for x in value) + "]"
    return _stringify_value(value)


def stringify(msg_defs: List[MessageDefinition]) -> str:
    lines: List[str] = []
    for i, msg_def in enumerate(msg_defs):
        constants = [d for d in msg_def.definitions if getattr(d, "isConstant", False)]
        variables = [
            d for d in msg_def.definitions if not getattr(d, "isConstant", False)
        ]

        if i > 0:
            lines.append("")
            lines.append("=" * 80)
            lines.append(f"MSG: {msg_def.name or ''}")
        for const in constants:
            value = (
                const.valueText
                if const.valueText is not None
                else _stringify_value(const.value)
            )
            lines.append(f"{const.type} {const.name} = {value}")
        if variables:
            if lines:
                lines.append("")
            for var in variables:
                upper_bound = (
                    f"<={var.upperBound}" if var.upperBound is not None else ""
                )
                if var.arrayLength is not None:
                    array_len = str(var.arrayLength)
                elif var.arrayUpperBound is not None:
                    array_len = f"<={var.arrayUpperBound}"
                else:
                    array_len = ""
                array_suffix = (
                    f"[{array_len}]" if getattr(var, "isArray", False) else ""
                )
                default_value = (
                    f" {stringify_default_value(var.defaultValue)}"
                    if var.defaultValue is not None
                    else ""
                )
                lines.append(
                    f"{var.type}{upper_bound}{array_suffix} {var.name}{default_value}"
                )
    return "\n".join(lines).rstrip()
