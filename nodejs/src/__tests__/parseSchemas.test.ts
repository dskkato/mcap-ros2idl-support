import test from "node:test";
import assert from "node:assert/strict";
import type { Schema } from "@mcap/core/dist/esm/src/types.js";
import { buildOutputData } from "../parseSchemas.js";

const encoder = new TextEncoder();

test("buildOutputData converts schemas to definitions", async () => {
  const schemas: Record<string, Schema> = {
    "1": { id: 1, name: "string", encoding: "ros2msg", data: encoder.encode("string data") },
    "2": {
      id: 2,
      name: "test/Msg",
      encoding: "ros2idl",
      data: encoder.encode("module test { struct Msg { string data; }; };"),
    },
  };

  const output = await buildOutputData(schemas);
  assert.equal(output["1"][0].name, "string");
  assert.equal(output["1"][0].definitions[0].name, "data");
  assert.equal(output["1"][0].definitions[0].type, "string");
  assert.equal(output["2"][0].name, "test/Msg");
  assert.equal(output["2"][0].definitions[0].name, "data");
});
