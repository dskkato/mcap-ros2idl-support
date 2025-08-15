from __future__ import annotations

import math
from typing import Sequence

import pytest

from mcap_ros2idl_support.cdr.encapsulation_kind import EncapsulationKind
from mcap_ros2idl_support.cdr.reader import CdrReader
from mcap_ros2idl_support.cdr.writer import CdrWriter

TF2_MSG_TFMESSAGE = (
    "0001000001000000cce0d158f08cf9060a000000626173655f6c696e6b0000000600000072616461"
    "72000000ae47e17a14ae0e4000000000000000000000000000000000000000000000000000000000"
    "000000000000000000000000000000000000f03f"
)


def test_parses_example_tf2_message() -> None:
    data = bytes.fromhex(TF2_MSG_TFMESSAGE)
    reader = CdrReader(data)
    assert reader.decoded_bytes == 4

    # geometry_msgs/TransformStamped[] transforms
    assert reader.sequence_length() == 1
    # std_msgs/Header header
    # time stamp
    assert reader.uint32() == 1490149580  # uint32 sec
    assert reader.uint32() == 117017840  # uint32 nsec
    assert reader.string() == "base_link"  # string frame_id
    assert reader.string() == "radar"  # string child_frame_id
    # geometry_msgs/Transform transform
    # geometry_msgs/Vector3 translation
    assert reader.float64() == pytest.approx(3.835)  # float64 x
    assert reader.float64() == pytest.approx(0)  # float64 y
    assert reader.float64() == pytest.approx(0)  # float64 z
    # geometry_msgs/Quaternion rotation
    assert reader.float64() == pytest.approx(0)  # float64 x
    assert reader.float64() == pytest.approx(0)  # float64 y
    assert reader.float64() == pytest.approx(0)  # float64 z
    assert reader.float64() == pytest.approx(1)  # float64 w

    assert reader.offset == len(data)
    assert reader.kind == EncapsulationKind.CDR_LE
    assert reader.decoded_bytes == len(data)
    assert reader.byte_length == len(data)


def test_reads_big_endian_values() -> None:
    data = bytes.fromhex("000100001234000056789abcdef0000000000000")
    reader = CdrReader(data)
    assert reader.uint16_be() == 0x1234
    assert reader.uint32_be() == 0x56789ABC
    assert reader.uint64_be() == 0xDEF0000000000000


def test_seeks_absolute_and_relative_positions() -> None:
    data = bytes.fromhex(TF2_MSG_TFMESSAGE)
    reader = CdrReader(data)

    reader.seek_to(4 + 4 + 4 + 4 + 4 + 10 + 4 + 6)
    assert reader.float64() == pytest.approx(3.835)

    reader.seek_to(4 + 4 + 4 + 4 + 4 + 10 + 4 + 3)
    assert reader.float64() == pytest.approx(3.835)

    reader.seek(-8)
    assert reader.float64() == pytest.approx(3.835)
    assert reader.float64() == pytest.approx(0)


@pytest.mark.parametrize(
    "getter,setter,expected",
    [
        ("int8_array", "int8", [-128, 127, 3]),
        ("uint8_array", "uint8", [0, 255, 3]),
        ("int16_array", "int16", [-32768, 32767, -3]),
        ("uint16_array", "uint16", [0, 65535, 3]),
        ("int32_array", "int32", [-2147483648, 2147483647, 3]),
        ("uint32_array", "uint32", [0, 4294967295, 3]),
    ],
)
def test_reads_int_arrays(getter: str, setter: str, expected: list[int]) -> None:
    writer = CdrWriter()
    _write_array(writer, setter, expected)

    reader = CdrReader(writer.data)
    array = getattr(reader, getter)()
    assert list(array) == expected


@pytest.mark.parametrize(
    "getter,setter,expected,num_digits",
    [
        ("float32_array", "float32", [-3.835, 0, math.pi], 6),
        ("float64_array", "float64", [-3.835, 0, math.pi], 15),
        (
            "float64_array",
            "float64",
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, -0.123456789121212121212],
            15,
        ),
    ],
)
def test_reads_float_arrays(
    getter: str, setter: str, expected: list[float], num_digits: int
) -> None:
    writer = CdrWriter()
    _write_array(writer, setter, expected)

    reader = CdrReader(writer.data)
    array = getattr(reader, getter)()
    _assert_close_list(array, expected, num_digits)


@pytest.mark.parametrize(
    "getter,setter,expected",
    [
        (
            "int64_array",
            "int64",
            [-9223372036854775808, 9223372036854775807, 3],
        ),
        (
            "uint64_array",
            "uint64",
            [0, 18446744073709551615, 3],
        ),
        ("uint64_array", "uint64", list(range(1, 13))),
    ],
)
def test_reads_bigint_arrays(getter: str, setter: str, expected: list[int]) -> None:
    writer = CdrWriter()
    _write_array(writer, setter, expected)

    reader = CdrReader(writer.data)
    array = getattr(reader, getter)()
    assert list(array) == expected


