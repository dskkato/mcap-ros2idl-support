"""Tests for :mod:`cdr.size_calculator`."""

from __future__ import annotations

from mcap_ros2idl_support.cdr.size_calculator import CdrSizeCalculator


def test_calculates_example_message() -> None:
    """Ensure example tf2_msgs/TFMessage size matches reference."""
    calc = CdrSizeCalculator()

    # geometry_msgs/TransformStamped[] transforms
    calc.sequence_length()
    # std_msgs/Header header
    # time stamp
    calc.uint32()  # uint32 sec
    calc.uint32()  # uint32 nsec
    calc.string(len("base_link"))  # string frame_id
    calc.string(len("radar"))  # string child_frame_id
    # geometry_msgs/Transform transform
    # geometry_msgs/Vector3 translation
    calc.float64()  # float64 x
    calc.float64()  # float64 y
    calc.float64()  # float64 z
    # geometry_msgs/Quaternion rotation
    calc.float64()  # float64 x
    calc.float64()  # float64 y
    calc.float64()  # float64 z
    calc.float64()  # float64 w

    assert calc.size == 100


def test_string_accounts_for_length_and_terminator() -> None:
    calc = CdrSizeCalculator()
    assert calc.size == 4
    assert calc.string(0) == 9  # 4 bytes length + 1 byte terminator
    assert calc.size == 9


def test_sequence_length_alignment() -> None:
    calc = CdrSizeCalculator()
    calc.int8()  # misalign the offset
    assert calc.sequence_length() == 12  # 3 padding bytes + 4 length bytes


def test_all_data_types_without_padding() -> None:
    """Offsets match Node.js implementation when no padding is required."""
    calc = CdrSizeCalculator()
    offset = 4  # initial encapsulation header
    assert calc.size == offset

    offset += 8
    assert calc.int64() == offset

    offset += 8
    assert calc.uint64() == offset

    offset += 8
    assert calc.float64() == offset

    offset += 4
    assert calc.int32() == offset

    offset += 4
    assert calc.uint32() == offset

    offset += 4
    assert calc.float32() == offset

    offset += 4
    assert calc.sequence_length() == offset

    offset += 2
    assert calc.int16() == offset

    offset += 2
    assert calc.uint16() == offset

    offset += 1
    assert calc.int8() == offset

    offset += 1
    assert calc.uint8() == offset

    offset += 2
    assert calc.uint16() == offset

    offset += 4 + 3 + 1  # length prefix, string data, null terminator
    assert calc.string(len("abc")) == offset


def test_all_data_types_with_padding() -> None:
    """Offsets match Node.js implementation when padding is required."""
    calc = CdrSizeCalculator()

    assert calc.size == 4
    assert calc.int8() == 5
    assert calc.int64() == 20
    assert calc.uint16() == 22
    assert calc.uint32() == 28
    assert calc.string(0) == 33
    assert calc.int16() == 36
    assert calc.uint8() == 37
    assert calc.float32() == 44
    assert calc.uint8() == 45
    assert calc.float64() == 60
