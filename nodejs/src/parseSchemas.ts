import type { MessageDefinition } from "@foxglove/message-definition";
import { parseRos2idl } from "@foxglove/ros2idl-parser";
import { parse as parseRos2msg } from "@foxglove/rosmsg";
import type { Schema } from "@mcap/core/dist/esm/src/types.js";

/**
 * Convert raw schema records into message definitions keyed by schema ID.
 *
 * Each schema is decoded and parsed according to its declared encoding. The
 * resulting message definitions can then be serialized to JSON for downstream
 * consumption.
 */
export async function buildOutputData(
  schemasById: Record<string, Schema>,
): Promise<Record<string, MessageDefinition[]>> {
  const output: Record<string, MessageDefinition[]> = {};
  const decoder = new TextDecoder("utf-8");
  for (const schema of Object.values(schemasById)) {
    const idlText = decoder.decode(schema.data);
    if (schema.encoding === "ros2idl") {
      // Parse ROS 2 interface definition language files.
      output[schema.id] = await parseRos2idl(idlText);
    } else if (schema.encoding === "ros2msg") {
      // Parse legacy ROS .msg files and ensure the top-level definition name
      // matches the schema name from the MCAP file.
      const definitions = await parseRos2msg(idlText);
      if (definitions.length > 0) {
        definitions[0].name = schema.name;
      }
      output[schema.id] = definitions;
    } else {
      // Warn and skip any schemas we don't know how to decode.
      console.warn(`Unsupported schema encoding: ${schema.encoding} for schema ID: ${schema.id}`);
    }
  }
  return output;
}
