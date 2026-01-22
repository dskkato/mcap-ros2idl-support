import struct

import pytest
from mcap.records import Schema

from mcap_ros2idl_support.encode_factory import Ros2EncodeFactory
from mcap_ros2idl_support.ros2idl_parser import parse_ros2idl
from mcap_ros2idl_support.rosmsg2_serialization import (
    MessageReader,
    MessageReaderOptions,
)


def test_register_schema_and_encode() -> None:
    factory = Ros2EncodeFactory()
    schema_text = "int32 counter"
    factory.register_schema(1, encoding="ros2msg", data=schema_text)

    message = {"counter": 42}
    encoded = factory.encode(1, message)
    expected = b"\x00\x01\x00\x00" + struct.pack("<i", 42)
    assert encoded == expected
    assert factory.calculate_size(1, message) == len(expected)


def test_encoder_for_schema_ros2idl() -> None:
    factory = Ros2EncodeFactory()
    idl = """module example {
  module msg {
    struct Sample {
      long data;
      int32 sequence_id;
    };
  };
};
"""
    schema = Schema(
        id=5,
        name="example/msg/Sample",
        encoding="ros2idl",
        data=idl.encode("utf-8"),
    )
    encoder = factory.encoder_for_schema(schema)

    message = {"data": 7}
    encoded = encoder(message)
    expected = b"\x00\x01\x00\x00" + struct.pack("<i", 7) + struct.pack("<i", 0)
    assert encoded == expected
    assert factory.calculate_size_with_schema(schema, message) == len(expected)
    assert factory.encode_with_schema(schema, message) == expected


def test_unknown_encoding_raises() -> None:
    factory = Ros2EncodeFactory()
    schema = Schema(id=3, name="test", encoding="jsonschema", data=b"{}")
    with pytest.raises(ValueError):
        factory.encoder_for_schema(schema)


def test_encode_nested_struct_and_arrays_ros2msg() -> None:
    factory = Ros2EncodeFactory()
    msg_def = """std_msgs/msg/Header header
geometry_msgs/msg/Vector3[] points
================================================================================
MSG: std_msgs/msg/Header
builtin_interfaces/msg/Time stamp
string frame_id
================================================================================
MSG: builtin_interfaces/msg/Time
int32 sec
uint32 nanosec
================================================================================
MSG: geometry_msgs/msg/Vector3
float64 x
float64 y
float64 z
"""
    schema = Schema(
        id=9,
        name="example/Nested",
        encoding="ros2msg",
        data=msg_def.encode("utf-8"),
    )
    message = {
        "header": {
            "stamp": {"sec": 10, "nanosec": 42},
            "frame_id": "map",
        },
        "points": [
            {"x": 1.5, "y": 2.5, "z": 3.5},
            {"x": -1.25, "y": 0.0, "z": 10.0},
        ],
    }
    expected = bytes.fromhex(
        "000100000a0000002a000000040000006d6170000200000000000000000000000000f83f"
        "00000000000004400000000000000c40000000000000f4bf000000000000000000000000"
        "00002440"
    )
    assert factory.encode_with_schema(schema, message) == expected
    # Ensure the cached encoder path returns the same payload
    encoder = factory.encoder_for_schema(schema)
    assert encoder(message) == expected
    assert factory.calculate_size_with_schema(schema, message) == len(expected)


def test_encode_fixed_and_bounded_arrays_ros2idl() -> None:
    factory = Ros2EncodeFactory()
    idl = """module example {
  module msg {
    struct Complex {
      Inner readings[2];
      sequence<double,2> weights;
    };
    struct Inner {
      long count;
      boolean flag;
    };
  };
};
"""
    schema = Schema(
        id=11,
        name="example/msg/Complex",
        encoding="ros2idl",
        data=idl.encode("utf-8"),
    )
    message = {
        "readings": [
            {"count": 5, "flag": True},
            {"count": -2, "flag": False},
        ],
        "weights": [1.0, -3.5],
    }
    expected = bytes.fromhex(
        "000100000500000001000000feffffff000000000200000000000000000000000000f03f"
        "0000000000000cc0"
    )
    assert factory.encode_with_schema(schema, message) == expected
    assert factory.calculate_size_with_schema(schema, message) == len(expected)


def test_multiple_schema_ids_and_channels() -> None:
    factory = Ros2EncodeFactory()
    schema_ros2msg = "int32 data"
    idl = """module example {
  module msg {
    struct Point {
      double x;
      double y;
    };
  };
};
"""
    factory.register_schema(1, encoding="ros2msg", data=schema_ros2msg)
    factory.register_schema(2, encoding="ros2idl", data=idl)

    msg_a = {"data": 10}
    msg_b = {"x": 1.0, "y": -2.5}

    expected_a = b"\x00\x01\x00\x00" + struct.pack("<i", 10)
    expected_b = b"\x00\x01\x00\x00" + struct.pack("<2d", 1.0, -2.5)

    assert factory.encode(1, msg_a) == expected_a
    assert factory.encode(2, msg_b) == expected_b

    # Re-encode to ensure cached writers remain distinct
    other_a = b"\x00\x01\x00\x00" + struct.pack("<i", -5)
    assert factory.encode(1, {"data": -5}) == other_a


def test_union_and_enum_encoding() -> None:
    factory = Ros2EncodeFactory()
    idl = """module test {
  enum Switch { INT_CASE, TEXT_CASE };
  union IntOrString switch(Switch) {
    case INT_CASE: int32 num;
    case TEXT_CASE: string text;
  };
  struct Wrapper {
    IntOrString value;
    test::Switch status;
  };
};
"""
    schema = Schema(
        id=13,
        name="test/Wrapper",
        encoding="ros2idl",
        data=idl.encode("utf-8"),
    )
    message = {
        "value": {"discriminator": "TEXT_CASE", "text": "hello"},
        "status": "INT_CASE",
    }
    expected = bytes.fromhex("00010000010000000600000068656c6c6f00000000000000")
    assert factory.encode_with_schema(schema, message) == expected

def test_encode_decode_round_trip_union_and_enum() -> None:
    factory = Ros2EncodeFactory()
    idl = """module test {
  enum Switch { INT_CASE, TEXT_CASE };
  union IntOrString switch(Switch) {
    case INT_CASE: int32 num;
    case TEXT_CASE: string text;
  };
  struct Wrapper {
    IntOrString value;
    test::Switch status;
  };
};
"""
    schema = Schema(
        id=21,
        name="test/Wrapper",
        encoding="ros2idl",
        data=idl.encode("utf-8"),
    )
    message = {
        "value": {"discriminator": "TEXT_CASE", "text": "hello"},
        "status": "INT_CASE",
    }
    encoded = factory.encode_with_schema(schema, message)
    defs = parse_ros2idl(idl)
    reader = MessageReader(defs, MessageReaderOptions(enumAsString=True))
    assert reader.read_message(encoded) == message