def test_reads_multiple_arrays() -> None:
    writer = CdrWriter()
    writer.float32Array([5.5, 6.5], True)
    writer.float32Array([7.5, 8.5], True)

    reader = CdrReader(writer.data)
    assert _approx_list(reader.float32_array(), [5.5, 6.5], 6)
    assert _approx_list(reader.float32_array(), [7.5, 8.5], 6)
    assert reader.offset == len(writer.data)


def test_reads_string_array() -> None:
    writer = CdrWriter()
    writer.sequenceLength(3)
    writer.string("abc")
    writer.string("")
    writer.string("test string")

    reader = CdrReader(writer.data)
    assert reader.string_array() == ["abc", "", "test string"]
    assert reader.offset == len(writer.data)


@pytest.mark.parametrize(
    "writer_key,reader_key",
    [
        ("int8Array", "int8_array"),
        ("uint8Array", "uint8_array"),
        ("int16Array", "int16_array"),
        ("uint16Array", "uint16_array"),
        ("int32Array", "int32_array"),
        ("uint32Array", "uint32_array"),
        ("int64Array", "int64_array"),
        ("uint64Array", "uint64_array"),
        ("float32Array", "float32_array"),
        ("float64Array", "float64_array"),
    ],
)
def test_handles_alignment_for_empty_arrays(writer_key: str, reader_key: str) -> None:
    writer = CdrWriter()
    getattr(writer, writer_key)([], True)
    assert len(writer.data) == 8

    reader = CdrReader(writer.data)
    assert list(getattr(reader, reader_key)()) == []
    assert reader.offset == len(writer.data)


@pytest.mark.parametrize(
    "getter,setter,values,digits",
    [
        ("int8_array", "int8", [-1, 2, 3], None),
        ("uint8_array", "uint8", [1, 2, 3], None),
        ("int16_array", "int16", [-1, 2, 3], None),
        ("uint16_array", "uint16", [1, 2, 3], None),
        ("int32_array", "int32", [-1, 2, 3], None),
        ("uint32_array", "uint32", [1, 2, 3], None),
        ("int64_array", "int64", [-1, 2, 3], None),
        ("uint64_array", "uint64", [1, 2, 3], None),
        ("float32_array", "float32", [1.5, 2.5, 3.5], 6),
        ("float64_array", "float64", [1.5, 2.5, 3.5], 15),
    ],
)
def test_array_returns_memoryview_zero_copy(
    getter: str, setter: str, values: list[int | float], digits: int | None
) -> None:
    writer = CdrWriter()
    _write_array(writer, setter, values)

    reader = CdrReader(writer.data)
    mv = getattr(reader, getter)()
    assert isinstance(mv, memoryview)
    assert mv.obj is reader._view.obj
    if digits is None:
        assert list(mv) == values
    else:
        _assert_close_list(mv, values, digits)


def test_array_falls_back_on_endian_mismatch() -> None:
    writer = CdrWriter(kind=EncapsulationKind.CDR_BE)
    _write_array(writer, "uint32", [1, 2, 3])

    reader = CdrReader(writer.data)
    arr = reader.uint32_array()
    assert isinstance(arr, list)
    assert arr == [1, 2, 3]


@pytest.mark.parametrize(
    "must_understand,pid,object_size",
    [
        (True, 100, 1),
        (False, 200, 2),
        (False, 1028, 4),
        (False, 65, 8),
        (True, 63, 9),
        (False, 127, 0xFFFF),
        (False, 127, 0x1FFFF),
        (True, 700000, 0xFFFF),
        (False, 700000, 0x1FFFF),
    ],
)
def test_round_trip_xcdr1_em_header(
    must_understand: bool, pid: int, object_size: int
) -> None:
    writer = CdrWriter(kind=EncapsulationKind.PL_CDR_BE)
    writer.emHeader(must_understand, pid, object_size)

    reader = CdrReader(writer.data)
    header = reader.em_header()
    assert header.id == pid
    assert header.object_size == object_size
    assert header.must_understand is must_understand


def test_converts_extended_pid() -> None:
    buffer = bytes.fromhex("00030000017f0800640000004000000000")
    reader = CdrReader(buffer)
    header = reader.em_header()
    assert header.id == 100
    assert header.must_understand is True
    assert header.object_size == 64


def test_read_string_with_preread_length() -> None:
    writer = CdrWriter()
    writer.string("test")

    reader = CdrReader(writer.data)
    length = reader.sequence_length()
    assert reader.string(length) == "test"


