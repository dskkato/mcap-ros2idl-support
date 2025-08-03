import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, rm, open } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { McapWriter } from "@mcap/core";
import { FileHandleWritable } from "@mcap/nodejs";
import { readSchemas } from "../readSchemas.js";

const encoder = new TextEncoder();

test("readSchemas reads schemas from an MCAP file", async () => {
  const dir = await mkdtemp(join(tmpdir(), "mcap-schema-cli-"));
  const mcapPath = join(dir, "test.mcap");
  const handle = await open(mcapPath, "w");
  const writer = new McapWriter({
    writable: new FileHandleWritable(handle),
    useSummaryOffsets: true,
    useMessageIndex: true,
  });

  try {
    await writer.start({ profile: "", library: "test" });
    const schemaId = await writer.registerSchema({
      name: "string",
      encoding: "ros2msg",
      data: encoder.encode("string data"),
    });
    const channelId = await writer.registerChannel({
      schemaId,
      topic: "/test",
      messageEncoding: "json",
      metadata: new Map(),
    });
    await writer.addMessage({
      channelId,
      sequence: 0,
      logTime: 0n,
      publishTime: 0n,
      data: encoder.encode("hello"),
    });
    await writer.end();
    await handle.close();

    const schemas = await readSchemas(mcapPath);
    const schema = schemas[String(schemaId)];
    assert.ok(schema);
    assert.equal(schema.name, "string");
    assert.equal(schema.encoding, "ros2msg");
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});
