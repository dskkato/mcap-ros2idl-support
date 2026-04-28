import struct

from mcap.reader import make_reader
from mcap.records import Schema
from mcap.writer import Writer

from mcap_ros2idl_support import Ros2DecodeFactory

CDR_LE_V1_HEADER = b"\x00\x01\x00\x00"  # CDR little-endian header (version 1)


def test_decode_factory_integration(tmp_path):
    factory = Ros2DecodeFactory()

    mcap_path = tmp_path / "test.mcap"
    with open(mcap_path, "wb") as f:
        writer = Writer(f)
        writer.start()
        schema_data = b"uint32 value\n"
        schema_id = writer.register_schema("Msg", "ros2msg", schema_data)
        channel_id = writer.register_channel("/test", "cdr", schema_id)
        data = CDR_LE_V1_HEADER + struct.pack("<I", 42)
        writer.add_message(channel_id, 0, data, 0)
        writer.finish()

    with open(mcap_path, "rb") as f:
        reader = make_reader(f, decoder_factories=[factory])
        decoded = list(reader.iter_decoded_messages())
        assert len(decoded) == 1
        _, _, _, msg = decoded[0]
        assert msg == {"value": 42}


def test_decode_factory_enum_as_string(tmp_path):
    factory = Ros2DecodeFactory(enum_as_string=True)

    mcap_path = tmp_path / "test_enum.mcap"
    with open(mcap_path, "wb") as f:
        writer = Writer(f)
        writer.start()
        schema_data = (
            b"module example { enum Status { UNKNOWN, OK }; "
            b"struct Msg { example::Status status; }; };"
        )
        schema_id = writer.register_schema("example/Msg", "ros2idl", schema_data)
        channel_id = writer.register_channel("/test", "cdr", schema_id)
        import struct

        data = CDR_LE_V1_HEADER + struct.pack("<I", 1)
        writer.add_message(channel_id, 0, data, 0)
        writer.finish()

    with open(mcap_path, "rb") as f:
        reader = make_reader(f, decoder_factories=[factory])
        decoded = list(reader.iter_decoded_messages())
        assert len(decoded) == 1
        _, _, _, msg = decoded[0]
        assert msg == {"status": "OK"}


def test_decode_factory_uses_schema_name_as_root_for_ros2idl(tmp_path):
    factory = Ros2DecodeFactory()

    mcap_path = tmp_path / "test_nested_root.mcap"
    with open(mcap_path, "wb") as f:
        writer = Writer(f)
        writer.start()
        schema_data = (
            b"module example { "
            b"struct Helper { uint32 nested; }; "
            b"struct Msg { uint32 prefix; Helper helper; uint32 suffix; }; "
            b"};"
        )
        schema_id = writer.register_schema("example/Msg", "ros2idl", schema_data)
        channel_id = writer.register_channel("/test", "cdr", schema_id)
        data = CDR_LE_V1_HEADER + struct.pack("<III", 1, 2, 3)
        writer.add_message(channel_id, 0, data, 0)
        writer.finish()

    with open(mcap_path, "rb") as f:
        reader = make_reader(f, decoder_factories=[factory])
        decoded = list(reader.iter_decoded_messages())
        assert len(decoded) == 1
        _, _, _, msg = decoded[0]
        assert msg == {"prefix": 1, "helper": {"nested": 2}, "suffix": 3}


def test_decoder_caches_unsupported_schema(monkeypatch):
    factory = Ros2DecodeFactory()
    schema = Schema(
        id=1,
        name="example/Invalid",
        encoding="unknown",
        data=b"",
    )

    assert factory.decoder_for("cdr", schema) is None

    def fail(*args, **kwargs):  # pragma: no cover - fail if called
        raise AssertionError("parse_ros2idl called again")

    monkeypatch.setattr("mcap_ros2idl_support.decode_factory.parse_ros2idl", fail)

    assert factory.decoder_for("cdr", schema) is None
