import { open } from "node:fs/promises";
import { McapWriter } from "@mcap/core";
import { FileHandleWritable } from "@mcap/nodejs";

const encoder = new TextEncoder();

const [, , mcapPath, encoding = "ros2msg"] = process.argv;

async function main() {
  const handle = await open(mcapPath, "w");
  const writer = new McapWriter({
    writable: new FileHandleWritable(handle),
    useSummaryOffsets: true,
    useMessageIndex: true,
  });

  try {
    await writer.start({ profile: "", library: "test" });
    const schemaData =
      encoding === "ros2idl"
        ? encoder.encode("struct Example { string data; };")
        : encoder.encode("string data");
    const schemaId = await writer.registerSchema({
      name: "Example",
      encoding,
      data: schemaData,
    });
    const channelId = await writer.registerChannel({
      schemaId,
      topic: "/test",
      messageEncoding: "cdr",
      metadata: new Map(),
    });
    const messageData = Buffer.concat([
      Buffer.from([0, 0, 0, 0]),
      Buffer.from([6, 0, 0, 0]),
      Buffer.from("hello\0"),
    ]);
    await writer.addMessage({
      channelId,
      sequence: 0,
      logTime: 0n,
      publishTime: 0n,
      data: messageData,
    });
    await writer.end();
  } finally {
    await handle.close();
  }
}

await main();
