import { Command } from "commander";
import * as fs from "fs";
import { stdout } from "process";
import type { MessageDefinition } from "@foxglove/message-definition";
import { readSchemas } from "./readSchemas.js";
import { buildOutputData } from "./parseSchemas.js";

/**
 * Serialize the parsed schema definitions to JSON and write them to the
 * provided file descriptor or path.
 *
 * @param data Mapping of schema IDs to their message definitions.
 * @param out File path or descriptor to write to. Defaults to stdout if a
 *   descriptor is used.
 */
function writeOutput(data: Record<string, MessageDefinition[]>, out: number | string): void {
  fs.writeFileSync(out, JSON.stringify(data, null, 2));
}

const program = new Command();

program
  .name("mcap-schema-extractor")
  .description("Extract schema definitions from an MCAP file")
  .version("0.0.1")
  .argument("<mcapFile>", "Path to the MCAP file")
  .option("-o, --output <file>", "Output JSON file (optional)")
  .action(async (mcapFile: string, options: { output?: string }) => {
    // Ensure the user supplied a valid MCAP file path.
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
    // Use stdout by default unless an explicit output path is provided.
    const outputFile = options.output || stdout.fd;
    try {
      // Read schemas from the MCAP file and convert them into message definitions.
      const schemasById = await readSchemas(mcapFile);
      const outputData = await buildOutputData(schemasById);

      // Persist the extracted schema information.
      writeOutput(outputData, outputFile);
      if (typeof outputFile === "string") {
        console.error(`Schemas have been written to ${outputFile}`);
      }
    } catch (error) {
      console.error("Error processing MCAP file:", error);
      process.exit(1);
    }
  });

// Execute the CLI program and report parsing failures.
program.parseAsync().catch((error) => {
  console.error("CLI parsing failed:", error);
  process.exit(1);
});
