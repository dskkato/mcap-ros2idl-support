import struct
import sys
from pathlib import Path

# Ensure local package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcap.reader import make_reader  # noqa: E402
from mcap.writer import Writer  # noqa: E402

from mcap_ros2idl_support import CdrDecodeFactory, MessageType, SchemaInfo  # noqa: E402

CDR_LE_V1_HEADER = b"\x00\x01\x00\x00"  # CDR little-endian header (version 1)


def test_decode_factory_integration(tmp_path):
    type_map = {
        "Msg": MessageType(
            "Msg",
            [{"name": "value", "type": "uint32", "isComplex": False}],
        )
    }
    info = SchemaInfo(type_map, {})
    factory = CdrDecodeFactory({1: info})

    mcap_path = tmp_path / "test.mcap"
    with open(mcap_path, "wb") as f:
        writer = Writer(f)
        writer.start()
        schema_id = writer.register_schema("Msg", "ros2msg", b"")
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
