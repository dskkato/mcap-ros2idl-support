# flake8: noqa
import struct

import pytest

from mcap_ros2idl_support.cdr import CdrWriter
from mcap_ros2idl_support.ros2idl_parser import parse_ros2idl
from mcap_ros2idl_support.rosmsg2_serialization import (
    MessageReader,
    MessageReaderOptions,
)
from mcap_ros2idl_support.rosmsg.parse import parse


def _serialize_string(string: str) -> bytes:
    data = string.encode("utf8")
    return struct.pack("<I", len(data) + 1) + data + b"\x00"


@pytest.mark.parametrize(
    "primitive,fmt,min_val,max_val",
    [
        ("int8", "<b", -128, 127),
        ("uint8", "<B", 0, 255),
        ("int16", "<h", -32768, 32767),
        ("uint16", "<H", 0, 65535),
        ("int32", "<i", -2147483648, 2147483647),
        ("uint32", "<I", 0, 4294967295),
        ("int64", "<q", -9223372036854775808, 9223372036854775807),
        ("uint64", "<Q", 0, 18446744073709551615),
    ],
)
def test_primitive_bounds(primitive: str, fmt: str, min_val: int, max_val: int) -> None:
    msg_def = f"{primitive} sample"
    defs = parse(msg_def, ros2=True)
    reader = MessageReader(defs)
    for val in (min_val, max_val):
        buffer = b"\x00\x01\x00\x00" + struct.pack(fmt, val)
        assert reader.read_message(buffer) == {"sample": val}


@pytest.mark.parametrize(
    "primitive,fmt,val",
    [
        ("float32", "<f", 5.5),
        ("float64", "<d", 0.123456789121212121212),
    ],
)
def test_float_samples(primitive: str, fmt: str, val: float) -> None:
    msg_def = f"{primitive} sample"
    defs = parse(msg_def, ros2=True)
    reader = MessageReader(defs)
    buffer = b"\x00\x01\x00\x00" + struct.pack(fmt, val)
    assert reader.read_message(buffer) == {"sample": val}


