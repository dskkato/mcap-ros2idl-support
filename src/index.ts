import { Command } from "commander";
import * as fs from "fs";
import { stdout } from "process";
import type { MessageDefinition } from "@foxglove/message-definition";
import { readSchemas } from "./readSchemas.js";
import { buildOutputData } from "./parseSchemas.js";

function writeOutput(data: Record<string, MessageDefinition[]>, out: number | string): void {
  fs.writeFileSync(out, JSON.stringify(data, null, 2));
}

const program = new Command();

program
  .name("mcap-schema-cli")
  .description("Extract schema definitions from an MCAP file")
  .version("0.0.1")
  .argument("<mcapFile>", "Path to the MCAP file")
  .option("-o, --output <file>", "Output JSON file (optional)")
  .action(async (mcapFile: string, options: { output?: string }) => {
    if (!mcapFile) {
      console.error("Please provide a path to the MCAP file.");
      process.exit(1);
    }
    if (!fs.existsSync(mcapFile)) {
      console.error(`MCAP file not found: ${mcapFile}`);
      process.exit(1);
    }
    if (!mcapFile.endsWith(".mcap")) {
      console.error("The provided file is not a valid MCAP file.");
      process.exit(1);
    }
    console.error(`Processing MCAP file: ${mcapFile}`);
    const outputFile = options.output || stdout.fd;
    try {
      const schemasById = await readSchemas(mcapFile);
      const outputData = await buildOutputData(schemasById);
      writeOutput(outputData, outputFile);
      if (typeof outputFile === "string") {
        console.error(`Schemas have been written to ${outputFile}`);
      }
    } catch (error) {
      console.error("Error processing MCAP file:", error);
      process.exit(1);
    }
  });
program.parse();
