from dataclasses import dataclass

from serde import serde, to_dict
from serde.json import from_json

from .cdr_reader import MessageType


@serde
@dataclass
class FieldDefinition:
    name: str
    type: str
    isComplex: bool
    isArray: bool = False
    arrayUpperBound: int | None = None
    defaultValue: str | int | float | bool | None = None
    upperBound: int | None = None
    enumType: str | None = None
    isConstant: bool = False
    value: int | str | None = None


@serde
@dataclass
class TypeDefinition:
    name: str
    definitions: list[FieldDefinition]


@dataclass
class SchemaInfo:
    """Container for message types and enum lookups for a schema."""

    type_map: dict[str, MessageType]
    enum_map: dict[str, dict[int, str]]


def load_idl(path: str) -> dict[int, SchemaInfo]:
    """Load type definitions and enums from a JSON file.

    Returns a dictionary indexed by schema ID containing a ``SchemaInfo``
    instance with message type and enum maps.
    """
    with open(path, "r", encoding="utf-8") as f:
        type_definitions = from_json(dict[str, list[TypeDefinition]], f.read())

    id_to_schema: dict[int, SchemaInfo] = {}

    for i, schema in type_definitions.items():
        schema_id = int(i)
        type_map: dict[str, MessageType] = {}
        enum_map: dict[str, dict[int, str]] = {}
        for type_def in schema:
            field_dicts = [to_dict(f, skip_none=True) for f in type_def.definitions]
            type_map[type_def.name] = MessageType(type_def.name, field_dicts)
            enum_candidates = [f for f in type_def.definitions if f.isConstant]
            if enum_candidates:
                enum_lookup: dict[int, str] = {f.value: f.name for f in enum_candidates}
                enum_map[type_def.name] = enum_lookup
        id_to_schema[schema_id] = SchemaInfo(type_map, enum_map)

    return id_to_schema
