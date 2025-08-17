# flake8: noqa
import struct

import pytest

from mcap_ros2idl_support.ros2idl_parser import parse_ros2idl
from mcap_ros2idl_support.rosmsg2_serialization import MessageWriter
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
    writer = MessageWriter(defs)
    for val in (min_val, max_val):
        expected = b"\x00\x01\x00\x00" + struct.pack(fmt, val)
        written = writer.write_message({"sample": val})
        assert written == expected
        assert writer.calculate_byte_size({"sample": val}) == len(expected)


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
    writer = MessageWriter(defs)
    expected = b"\x00\x01\x00\x00" + struct.pack(fmt, val)
    written = writer.write_message({"sample": val})
    assert written == expected
    assert writer.calculate_byte_size({"sample": val}) == len(expected)


def test_time_and_duration_fields() -> None:
    msg_def = """builtin_interfaces/msg/Time stamp
================================================================================
MSG: builtin_interfaces/msg/Time
int32 sec
uint32 nanosec
"""
    defs = parse(msg_def, ros2=True)
    writer = MessageWriter(defs)
    message = {"stamp": {"sec": 0, "nsec": 1}}
    expected = b"\x00\x01\x00\x00" + struct.pack("<iI", 0, 1)
    written = writer.write_message(message)
    assert written == expected

    msg_def = """builtin_interfaces/msg/Duration stamp
================================================================================
MSG: builtin_interfaces/msg/Duration
int32 sec
uint32 nanosec
"""
    defs = parse(msg_def, ros2=True)
    writer = MessageWriter(defs)
    message = {"stamp": {"sec": 0, "nsec": 1}}
    expected = b"\x00\x01\x00\x00" + struct.pack("<iI", 0, 1)
    written = writer.write_message(message)
    assert written == expected


