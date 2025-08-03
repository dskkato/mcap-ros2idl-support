import { FileHandleReadable } from "@mcap/nodejs";
import { McapIndexedReader } from "@mcap/core";
import { open } from "fs/promises";
import type { Schema } from "@mcap/core/dist/esm/src/types.js";

export async function readSchemas(inputPath: string): Promise<Record<string, Schema>> {
  const fileHandle = await open(inputPath, "r");
  try {
    const reader = await McapIndexedReader.Initialize({
      readable: new FileHandleReadable(fileHandle),
    });

    const schemas: Record<string, Schema> = {};
    const decoder = new TextDecoder("utf-8");
    for (const schema of reader.schemasById.values()) {
      if (schema.encoding !== "ros2idl" && schema.encoding !== "ros2msg") {
        throw new Error(`Unsupported schema encoding: ${schema.encoding}`);
      }
      const idlText = decoder.decode(schema.data);
      if (idlText.includes("union")) {
        console.warn(
          `Skipping schema with union: ${schema.id}, name: ${schema.name}, encoding: ${schema.encoding}`,
        );
        continue;
      }
      schemas[schema.id] = schema;
    }
    return schemas;
  } finally {
    await fileHandle.close();
  }
}
