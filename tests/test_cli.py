import sys
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[1]))

from mcap_schema_cli import cli  # noqa: E402


def test_cli_invokes_node_when_no_defs(tmp_path):
    mcap_path = tmp_path / "test.mcap"
    mcap_path.write_bytes(b"")

    called = {}

    def fake_run(cmd, check):
        called["cmd"] = cmd
        Path(cmd[-1]).write_text("{}")
        return CompletedProcess(cmd, 0)

    class FakeReader:
        def iter_messages(self):
            return []

    with patch("subprocess.run", side_effect=fake_run):
        with patch("mcap_schema_cli.cli.make_reader", return_value=FakeReader()):
            sys.argv = ["prog", "--mcap-file", str(mcap_path)]
            cli.main()

    assert called["cmd"][0] == "mcap-schema-cli"