@pytest.mark.parametrize(
    "msg_def,message,expected",
    [
        (
            "int32[] arr",
            {"arr": [3, 7]},
            b"\x00\x01\x00\x00" + struct.pack("<I", 2) + struct.pack("<2i", 3, 7),
        ),
        (
            "uint8 blank\nint32[] arr",
            {"blank": 0, "arr": [3, 7]},
            b"\x00\x01\x00\x00"
            + b"\x00"
            + b"\x00\x00\x00"
            + struct.pack("<I", 2)
            + struct.pack("<2i", 3, 7),
        ),
        (
            "float32[2] arr",
            {"arr": [5.5, 6.5]},
            b"\x00\x01\x00\x00" + struct.pack("<2f", 5.5, 6.5),
        ),
        (
            "uint8 blank\nfloat32[2] arr",
            {"blank": 0, "arr": [5.5, 6.5]},
            b"\x00\x01\x00\x00"
            + b"\x00"
            + b"\x00\x00\x00"
            + struct.pack("<2f", 5.5, 6.5),
        ),
        (
            "float32[] arr",
            {"arr": [5.5, 6.5]},
            b"\x00\x01\x00\x00" + struct.pack("<I", 2) + struct.pack("<2f", 5.5, 6.5),
        ),
        (
            "uint8 blank\nfloat32[] arr",
            {"blank": 0, "arr": [5.5, 6.5]},
            b"\x00\x01\x00\x00"
            + b"\x00"
            + b"\x00\x00\x00"
            + struct.pack("<I", 2)
            + struct.pack("<2f", 5.5, 6.5),
        ),
        (
            "float32[] first\nfloat32[] second",
            {"first": [5.5, 6.5], "second": [5.5, 6.5]},
            b"\x00\x01\x00\x00"
            + struct.pack("<I", 2)
            + struct.pack("<2f", 5.5, 6.5)
            + struct.pack("<I", 2)
            + struct.pack("<2f", 5.5, 6.5),
        ),
        (
            "string sample",
            {"sample": ""},
            b"\x00\x01\x00\x00" + _serialize_string(""),
        ),
        (
            "string sample",
            {"sample": "some string"},
            b"\x00\x01\x00\x00" + _serialize_string("some string"),
        ),
        (
            "int8[4] first",
            {"first": [0, -1, -128, 127]},
            b"\x00\x01\x00\x00" + bytes([0x00, 0xFF, 0x80, 0x7F]),
        ),
        (
            "int8[] first",
            {"first": [0, -1, -128, 127]},
            b"\x00\x01\x00\x00"
            + struct.pack("<I", 4)
            + bytes([0x00, 0xFF, 0x80, 0x7F]),
        ),
        (
            "uint8[4] first",
            {"first": [0, 255, 128, 127]},
            b"\x00\x01\x00\x00" + bytes([0x00, 0xFF, 0x80, 0x7F]),
        ),
        (
            "string[2] first",
            {"first": ["one", "longer string"]},
            b"\x00\x01\x00\x00"
            + _serialize_string("one")
            + _serialize_string("longer string"),
        ),
        (
            "string[] first",
            {"first": ["one", "longer string"]},
            b"\x00\x01\x00\x00"
            + struct.pack("<I", 2)
            + _serialize_string("one")
            + _serialize_string("longer string"),
        ),
        (
            "int8 first\nint8 second",
            {"first": -128, "second": 127},
            b"\x00\x01\x00\x00" + bytes([0x80, 0x7F]),
        ),
        (
            "string first\nint8 second",
            {"first": "some string", "second": -128},
            b"\x00\x01\x00\x00" + _serialize_string("some string") + bytes([0x80]),
        ),
        (
            """CustomType custom
================================================================================
MSG: custom_type/CustomType
uint8 first
""",
            {"custom": {"first": 0x02}},
            b"\x00\x01\x00\x00" + bytes([0x02]),
        ),
        (
            """CustomType[3] custom
================================================================================
MSG: custom_type/CustomType
uint8 first
""",
            {"custom": [{"first": 0x02}, {"first": 0x03}, {"first": 0x04}]},
            b"\x00\x01\x00\x00" + bytes([0x02, 0x03, 0x04]),
        ),
        (
            """CustomType[] custom
================================================================================
MSG: custom_type/CustomType
uint8 first
""",
            {"custom": [{"first": 0x02}, {"first": 0x03}, {"first": 0x04}]},
            b"\x00\x01\x00\x00" + struct.pack("<I", 3) + bytes([0x02, 0x03, 0x04]),
        ),
        (
            "int8 STATUS_ONE = 1\nint8 STATUS_TWO = 2\nint8 status",
            {"status": 2},
            b"\x00\x01\x00\x00" + bytes([0x02]),
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
            {
                "custom": [
                    {"another": {"field": 0x02}},
                    {"another": {"field": 0x03}},
                    {"another": {"field": 0x04}},
                ]
            },
            b"\x00\x01\x00\x00" + struct.pack("<I", 3) + bytes([0x02, 0x03, 0x04]),
        ),
    ],
)
def test_misc_cases(msg_def: str, message: dict, expected: bytes) -> None:
    defs = parse(msg_def, ros2=True)
    writer = MessageWriter(defs)
    written = writer.write_message(message)
    assert written == expected
    assert writer.calculate_byte_size(message) == len(expected)


