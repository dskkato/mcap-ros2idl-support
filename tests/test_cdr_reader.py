import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcap_schema_cli import (  # noqa: E402
    CdrReader,
    MessageDefinitionField,
    MessageReader,
    MessageType,
)


def test_enum_with_uint8():
    type_map = {
        "Status": MessageType(
            "Status",
            [
                {
                    "name": "UNKNOWN",
                    "type": "uint8",
                    "isComplex": False,
                    "isConstant": True,
                    "value": 0,
                },
                {
                    "name": "OK",
                    "type": "uint8",
                    "isComplex": False,
                    "isConstant": True,
                    "value": 2,
                },
            ],
        ),
        "Msg": MessageType(
            "Msg",
            [
                {
                    "name": "status",
                    "type": "uint8",
                    "isComplex": False,
                    "enumType": "Status",
                }
            ],
        ),
    }
    enum_map = {"Status": {0: "UNKNOWN", 2: "OK"}}
    reader = CdrReader(type_map, enum_map)
    data = b"\x00\x00\x00\x00" + b"\x02"
    assert reader.read("Msg", data) == {"status": "OK"}


def test_default_with_reader_map():
    type_map = {"Msg": MessageType("Msg", [])}
    reader_map = {
        "Msg": MessageReader(
            [MessageDefinitionField(name="value", type="uint32", default_value=5)]
        )
    }
    reader = CdrReader(type_map, reader_map=reader_map)
    data = b"\x00\x00\x00\x00"
    assert reader.read("Msg", data) == {"value": 5}