@pytest.mark.parametrize(
    "msg_def,arr,expected",
    [
        (
            "int32[] arr",
            struct.pack("<I", 2) + struct.pack("<2i", 3, 7),
            {"arr": [3, 7]},
        ),
        (
            "uint8 blank\nint32[] arr",
            b"\x00" + b"\x00\x00\x00" + struct.pack("<I", 2) + struct.pack("<2i", 3, 7),
            {"blank": 0, "arr": [3, 7]},
        ),
        (
            "float32[2] arr",
            struct.pack("<2f", 5.5, 6.5),
            {"arr": [5.5, 6.5]},
        ),
        (
            "uint8 blank\nfloat32[2] arr",
            b"\x00" + b"\x00\x00\x00" + struct.pack("<2f", 5.5, 6.5),
            {"blank": 0, "arr": [5.5, 6.5]},
        ),
        (
            "float32[] arr",
            struct.pack("<I", 2) + struct.pack("<2f", 5.5, 6.5),
            {"arr": [5.5, 6.5]},
        ),
        (
            "uint8 blank\nfloat32[] arr",
            b"\x00"
            + b"\x00\x00\x00"
            + struct.pack("<I", 2)
            + struct.pack("<2f", 5.5, 6.5),
            {"blank": 0, "arr": [5.5, 6.5]},
        ),
        (
            "float32[] first\nfloat32[] second",
            struct.pack("<I", 2)
            + struct.pack("<2f", 5.5, 6.5)
            + struct.pack("<I", 2)
            + struct.pack("<2f", 5.5, 6.5),
            {
                "first": [5.5, 6.5],
                "second": [5.5, 6.5],
            },
        ),
        (
            "string sample",
            _serialize_string(""),
            {"sample": ""},
        ),
        (
            "string sample",
            _serialize_string("some string"),
            {"sample": "some string"},
        ),
        (
            "int8[4] first",
            bytes([0x00, 0xFF, 0x80, 0x7F]),
            {"first": [0, -1, -128, 127]},
        ),
        (
            "int8[] first",
            struct.pack("<I", 4) + bytes([0x00, 0xFF, 0x80, 0x7F]),
            {"first": [0, -1, -128, 127]},
        ),
        (
            "uint8[4] first",
            bytes([0x00, 0xFF, 0x80, 0x7F]),
            {"first": [0, 255, 128, 127]},
        ),
        (
            "string[2] first",
            _serialize_string("one") + _serialize_string("longer string"),
            {"first": ["one", "longer string"]},
        ),
        (
            "string[] first",
            struct.pack("<I", 2)
            + _serialize_string("one")
            + _serialize_string("longer string"),
            {"first": ["one", "longer string"]},
        ),
        (
            "int8 first\nint8 second",
            bytes([0x80, 0x7F]),
            {"first": -128, "second": 127},
        ),
        (
            "string first\nint8 second",
            _serialize_string("some string") + bytes([0x80]),
            {"first": "some string", "second": -128},
        ),
        (
            """CustomType custom
================================================================================
MSG: custom_type/CustomType
uint8 first
""",
            bytes([0x02]),
            {"custom": {"first": 0x02}},
        ),
        (
            """CustomType[3] custom
================================================================================
MSG: custom_type/CustomType
uint8 first
""",
            bytes([0x02, 0x03, 0x04]),
            {"custom": [{"first": 0x02}, {"first": 0x03}, {"first": 0x04}]},
        ),
        (
            """CustomType[] custom
================================================================================
MSG: custom_type/CustomType
uint8 first
""",
            struct.pack("<I", 3) + bytes([0x02, 0x03, 0x04]),
            {"custom": [{"first": 0x02}, {"first": 0x03}, {"first": 0x04}]},
        ),
        (
            "int8 STATUS_ONE = 1\nint8 STATUS_TWO = 2\nint8 status",
            bytes([0x02]),
            {"status": 2},
        ),
        (
            """CustomType[] custom
================================================================================
MSG: custom_type/CustomType
MoreCustom another
================================================================================
MSG: custom_type/MoreCustom
uint8 field
""",
            struct.pack("<I", 3) + bytes([0x02, 0x03, 0x04]),
            {
                "custom": [
                    {"another": {"field": 0x02}},
                    {"another": {"field": 0x03}},
                    {"another": {"field": 0x04}},
                ]
            },
        ),
    ],
)
def test_misc_cases(msg_def: str, arr: bytes, expected: dict) -> None:
    defs = parse(msg_def, ros2=True)
    reader = MessageReader(defs)
    buffer = b"\x00\x01\x00\x00" + arr
    assert reader.read_message(buffer) == expected


@pytest.mark.parametrize(
    "msg_def,arr,expected,ros1_expected",
    [
        (
            "time stamp",
            struct.pack("<iI", 0, 1),
            {"stamp": {"sec": 0, "nanosec": 1}},
            {"stamp": {"sec": 0, "nsec": 1}},
        ),
        (
            "duration stamp",
            struct.pack("<iI", 0, 1),
            {"stamp": {"sec": 0, "nanosec": 1}},
            {"stamp": {"sec": 0, "nsec": 1}},
        ),
        (
            "time[1] arr",
            struct.pack("<iI", 1, 2),
            {"arr": [{"sec": 1, "nanosec": 2}]},
            {"arr": [{"sec": 1, "nsec": 2}]},
        ),
        (
            "duration[1] arr",
            struct.pack("<iI", 1, 2),
            {"arr": [{"sec": 1, "nanosec": 2}]},
            {"arr": [{"sec": 1, "nsec": 2}]},
        ),
        (
            "time[] arr",
            struct.pack("<I", 1) + struct.pack("<iI", 2, 3),
            {"arr": [{"sec": 2, "nanosec": 3}]},
            {"arr": [{"sec": 2, "nsec": 3}]},
        ),
        (
            "duration[] arr",
            struct.pack("<I", 1) + struct.pack("<iI", 2, 3),
            {"arr": [{"sec": 2, "nanosec": 3}]},
            {"arr": [{"sec": 2, "nsec": 3}]},
        ),
        (
            "uint8 blank\ntime[] arr",
            b"\x00" + b"\x00\x00\x00" + struct.pack("<I", 1) + struct.pack("<iI", 2, 3),
            {"blank": 0, "arr": [{"sec": 2, "nanosec": 3}]},
            {"blank": 0, "arr": [{"sec": 2, "nsec": 3}]},
        ),
    ],
)
def test_time_type_option(
    msg_def: str, arr: bytes, expected: dict, ros1_expected: dict
) -> None:
    defs = parse(msg_def, ros2=True)
    buffer = b"\x00\x01\x00\x00" + arr
    assert MessageReader(defs).read_message(buffer) == expected
    assert (
        MessageReader(defs, MessageReaderOptions(timeType="sec,nsec")).read_message(
            buffer
        )
        == ros1_expected
    )


