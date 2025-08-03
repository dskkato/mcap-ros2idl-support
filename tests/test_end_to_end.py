import subprocess
import sys
from pathlib import Path

import pytest
from mcap.reader import make_reader

sys.path.append(str(Path(__file__).resolve().parents[1]))

from mcap_schema_cli.cdr_reader import CdrReader  # noqa: E402
from mcap_schema_cli.idl_loader import load_idl  # noqa: E402


@pytest.mark.parametrize("encoding", ["ros2msg", "ros2idl"])
def test_end_to_end(tmp_path: Path, encoding: str) -> None:
    mcap_path = tmp_path / "test.mcap"
    subprocess.run(
        ["node", "tests/generate_mcap.js", str(mcap_path), encoding],
        check=True,
    )

    json_path = tmp_path / "types.json"
    subprocess.run(
        ["node", "dist/index.js", str(mcap_path), "-o", str(json_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    schemas = load_idl(str(json_path))

    with open(mcap_path, "rb") as f:
        reader = make_reader(f)
        for schema, channel, message in reader.iter_messages():
            info = schemas[schema.id]
            cdr_reader = CdrReader(info.type_map, info.enum_map)
            decoded = cdr_reader.read(schema.name, message.data)
            assert decoded["data"] == "hello"
