import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, rm, open } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { McapWriter } from "@mcap/core";
import { FileHandleWritable } from "@mcap/nodejs";
import { promisify } from "node:util";
import { execFile } from "node:child_process";

const execFileAsync = promisify(execFile);

const encoder = new TextEncoder();

test("CLI outputs parsed schemas", async () => {
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

    // Build the CLI and run it against the generated MCAP
    await execFileAsync("npm", ["run", "build"]);
    const { stdout } = await execFileAsync("node", ["mcap_schema_cli/dist/index.js", mcapPath], {
      encoding: "utf8",
    });

    const output = JSON.parse(stdout);
    const defs = output[String(schemaId)];
    assert.ok(Array.isArray(defs));
    assert.equal(defs[0].name, "string");
    assert.equal(defs[0].definitions[0].name, "data");
    assert.equal(defs[0].definitions[0].type, "string");
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});
