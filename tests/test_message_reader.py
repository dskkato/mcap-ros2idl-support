import struct

from mcap_ros2idl_support import MessageReader, MessageReaderOptions
from mcap_ros2idl_support.ros2idl_parser import parse_ros2idl
from mcap_ros2idl_support.rosmsg import parse


def test_enum_with_uint32():
    definitions = parse_ros2idl(
        """
        module example {
          enum Status {
            UNKNOWN,
            OK
          };
          struct Msg {
            example::Status status;
          };
        };
        """
    )
    reader = MessageReader(definitions)
    data = b"\x00\x01\x00\x00" + struct.pack("<I", 1)
    assert reader.read_message(data) == {"status": 1}


def test_enum_with_uint32_as_string():
    definitions = parse_ros2idl(
        """
        module example {
          enum Status {
            UNKNOWN,
            OK
          };
          struct Msg {
            example::Status status;
          };
        };
        """
    )
    options = MessageReaderOptions(enumAsString=True)
    reader = MessageReader(definitions, options)
    data = b"\x00\x01\x00\x00" + struct.pack("<I", 1)
    assert reader.read_message(data) == {"status": "OK"}


def test_little_endian_uint32():
    definitions = parse("uint32 value")
    reader = MessageReader(definitions)
    data = b"\x00\x01\x00\x00" + struct.pack("<I", 0x01020304)
    assert reader.read_message(data) == {"value": 0x01020304}


def test_big_endian_uint32():
    definitions = parse("uint32 value")
    reader = MessageReader(definitions)
    data = b"\x00\x00\x00\x00" + struct.pack(">I", 0x01020304)
    assert reader.read_message(data) == {"value": 0x01020304}
