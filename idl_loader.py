import json
from typing import Dict, Tuple

from cdr_reader import MessageType


def load_idl(path: str) -> Tuple[Dict[int, Dict[str, MessageType]], Dict[int, Dict[str, dict]]]:
    """Load type definitions and enums from a JSON file.

    Returns two dictionaries indexed by schema ID: a map of message types
    and a map of enum lookups.
    """
    with open(path, "r") as f:
        type_definitions = json.load(f)

    id_to_type_map: Dict[int, Dict[str, MessageType]] = {}
    id_to_enum_map: Dict[int, Dict[str, dict]] = {}

    for i, schema in type_definitions.items():
        schema_id = int(i)
        type_map: Dict[str, MessageType] = {}
        enum_map: Dict[str, dict] = {}
        for type_def in schema:
            type_map[type_def["name"]] = MessageType(
                type_def["name"], type_def["definitions"]
            )
            enum_candidates = [
                f for f in type_def.get("definitions", []) if f.get("isConstant")
            ]
            if enum_candidates:
                enum_lookup = {f["value"]: f["name"] for f in enum_candidates}
                enum_map[type_def["name"]] = enum_lookup
        id_to_type_map[schema_id] = type_map
        id_to_enum_map[schema_id] = enum_map

    return id_to_type_map, id_to_enum_map
