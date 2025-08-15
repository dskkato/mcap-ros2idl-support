from __future__ import annotations

from array import array

import pytest

from mcap_ros2idl_support.cdr.encapsulation_kind import EncapsulationKind
from mcap_ros2idl_support.cdr.reader import CdrReader
from mcap_ros2idl_support.cdr.writer import CdrWriter

CDR2_KINDS = {
    EncapsulationKind.CDR2_BE,
    EncapsulationKind.CDR2_LE,
    EncapsulationKind.PL_CDR2_BE,
    EncapsulationKind.PL_CDR2_LE,
    EncapsulationKind.DELIMITED_CDR2_BE,
    EncapsulationKind.DELIMITED_CDR2_LE,
    EncapsulationKind.RTPS_CDR2_BE,
    EncapsulationKind.RTPS_CDR2_LE,
    EncapsulationKind.RTPS_PL_CDR2_BE,
    EncapsulationKind.RTPS_PL_CDR2_LE,
    EncapsulationKind.RTPS_DELIMITED_CDR2_BE,
    EncapsulationKind.RTPS_DELIMITED_CDR2_LE,
}

TF2_MSG_TFMESSAGE = (
    "0001000001000000cce0d158f08cf9060a000000626173655f6c696e6b0000000600000072616461"
    "72000000ae47e17a14ae0e4000000000000000000000000000000000000000000000000000000000"
    "000000000000000000000000000000000000f03f"
)


def write_example_message(writer: CdrWriter) -> None:
    # geometry_msgs/TransformStamped[] transforms
    writer.sequenceLength(1)
    # std_msgs/Header header
    # time stamp
    writer.uint32(1490149580)  # uint32 sec
    writer.uint32(117017840)  # uint32 nsec
    writer.string("base_link")  # string frame_id
    writer.string("radar")  # string child_frame_id
    # geometry_msgs/Transform transform
    # geometry_msgs/Vector3 translation
    writer.float64(3.835)  # float64 x
    writer.float64(0)  # float64 y
    writer.float64(0)  # float64 z
    # geometry_msgs/Quaternion rotation
    writer.float64(0)  # float64 x
    writer.float64(0)  # float64 y
    writer.float64(0)  # float64 z
    writer.float64(1)  # float64 w


@pytest.mark.parametrize("kwargs", [{"size": 100}, {"buffer": bytearray(100)}])
@pytest.mark.parametrize("kind", [EncapsulationKind.CDR_LE, EncapsulationKind.CDR2_LE])
def test_serializes_example_message_with_preallocation(
    kind: EncapsulationKind,
    kwargs: dict,
) -> None:
    writer = CdrWriter(kind=kind, **kwargs)
    write_example_message(writer)
    assert writer.size == 100
    expected = bytearray.fromhex(TF2_MSG_TFMESSAGE)
    expected[1] = kind.value
    assert writer.data == bytes(expected)


def test_serializes_example_message_without_preallocation() -> None:
    writer = CdrWriter()
    write_example_message(writer)
    assert writer.size == 100
    assert writer.data.hex() == TF2_MSG_TFMESSAGE


@pytest.mark.parametrize("kind", list(EncapsulationKind))
def test_round_trips_all_primitive_types(kind: EncapsulationKind) -> None:
    writer = CdrWriter(kind=kind)
    writer.int8(-1)
    writer.uint8(2)
    writer.int16(-300)
    writer.uint16(400)
    writer.int32(-500_000)
    writer.uint32(600_000)
    writer.int64(-7_000_000_001)
    writer.uint64(8_000_000_003)
    writer.uint16BE(0x1234)
    writer.uint32BE(0x12345678)
    writer.uint64BE(0x123456789ABCDEF0)
    writer.float32(-9.14)
    writer.float64(1.7976931348623158e100)
    writer.string("abc")
    writer.sequenceLength(42)
    data = writer.data
    assert len(data) == (76 if kind in CDR2_KINDS else 80)

    reader = CdrReader(data)
    assert reader.int8() == -1
    assert reader.uint8() == 2
    assert reader.int16() == -300
    assert reader.uint16() == 400
    assert reader.int32() == -500_000
    assert reader.uint32() == 600_000
    assert reader.int64() == -7_000_000_001
    assert reader.uint64() == 8_000_000_003
    assert reader.uint16_be() == 0x1234
    assert reader.uint32_be() == 0x12345678
    assert reader.uint64_be() == 0x123456789ABCDEF0
    assert reader.float32() == pytest.approx(-9.14)
    assert reader.float64() == pytest.approx(1.7976931348623158e100)
    assert reader.string() == "abc"
    assert reader.sequence_length() == 42


