// Reads one JSON string per line on stdin, writes one JSON list of [start, end] spans per line.
import { createInterface } from "node:readline";
import { LocalLinter } from "harper.js";
import { binaryInlined } from "harper.js/binaryInlined";

const linter = new LocalLinter({ binary: binaryInlined });
await linter.setup();
const rl = createInterface({ input: process.stdin, crlfDelay: Infinity });
for await (const line of rl) {
  if (!line.trim()) continue;
  const text = JSON.parse(line);
  const lints = await linter.lint(text, { language: "plaintext" });
  const spans = lints.map((l) => { const s = l.span(); return [s.start, s.end]; });
  process.stdout.write(JSON.stringify(spans) + "\n");
}
