from dataclasses import asdict, dataclass

from mcap.reader import make_reader
from mcap.records import Schema
from ros2idl_parser import parse_ros2idl
from rosmsg import parse as parse_ros2msg

from .cdr_reader import MessageType


@dataclass
class SchemaInfo:
    """Container for message types and enum lookups for a schema."""

    type_map: dict[str, MessageType]
    enum_map: dict[str, dict[int, str]]


def load_idl(mcap_file: str) -> dict[int, SchemaInfo]:
    """Load type definitions and enums from an MCAP file.

    Returns a dictionary indexed by schema ID containing a ``SchemaInfo``
    instance with message type and enum maps.
    """
    with open(mcap_file, "rb") as f:
        reader = make_reader(f)
        summary = reader.get_summary()
        schemas: dict[int, Schema] = summary.schemas

    id_to_schema: dict[int, SchemaInfo] = {}

    for i, schema in schemas.items():
        schema_id = int(i)
        type_map: dict[str, MessageType] = {}
        enum_map: dict[str, dict[int, str]] = {}
        if schema.encoding == "ros2idl":
            try:
                s = parse_ros2idl(schema.data.decode("utf-8"))
            except ValueError as e:
                print(f"Error parsing ros2idl for schema ID {schema_id}: {e}")
                continue
        elif schema.encoding == "ros2msg":
            s = parse_ros2msg(schema.data.decode("utf-8"))
        else:
            print(
                f"Unknown schema encoding: {schema.encoding} for schema ID: {schema_id}"
            )
            continue
        for type_def in s:
            field_dicts = [asdict(f) for f in type_def.definitions]
            type_map[type_def.name] = MessageType(type_def.name, field_dicts)
            enum_candidates = [f for f in type_def.definitions if f.isConstant]
            if enum_candidates:
                enum_lookup: dict[int, str] = {f.value: f.name for f in enum_candidates}
                enum_map[type_def.name] = enum_lookup
        id_to_schema[schema_id] = SchemaInfo(type_map, enum_map)

    return id_to_schema
