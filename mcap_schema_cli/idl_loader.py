import json
from dataclasses import dataclass
from typing import Dict

from .cdr_reader import MessageType
from python_omgidl.omgidl_serialization.message_reader import (
    MessageDefinitionField,
    MessageReader,
)


@dataclass
class SchemaInfo:
    """Container for message and enum definitions for a schema."""

    type_map: Dict[str, MessageType]
    enum_map: Dict[str, dict]
    reader_map: Dict[str, MessageReader]


def load_idl(path: str) -> Dict[int, SchemaInfo]:
    """Load type definitions and enums from a JSON file.

    Returns a dictionary indexed by schema ID containing a ``SchemaInfo``
    instance with message type and enum maps.
    """
    with open(path, "r") as f:
        type_definitions = json.load(f)

    id_to_schema: Dict[int, SchemaInfo] = {}

    for i, schema in type_definitions.items():
        schema_id = int(i)
        type_map: Dict[str, MessageType] = {}
        enum_map: Dict[str, dict] = {}
        reader_map: Dict[str, MessageReader] = {}
        for type_def in schema:
            non_constants = [
                f for f in type_def.get("definitions", []) if not f.get("isConstant")
            ]
            type_map[type_def["name"]] = MessageType(
                type_def["name"], non_constants
            )

            fields = [
                MessageDefinitionField(
                    name=f["name"],
                    type=f["type"],
                    is_constant=f.get("isConstant", False),
                    default_value=f.get("defaultValue"),
                )
                for f in type_def.get("definitions", [])
            ]
            reader_map[type_def["name"]] = MessageReader(fields)

            enum_candidates = [
                f for f in type_def.get("definitions", []) if f.get("isConstant")
            ]
            if enum_candidates:
                enum_lookup = {f["value"]: f["name"] for f in enum_candidates}
                enum_map[type_def["name"]] = enum_lookup
        id_to_schema[schema_id] = SchemaInfo(type_map, enum_map, reader_map)

    return id_to_schema
