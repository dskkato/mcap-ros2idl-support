#!/usr/bin/env node
import { FileHandleReadable } from "@mcap/nodejs";
import { Command } from "commander";
import { MessageDefinition } from "@foxglove/message-definition";
import { open } from "fs/promises";
import { McapIndexedReader } from "@mcap/core";
import { parseRos2idl } from "@foxglove/ros2idl-parser";
import * as fs from "fs";
import { parse as parseRos2msg } from "@foxglove/rosmsg";
import { stdout } from "process";
import { Console } from 'console';
import { Schema } from "@mcap/core/dist/esm/src/types.js";

const logger = new Console(process.stderr);


const program = new Command();

async function dumpSchemasAsText(inputPath: string) {
  const fileHandle = await open(inputPath, "r");

  const reader = await McapIndexedReader.Initialize({
    readable: new FileHandleReadable(fileHandle),
  });

  const schema_texts: { [id: string]: Schema } = {};

  const decoder = new TextDecoder("utf-8");
  for (const schema of reader.schemasById.values()) {
    if (schema.encoding !== "ros2idl" && schema.encoding !== "ros2msg") {
      throw new Error(`Unsupported schema encoding: ${schema.encoding}`);
    }
    const idlText = decoder.decode(schema.data);
    // if the schema contains "union", skip it
    if (idlText.includes("union")) {
      logger.warn(`Skipping schema with union: ${schema.id}, name: ${schema.name}, encoding: ${schema.encoding}`);
      continue;
    }
    // Store the schema text with its encoding
    schema_texts[schema.id] = schema;
  }
  fileHandle.close();
  return schema_texts;
}

program
  .name("mcap-schema-cli")
  .description("Extract schema definitions from an MCAP file")
  .version("0.0.1")
  .argument("<mcapFile>", "Path to the MCAP file")
  .option("-o, --output <file>", "Output JSON file (optional)")
  .action(async (mcapFile, options) => {
    if (!mcapFile) {
      logger.error("Please provide a path to the MCAP file.");
      process.exit(1);
    }
    if (!fs.existsSync(mcapFile)) {
      logger.error(`MCAP file not found: ${mcapFile}`);
      process.exit(1);
    }
    if (!mcapFile.endsWith(".mcap")) {
      logger.error("The provided file is not a valid MCAP file.");
      process.exit(1);
    }
    // Log the input file and output file
    logger.log(`Input MCAP file: ${mcapFile}`);
    if (options.output) {
      logger.log(`Output file: ${options.output}`);
    } else {
      logger.log("No output file specified, results will be printed to stdout.");
    }

    logger.log(`Processing MCAP file: ${mcapFile}`);
    const outputFile = options.output || stdout.fd;
    logger.log(`Output will be written to: ${outputFile}`);
    try {
      const schemasById = await dumpSchemasAsText(mcapFile);
      const outputData: { [id: string]: MessageDefinition[] } = {};
      const decoder = new TextDecoder("utf-8");
      for (const schema of Object.values(schemasById)) {
        const idlText: string = decoder.decode(schema.data);
        if (schema.encoding === "ros2idl") {
          outputData[schema.id] = await parseRos2idl(idlText);
        } else if (schema.encoding === "ros2msg") {
          var definitions = await parseRos2msg(idlText);
          definitions[0]["name"] = schema.name; // Set the name to the schema ID
          outputData[schema.id] = definitions;
        } else {
          logger.warn(`Unsupported schema encoding: ${schema.encoding} for schema ID: ${schema.id}`);
          continue;
        }
      }
      fs.writeFileSync(outputFile, JSON.stringify(outputData, null, 2));
      logger.log("");
      logger.log(`Schemas have been written to ${outputFile}`);
    } catch (error) {
      logger.error("Error processing MCAP file:", error);
      process.exit(1);
    }

  });
program.parse();
