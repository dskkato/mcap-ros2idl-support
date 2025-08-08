import type { MessageDefinition } from "@foxglove/message-definition";
import { parseRos2idl } from "@foxglove/ros2idl-parser";
import { parse as parseRos2msg } from "@foxglove/rosmsg";
import type { Schema } from "@mcap/core/dist/esm/src/types.js";

export async function buildOutputData(
  schemasById: Record<string, Schema>,
): Promise<Record<string, MessageDefinition[]>> {
  const output: Record<string, MessageDefinition[]> = {};
  const decoder = new TextDecoder("utf-8");
  for (const schema of Object.values(schemasById)) {
    const idlText = decoder.decode(schema.data);
    if (schema.encoding === "ros2idl") {
      output[schema.id] = await parseRos2idl(idlText);
    } else if (schema.encoding === "ros2msg") {
      const definitions = await parseRos2msg(idlText);
      if (definitions.length > 0) {
        definitions[0].name = schema.name;
      }
      output[schema.id] = definitions;
    } else {
      console.warn(`Unsupported schema encoding: ${schema.encoding} for schema ID: ${schema.id}`);
    }
  }
  return output;
}
