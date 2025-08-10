import struct

from rosmsg import parse

from mcap_ros2idl_support import MessageReader


def test_enum_with_uint8():
    definitions = parse(
        """
        uint8 UNKNOWN=0
        uint8 OK=2
        ==
        uint8 status
        """
    )
    reader = MessageReader(definitions)
    data = b"\x00\x00\x00\x00" + b"\x02"
    assert reader.read_message(data) == {"status": 2}


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
