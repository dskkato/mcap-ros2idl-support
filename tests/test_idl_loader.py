import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcap_schema_cli.idl_loader import load_idl  # noqa: E402


def test_load_idl(tmp_path):
    data = {
        "1": [
            {
                "name": "Foo",
                "definitions": [
                    {"name": "bar", "type": "string", "isComplex": False},
                    {
                        "name": "BAZ",
                        "type": "int32",
                        "isComplex": False,
                        "isConstant": True,
                        "value": 0,
                    },
                ],
            }
        ]
    }
    json_path = tmp_path / "types.json"
    json_path.write_text(json.dumps(data))
    schemas = load_idl(str(json_path))
    assert 1 in schemas
    info = schemas[1]
    assert "Foo" in info.type_map
    assert "Foo" in info.enum_map
    assert info.enum_map["Foo"][0] == "BAZ"
    assert info.type_map["Foo"].name == "Foo"
    assert "Foo" in info.reader_map
    assert len(info.type_map["Foo"].fields) == 1