def test_log_message() -> None:
    hexdata = "00010000fb65865e80faae0614000000120000006d696e696d616c5f7075626c69736865720000001e0000005075626c697368696e673a202748656c6c6f2c20776f726c64212030270000004c0000002f6f70742f726f73325f77732f656c6f7175656e742f7372632f726f73322f6578616d706c65732f72636c6370702f6d696e696d616c5f7075626c69736865722f6c616d6264612e637070000b0000006f70657261746f722829007326000000"
    buffer = bytes.fromhex(hexdata)
    msg_def = """byte DEBUG=10
byte INFO=20
byte WARN=30
byte ERROR=40
byte FATAL=50
##
## Fields
##
builtin_interfaces/Time stamp
uint8 level
string name # name of the node
string msg # message
string file # file the message came from
string function # function the message came from
uint32 line # line the message came from
"""
    defs = parse(msg_def, ros2=True)
    reader = MessageReader(defs)
    read = reader.read_message(buffer)
    assert read == {
        "stamp": {"sec": 1585866235, "nanosec": 112130688},
        "level": 20,
        "name": "minimal_publisher",
        "msg": "Publishing: 'Hello, world! 0'",
        "file": "/opt/ros2_ws/eloquent/src/ros2/examples/rclcpp/minimal_publisher/lambda.cpp",
        "function": "operator()",
        "line": 38,
    }


def test_tf_message() -> None:
    hexdata = "0001000001000000286fae6169ddd73108000000747572746c6531000e000000747572746c65315f616865616400000000000000000000000000f03f00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000f03f"
    buffer = bytes.fromhex(hexdata)
    msg_def = """geometry_msgs/TransformStamped[] transforms
================================================================================
MSG: geometry_msgs/TransformStamped
Header header
string child_frame_id # the frame id of the child frame
Transform transform
================================================================================
MSG: std_msgs/Header
time stamp
string frame_id
================================================================================
MSG: geometry_msgs/Transform
Vector3 translation
Quaternion rotation
================================================================================
MSG: geometry_msgs/Vector3
float64 x
float64 y
float64 z
================================================================================
MSG: geometry_msgs/Quaternion
float64 x
float64 y
float64 z
float64 w
"""
    defs = parse(msg_def, ros2=True)
    reader = MessageReader(defs)
    read = reader.read_message(buffer)
    assert read == {
        "transforms": [
            {
                "header": {
                    "stamp": {"sec": 1638821672, "nanosec": 836230505},
                    "frame_id": "turtle1",
                },
                "child_frame_id": "turtle1_ahead",
                "transform": {
                    "translation": {"x": 1, "y": 0, "z": 0},
                    "rotation": {"x": 0, "y": 0, "z": 0, "w": 1},
                },
            }
        ]
    }


