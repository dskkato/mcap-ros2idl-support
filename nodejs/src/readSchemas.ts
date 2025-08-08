import { FileHandleReadable } from "@mcap/nodejs";
import { McapIndexedReader } from "@mcap/core";
import { open } from "fs/promises";
import type { Schema } from "@mcap/core/dist/esm/src/types.js";

/**
 * Read and validate schemas from an MCAP file.
 *
 * Only schemas encoded as ROS 2 IDL or ROS 2 msg are returned. Schemas
 * containing union declarations are skipped since the downstream parser cannot
 * currently handle them.
 *
 * @param inputPath Path to the MCAP file on disk.
 * @returns Mapping of schema IDs to their schema records.
 */
export async function readSchemas(inputPath: string): Promise<Record<string, Schema>> {
  const fileHandle = await open(inputPath, "r");
  try {
    // Initialize an indexed reader to iterate through the MCAP schemas.
    const reader = await McapIndexedReader.Initialize({
      readable: new FileHandleReadable(fileHandle),
    });

    const schemas: Record<string, Schema> = {};
    const decoder = new TextDecoder("utf-8");
    for (const schema of reader.schemasById.values()) {
      if (schema.encoding !== "ros2idl" && schema.encoding !== "ros2msg") {
        // Fail fast for encodings we don't support.
        throw new Error(`Unsupported schema encoding: ${schema.encoding}`);
      }
      const idlText = decoder.decode(schema.data);
      if (idlText.includes("union")) {
        // Union types are not yet supported by downstream tooling, so warn and
        // skip them to avoid runtime errors.
        console.warn(
          `Skipping schema with union: ${schema.id}, name: ${schema.name}, encoding: ${schema.encoding}`,
        );
        continue;
      }
      // Store the validated schema using its numeric ID.
      schemas[schema.id] = schema;
    }
    return schemas;
  } finally {
    // Ensure the file handle is closed even if parsing fails.
    await fileHandle.close();
  }
}