@pytest.mark.parametrize("kind", list(EncapsulationKind))
def test_round_trips_all_array_types(kind: EncapsulationKind) -> None:
    writer = CdrWriter(kind=kind)
    writer.int8Array([-128, 127, 3], True)
    writer.uint8Array([0, 255, 3], True)
    writer.int16Array([-32768, 32767, -3], True)
    writer.uint16Array([0, 65535, 3], True)
    writer.int32Array([-2147483648, 2147483647, 3], True)
    writer.uint32Array([0, 4294967295, 3], True)
    writer.int64Array([-9223372036854775808, 9223372036854775807, 3], True)
    writer.uint64Array([0, 18446744073709551615, 3], True)

    reader = CdrReader(writer.data)
    assert list(reader.int8_array()) == [-128, 127, 3]
    assert list(reader.uint8_array()) == [0, 255, 3]
    assert list(reader.int16_array()) == [-32768, 32767, -3]
    assert list(reader.uint16_array()) == [0, 65535, 3]
    assert list(reader.int32_array()) == [-2147483648, 2147483647, 3]
    assert list(reader.uint32_array()) == [0, 4294967295, 3]
    assert list(reader.int64_array()) == [-9223372036854775808, 9223372036854775807, 3]
    assert list(reader.uint64_array()) == [0, 18446744073709551615, 3]


@pytest.mark.parametrize("kind", [EncapsulationKind.CDR_LE, EncapsulationKind.CDR_BE])
@pytest.mark.parametrize(
    "method, values, typecode",
    [
        ("int16Array", [-32768, 0, 32767], "h"),
        ("uint16Array", [0, 1, 65535], "H"),
        ("int32Array", [-2147483648, 0, 2147483647], "i"),
        ("uint32Array", [0, 1, 0xFFFFFFFF], "I"),
        ("int64Array", [-9223372036854775808, 0, 9223372036854775807], "q"),
        ("uint64Array", [0, 1, 0xFFFFFFFFFFFFFFFF], "Q"),
        ("float32Array", [0.0, 1.5, -2.25], "f"),
        ("float64Array", [0.0, 1.5, -2.25], "d"),
    ],
)
@pytest.mark.parametrize("container", ["array", "memoryview", "list"])
def test_array_bulk_and_fallback_paths(
    kind: EncapsulationKind,
    method: str,
    values: list,
    typecode: str,
    container: str,
) -> None:
    writer = CdrWriter(kind=kind)
    if container == "array":
        data = array(typecode, values)
    elif container == "memoryview":
        data = memoryview(array(typecode, values))
    else:
        data = list(values)
    getattr(writer, method)(data, True)
    reader = CdrReader(writer.data)
    read_method = method.replace("Array", "_array")
    result = getattr(reader, read_method)()
    result = list(result)
    assert result == values


def test_writes_parameter_list_and_sentinel_header() -> None:
    writer = CdrWriter(kind=EncapsulationKind.PL_CDR_LE)
    writer.uint8(0x42)
    writer.sentinelHeader()
    assert writer.data.hex() == "0003000042000000023f0000"


def test_aligns_cdr1() -> None:
    writer = CdrWriter()
    writer.align(0)
    assert writer.data.hex() == "00010000"
    writer.align(8)
    assert writer.data.hex() == "00010000"
    writer.uint8(1)
    writer.align(8)
    writer.uint32(2)
    writer.align(4)
    assert writer.data.hex() == "00010000010000000000000002000000"


def test_aligns_cdr2() -> None:
    writer = CdrWriter(kind=EncapsulationKind.RTPS_PL_CDR2_LE)
    writer.align(0)
    assert writer.data.hex() == "000b0000"
    writer.align(4)
    assert writer.data.hex() == "000b0000"
    writer.uint8(1)
    writer.align(4)
    writer.uint32(2)
    writer.align(4)
    assert writer.data.hex() == "000b00000100000002000000"


def test_aligns_8byte_values_in_pl_cdr_without_emheader() -> None:
    writer = CdrWriter(kind=EncapsulationKind.PL_CDR_LE)
    writer.uint32(1)
    writer.uint64(0x0F)
    assert writer.data.hex() == "0003000001000000000000000f00000000000000"


def test_emheader_resets_origin_for_alignment() -> None:
    writer = CdrWriter(kind=EncapsulationKind.PL_CDR_LE)
    writer.emHeader(True, 5, 8)
    writer.uint64(0x0F)
    assert writer.data.hex() == "00030000054008000f00000000000000"
