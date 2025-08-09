"""Command-line interface for reading CDR messages from MCAP files."""

import json
import os
import sys
import tempfile
from argparse import ArgumentParser

from mcap.reader import make_reader

from .cdr_reader import CdrReader
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
    # add flag to use python implementation
    parser.add_argument(
        "--use-python-impl",
        action="store_true",
        help="Use pure Python implementation (experimental).",
    )
    args = parser.parse_args()

    if not args.use_python_impl:
        with tempfile.NamedTemporaryFile(suffix=".json") as tmp:
            type_defs_path = tmp.name
            run_node_cli([args.mcap_file, "-o", type_defs_path])
            schemas = load_idl(type_defs_path)

    else:
        # Pure Python implementation (experimental)
        from .idl_loader_py import load_idl as load_idl_py

        schemas = load_idl_py(args.mcap_file)

    id_to_cdr_reader = {
        schema_id: CdrReader(info.type_map, info.enum_map)
        for schema_id, info in schemas.items()
    }

    with open(args.mcap_file, "rb") as f:
        reader = make_reader(f)
        for topic, schema, message in reader.iter_messages():
            print(f"Topic: {topic}, Schema ID: {schema.schema_id}")
            if schema.schema_id not in id_to_cdr_reader:
                print(f"Schema ID {schema.schema_id} not found in type definitions.")
                continue
            msg = id_to_cdr_reader[schema.schema_id].read(topic.name, message.data)
            print(json.dumps(msg, indent=2))


if __name__ == "__main__":
    main()
