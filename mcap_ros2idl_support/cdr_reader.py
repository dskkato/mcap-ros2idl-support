import io
import struct


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
    _ALIGNMENT = {
        "uint8": 1,
        "int8": 1,
        "bool": 1,
        "uint16": 2,
        "int16": 2,
        "uint32": 4,
        "int32": 4,
        "float32": 4,
        "uint64": 8,
        "int64": 8,
        "float64": 8,
    }

    def __init__(self, type_map, enum_map=None):
        self.types = type_map
        self.enums = enum_map
        self.stream = None
        self.endianness = "<"
        self._structs: dict[str, struct.Struct] = {}

    def read(self, typename, data: bytes):
        self.stream = io.BytesIO(data)
        header = self.stream.read(4)
        if len(header) < 4:
            raise ValueError("Incomplete CDR header")
        # According to the CDR specification, bit 0 of byte 1 indicates
        # little endian when set.
        self.endianness = "<" if header[1] & 0x01 else ">"
        # Initialize cached struct objects for primitives with the current endianness
        self._structs = {
            name: struct.Struct(self.endianness + fmt)
            for name, fmt in {
                "uint8": "B",
                "int8": "b",
                "uint16": "H",
                "int16": "h",
                "int32": "i",
                "uint32": "I",
                "int64": "q",
                "uint64": "Q",
                "float32": "f",
                "float64": "d",
                "bool": "?",
            }.items()
        }
        return self._read_message(self.types[typename])

    def _align(self, size: int, base: int = 4):
        relative_offset = self.stream.tell() - base
        padding = (size - (relative_offset % size)) % size
        self.stream.seek(padding, io.SEEK_CUR)

    def _read_message(self, msg_type: "MessageType"):
        result = {}
        types = self.types
        read_array = self._read_array
        read_message = self._read_message
        read_primitive = self._read_primitive
        for field in msg_type.fields:
            if field.is_array:
                result[field.name] = read_array(field)
            elif field.is_complex:
                result[field.name] = read_message(types[field.type])
            else:
                result[field.name] = read_primitive(field.type, field.enum_type)
        return result

    def _read_array(self, field):
        # Sequence length is prefixed with UInt32
        length = self._read_primitive("uint32")
        if field.is_complex:
            msg_type = self.types[field.type]
            read_message = self._read_message
            return [read_message(msg_type) for _ in range(length)]

        # Primitive array fast path
        struct_obj = self._structs.get(field.type)
        if struct_obj is None:
            raise ValueError(f"Unsupported primitive type: {field.type}")

        align_size = self._ALIGNMENT.get(field.type, 1)
        if align_size > 1:
            self._align(align_size)
        data = self.stream.read(struct_obj.size * length)

        if field.enum_type:
            enum_lookup = self.enums[field.enum_type]
            return [
                enum_lookup.get(v, f"Unknown enum value: {v}")
                for (v,) in struct_obj.iter_unpack(data)
            ]

        return [v for (v,) in struct_obj.iter_unpack(data)]

    def _read_primitive(self, type_name, enum_type=None):
        align_size = self._ALIGNMENT.get(type_name, 1)
        if align_size > 1:
            self._align(align_size)

        struct_obj = self._structs.get(type_name)
        if struct_obj:
            value = struct_obj.unpack(self.stream.read(struct_obj.size))[0]
        elif type_name == "string":
            length = self._read_primitive("uint32")
            bytes_ = self.stream.read(length)
            value = bytes_[:-1].decode("utf-8")
        else:
            raise ValueError(f"Unknown primitive type: {type_name}")

        if enum_type:
            if enum_type not in self.enums:
                raise ValueError(f"Unknown enum type: {enum_type}")
            enum_lookup = self.enums[enum_type]
            return enum_lookup.get(value, f"Unknown enum value: {value}")

        return value
