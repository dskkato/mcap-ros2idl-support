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
    def __init__(self, type_map, enum_map=None):
        self.types = type_map
        self.enums = enum_map
        self.stream = None
        self.endianness = "<"

    def read(self, typename, data: bytes):
        self.stream = io.BytesIO(data)
        header = self.stream.read(4)
        if len(header) < 4:
            raise ValueError("Incomplete CDR header")
        self.endianness = "<" if header[1] & 0x01 else ">"
        return self._read_message(self.types[typename])

    def _align(self, size: int, base: int = 4):
        relative_offset = self.stream.tell() - base
        padding = (size - (relative_offset % size)) % size
        self.stream.seek(padding, io.SEEK_CUR)

    def _read_message(self, msg_type: "MessageType"):
        result = {}
        for field in msg_type.fields:
            if field.is_array:
                result[field.name] = self._read_array(field)
            elif field.is_complex:
                result[field.name] = self._read_message(self.types[field.type])
            else:
                result[field.name] = self._read_primitive(field.type, field.enum_type)
        return result

    def _read_array(self, field):
        # Sequence length is prefixed with UInt32
        length = self._read_primitive("uint32")
        items = []
        for _ in range(length):
            if field.is_complex:
                items.append(self._read_message(self.types[field.type]))
            else:
                items.append(self._read_primitive(field.type, field.enum_type))
        return items

    def _read_primitive(self, type_name, enum_type=None):
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
            "int64": "q",
            "uint64": "Q",
            "float32": "f",
            "float64": "d",
            "bool": "?",
        }.get(type_name)

        if fmt:
            value = struct.unpack(self.endianness + fmt, self.stream.read(struct.calcsize(fmt)))[0]
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
