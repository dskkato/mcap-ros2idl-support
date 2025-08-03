import sys
import struct
from pathlib import Path

# Insert the parent directory at the start of sys.path to ensure tests use the local (uninstalled) version of the package.
# This is intentional to avoid conflicts with installed packages and to test the current source.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcap_ros2idl_support.cdr_reader import CdrReader, MessageType  # noqa: E402


def test_enum_with_uint8():
    type_map = {
        "Status": MessageType(
            "Status",
            [
                {
                    "name": "UNKNOWN",
                    "type": "uint8",
                    "isComplex": False,
                    "isConstant": True,
                    "value": 0,
                },
                {
                    "name": "OK",
                    "type": "uint8",
                    "isComplex": False,
                    "isConstant": True,
                    "value": 2,
                },
            ],
        ),
        "Msg": MessageType(
            "Msg",
            [
                {
                    "name": "status",
                    "type": "uint8",
                    "isComplex": False,
                    "enumType": "Status",
                }
            ],
        ),
    }
    enum_map = {"Status": {0: "UNKNOWN", 2: "OK"}}
    reader = CdrReader(type_map, enum_map)
    data = b"\x00\x00\x00\x00" + b"\x02"
    assert reader.read("Msg", data) == {"status": "OK"}


def test_little_endian_uint32():
    type_map = {
        "Msg": MessageType(
            "Msg",
            [
                {
                    "name": "value",
                    "type": "uint32",
                    "isComplex": False,
                }
            ],
        )
    }
    reader = CdrReader(type_map)
    data = b"\x00\x01\x00\x00" + struct.pack("<I", 0x01020304)
    assert reader.read("Msg", data) == {"value": 0x01020304}


def test_big_endian_uint32():
    type_map = {
        "Msg": MessageType(
            "Msg",
            [
                {
                    "name": "value",
                    "type": "uint32",
                    "isComplex": False,
                }
            ],
        )
    }
    reader = CdrReader(type_map)
    data = b"\x00\x00\x00\x00" + struct.pack(">I", 0x01020304)
    assert reader.read("Msg", data) == {"value": 0x01020304}
