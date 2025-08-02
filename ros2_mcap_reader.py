import io
import struct

from mcap.reader import make_reader


class Field:
    def __init__(self, name, type, isComplex, **kwargs):
        self.name = name
        self.type = type
        self.is_complex = isComplex
        self.is_array = kwargs.get("isArray", False)
        self.array_upper_bound = kwargs.get("arrayUpperBound")
        self.default_value = kwargs.get("defaultValue")
        self.upper_bound = kwargs.get("upperBound")
        self.enum_type = kwargs.get("enumType")
        if self.enum_type:
            self.enum_type = self.enum_type.replace("::", "/")


class MessageType:
    def __init__(self, name, definitions):
        self.name = name
        self.fields = [Field(**field) for field in definitions]


class CdrReader:
    def __init__(self, type_map, enum_map=None):
        self.types = type_map
        self.enums = enum_map
        self.stream = None

    def read(self, typename, data: bytes):
        self.stream = io.BytesIO(data)
        self._read_primitive("uint32")  # Skip the CDR header
        return self._read_message(self.types[typename])

    def _align(self, size: int, base: int = 4):
        relative_offset = self.stream.tell() - base
        padding = (size - (relative_offset % size)) % size
        self.stream.seek(padding, io.SEEK_CUR)

    def _read_message(self, msg_type: MessageType):
        result = {}
        for field in msg_type.fields:
            print(f"Reading field: {field.name} of type {field.type}")
            if field.name == "status":
                print(f"Reading status field: {field.name} of type {field.type}")
                print(f"Enum type: {field.enum_type}")
            if field.is_array:
                result[field.name] = self._read_array(field)
            elif field.is_complex:
                result[field.name] = self._read_message(self.types[field.type])
            else:
                result[field.name] = self._read_primitive(field.type, field.enum_type)
        return result

    def _read_array(self, field):
        # シーケンスの長さは UInt32 prefix 付き
        length = self._read_primitive("uint32")
        items = []
        for _ in range(length):
            if field.is_complex:
                items.append(self._read_message(self.types[field.type]))
            else:
                items.append(self._read_primitive(field.type, field.enum_type))
        return items

    def _read_primitive(self, type_name, enum_type=None):
        if enum_type:
            print(f"Reading enum type: {enum_type}")
        if type_name in ("uint32", "int32", "float32"):
            self._align(4)
        elif type_name in ("uint64", "int64", "float64"):
            self._align(8)
        elif type_name in ("uint16", "int16"):
            self._align(2)
        fmt = {
            "uint8": "B",
            "int8": "b",
            "uint16": "H",
            "int16": "h",
            "int32": "i",
            "uint32": "I",
            "int16": "h",
            "uint16": "H",
            "int64": "q",
            "uint64": "Q",
            "float32": "f",
            "float64": "d",
            "bool": "?",
        }.get(type_name)
        if enum_type:
            print(f"Reading enum type: {enum_type}")
            if enum_type not in self.enums:
                raise ValueError(f"Unknown enum type: {enum_type}")
            enum_lookup = self.enums[enum_type]
            value = self._read_primitive("int32")
            return enum_lookup.get(value, f"Unknown enum value: {value}")

        if fmt:
            return struct.unpack("<" + fmt, self.stream.read(struct.calcsize(fmt)))[0]
        elif type_name == "string":
            length = self._read_primitive("uint32")
            bytes_ = self.stream.read(length)
            return bytes_[:-1].decode("utf-8")
        else:
            raise ValueError(f"Unknown primitive type: {type_name}")


if __name__ == "__main__":
    import json
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Read CDR messages from MCAP files.")
    parser.add_argument(
        "--type-definitions",
        type=str,
        required=True,
        help="Path to the JSON file containing type definitions.",
    )
    parser.add_argument(
        "--mcap-file",
        type=str,
        required=True,
        help="Path to the MCAP file to read messages from.",
    )
    args = parser.parse_args()

    with open(args.type_definitions, "r") as f:
        type_definitions = json.load(f)

    id_to_cdr_reader = {}
    for i, schema in type_definitions.items():
        type_map = {}
        for type_def in schema:
            type_map[type_def["name"]] = MessageType(
                type_def["name"], type_def["definitions"]
            )

        enum_map = {}  # str -> dict[int -> str]
        for type_def in schema:
            enum_candidates = [
                f for f in type_def.get("definitions", []) if f.get("isConstant")
            ]
            if enum_candidates:
                enum_lookup = {f["value"]: f["name"] for f in enum_candidates}
                enum_map[type_def["name"]] = enum_lookup

        id_to_cdr_reader[int(i)] = CdrReader(type_map, enum_map)

    file_path = args.mcap_file
    with open(file_path, "rb") as f:
        reader = make_reader(f)
        for topic, schema, message in reader.iter_messages():
            print(f"Topic: {topic}, Schema ID: {schema.schema_id}")
            if schema.schema_id not in id_to_cdr_reader:
                print(f"Schema ID {schema.schema_id} not found in type definitions.")
                continue
            msg = id_to_cdr_reader[schema.schema_id].read(topic.name, message.data)
            print(json.dumps(msg, indent=2))
