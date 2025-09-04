import pytest

from mcap_ros2idl_support.omgidl_parser.parse import Constant, Struct, parse_idl


def test_forward_constant_reference() -> None:
    source = """
    const long A = B + 1;
    const long B = 2;
    """
    definitions = parse_idl(source)
    consts = {d.name: d for d in definitions if isinstance(d, Constant)}
    assert consts["A"].value == 3
    assert consts["B"].value == 2


def test_forward_sequence_bound() -> None:
    source = """
    struct Foo { sequence<long, SIZE> data; };
    const long SIZE = 5;
    """
    definitions = parse_idl(source)
    struct = next(d for d in definitions if isinstance(d, Struct))
    field = struct.fields[0]
    assert field.sequence_bound == 5


def test_unknown_identifier_raises() -> None:
    source = "const long A = B + 1;"
    with pytest.raises(ValueError):
        parse_idl(source)
