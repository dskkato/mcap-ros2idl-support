"""Command-line interface for reading CDR messages from MCAP files."""

import json
from argparse import ArgumentParser

from mcap.reader import make_reader

from .cdr_reader import CdrReader
from .idl_loader import load_idl


def main() -> None:
    """Entry point for the ``mcap-schema-cli`` command."""
    parser = ArgumentParser(description="Read CDR messages from MCAP files.")
    parser.add_argument(
        "--type-definitions",
        type=str,
        required=True,
        help="Path to the JSON file containing type definitions.",
    )
    parser.add_argument(
        "--mcap-file",
        type=str,
        required=True,
        help="Path to the MCAP file to read messages from.",
    )
    args = parser.parse_args()

    schemas = load_idl(args.type_definitions)
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
