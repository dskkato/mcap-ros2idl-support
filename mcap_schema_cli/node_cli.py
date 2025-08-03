"""Helpers to invoke the bundled Node.js CLI."""

from pathlib import Path
import subprocess
import sys
from typing import Sequence


def run_node_cli(args: Sequence[str]) -> None:
    """Execute the bundled Node script with ``args``.

    ``args`` should contain the command line arguments passed to the Node CLI
    *excluding* the node executable and script path.
    """

    js_path = Path(__file__).with_name("dist") / "index.js"
    cmd = ["node", str(js_path), *args]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(
            f"Error: Node.js CLI execution failed with exit code {e.returncode}.",
            file=sys.stderr,
        )
        if e.output:
            print("Output:", e.output, file=sys.stderr)
        if e.stderr:
            print("Error output:", e.stderr, file=sys.stderr)
        raise