def test_log_message() -> None:
    hexdata = "00010000fb65865e80faae0614000000120000006d696e696d616c5f7075626c69736865720000001e0000005075626c697368696e673a202748656c6c6f2c20776f726c64212030270000004c0000002f6f70742f726f73325f77732f656c6f7175656e742f7372632f726f73322f6578616d706c65732f72636c6370702f6d696e696d616c5f7075626c69736865722f6c616d6264612e637070000b0000006f70657261746f722829000026000000"
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
    writer = MessageWriter(defs)
    message = {
        "stamp": {"sec": 1585866235, "nsec": 112130688},
        "level": 20,
        "name": "minimal_publisher",
        "msg": "Publishing: 'Hello, world! 0'",
        "file": "/opt/ros2_ws/eloquent/src/ros2/examples/rclcpp/minimal_publisher/lambda.cpp",
        "function": "operator()",
        "line": 38,
    }
    written = writer.write_message(message)
    assert written == buffer
    assert writer.calculate_byte_size(message) == len(buffer)


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
builtin_interfaces/Time stamp
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
    writer = MessageWriter(defs)
    message = {
        "transforms": [
            {
                "header": {
                    "stamp": {"sec": 1638821672, "nsec": 836230505},
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
    written = writer.write_message(message)
    assert written == buffer
    assert writer.calculate_byte_size(message) == len(buffer)


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
    writer = MessageWriter(defs)
    message = {
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
    written = writer.write_message(message)
    assert written == buffer
    assert writer.calculate_byte_size(message) == len(buffer)


def test_empty_message_and_empty_fields() -> None:
    defs = parse("", ros2=True)
    writer = MessageWriter(defs)
    assert writer.write_message({}) == b"\x00\x01\x00\x00\x00"

    msg_def = """std_msgs/msg/Empty empty
uint8 uint_8_field
================================================================================
MSG: std_msgs/msg/Empty
"""
    defs = parse(msg_def, ros2=True)
    writer = MessageWriter(defs)
    message = {"uint_8_field": 123}
    expected = bytes.fromhex("00010000007b")
    assert writer.write_message(message) == expected

    msg_def = """std_msgs/msg/Empty empty
int32 int_32_field
================================================================================
MSG: std_msgs/msg/Empty
"""
    defs = parse(msg_def, ros2=True)
    writer = MessageWriter(defs)
    message = {"int_32_field": 16777339}
    expected = bytes.fromhex("00010000000000007b000001")
    assert writer.write_message(message) == expected

    msg_def = """custom_msgs/msg/Nothing empty
int32 int_32_field
================================================================================
MSG: custom_msgs/msg/Nothing
int32 EXAMPLE=123
"""
    defs = parse(msg_def, ros2=True)
    writer = MessageWriter(defs)
    message = {"int_32_field": 16777339}
    expected = bytes.fromhex("00010000000000007b000001")
    assert writer.write_message(message) == expected


def test_ros2idl_root_selection() -> None:
    message = {"status": 2}
    message_bin = bytes([0x02])
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
    writer = MessageWriter(defs)
    expected = b"\x00\x01\x00\x00" + message_bin
    written = writer.write_message(message)
    assert written == expected
    assert writer.calculate_byte_size(message) == len(expected)


@pytest.mark.parametrize(
    "type_,length,expected_len",
    [("float64", 10, 84), ("time", 10, 84), ("uint8", 5, 9)],
)
def test_default_initialization_fixed_arrays(
    type_: str, length: int, expected_len: int
) -> None:
    msg_def = f"{type_}[{length}] array"
    defs = parse(msg_def, ros2=True)
    writer = MessageWriter(defs)
    written = writer.write_message({})
    assert len(written) == expected_len


def test_fixed_array_size_validation() -> None:
    from array import array as arr

    msg_def = "float64[10] array"
    defs = parse(msg_def, ros2=True)
    writer = MessageWriter(defs)
    with pytest.raises(ValueError):
        writer.write_message({"array": []})
    with pytest.raises(ValueError):
        writer.write_message({"array": arr("d")})
    with pytest.raises(ValueError):
        writer.write_message({"array": arr("d", [0] * 5)})
    writer.write_message({"array": arr("d", [0] * 10)})
    writer.write_message({"array": [0] * 10})


@pytest.mark.parametrize("msg_def", ["wstring field", "wstring[10] field"])
def test_wstring_unsupported(msg_def: str) -> None:
    defs = parse(msg_def, ros2=True)
    writer = MessageWriter(defs)
    with pytest.raises(RuntimeError, match="wstring is implementation-defined"):
        writer.write_message({"field": []})