def test_em_header_reports_sentinel_read() -> None:
    writer = CdrWriter(kind=EncapsulationKind.PL_CDR_LE)
    writer.sentinelHeader()

    reader = CdrReader(writer.data)
    em_header = reader.em_header()
    assert em_header.read_sentinel_header is True


def test_sentinel_header_errors_on_non_sentinel() -> None:
    writer = CdrWriter(kind=EncapsulationKind.PL_CDR_LE)
    writer.emHeader(False, 100, 4)

    reader = CdrReader(writer.data)
    with pytest.raises(ValueError):
        reader.sentinel_header()


@pytest.mark.parametrize("object_size", [1, 2, 4, 8, 0x7FFFFFFF])
def test_round_trip_dheader(object_size: int) -> None:
    writer = CdrWriter(kind=EncapsulationKind.DELIMITED_CDR2_LE)
    writer.dHeader(object_size)

    reader = CdrReader(writer.data)
    assert reader.d_header() == object_size


@pytest.mark.parametrize(
    "must_understand,pid,object_size",
    [
        (True, 100, 1),
        (False, 200, 2),
        (False, 1028, 4),
        (False, 65, 8),
        (True, 63, 9),
        (False, 127, 0xFFFFFFFF),
    ],
)
def test_round_trip_emheader_without_length_code(
    must_understand: bool, pid: int, object_size: int
) -> None:
    writer = CdrWriter(kind=EncapsulationKind.PL_CDR2_LE)
    writer.emHeader(must_understand, pid, object_size)

    reader = CdrReader(writer.data)
    header = reader.em_header()
    assert header.id == pid
    assert header.object_size == object_size
    assert header.must_understand is must_understand
    assert header.length_code is not None


@pytest.mark.parametrize(
    "must_understand,pid,object_size,length_code",
    [
        (True, 100, 1, 0),
        (False, 200, 2, 1),
        (False, 1028, 4, 2),
        (False, 65, 8, 3),
        (True, 63, 9, 4),
        (False, 127, 0xFFFFFFFF, 5),
        (False, 65, 12, 6),
        (False, 65, 32, 7),
    ],
)
def test_round_trip_emheader_with_length_code(
    must_understand: bool, pid: int, object_size: int, length_code: int
) -> None:
    writer = CdrWriter(kind=EncapsulationKind.PL_CDR2_LE)
    writer.emHeader(must_understand, pid, object_size, length_code)

    reader = CdrReader(writer.data)
    header = reader.em_header()
    assert header.id == pid
    assert header.object_size == object_size
    assert header.must_understand is must_understand
    assert header.length_code == length_code


def test_clone_creates_independent_reader() -> None:
    writer = CdrWriter(kind=EncapsulationKind.CDR2_LE)
    writer.int32(42)
    writer.float64(2.67)

    reader = CdrReader(writer.data)
    assert reader.int32() == 42

    clone = reader.clone()
    assert clone.offset == reader.offset
    assert clone.byte_length == reader.byte_length

    assert reader.float64() == pytest.approx(2.67)
    assert reader.offset == 4 + 4 + 8
    assert clone.offset == 4 + 4
    assert clone.float64() == pytest.approx(2.67)


def test_limit_restricts_readable_range() -> None:
    writer = CdrWriter()
    writer.int32(1)
    writer.int32(2)
    writer.int32(3)

    reader = CdrReader(writer.data)
    assert reader.int32() == 1
    reader.limit(4)
    assert reader.int32() == 2
    assert reader.is_at_end() is True
    with pytest.raises(Exception):
        reader.int32()


def test_limit_throws_if_length_beyond_end() -> None:
    writer = CdrWriter()
    writer.int32(1)
    reader = CdrReader(writer.data)
    with pytest.raises(ValueError):
        reader.limit(1000)


def test_limit_cannot_be_relaxed() -> None:
    writer = CdrWriter()
    writer.int32(1)
    reader = CdrReader(writer.data)
    reader.limit(2)
    reader.limit(1)
    with pytest.raises(ValueError):
        reader.limit(2)


def test_is_at_end() -> None:
    writer = CdrWriter()
    writer.int32(1)
    reader = CdrReader(writer.data)
    assert reader.is_at_end() is False
    reader.int32()
    assert reader.is_at_end() is True


def _write_array(writer: CdrWriter, setter: str, values: list[int | float]) -> None:
    writer.sequenceLength(len(values))
    for value in values:
        getattr(writer, setter)(value)


def _assert_close_list(
    actual: Sequence[float], expected: Sequence[float], digits: int
) -> None:
    assert len(actual) == len(expected)
    for a, e in zip(actual, expected):
        assert a == pytest.approx(e, rel=0, abs=10**-digits)


def _approx_list(
    actual: Sequence[float], expected: Sequence[float], digits: int
) -> bool:
    _assert_close_list(actual, expected, digits)
    return True
