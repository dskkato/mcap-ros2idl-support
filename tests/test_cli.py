import json
import sys
from collections import namedtuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.modules.pop("mcap_ros2idl_support", None)
import mcap_ros2idl_support.cli as cli


def test_cli_decodes_with_schema_name(tmp_path, capsys, monkeypatch):
    type_defs = {
        "1": [
            {
                "name": "Status",
                "definitions": [
                    {"name": "UNKNOWN", "type": "uint8", "isComplex": False, "isConstant": True, "value": 0},
                    {"name": "OK", "type": "uint8", "isComplex": False, "isConstant": True, "value": 1},
                ],
            },
            {
                "name": "Msg",
                "definitions": [
                    {"name": "status", "type": "uint8", "isComplex": False, "enumType": "Status"},
                ],
            },
        ]
    }
    type_path = tmp_path / "types.json"
    type_path.write_text(json.dumps(type_defs))
    mcap_path = tmp_path / "data.mcap"
    mcap_path.write_bytes(b"dummy")

    data = b"\x00\x00\x00\x00" + b"\x01"

    Topic = namedtuple("Topic", ["name"])
    Schema = namedtuple("Schema", ["schema_id", "name"])
    Message = namedtuple("Message", ["data"])

    class FakeReader:
        def iter_messages(self):
            yield Topic("NotMsg"), Schema(1, "Msg"), Message(data)

    monkeypatch.setattr(cli, "make_reader", lambda _: FakeReader())
    monkeypatch.setattr(sys, "argv", [
        "cli",
        "--type-definitions",
        str(type_path),
        "--mcap-file",
        str(mcap_path),
    ])

    cli.main()
    captured = capsys.readouterr()
    assert '"status": "OK"' in captured.out
