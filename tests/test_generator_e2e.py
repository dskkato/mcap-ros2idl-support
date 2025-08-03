import subprocess
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from mcap_schema_cli.cdr_reader import CdrReader  # noqa: E402
from mcap_schema_cli.idl_loader import load_idl  # noqa: E402
from mcap.reader import make_reader  # noqa: E402


@pytest.fixture(scope="session")
def build_cli() -> None:
    subprocess.run(["npm", "run", "build"], check=True)


@pytest.mark.parametrize("encoding", ["ros2msg", "ros2idl"])
def test_generate_and_decode(tmp_path, build_cli, encoding):
    mcap_path = tmp_path / "test.mcap"
    types_path = tmp_path / "types.json"

    script = Path(__file__).resolve().parents[1] / "generate_mcap.py"
    subprocess.run(
        [sys.executable, str(script), "--encoding", encoding, "--output", str(mcap_path)],
        check=True,
    )

    subprocess.run(
        ["node", "dist/index.js", str(mcap_path), "-o", str(types_path)],
        check=True,
    )

    schemas = load_idl(str(types_path))
    readers = {
        sid: CdrReader(info.type_map, info.enum_map) for sid, info in schemas.items()
    }

    with open(mcap_path, "rb") as f:
        reader = make_reader(f)
        for topic, schema, message in reader.iter_messages():
            decoded = readers[schema.schema_id].read(topic.name, message.data)
            assert decoded["data"] == "hello"
