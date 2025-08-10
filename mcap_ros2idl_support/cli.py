"""Command-line interface for reading CDR messages from MCAP files."""

import json
import os
import sys
import tempfile
from argparse import ArgumentParser

from mcap.reader import make_reader

from .decode_factory import CdrDecodeFactory
from .idl_loader import load_idl
from .node_cli import run_node_cli


def main() -> None:
    """Entry point for the ``mcap-ros2idl-support`` command."""
    prog = "mcap-ros2idl-support"
    if sys.argv[0].endswith("__main__.py"):
        prog = f"{os.path.basename(sys.executable)} -m mcap_ros2idl_support"
    parser = ArgumentParser(prog=prog, description="Read CDR messages from MCAP files.")
    parser.add_argument(
        "--mcap-file",
        type=str,
        required=True,
        help="Path to the MCAP file to read messages from.",
    )
    parser.add_argument(
        "--use-nodejs-impl",
        action="store_true",
        help="Use Node.js implementation (experimental).",
    )
    args = parser.parse_args()

    if args.use_nodejs_impl:
        with tempfile.NamedTemporaryFile(suffix=".json") as tmp:
            type_defs_path = tmp.name
            run_node_cli([args.mcap_file, "-o", type_defs_path])
            schemas = load_idl(type_defs_path)

    else:
        # Pure Python implementation (experimental)
        from .idl_loader_py import load_idl as load_idl_py

        schemas = load_idl_py(args.mcap_file)

    factory = CdrDecodeFactory(schemas)

    with open(args.mcap_file, "rb") as f:
        reader = make_reader(f, decoder_factories=[factory])
        for decoded in reader.iter_decoded_messages():
            print(f"Topic: {decoded.channel.topic}, Schema ID: {decoded.schema.id}")
            print(json.dumps(decoded.decoded_message, indent=2))


if __name__ == "__main__":
    main()