def test_ros2idl_tf_message() -> None:
    hexdata = "0001000001000000286fae6169ddd73108000000747572746c6531000e000000747572746c65315f616865616400000000000000000000000000f03f00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000f03f"
    buffer = bytes.fromhex(hexdata)
    msg_def = """================================================================================
IDL: geometry_msgs/msg/Transforms

module geometry_msgs {
  module msg {
    struct Transforms {
      sequence<geometry_msgs::msg::TransformStamped> transforms;
    };
  };
};
================================================================================
IDL: geometry_msgs/msg/TransformStamped

module geometry_msgs {
  module msg {
    struct TransformStamped {
      std_msgs::msg::Header header;
      string child_frame_id; // the frame id of the child frame
      geometry_msgs::msg::Transform transform;
    };
  };
};
================================================================================
IDL: std_msgs/msg/Header

module std_msgs {
  module msg {
    struct Header {
      builtin_interfaces::Time stamp;
      string frame_id;
    };
  };
};
================================================================================
IDL: geometry_msgs/msg/Transform

module geometry_msgs {
  module msg {
    struct Transform {
      geometry_msgs::msg::Vector3 translation;
      geometry_msgs::msg::Quaternion rotation;
    };
  };
};

================================================================================
IDL: geometry_msgs/msg/Vector3

module geometry_msgs {
  module msg {
    struct Vector3 {
      double x;
      double y;
      double z;
    };
  };
};

================================================================================
IDL: geometry_msgs/msg/Quaternion

module geometry_msgs {
  module msg {
    struct Quaternion {
      double x;
      double y;
      double z;
      double w;
    };
  };
};

================================================================================
IDL: builtin_interfaces/Time
// Normally added when generating idl schemas

module builtin_interfaces {
  struct Time {
    int32 sec;
    uint32 nanosec;
  };
};
"""
    defs = parse_ros2idl(msg_def)
    reader = MessageReader(defs)
    read = reader.read_message(buffer)
    assert read == {
        "transforms": [
            {
                "header": {
                    "stamp": {"sec": 1638821672, "nanosec": 836230505},
                    "frame_id": "turtle1",
                },
                "child_frame_id": "turtle1_ahead",
                "transform": {
                    "translation": {"x": 1.0, "y": 0.0, "z": 0.0},
                    "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                },
            }
        ]
    }


def test_ros2idl_root_selection() -> None:
    data = bytes([0x02])
    buffer = b"\x00\x01\x00\x00" + data
    msg_def = """module a {
  module b {
    const int8 STATUS_ONE = 1;
    const int8 STATUS_TWO = 2;
  };
  struct c {
   int8 status;
  };
};
"""
    defs = parse_ros2idl(msg_def)
    reader = MessageReader(defs)
    read = reader.read_message(buffer)
    assert read == {"status": 2}


def test_union_parsing() -> None:
    idl = """module test {
  union IntOrString switch(uint8) {
    case 0: int32 num;
    case 1: string text;
  };
};"""
    defs = parse_ros2idl(idl)
    reader = MessageReader(defs)

    w = CdrWriter()
    w.uint8(0)
    w.int32(42)
    buffer = w.data
    assert reader.read_message(buffer) == {"discriminator": 0, "num": 42}

    w = CdrWriter()
    w.uint8(1)
    w.string("hello")
    buffer = w.data
    assert reader.read_message(buffer) == {"discriminator": 1, "text": "hello"}


def test_nested_union_parsing() -> None:
    idl = """module test {
  struct Wrapper { IntOrString value; };
  union IntOrString switch(uint8) {
    case 0: int32 num;
    case 1: string text;
  };
};"""
    defs = parse_ros2idl(idl)
    reader = MessageReader(defs)

    w = CdrWriter()
    w.uint8(1)
    w.string("hi")
    buffer = w.data
    assert reader.read_message(buffer) == {"value": {"discriminator": 1, "text": "hi"}}


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


def test_enum_union_parsing() -> None:
    idl = """module test {
  enum Switch { NUM, TEXT };
  union IntOrString switch(Switch) {
    case NUM: int32 num;
    case TEXT: string text;
  };
};"""
    defs = parse_ros2idl(idl)
    reader = MessageReader(defs)

    w = CdrWriter()
    w.uint32(0)
    w.int32(99)
    buffer = w.data
    assert reader.read_message(buffer) == {"discriminator": 0, "num": 99}

    w = CdrWriter()
    w.uint32(1)
    w.string("enum")
    buffer = w.data
    assert reader.read_message(buffer) == {"discriminator": 1, "text": "enum"}


def test_enum_union_parsing_as_string() -> None:
    idl = """module test {
  enum Switch { NUM, TEXT };
  union IntOrString switch(Switch) {
    case NUM: int32 num;
    case TEXT: string text;
  };
};"""
    defs = parse_ros2idl(idl)
    reader = MessageReader(defs, MessageReaderOptions(enumAsString=True))

    w = CdrWriter()
    w.uint32(0)
    w.int32(99)
    buffer = w.data
    assert reader.read_message(buffer) == {"discriminator": "NUM", "num": 99}

    w = CdrWriter()
    w.uint32(1)
    w.string("enum")
    buffer = w.data
    assert reader.read_message(buffer) == {"discriminator": "TEXT", "text": "enum"}


def test_enum_field_as_string() -> None:
    idl = """module test {
  enum Switch { NUM, TEXT };
  struct Bar { Switch mode; };
};"""
    defs = parse_ros2idl(idl)
    reader = MessageReader(defs, MessageReaderOptions(enumAsString=True))

    w = CdrWriter()
    w.uint32(1)
    buffer = w.data
    assert reader.read_message(buffer) == {"mode": "TEXT"}


def test_enum_array_field_as_string() -> None:
    idl = """module test {
  enum Switch { NUM, TEXT };
  struct Bar { Switch mode; sequence<Switch> modes; };
};"""
    defs = parse_ros2idl(idl)
    reader = MessageReader(defs, MessageReaderOptions(enumAsString=True))

    w = CdrWriter()
    w.uint32(0)
    w.uint32(2)
    w.uint32(1)
    w.uint32(0)
    buffer = w.data
    assert reader.read_message(buffer) == {
        "mode": "NUM",
        "modes": ["TEXT", "NUM"],
    }


def test_nested_enum_union_parsing() -> None:
    idl = """module test {
  enum Switch { NUM, TEXT };
  struct Wrapper { IntOrString value; };
  union IntOrString switch(Switch) {
    case NUM: int32 num;
    case TEXT: string text;
  };
};"""
    defs = parse_ros2idl(idl)
    reader = MessageReader(defs)

    w = CdrWriter()
    w.uint32(1)
    w.string("nested")
    buffer = w.data
    assert reader.read_message(buffer) == {
        "value": {"discriminator": 1, "text": "nested"}
    }


def test_union_default_case_uint8() -> None:
    idl = """module test {
  union IntOrString switch(uint8) {
    case 0: int32 num;
    default: string text;
  };
};"""
    defs = parse_ros2idl(idl)
    reader = MessageReader(defs)

    w = CdrWriter()
    w.uint8(1)
    w.string("fallback")
    buffer = w.data
    assert reader.read_message(buffer) == {"discriminator": 1, "text": "fallback"}


def test_enum_union_default_case() -> None:
    idl = """module test {
  enum Switch { NUM, TEXT };
  union IntOrString switch(Switch) {
    case NUM: int32 num;
    default: string text;
  };
};"""
    defs = parse_ros2idl(idl)
    reader = MessageReader(defs)

    w = CdrWriter()
    w.uint32(1)
    w.string("enum default")
    buffer = w.data
    assert reader.read_message(buffer) == {"discriminator": 1, "text": "enum default"}


def test_nested_module_enum_union() -> None:
    idl = """module test {
  module t2_test_msgs {

  enum FooEnum {
    ENUMERATOR1,
    ENUMERATOR2
  };

  union FooUnion switch(FooEnum) {
  case ENUMERATOR1:
    int32 int_value;
  case ENUMERATOR2:
    string<32> string_value;
  };

  module msg {
     @verbatim (language="comment", text=
     "This is a comment about the Bar message")
     struct Bar {
       FooUnion union_value;  // member is a union discriminated by FooEnum
       };
    };
  };

};"""
    defs = parse_ros2idl(idl)
    reader = MessageReader(defs)

    w = CdrWriter()
    w.uint32(1)
    w.string("Hello!")
    buffer = w.data
    assert reader.read_message(buffer) == {
        "union_value": {"discriminator": 1, "string_value": "Hello!"}
    }


def test_nested_module_enum_union_as_string() -> None:
    idl = """module test {
  module t2_test_msgs {

  enum FooEnum {
    ENUMERATOR1,
    ENUMERATOR2
  };

  union FooUnion switch(FooEnum) {
  case ENUMERATOR1:
    int32 int_value;
  case ENUMERATOR2:
    string<32> string_value;
  };

  module msg {
     @verbatim (language="comment", text=
     "This is a comment about the Bar message")
     struct Bar {
       FooUnion union_value;  // member is a union discriminated by FooEnum
       };
    };
  };

};"""
    defs = parse_ros2idl(idl)
    reader = MessageReader(defs, MessageReaderOptions(enumAsString=True))

    w = CdrWriter()
    w.uint32(1)
    w.string("Hello!")
    buffer = w.data
    assert reader.read_message(buffer) == {
        "union_value": {"discriminator": "ENUMERATOR2", "string_value": "Hello!"}
    }


@pytest.mark.parametrize("msg_def", ["wstring field", "wstring[] field"])
def test_wstring_unsupported(msg_def: str) -> None:
    buffer = bytes.fromhex("00010000000000007b000000")
    defs = parse(msg_def, ros2=True)
    reader = MessageReader(defs)
    with pytest.raises(RuntimeError, match="wstring is implementation-defined"):
        reader.read_message(buffer)
