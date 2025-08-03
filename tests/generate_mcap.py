import argparse

from mcap.writer import Writer


def encode_cdr_string(value: str) -> bytes:
    data = value.encode("utf-8") + b"\x00"
    length = len(data)
    return length.to_bytes(4, "little") + data


def main():
    parser = argparse.ArgumentParser(description="Generate a simple MCAP file")
    parser.add_argument("output", help="Path to output MCAP file")
    parser.add_argument("--encoding", choices=["ros2msg", "ros2idl"], default="ros2msg")
    args = parser.parse_args()

    schema_data_map = {
        "ros2msg": b"string data\n",
        "ros2idl": b"struct String { string data; };",
    }
    schema_data = schema_data_map[args.encoding]

    cdr = (0).to_bytes(4, "little") + encode_cdr_string("hello")

    with open(args.output, "wb") as f:
        writer = Writer(f)
        writer.start(profile="", library="test")
        schema_id = writer.register_schema(
            name="String", encoding=args.encoding, data=schema_data
        )
        channel_id = writer.register_channel(
            topic="String", message_encoding="cdr", schema_id=schema_id
        )
        writer.add_message(channel_id=channel_id, log_time=0, publish_time=0, data=cdr)
        writer.finish()


if __name__ == "__main__":
    main()
