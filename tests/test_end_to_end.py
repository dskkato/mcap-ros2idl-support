import json
import subprocess
import sys
from pathlib import Path

import pytest
from mcap.reader import make_reader

from mcap_schema_cli.cdr_reader import CdrReader
from mcap_schema_cli.idl_loader import load_idl

GENERATE_SCRIPT = Path(__file__).parent / "generate_mcap.py"


@pytest.mark.parametrize("encoding", ["ros2msg", "ros2idl"])
def test_end_to_end(tmp_path, encoding):
    mcap_path = tmp_path / "test.mcap"
    subprocess.run(
        [sys.executable, str(GENERATE_SCRIPT), str(mcap_path), "--encoding", encoding],
        check=True,
    )

    subprocess.run(["npm", "run", "build"], check=True)
    types_path = tmp_path / "types.json"
    subprocess.run(
        ["node", "dist/index.js", str(mcap_path), "-o", str(types_path)], check=True
    )

    schemas = load_idl(str(types_path))
    info = next(iter(schemas.values()))
    reader = CdrReader(info.type_map, info.enum_map)

    with open(mcap_path, "rb") as f:
        r = make_reader(f)
        for schema, channel, msg in r.iter_messages():
            decoded = reader.read(schema.name, msg.data)
            assert decoded["data"] == "hello"
