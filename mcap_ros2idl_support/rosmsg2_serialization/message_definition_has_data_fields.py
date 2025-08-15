from __future__ import annotations

from typing import Sequence

from mcap_ros2idl_support.message_definition import MessageDefinitionField


def message_definition_has_data_fields(
    fields: Sequence[MessageDefinitionField],
) -> bool:
    """Return True if any field is not a constant."""
    return any(field.isConstant is not True for field in fields)
