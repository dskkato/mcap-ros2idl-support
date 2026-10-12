"""Native boundary regressions not covered by the original reader tests."""

import struct

import pytest

from mcap_ros2idl_support.rosmsg import parse
from mcap_ros2idl_support.rosmsg2_serialization import MessageReader


def test_big_endian_numeric_arrays():
    reader = MessageReader(parse("int16[] values\nfloat64[] weights", ros2=True))
    data = b"\x00\x00\x00\x00" + struct.pack(">IhhIdd", 2, -3, 4, 2, 1.5, -2.0)
    # First double starts at offset 16 (12 relative to the CDR origin).
    data = data[:16] + b"\x00" * 4 + data[16:]
    assert reader.read_message(data) == {"values": [-3, 4], "weights": [1.5, -2.0]}


@pytest.mark.parametrize(
    "data", [b"", b"\x00\x01\x00\x00", b"\x00\x01\x00\x00\xff\xff\xff\xff"]
)
def test_truncated_or_oversized_sequence(data):
    reader = MessageReader(parse("uint64[] values", ros2=True))
    with pytest.raises(ValueError):
        reader.read_message(data)


def test_zero_length_fixed_array_does_not_read_sequence_length():
    reader = MessageReader(parse("uint8[0] values\nuint32 next", ros2=True))
    assert reader.read_message(b"\x00\x01\x00\x00" + struct.pack("<I", 42)) == {
        "values": [],
        "next": 42,
    }


@pytest.mark.parametrize("buffer_type", [bytes, bytearray, memoryview])
def test_buffer_inputs(buffer_type):
    reader = MessageReader(parse("uint32 value", ros2=True))
    assert reader.read_message(
        buffer_type(b"\x00\x01\x00\x00" + struct.pack("<I", 42))
    ) == {"value": 42}


def test_plain_xcdr2_uses_four_byte_double_alignment():
    reader = MessageReader(parse("uint32 value\nfloat64 weight", ros2=True))
    assert reader.read_message(b"\x00\x07\x00\x00" + struct.pack("<Id", 42, 1.5)) == {
        "value": 42,
        "weight": 1.5,
    }


def test_parameter_list_encoding_is_rejected():
    reader = MessageReader(parse("uint32 value", ros2=True))
    with pytest.raises(ValueError, match="Unsupported CDR encapsulation"):
        reader.read_message(b"\x00\x03\x00\x00" + struct.pack("<I", 42))


@pytest.mark.parametrize(
    "declaration, payload, expected",
    [
        ("uint8[] data", struct.pack("<I", 3) + b"abc", b"abc"),
        ("uint8[3] data", b"abc", b"abc"),
        ("uint8[] data", struct.pack("<I", 0), b""),
    ],
)
def test_bytes_array_mode(declaration, payload, expected):
    from mcap_ros2idl_support.rosmsg2_serialization import MessageReaderOptions

    reader = MessageReader(
        parse(declaration, ros2=True), MessageReaderOptions(arrayMode="bytes")
    )
    assert reader.read_message(b"\x00\x01\x00\x00" + payload) == {"data": expected}


def test_factory_array_modes():
    from mcap.records import Schema

    from mcap_ros2idl_support import Ros2DecodeFactory

    schema = Schema(id=1, name="Msg", encoding="ros2msg", data=b"uint8[] data")
    payload = b"\x00\x01\x00\x00" + struct.pack("<I", 3) + b"abc"
    assert Ros2DecodeFactory().decoder_for("cdr", schema)(payload) == {"data": b"abc"}
    assert Ros2DecodeFactory(array_mode="list").decoder_for("cdr", schema)(payload) == {
        "data": [97, 98, 99]
    }
    with pytest.raises(ValueError, match="array_mode"):
        Ros2DecodeFactory(array_mode="invalid")
