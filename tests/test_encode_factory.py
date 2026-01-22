import struct

import pytest
from mcap.records import Schema

from mcap_ros2idl_support.encode_factory import Ros2EncodeFactory


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
