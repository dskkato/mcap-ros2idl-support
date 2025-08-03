import json
from argparse import ArgumentParser

from mcap.reader import make_reader

from cdr_reader import CdrReader
from idl_loader import load_idl


if __name__ == "__main__":
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

    id_to_type_map, id_to_enum_map = load_idl(args.type_definitions)
    id_to_cdr_reader = {
        schema_id: CdrReader(type_map, id_to_enum_map.get(schema_id))
        for schema_id, type_map in id_to_type_map.items()
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
